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

from .utils import colorify
from .common import *
from .utils import timeit, debug
from . import layout

COLLAPSE_RESOLUTION = 10
MAX_SCREEN_SIZE = 999999999999999

def pol2cart(rho, phi):
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)
    return(x, y)
        
def get_cart_coords(radius, radians, cx, cy):
    a = (2 * math.pi) - radians;
    x = math.cos(a) * radius
    y = math.sin(a) * radius
    return x + cx, -y + cy

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
    fpath= QPainterPath()
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
    draw_region(tree_image, pp, zoom_factor, source_rect)
    pp.end()
    return ii

@timeit
def draw_region(tree_image, pp, zoom_factor, scene_rect):
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

        # If node and their descendants are not visible, skip them
        if not fpath.intersects(m_scene_rect):
            new_curr = max(int(dim[_max_leaf_idx]+1), curr)
            terminal_nodes.append(node)
            OUTSIDE += 1
            curr = new_curr
            continue

        # Calculate how much space is there at this zoom for drawing the node
        if treemode == 'c' and dim[_fnh] >= R180:
            node_height = MAX_SCREEN_SIZE
            node_height_up = MAX_SCREEN_SIZE
            node_height_down = MAX_SCREEN_SIZE
        elif treemode == 'c':
            node_height = ((math.sin(dim[_fnh]/2.0) * dim[_fnw]) * 2) * zoom_factor
            node_height_up = ((math.sin(dim[_acenter]-dim[_astart]) * dim[_fnw]) ) * zoom_factor
            node_height_down = ((math.sin(dim[_aend]-dim[_acenter]) * dim[_fnw]) ) * zoom_factor
        elif treemode == 'r':
            node_height = fpath.boundingRect().height() * zoom_factor
            node_height_up = node_height / 2.0
            node_height_down = node_height / 2.0

        # Decides if the node is small enough to be considered a collapsed
        # terminal node
        if (node_height_up < COLLAPSE_RESOLUTION) \
           or node_height_down < COLLAPSE_RESOLUTION \
           or node_height/len(node.children) < 3:
            curr = int(dim[_max_leaf_idx] + 1)
            draw_collapsed = True
            is_terminal = True
            COLLAPSED += 1
        elif dim[_is_leaf]:
            curr += 1
            is_terminal = True
        else:
            curr += 1
            is_terminal = False
              
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
                face_pos_sizes = layout.compute_face_dimensions(node, node._temp_faces)
                dim[_btw:_bah+1] = face_pos_sizes

        if draw_collapsed:
            pp.setPen(QPen(QColor("LightSteelBlue")))
            pp.drawPath(M.map(fpath))            
        else:
            if treemode == "c":
                parent_radius = img_data[int(dim[_parent])][_rad] if nid else tree_image.root_open

                # Draw arc line connecting children
                if not dim[_is_leaf] and len(node.children) > 1:
                    acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
                    acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]
                    pp.setPen(QColor(node.img_style.vt_line_color))
                    vLinePath = get_arc_path(dim[_rad], dim[_rad], [acen_0, acen_1])
                    pp.drawPath(M.map(vLinePath))

                hLinePath = get_arc_path(parent_radius, parent_radius+branch_length, [dim[_acenter]])
                pp.setPen(QColor(node.img_style.hz_line_color))
                pp.drawPath(M.map(hLinePath))

                new_rad, new_angle = get_qt_corrected_angle(parent_radius, dim[_acenter])
                pp.translate(cx * zoom_factor, cy * zoom_factor)
                pp.rotate(np.degrees(new_angle))
                #pp.translate(new_rad * zoom_factor, 0)
                endx = draw_faces(pp, new_rad * zoom_factor, 0, node, zoom_factor, tree_image,
                                       is_collapsed=False, target_positions = set([0, 1, 2, 3]))

            elif treemode == "r":
                parent_radius = img_data[int(dim[_parent])][_xend] if nid else tree_image.root_open
                new_rad = parent_radius
                # Draw vertical line connecting children
                if not dim[_is_leaf] and len(node.children) > 1:
                    acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
                    acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]
                    pp.setPen(QColor(node.img_style.vt_line_color))
                    pp.drawLine(M.map(QLineF(parent_radius+branch_length, acen_0,
                                             parent_radius+branch_length, acen_1)))

                pp.setPen(QColor(node.img_style.hz_line_color))
                pp.drawLine(M.map(QLineF(parent_radius, dim[_acenter],
                                         parent_radius+branch_length, dim[_acenter])))

                pp.translate(parent_radius*zoom_factor, dim[_ycenter]*zoom_factor)

                endx = draw_faces(pp, 0, 0, node, zoom_factor, tree_image,
                                       is_collapsed=False, target_positions = set([0, 1, 2, 3]))
        pp.restore()

        # If the node is terminal, it should be used to adjust the aligned face
        # start_x position dynamically. If the end_x position of the terminal
        # node is visiable, then it should be considered, otherwise skip it.
        if is_terminal:            
            terminal_nodes.append(node)
            endpos = (dim[_rad] * zoom_factor) + endx

            matrix = QTransform()
            if treemode == "c":
                matrix.translate(cx * zoom_factor, cy * zoom_factor)
                middle_a = np.degrees(dim[_astart] + (dim[_aend] - dim[_astart])/2)
                matrix.rotate(middle_a)
                node_y_middle = 0 
                node_end = matrix.map(QPointF(endpos, node_y_middle))
                
            elif treemode == "r":
                #endpos = (dim[_xend] * zoom_factor) + endx
                #print(dim[_xend], dim[_fnw])
                node_y_middle = dim[_acenter] * zoom_factor
                node_end = QPointF(endpos, node_y_middle)

            if scene_rect.contains(node_end):
                visible_leaves.append(node)
                # Debug 
                #temppath = QPainterPath()
                #temppath.addRect(QRectF(endpos, node_y_middle, 1, 1))
                # if treemode == "c":
                #     pp.drawPath(matrix.map(temppath))
                # else: 
                #     pp.drawPath(temppath)
                #pp.setPen(QPen(QColor("Green")))
                #pp.drawPath(M.map(fpath))
             
                if endpos > start_x_aligned_faces: 
                    start_x_aligned_faces = max(start_x_aligned_faces, endpos)
                    farthest_fpath = fpath
            
    if farthest_fpath: 
        pp.setPen(QPen(QColor("Red")))
        pp.drawPath(M.map(farthest_fpath))
             
    # Draw aligned faces
    for node in terminal_nodes:
        dim = tree_image.img_data[node._id]
        pp.save()
        if treemode == "c":
            #new_rad, new_angle = get_qt_corrected_angle(start_x_aligned_faces, dim[_acenter])
            pp.translate(cx*zoom_factor, cy*zoom_factor)
            #pp.rotate(np.degrees(new_angle))
            pp.rotate(np.degrees(dim[_acenter]))
            endx = draw_faces(pp, start_x_aligned_faces, 0, node, zoom_factor,
                              tree_image, is_collapsed=False, target_positions = [4])
        elif treemode == "r":
            pp.translate(start_x_aligned_faces, dim[_ycenter]*zoom_factor)
            endx = draw_faces(pp, 0, 0, node, zoom_factor,
                              tree_image, is_collapsed=False, target_positions = [4])


        pp.restore()

