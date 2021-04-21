"""
Classes and functions for drawing a tree.
"""

from math import sin, cos, pi, sqrt, atan2
from collections import namedtuple
import random

Size = namedtuple('Size', 'dx dy')  # size of a 2D shape (sizes are always >= 0)
Box = namedtuple('Box', 'x y dx dy')  # corner and size of a 2D shape
# They are all "generalized coordinates" (can be radius and angle, say).


# The convention for coordinates is:
#   x increases to the right, y increases to the bottom.
#
#  +-----> x          +------.
#  |                   \   a .
#  |                    \   .   (the angle thus increases clockwise too)
#  v y                 r \.
#
# This is the convention normally used in computer graphics, including SVGs,
# HTML Canvas, Qt, and PixiJS.
#
# The boxes (shapes) we use are:
#
# * Rectangle         w
#              x,y +-----+          so (x,y) is its (left,top) corner
#                  |     | h        and (x+w,y+h) its (right,bottom) one
#                  +-----+
#
# * Annular sector   r,a .----.
#                       .  dr .     so (r,a) is its (inner,smaller-angle) corner
#                       \   .       and (r+dr,a+da) its (outer,bigger-angle) one
#                        \. da

# Drawing.

class Drawer:
    "Base class (needs subclassing with extra functions to draw)"

    MIN_SIZE = 6  # anything that has less pixels will be outlined

    NPANELS = 1  # number of drawing panels (including the aligned ones)
    TYPE = 'base'  # can be 'rect' or 'circ' for working drawers

    def __init__(self, tree, viewport=None, panel=0, zoom=(1, 1),
                 limits=None, searches=None):
        self.tree = tree
        self.viewport = Box(*viewport) if viewport else None
        self.panel = panel
        self.zoom = zoom
        self.xmin, self.xmax, self.ymin, self.ymax = limits or (0, 0, 0, 0)
        self.searches = searches or {}  # looks like {text: (results, parents)}

    def draw(self):
        "Yield graphic elements to draw the tree"
        self.outline = None  # box surrounding collapsed nodes
        self.collapsed = []  # nodes that are collapsed together
        self.nodeboxes = []  # node and collapsed boxes
        self.node_dxs = [[]]  # lists of nodes dx (to find the max)
        self.bdy_dys = [[]]  # lists of branching dys and total dys

        point = self.xmin, self.ymin
        for it in self.tree.walk():
            graphics = []
            if it.first_visit:
                point = self.on_first_visit(point, it, graphics)
            else:
                point = self.on_last_visit(point, it, graphics)
            yield from graphics

        if self.outline:
            yield from self.get_outline()

        if self.panel == 0:  # draw in preorder the boxes we found in postorder
            yield from self.nodeboxes[::-1]  # (so they overlap nicely)

    def on_first_visit(self, point, it, graphics):
        "Update list of graphics to draw and return new position"
        box_node = make_box(point, self.node_size(it.node))
        x, y = point

        if not self.in_viewport(box_node):
            self.bdy_dys[-1].append( (box_node.dy / 2, box_node.dy) )
            it.descend = False  # skip children
            return x, y + box_node.dy

        if self.is_small(box_node):
            self.node_dxs[-1].append(box_node.dx)
            self.collapsed.append(it.node)
            self.outline = stack(self.outline, box_node)
            it.descend = False  # skip children
            return x, y + box_node.dy

        if self.outline:
            graphics += self.get_outline()

        self.bdy_dys.append([])

        dx, dy = self.content_size(it.node)
        if it.node.is_leaf:
            return self.on_last_visit((x + dx, y + dy), it, graphics)
        else:
            self.node_dxs.append([])
            return x + dx, y

    def on_last_visit(self, point, it, graphics):
        "Update list of graphics to draw and return new position"
        if self.outline:
            graphics += self.get_outline()

        x_after, y_after = point
        dx, dy = self.content_size(it.node)
        x_before, y_before = x_after - dx, y_after - dy

        content_graphics = list(self.draw_content(it.node, (x_before, y_before)))
        graphics += content_graphics

        ndx = (drawn_size(content_graphics, self.get_box).dx if it.node.is_leaf
                else (dx + max(self.node_dxs.pop() or [0])))
        self.node_dxs[-1].append(ndx)

        box = Box(x_before, y_before, ndx, dy)
        result_of = [text for text,(results,_) in self.searches.items()
                        if it.node in results]
        self.nodeboxes += self.draw_nodebox(it.node, it.node_id, box, result_of)

        return x_before, y_after

    def draw_content(self, node, point):
        "Yield the node content's graphic elements"
        x, y = point
        dx, dy = self.content_size(node)

        if not self.in_viewport(Box(x, y, dx, dy)):
            return

        # Find branching dy of first child (bdy0), last (bdy1), and self (bdy).
        bdy_dys = self.bdy_dys.pop()  # bdy_dys[i] == (bdy, dy)
        bdy0 = bdy1 = dy / 2  # branching dys of the first and last children
        if bdy_dys:
            bdy0 = bdy_dys[0][0]
            bdy1 = sum(bdy_dy[1] for bdy_dy in bdy_dys[:-1]) + bdy_dys[-1][0]
        bdy = (bdy0 + bdy1) / 2  # this node's branching dy
        self.bdy_dys[-1].append( (bdy, dy) )

        # Draw the branch line ("lengthline") and a line spanning all children.
        if self.panel == 0:
            if dx > 0:
                parent_of = [text for text,(_,parents) in self.searches.items()
                                if node in parents]
                yield from self.draw_lengthline((x, y + bdy), (x + dx, y + bdy),
                                                parent_of)

            if bdy0 != bdy1:
                yield from self.draw_childrenline((x + dx, y + bdy0),
                                                  (x + dx, y + bdy1))

        yield from self.draw_node(node, point, bdy)

    def get_outline(self):
        "Yield the outline representation"
        result_of = [text for text,(results,parents) in self.searches.items()
            if any(node in results or node in parents for node in self.collapsed)]

        graphics = [draw_outline(self.outline)] if self.panel == 0 else []

        graphics += self.draw_collapsed()
        self.collapsed = []

        self.bdy_dys[-1].append( (self.outline.dy / 2, self.outline.dy) )

        ndx = drawn_size(graphics, self.get_box).dx
        self.node_dxs[-1].append(ndx)

        box = draw_nodebox(self.flush_outline(ndx), '(collapsed)', {}, [], result_of)
        self.nodeboxes.append(box)

        yield from graphics

    def flush_outline(self, minimum_dx=0):
        "Return box outlining the collapsed nodes and reset the current outline"
        x, y, dx, dy = self.outline
        self.outline = None
        return Box(x, y, max(dx, minimum_dx), dy)

    def dx_fitting_texts(self, texts, dy):
        "Return a dx wide enough on the screen to fit all texts in the given dy"
        zx, zy = self.zoom
        dy_char = zy * dy / len(texts)  # height of a char, in screen units
        dx_char = dy_char / 1.5  # approximate width of a char
        max_len = max(len(t) for t in texts)  # number of chars of the longest
        return max_len * dx_char / zx  # in tree units

    # These are the 2 functions that the user overloads to choose what to draw
    # and how when representing a node and a group of collapsed nodes:

    def draw_node(self, node, point, bdy):  # bdy: branch dy (height)
        "Yield graphic elements to draw the contents of the node"
        yield from []  # only drawn if any of the node's content is visible

    def draw_collapsed(self):
        "Yield graphic elements to draw the list of nodes in self.collapsed"
        yield from []  # they are always drawn (only visible nodes can collapse)
        # Uses self.collapsed and self.outline to extract and place info.



