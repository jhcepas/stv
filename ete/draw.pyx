"""
Classes and functions for drawing a tree.
"""

from math import sin, cos, pi, sqrt, atan2
from collections import namedtuple

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

        self.outline = None

    def update_outline(self, box):
        "Update the current outline and yield a graphic box if appropriate"
        if not self.outline:
            self.outline = box
        else:
            stacked_box = stack(self.outline, box)
            if stacked_box:
                self.outline = stacked_box
            else:
                yield self.draw_outline(self.outline)
                self.outline = box

    def draw(self):
        "Yield graphic elements to draw the tree"
        node_dxs = [[]]
        nodeboxes = []  # for boxes containing the nodes (filled in postorder)

        x, y = self.xmin, self.ymin
        for node, node_id, first in self.tree.walk():
            dx, dy = self.content_size(node)
            if first:  # first time we visit this node
                gs, draw_children = self.get_content(node, (x, y))
                yield from gs

                if node.is_leaf or not draw_children:
                    ndx = max(self.node_size(node).dx,
                        drawn_size(gs, self.get_box).dx)
                    node_dxs[-1].append(ndx)
                    nodeboxes.append( (node, node_id[:], Box(x, y, ndx, dy)) )
                    y += dy
                else:
                    node_dxs.append([])
                    x += dx

                if not draw_children:
                    node_id[:] = [None]  # mark for not following children
            else:  # last time we visit this node
                x -= dx
                ndx = dx + max(node_dxs.pop())
                if node_dxs:
                    node_dxs[-1].append(ndx)
                nodeboxes.append( (node, node_id, Box(x, y - dy, ndx, dy)) )

        if self.outline and not self.aligned:  # draw the last outline stacked
            yield self.draw_outline(self.outline)

        if not self.aligned:
            for node, node_id, box in nodeboxes[::-1]:
                yield self.draw_nodebox(node, node_id, box)

    def get_content(self, node, point):
        "Return list of content's graphic elements, and if children need drawing"
        # Both the node's box and its content's box start at the given point.
        box_node = make_box(point, self.node_size(node))

        if not self.in_viewport(box_node):  # don't draw & skip children
            return [], False

        if self.is_small(box_node):         # draw as collapsed & skip children
            return list(self.draw_collapsed(node, point)), False

        if self.aligned:
            return list(self.draw_content_align(node, point)), True

        x, y = point
        dx, dy = self.content_size(node)

        gs = []  # graphic elements to return
        if self.in_viewport(Box(x, y, dx, dy)):
            bh = self.bh(node)  # node's branching height (in the right units)
            gs.append(self.draw_lengthline((x, y + bh), (x + dx, y + bh)))
            if len(node.children) > 1:
                c0, c1 = node.children[0], node.children[-1]
                bh0, bh1 = self.bh(c0), dy - self.node_size(c1).dy + self.bh(c1)
                gs.append(self.draw_childrenline((x + dx, y + bh0),
                                                 (x + dx, y + bh1)))
            gs += self.draw_content_inline(node, (x, y))
        gs += self.draw_content_float(node, (x, y))

        return gs, True

    def get_nodes(self, func):
        "Yield (node_id, box) of the nodes with func(node) == True"
        x, y = self.xmin, self.ymin
        for node, node_id, first in self.tree.walk():
            dx, dy = self.content_size(node)

            if first and func(node):
                yield node_id, make_box((x, y), self.node_size(node))

            if node.is_leaf:
                y += dy
            elif first:  # first time we visit this node
                x += dx
            else:  # last time we will visit this node
                x -= dx

    def get_node_at(self, point):
        "Return the node whose content area contains the given point"
        x, y = self.xmin, self.ymin
        for node, node_id, _ in self.tree.walk():
            ndx, ndy = self.node_size(node)
            cdx, cdy = self.content_size(node)
            if not is_inside(point, Box(x, y, ndx, ndy)):
                node_id[:] = [None]  # skip walking over the node's children
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

    def draw_collapsed(self, node, point):
        "Yield graphic elements to draw a collapsed node"
        if self.aligned:
            yield from []
        else:
            yield from self.update_outline(make_box(point, self.node_size(node)))



class DrawerRect(Drawer):
    "Minimal functional drawer for a rectangular representation"

    def in_viewport(self, box):
        return intersects(self.viewport, box)

    def draw_outline(self, box):
        return draw_box('r', box, 'outline')

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
        "Return a line representing a length"
        return draw_line(p1, p2)

    def draw_childrenline(self, p1, p2):
        "Return a line spanning children that starts at p1 and ends at p2"
        return draw_line(p1, p2)

    def draw_nodebox(self, node, node_id, box):
        return draw_box('r', box, 'node', node.name, node.properties, node_id)