def draw_faces(pp, x, y, node, zoom_factor, tree_image, is_collapsed,
               target_positions=None):


    dim = tree_image.img_data[node._id]
    branch_length = dim[_blen]
    facegrid = node._temp_faces
    tree_mode = tree_image.tree_style.mode
    if not facegrid:
        return

    correct_rotation = True if (tree_mode == 'c' and dim[_acenter] > R90 and dim[_acenter] < R270) else False

    # Apertures top-branch and bottom-branch
    a_top = dim[_acenter] - dim[_astart]
    a_bot = dim[_aend] - dim[_acenter]

    # end position hit by these faces
    endx = 0

    # Calculates basic info on how to start drawing each facegrid position block
    pos2params = {}
    for pos in range(5):
        if pos == 0: # btop
            facegrid_width = dim[_btw]
            facegrid_height = dim[_bth]
            available_pos_width = branch_length * zoom_factor
            start_x = x # IDEA: align to right
            if tree_mode == 'c':
                available_pos_height = get_aperture(start_x, a_top, MAX_SCREEN_SIZE)
            elif tree_mode == 'r':
                available_pos_height = a_top * zoom_factor 

        elif pos == 1: # bbottom
            facegrid_width = dim[_bbw]
            facegrid_height = dim[_bbh]
            available_pos_width = branch_length * zoom_factor
            start_x = x # IDEA: align to right
            if tree_mode == 'c':
                available_pos_height = get_aperture(start_x, a_bot, MAX_SCREEN_SIZE)
            elif tree_mode == 'r':
                available_pos_height = a_bot * zoom_factor 

        elif pos == 2: # branch right
            facegrid_width = dim[_brw]
            facegrid_height = dim[_brh]
            available_pos_width = dim[_brw] * zoom_factor
            start_x = x + (branch_length * zoom_factor)
            if tree_mode == 'c':
                available_pos_height = min(get_aperture(start_x, a_top, MAX_SCREEN_SIZE) * 2,
                                            get_aperture(start_x, a_bot, MAX_SCREEN_SIZE) * 2)
            elif tree_mode == 'r':
                available_pos_height = (a_top + a_bot) * zoom_factor 

        elif pos == 3: # float
            facegrid_width = 0
            facegrid_height = 0
            available_pos_width = 0
            start_x = x 
            available_pos_height= 0

        elif pos == 4: # aligned
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
        pos2params[pos] = [start_x, available_pos_width, available_pos_height, facegrid_width, facegrid_height]

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
        (start_x, avail_pos_width, avail_pos_height, pos_width, pos_height) =  pos2params[pos]
        
        # TODO: Skip if facegrid too small

        for col, selected_faces in columns.items(): 

            col_height = poscol2height[(pos, col)]
            col_width = poscol2width[(pos, col)]
            avail_col_width  = min(col_width, 
                                   ((col_width / pos_width) * avail_pos_width))
            avail_col_height  = min(col_height, 
                                    ((col_height / pos_height) * avail_pos_height))

            start_y = 0 # We assume painter 0,0 coords are placed at the node center 
            if pos == 0: # branch top
                start_y -= avail_col_height
            elif pos == 1: # branch bottom
                start_y = start_y
            elif pos == 2 or pos == 4: # branch right or aligned
                start_y -=  avail_col_height / 2.0
            elif pos == 3: # branch float
                start_y -=  col_height

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
                                  
                face._draw(pp, 0, 0, face_zoom_factor)

                if restore_rot_painter:
                    pp.restore()

                # END OF DRAW FACE 
                # =======================
                start_y += avail_face_height 

            start_x += avail_col_width
            if pos == 2 or pos == 4:
                endx += avail_col_width

    return endx







