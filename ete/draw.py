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

# Drawing functions.
#
# To draw a tree, its nodes must have the members content_size and childs_size
# with the right values. They can be filled with store_sizes().

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
    #     p0....p2.....    p0 (p_node): top-left point of the node's rect
    #       .    [ ]  .    p1 (p_content): top-left point of the content's rect
    #     p1[   ][]   .    p2 (p_childs): top-left point of the childs' rect
    #       [   ][    ]
    #       .....[  ]..

    def draw(self, tree, point=(0, 0)):
        "Yield graphic elements to draw the tree"
        r_node = make_rect(point, node_size(tree))

        p_content = (r_node.x, r_node.y + (r_node.h - tree.content_size.h) / 2)
        r_content = make_rect(p_content, tree.content_size)

        p_left = (r_content.x, r_content.y + r_content.h / 2)
        p_right = (r_content.x + r_content.w, r_content.y + r_content.h / 2)
        yield draw_line(p_left, p_right)

        f = lambda: self.draw_content_inline(tree, p_content)
        yield from self.draw_or_outline(f, r_content)

        yield from self.draw_content_float(tree, p_content)
        yield from self.draw_content_align(tree, p_content)

        p_childs = (r_node.x + r_content.w, r_node.y)
        r_childs = make_rect(p_childs, tree.childs_size)

        f = lambda: self.draw_childs(tree, p_childs)
        yield from self.draw_or_outline(f, r_childs)

        if self.outline_rect:
            yield draw_rect(self.outline_rect)
            self.outline_rect = None


    def draw_childs(self, tree, point=(0, 0)):
        "Yield lines to the childs and all the graphic elements to draw them"
        x, y = point  # top-left of childs
        pc = (x, y + tree.childs_size.h / 2)  # center-left of childs
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
    "Draws the skeleton of the tree"
    pass



class DrawerCool(Drawer):
    "Draws with the name of the leaf nodes and labels on the lengths"

    def draw_content_inline(self, node, point=(0, 0)):
        if node.length:
            x, y = point
            w, h = node.content_size
            zx, zy = self.zoom
            text = '%.2g' % node.length
            g_text = draw_label(Rect(x, y + h/2, w, h/2), text)

            if zy * h > 1:  # NOTE: we may want to change this, but it's tricky
                yield g_text
            else:
                yield draw_rect(get_rect(g_text))

    def draw_content_float(self, node, point=(0, 0)):
        if not node.childs:
            x, y = point
            w, h = node.content_size
            zx, zy = self.zoom
            p_after_content = (x + node.content_size.w + 2 / zx, y + h / 1.5)
            yield draw_name(make_rect(p_after_content, Size(0, h/2)), node.name)

    def draw_content_align(self, node, point=(0, 0)):
        if not node.childs:
            w, h = node.content_size
            yield align(draw_name(make_rect(point, Size(0, h/2)), node.name))



def get_drawers():
    return [DrawerSimple, DrawerCool]



def draw_rect(r):
    return ['r', r.x, r.y, r.w, r.h]

def draw_line(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return ['l', x1, y1, x2, y2]

def draw_text(rect, text, text_type=''):
    x, y, w, h = rect
    return ['t' + text_type, x, y, w, h, text]

draw_name = lambda *args, **kwargs: draw_text(*args, **kwargs, text_type='n')
draw_label = lambda *args, **kwargs: draw_text(*args, **kwargs, text_type='l')

def align(element):
    return ['a'] + element


# Size-related functions.

def store_sizes(tree):
    "Store in each node of the tree its content size and childs size"
    for node in tree.childs:
        store_sizes(node)

    tree.childs_size = stack_vertical_size(node_size(n) for n in tree.childs)

    MIN_HEIGHT_CONTENT = 8  # TODO: think whether to put this somewhere else
    width = tree.length or 1
    height = max(tree.childs_size.h, MIN_HEIGHT_CONTENT)
    tree.content_size = Size(width, height)

# TODO: See if we only want to use childs_size.h (because in our current
#       implementation, content_size and childs_size.w are irrelevant).


def node_size(node):
    "Return the size of a node (its content and its childs)"
    return stack_horizontal_size([node.content_size, node.childs_size])


def stack_vertical_size(sizes):
    "Return the size of a rectangle containing all sizes vertically stacked"
    # []      [   ]
    # [  ] -> |   |
    # [ ]     [   ]
    max_width = 0
    sum_height = 0
    for size in sizes:
        max_width = max(max_width, size.w)
        sum_height += size.h
    return Size(max_width, sum_height)


def stack_horizontal_size(sizes):
    "Return the size of a rectangle containing all sizes horizontally stacked"
    # [ ] [   ] [  ]     [         ]
    # | |       [  ] ->  |         |
    # [ ]                [         ]
    sum_width = 0
    max_height = 0
    for size in sizes:
        sum_width += size.w
        max_height = max(max_height, size.h)
    return Size(sum_width, max_height)



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
