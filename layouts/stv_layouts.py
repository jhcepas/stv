from smartview import style, face
from smartview.ete_smartview import N2LEAVES, N2CONTENT, ALIGN, MATRIX, BLOCK_SEQ_FACE

add = style.add_face_to_node

nameF = face.AttrFace("name", fsize=11, fgcolor='royalBlue', ftype='Arial')
#nameF.margin_right = 10
nameF2 = face.AttrFace("name", fsize=16, fgcolor='indianred', ftype='Arial')
nameF3 = face.AttrFace("name", fsize=8, fgcolor='grey', ftype='Arial')
distF = face.AttrFace("dist", fsize=10, fgcolor="grey", formatter="%0.3g")
supportF = face.AttrFace("support", fsize=16)
# labelF = face.LabelFace(70)
# labelF.fill_color = "thistle"
# labelF2 = face.LabelFace(70)
# labelF2.fill_color = "indianred"

circleF = face.CircleLabelFace(attr="support", solid=True, color="blue")

hola = face.TextFace("hola")
mundo = face.TextFace("mundo", fsize=7, fgcolor="grey")
ornot = face.TextFace("ornot", fsize=6, fgcolor="steelblue")
rectF = face.RectFace(100, 100, bgcolor="indianred")
f = face.RectFace(20, 10, bgcolor="pink")
f2 = face.RectFace(120, 10, bgcolor="blue")
f3 = face.RectFace(20, 10, bgcolor="green")
f4 = face.RectFace(20, 10, bgcolor="indianred")
f5 = face.RectFace(20, 10, bgcolor="steelblue")

# gradF = face.GradientFace(width=50, node_attr="custom")
# gradF.only_if_leaf = True


def layout_real(node):
    if node.is_leaf():
        add(nameF, node, column=0, position="branch-right")
        add(distF, node, column=0, position="branch-top")
        add(supportF, node, column=1, position="branch-bottom")
    elif node.up:
        if node.name:
            add(nameF, node, column=0, position="branch-top")
        add(supportF, node, column=1, position="branch-bottom")


def layout_align(node):
    if ALIGN and node in ALIGN:
        add(BLOCK_SEQ_FACE, node, column=10, position="aligned")


def layout_test(node):
    node.img_style.size = 1
    # f.margin_left=20
    add(f, node, column=0, position="branch-right")
    add(f, node, column=0, position="branch-right")
    #add(rectF, node, column=1, position="branch-right")
    if node.is_leaf():
        add(nameF, node, column=2, position="branch-right")
    else:
        if node.name:
            add(nameF, node, column=0, position="branch-top")

    add(hola, node, column=1, position="branch-top")
    add(ornot, node, column=1, position="branch-bottom")
    add(mundo, node, column=2, position="branch-bottom")
    add(mundo, node, column=1, position="branch-bottom")


def layout_crouded(node):
    if node.is_leaf():
        add(nameF, node, column=0, position="branch-right")
        add(nameF2, node, column=0, position="branch-right")
        add(nameF3, node, column=1, position="branch-right")

    else:
        if MATRIX is not None:
            hface = face.HeatmapArcFace(MATRIX[node._id], 100, 0.8)
            add(hface, node, column=0, position="aligned")

        if node.name:
            add(nameF, node, column=0, position="branch-top")
        add(distF, node, column=0, position="branch-bottom")
        #add(face.TextFace(str(N2LEAVES[node]), fsize=13), node, column=0, position="branch-top")
#        add(face.TextFace("%0.2f" % n2dist[n], fsize=13), node, column=0, position="branch-top")
#            add(nameF, node, column=0, position="aligned")


def layout_basic(node):
    if node.is_leaf():
        add(nameF, node, column=0, position="branch-right")
    else:
        if node.name:
            add(distF, node, column=0, position="branch-bottom")
            #add(nameF, node, column=0, position="branch-top")


def layout_stacked(node, dim=None):
    if node.is_leaf():
        add(nameF, node, column=0, position="branch-right")
        add(nameF2, node, column=0, position="branch-right")
        add(nameF3, node, column=1, position="branch-right")
        if MATRIX is not None:
            hface = HeatmapArcFace(MATRIX[node._id], 100, 0.5)
            add(hface, node, column=0, position="aligned")
            hface = HeatmapFace(MATRIX[node._id], 10, 10)
            add(hface, node, column=2, position="branch-right")

    else:
        if MATRIX is not None:
            hface = HeatmapArcFace(MATRIX[node._id], 100, 0.8)
            add(hface, node, column=0, position="aligned")

        if node.name:
            add(nameF, node, column=0, position="branch-top")
        add(distF, node, column=0, position="branch-bottom")
        add(
            face.TextFace(str(N2LEAVES[node]), fsize=13), node, column=0, position="branch-top")
#        add(face.TextFace("%0.2f" % n2dist[n], fsize=13), node, column=0, position="branch-top")
#            add(nameF, node, column=0, position="aligned")


def layout_tol(node, dim=None):
    nameF = face.TextFace(node.name, fgcolor="indianRed", fsize=16)
    # if node.rank:
    #     rankF = face.TextFace(node.sci_name, fgcolor="orange", fsize=10)
    distF = face.TextFace("%0.2f" % node.dist, fgcolor="#888888", fsize=8)
    sizeF = face.TextFace(" (size: %d)" % N2LEAVES[node], fsize=8)

    add(distF, node, column=0, position="branch-bottom")
    if node.is_leaf():
        add(nameF, node, column=0, position="branch-right")
        if MATRIX is not None:
            hface = HeatmapArcFace(MATRIX[node._id], 100, 0.5)
            add(hface, node, column=0, position="aligned")
            hface = HeatmapFace(MATRIX[node._id], 10, 10)
            add(hface, node, column=2, position="branch-right")

    else:
        if MATRIX is not None:
            hface = HeatmapArcFace(MATRIX[node._id], 100, 0.8)
            add(hface, node, column=0, position="aligned")

        if node.name:
            add(nameF, node, column=0, position="branch-top")
            add(sizeF, node, column=1, position="branch-bottom")


def layout_rect(node):
    if node.is_leaf():
        add(rectF, node, column=0, position="branch-right")


def layout_clean(node):
    pass