# @timeit
# def draw_region_circ(tree_image, pp, zoom_factor, scene_rect):
#     arc_paths = tree_image.circ_collision_paths
#     img_data = tree_image.img_data
#     cx = tree_image.radius[0]
#     cy = cx

#     m = QTransform()
#     m.translate(-cx, -cy)
#     m.scale(1/zoom_factor, 1/zoom_factor)
#     m_scene_rect = m.mapRect(scene_rect)

#     M = QTransform()
#     M.scale(zoom_factor, zoom_factor)
#     M.translate(cx, cy)

#     #aligned_circ_diam = tree_image.radius[0] * zoom_factor * 2
#     #c1 = (tree_image.radius[-1] -  tree_image.radius[-0]) * zoom_factor
#     #pp.drawEllipse(c1, c1, aligned_circ_diam, aligned_circ_diam)

#     # DEBUG INFO
#     DRAWN, OUTSIDE, COLLAPSED, ITERS = 0, 0, 0, 0

#     curr = 0
#     nid = curr
#     end = img_data[curr][_max_leaf_idx] + 1
#     max_observed_radius = 0
#     visible_leaves = []
#     terminal_nodes = []
#     visible_labels = []
#     while curr < end:
#         ITERS += 1
#         draw_collapsed = False
#         nid = curr
#         node = tree_image.cached_preorder[nid]
#         dim = img_data[nid]
#         nsize = nid - tree_image.img_data[nid][_max_leaf_idx]+1
#         branch_length = dim[_blen] #* tree_image.scale

#         # Compute node and full paths for the node
#         if arc_paths[nid][0] is None:
#             path, fpath = get_node_arc_path(tree_image, nid)
#             arc_paths[nid] = [path, fpath]
#         else:
#             path, fpath = arc_paths[nid]

#         # If node and their descendants are not visible, skip them
#         if not fpath.intersects(m_scene_rect):
#             new_curr = max(int(dim[_max_leaf_idx]+1), curr)
#             terminal_nodes.append(node)
#             OUTSIDE += 1
#             curr = new_curr
#             continue

