from . import layout
from .common import *
import math
import time
from collections import defaultdict

from ctypes import *
from numpy.ctypeslib import ndpointer
import numpy as np

from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtSvg import *

import logging
logger = logging.getLogger("smartview")


COLLAPSE_RESOLUTION = 5
W_COLLAPSE_RESOLUTION = 5
MAX_SCREEN_SIZE = 4000


def get_aperture(radius, angle, default):
    if angle > R90:
        return default
    else:
        return math.tan(angle) * radius


def get_node_arc_path(tree_image, nid):
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


def get_node_rect_path(tree_image, nid):
    dim = tree_image.img_data[nid]
    node = tree_image.cached_preorder[nid]

    ystart = dim[_ystart]
    yend = dim[_yend]
    xend = dim[_xend]
    xstart = tree_image.img_data[int(dim[_parent])][_xend]
    path = QPainterPath()
    fpath = QPainterPath()
    path.addRect(xstart, ystart, xend-xstart, yend-ystart)
    fpath.addRect(xstart, ystart, dim[_fnw], dim[_fnh])
    return path, fpath


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
    angles = list(map(np.degrees, rad_angles))
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
        if span < 0.1:  # solves precision problems drawing small arcs
            i1 = path.currentPosition()
            path.arcMoveTo(-inner_r, -inner_r, inner_diam,
                           inner_diam, -angles[-1])
            path.lineTo(i1)
        else:
            path.arcTo(-inner_r, -inner_r, inner_diam, inner_diam,
                       -angles[0], -span)
    # draw arc
    else:
        outter_diam = outter_r * 2.0
        rect2 = QRectF(-outter_r, -outter_r, outter_diam, outter_diam)

        span = angles[-1] - angles[0]
        if span < 0.1:  # solves precision problems drawing small arcs
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


