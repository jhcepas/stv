def get_absolute_coords(radius, rot_deg, cx, cy):
    theta = rot_deg - int(rot_deg / 90) * 90
    angle = (theta * math.pi)/180
    adj = math.cos(angle) * radius
    opo = math.sin(angle) * radius
    if rot_deg >= 0 and rot_deg < HALFPI:      # bottom-right
        x = cx + adj
        y = cy + opo
    elif rot_deg >= 90 and rot_deg < 180:  # bottom-left
        x = cx - opo
        y = cy + adj
    elif rot_deg >= 180 and rot_deg < 270: # top-left
        x = cx - adj
        y = cy - opo
    else:                              # top-right
        x = cx + opo
        y = cy - adj
    return x, y


def draw_circ_node_links(pp, node_links, cx, cy, node_zoom_positions):
    link_paths = []
    #max_rad = max([reg[_rad] for reg in node_zoom_positions])
        
    for a, b, a_mode, b_mode, bg, lw, opa, text, fsize, fcolor, ftype in node_links:
        if node_zoom_positions[a._id][_rot] > node_zoom_positions[b._id][_rot]:
            a, b = b, a

        if b in set(a.get_ancestors()): ############ CACHE THIS!
            b_mode = 0
        elif a in set(b.get_ancestors()):
            a_mode = 0
        
        if not a.is_leaf() and a_mode == 1:
            a_max_rad = 0
            a_min_rot = 360
            a_max_rot = 0
            for lf in a.iter_leaves():
                a_max_rad = max((a_max_rad, node_zoom_positions[lf._id][_rad]))
                a_min_rot = min((a_min_rot, node_zoom_positions[lf._id][_astart]))
                a_max_rot = max((a_max_rot, node_zoom_positions[lf._id][_aend]))
            a1x, a1y = get_absolute_coords(a_max_rad, a_min_rot, cx, cy)
            a2x, a2y = get_absolute_coords(a_max_rad, a_max_rot, cx, cy)
            acx, acy = get_absolute_coords(a_max_rad, a_min_rot +(a_max_rot-a_min_rot)/2, cx, cy)
        else:
            a_pos = node_zoom_positions[a._id]
            a_max_rad = a_pos[_rad]
            a_min_rot = a_max_rot = a_pos[_rot]
            a1x, a1y = get_absolute_coords(a_pos[_rad], a_pos[_rot], cx, cy)
            a2x, a2y = a1x, a1y
            acx, acy = a1x, a1y

        if not b.is_leaf() and b_mode == 1:
            b_max_rad = 0
            b_min_rot = 360
            b_max_rot = 0
            for lf in b.iter_leaves():
                b_max_rad = max((b_max_rad, node_zoom_positions[lf._id][_rad]))
                b_min_rot = min((b_min_rot, node_zoom_positions[lf._id][_astart]))
                b_max_rot = max((b_max_rot, node_zoom_positions[lf._id][_aend]))
            b1x, b1y = get_absolute_coords(b_max_rad, b_min_rot, cx, cy)
            b2x, b2y = get_absolute_coords(b_max_rad, b_max_rot, cx, cy)
            bcx, bcy = get_absolute_coords(b_max_rad, b_min_rot + (b_max_rot-b_min_rot)/2, cx, cy)
        else:
            b_pos = node_zoom_positions[b._id]
            b_max_rad = b_pos[_rad]
            b_min_rot = b_max_rot = b_pos[_rot]
            b1x, b1y = get_absolute_coords(b_pos[_rad], b_pos[_rot], cx, cy)
            b2x, b2y = b1x, b1y
            bcx, bcy = b1x, b1y
           
        path = QPainterPath()
        path.moveTo(a2x, a2y)
        path.quadTo(cx, cy, b1x, b1y)
        pp.setBrush(get_qbrush(None))
        pp.setPen(get_qpen(bg, lw, 0, Qt.FlatCap))
        
        if b1x != b2x or b1y != b2y:
            path.arcTo(cx - b_max_rad, cy - b_max_rad,
                       b_max_rad*2, b_max_rad*2,
                       -b_min_rot, -(b_max_rot-b_min_rot))
            path.quadTo(cx, cy, a1x, a1y)
            pp.setPen(get_qpen(bg, 0, 0, Qt.FlatCap))
            pp.setBrush(get_qbrush(bg))
        else:
            path.quadTo(cx, cy, a1x, a1y)
            
        if a1x != a2x or a1y != a2y:
            path.arcTo(cx - a_max_rad, cy - a_max_rad,
                       a_max_rad*2, a_max_rad*2,
                       -a_min_rot, -(a_max_rot-a_min_rot))
            pp.setPen(get_qpen(bg, 0, 0, Qt.FlatCap))
            pp.setBrush(get_qbrush(bg))
            
        pp.setOpacity(opa)
        pp.drawPath(path)            
                
        if bcx < acx:
            acx, acy, bcx, bcy = bcx, bcy, acx, acy

        txtpath = QPainterPath()
        txtpath.moveTo(acx, acy)
        txtpath.quadTo(cx, cy, bcx, bcy)
        draw_text_in_path(pp, "Esto es una prueba muy muy larga para ver que pasa con las curvas",
                          txtpath, ftype, fcolor, fsize)
        
    #draw_rings(pp, cx, cy, node_zoom_positions, node_links)
    
