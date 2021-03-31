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

    def __init__(self, tree, viewport=None, zoom=(1, 1), aligned=False, limits=None):
        self.tree = tree
        self.zoom = zoom
        self.aligned = aligned

        if not viewport or not aligned:
            self.viewport = viewport
        else:
            x, y, dx, dy = viewport
            self.viewport = Box(0, y, self.tree.size[0], dy)

        self.xmin, self.xmax, self.ymin, self.ymax = limits or (0, 0, 0, 0)

    def draw(self):
        "Yield graphic elements to draw the tree"
        self.outline = None  # box surrounding collapsed nodes
        self.collapsed = []  # nodes that are collapsed together
        self.boxes = []  # node and collapsed boxes (will be filled in postorder)
        self.node_dxs = [[]]  # lists of nodes dx (to find the max)

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

        if not self.aligned:  # draw in preorder the boxes we found in postorder
            yield from self.boxes[::-1]  # (so they overlap nicely)

    def on_first_visit(self, point, it, graphics):
        "Update list of graphics to draw and return new position"
        node = it.node  # shortcut
        box_node = make_box(point, self.node_size(node))
        x, y = point

        if not self.in_viewport(box_node):
            it.descend = False  # skip children
            return x, y + box_node.dy

        if self.is_small(box_node):
            self.node_dxs[-1].append(box_node.dx)
            self.collapsed.append(node)
            self.outline = stack(self.outline, box_node)
            it.descend = False  # skip children
            return x, y + box_node.dy

        if self.outline:
            graphics += self.get_outline()

        graphics += self.get_content(node, point)

        dx, dy = self.content_size(node)

        if node.is_leaf:
            ndx = drawn_size(graphics, self.get_box).dx
            self.node_dxs[-1].append(ndx)
            self.boxes += self.draw_nodebox(node, it.node_id, Box(x, y, ndx, dy))
            return x, y + dy
        else:
            self.node_dxs.append([])
            return x + dx, y

    def on_last_visit(self, point, it, graphics):
        "Update list of graphics to draw and return new position"
        # Last time we visit this node (who is internal and visible).
        if self.outline:
            graphics += self.get_outline()

        x_after, y_after = point
        dx, dy = self.content_size(it.node)
        x_before, y_before = x_after - dx, y_after - dy

        ndx = dx + max(self.node_dxs.pop() or [0])
        self.node_dxs[-1].append(ndx)

        box = Box(x_before, y_before, ndx, dy)
        self.boxes += self.draw_nodebox(it.node, it.node_id, box)

        return x_before, y_after

    def get_content(self, node, point):
        "Yield the node content's graphic elements"
        x, y = point
        dx, dy = self.content_size(node)

        if not self.aligned and self.in_viewport(Box(x, y, dx, dy)):
            bh = self.bh(node)  # node's branching height (in the right units)
            yield from self.draw_lengthline((x, y + bh), (x + dx, y + bh))

            if len(node.children) > 1:
                c0, c1 = node.children[0], node.children[-1]
                bh0, bh1 = self.bh(c0), dy - self.node_size(c1).dy + self.bh(c1)
                yield from self.draw_childrenline((x + dx, y + bh0),
                                                  (x + dx, y + bh1))

            yield from self.draw_content_inline(node, point)

        yield from self.draw_content_float(node, point)

    def get_outline(self):
        "Yield the outline representation"
        graphics = [] if self.aligned else [draw_cone(self.outline)]

        graphics += self.draw_collapsed()
        self.collapsed = []

        ndx = drawn_size(graphics, self.get_box).dx
        self.node_dxs[-1].append(ndx)

        box = draw_box(self.flush_outline(ndx), '(collapsed)')
        self.boxes.append(box)

        yield from graphics

    def flush_outline(self, minimum_dx=0):
        "Return box outlining the collapsed nodes and reset the current outline"
        x, y, dx, dy = self.outline
        self.outline = None
        return Box(x, y, max(dx, minimum_dx), dy)

    # These are functions useful for searches and for picking a node from
    # a point inside it.
    def get_nodes(self, func):
        "Yield (node_id, box) of the nodes with func(node) == True"
        x, y = self.xmin, self.ymin
        for it in self.tree.walk():
            node = it.node  # shortcut
            dx, dy = self.content_size(node)

            if it.first_visit and func(node):
                yield it.node_id, make_box((x, y), self.node_size(node))

            if node.is_leaf:
                y += dy
            elif it.first_visit:  # first time we visit this node
                x += dx
            else:  # last time we will visit this node
                x -= dx

    def get_node_at(self, point):
        "Return the node whose content area contains the given point"
        x, y = self.xmin, self.ymin
        for it in self.tree.walk():
            node = it.node  # shortcut
            ndx, ndy = self.node_size(node)
            cdx, cdy = self.content_size(node)
            if not is_inside(point, Box(x, y, ndx, ndy)):
                it.descend = False  # skip walking over the node's children
                y += ndy
            elif node.is_leaf or is_inside(point, Box(x, y, cdx, cdy)):
                return node
            else:
                x += cdx
        return None

    # These are the functions that the user would supply to decide how to
    # represent a node.
    def draw_content_inline(self, node, point):
        "Yield graphic elements to draw the inline contents of the node"
        yield from []

    def draw_content_float(self, node, point):
        "Yield graphic elements to draw the floated contents of the node"
        if self.aligned:
            yield from []
        else:
            yield from []

    def draw_collapsed(self):
        "Yield graphic elements to draw a collapsed node"
        # Can use self.outline and self.collapsed to extract and place info.
        if self.aligned:
            yield from []
        else:
            yield from []