class DrawerRect(Drawer):
    "Minimal functional drawer for a rectangular representation"

    TYPE = 'rect'

    def in_viewport(self, box):
        if not self.viewport:
            return True

        if self.panel == 0:
            return intersects_box(self.viewport, box)
        else:
            return intersects_segment(get_ys(self.viewport), get_ys(box))

    def node_size(self, node):
        "Return the size of a node (its content and its children)"
        return Size(node.size[0], node.size[1])

    def content_size(self, node):
        "Return the size of the node's content"
        return Size(abs(node.length), node.size[1])

    def children_size(self, node):
        "Return the size of the node's children"
        return Size(node.size[0] - abs(node.length), node.size[1])

    def is_small(self, box):
        zx, zy = self.zoom
        return box.dy * zy < self.MIN_SIZE

    def get_box(self, element):
        return get_rect(element, self.zoom)

    def draw_lengthline(self, p1, p2, parent_of):
        "Yield a line representing a length"
        yield draw_line(p1, p2, '', parent_of)

    def draw_childrenline(self, p1, p2):
        "Yield a line spanning children that starts at p1 and ends at p2"
        yield draw_line(p1, p2)

    def draw_nodebox(self, node, node_id, box, result_of):
        yield draw_nodebox(box, node.name, node.properties, node_id, result_of)



