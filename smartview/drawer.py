import math
import time

from ctypes import *
from numpy.ctypeslib import ndpointer
import numpy as np

from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *

from .common import *
from .utils import timeit, debug
from . import layout

COLLAPSE_RESOLUTION = 25

def get_node_paths(tree_image, nid):
    dim = tree_image.img_data[nid]
    node = tree_image.cached_preorder[nid]
    radius = dim[_rad]
    parent_radius = tree_image.img_data[int(dim[_parent])][_rad]
    if not dim[_is_leaf]:
        angles = (tree_image.img_data[node.children[0]._id][_astart],
                  tree_image.img_data[node.children[-1]._id][_aend])
    else:
        angles = (dim[_astart], dim[_aend])

    path = get_arc_path(parent_radius, radius, angles)
    full_path = get_arc_path(parent_radius, dim[_fnw], angles)

    return path, full_path

def get_qt_corrected_angle(rad, angle):
    path = QPainterPath()
    inner_diam = rad * 2.0
    rect1 = QRectF(-rad, -rad, inner_diam, inner_diam)
    path.arcMoveTo(rect1, -np.degrees(angle))
    i1 = path.currentPosition()
    new_angle = np.arctan2(i1.y(), i1.x())
    new_rad = np.hypot(i1.y(), i1.x())
    return new_rad, new_angle

def get_arc_path(inner_r, outter_r, rad_angles):
    angles = map(np.degrees, rad_angles)
    path = QPainterPath()
    inner_diam = inner_r * 2.0
    rect1 = QRectF(-inner_r, -inner_r, inner_diam, inner_diam)
    # draw a horizontal line
    if len(angles) == 1:
        outter_diam = outter_r * 2.0
        rect2 = QRectF(-outter_r, -outter_r, outter_diam, outter_diam)

        path.arcMoveTo(rect1, -angles[0])
        i1 = path.currentPosition()
        path.arcMoveTo(rect2, -angles[0])
        path.lineTo(i1)
    # draw a vertical line
    elif inner_r == outter_r:
        span = angles[-1] - angles[0]
        path.arcMoveTo(-inner_r, -inner_r, inner_diam, inner_diam, -angles[0])
        if span < 0.1: # solves precision problems drawing small arcs
            i1 = path.currentPosition()
            path.arcMoveTo(-inner_r, -inner_r, inner_diam, inner_diam, -angles[-1])
            path.lineTo(i1)
        else:
            path.arcTo(-inner_r, -inner_r, inner_diam, inner_diam,
                   -angles[0], -span)
    # draw arc
    else:
        outter_diam = outter_r * 2.0
        rect2 = QRectF(-outter_r, -outter_r, outter_diam, outter_diam)

        span = angles[-1] - angles[0]
        if span < 0.1: # solves precision problems drawing small arcs
            path.arcMoveTo(rect1, -angles[0])
            i1 = path.currentPosition()
            path.arcMoveTo(rect1, -angles[-1])
            i2 = path.currentPosition()
            path.arcMoveTo(rect2, -angles[0])
            o1 = path.currentPosition()
            path.arcMoveTo(rect2, -angles[-1])
            o2 = path.currentPosition()

            path.moveTo(i1)
            path.lineTo(i2)
            path.lineTo(o2)
            path.lineTo(o1)
            path.closeSubpath()

        else:
            path.arcMoveTo(rect1, -angles[0])
            i1 = path.currentPosition()

            path.arcMoveTo(rect2, -angles[-1])
            o2 = path.currentPosition()

            path.moveTo(i1)

            path.arcTo(rect1, -angles[0], -span)
            path.lineTo(o2)
            path.arcTo(rect2, -angles[-1], span)
            path.closeSubpath()

    return path


def get_tile_img(tree_image, zoom_factor, treemode, tile_rect):
    # Create an empty tile image
    source_rect = QRectF(*tile_rect)
    target_rect = QRectF(0, 0, source_rect.width(), source_rect.height())
    ii= QImage(source_rect.width(), source_rect.height(),
               QImage.Format_ARGB32_Premultiplied)
    ii.fill(QColor(Qt.white).rgb())

    pp = QPainter()
    pp.begin(ii)

    pp.setRenderHint(QPainter.Antialiasing)
    pp.setRenderHint(QPainter.TextAntialiasing)
    pp.setRenderHint(QPainter.SmoothPixmapTransform)

    # Prevent drawing outside target_rect boundaries
    pp.setClipRect(target_rect, Qt.IntersectClip)

    # Transform space of coordinates: I want source_rect.top_left() to be
    # translated as 0,0
    matrix = QTransform().translate(-source_rect.left(), -source_rect.top())
    pp.setWorldTransform(matrix, True)
    # Paint on tile
    if treemode == "c":
        draw_region_circ(tree_image, pp, zoom_factor, source_rect)
    elif treemode == "r":
        draw_region_rect(tree_image, pp, source_rect)
    pp.end()
    return ii