class DrawerRect(Drawer):
    "Minimal functional drawer for a rectangular representation"

    def in_viewport(self, box):
        return intersects(self.viewport, box)

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
        return box.dy * self.zoom[1] < self.MIN_SIZE

    def bh(self, node):
        "Return branching height of the node (where its horizontal line is)"
        return node.bh

    def get_box(self, element):
        return get_rect(element, self.zoom)

    def draw_lengthline(self, p1, p2):
        "Yield a line representing a length"
        yield draw_line(p1, p2)

    def draw_childrenline(self, p1, p2):
        "Yield a line spanning children that starts at p1 and ends at p2"
        yield draw_line(p1, p2)

    def draw_nodebox(self, node, node_id, box):
        yield draw_box(box, node.name, node.properties, node_id)



class DrawerCirc(Drawer):
    "Minimal functional drawer for a circular representation"

    def __init__(self, tree, viewport=None, zoom=(1, 1), aligned=False, limits=None):
        super().__init__(tree, viewport, zoom, aligned, limits)

        if not limits:
            self.ymin, self.ymax = -pi, pi

        self.y2a = (self.ymax - self.ymin) / self.tree.size[1]

        self.circumasec_viewport = circumasec(self.viewport)

    def in_viewport(self, box):
        return ((intersects(self.circumasec_viewport, box) or
            intersects(self.viewport, circumrect(box))) and
            intersects(Box(0, -pi, self.node_size(self.tree).dx, 2*pi), box))

    def flush_outline(self, minimum_dr=0):
        "Return box outlining the collapsed nodes"
        r, a, dr, da = super().flush_outline(minimum_dr)
        a1, a2 = clip_angles(a, a + da)
        return Box(r, a1, dr, a2 - a1)

    def node_size(self, node):
        "Return the size of a node (its content and its children)"
        return Size(node.size[0], node.size[1] * self.y2a)

    def content_size(self, node):
        "Return the size of the node's content"
        return Size(abs(node.length), node.size[1] * self.y2a)

    def children_size(self, node):
        "Return the size of the node's children"
        return Size(node.size[0] - abs(node.length), node.size[1] * self.y2a)

    def is_small(self, box):
        return (box.x + box.dx) * box.dy * self.zoom[0] < self.MIN_SIZE

    def bh(self, node):
        "Return branching height of the node (where its radial line is)"
        return node.bh * self.y2a  # in the right angular units

    def get_box(self, element):
        return get_asec(element, self.zoom)

    def draw_lengthline(self, p1, p2):
        "Yield a line representing a length"
        if -pi <= p1[1] < pi:  # NOTE: the angles p1[1] and p2[1] are equal
            yield draw_line(cartesian(p1), cartesian(p2))

    def draw_childrenline(self, p1, p2):
        "Yield an arc spanning children that starts at p1 and ends at p2"
        (r1, a1), (r2, a2) = p1, p2
        a1, a2 = clip_angles(a1, a2)
        if a1 < a2:
            yield draw_arc(cartesian((r1, a1)), cartesian((r2, a2)), a2 - a1 > pi)

    def draw_nodebox(self, node, node_id, box):
        r, a, dr, da = box
        a1, a2 = clip_angles(a, a + da)
        if a1 < a2:
            yield draw_box(Box(r, a1, dr, a2 - a1),
                           node.name, node.properties, node_id)


def clip_angles(double a1, double a2):
    "Return the angles such that a1 to a2 extend at maximum from -pi to pi"
    EPSILON = 1e-8  # without it, p1 == p2 and svg arcs are not drawn
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


class DrawerSimple(DrawerRect):
    "Skeleton of the tree"
    pass