class DrawerCirc(Drawer):
    "Minimal functional drawer for a circular representation"

    TYPE = 'circ'

    def __init__(self, tree, viewport=None, panel=0, zoom=(1, 1),
                 limits=None, searches=None):
        super().__init__(tree, viewport, panel, zoom, limits, searches)

        assert self.zoom[0] == self.zoom[1], 'zoom must be equal in x and y'

        if not limits:
            self.ymin, self.ymax = -pi, pi

        self.dy2da = (self.ymax - self.ymin) / self.tree.size[1]

    def in_viewport(self, box):
        if not self.viewport:
            return True

        if self.panel == 0:
            return (intersects_box(self.viewport, circumrect(box)) and
                    intersects_segment((-pi, +pi), get_ys(box)))
        else:
            return intersects_segment(get_ys(circumasec(self.viewport)), get_ys(box))

    def flush_outline(self, minimum_dr=0):
        "Return box outlining the collapsed nodes"
        r, a, dr, da = super().flush_outline(minimum_dr)
        a1, a2 = clip_angles(a, a + da)
        return Box(r, a1, dr, a2 - a1)

    def node_size(self, node):
        "Return the size of a node (its content and its children)"
        return Size(node.size[0], node.size[1] * self.dy2da)

    def content_size(self, node):
        "Return the size of the node's content"
        return Size(abs(node.length), node.size[1] * self.dy2da)

    def children_size(self, node):
        "Return the size of the node's children"
        return Size(node.size[0] - abs(node.length), node.size[1] * self.dy2da)

    def is_small(self, box):
        z = self.zoom[0]  # zx == zy in this drawer
        r, a, dr, da = box
        return (r + dr) * da * z < self.MIN_SIZE

    def get_box(self, element):
        return get_asec(element, self.zoom)

    def draw_lengthline(self, p1, p2, parent_of):
        "Yield a line representing a length"
        if -pi <= p1[1] < pi:  # NOTE: the angles p1[1] and p2[1] are equal
            yield draw_line(cartesian(p1), cartesian(p2), '', parent_of)

    def draw_childrenline(self, p1, p2):
        "Yield an arc spanning children that starts at p1 and ends at p2"
        (r1, a1), (r2, a2) = p1, p2
        a1, a2 = clip_angles(a1, a2)
        if a1 < a2:
            is_large = a2 - a1 > pi
            yield draw_arc(cartesian((r1, a1)), cartesian((r2, a2)), is_large)

    def draw_nodebox(self, node, node_id, box, result_of):
        r, a, dr, da = box
        a1, a2 = clip_angles(a, a + da)
        if a1 < a2:
            yield draw_nodebox(Box(r, a1, dr, a2 - a1),
                               node.name, node.properties, node_id, result_of)


def clip_angles(double a1, double a2):
    "Return the angles such that a1 to a2 extend at maximum from -pi to pi"
    EPSILON = 1e-8  # without it, p1 can be == p2 and svg arcs are not drawn
    return max(-pi + EPSILON, a1), min(pi - EPSILON, a2)


def cartesian((double, double) point):
    r, a = point
    return r * cos(a), r * sin(a)


def polar((double, double) point):
    x, y = point
    return sqrt(x*x + y*y), atan2(y, x)


def is_good_angle_interval(a1, a2):
    EPSILON = 1e-12  # without it, rounding can fake a2 > pi
    return -pi <= a1 < a2 < pi + EPSILON


def draw_rect_leaf_names(drawer, node, point):
    if not node.is_leaf or not node.name:
        return

    x, y = point
    dx, dy = drawer.content_size(node)

    x_text = (x + dx) if drawer.panel == 0 else drawer.xmin
    dx_fit = drawer.dx_fitting_texts([node.name], dy)
    box = Box(x_text, y, dx_fit, dy)

    yield draw_text(box, (0, 0.5), node.name, 'name')


