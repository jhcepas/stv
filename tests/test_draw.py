"""
Tests for drawing trees. To run with pytest.
"""

import sys
from os.path import abspath, dirname
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

from math import pi, sqrt

from ete import tree, draw
Size, Box = draw.Size, draw.Box


def test_draw_elements():
    assert draw.draw_box(Box(1, 2, 3, 4)) == \
        ['box', (1, 2, 3, 4), '', {}, [], []]
    assert draw.draw_line((1, 2), (3, 4)) == \
        ['line', (1, 2), (3, 4), '', []]
    assert draw.draw_arc((1, 2), (3, 4), True) == \
        ['arc', (1, 2), (3, 4), 1, '']
    assert draw.draw_text('hello', (1, 2, 3, 4), (5, 6)) == \
        ['text', 'hello', (1, 2, 3, 4), (5, 6), '']
    assert draw.draw_text('world', (1, 2, 3, 4), (5, 6), 'node') == \
        ['text', 'world', (1, 2, 3, 4), (5, 6), 'node']


def test_draw_content_inline():
    t = tree.Tree('A:10')
    t.properties['support'] = 0.9
    drawer1 = draw.DrawerRectFull(t, zoom=(20, 20))
    assert list(drawer1.draw_content_inline(t, (0, 0), 0.5)) == [
            ['text', (0, 0, 10.0, 0.5), (0, 1), '10', 'length'],
            ['text', (0, 0.5, 10.0, 0.5), (0, 0), '0.9', 'support']
        ]
    drawer2 = draw.DrawerRectFull(t, zoom=(0.1, 0.1))
    assert list(drawer2.draw_content_inline(t, (0, 0), 0.5)) == []


def test_draw_content_float():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.Tree(tree_text)

    drawer = draw.DrawerRectFull(t, zoom=(10, 10))
    assert list(drawer.draw_content_float(t, (0, 0))) == []
    assert list(drawer.draw_content_float(t[0,0], (0, 0))) == [
        ['text', (200.0, 0, 0.6666666666666667, 1.0), (0, 0.5), 'B', 'name']]
    assert list(drawer.draw_content_float(t[0,0], (6, 7))) == [
        ['text', (206.0, 7, 0.6666666666666667, 1.0), (0, 0.5), 'B', 'name']]


def test_draw_collapsed():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.Tree(tree_text)

    drawer_z10 = draw.DrawerRectCollapsed(t, zoom=(10, 10))
    assert not any(e[0] == 'b' and e[2] == 'outline' for e in drawer_z10.draw())

    drawer_z2 = draw.DrawerRectCollapsed(t, zoom=(2, 2))
    elements_z2 = list(drawer_z2.draw())
    assert elements_z2 == [
        ['cone', (101.0, 0, 650.0, 3.0)],
        ['text', (751.0, 0, 1.0, 1.5), (0, 0.5), 'B', 'name'],
        ['text', (751.0, 1.5, 1.0, 1.5), (0, 0.5), 'E', 'name'],
        ['line', (1.0, 1.5), (101.0, 1.5), '', []],
        ['line', (0.0, 1.5), (1.0, 1.5), '', []],
        ['box', (0.0, 0.0, 752.0, 3.0), 'F', {}, [], []],
        ['box', (1.0, 0.0, 751.0, 3.0), 'A', {}, [0], []],
        ['box', (101.0, 0, 651.0, 3.0), '(collapsed)', {}, [], []]]

    drawer_z1 = draw.DrawerRectCollapsed(t)
    elements_z1 = list(drawer_z1.draw())
    assert elements_z1 == [
        ['cone', (0, 0, 751.0, 3.0)],
        ['text', (751.0, 0, 2.0, 3.0), (0, 0.5), 'F', 'name'],
        ['box', (0, 0, 753.0, 3.0), '(collapsed)', {}, [], []]]


