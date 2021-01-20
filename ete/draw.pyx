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
# * Annulus sector   r,a .----.
#                       .  dr .     so (r,a) is its (inner,smaller-angle) corner
#                       \   .       and (r+dr,a+da) its (outer,bigger-angle) one
#                        \. da

# Drawing.

class Drawer:
    "Base class (needs subclassing with extra functions to draw)"

    MIN_SIZE = 6  # anything that has less pixels will be outlined

    def __init__(self, viewport=None, zoom=(1, 1)):
        self.viewport = viewport
        self.zoom = zoom
        self.outline = None
        self.xmin = self.xmax = self.ymin = self.ymax = 0

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

    def draw(self, tree):
        "Yield graphic elements to draw the tree"
        x, y = self.xmin, self.ymin

        # We traverse the tree with a stack of nodes being visited and their
        # number of children already visited. At a given moment it could be:
        visiting_nodes = [tree]  # [root, child2, child20, child201 (leaf)]
        visited_children = [0]   # [   2,      0,       1,               0]

        while visiting_nodes:
            node = visiting_nodes[-1]   # current node
            nch = visited_children[-1]  # number of children visited on the node
            dx, dy = self.content_size(node)

            if nch == 0:  # first time we visit this node
                elements, draw_children = self.get_content(node, (x, y))
                yield from elements
                if draw_children:
                    x += dx  # move our pointer forward
                else:
                    y += dy
                    pop(visiting_nodes, visited_children)
                    continue

            if len(node.children) > nch:  # add next child to the list to visit
                visiting_nodes.append(node.children[nch])
                visited_children.append(0)
            else:                         # go back to parent node
                x -= dx  # move our pointer back
                if node.is_leaf:
                    y += dy
                pop(visiting_nodes, visited_children)

        if self.outline:  # draw the last outline stacked
            yield self.draw_outline(self.outline)

    def get_content(self, node, point):
        "Return list of content's graphic elements, and if children need drawing"
        # Both the node's box and its content's box start at the given point.
        box_node = make_box(point, self.node_size(node))

        if not self.in_viewport(box_node):   # skip
            return [], False

        if self.is_small(box_node):          # outline & skip
            return list(self.update_outline(box_node)), False

        x, y = point
        dx, dy = self.content_size(node)

        elems = []  # graphic elements to return
        if self.in_viewport(Box(x, y, dx, dy)):
            bh = self.bh(node)  # node's branching height (in the right units)
            elems.append(self.draw_lengthline((x, y + bh), (x + dx, y + bh)))

            if len(node.children) > 1:
                c0, c1 = node.children[0], node.children[-1]
                bh0, bh1 = self.bh(c0), dy - self.node_size(c1).dy + self.bh(c1)
                elems.append(self.draw_childrenline((x + dx, y + bh0),
                                                    (x + dx, y + bh1)))

            elems += self.draw_content_inline(node, (x, y))
            elems.append(self.draw_nodebox(box_node, node.name, node.properties))

        elems += self.draw_content_float(node, (x, y))
        elems += self.draw_content_align(node, (x, y))

        return elems, True

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


def pop(visiting_nodes, visited_children):
    visiting_nodes.pop()
    visited_children.pop()
    if visited_children:
        visited_children[-1] += 1


class DrawerRect(Drawer):
    "Minimal functional drawer for a rectangular representation"

    def in_viewport(self, box):
        return intersects(self.viewport, box)

    def draw_outline(self, box):
        return draw_rect(box, 'outline')

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

    def draw_lengthline(self, p1, p2):
        "Return a line representing a length"
        return draw_line(p1, p2)

    def draw_childrenline(self, p1, p2):
        "Return a line spanning children that starts at p1 and ends at p2"
        return draw_line(p1, p2)

    def draw_nodebox(self, box, name, properties):
        return draw_rect(box, 'node', name, properties)



class DrawerCirc(Drawer):
    "Minimal functional drawer for a circular representation"

    def __init__(self, viewport=None, zoom=(1, 1), limits=(-pi, pi)):
        super().__init__(viewport, zoom)

        self.ymin, self.ymax = limits
        self.y2a = 0  # will be computed on self.draw()

        self.circumasec_viewport = circumasec(self.viewport)

    def in_viewport(self, box):
        return (intersects(self.circumasec_viewport, box) or
                intersects(self.viewport, circumrect(box)))

    def draw_outline(self, box):
        return draw_asec(box, 'outline')

    def draw(self, tree):
        self.y2a = (self.ymax - self.ymin) / tree.size[1]
        yield from super().draw(tree)

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

    def draw_lengthline(self, p1, p2):
        "Return a line representing a length"
        return draw_line(cartesian(*p1), cartesian(*p2))

    def draw_childrenline(self, p1, p2):
        "Return a line spanning children that starts at p1 and ends at p2"
        a1, a2 = p1[1], p2[1]  # angles
        return draw_arc(cartesian(*p1), cartesian(*p2), a2 - a1 > pi)

    def draw_nodebox(self, box, name, properties):
        return draw_asec(box, 'node', name, properties)