def draw_circ_leaf_names(drawer, node, point):
    if not node.is_leaf or not node.name:
        return

    r, a = point
    dr, da = drawer.content_size(node)

    if is_good_angle_interval(a, a + da) and r + dr > 0:
        r_text = (r + dr) if drawer.panel == 0 else drawer.xmin
        dr_fit = drawer.dx_fitting_texts([node.name], (r + dr) * da)
        box = Box(r_text, a, dr_fit, da)
        yield draw_text(box, (0, 0.5), node.name, 'name')


def draw_rect_lengths(drawer, node, point, bdy):
    if node.length <= 0:
        return

    x, y = point
    dx, dy = drawer.content_size(node)
    zx, zy = drawer.zoom

    text = '%.2g' % node.length

    box = Box(x, y, dx, bdy)
    if box.dx * zx > drawer.MIN_SIZE and box.dy * zy > drawer.MIN_SIZE:
        yield draw_text(box, (0, 1), text, 'length')


def draw_circ_lengths(drawer, node, point, bda):
    if node.length <= 0:
        return

    r, a = point
    dr, da = drawer.content_size(node)
    z = drawer.zoom[0]  # zx == zy

    if is_good_angle_interval(a, a + da):
        text = '%.2g' % node.length

        box = Box(r, a, dr, bda)
        if dr * z > drawer.MIN_SIZE and r * bda * z > drawer.MIN_SIZE:
            yield draw_text(box, (0, 1), text, 'length')


def draw_rect_collapsed_names(drawer):
    x, y, dx, dy = drawer.outline

    names = [first_name(node) for node in drawer.collapsed]
    if all(name == '' for name in names):
        return

    texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])

    x_text = (x + dx) if drawer.panel == 0 else drawer.xmin
    dx_fit = drawer.dx_fitting_texts(texts, dy)
    box = Box(x_text, y, dx_fit, dy)

    yield from draw_texts(box, (0, 0.5), texts, 'name')


def draw_circ_collapsed_names(drawer):
    r, a, dr, da = drawer.outline
    if not (-pi <= a <= pi and -pi <= a + da <= pi):
        return

    names = [first_name(node) for node in drawer.collapsed]
    if all(name == '' for name in names):
        return

    texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])

    r_text = (r + dr) if drawer.panel == 0 else drawer.xmin
    dr_fit = drawer.dx_fitting_texts(texts, (r + dr) * da)
    box = Box(r_text, a, dr_fit, da)

    yield from draw_texts(box, (0, 0.5), texts, 'name')


class DrawerRectFull(DrawerRect):
    def draw_node(self, node, point, bdy):
        yield from draw_rect_leaf_names(self, node, point)
        yield from draw_rect_lengths(self, node, point, bdy)

    def draw_collapsed(self):
        yield from draw_rect_collapsed_names(self)


class DrawerCircFull(DrawerCirc):
    def draw_node(self, node, point, bdy):
        yield from draw_circ_leaf_names(self, node, point)
        yield from draw_circ_lengths(self, node, point, bdy)

    def draw_collapsed(self):
        yield from draw_circ_collapsed_names(self)


class DrawerAlignNames(DrawerRect):
    NPANELS = 2

    def draw_node(self, node, point, bdy):
        if self.panel == 0:
            yield from draw_rect_lengths(self, node, point, bdy)

            if node.is_leaf and self.viewport:
                x, y = point
                dx, dy = self.content_size(node)
                p1 = (x + dx, y + dy/2)
                p2 = (self.viewport.x + self.viewport.dx, y + dy/2)
                yield draw_line(p1, p2, 'dotted')
        elif self.panel == 1:
            yield from draw_rect_leaf_names(self, node, point)

    def draw_collapsed(self):
        names = [first_name(node) for node in self.collapsed]
        if all(name == '' for name in names):
            return

        if self.panel == 0:
            if self.viewport:
                x, y, dx, dy = self.outline
                p1 = (x + dx, y + dy/2)
                p2 = (self.viewport.x + self.viewport.dx, y + dy/2)
                yield draw_line(p1, p2, 'dotted')
        elif self.panel == 1:
            yield from draw_rect_collapsed_names(self)


