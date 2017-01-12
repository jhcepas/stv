from .common import *
from .utils import timeit, debug
from .painter import QETEPainter

from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
import base64
# TODO: cover scenario where internal nodes are higher than all children
@timeit
def update_rect_coordinates(img_data, cached_prepostorder,
                            cached_preorder,
                            leaf_apertures,
                            branch_scale):

    current_y = 0.0
    current_x = 0.0
    root_visited = False

    for nid in cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0:
            root_visited = True
        node = cached_preorder[abs(nid)]
        dim = img_data[node._id]

        # calculate node width, could this be cached so it is not recalculate
        # in post and pre order?
        wtop = max(dim[_btw], dim[_blen]) + dim[_brw]
        wbot = max(dim[_bbw], dim[_blen]) + dim[_brw]
        node_width = max(wtop, wbot)

        if postorder:
            if len(node.children) > 1:
                # If node has more than 1 children, set vertical center to the
                # middle of all their siblings
                ycen_0 = img_data[node.children[0]._id][_ycenter]
                ycen_1 = img_data[node.children[-1]._id][_ycenter]
                node_ycenter = ycen_0 + ((ycen_1 - ycen_0) / 2.0)
                node_ystart = img_data[node.children[0]._id][_ystart]
                node_yend = img_data[node.children[-1]._id][_yend]
            else:
                # Otherwise just set the same rotation as the single child
                node_ycenter = img_data[node.children[0]._id][_ycenter]
                node_ystart = img_data[node.children[0]._id][_ystart]
                node_yend = img_data[node.children[0]._id][_yend]

            dim[_ystart] = node_ystart
            dim[_yend] = node_yend
            dim[_ycenter] = node_ycenter
            dim[_xend] = current_x

            for ch in node.children:
                dim[_fnw] = max(dim[_fnw], img_data[ch._id][_fnw])
                dim[_fnh] += img_data[ch._id][_fnh]
            dim[_fnw] += node_width
            current_x -= node_width
        else:
            if dim[_is_leaf]:
                dim[_ystart] = current_y
                dim[_yend] = current_y + dim[_nht] + dim[_nhb] + dim[_bh]
                dim[_ycenter] = current_y + dim[_nht] + dim[_bh]/2.0

                current_y += dim[_nht] + dim[_nhb] + dim[_bh]
                # increase hz
                dim[_xend] = current_x + node_width
                dim[_fnw] = node_width
                dim[_fnh] = dim[_yend] - dim[_ystart]
            else:
                current_x += node_width

    return img_data[0][_fnw], img_data[0][_fnh]


@timeit
def get_rect_collision_paths(tree_image):
    """ collision paths in the un-transformed scene"""
    collistion_paths = []
    img_data = tree_image.img_data
    for nid, dim in enumerate(img_data):
        node = tree_image.cached_preorder[nid]
        ystart = dim[_ystart]
        yend = dim[_yend]
        xend = dim[_xend]
        xstart = img_data[dim[_parent]][_xend]
        path = QtGui.QPainterPath()
        fpath= QtGui.QPainterPath()
        path.addRect(xstart, ystart, xend-xstart, yend-ystart)
        fpath.addRect(xstart, ystart, dim[_fnw], dim[_fnh])
        collistion_paths.append([path, fpath])
    return collistion_paths