def draw_tree_scene_region(pp, painter, tree_image, zoom_factor, scene_rect):
    """ Draws a region of the scene.

        scene_rect represents the target rectangle in the transformed scene
        (zoomed and translated) that needs to be drawn.

        """

    img_data = tree_image.img_data
    treemode = tree_image.tree_style.mode
    if treemode == 'c':
        collision_paths = tree_image.circ_collision_paths
        cx = tree_image.radius[0]
        cy = cx

        # untransformed scene rect used to calculate overlaps with original node
        # positions and sizes
        m = QTransform()
        m.translate(-cx, -cy)
        m.scale(1/zoom_factor, 1/zoom_factor)
        m_scene_rect = m.mapRect(scene_rect)

        # transformed scene matrix used to map original node elements into
        # target scence rect
        M = QTransform()
        M.scale(zoom_factor, zoom_factor)
        M.translate(cx, cy)

    elif treemode == 'r':
        collision_paths = tree_image.rect_collision_paths

        # untransformed scene rect used to calculate overlaps with original node
        # positions and sizes
        m = QTransform()
        m.scale(1/zoom_factor, 1/zoom_factor)
        m_scene_rect = m.mapRect(scene_rect)

        # transformed scene matrix used to map original node elements into
        # target scence rect
        M = QTransform()
        M.scale(zoom_factor, zoom_factor)

    pp.drawRect(scene_rect)

    pp.save()
    # Lets draw tree scene
    pp.setClipRect(scene_rect)

    # DEBUG INFO
    DRAWN, OUTSIDE, COLLAPSED, ITERS = 0, 0, 0, 0

    curr = 0
    nid = curr
    end = img_data[curr][_max_leaf_idx] + 1
    max_observed_radius = 0
    visible_leaves = []
    terminal_nodes = []
    visible_labels = []
    start_x_aligned_faces = 0
    farthest_fpath = None
    while curr < end:
        ITERS += 1
        draw_collapsed = False
        nid = curr
        node = tree_image.cached_preorder[nid]
        dim = img_data[nid]
        nsize = nid - tree_image.img_data[nid][_max_leaf_idx]+1
        branch_length = dim[_blen]

        # Compute node and full paths for the node
        if collision_paths[nid][0] is None:
            if treemode == "c":
                path, fpath = get_node_arc_path(tree_image, nid)
            elif treemode == "r":
                path, fpath = get_node_rect_path(tree_image, nid)
            collision_paths[nid] = [path, fpath]
        else:
            path, fpath = collision_paths[nid]

        not_visible = False
        brect = fpath.boundingRect()
        top_left = brect.topLeft()
        y_range = QRectF(m_scene_rect.x()+1, top_left.y(),
                         brect.width(), brect.height())
        if not m_scene_rect.intersects(y_range):
            # if the node is outside the vertical range, skip it (no draw no
            # visiable terminal nodes)
            new_curr = max(int(dim[_max_leaf_idx]+1), curr)
            OUTSIDE += 1
            curr = new_curr
            y_range = QRectF(m_scene_rect.x()+1, top_left.y(),
                             brect.width(), brect.height())
            continue
        elif not fpath.intersects(m_scene_rect):
            # if in the y range, but not in the x range. Don't draw it, but
            # keeps the iteration to find terminal nodes.
            not_visible = True

        # Calculate how much space is there at this zoom for drawing the node
        if treemode == 'c' and dim[_fnh] >= R180:
            node_height = MAX_SCREEN_SIZE
            node_height_up = MAX_SCREEN_SIZE
            node_height_down = MAX_SCREEN_SIZE
        elif treemode == 'c':
            node_height = (
                (math.sin(dim[_fnh]/2.0) * dim[_fnw]) * 2) * zoom_factor
            node_height_up = (
                (math.sin(dim[_acenter]-dim[_astart]) * dim[_fnw])) * zoom_factor
            node_height_down = (
                (math.sin(dim[_aend]-dim[_acenter]) * dim[_fnw])) * zoom_factor
        elif treemode == 'r':
            node_height = brect.height() * zoom_factor
            node_width = brect.width() * zoom_factor
            node_height_up = node_height / 2.0
            node_height_down = node_height / 2.0

        if dim[_is_leaf]:
            curr += 1
            is_terminal = True
        elif (node_height_up < COLLAPSE_RESOLUTION) \
                or node_height_down < COLLAPSE_RESOLUTION \
                or node_width < W_COLLAPSE_RESOLUTION \
                or node_height/(len(node.children)+1) < 3:
            # If this is an internal node which is being drawn very samll, draw
            # it as a collapsed terminal, and skip the subtree down.
            curr = int(dim[_max_leaf_idx] + 1)
            draw_collapsed = True
            is_terminal = True
            COLLAPSED += 1
        else:
            curr += 1
            is_terminal = False

        if is_terminal:
            terminal_nodes.append(node)

        if not_visible:
            continue

        # If it gets to here, draw the node
        pp.save()
        DRAWN += 1

        # Load faces and styles for the node by applying user's layout function
        if not node._temp_faces:
            node._temp_faces = None
            for func in tree_image.tree_style.layout_fn:
                func(node)

            # if node was not visited yet, compute face dimensions
            if not np.any(dim[_btw:_bah+1]):
                face_pos_sizes = layout.compute_face_dimensions(
                    node, node._temp_faces)
                dim[_btw:_bah+1] = face_pos_sizes

        if draw_collapsed:
            # pp.setPen(QPen(QColor("LightSteelBlue")))
            # pp.drawPath(M.map(fpath)) # TODO: Draw triangle or similar in rect mode
            r = M.mapRect(fpath.boundingRect())
            painter.drawRect(r.x(), r.y(), r.width(),
                             r.height(), "LightSteelBlue", None)

        else:
            if treemode == "c":
                parent_radius = img_data[int(
                    dim[_parent])][_rad] if nid else tree_image.root_open

                # Draw arc line connecting children
                if not dim[_is_leaf] and len(node.children) > 1:
                    acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
                    acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]
                    pp.setPen(QColor(node.img_style.vt_line_color))
                    vLinePath = get_arc_path(
                        dim[_rad], dim[_rad], [acen_0, acen_1])
                    pp.drawPath(M.map(vLinePath))

                hLinePath = get_arc_path(
                    parent_radius, parent_radius+branch_length, [dim[_acenter]])
                pp.setPen(QColor(node.img_style.hz_line_color))
                pp.drawPath(M.map(hLinePath))

                new_rad, new_angle = get_qt_corrected_angle(
                    parent_radius, dim[_acenter])
                pp.translate(cx * zoom_factor, cy * zoom_factor)
                pp.rotate(np.degrees(new_angle))
                #pp.translate(new_rad * zoom_factor, 0)
                # endx = draw_faces(pp, new_rad * zoom_factor, 0, node, zoom_factor, tree_image,
                #                   is_collapsed=False, target_positions=set([0, 1, 2, 3]))

            elif treemode == "r":
                parent_radius = img_data[int(
                    dim[_parent])][_xend] if nid else tree_image.root_open
                new_rad = parent_radius
                # Draw vertical line connecting children
                if not dim[_is_leaf] and len(node.children) > 1:
                    acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
                    acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]
                    # pp.setPen(QColor(node.img_style.vt_line_color))
                    # pp.drawLine(M.map(QLineF(parent_radius+branch_length, acen_0,
                    #                          parent_radius+branch_length, acen_1)))
                    vline = M.map(QLineF(parent_radius+branch_length, acen_0,
                                         parent_radius+branch_length, acen_1))

                    painter.drawLine(vline.x1(), vline.y1(),
                                     vline.x2(), vline.y2(), "black")

                # pp.setPen(QColor(node.img_style.hz_line_color))
                # pp.drawLine(M.map(QLineF(parent_radius, dim[_acenter],
                #                          parent_radius+branch_length, dim[_acenter])))
                hline = M.map(QLineF(parent_radius, dim[_acenter],
                                     parent_radius+branch_length, dim[_acenter]))
                painter.drawLine(hline.x1(), hline.y1(),
                                 hline.x2(), hline.y2(), "black")

                pp.translate(parent_radius*zoom_factor,
                             dim[_ycenter]*zoom_factor)

                endx = draw_faces(pp, painter, 0, 0, node, zoom_factor, tree_image,
                                  is_collapsed=False, target_positions=set([0, 1, 2, 3]))
        pp.restore()

    pp.restore()
    return terminal_nodes