class DrawerCircAlignNames(DrawerCirc):
    NPANELS = 2

    def draw_node(self, node, point, bdy):
        if self.panel == 0:
            yield from draw_circ_lengths(self, node, point, bdy)

            if node.is_leaf and self.viewport:
                r, a = point
                dr, da = self.content_size(node)
                p1 = (r + dr, a + da/2)
                p2 = (self.xmin + self.tree.size[0], a + da/2)
                yield draw_line(cartesian(p1), cartesian(p2), 'dotted')
        elif self.panel == 1:
            yield from draw_circ_leaf_names(self, node, point)

    def draw_collapsed(self):
        names = [first_name(node) for node in self.collapsed]
        if all(name == '' for name in names):
            return

        if self.panel == 0:
            if self.viewport:
                r, a, dr, da = self.outline
                p1 = (r + dr, a + da/2)
                p2 = (self.xmin + self.tree.size[0], a + da/2)
                yield draw_line(cartesian(p1), cartesian(p2), 'dotted')
        elif self.panel == 1:
            yield from draw_circ_collapsed_names(self)


# NOTE: The next two drawers (DrawerAlignHeatMap and DrawerCircAlignHeatMap)
#   are only there as an example for how to represent gene array data and so on
#   with heatmaps, but not really useful now (as opposed to the previous ones!).

class DrawerAlignHeatMap(DrawerRect):
    NPANELS = 2

    def draw_node(self, node, point, bdy):
        if self.panel == 0:
            yield from draw_rect_leaf_names(self, node, point)
            yield from draw_rect_lengths(self, node, point, bdy)
        elif self.panel == 1 and node.is_leaf:
            x, y = point
            dx, dy = self.content_size(node)
            random.seed(node.name)
            array = [random.randint(1, 360) for i in range(300)]
            yield draw_array(Box(0, y, 600, dy), array)

    def draw_collapsed(self):
        if self.panel == 0:
            yield from draw_rect_collapsed_names(self)
        elif self.panel == 1:
            x, y, dx, dy = self.outline
            text = ''.join(first_name(node) for node in self.collapsed)
            random.seed(text)
            array = [random.randint(1, 360) for i in range(300)]
            yield draw_array(Box(0, y, 600, dy), array)


class DrawerCircAlignHeatMap(DrawerCirc):
    NPANELS = 2

    def draw_node(self, node, point, bdy):
        if self.panel == 0:
            yield from draw_circ_leaf_names(self, node, point)
            yield from draw_circ_lengths(self, node, point, bdy)
        elif self.panel == 1 and node.is_leaf:
            r, a = point
            dr, da = self.content_size(node)
            random.seed(node.name)
            array = [random.randint(1, 360) for i in range(50)]
            box = Box(1.5 * self.xmin, a, 20 * self.tree.size[0], da)
            yield draw_array(box, array)

    def draw_collapsed(self):
        if self.panel == 0:
            yield from draw_circ_collapsed_names(self)
        elif self.panel == 1:
            r, a, dr, da = self.outline
            text = ''.join(first_name(node) for node in self.collapsed)
            random.seed(text)
            array = [random.randint(1, 360) for i in range(50)]
            box = Box(1.5 * self.xmin, a, 20 * self.tree.size[0], da)
            yield draw_array(box, array)


def get_drawers():
    return [
        DrawerRect, DrawerCirc,
        DrawerRectFull, DrawerCircFull,
        DrawerAlignNames, DrawerCircAlignNames,
        DrawerAlignHeatMap, DrawerCircAlignHeatMap]


def first_name(tree):
    "Return the name of the first node that has a name"
    return next((node.name for node in tree if node.name), '')


def draw_texts(box, anchor, texts, text_type):
    "Yield texts so they fit in the box"
    dy = box.dy / len(texts)
    y = box.y
    for text in texts:
        yield draw_text(Box(box.x, y, box.dx, dy), anchor, text, text_type)
        y += dy


# Basic drawing elements.

def draw_nodebox(box, name='', properties=None, node_id=None, result_of=None):
    return ['nodebox', box, name, properties or {}, node_id or [], result_of or []]

def draw_outline(box):
    return ['outline', box]

def draw_line(p1, p2, line_type='', parent_of=None):
    return ['line', p1, p2, line_type, parent_of or []]

def draw_arc(p1, p2, large=False, arc_type=''):
    return ['arc', p1, p2, int(large), arc_type]

def draw_text(box, anchor, text, text_type=''):
    return ['text', box, anchor, text, text_type]