def draw_text_in_path(pp, text, follow_path, ftype, fcolor, fsize):
    length = follow_path.length()
    pp.setPen(get_qpen(fcolor))
    font = get_qfont(ftype, fsize, False)
    pp.setFont(font)
    fm = QFontMetrics(font)
    text_width = fm.width(text)
   
    # approx center text in path
    current_length = (length/2) - (text_width/2)
    for letter in text:
        perc = follow_path.percentAtLength(current_length)
        point = QPointF(follow_path.pointAtPercent(perc))
        angle = follow_path.angleAtPercent(perc)

        current_length += fm.width(letter)
        
        pp.save()
        pp.translate(point)
        pp.rotate(-angle)
        pp.drawText(QPoint(0, 0), letter)
        pp.restore()



def draw_circ_node_rings(pp, node_rings, cx, cy, node_zoom_positions):
    t = node_rings[0][0].get_tree_root()
    max_rad = max([reg[_rad] for reg in node_zoom_positions])
    ftype = "Arial"
    fsize = 20
    fcolor = "black"
    for n in t.children:
        # ring = get_arc_path(node_zoom_positions[n.up._id][_rad], node_zoom_positions[n._id][_rad],
        #                    node_zoom_positions[n._id][_astart], node_zoom_positions[n._id][_aend],
        #               cx, cy)
        height = n.img_style.size * 10
        
        ring = get_arc_path(max_rad-50, max_rad-height,
                            node_zoom_positions[n._id][_astart], node_zoom_positions[n._id][_aend],
                            cx, cy)

        color = "blue" #random_color()
        pp.setPen(get_qpen(color, 1))
        pp.setBrush(get_qbrush(color))
        pp.setOpacity(0.4)
        pp.drawPath(ring)
        
        textpath = QPainterPath()
        astart = node_zoom_positions[n._id][_astart]
        aend = node_zoom_positions[n._id][_aend]
        aspan = aend - astart
        center_rad = max_rad - 50 + ((50-height)/2.0)
        diam = center_rad * 2
        textpath.arcMoveTo(cx - center_rad, cy - center_rad, diam, diam, -astart)
        start = textpath.currentPosition()
        textpath.moveTo(start)
        textpath.arcTo(cx - center_rad, cy - center_rad, diam, diam, -astart, -aspan)
        pp.setBrush(get_qbrush(None))
        pp.setPen(get_qpen("black", 1))
        pp.drawPath(textpath)
        pp.save()
        pp.setClipPath(ring)
        draw_text_in_path(pp, "ABCDEFGhijkLM", textpath, ftype, fcolor, fsize)
        pp.restore()


    