@timeit
def draw_region_circ(tree_image, pp, zoom_factor, scene_rect):
    arc_paths = tree_image.circ_collistion_paths
    img_data = tree_image.img_data
    cx = tree_image.radius[0]
    cy = cx

    m = QTransform()
    m.translate(-cx, -cy)
    m.scale(1/zoom_factor, 1/zoom_factor)
    m_scene_rect = m.mapRect(scene_rect)

    M = QTransform()
    M.scale(zoom_factor, zoom_factor)
    M.translate(cx, cy)

    #aligned_circ_diam = tree_image.radius[0] * zoom_factor * 2
    #c1 = (tree_image.radius[-1] -  tree_image.radius[-0]) * zoom_factor
    #pp.drawEllipse(c1, c1, aligned_circ_diam, aligned_circ_diam)

    # DEBUG INFO
    DRAWN, OUTSIDE, TOO_SMALL, COLLAPSED, MULTI, ITERS = 0, 0, 0, 0, 0, 0

    curr = 0
    nid = curr
    end = img_data[curr][_max_leaf_idx] + 1
    max_observed_radius = 0
    visible_leaves = []
    while curr < end:
        ITERS += 1
        draw_collapsed = False
        nid = curr
        node = tree_image.cached_preorder[nid]
        dim = img_data[nid]
        #path = M.map(arc_paths[nid][0])
        #fpath = M.map(arc_paths[nid][1])

        #path = arc_paths[nid][0]
        #fpath = arc_paths[nid][1]

        if dim[_fnh] >= R180:
            node_height = 999999999
        else:
            node_height = ((math.sin(dim[_fnh]/2.0) * dim[_fnw]) * 2) * zoom_factor

        # if node looks smaller than a pixel
        if node_height < 3:
            curr = int(dim[_max_leaf_idx] + 1)
            TOO_SMALL += 1
            continue
        # if descendants are too small, draw the whole partition as a single
        # simplified item
        elif not dim[_is_leaf] and (node_height < COLLAPSE_RESOLUTION or node_height/len(node.children) < 3):
            curr = int(dim[_max_leaf_idx] + 1)
            draw_collapsed = True
            COLLAPSED += 1
        else:
            curr += 1

        if 1  and arc_paths[nid][0] is None:
            path, fpath = get_node_paths(tree_image, nid)
            arc_paths[nid] = [path, fpath]
        else:
            path, fpath = arc_paths[nid]

        # skip if node does not overlap with requested region
        if not path.intersects(m_scene_rect):
            # and skip all descendants in case none fits in region
            if not fpath.intersects(m_scene_rect):
                new_curr = max(int(dim[_max_leaf_idx]+1), curr)
                OUTSIDE += new_curr - curr
                curr = new_curr
            continue

        scene_rect_path = QPainterPath()
        scene_rect_path.addRect(m_scene_rect)
        
        
        if (draw_collapsed or dim[_is_leaf]) and scene_rect_path.contains(fpath):
            visible_leaves.append(node)
            is_terminal = True
            scaled_path = M.map(fpath)
            endx = fpath.boundingRect().width()
        else:
            endx = 0
            is_terminal = False
    
        
        # Draw the node
        DRAWN += 1

        if not node._temp_faces:
            node._temp_faces = None
            for func in tree_image.tree_style.layout_fn:
                func(node)

        pp.save()

        if draw_collapsed:
            branch_length = dim[_blen] * tree_image.scale
            pp.setPen(QPen(QColor("#AAAAAA")))
            parent_radius = img_data[int(dim[_parent])][_rad] if nid else tree_image.root_open
            pp.drawPath(M.map(fpath))
        else:
            pp.setPen(QPen(QColor("black")))
            node = tree_image.cached_preorder[nid]
            parent_radius = img_data[int(dim[_parent])][_rad] if nid else tree_image.root_open

            # if dim[_is_leaf]:
            #     pp.setPen(QColor("green"))
            #     pp.setBrush(QColor("indianred"))
            #     bkg_arc = get_arc_path(parent_radius, tree_image.radius[0], [dim[_astart], dim[_aend]])
            #     pp.drawPath(M.map(bkg_arc))
            #     pp.setBrush(Qt.NoBrush)

            # Draw arc line connecting children
            if not dim[_is_leaf] and len(node.children) > 1:
                acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
                acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]
                pp.setPen(QColor(node.img_style.vt_line_color))
                vLinePath = get_arc_path(dim[_rad], dim[_rad], [acen_0, acen_1])
                pp.drawPath(M.map(vLinePath))

            branch_length = dim[_blen] * tree_image.scale
            #linew = max(branch_length, dim[_btw], dim[_bbw])
            linew = branch_length
            hLinePath = get_arc_path(parent_radius, parent_radius+linew, [dim[_acenter]])
            pp.setPen(QColor(node.img_style.hz_line_color))
            pp.drawPath(M.map(hLinePath))

            pp.setPen(QColor("black"))

        new_rad, new_angle = get_qt_corrected_angle(parent_radius, dim[_acenter])
        pp.translate(cx*zoom_factor, cy*zoom_factor)
        pp.rotate(np.degrees(new_angle))

        # if node was not visited yet, compute face dimensions
        if not np.any(dim[_btw:_bah+1]):
            face_pos_sizes = layout.compute_face_dimensions(node, node._temp_faces)
            dim[_btw:_bah+1] = face_pos_sizes

        end_faces = draw_faces(pp, new_rad, 0, node, zoom_factor, tree_image,
                          is_collapsed=False, target_positions = set([0, 1, 2, 3]))
        if is_terminal: 
            endx += end_faces
            max_observed_radius = max(max_observed_radius, endx)
        
        pp.restore()
        # Draw overlay labels
        label_rect = path.boundingRect()
        if dim[_fnh] *zoom_factor > 60 and (dim[_rad]-parent_radius) > 100:
            pp.save()
            pp.setPen(QColor("white"))
            pp.setBrush(QColor("royalBlue"))
            qfont = QFont("Verdana",pointSize=16)
            qfont.setWeight(QFont.Black)
            fm = QFontMetrics(qfont)
            text_w = fm.width(node.name)
            pp.setFont(qfont)
            pp.setOpacity(0.8)
            new_rad, new_angle = get_qt_corrected_angle(parent_radius, dim[_acenter])
            node_x, node_y = get_cart_coords((new_rad*zoom_factor), new_angle, cx*zoom_factor, cy*zoom_factor)
            if dim[_acenter] <R90 or dim[_acenter] >R270:
                node_x -= text_w

            text_path = QPainterPath()
            text_path.addText(node_x, node_y, qfont, node.name)
            #pp.drawText(node_x, node_y, node.name)
            pp.drawPath(text_path)
            pp.restore()


    for node in visible_leaves:
        pp.save()
        dim = tree_image.img_data[node._id]
        new_rad, new_angle = get_qt_corrected_angle(max_observed_radius, dim[_acenter])
        pp.translate(cx*zoom_factor, cy*zoom_factor)
        pp.rotate(np.degrees(new_angle))
        endx = draw_faces(pp, new_rad , 0, node, 1,
                          tree_image, is_collapsed=False, target_positions = [4])
        pp.restore()
    pp.scale(zoom_factor, zoom_factor)
    for path in tree_image.link_paths:
        pp.setOpacity(0.5)
        pp.fillPath(path, QColor("green"))

    debug("NODES DRAWN", DRAWN, 'OutsideRegion', OUTSIDE, 'too_small', TOO_SMALL, "collapsed", COLLAPSED, "iters", ITERS, "MULTI", MULTI)




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