def draw_array(box, a):
    return ['array', box, a]


# Box-related functions.

def make_box(point, size):
    x, y = point
    dx, dy = size
    return Box(x, y, dx, dy)

def get_xs(box):
    x, _, dx, _ = box
    return x, x + dx

def get_ys(box):
    _, y, _, dy = box
    return y, y + dy


def get_rect(element, zoom):
    "Return the rectangle that contains the given graphic element"
    eid = element[0]
    if eid in ['nodebox', 'outline', 'array', 'text']:
        return element[1]
    elif eid in ['line', 'arc']:
        (x1, y1), (x2, y2) = element[1], element[2]
        return Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    else:
        raise ValueError(f'unrecognized element: {element!r}')


def get_asec(element, zoom):
    "Return the annular sector that contains the given graphic element"
    eid = element[0]
    if eid in ['nodebox', 'outline', 'array', 'text']:
        return element[1]
    elif eid in ['line', 'arc']:
        (x1, y1), (x2, y2) = element[1], element[2]
        rect = Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        return circumasec(rect)
    else:
        raise ValueError(f'unrecognized element: {element!r}')


def drawn_size(elements, get_box):
    "Return the size of a box containing all the elements"
    # The type of size will depend on the kind of boxes that are returned by
    # get_box() for the elements. It is width and height for boxes that are
    # rectangles, and dr and da for boxes that are annular sectors.
    cdef double x, y, dx, dy, x_min, x_max, y_min, y_max

    if not elements:
        return Size(0, 0)

    x, y, dx, dy = get_box(elements[0])
    x_min, x_max = x, x + dx
    y_min, y_max = y, y + dy

    for element in elements[1:]:
        x, y, dx, dy = get_box(element)
        x_min, x_max = min(x_min, x), max(x_max, x + dx)
        y_min, y_max = min(y_min, y), max(y_max, y + dy)

    return Size(x_max - x_min, y_max - y_min)


def intersects_box(b1, b2):
    "Return True if the boxes b1 and b2 (of the same kind) intersect"
    return (intersects_segment(get_xs(b1), get_xs(b2)) and
            intersects_segment(get_ys(b1), get_ys(b2)))


def intersects_segment(s1, s2):
    "Return True if the segments s1 and s2 intersect"
    s1min, s1max = s1
    s2min, s2max = s2
    return s1min <= s2max and s2min <= s1max


def stack(b1, b2):
    "Return the box resulting from stacking boxes b1 and b2"
    if not b1:
        return b2
    else:
        x, y, dx1, dy1 = b1
        _, _, dx2, dy2 = b2
        return Box(x, y, max(dx1, dx2), dy1 + dy2)


def circumrect(asec):
    "Return the rectangle that circumscribes the given annular sector"
    cdef double rmin, amin, dr, da
    if asec is None:
        return None

    rmin, amin, dr, da = asec
    rmax, amax = rmin + dr, amin + da

    points = [(rmin, amin), (rmin, amax), (rmax, amin), (rmax, amax)]
    xs = [r * cos(a) for r,a in points]
    ys = [r * sin(a) for r,a in points]
    xmin, ymin = min(xs), min(ys)
    xmax, ymax = max(xs), max(ys)

    if amin < -pi/2 < amax:  # asec traverses the -y axis
        ymin = -rmax
    if amin < 0 < amax:  # asec traverses the +x axis
        xmax = rmax
    if amin < pi/2 < amax:  # asec traverses the +y axis
        ymax = rmax
    # NOTE: the annular sectors we consider never traverse the -x axis.

    return Box(xmin, ymin, xmax - xmin, ymax - ymin)


def circumasec(rect):
    "Return the annular sector that circumscribes the given rectangle"
    cdef double x, y, dx, dy
    if rect is None:
        return None
    x, y, dx, dy = rect
    points = [(x, y), (x, y+dy), (x+dx, y), (x+dx, y+dy)]
    radius2 = [x*x + y*y for x,y in points]
    if x <= 0 and x+dx >= 0 and y <= 0 and y+dy >= 0:
        return Box(0, -pi, sqrt(max(radius2)), 2*pi)
    else:
        angles = [atan2(y, x) for x,y in points]
        rmin, amin = sqrt(min(radius2)), min(angles)
        return Box(rmin, amin, sqrt(max(radius2)) - rmin, max(angles) - amin)