class DrawerCircSimple(DrawerCirc):
    "Skeleton of the tree"
    pass


class DrawerLeafNames(DrawerRect):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if not self.aligned and node.is_leaf:
            x, y = point
            dx, dy = self.content_size(node)

            p = (x + dx, y + dy/1.3)
            fs = dy/1.4
            yield draw_text(node.name, p, fs, 'name')


class DrawerCircLeafNames(DrawerCirc):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if not self.aligned and node.is_leaf:
            r, a = point
            dr, da = self.content_size(node)

            if is_good_angle_interval(a, a + da):
                p = cartesian((r + dr, a + da/1.3))
                fs = (r + dr) * da/1.4
                yield draw_text(node.name, p, fs, 'name')


class DrawerLengths(DrawerRect):
    "With labels on the lengths"

    def draw_content_inline(self, node, point):
        if node.length >= 0:
            x, y = point
            dx, dy = self.content_size(node)
            zx, zy = self.zoom

            text = '%.2g' % node.length
            p = (x, y + node.bh)
            fs = min(node.bh, zx/zy * 1.5 * dx / len(text))
            if fs * zy > self.MIN_SIZE:
                yield draw_text(text, p, fs, 'length')


class DrawerCircLengths(DrawerCirc):
    "With labels on the lengths"

    def draw_content_inline(self, node, point):
        if node.length >= 0:
            r, a = point
            dr, da = self.content_size(node)
            zx, zy = self.zoom

            if is_good_angle_interval(a, a + da):
                text = '%.2g' % node.length
                p = cartesian((r, a + self.bh(node)))
                fs = min((r + dr) * self.bh(node), zx/zy * 1.5 * dr / len(text))
                if fs * zy > self.MIN_SIZE:
                    yield draw_text(text, p, fs, 'length')


class DrawerCollapsed(DrawerLeafNames):
    "With text on collapsed nodes"

    def draw_collapsed(self):
        if self.aligned:
            return

        names = [first_name(node) for node in self.collapsed]
        if all(name == '' for name in names):
            return

        x, y, dx, dy = self.outline

        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])
        p = (x + dx, y + dy/1.1)
        fs = dy/1.2
        yield from draw_texts(texts, p, fs, 'name')


class DrawerCircCollapsed(DrawerCircLeafNames):
    "With text on collapsed nodes"

    def draw_collapsed(self):
        if self.aligned:
            return

        r, a, dr, da = self.outline
        if not (-pi <= a <= pi and -pi <= a + da <= pi):
            return

        names = [first_name(node) for node in self.collapsed]
        if all(name == '' for name in names):
            return

        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])
        p = (r + dr, a + da/1.1)
        fs = (r + dr) * da/1.2

        # TODO: mix the code below properly with draw_texts().
        r, a = p
        alpha = 0.2  # space between texts, as a fraction of the font size
        font_size = fs / (len(texts) + (len(texts) - 1) * alpha)
        da = font_size * (1 + alpha) / r if r > 0 else 2*pi
        for text in texts[::-1]:
            yield draw_text(text, cartesian((r, a)), font_size, 'name')
            a -= da


class DrawerFull(DrawerCollapsed, DrawerLengths):
    "With names on leaf nodes and labels on the lengths"
    pass


class DrawerCircFull(DrawerCircCollapsed, DrawerCircLengths):
    "With names on leaf nodes and labels on the lengths"
    pass


class DrawerAlign(DrawerFull):
    "With aligned content"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree_dx = self.tree.size[0]

    def draw_content_float(self, node, point):
        if node.is_leaf:
            x, y = point
            dx, dy = self.content_size(node)

            if not self.aligned:
                p1 = (x + dx, y + dy/2)
                p2 = (2 * self.tree_dx, y + dy/2)
                yield draw_line(p1, p2, 'dotted')
            else:
                yield draw_text(node.name, (0, y + dy/1.5), dy/2, 'name')

    def draw_collapsed(self):
        names = [first_name(node) for node in self.collapsed]
        if all(name == '' for name in names):
            return

        x, y, dx, dy = self.outline

        if not self.aligned:
            p1 = (x + dx, y + dy/2)
            p2 = (2 * self.tree_dx, y + dy/2)
            yield draw_line(p1, p2, 'dotted')
        else:
            texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])
            p = (0, y + dy/1.1)
            fs = dy/1.2
            yield from draw_texts(texts, p, fs, 'name')