#         if dim[_fnh] >= R180:
#             node_height = 999999999
#             node_height_left = 999999999
#             node_height_right = 999999999

#         else:
#             node_height = ((math.sin(dim[_fnh]/2.0) * dim[_fnw]) * 2) * zoom_factor
#             node_height_left = ((math.sin(dim[_acenter]-dim[_astart]) * dim[_fnw]) ) * zoom_factor
#             node_height_right = ((math.sin(dim[_aend]-dim[_acenter]) * dim[_fnw]) ) * zoom_factor


#         # if descendants are too small, draw the whole partition as a single
#         # simplified item
#         if (node_height_left < COLLAPSE_RESOLUTION) \
#            or node_height_right < COLLAPSE_RESOLUTION \
#            or node_height/len(node.children) < 3:
#             curr = int(dim[_max_leaf_idx] + 1)
#             draw_collapsed = True
#             is_terminal = True
#             COLLAPSED += 1
#         elif dim[_is_leaf]:
#             curr += 1
#             is_terminal = True
#         else:
#             curr += 1
#             is_terminal = False

#        # record node as terminal
#         if is_terminal:
#             # visible leaves for aligned faces
#             terminal_nodes.append(node)
#             #node_x, node_y = pol2cart(dim[_fnw], dim[_acenter])

#             new_rad, new_angle = get_qt_corrected_angle(dim[_fnw], dim[_acenter])
#             anode_x, anode_y = get_cart_coords(new_rad*zoom_factor, new_angle, cx*zoom_factor, cy*zoom_factor)
            
#             if scene_rect.contains(anode_x, anode_y):
#                 visible_leaves.append(node)
#                 endx = dim[_fnw] * zoom_factor
#             else:
#                 endx = 0

#         # If node is not visible, don't draw it
#         #if not draw_collapsed and not path.intersects(m_scene_rect):
#         #    continue

#         # Actually draw the node
#         DRAWN += 1

#         # Compute faces
#         if not node._temp_faces:
#             node._temp_faces = None
#             for func in tree_image.tree_style.layout_fn:
#                 func(node)

#         pp.save()
#         parent_radius = img_data[int(dim[_parent])][_rad] if nid else tree_image.root_open
#         node = tree_image.cached_preorder[nid]

#         if draw_collapsed:
#             if node in visible_leaves:
#                 pp.setPen(QPen(QColor("LightSteelBlue")))
#             else:
#                 pp.setPen(QPen(QColor("#AAAAAA")))
#             pp.drawPath(M.map(fpath))
#         else:

#             # Draw arc line connecting children
#             if not dim[_is_leaf] and len(node.children) > 1:
#                 acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
#                 acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]
#                 pp.setPen(QColor(node.img_style.vt_line_color))
#                 vLinePath = get_arc_path(dim[_rad], dim[_rad], [acen_0, acen_1])
#                 pp.drawPath(M.map(vLinePath))

#             hLinePath = get_arc_path(parent_radius, parent_radius+branch_length, [dim[_acenter]])
#             pp.setPen(QColor(node.img_style.hz_line_color))
#             pp.drawPath(M.map(hLinePath))

#         new_rad, new_angle = get_qt_corrected_angle(parent_radius, dim[_acenter])
#         pp.translate(cx*zoom_factor, cy*zoom_factor)
#         pp.rotate(np.degrees(new_angle))

#         # if node was not visited yet, compute face dimensions
#         if not np.any(dim[_btw:_bah+1]):
#             face_pos_sizes = layout.compute_face_dimensions(node, node._temp_faces)
#             dim[_btw:_bah+1] = face_pos_sizes

#         end_faces = draw_faces(pp, new_rad, 0, node, zoom_factor, tree_image,
#                           is_collapsed=False, target_positions = set([0, 1, 2, 3]))
#         if is_terminal:
#             max_observed_radius = max(max_observed_radius, endx + end_faces)

#         pp.restore()

#     visible_leaves.sort(reverse=True,
#                         key = lambda x: x._id - tree_image.img_data[x._id][_max_leaf_idx])

#     for node in terminal_nodes:
#         dim = tree_image.img_data[node._id]
#         pp.save()
#         new_rad, new_angle = get_qt_corrected_angle(max_observed_radius, dim[_acenter])
#         pp.translate(cx*zoom_factor, cy*zoom_factor)
#         pp.rotate(np.degrees(new_angle))
#         endx = draw_faces(pp, new_rad, 0, node, 1,
#                           tree_image, is_collapsed=False, target_positions = [4])
#         pp.restore()

