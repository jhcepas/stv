"""
Functions for drawing a tree.
"""

from collections import namedtuple

Size = namedtuple('Size', ['w', 'h'])  # width and height
Rect = namedtuple('Rect', ['x', 'y', 'w', 'h'])  # top-left corner and size

# The convention for coordinates is:
#   x increases to the right, y increases to the bottom.
#
#  +-----> x
#  |
#  |
#  v y
#
# This is the one normally used in computer graphics, including HTML Canvas,
# SVGs, Qt, and PixiJS.
#
# For a rectangle:           w
#                     x,y +-----+          so x,y is its top-left corner
#                         |     | h        and x+w,y+h its bottom-right one
#                         +-----+

# Drawing.

class Drawer:
    MIN_HEIGHT = 6  # anything that has less pixels will be a rectangle

    def __init__(self, viewport=None, zoom=(1, 1)):
        self.viewport = viewport
        self.zoom = zoom
        self.outline_rect = None

    def draw_or_outline(self, drawing_f, rect):
        "Yield the graphic elements of drawing_f() or an outline of rect"
        if intersects(rect, self.viewport):
            zx, zy = self.zoom
            height_draw = rect.h * zy
            if height_draw > Drawer.MIN_HEIGHT:
                yield from drawing_f()
            else:
                yield from self.outline(rect)

    def outline(self, rect):
        "Update the current outline and yield a graphic rect if appropriate"
        if not self.outline_rect:
            self.outline_rect = rect
        else:
            stacked_rect = stack_vertical_rect(self.outline_rect, rect)
            if stacked_rect:
                self.outline_rect = stacked_rect
            else:
                yield draw_rect(self.outline_rect)
                self.outline_rect = rect

    # To draw a tree, we draw its node content and then we draw its children to
    # its right. The relevant points in the node that we use are:
    #
    #     p0....p1.....    p0 (point): top-left point of the node's rect
    #       .    [ ]  .    p1 (p_childs): top-left point of the childs' rect
    #       [   ][]   .
    #       [   ][    ]
    #       .....[  ]..

    def draw(self, tree, point=(0, 0)):
        "Yield graphic elements to draw the tree"
        x, y = point
        w, h = content_size(tree)

        yield draw_line((x, y + h/2), (x + w, y + h/2))

        f = lambda: self.draw_content_inline(tree, point)
        yield from self.draw_or_outline(f, Rect(x, y, w, h))

        yield from self.draw_content_float(tree, point)
        yield from self.draw_content_align(tree, point)

        p_childs = (x + w, y)
        r_childs = make_rect(p_childs, childs_size(tree))

        f = lambda: self.draw_childs(tree, p_childs)
        yield from self.draw_or_outline(f, r_childs)

        if self.outline_rect:
            yield draw_rect(self.outline_rect)
            self.outline_rect = None


    def draw_childs(self, tree, point=(0, 0)):
        "Yield lines to the childs and all the graphic elements to draw them"
        x, y = point  # top-left of childs
        pc = (x, y + childs_size(tree).h / 2)  # center-left of childs
        for node in tree.childs:
            w, h = node_size(node)
            yield draw_line(pc, (x, y + h/2))
            f = lambda: self.draw(node, (x, y))
            yield from self.draw_or_outline(f, Rect(x, y, w, h))
            y += h

    # These are the functions that the user would supply to decide how to
    # represent a node.
    def draw_content_inline(self, node, point=(0, 0)):
        "Yield graphic elements to draw the inline contents of the node"
        yield from []

    def draw_content_float(self, node, point=(0, 0)):
        "Yield graphic elements to draw the floated contents of the node"
        yield from []

    def draw_content_align(self, node, point=(0, 0)):
        "Yield graphic elements to draw the aligned contents of the node"
        yield from []



class DrawerSimple(Drawer):
    "Skeleton of the tree"
    pass


class DrawerLeafNames(Drawer):
    "With names on leaf nodes"

    def draw_content_float(self, node, point=(0, 0)):
        if not node.childs:
            x, y = point
            w, h = content_size(node)
            zx, zy = self.zoom
            p_after_content = (x + w + 2 / zx, y + h / 1.5)
            yield draw_name(make_rect(p_after_content, Size(0, h/2)), node.name)