@timeit
def draw_region_rect(tree_image, region, zoom_factor, pngreturn=False):
    COLLAPSE_RESOLUTION = 1
    # DEBUGGING INFO
    DRAWN, SKIPPED, TOO_SMALL, COLLAPSED, MULTI, ITERS = 0, 0, 0, 0, 0, 0
    coll_paths = tree_image.rect_collision_paths
    img_data = tree_image.img_data

    ii = QImage(region[2], region[3], QImage.Format_RGB32)
    ii.fill(QColor("white"))

    _pp = QPainter()
    _pp.begin(ii)
    _pp.setRenderHint(QPainter.Antialiasing)
    _pp.setRenderHint(QPainter.TextAntialiasing)
    _pp.setRenderHint(QPainter.SmoothPixmapTransform)
    # Prevent drawing outside target_rect boundaries
    _pp.setClipRect(0, 0, region[2], region[3])#, Qt.IntersectClip)
    # Transform space of coordinates: I want source_rect.top_left() to be
    # translated as 0,0
    matrix = QTransform().translate(-region[0], -region[1])
    #matrix.scale(zoom_factor, zoom_factor)
    _pp.setWorldTransform(matrix, True)

    pp = QETEPainter(painter=_pp)

    pp.zoom_factor = zoom_factor
    scene_rect = QRectF(region[0]/zoom_factor, region[1]/zoom_factor,
                        region[2]/zoom_factor, region[3]/zoom_factor)

    curr = 0
    nid = curr
    end = img_data[curr][_max_leaf_idx] + 1
    while curr < end:
        ITERS += 1
        draw_collapsed = 0
        nid = curr

        dim = img_data[nid]

        path = coll_paths[nid][0]
        fpath = coll_paths[nid][1]

        if (dim[_fnh] * zoom_factor) < 0.25:
            curr = int(dim[_max_leaf_idx] + 1)
            TOO_SMALL += 1
            continue

        # if desdendant space is too small, draw the whole branch as a single
        # simplified item
        elif not dim[_is_leaf] and (dim[_fnh] * zoom_factor) < COLLAPSE_RESOLUTION:
            curr = int(dim[_max_leaf_idx] + 1)
            draw_collapsed = 2
            path = fpath
            COLLAPSED += 1
        elif not dim[_is_leaf] and (dim[_max_leaf_idx] - curr) == len(tree_image.cached_preorder[curr].children) and \
             (dim[_fnh] * zoom_factor)/len(tree_image.cached_preorder[curr].children) < 1:
            curr = int(dim[_max_leaf_idx] + 1)
            draw_collapsed = 3
            MULTI += 1
        else:
            curr += 1

        # skip if node does not overlap with requested region
        if not path.intersects(scene_rect):
            # and skip all descendants in case none fits in region
            if not fpath.intersects(scene_rect):
                new_curr = max(int(dim[_max_leaf_idx]+1), curr)
                SKIPPED += new_curr - curr
                curr = new_curr
            continue

        # Draw the node
        DRAWN += 1
        node = tree_image.cached_preorder[nid]
        parent_radius = img_data[dim[_parent]][_xend] if nid else tree_image.root_open
        branch_length = dim[_blen]
        nw = max(dim[_blen], dim[_btw], dim[_bbw]) + dim[_brw]
        extra_length = max(dim[_btw], dim[_bbw]) - dim[_blen]

        if draw_collapsed:
            # HZ line
            pp.draw_line(parent_radius, dim[_ycenter],
                         parent_radius + branch_length, dim[_ycenter])

            pp.draw_line(parent_radius + branch_length, dim[_ycenter],
                         parent_radius + branch_length + extra_length, dim[_ycenter], 'grey')

        else:
            if not dim[_is_leaf] and len(node.children) > 1:
                ycen_0 = tree_image.img_data[node.children[0]._id][_ycenter]
                ycen_1 = tree_image.img_data[node.children[-1]._id][_ycenter]
                # VT line
                pp.draw_line(parent_radius + nw, ycen_0,
                             parent_radius + nw, ycen_1)
            # HZ line
            pp.draw_line(parent_radius, dim[_ycenter],
                         parent_radius + branch_length, dim[_ycenter])

            pp.draw_line(parent_radius + branch_length, dim[_ycenter],
                         parent_radius + branch_length + extra_length, dim[_ycenter], 'grey')

            draw_faces(pp, parent_radius, dim[_ycenter]*zoom_factor, node, dim, zoom_factor, tree_image, is_collapsed=False)

        # label_rect = path.boundingRect()
        # if dim[_fnh] *zoom_factor > 60 and (dim[_rad]-parent_radius) > 100:
        #     pp.save()
        #     pp.setPen(QColor("white"))
        #     pp.setBrush(QColor("royalBlue"))
        #     qfont = QFont("Verdana",pointSize=16)
        #     qfont.setWeight(QFont.Black)
        #     fm = QFontMetrics(qfont)
        #     text_w = fm.width(node.name)
        #     pp.setFont(qfont)
        #     pp.setOpacity(0.8)
        #     new_rad, new_angle = get_qt_corrected_angle(parent_radius, dim[_acenter])
        #     node_x, node_y = get_cart_coords((new_rad*zoom_factor), new_angle, cx*zoom_factor, cy*zoom_factor)
        #     if dim[_acenter] <R90 or dim[_acenter] >R270:
        #         node_x -= text_w

        #     text_path = QPainterPath()
        #     text_path.addText(node_x, node_y, qfont, node.name)
        #     #pp.drawText(node_x, node_y, node.name)
        #     pp.drawPath(text_path)
        #     pp.restore()


    print "NODES DRAWN:", DRAWN, 'skipped:', SKIPPED, 'too_small:', TOO_SMALL, "collapsed:", COLLAPSED, "iters:", ITERS, "MULTI:", MULTI

    pp.pp.end()
    ba = QtCore.QByteArray()
    buf = QtCore.QBuffer(ba)
    buf.open(QtCore.QIODevice.WriteOnly)
    ii.save(buf, "PNG")
    #ii.save('/Users/jhc/testimg.png')
    if pngreturn:
        return ba.data()
    else:
        return base64.encodestring(ba.data())