class DrawerCirc(Drawer):
    "Minimal functional drawer for a circular representation"

    def __init__(self, tree, viewport=None, zoom=(1, 1), aligned=False, limits=None):
        super().__init__(tree, viewport, zoom, aligned, limits)

        if not limits:
            self.ymin, self.ymax = -pi, pi

        self.y2a = (self.ymax - self.ymin) / self.tree.size[1]

        self.circumasec_viewport = circumasec(self.viewport)

    def in_viewport(self, box):
        return (intersects(self.circumasec_viewport, box) or
                intersects(self.viewport, circumrect(box)))

    def draw_outline(self, box):
        return draw_box('s', box, 'outline')

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
        "Return a line representing a length"
        return draw_line(cartesian(*p1), cartesian(*p2))

    def draw_childrenline(self, p1, p2):
        "Return a line spanning children that starts at p1 and ends at p2"
        a1, a2 = p1[1], p2[1]  # angles
        return draw_arc(cartesian(*p1), cartesian(*p2), a2 - a1 > pi)

    def draw_nodebox(self, node, node_id, box):
        return draw_box('s', box, 'node', node.name, node.properties, node_id)


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
            p_after_content = (x + w, y + h / 1.3)
            fs = h / 1.4
            yield draw_text(node.name, p_after_content, fs, 'name')


class DrawerCircLeafNames(DrawerCirc):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if node.is_leaf:
            r, a = point
            dr, da = self.content_size(node)
            p_after_content = cartesian(r + dr, a + da / 1.3)
            fs = (r + dr) * da / 1.4
            yield draw_text(node.name, p_after_content, fs, 'name')


class DrawerLengths(DrawerRect):
    "With labels on the lengths"

    def draw_content_inline(self, node, point):
        if node.length >= 0:
            x, y = point
            w, h = self.content_size(node)
            zx, zy = self.zoom
            text = '%.2g' % node.length
            fs = min(zy * node.bh, zx * 1.5 * w / len(text)) / zy
            g_text = draw_text(text, (x, y + node.bh), fs, 'length')

            if zy * h > 1:  # NOTE: we may want to change this, but it's tricky
                yield g_text
            else:
                pass  # TODO: something like  yield draw_box(get_box(g_text))


class DrawerCircLengths(DrawerCirc):
    "With labels on the lengths"

    def draw_content_inline(self, node, point):
        if node.length >= 0:
            r, a = point
            dr, da = self.content_size(node)
            zx, zy = self.zoom
            text = '%.2g' % node.length
            fs = min(zy * (r + dr) * self.bh(node), zx * 1.5 * dr / len(text)) / zy
            g_text = draw_text(text, cartesian(r, a + self.bh(node)), fs, 'length')

            if zy * da > 1:  # NOTE: we may want to change this, but it's tricky
                yield g_text
            else:
                pass  # TODO: something like  yield draw_box(get_box(g_text))


class DrawerCollapsed(DrawerLeafNames):
    "With text on collapsed nodes"

    def draw_collapsed(self, node, point):
        x, y = point
        w, h = self.content_size(node)
        if self.aligned:
            if node.name:
                yield draw_text(node.name, (0, y + h / 1.5), h / 2, 'name')
        else:
            yield from self.update_outline(make_box(point, self.node_size(node)))
            if node.name:
                p_before_content = (x, y + h / 1.3)
                fs = h / 1.4
                yield draw_text(node.name, p_before_content, fs, 'name')


class DrawerCircCollapsed(DrawerCircLeafNames):
    "With text on collapsed nodes"

    def draw_collapsed(self, node, point):
        yield from self.update_outline(make_box(point, self.node_size(node)))
        if node.name:
            r, a = point
            dr, da = self.content_size(node)
            p_before_content = cartesian(r, a + da / 1.3)
            fs = r * da / 1.4
            yield draw_text(node.name, p_before_content, fs, 'name')


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
            yield draw_text(node.name, (0, y+h/1.5), h/2, 'name')


class DrawerAlignHeatMap(DrawerFull):
    "With an example heatmap as aligned content"

    def draw_content_align(self, node, point):
        if node.is_leaf:
            _, y = point
            w, h = self.content_size(node)
            zx, zy = self.zoom
            a = list(range(360))
            yield draw_array(Box(0, y + h/8, 100, h * 0.75), a)


def get_drawers():
    return [DrawerSimple, DrawerLeafNames, DrawerLengths, DrawerFull,
        DrawerCircSimple, DrawerCircLeafNames, DrawerCircLengths, DrawerCircFull,
        DrawerAlign, DrawerAlignHeatMap]


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
