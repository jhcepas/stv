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

    def __init__(self, tree, viewport=None, zoom=(1, 1),
                 aligned=False, limits=None, searches=None):
        self.tree = tree
        self.zoom = zoom
        self.aligned = aligned

        if viewport:
            x, y, dx, dy = viewport
            if not aligned:  # normal case
                self.viewport = Box(x, y, dx, dy)
            else:  # drawing for the aligned panel, so consider full tree width
                self.viewport = Box(0, y, self.tree.size[0], dy)
        else:
            self.viewport = None

        self.xmin, self.xmax, self.ymin, self.ymax = limits or (0, 0, 0, 0)

        self.searches = searches or {}  # looks like {text: (results, parents)}

    def draw(self):
        "Yield graphic elements to draw the tree"
        self.outline = None  # box surrounding collapsed nodes
        self.collapsed = []  # nodes that are collapsed together
        self.boxes = []  # node and collapsed boxes (will be filled in postorder)
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

        if not self.aligned:  # draw in preorder the boxes we found in postorder
            yield from self.boxes[::-1]  # (so they overlap nicely)

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
        self.boxes += self.draw_nodebox(it.node, it.node_id, box, result_of)

        return x_before, y_after

    def draw_content(self, node, point):
        "Yield the node content's graphic elements"
        x, y = point
        dx, dy = self.content_size(node)

        # Find branching dy of first child (bdy0), last (bdy1), and self (bdy).
        bdy_dys = self.bdy_dys.pop()  # bdy_dys[i] == (bdy, dy)
        bdy0 = bdy1 = dy / 2  # branching dys of the first and last children
        if bdy_dys:
            bdy0 = bdy_dys[0][0]
            bdy1 = sum(bdy_dy[1] for bdy_dy in bdy_dys[:-1]) + bdy_dys[-1][0]
        bdy = (bdy0 + bdy1) / 2  # this node's branching dy
        self.bdy_dys[-1].append( (bdy, dy) )

        # Draw line spanning content, line to children, and inline content.
        if not self.aligned and self.in_viewport(Box(x, y, dx, dy)):
            if dx > 0:
                parent_of = [text for text,(_,parents) in self.searches.items()
                                if node in parents]
                yield from self.draw_lengthline((x, y + bdy), (x + dx, y + bdy),
                                                parent_of)

            if bdy0 != bdy1:
                yield from self.draw_childrenline((x + dx, y + bdy0),
                                                  (x + dx, y + bdy1))

            yield from self.draw_content_inline(node, point, bdy)

        # Draw things that may be floating (typically to the right for leaves).
        yield from self.draw_content_float(node, point)

    def get_outline(self):
        "Yield the outline representation"
        result_of = [text for text,(results,parents) in self.searches.items()
            if any(node in results or node in parents for node in self.collapsed)]

        graphics = [draw_cone(self.outline)] if not self.aligned else []

        graphics += self.draw_collapsed()
        self.collapsed = []

        self.bdy_dys[-1].append( (self.outline.dy / 2, self.outline.dy) )

        ndx = drawn_size(graphics, self.get_box).dx
        self.node_dxs[-1].append(ndx)

        box = draw_box(self.flush_outline(ndx), '(collapsed)', {}, [], result_of)
        self.boxes.append(box)

        yield from graphics

    def flush_outline(self, minimum_dx=0):
        "Return box outlining the collapsed nodes and reset the current outline"
        x, y, dx, dy = self.outline
        self.outline = None
        return Box(x, y, max(dx, minimum_dx), dy)

    def dx_fitting_texts(self, texts, dy):
        "Return a dx wide enough on the screen to fit all texts in the given dy"
        zx, zy = self.zoom
        dy_char = zy * dy / len(texts)  # height of 1 char, in screen units
        dx_char = dy_char / 1.5  # approximate width of a char
        max_len = max(len(t) for t in texts)  # number of chars of the longest
        return max_len * dx_char / zx  # in tree units

    # These are the 3 functions that the user overloads to choose what to draw
    # and how when representing a node (or group of collapsed nodes):

    def draw_content_inline(self, node, point, bdy):  # bdy: branch dy (height)
        "Yield graphic elements to draw the inline contents of the node"
        yield from []  # graphics that go to the area inside the node
        # They are only drawn if any of the node's content is visible.
        # They never go to the aligned panel.

    def draw_content_float(self, node, point):
        "Yield graphic elements to draw the floated contents of the node"
        if self.aligned:
            yield from []  # graphics that go to the aligned panel
        else:
            yield from []  # graphics that go to the main area
        # They are drawn if any of the node (including all children) is visible.

    def draw_collapsed(self):
        "Yield graphic elements to draw the list of nodes in self.collapsed"
        # Uses self.collapsed and self.outline to extract and place info.
        if self.aligned:
            yield from []  # graphics that go to the aligned panel
        else:
            yield from []  # graphics that go to the main area
        # They are always drawn (only visible nodes can collapse).



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
        yield draw_box(box, node.name, node.properties, node_id, result_of)