def test_draw_tree():

    # TODO: fix the rounding errors when comparing

    tree_text = '((A:200,(B:250,C:300)D:350)E:100)F;'
    t = tree.Tree(tree_text)
    # TODO: include support directly in tree_text
    t['D'].properties['support'] = 0.9
    t['E'].properties['support'] = 0.8
    t['F'].properties['support'] = 0.3

    drawer = draw.DrawerRectFull(t, zoom=(10, 10))
    elements = list(drawer.draw())
    assert elements == [
        ['line', (101.0, 0.5), (301.0, 0.5), '', []], 
        ['text', Box(x=301.0, y=0.0, dx=0.6666666666666667, dy=1.0), (0, 0.5), 'A', 'name'],
        ['line', (451.0, 1.5), (701.0, 1.5), '', []],
        ['text', Box(x=701.0, y=1.0, dx=0.6666666666666667, dy=1.0), (0, 0.5), 'B', 'name'], 
        ['line', (451.0, 2.5), (751.0, 2.5), '', []], 
        ['text', Box(x=751.0, y=2.0, dx=0.6666666666666667, dy=1.0), (0, 0.5), 'C', 'name'], 
        ['line', (101.0, 2.0), (451.0, 2.0), '', []], ['line', (451.0, 1.5), (451.0, 2.5), '', []], 
        ['text', Box(x=101.0, y=1.0, dx=350.0, dy=1.0), (0, 1), '3.5e+02', 'length'], 
        ['text', Box(x=101.0, y=2.0, dx=350.0, dy=1.0), (0, 0), '0.9', 'support'], 
        ['line', (1.0, 1.25), (101.0, 1.25), '', []],
        ['line', (101.0, 0.5), (101.0, 2.0), '', []], 
        ['text', Box(x=1.0, y=0.0, dx=100.0, dy=1.25), (0, 1), '1e+02', 'length'], 
        ['text', Box(x=1.0, y=1.25, dx=100.0, dy=1.75), (0, 0), '0.8', 'support'], 
        ['line', (0.0, 1.25), (1.0, 1.25), '', []],
        ['text', Box(x=0.0, y=1.25, dx=1.0, dy=1.75), (0, 0), '0.3', 'support'], 
        ['box', Box(x=0.0, y=0.0, dx=751.6666666666666, dy=3.0), 'F', {'support': 0.3}, [], []], 
        ['box', Box(x=1.0, y=0.0, dx=750.6666666666666, dy=3.0), 'E', {'support': 0.8}, [0], []],
        ['box', Box(x=101.0, y=1.0, dx=650.6666666666666, dy=2.0), 'D', {'support': 0.9}, [0, 1], []],
        ['box', Box(x=451.0, y=2.0, dx=300.66666666666663, dy=1.0), 'C', {}, [0, 1, 1], []], 
        ['box', Box(x=451.0, y=1.0, dx=250.66666666666663, dy=1.0), 'B', {}, [0, 1, 0], []],
        ['box', Box(x=101.0, y=0.0, dx=200.66666666666669, dy=1.0), 'A', {}, [0, 0], []]
    ]

    drawer_circ = draw.DrawerCircFull(t, zoom=(10, 10))
    elements_circ = list(drawer_circ.draw())
    assert elements_circ == [
        ['line', (-50.500000000000014, -87.4685657822283), 
                 (-150.50000000000003, -260.673646539116), '', []],
        ['text', Box(x=101.0, y=-3.141592653589793, dx=200.0, dy=1.0471975511965976), (0, 1), '2e+02', 'length'], 
        ['text', Box(x=301.0, y=-3.141592653589793, dx=420.27528388023455, dy=2.0943951023931953), (0, 0.5), 'A', 'name'],
        ['line', (451.0, -1.0014211682118912e-13), 
                 (701.0, -1.5565326805244695e-13), '', []], 
        ['text', Box(x=451.0, y=-1.0471975511965979, dx=250.0, dy=1.0471975511965976), (0, 1), '2.5e+02', 'length'],
        ['text', Box(x=701.0, y=-1.0471975511965979, dx=978.78064451842, dy=2.0943951023931953), (0, 0.5), 'B', 'name'],
        ['line', (-225.49999999999972, 390.577457106782), 
                 (-375.49999999999955, 650.3850782421138), '', []], 
        ['text', Box(x=451.0, y=1.0471975511965974, dx=300.0, dy=1.0471975511965976), (0, 1), '3e+02', 'length'],
        ['text', Box(x=751.0, y=1.0471975511965974, dx=1048.5938145981931, dy=2.0943951023931953), (0, 0.5), 'C', 'name'],
        ['line', (50.500000000000036, 87.46856578222828), 
                 (225.50000000000014, 390.57745710678176), '', []],
        ['arc', (451.0, -1.0014211682118912e-13), (-225.4999999999999, 390.57745710678194), 0, ''], 
        ['text', Box(x=101.0, y=-1.0471975511965979, dx=350.0, dy=2.0943951023931953), (0, 1), '3.5e+02', 'length'],
        ['text', Box(x=101.0, y=1.0471975511965974, dx=350.0, dy=2.0943951023931953), (0, 0), '0.9', 'support'], 
        ['line', (0.8660254037844383, -0.5000000000000007), 
                 (87.46856578222827, -50.500000000000064), '', []], 
        ['arc', (-50.500000000000014, -87.4685657822283), 
                (50.500000000000064, 87.46856578222827), 0, ''], 
        ['line', (0.0, -0.0), (0.8660254037844383, -0.5000000000000007), '', []],
        ['box', Box(x=0.0, y=-3.141592643589793, dx=1799.5938145981931, dy=6.283185287179586), 'F', {'support': 0.3}, [], []],
        ['box', Box(x=1.0, y=-3.141592643589793, dx=1798.5938145981931, dy=6.283185287179586), 'E', {'support': 0.8}, [0], []],
        ['box', Box(x=101.0, y=-1.0471975511965979, dx=1698.5938145981931, dy=4.188790194786391), 'D', {'support': 0.9}, [0, 1], []],
        ['box', Box(x=451.0, y=1.0471975511965974, dx=1348.5938145981931, dy=2.0943950923931958), 'C', {}, [0, 1, 1], []], 
        ['box', Box(x=451.0, y=-1.0471975511965979, dx=1228.78064451842, dy=2.0943951023931953), 'B', {}, [0, 1, 0], []],
        ['box', Box(x=101.0, y=-3.141592643589793, dx=620.2752838802346, dy=2.0943950923931953), 'A', {}, [0, 0], []]
    ]