def cartesian(double r, double a):
    return r * cos(a), r * sin(a)


class DrawerSimple(DrawerRect):
    "Skeleton of the tree"
    pass


class DrawerLeafNames(DrawerRect):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if node.is_leaf:
            x, y = point
            w, h = self.content_size(node)
            zx, zy = self.zoom
            p_after_content = (x + w + 2 / zx, y + h / 1.5)
            fs = h/2
            yield draw_text(p_after_content, fs, node.name, 'name')


class DrawerCircLeafNames(DrawerCirc):
    "With names on leaf nodes"

    def draw_content_float(self, node, point):
        if node.is_leaf:
            r, a = point
            dr, da = self.content_size(node)
            zx, zy = self.zoom
            p_after_content = cartesian(r + dr + 2 / zx, a + da/1.5)
            fs = 2 * da
            yield draw_text(p_after_content, fs, node.name, 'name')


class DrawerLengths(DrawerRect):
    "With labels on the lengths"

    def draw_content_inline(self, node, point):
        if node.length >= 0:
            x, y = point
            w, h = self.content_size(node)
            zx, zy = self.zoom
            text = '%.2g' % node.length
            fs = min(zy * node.bh, zx * 1.5 * w / len(text))
            g_text = draw_text((x, y + node.bh), fs, text, 'length')

            if zy * h > 1:  # NOTE: we may want to change this, but it's tricky
                yield g_text
            else:
                pass  # TODO: something like  yield draw_box(get_box(g_text))


class DrawerFull(DrawerLeafNames, DrawerLengths):
    "With names on leaf nodes and labels on the lengths"
    pass


class DrawerAlign(DrawerFull):
    "With aligned content"

    def draw_content_align(self, node, point):
        if node.is_leaf:
            x, y = point
            w, h = self.content_size(node)
            yield align(draw_text((0, y+h/1.5), h/2, node.name, 'name'))



def get_drawers():
    return [DrawerSimple, DrawerLengths, DrawerLeafNames, DrawerFull,
        DrawerAlign, DrawerCirc, DrawerCircLeafNames]


# Basic drawing elements.

def draw_rect(box, box_type='', name='', properties=None):
    x, y, w, h = box
    return ['r', box_type, x, y, w, h, name, properties or {}]

def draw_asec(box, box_type='', name='', properties=None):
    r, a, dr, da = box
    return ['s', box_type, r, a, dr, da, name, properties or {}]

def draw_line(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return ['l', x1, y1, x2, y2]

def draw_arc(p1, p2, large=False):
    x1, y1 = p1
    x2, y2 = p2
    return ['c', x1, y1, x2, y2, int(large)]

def draw_text(point, fs, text, text_type=''):
    x, y = point
    return ['t', text_type, x, y, fs, text]

def align(element):
    return ['a'] + element


# Box-related functions.

def make_box(point, size):
    x, y = point
    dx, dy = size
    return Box(x, y, dx, dy)


def intersects(b1, b2):
    "Return True if the boxes b1 and b2 (of the same kind) intersect"
    cdef double x1min, x1max, x2min, x2max

    if b1 is None or b2 is None:
        return True  # the box "None" represents the full plane

    x1min, y1min, dx1, dy1 = b1
    x1max, y1max = x1min + dx1, y1min + dy1
    x2min, y2min, dx2, dy2 = b2
    x2max, y2max = x2min + dx2, y2min + dy2
    return ((x1min < x2max and x2min < x1max) and
            (y1min < y2max and y2min < y1max))


def stack(b1, b2):
    "Return the box containing boxes b1 and b2 stacked"
    if b1.x == b2.x and b1.y + b1.dy == b2.y:
        return Box(b1.x, b1.y, max(b1.dx, b2.dx), b1.dy + b2.dy)
    else:
        return None


def circumrect(asec):
    "Return the rectangle that circumscribes the given annulus sector"
    cdef double r, a, dr, da
    r, a, dr, da = asec
    points = [(r, a), (r, a+da), (r+dr, a), (r+dr, a+da)]
    xs = [r * cos(a) for r,a in points]
    ys = [r * sin(a) for r,a in points]
    xmin, ymin = min(xs), min(ys)
    return Box(xmin, ymin, max(xs) - xmin, max(ys) - ymin)


def circumasec(rect):
    "Return the annulus sector that circumscribes the given rectangle"
    cdef double x, y, w, h
    x, y, w, h = rect
    points = [(x, y), (x, y+h), (x+w, y), (x+w, y+h)]
    radius2 = [x*x + y*y for x,y in points]
    if x <= 0 and x+w >= 0 and y <= 0 and y+h >= 0:
        return Box(0, -pi, sqrt(max(radius2)), 2*pi)
    else:
        angles = [atan2(y, x) for x,y in points]
        rmin, amin = sqrt(min(radius2)), min(angles)
        return Box(rmin, amin, sqrt(max(radius2)) - rmin, max(angles) - amin)