class DrawerCirc(Drawer):
    "Minimal functional drawer for a circular representation"

    def __init__(self, tree, viewport=None, zoom=(1, 1),
                 aligned=False, limits=None, searches=None):
        super().__init__(tree, viewport, zoom, aligned, limits, searches)

        assert self.zoom[0] == self.zoom[1], 'zoom must be equal in x and y'

        if not limits:
            self.ymin, self.ymax = -pi, pi

        self.dy2da = (self.ymax - self.ymin) / self.tree.size[1]

    def in_viewport(self, box):
        return (intersects(self.viewport, circumrect(box)) and
            intersects(Box(0, -pi, self.node_size(self.tree).dx, 2*pi), box))

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
            yield draw_box(Box(r, a1, dr, a2 - a1),
                           node.name, node.properties, node_id, result_of)


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


class DrawerRectSimple(DrawerRect):
    "Skeleton of the tree"
    pass


class DrawerCircSimple(DrawerCirc):
    "Skeleton of the tree"
    pass


class DrawerRectLeafNames(DrawerRect):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if not self.aligned and node.is_leaf:
            x, y = point
            dx, dy = self.content_size(node)

            dx_fit = self.dx_fitting_texts([node.name], dy)
            box = Box(x + dx, y, dx_fit, dy)
            yield draw_text(box, (0, 0.5), node.name, 'name')


class DrawerCircLeafNames(DrawerCirc):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if not self.aligned and node.is_leaf:
            r, a = point
            dr, da = self.content_size(node)

            if is_good_angle_interval(a, a + da) and r + dr > 0:
                dr_fit = self.dx_fitting_texts([node.name], (r + dr) * da)
                box = Box(r + dr, a, dr_fit, da)
                yield draw_text(box, (0, 0.5), node.name, 'name')


class DrawerRectProperties(DrawerRect):
    "With labels on the properties (length, support)"

    def draw_content_inline(self, node, point, bdy):
        x, y = point
        dx, dy = self.content_size(node)
        zx, zy = self.zoom

        if node.length >= 0:
            text = '%.2g' % node.length
            box = Box(x, y, dx, bdy)
            if box.dx * zx > self.MIN_SIZE and box.dy * zy > self.MIN_SIZE:
                yield draw_text(box, (0, 1), text, 'length')

        support = node.properties.get('support', False)
        if support:
            text = '%.2g' % support
            box = Box(x, y + bdy, dx, dy - bdy)
            if box.dx * zx > self.MIN_SIZE and box.dy * zy > self.MIN_SIZE:
                yield draw_text(box, (0, 0), text, 'support')


class DrawerCircLengths(DrawerCirc):
    "With labels on the lengths"

    def draw_content_inline(self, node, point, bda):
        if node.length >= 0:
            r, a = point
            dr, da = self.content_size(node)
            z = self.zoom[0]  # zx == zy

            if is_good_angle_interval(a, a + da):
                text = '%.2g' % node.length
                box = Box(r, a, dr, bda)
                if dr * z > self.MIN_SIZE and r * bda * z > self.MIN_SIZE:
                    yield draw_text(box, (0, 1), text, 'length')


class DrawerRectCollapsed(DrawerRectLeafNames):
    "With text on collapsed nodes"

    def draw_collapsed(self):
        if self.aligned:
            return

        names = [first_name(node) for node in self.collapsed]
        if all(name == '' for name in names):
            return

        x, y, dx, dy = self.outline

        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])
        dx_fit = self.dx_fitting_texts(texts, dy)
        box = Box(x + dx, y, dx_fit, dy)
        yield from draw_texts(box, (0, 0.5), texts, 'name')


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
        dr_fit = self.dx_fitting_texts(texts, (r + dr) * da)
        box = Box(r + dr, a, dr_fit, da)
        yield from draw_texts(box, (0, 0.5), texts, 'name')