def get_face_dimensions(node, facegrid, target_pos=None):
    """ Given a list of faces, calculate the size of each faceposition and column """

    if facegrid is None:
        facegrid = []

    def listdict(): return defaultdict(list)
    poscol2w = defaultdict(listdict)
    poscol2h = defaultdict(listdict)
    poscol2faces = defaultdict(listdict)

    for index, (f, pos, row, col, _, _) in enumerate(facegrid):
        f.node = node
        fw, fh = f._size()
        fw += f.margin_right + f.margin_left
        fh += f.margin_top + f.margin_bottom

        # correct dimensions in case face is rotated
        if f.rotation:
            if f.rotation == 90 or f.rotation == 270:
                fw, fh = fh, fw
            elif f.rotation == 180:
                pass
            else:
                x0 = fw / 2.0
                y0 = fh / 2.0
                theta = (f.rotation * math.pi) / 180
                def trans(x, y): return (x0+(x-x0) * math.cos(theta) + (y-y0) * math.sin(theta),
                                         y0-(x-x0) * math.sin(theta) + (y-y0) * math.cos(theta))
                coords = (trans(0, 0), trans(0, fh),
                          trans(fw, 0), trans(fw, fh))
                x_coords = [e[0] for e in coords]
                y_coords = [e[1] for e in coords]
                fw = max(x_coords) - min(x_coords)
                fh = max(y_coords) - min(y_coords)

        # Update overal grid data
        poscol2w[pos][col].append(fw)
        poscol2h[pos][col].append(fh)
        poscol2faces[pos][col].append([f, fw, fh])

    # Calculate total facegrid size
    pos2dim = {}
    for fpos in FACE_POS_INDEXES:
        total_w = sum([max(v) for v in list(poscol2w[fpos].values())]
                      ) if fpos in poscol2w else 0.0
        total_h = max([sum(v) for v in list(poscol2h[fpos].values())]
                      ) if fpos in poscol2h else 0.0
        pos2dim[fpos] = (total_w, total_h)

    return pos2dim, poscol2w, poscol2h, poscol2faces


