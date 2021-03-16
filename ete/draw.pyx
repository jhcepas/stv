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

        self.outline = None  # will contain a box surrounding collapsed nodes
        self.collapsed = []  # will contain nodes that are collapsed together

    def update_collapsed(self, node, point):
        "Update collapsed nodes and outline, and yield graphics if appropriate"
        box = make_box(point, self.node_size(node))

        if not self.outline:
            self.outline = box
            self.collapsed = [node]
        else:
            stacked_box = stack(self.outline, box)
            if stacked_box:
                self.outline = stacked_box
                self.collapsed.append(node)
            else:
                if not self.aligned:
                    yield from self.draw_outline()
                yield from self.draw_collapsed()
                self.outline = box
                self.collapsed = [node]

    def draw(self):
        "Yield graphic elements to draw the tree"
        node_dxs = []  # in postorder, lists of nodes dx (to find the max)
        nodeboxes = []  # will contain the node boxes (filled in postorder)

        x, y = self.xmin, self.ymin
        for it in self.tree.walk():
            node = it.node  # shortcut
            dx, dy = self.content_size(node)
            if it.first_visit:
                box_node = make_box((x, y), self.node_size(node))

                if not self.in_viewport(box_node):
                    y += dy
                    it.descend = False  # skip children
                    continue

                if self.is_small(box_node):
                    if node_dxs:  # node_dxs is empty if the root node is small
                        node_dxs[-1].append(box_node.dx)
                    yield from self.update_collapsed(node, (x, y))
                    y += dy
                    it.descend = False  # skip children
                    continue

                gs = self.get_content(node, (x, y))
                yield from gs

                if node.is_leaf:
                    ndx = drawn_size(gs, self.get_box).dx
                    if node_dxs:
                        node_dxs[-1].append(ndx)
                    nodeboxes.append( (node, it.node_id, Box(x, y, ndx, dy)) )
                    y += dy
                else:
                    node_dxs.append([])
                    x += dx
            else:  # last time we visit this node (who is internal and visible)
                x -= dx
                ndx = dx + max(node_dxs.pop() or [0])
                if node_dxs:
                    node_dxs[-1].append(ndx)
                nodeboxes.append( (node, it.node_id, Box(x, y - dy, ndx, dy)) )

        if self.outline:  # draw the last collapsed nodes
            if not self.aligned:
                yield from self.draw_outline()
            yield from self.draw_collapsed()

        if not self.aligned:
            for node, node_id, box in nodeboxes[::-1]:
                yield from self.draw_nodebox(node, node_id, box)

    def get_content(self, node, point):
        "Return list of content's graphic elements"
        if self.aligned:
            return list(self.draw_content_align(node, point))

        x, y = point
        dx, dy = self.content_size(node)

        gs = []  # graphic elements to return
        if self.in_viewport(Box(x, y, dx, dy)):
            bh = self.bh(node)  # node's branching height (in the right units)
            gs += self.draw_lengthline((x, y + bh), (x + dx, y + bh))
            if len(node.children) > 1:
                c0, c1 = node.children[0], node.children[-1]
                bh0, bh1 = self.bh(c0), dy - self.node_size(c1).dy + self.bh(c1)
                gs += self.draw_childrenline((x + dx, y + bh0), (x + dx, y + bh1))
            gs += self.draw_content_inline(node, (x, y))
        gs += self.draw_content_float(node, (x, y))

        return gs

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
                y += cdy
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
        yield from []

    def draw_content_align(self, node, point):
        "Yield graphic elements to draw the aligned contents of the node"
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

    def draw_outline(self):
        yield draw_box('r', self.outline, 'outline')

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
        yield draw_box('r', box, 'node', node.name, node.properties, node_id)



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

    def draw_outline(self):
        r, a, dr, da = self.outline
        a1, a2 = clip_angles(a, a + da)
        if a1 is not None:
            yield draw_box('s', Box(r, a1, dr, a2 - a1), 'outline')

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
        if -pi <= p1[1] <= pi:  # NOTE: the angles p1[1] and p2[1] are equal
            yield draw_line(cartesian(*p1), cartesian(*p2))

    def draw_childrenline(self, p1, p2):
        "Yield an arc spanning children that starts at p1 and ends at p2"
        (r1, a1), (r2, a2) = p1, p2
        a1, a2 = clip_angles(a1, a2)
        if a1 is not None:
            yield draw_arc(cartesian(r1, a1), cartesian(r2, a2), a2 - a1 > pi)

    def draw_nodebox(self, node, node_id, box):
        r, a, dr, da = box
        a1, a2 = clip_angles(a, a + da)
        if a1 is not None:
            yield draw_box('s', Box(r, a1, dr, a2 - a1), 'node',
                           node.name, node.properties, node_id)