def draw_vertical_connector(pp, x, y_start, y_end, node):
    # Draw arc line connecting to children nodes
    pp.setBrush(get_qbrush(None))
    style = node.img_style
    pp.setPen(get_qpen(style["vt_line_color"],
                       node.img_style.vt_line_width,
                       style["vt_line_type"], Qt.FlatCap))
    pp.drawLine(x, y_start, x, y_end)
            
def draw_node_shape(pp, x, y, node):
    style = node.img_style
    w = style.size
    halfw = w / 2.0
    pp.setPen(get_qpen(None))
    if style.shape == "sphere":
        pp.setBrush(get_qbrush(style.fgcolor))
        pp.drawEllipse(x, y - halfw, w, w)
    elif style.shape == "circle":
        pp.setBrush(get_qbrush(style.fgcolor))
        pp.drawEllipse(x, y - halfw, w, w)
    elif style.shape == "square":
        pp.setBrush(get_qbrush(style.fgcolor))
        pp.fillRect(x, y - halfw, w, w)
    
def draw_region_rect(tree_image, pp, target_rect):
    node_zoom_positions = tree_image.zoom_rect_pos

    pp.save()

    DRAWS = 0
    for node in tree_image.cached_preorder:

        nodepos = node_zoom_positions[node._id]
        node_rect = QRectF(nodepos[_xpos], nodepos[_ystart],
                           nodepos[_nw],
                           (nodepos[_nht] + nodepos[_nhb]))

        # If node does not collides with tile, skip
        if not target_rect.intersects(node_rect):
            continue

        # Draws background
        if node.img_style.bgcolor:
            pp.fillRect(node_rect, get_qbrush(node.img_style.bgcolor))

        DRAWS += 1

        # use cached data in order to quickly identify what elements have space to be drawn.
        x = xstart = nodepos[_xpos]
        y = nodepos[_ypos]
        if CONFIG["debug"]:
            # Draw node square region
            pp.setPen(get_qpen("red"))
            pp.setBrush(get_qbrush(None))
            #pp.drawRect(node_rect)

        if nodepos[_blen] or nodepos[_eblen]:
            draw_branch(pp, x, y, nodepos[_blen], nodepos[_eblen], node, tree_image.tree_style)
            x += nodepos[_blen] + nodepos[_eblen]

        if nodepos[_ncw]:
            draw_node(pp, x, y, node)
            x += nodepos[_ncw]

        if node not in tree_image.cached_leaves and len(node.children) > 1:
            ycen_0 = node_zoom_positions[node.children[0]._id][_ypos]
            ycen_1 = node_zoom_positions[node.children[-1]._id][_ypos]
            draw_vertical_connector(pp, x, ycen_0, ycen_1, node)

        # draw faces if necessary. It reads cached info about
        # available space to draw different face types.
        if sum(nodepos[_fbt_w:_fbr_w+1]):
            draw_faces(pp, xstart, y, node, tree_image.node_regions[node._id],
                       nodepos, correct_rotation=False)

    pp.restore()