class DrawerLengths(Drawer):
    "With labels on the lengths"

    def draw_content_inline(self, node, point=(0, 0)):
        if node.length >= 0:
            x, y = point
            w, h = content_size(node)
            zx, zy = self.zoom
            text = '%.2g' % node.length
            g_text = draw_label(Rect(x, y + h/2, w, h/2), text)

            if zy * h > 1:  # NOTE: we may want to change this, but it's tricky
                yield g_text
            else:
                yield draw_rect(get_rect(g_text))


class DrawerFull(DrawerLeafNames, DrawerLengths):
    "With names on leaf nodes and labels on the lengths"
    pass


class DrawerTooltips(DrawerFull):
    "With tooltips with the names and properties of all nodes"

    def draw_content_inline(self, node, point=(0, 0)):
        yield from super().draw_content_inline(node, point)

        if node.name or node.properties:
            x, y = point
            w, h = content_size(node)
            zx, zy = self.zoom
            ptext = ', '.join(f'{k}: {v}' for k,v in node.properties.items())
            text = node.name + (' - ' if node.name and ptext else '')  + ptext
            fs = min(h/2, 15/zy)
            yield draw_tooltip(Rect(x + w/2, y + h/2, w/2, fs), text)


class DrawerAlign(DrawerFull):
    "With aligned content"

    def draw_content_align(self, node, point=(0, 0)):
        if not node.childs:
            w, h = content_size(node)
            yield align(draw_name(make_rect(point, Size(0, h/2)), node.name))



def get_drawers():
    return [DrawerSimple, DrawerLengths, DrawerLeafNames, DrawerFull,
        DrawerTooltips, DrawerAlign]



def draw_rect(r):
    return ['r', r.x, r.y, r.w, r.h]

def draw_line(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return ['l', x1, y1, x2, y2]

def draw_text(rect, text, text_type=''):
    x, y, w, h = rect
    return ['t' + text_type, x, y, w, h, text]

draw_name = lambda *args: draw_text(*args, text_type='n')
draw_label = lambda *args: draw_text(*args, text_type='l')
draw_tooltip = lambda *args: draw_text(*args, text_type='t')

def align(element):
    return ['a'] + element


# Size-related functions.

def node_size(node):
    "Return the size of a node (its content and its childs)"
    return Size(abs(node.length) + node.size[0], node.size[1])

def content_size(node):
    return Size(abs(node.length), node.size[1])

def childs_size(node):
    return Size(node.size[0], node.size[1])


# Rectangle-related functions.

def make_rect(p, size):
    x, y = p
    w, h = size
    return Rect(x, y, w, h)


def get_rect(element):
    "Return the rectangle that contains the given element"
    if type(element) == Rect:
        return element
    elif element[0] == 'r':
        _, x, y, w, h = element
        return Rect(x, y, w, h)
    elif element[0] == 'l':
        _, x1, y1, x2, y2 = element
        return Rect(min(x1, x2), min(y1, y2),
                    abs(x2 - x1), abs(y2 - y1))
    elif element[0].startswith('t'):
        _, x, y, w, h, text = element
        return Rect(x, y - h, w, h)
    else:
        raise ValueError('unrecognized element: ' + repr(element))


def intersects(r1, r2):
    "Return True if the rectangles r1 and r2 intersect"
    if r1 is None or r2 is None:
        return True  # the rectangle "None" represents the full plane
    x1min, y1min, w1, h1 = r1
    x1max, y1max = x1min + w1, y1min + h1
    x2min, y2min, w2, h2 = r2
    x2max, y2max = x2min + w2, y2min + h2
    return ((x1min < x2max and x2min < x1max) and
            (y1min < y2max and y2min < y1max))


def stack_vertical_rect(r1, r2):
    "Return the rectangle containing rectangles r1 and r2 vertically stacked"
    if r1.x == r2.x and r1.y + r1.h == r2.y:
        return Rect(r1.x, r1.y, max(r1.w, r2.w), r1.h + r2.h)
    else:
        return None