def draw_aligned_panel_region(pp, terminal_nodes, tree_image, zoom_factor, scene_rect):
    # pp.setClipRect(scene_rect)
    img_data = tree_image.img_data
    treemode = tree_image.tree_style.mode

    for node in terminal_nodes:
        dim = tree_image.img_data[node._id]
        avail_h = dim[_fnh] * zoom_factor
        avail_w = MAX_SCREEN_SIZE

        if node._temp_faces is None:
            for func in tree_image.tree_style.layout_fn:
                func(node)
            # if node was not visited yet, compute face dimensions
            if not np.any(dim[_btw:_bah+1]):
                face_pos_sizes = layout.compute_face_dimensions(
                    node, node._temp_faces)
                dim[_btw:_bah+1] = face_pos_sizes

        # if node was not visited yet, compute face dimensions
        pos2dim, poscol2w, poscol2h, poscol2faces = get_face_dimensions(
            node, node._temp_faces)

        pp.save()
        if treemode == "c":
            #new_rad, new_angle = get_qt_corrected_angle(start_x_aligned_faces, dim[_acenter])
            #pp.translate(cx*zoom_factor, cy*zoom_factor)
            # pp.rotate(np.degrees(new_angle))
            # pp.rotate(np.degrees(dim[_acenter]))
            # endx = draw_faces(pp, start_x_aligned_faces, 0, node, zoom_factor,
            #
            pass
        elif treemode == "r":
            pp.translate(0, dim[_ycenter]*zoom_factor)
            for col, colfaces in poscol2faces[4].items():
                col_w = max(poscol2w[4][col])
                col_h = sum(poscol2h[4][col])
                draw_face_column(pp, node, colfaces, col_w,
                                 col_h, avail_w, avail_h)
        pp.restore()


def draw_face_column(pp, node, colfaces, col_w, col_h, avail_w, avail_h):
    pp.save()
    xpos = 0
    ypos = 0 - (avail_h/2)
    pp.translate(0, -avail_h/2)
    xmax = 0

    for face, fw, fh in colfaces:
        percent_height = fh / col_h

        avail_face_h = avail_h * percent_height
        face_face_w = avail_w

        if xpos > avail_w or ypos > avail_h:
            break

        face._draw(pp, node, avail_w=avail_w, avail_h=avail_face_h)
        ypos += avail_face_h
        pp.translate(0, avail_face_h)
    pp.restore()