#     if tree_image.tree_style.show_labels:
#         for node in visible_leaves:
#             dim = tree_image.img_data[node._id]
#             # Draw overlay labels
#             if not dim[_is_leaf]:
#                 pp.save()
#                 qfont = QFont("Verdana",pointSize=16)
#                 qfont.setWeight(QFont.Black)
#                 fm = QFontMetrics(qfont)
#                 name = node.name.strip()
#                 text_w = fm.width(name)
#                 text_h = fm.height()
#                 new_rad, new_angle = get_qt_corrected_angle(dim[_fnw], dim[_acenter])
#                 node_x, node_y = get_cart_coords(new_rad*zoom_factor, new_angle, cx*zoom_factor, cy*zoom_factor)
#                 label_rect = QRectF(node_x, node_y, text_w, text_h)
#                 # if dim[_acenter] >= R90 and dim[_acenter] <=R270:
#                 #     label_rect.translate(-text_w,0)

#                 rect_x = node_x
#                 rect_y = node_y
#                 if dim[_acenter] <R90:
#                     label_rect.translate(-text_w, -text_h)
#                     rect_x -= text_w
#                     color= "teal"
#                 elif dim[_acenter] <R180:
#                     label_rect.translate(0, -text_h)
#                     color= "seagreen"
#                 elif dim[_acenter] < R270:
#                     label_rect.translate(0, 0)
#                     rect_y += text_h
#                     color= "slategrey"
#                 else:
#                     label_rect.translate(-text_w, 0)
#                     rect_x -= text_w
#                     rect_y += text_h
#                     color = "darkgoldenrod"

#                 skip_label = False
#                 for x in visible_labels:
#                     if label_rect.intersects(x):
#                         skip_label = True
#                         break
#                 if not skip_label:
#                     visible_labels.append(label_rect)
#                     pp.setFont(qfont)

#                     pp.setPen(QColor("white"))
#                     pp.setBrush(QColor(color))

#                     text_path = QPainterPath()
#                     text_path.addText(rect_x, rect_y-5, qfont, name)
#                     pp.setOpacity(0.2)
#                     pp.drawRoundedRect(label_rect, 5, 5)
#                     pp.setOpacity(0.7)
#                     pp.drawText(rect_x, rect_y-5, node.name)
#                     pp.drawEllipse(node_x-5, node_y-5, 10, 10)
#                     pp.drawPath(text_path)
#                 pp.restore()

#     logger.debug(colorify("Iters: %d, Drawn:%d, OutScene:%d, Collapsed:%d" %(ITERS, DRAWN, OUTSIDE, COLLAPSED), "lblue"))
#     logger.debug(colorify(" Visible leaves: %d rad: %0.3f (term nodes: %d)" \
#                           %(len(visible_leaves), max_observed_radius, len(terminal_nodes)), "magenta" ))


# @timeit
# def draw_faces2(pp, x, y, node, zoom_factor, tree_image, is_collapsed,
#                target_positions=None):

#     dim = tree_image.img_data[node._id]
#     branch_length = dim[_blen]
#     facegrid = node._temp_faces
#     if not facegrid:
#         return

#     correct_rotation = True if tree_image.tree_style.mode == 'c' and \
#                        dim[_acenter] > R90 and dim[_acenter] < R270 \
#                        else False

#     # Apertures top-branch and bottom-branch
#     a_top = dim[_acenter] - dim[_astart]
#     a_bot = dim[_aend] - dim[_acenter]

#     def draw_face_column(faces, _x, _y, _rad, _face_zoom_factor):
#         for _f, fw, fh in faces:
#             if not dim[_is_leaf] and _f.only_if_leaf and not is_collapsed:
#                 continue


#             restore_rot_painter = False
#             _f.node = node
#             _f.arc_start = dim[_astart]
#             _f.arc_end = dim[_aend]
#             _f.arc_center = dim[_acenter]
#             _f.img_rad = _rad

#             _f._pre_draw()

#             if correct_rotation and _f.rotable:
#                 restore_rot_painter = True
#                 pp.save()
#                 zoom_half_fw = ((fw * _face_zoom_factor)/2)
#                 zoom_half_fh = ((fh * _face_zoom_factor)/2)
#                 pp.translate(zoom_half_fw, zoom_half_fh)
#                 pp.rotate(180)
#                 pp.translate(-(zoom_half_fw), -(zoom_half_fh))