def draw_node(pp, nid, cx, cy, tree_image, zoom_factor, draw_collapsed=False):
    dim = tree_image.img_data[nid]

    rad_start = tree_image.img_data[dim[_parent]][_rad] if nid > 0 else tree_image.root_open    
    if draw_collapsed:
        if draw_collapsed == 1:
            pp.save()
            pp.scale(zoom_factor, zoom_factor)
            pp.translate(cx, cy)        
            pp.rotate(math.degrees(dim[_acenter]))
            pp.setPen(QColor("#dddddd"))
            pp.drawLine(rad_start, 0, dim[_fnw], 0)
            p.restore()        
        else:
            pp.save()
            pp.scale(zoom_factor, zoom_factor)
            pp.translate(cx, cy)        
            pp.rotate(math.degrees(dim[_astart]))
            node_path = get_arc_path(rad_start, dim[_fnw], 0, dim[_aend]-dim[_astart], 0, 0)        
            pp.setPen(QColor("#dddddd"))
            pp.drawPath(node_path)
            pp.restore()
    else:
        node = tree_image.cached_preorder[nid]           
        rotation = dim[_acenter]
            
        branch_length = (dim[_blen] * tree_image.scale)
        extra_branch = 0.0
        
        pp.save()
        pp.scale(zoom_factor, zoom_factor)
        pp.translate(cx, cy)        

        if not dim[_is_leaf] and len(node.children) > 1:            
            rad_end = dim[_rad]
            acen_0 = tree_image.img_data[node.children[0]._id][_acenter]
            acen_1 = tree_image.img_data[node.children[-1]._id][_acenter]            
            pp.save()
            pp.rotate(math.degrees(acen_0))
            draw_circular_connector(pp, rad_end, 0, acen_1-acen_0, node)
            pp.restore()
            
        # rotate to center
        pp.rotate(math.degrees(rotation))                                  
        draw_branch(pp, rad_start, 0, branch_length,
                         extra_branch, node, tree_image.tree_style)
        pp.restore()
        
        pp.save()
        pp.translate(cx*zoom_factor, cy*zoom_factor)        
        pp.rotate(math.degrees(rotation))            
        draw_faces(pp, rad_start, 0, node, dim, branch_length, zoom_factor)
        pp.restore()       

def draw_branch(pp, x, y, branch_length, extra_length, node, tree_style):
    style = node.img_style
    hz_line_width = style.hz_line_width
    vt_line_width = style.vt_line_width
    # Let's try to keep nice joints between hz and vt lines
    capstyle = Qt.FlatCap
    join_fix = node.up.img_style.vt_line_width/2.0 if node.up else 0.0
    # draw branch 
    pp.setPen(get_qpen(style["hz_line_color"],
                       hz_line_width,
                       style["hz_line_type"], capstyle))
    pp.drawLine(QLineF(x - join_fix, y, x + branch_length, y))

    # draw extra length if necessary
    if extra_length:
        pp.setPen(get_qpen(tree_style.extra_branch_line_color,
                           hz_line_width,
                           tree_style.extra_branch_line_type,
                           Qt.FlatCap))
        pp.drawLine(x + branch_length, y,
                    x + branch_length + extra_length, y)


from PyQt4.QtOpenGL import *
class test(QGLWidget):
    def __init__(self, tree_image, zoom_factor, treemode, tile_rect):
        super(test, self).__init__(QGLFormat(QGL.SampleBuffers))
        self.tree_image = tree_image
        self.zoom_factor = zoom_factor
        self.treemode = treemode
        self.scene_rect = QRectF(*tile_rect)        
        self.resize(self.scene_rect.width(), self.scene_rect.height())
        self.painted = False
        
    def initializeGL(self):
        pass#glClearColor(0.0, 0.0, 0.0, 1.0)
        
    def paintEvent(self, event):
        if self.painted:
            return
        self.painter = True
            
        # Create an empty tile image
        print self.scene_rect
        target_rect = QRectF(0, 0, self.scene_rect.width(), self.scene_rect.height())
        
        pp = QPainter()        
        pp.begin(self)
        pp.fillRect(target_rect, QColor("white"))
        
        pp.setRenderHint(QPainter.Antialiasing)
        pp.setRenderHint(QPainter.TextAntialiasing)
        pp.setRenderHint(QPainter.SmoothPixmapTransform)
    
        # Prevent drawing outside target_rect boundaries
        pp.setClipRect(target_rect, Qt.IntersectClip)
    
        # Transform space of coordinates: I want source_rect.top_left() to be
        # translated as 0,0
        matrix = QTransform().translate(-self.scene_rect.left(), -self.scene_rect.top())
        pp.setWorldTransform(matrix, True)
    
        # Paint on tile
        if self.treemode == "c":
            draw_region_circ(self.tree_image, pp, self.zoom_factor, self.scene_rect)
        elif self.treemode == "r":
            draw_region_rect(tree_image, pp, source_rect)
        pp.end()