def clip_angles(double a1, double a2):
    "Return the angles such that a1 to a2 extend at maximum from -pi to pi"
    if (a1 < -pi and a2 < -pi) or (a1 > pi and a2 > pi):
        return None, None
    else:
        EPSILON = 1e-6  # NOTE: without it, p1 == p2 and svg arcs are not drawn
        return max(-pi + EPSILON, a1), min(pi - EPSILON, a2)


def cartesian(double r, double a):
    return r * cos(a), r * sin(a)


def polar(double x, double y):
    return sqrt(x*x + y*y), atan2(y, x)


class DrawerSimple(DrawerRect):
    "Skeleton of the tree"
    pass


class DrawerCircSimple(DrawerCirc):
    "Skeleton of the tree"
    pass


class DrawerLeafNames(DrawerRect):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if node.is_leaf:
            x, y = point
            w, h = self.content_size(node)

            p = (x + w, y + h/1.3)
            fs = h/1.4
            yield draw_text(node.name, p, fs, 'name')


class DrawerCircLeafNames(DrawerCirc):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if node.is_leaf:
            r, a = point
            dr, da = self.content_size(node)

            if -pi <= a <= pi and -pi <= a + da <= pi:
                p = cartesian(r + dr, a + da/1.3)
                fs = (r + dr) * da/1.4
                yield draw_text(node.name, p, fs, 'name')


class DrawerLengths(DrawerRect):
    "With labels on the lengths"

    def draw_content_inline(self, node, point):
        if node.length >= 0:
            x, y = point
            w, h = self.content_size(node)
            zx, zy = self.zoom

            text = '%.2g' % node.length
            p = (x, y + node.bh)
            fs = min(node.bh, zx/zy * 1.5 * w / len(text))
            yield draw_text(text, p, fs, 'length')


class DrawerCircLengths(DrawerCirc):
    "With labels on the lengths"

    def draw_content_inline(self, node, point):
        if node.length >= 0:
            r, a = point
            dr, da = self.content_size(node)
            zx, zy = self.zoom

            if -pi <= a <= pi and -pi <= a + da <= pi:
                text = '%.2g' % node.length
                p = cartesian(r, a + self.bh(node))
                fs = min((r + dr) * self.bh(node), zx/zy * 1.5 * dr / len(text))
                yield draw_text(text, p, fs, 'length')


class DrawerCollapsed(DrawerLeafNames):
    "With text on collapsed nodes"

    def draw_collapsed(self):
        names = [n.name for n in self.collapsed if n.name]
        if not names:
            return

        x, y, w, h = self.outline

        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])
        p = ((0 if self.aligned else x), y + h/1.1)
        fs = h/1.2
        yield from draw_texts(texts, p, fs, 'name')


class DrawerCircCollapsed(DrawerCircLeafNames):
    "With text on collapsed nodes"

    def draw_collapsed(self):
        r, a, dr, da = self.outline
        if not (-pi <= a <= pi and -pi <= a + da <= pi):
            return

        names = [n.name for n in self.collapsed if n.name]
        if not names:
            return

        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])
        p = (r, a + da/1.1)
        fs = r * da/1.2

        # TODO: mix the code below properly with draw_texts().
        r, a = p
        alpha = 0.2  # space between texts, as a fraction of the font size
        font_size = fs / (len(texts) + (len(texts) - 1) * alpha)
        da = font_size * (1 + alpha) / r
        for text in texts[::-1]:
            yield draw_text(text, cartesian(r, a), font_size, 'name')
            a -= da


class DrawerFull(DrawerCollapsed, DrawerLengths):
    "With names on leaf nodes and labels on the lengths"
    pass


class DrawerCircFull(DrawerCircCollapsed, DrawerCircLengths):
    "With names on leaf nodes and labels on the lengths"
    pass


class DrawerAlign(DrawerFull):
    "With aligned content"

    def draw_content_align(self, node, point):
        if node.is_leaf:
            x, y = point
            w, h = self.content_size(node)
            yield draw_text(node.name, (0, y + h/1.5), h/2, 'name')