#             # Draw face
#             _f._draw(pp, _x, _y, _face_zoom_factor)

#             # # Draw face border (DEBUG)
#             if 1:
#                 pp.save()
#                 pp.setPen(QPen(QColor('orange'), ))
#                 pp.scale(_face_zoom_factor, _face_zoom_factor)
#                 pp.drawRect(_x, _y, fw, fh)
#                 pp.restore()


#             if restore_rot_painter:
#                 pp.restore()
#                 _y -= fh
#             else:
#                 _y += fh


#     # calculate width and height of each facegrid column
#     pos2colfaces = {}
#     poscol2width = {}
#     poscol2height = {}
#     for face, pos, row, col, fw, fh in facegrid:
#         if target_positions is not None and pos not in target_positions:
#             continue

#         if not dim[_is_leaf] and face.only_if_leaf and not is_collapsed:
#             continue

#         pos2colfaces.setdefault(pos, {}).setdefault(col, []).append([face, fw, fh])
#         poscol2width[pos, col] = max(fw, poscol2width.get((pos, col), 0))
#         poscol2height[pos, col] = poscol2height.get((pos, col), 0) + fh

#     endx = 0
#     for pos, colfaces in pos2colfaces.items():
#         if pos == 0:
#             facegrid_width = dim[_btw]
#             facegrid_height = dim[_bth]
#             #available_pos_width = max(dim[_btw], branch_length) * zoom_factor
#             available_pos_width = branch_length * zoom_factor
#             start_x = x
#         elif pos == 1: #bbottom
#             facegrid_width = dim[_bbw]
#             facegrid_height = dim[_bbh]
#             #available_pos_width = max(dim[_bbw], branch_length) * zoom_factor
#             available_pos_width = branch_length * zoom_factor
#             start_x = x
#         elif pos == 2: #bright
#             facegrid_width = dim[_brw]
#             facegrid_height = dim[_brh]
#             available_pos_width = dim[_brw] * zoom_factor
#             start_x = x + branch_length
#         elif pos == 3: #float
#            pass
#         elif pos == 4: #aligned
#             facegrid_width = dim[_baw]
#             facegrid_height = dim[_bah]
#             available_pos_width = 99999999999 * zoom_factor
#             start_x = x
#         else:
#             continue

#         start_x *= zoom_factor

#         # Calculate available angle aperture to draw face
#         if pos == 0:
#             aperture = get_aperture(start_x, a_top, 9999999999)
#         elif pos == 1:
#             aperture = get_aperture(start_x, a_bot, 9999999999)
#         elif pos == 2:
#             aperture = min(get_aperture(start_x, a_top, 99999999999) * 2,
#                                get_aperture(start_x, a_bot, 99999999999) * 2)
#         elif pos == 3:
#             pass
#         elif pos == 4:
#             aperture = min(get_aperture(start_x, a_top, 99999999999) * 2,
#                                get_aperture(start_x, a_bot, 99999999999) * 2)
#         else:
#             raise ValueError("not supported face position")

#         # skip if there is not enough height
#         if aperture < 1:
#             continue

#         # skip if there is not enough width
#         if available_pos_width < 1:
#             continue

#         # Faces are scaled based on available space given current zoom factor
#         y_face_zoom_factor = aperture / facegrid_height
#         x_face_zoom_factor = available_pos_width / facegrid_width

#         face_zoom_factor = min(x_face_zoom_factor, y_face_zoom_factor, 1.0)

#         for col, faces in colfaces.items():
#             if pos == 0:
#                 start_y = y - (poscol2height[pos, col])
#             elif pos == 1:
#                 start_y = y
#             elif pos == 2 or pos == 4:
#                 start_y = y - (poscol2height[pos, col]/2.0)
#                 endx += (poscol2width[pos, col] * face_zoom_factor)
#             elif pos == 3:
#                 pass

#             if zoom_factor > 0:
#                 pp.save()
#                 pp.setOpacity(face.opacity)
#                 pp.translate(start_x, start_y * face_zoom_factor)
#                 draw_face_column(faces, 0.0, 0.0, start_x, face_zoom_factor)
#                 pp.restore()

#             # continue with next column
#             start_x += poscol2width[pos, col] * face_zoom_factor

#     return endx