def draw_faces(pp, x, y, node, zoom_factor, tree_image, is_collapsed,
               target_positions=None):
    
    dim = tree_image.img_data[node._id]
    branch_length = dim[_blen]
    facegrid = node._temp_faces
    if not facegrid:
        return

    correct_rotation = True if tree_image.tree_style.mode == 'c' and \
                       dim[_acenter] > R90 and dim[_acenter] < R270 \
                       else False

    # Apertures top-branch and bottom-branch
    a_top = dim[_acenter] - dim[_astart]
    a_bot = dim[_aend] - dim[_acenter]

    def draw_face_column(faces, _x, _y, _rad, _face_zoom_factor):
        for _f, fw, fh in faces:
            if not dim[_is_leaf] and _f.only_if_leaf and not is_collapsed:
                continue
            restore_rot_painter = False
            _f.node = node
            _f.arc_start = dim[_astart]
            _f.arc_end = dim[_aend]
            _f.img_rad = _rad

            _f._pre_draw()


            if correct_rotation and _f.rotable:
                restore_rot_painter = True
                pp.save()
                zoom_half_fw = ((fw * _face_zoom_factor)/2)
                zoom_half_fh = ((fh * _face_zoom_factor)/2)
                pp.translate(zoom_half_fw, zoom_half_fh)
                pp.rotate(180)
                pp.translate(-(zoom_half_fw), -(zoom_half_fh))

            # Draw face
            _f._draw(pp, _x, _y, _face_zoom_factor)

            # # Draw face border (DEBUG)
            if 0:
                pp.save()
                pp.setPen(QPen(QColor('orange'), ))
                pp.scale(_face_zoom_factor, _face_zoom_factor)
                pp.drawRect(_x, _y, fw, fh)
                pp.restore()


            if restore_rot_painter:
                pp.restore()
                _y -= fh
            else:
                _y += fh
        

    # calculate width and height of each facegrid column
    pos2colfaces = {}
    poscol2width = {}
    poscol2height = {}
    for face, pos, row, col, fw, fh in facegrid:
        if target_positions is not None and pos not in target_positions:
            continue

        if not dim[_is_leaf] and face.only_if_leaf and not is_collapsed:
            continue
        
        pos2colfaces.setdefault(pos, {}).setdefault(col, []).append([face, fw, fh])
        poscol2width[pos, col] = max(fw, poscol2width.get((pos, col), 0))
        poscol2height[pos, col] = poscol2height.get((pos, col), 0) + fh

    endx = 0
    for pos, colfaces in pos2colfaces.iteritems():
        if pos == 0:
            facegrid_width = dim[_btw]
            facegrid_height = dim[_bth]
            #available_pos_width = max(dim[_btw], branch_length) * zoom_factor
            available_pos_width = branch_length * zoom_factor
            start_x = x
        elif pos == 1: #bbottom
            facegrid_width = dim[_bbw]
            facegrid_height = dim[_bbh]
            #available_pos_width = max(dim[_bbw], branch_length) * zoom_factor
            available_pos_width = branch_length * zoom_factor
            start_x = x
        elif pos == 2: #bright
            facegrid_width = dim[_brw]
            facegrid_height = dim[_brh]
            available_pos_width = dim[_brw] * zoom_factor
            start_x = x + branch_length

        elif pos == 3: #float
           pass
        elif pos == 4: #aligned
            facegrid_width = dim[_baw]
            facegrid_height = dim[_bah]
            available_pos_width = 99999999999 * zoom_factor
            start_x = x
        else:
            continue


        start_x *= zoom_factor
        endx = max(start_x, endx)
        
        # Calculate available angle aperture to draw face
        if pos == 0:
            aperture = get_aperture(start_x, a_top, 9999999999)
        elif pos == 1:
            aperture = get_aperture(start_x, a_bot, 9999999999)
        elif pos == 2:
            aperture = min(get_aperture(start_x, a_top, 99999999999) * 2,
                               get_aperture(start_x, a_bot, 99999999999) * 2)
        elif pos == 3:
            pass
        elif pos == 4:
            aperture = min(get_aperture(start_x, a_top, 99999999999) * 2,
                               get_aperture(start_x, a_bot, 99999999999) * 2)
        else:
            raise ValueError("not supported face position")

        # skip if there is not enough height
        if aperture < 1:
            continue

        # skip if there is not enough width
        if available_pos_width < 1:
            continue
        # Faces are scaled based on available space given current zoom factor
        y_face_zoom_factor = aperture / facegrid_height
        x_face_zoom_factor = available_pos_width / facegrid_width

        face_zoom_factor = min(x_face_zoom_factor, y_face_zoom_factor, 1.0)

        for col, faces in colfaces.iteritems():
            if pos == 0:
                start_y = y - (poscol2height[pos, col]) 
            elif pos == 1:
                start_y = y
            elif pos == 2 or pos == 4:
                start_y = y - (poscol2height[pos, col]/2.0)
            elif pos == 3:
                pass
            endx = max(endx, endx + (poscol2width[pos, col] * face_zoom_factor))
            if zoom_factor > 0:
                pp.save()
                pp.setOpacity(face.opacity)
                pp.translate(start_x, start_y * face_zoom_factor)
                draw_face_column(faces, 0.0, 0.0, start_x, face_zoom_factor)
                pp.restore()

            # continue with next column
            start_x += poscol2width[pos, col] * face_zoom_factor

    return endx