def draw_faces(pp, painter, x, y, node, zoom_factor, tree_image, is_collapsed,
               target_positions=None, target_rect=None):

    dim = tree_image.img_data[node._id]
    branch_length = dim[_blen]
    facegrid = node._temp_faces
    tree_mode = tree_image.tree_style.mode
    if not facegrid:
        return

    correct_rotation = True if (
        tree_mode == 'c' and dim[_acenter] > R90 and dim[_acenter] < R270) else False

    # Apertures top-branch and bottom-branch
    a_top = dim[_acenter] - dim[_astart]
    a_bot = dim[_aend] - dim[_acenter]

    # end position hit by these faces
    endx = 0

    # Calculates basic info on how to start drawing each facegrid position block
    pos2params = {}
    for pos in range(5):
        if pos == 0:  # btop
            facegrid_width = dim[_btw]
            facegrid_height = dim[_bth]
            available_pos_width = branch_length * zoom_factor
            start_x = x  # IDEA: align to right
            if tree_mode == 'c':
                available_pos_height = get_aperture(
                    start_x, a_top, MAX_SCREEN_SIZE)
            elif tree_mode == 'r':
                available_pos_height = a_top * zoom_factor

        elif pos == 1:  # bbottom
            facegrid_width = dim[_bbw]
            facegrid_height = dim[_bbh]
            available_pos_width = branch_length * zoom_factor
            start_x = x  # IDEA: align to right
            if tree_mode == 'c':
                available_pos_height = get_aperture(
                    start_x, a_bot, MAX_SCREEN_SIZE)
            elif tree_mode == 'r':
                available_pos_height = a_bot * zoom_factor

        elif pos == 2:  # branch right
            facegrid_width = dim[_brw]
            facegrid_height = dim[_brh]
            available_pos_width = dim[_brw] * zoom_factor
            start_x = x + (branch_length * zoom_factor)
            if tree_mode == 'c':
                available_pos_height = min(get_aperture(start_x, a_top, MAX_SCREEN_SIZE) * 2,
                                           get_aperture(start_x, a_bot, MAX_SCREEN_SIZE) * 2)
            elif tree_mode == 'r':
                available_pos_height = (a_top + a_bot) * zoom_factor

        elif pos == 3:  # float
            facegrid_width = 0
            facegrid_height = 0
            available_pos_width = 0
            start_x = x
            available_pos_height = 0

        elif pos == 4:  # aligned
            facegrid_width = dim[_baw]
            facegrid_height = dim[_bah]
            available_pos_width = MAX_SCREEN_SIZE
            start_x = x
            if tree_mode == 'c':
                available_pos_height = min(get_aperture(start_x, a_top, MAX_SCREEN_SIZE) * 2,
                                           get_aperture(start_x, a_bot, MAX_SCREEN_SIZE) * 2)
            elif tree_mode == 'r':
                available_pos_height = (a_top + a_bot) * zoom_factor
            #print("aligned", node.name, facegrid_width, facegrid_height, available_pos_height)
        # saves important data of each pos
        pos2params[pos] = [start_x, available_pos_width,
                           available_pos_height, facegrid_width, facegrid_height]

    # calculate face information per pos and columns (face list, column width
    # and height)
    pos2colfaces = {}
    poscol2width = {}
    poscol2height = {}

    for faceidx, (face, pos, row, col, fw, fh) in enumerate(facegrid):
        if target_positions is not None and pos not in target_positions:
            continue
        if not dim[_is_leaf] and face.only_if_leaf and not is_collapsed:
            continue
        pos2colfaces.setdefault(pos, {}).setdefault(col, []).append(faceidx)
        poscol2width[(pos, col)] = max(fw, poscol2width.get((pos, col), 0))
        poscol2height[(pos, col)] = poscol2height.get((pos, col), 0) + fh

    # Set up each face position and available space, and call draw_face
    for pos, columns in pos2colfaces.items():
        (start_x, avail_pos_width, avail_pos_height,
         pos_width, pos_height) = pos2params[pos]

        # TODO: Skip if facegrid too small

        for col, selected_faces in columns.items():

            col_height = poscol2height[(pos, col)]
            col_width = poscol2width[(pos, col)]
            avail_col_width = min(col_width,
                                  ((col_width / pos_width) * avail_pos_width))
            avail_col_height = min(col_height,
                                   ((col_height / pos_height) * avail_pos_height))

            start_y = 0  # We assume painter 0,0 coords are placed at the node center
            if pos == 0:  # branch top
                start_y -= avail_col_height
            elif pos == 1:  # branch bottom
                start_y = start_y
            elif pos == 2 or pos == 4:  # branch right or aligned
                start_y -= avail_col_height / 2.0
            elif pos == 3:  # branch float
                start_y -= col_height

            for faceidx in selected_faces:
                face, _pos, _row, _col, fw, fh = facegrid[faceidx]
                avail_face_height = (fh / col_height) * avail_col_height

                y_face_zoom_factor = (avail_face_height / fh)
                x_face_zoom_factor = (avail_col_width / fw)

                face_zoom_factor = min(x_face_zoom_factor, y_face_zoom_factor)
                if 0 and not node.children:
                    print(node.name)
                    print(" aph: ", avail_pos_height)
                    print(" ach: ", avail_col_height)
                    print(" afh: ", avail_face_height)
                    print(" ph:  ", pos_height)
                    print(" ch:  ", col_height)
                    print(" fh:  ", fh)
                    print()
                    print(" apw: ", avail_pos_width)
                    print(" acw: ", avail_col_width)
                    print(" afw: ", avail_col_width)
                    print(" pw:  ", pos_width)
                    print(" cw:  ", col_width)
                    print(" fw:  ", fw)
                    print()
                    print(" zoom_factor", face_zoom_factor)
                    print("------")

                draw = True
                if target_rect and not target_rect.intersects(QRectF(start_x, start_y, avail_col_width, avail_face_height)):
                    #draw = False
                    pass

                if draw:
                    # ======================+
                    # DRAW FACE
                    face.node = node

                    face.arc_start = dim[_astart]
                    face.arc_end = dim[_aend]
                    face.arc_center = dim[_acenter]
                    face.img_rad = _rad

                    face._pre_draw()

                    pp.translate(start_x, start_y)

                    restore_rot_painter = False
                    if correct_rotation and face.rotable:
                        restore_rot_painter = True
                        pp.save()
                        zoom_half_fw = ((fw * face_zoom_factor)/2)
                        zoom_half_fh = ((fh * face_zoom_factor)/2)
                        pp.translate(zoom_half_fw, zoom_half_fh)
                        pp.rotate(180)
                        pp.translate(-(zoom_half_fw), -(zoom_half_fh))

                    face._draw(pp, painter, 0, 0, face_zoom_factor,
                               w=available_pos_width, h=avail_col_width)

                    if restore_rot_painter:
                        pp.restore()

                    # END OF DRAW FACE
                    # =======================

                start_y += avail_face_height

            start_x += avail_col_width
            if pos == 2 or pos == 4:
                endx += avail_col_width

    return endx