def draw_faces(painter, x, y, node, dim, zoom_factor, tree_image, is_collapsed):
    pp = painter.pp
    def draw_face_column(faces, _x, _y, _rad, face_zoom_factor):
        for _f, fw, fh in faces:
            if not dim[_is_leaf] and _f.only_if_leaf and not is_collapsed:
                continue
            restore_painter = False
            _f.node = node
            _f._pre_draw()

            if _f.fill_color:
                pp.save()
                pp.scale(1/face_zoom_factor, 1/face_zoom_factor)
                face_path = QTransform().translate(-_rad, 0).map(
                    get_arc_path(_rad, _rad + _f._width()*face_zoom_factor, [-a_top, a_bot]))
                pp.fillPath(face_path, QColor(_f.fill_color))
                pp.restore()

            if correct_rotation and _f.rotable:
                restore_painter = True
                pp.save()
                pp.setTransform(pp.transform().translate(_x+(fw/2), _y+(fh/2)).rotate(180).translate(-(_x+(fw/2)), -(_y+(fh/2))))
            _f.painter = painter
            _f._draw((_x + _f.margin_left), (_y + _f.margin_top), face_zoom_factor)

            if restore_painter:
                pp.restore()
            _y += fh


    facegrid = node._temp_faces
    mode = tree_image.tree_style.mode
    if not facegrid:
        return

    if mode == 'c':
        correct_rotation = True if dim[_acenter] > R90 and dim[_acenter] < R270 else False
    else:
        correct_rotation = False

    a_top = dim[_acenter] - dim[_astart] # same as dim[_ycenter] - dim[_ystart]
    a_bot = dim[_aend] - dim[_acenter] # same as dim[_yend] - dim[_ycenter]

    aligned_faces_start = tree_image.radius[0]

    pos2colfaces = {}
    poscol2width = {}
    poscol2height = {}
    # sort faces at each pos by column
    for face, pos, row, col, fw, fh in facegrid:
        if not dim[_is_leaf] and face.only_if_leaf and not is_collapsed:
            continue
        pos2colfaces.setdefault(pos, {}).setdefault(col, []).append([face, fw, fh])
        poscol2width[pos, col] = max(fw, poscol2width.get((pos, col), 0))
        poscol2height[pos, col] = poscol2height.get((pos, col), 0) + fh

    for pos, colfaces in pos2colfaces.iteritems():
        if pos == 0 or pos == 1: #btop or bbottom
            available_pos_width = max(dim[_btw], dim[_blen]) * zoom_factor
            start_x = x
        elif pos == 1:
            available_pos_width = max(dim[_bbw], dim[_blen]) * zoom_factor
            start_x = x
        elif pos == 2: # bright
            available_pos_width = dim[_brw] * zoom_factor
            start_x = x + max(dim[_btw], dim[_bbw], dim[_blen])
        elif pos == 3: # float
           pass
        elif pos == 4: # aligned
            available_pos_width = (tree_image.radius[-1] - tree_image.radius[0]) * zoom_factor
            start_x = aligned_faces_start
        else:
            continue

        start_x *= zoom_factor

        for col, faces in colfaces.iteritems():
            if available_pos_width <= 0:
                continue

            if pos == 0:
                aperture = get_aperture(start_x, a_top, 9999999999) if mode == 'c' else a_top
            elif pos == 1:
                aperture = get_aperture(start_x, a_bot, 9999999999) if mode == 'c' else a_bot
            elif pos == 2:
                if mode == 'c':
                    aperture = min(get_aperture(start_x, a_top, 99999999999) * 2,
                                   get_aperture(start_x, a_bot, 99999999999) * 2)
                else:
                    aperture = min(a_top * 2, a_bot * 2)

            elif pos == 3: # float
                continue
            elif pos == 4: # aligned
                continue
            else:
                raise ValueError("not supported face position")

            y_face_zoom_factor = aperture / poscol2height[pos, col] if poscol2height[pos, col] else 0.0
            x_face_zoom_factor = available_pos_width / poscol2width[pos, col] if poscol2width[pos, col] else 0.0
            face_zoom_factor = max(zoom_factor, min(3, x_face_zoom_factor/2, y_face_zoom_factor/2))

            drawing_w = poscol2width[pos, col] * face_zoom_factor
            drawing_h = poscol2height[pos, col] * face_zoom_factor
            available_pos_width -= drawing_w

            if drawing_w < 1 and drawing_h < 1:
                continue

            if pos == 0:
                start_y = y - drawing_h
            elif pos == 1:
                start_y = y
            elif pos == 2 or pos == 4:
                start_y = y - drawing_h / 2.0
            elif pos == 3:
                pass

            pp.save()
            pp.setOpacity(face.opacity)
            pp.translate(start_x, start_y)
            pp.scale(face_zoom_factor, face_zoom_factor)

            draw_face_column(faces, 0.0, 0.0, start_x, face_zoom_factor)
            pp.restore()

            # continue with next column
            start_x += drawing_w


def get_cart_coords(radius, radians, cx, cy):
    a = (2*math.pi)-radians;
    x = math.cos(a) * radius
    y = math.sin(a) * radius
    return x+cx, -y+cy


def get_aperture(radius, angle, default):
    if angle > R90:
        return default
    else:
        return math.tan(angle) * radius