def test_intersects():
    # Simple intersection test.
    r1 = Box(0, 0, 10, 20)
    r2 = Box(-5, 0, 10, 20)
    assert draw.intersects(r1, r2)

    # Create several rectangles that start at their visual position and
    # have the size (width and height) as they appear in numbers.
    rects_text = """
  10,4
      5,2

                  2,3
 20,1
"""
    rects = []
    for y, line in enumerate(rects_text.splitlines()):
        for x, c in enumerate(line):
            if c != ' ':
                w, h = [int(v) for v in line.split(',')]
                rects.append(Box(x, y, w, h))
                break

    assert draw.intersects(rects[0], rects[1])
    assert not draw.intersects(rects[1], rects[2])
    assert draw.intersects(rects[2], rects[3])


def test_size():
    t = tree.Tree('(a:2,b:3,c:4)d;')
    drawer = draw.DrawerRectFull(t, zoom=(10, 10))
    assert drawer.node_size(t) == Size(5, 3)
    assert drawer.content_size(t) == Size(1, 3)
    assert drawer.children_size(t) == Size(4, 3)


def test_stack():
    b1 = Box(x=0, y= 0, dx=10, dy=5)
    b2 = Box(x=0, y= 5, dx=20, dy=10)
    b3 = Box(x=0, y=15, dx= 5, dy=3)
    b4 = Box(x=5, y=15, dx= 5, dy=3)

    assert draw.stack(None, b1) == b1
    assert draw.stack(b1, b2) == Box(0, 0, 20, 15)
    assert draw.stack(b2, b3) == Box(0, 5, 20, 13)
    assert draw.stack(b1, draw.stack(b2, b3)) == Box(0, 0, 20, 18)
    assert draw.stack(draw.stack(b1, b2), b3) == Box(0, 0, 20, 18)


def test_circumshapes():
    # Make sure that the rectangles or annular sectors that represent the full
    # plane stay representing the full plane.
    assert draw.circumrect(None) is None
    assert draw.circumasec(None) is None

    # Rectangles surrounding annular sectors.
    assert draw.circumrect(Box(0, 0, 1, pi/2)) == Box(0, 0, 1, 1)
    assert draw.circumrect(Box(0, 0, 2, -pi/2)) == Box(0, -2, 2, 2)
    assert draw.circumrect(Box(0, 0, 1, pi/4)) == Box(0, 0, 1, 1/sqrt(2))

    # Annular sectors surrounding rectangles.
    assert draw.circumasec(Box(0, -2, 1, 1)) == Box(1, -pi/2, sqrt(5) - 1, pi/4)


def test_in_viewport():
    t = tree.Tree('(a:2,b:3,c:4)d;')
    viewport = Box(-1, -2, 10, 20)
    drawer = draw.DrawerRectFull(t, viewport, zoom=(10, 10))
    assert drawer.in_viewport(Box(0, 0, 1, 1))
    assert not drawer.in_viewport(Box(30, 20, 5, 5))
