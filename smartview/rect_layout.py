from .common import *
from .utils import timeit, debug
from .painter import SmartPainter, QETEPainter

from PyQt4 import QtCore
from PyQt4.QtGui import *
from PyQt4.QtCore import *


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

        # calculate node width, could this be cached so is not recalculate in
        # post and pre order?
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

from PyQt4 import QtGui

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


def doRectsOverlap(rect1, rect2):
    for a, b in [(rect1, rect2), (rect2, rect1)]:
        # Check if a's corners are inside b
        if ((isPointInsideRect(a.left, a.top, b)) or
            (isPointInsideRect(a.left, a.bottom, b)) or
            (isPointInsideRect(a.right, a.top, b)) or
            (isPointInsideRect(a.right, a.bottom, b))):
            return True
    return False

def isPointInsideRect(x, y, rect):
    if (x > rect.left) and (x < rect.right) and (y > rect.top) and (y < rect.bottom):
        return True
    else:
        return False

@timeit
def draw_region_rect(tree_image, region, zoom_factor):
    COLLAPSE_RESOLUTION = 1
    # DEBUG INFO
    DRAWN, SKIPPED, TOO_SMALL, COLLAPSED, MULTI, ITERS = 0, 0, 0, 0, 0, 0
    coll_paths = tree_image.rect_collision_paths
    img_data = tree_image.img_data

    ii = QImage(region[2], region[3], QImage.Format_RGB32)
    ii.fill(QColor("white"))
    pp = SmartPainter()
    pp2 = QETEPainter(ii)

    scene_rect = QRectF(*region)
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
        #print dim[_fnh], dim[_fnw]
        if (dim[_fnh] * zoom_factor) < 1:
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
        if draw_collapsed:
            pp.draw_line(parent_radius, dim[_ycenter],
                         parent_radius+branch_length, dim[_ycenter])
            pp2.draw_line(parent_radius, dim[_ycenter],
                         parent_radius+branch_length, dim[_ycenter])

        else:
            if not dim[_is_leaf] and len(node.children) > 1:
                acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
                acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]
                pp.draw_line(parent_radius+branch_length, acen_0,
                             parent_radius+branch_length, acen_1)
                pp2.draw_line(parent_radius+branch_length, acen_0,
                             parent_radius+branch_length, acen_1)

            pp.draw_line(parent_radius, dim[_ycenter],
                         parent_radius+branch_length, dim[_ycenter])

            pp2.draw_line(parent_radius, dim[_ycenter],
                         parent_radius+branch_length, dim[_ycenter])



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



    print "NODES DRAWN", DRAWN, 'skipped', SKIPPED, 'too_small', TOO_SMALL, "collapsed", COLLAPSED, "iters", ITERS, "MULTI", MULTI
    pp2.p.end()
    ii.save("/Users/jhc/test.png")
    return pp.lines