class DrawerAlignHeatMap(DrawerFull):
    "With an example heatmap as aligned content"

    def draw_content_float(self, node, point):
        yield from super().draw_content_float(node, point)

        if self.aligned and node.is_leaf:
            _, y = point
            dx, dy = self.content_size(node)
            zx, zy = self.zoom
            random.seed(node.name)
            a = [random.randint(1, 360) for i in range(100)]
            yield draw_array(Box(0, y + dy/8, 200, dy * 0.75), a)

    def draw_collapsed(self):
        names = [first_name(node) for node in self.collapsed]
        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])

        x, y, dx, dy = self.outline
        if self.aligned:
            zx, zy = self.zoom
            random.seed(str(texts))
            a = [random.randint(1, 360) for i in range(100)]
            yield draw_array(Box(0, y + dy/8, 200, dy * 0.75), a)
        else:
            if all(name == '' for name in names):
                return
            p = (x + dx, y + dy/1.1)
            fs = dy/1.2
            yield from draw_texts(texts, p, fs, 'name')


def get_drawers():
    return [DrawerSimple, DrawerLeafNames, DrawerLengths, DrawerFull,
        DrawerCircSimple, DrawerCircLeafNames, DrawerCircLengths, DrawerCircFull,
        DrawerAlign, DrawerAlignHeatMap]


def first_name(tree):
    "Return the name of the first node that has a name"
    return next((node.name for node in tree if node.name), '')


def draw_texts(texts, point, fs, text_type):
    "Yield texts from the bottom-left point, with total height fs"
    alpha = 0.2  # space between texts, as a fraction of the font size
    font_size = fs / (len(texts) + (len(texts) - 1) * alpha)
    dy = font_size * (1 + alpha)
    x, y = point
    for text in texts[::-1]:
        yield draw_text(text, (x, y), font_size, text_type)
        y -= dy


# Basic drawing elements.

def draw_box(box, name='', properties=None, node_id=None):
    return ['box', box, name, properties or {}, node_id or []]

def draw_cone(box):
    return ['cone', box]

def draw_line(p1, p2, line_type=''):
    return ['line', p1, p2, line_type]

def draw_arc(p1, p2, large=False, arc_type=''):
    return ['arc', p1, p2, int(large), arc_type]

def draw_text(text, point, fs, text_type=''):
    return ['text', text, point, fs, text_type]

def draw_array(box, a):
    return ['array', box, a]


# Box-related functions.

def make_box(point, size):
    x, y = point
    dx, dy = size
    return Box(x, y, dx, dy)


def get_rect(element, zoom):
    "Return the rectangle that contains the given graphic element"
    eid = element[0]
    if eid in ['box', 'cone', 'array']:
        return element[1]
    elif eid in ['line', 'arc']:
        (x1, y1), (x2, y2) = element[1], element[2]
        return Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    elif eid == 'text':
        _, text, (x, y), fs, _ = element
        zx, zy = zoom
        return Box(x, y - fs, zy/zx * fs / 1.5 * len(text), fs)
    else:
        raise ValueError(f'unrecognized element: {element!r}')


def get_asec(element, zoom):
    "Return the annular sector that contains the given graphic element"
    eid = element[0]
    if eid in ['box', 'cone', 'array']:
        return element[1]
    elif eid in ['line', 'arc']:
        (x1, y1), (x2, y2) = element[1], element[2]
        rect = Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        return circumasec(rect)
    elif eid == 'text':
        _, text, point, fs, _ = element
        r, a = polar(point)
        zx, zy = zoom
        dr = zy/zx * fs / 1.5 * len(text)
        da = fs/r if r > 0 else 2*pi
        return Box(r, a - da, dr, da)
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


def intersects(b1, b2):
    "Return True if the boxes b1 and b2 (of the same kind) intersect"
    cdef double x1min, x1max, x2min, x2max

    if b1 is None or b2 is None:
        return True  # the box "None" represents the full plane

    x1min, y1min, dx1, dy1 = b1
    x1max, y1max = x1min + dx1, y1min + dy1
    x2min, y2min, dx2, dy2 = b2
    x2max, y2max = x2min + dx2, y2min + dy2
    return ((x1min <= x2max and x2min <= x1max) and
            (y1min <= y2max and y2min <= y1max))


def is_inside(point, box):
    "Return True if point is inside the box"
    cdef double px, py, x, y, dx, dy
    if box is None:
        return True
    px, py = point
    x, y, dx, dy = box
    return (x <= px < x + dx) and (y <= py < y + dy)


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
    cdef double r, a, dr, da
    if asec is None:
        return None
    r, a, dr, da = asec
    points = [(r, a), (r, a+da), (r+dr, a), (r+dr, a+da)]
    xs = [r * cos(a) for r,a in points]
    ys = [r * sin(a) for r,a in points]
    xmin, ymin = min(xs), min(ys)
    return Box(xmin, ymin, max(xs) - xmin, max(ys) - ymin)


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