class DrawerRectFull(DrawerRectCollapsed, DrawerRectProperties):
    "With names on leaf nodes and labels on the properties (length, support)"
    pass


class DrawerCircFull(DrawerCircCollapsed, DrawerCircLengths):
    "With names on leaf nodes and labels on the lengths"
    pass


class DrawerAlignNames(DrawerRectFull):
    "With aligned content"

    def draw_content_float(self, node, point):
        if node.is_leaf:
            x, y = point
            dx, dy = self.content_size(node)

            if not self.aligned:
                if self.viewport:
                    p1 = (x + dx, y + dy/2)
                    p2 = (self.viewport.x + self.viewport.dx, y + dy/2)
                    yield draw_line(p1, p2, 'dotted')
            else:
                dx_fit = self.dx_fitting_texts([node.name], dy)
                box = Box(0, y, dx_fit, dy)
                yield draw_text(box, (0, 0.5), node.name, 'name')

    def draw_collapsed(self):
        names = [first_name(node) for node in self.collapsed]
        if all(name == '' for name in names):
            return

        x, y, dx, dy = self.outline

        if not self.aligned:
            if self.viewport:
                p1 = (x + dx, y + dy/2)
                p2 = (self.viewport.x + self.viewport.dx, y + dy/2)
                yield draw_line(p1, p2, 'dotted')
        else:
            texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])
            dx_fit = self.dx_fitting_texts(texts, dy)
            box = Box(0, y, dx_fit, dy)
            yield from draw_texts(box, (0, 0.5), texts, 'name')



class DrawerAlignHeatMap(DrawerRectFull):
    "With an example heatmap as aligned content"

    def draw_content_float(self, node, point):
        yield from super().draw_content_float(node, point)

        if self.aligned and node.is_leaf:
            _, y = point
            dx, dy = self.content_size(node)
            zx, zy = self.zoom
            random.seed(node.name)
            a = [random.randint(1, 360) for i in range(300)]
            yield draw_array(Box(0, y, 600, dy), a)

    def draw_collapsed(self):
        names = [first_name(node) for node in self.collapsed]
        texts = names if len(names) < 6 else (names[:3] + ['...'] + names[-2:])

        x, y, dx, dy = self.outline
        if self.aligned:
            zx, zy = self.zoom
            random.seed(str(texts))
            a = [random.randint(1, 360) for i in range(300)]
            yield draw_array(Box(0, y, 600, dy), a)
        else:
            if all(name == '' for name in names):
                return
            dx_fit = self.dx_fitting_texts(texts, dy)
            box = Box(x + dx, y, dx_fit, dy)
            yield from draw_texts(box, (0, 0.5), texts, 'name')


def get_drawers():
    return [
        DrawerRectSimple, DrawerRectFull,
        DrawerCircSimple, DrawerCircFull,
        DrawerAlignNames, DrawerAlignHeatMap]


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

def draw_box(box, name='', properties=None, node_id=None, result_of=None):
    return ['box', box, name, properties or {}, node_id or [], result_of or []]

def draw_cone(box):
    return ['cone', box]

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


def get_rect(element, zoom):
    "Return the rectangle that contains the given graphic element"
    eid = element[0]
    if eid in ['box', 'cone', 'array', 'text']:
        return element[1]
    elif eid in ['line', 'arc']:
        (x1, y1), (x2, y2) = element[1], element[2]
        return Box(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    else:
        raise ValueError(f'unrecognized element: {element!r}')


def get_asec(element, zoom):
    "Return the annular sector that contains the given graphic element"
    eid = element[0]
    if eid in ['box', 'cone', 'array', 'text']:
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


def intersects(b1, b2):
    "Return True if the boxes b1 and b2 (of the same kind) intersect"
    cdef double x1min, y1min, dx1, dy1, x2min, y2min, dx2, dy2

    if b1 is None or b2 is None:
        return True  # the box "None" represents the full plane

    x1min, y1min, dx1, dy1 = b1
    x1max, y1max = x1min + dx1, y1min + dy1
    x2min, y2min, dx2, dy2 = b2
    x2max, y2max = x2min + dx2, y2min + dy2
    return ((x1min <= x2max and x2min <= x1max) and
            (y1min <= y2max and y2min <= y1max))


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