class DrawerAlignHeatMap(DrawerFull):
    "With an example heatmap as aligned content"

    def draw_content_align(self, node, point):
        if node.is_leaf:
            _, y = point
            w, h = self.content_size(node)
            zx, zy = self.zoom
            random.seed(node.name)
            a = [random.randint(1, 360) for i in range(100)]
            yield draw_array(Box(0, y + h/8, 200, h * 0.75), a)

    def draw_collapsed(self):
        names = [n.name for n in self.collapsed if n.name]
        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])

        x, y, w, h = self.outline
        if self.aligned:
            zx, zy = self.zoom
            random.seed(str(texts))
            a = [random.randint(1, 360) for i in range(100)]
            yield draw_array(Box(0, y + h/8, 200, h * 0.75), a)
        else:
            if not names:
                return
            x, y, w, h = self.outline
            p = (x, y + h/1.1)
            fs = h/1.2
            yield from draw_texts(texts, p, fs, 'name')


def get_drawers():
    return [DrawerSimple, DrawerLeafNames, DrawerLengths, DrawerFull,
        DrawerCircSimple, DrawerCircLeafNames, DrawerCircLengths, DrawerCircFull,
        DrawerAlign, DrawerAlignHeatMap]


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

def draw_box(shape, box, box_type='', name='', properties=None, node_id=None):
    return [shape, box, box_type, name, properties or {}, node_id or []]

def draw_line(p1, p2):
    return ['l', p1, p2]

def draw_arc(p1, p2, large=False):
    return ['c', p1, p2, int(large)]

def draw_text(text, point, fs, text_type=''):
    return ['t', text, point, fs, text_type]

def draw_array(box, a):
    return ['a', box, a]


# Box-related functions.

def make_box(point, size):
    x, y = point
    dx, dy = size
    return Box(x, y, dx, dy)


def get_rect(element, zoom):
    "Return the rectangle that contains the given graphic element"
    eid = element[0]
    if eid == 'r':
        _, box, _, _, _, _ = element
        return box
    elif eid == 's':
        _, box, _, _, _, _ = element
        return circumrect(box)
    elif eid in ['l', 'c']:
        _, (x1, y1), (x2, y2) = element
        return Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    elif eid == 't':
        _, text, (x, y), fs, _ = element
        zx, zy = zoom
        return Box(x, y - fs, zy/zx * fs / 1.5 * len(text), fs)
    elif eid == 'a':
        _, box, _ = element
        return box
    else:
        raise ValueError(f'unrecognized element: {element!r}')


def get_asec(element, zoom):
    "Return the annular sector that contains the given graphic element"
    eid = element[0]
    if eid == 'r':
        _, box, _, _, _, _ = element
        return circumasec(box)
    elif eid == 's':
        _, box, _, _, _, _ = element
        return box
    elif eid in ['l', 'c']:
        _, (x1, y1), (x2, y2) = element
        rect = Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        return circumasec(rect)
    elif eid == 't':
        _, text, point, fs, _ = element
        r, a = polar(*point)
        zx, zy = zoom
        return Box(r, a - fs / r, zy/zx * fs / 1.5 * len(text), fs / r)
    elif eid == 'a':
        _, box, _ = element
        return box
    else:
        raise ValueError(f'unrecognized element: {element!r}')


def drawn_size(elements, get_box):
    "Return the size of a box containing all the elements"
    # The type of size will depend on the kind of boxes that are returned by
    # get_box() for the elements. It is width and height for boxes that are
    # rectangles, and dr and da for boxes that are annular sectors.
    cdef double x, y, dx, dy, x_min, x_max, y_min, y_max

    elements = [e for e in elements if not is_outline(e)]
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


def is_outline(element):
    return element[0] in ['r', 's'] and element[2] == 'outline'


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
    "Return the box containing boxes b1 and b2 stacked, or None if unstackable"
    if b1.x == b2.x and b1.y + b1.dy == b2.y:
        return Box(b1.x, b1.y, max(b1.dx, b2.dx), b1.dy + b2.dy)
    else:
        return None


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
    cdef double x, y, w, h
    if rect is None:
        return None
    x, y, w, h = rect
    points = [(x, y), (x, y+h), (x+w, y), (x+w, y+h)]
    radius2 = [x*x + y*y for x,y in points]
    if x <= 0 and x+w >= 0 and y <= 0 and y+h >= 0:
        return Box(0, -pi, sqrt(max(radius2)), 2*pi)
    else:
        angles = [atan2(y, x) for x,y in points]
        rmin, amin = sqrt(min(radius2)), min(angles)
        return Box(rmin, amin, sqrt(max(radius2)) - rmin, max(angles) - amin)
