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
    assert draw.draw_box('r', Box(1, 2, 3, 4)) == \
        ['r', (1, 2, 3, 4), '', '', {}, []]
    assert draw.draw_box('s', Box(1, 2, 3, 4)) == \
        ['s', (1, 2, 3, 4), '', '', {}, []]
    assert draw.draw_line((1, 2), (3, 4)) == \
        ['l', (1, 2), (3, 4)]
    assert draw.draw_arc((1, 2), (3, 4), True) == \
        ['c', (1, 2), (3, 4), 1]
    assert draw.draw_text('hello', (1, 2), 3) == \
        ['t', 'hello', (1, 2), 3, '']
    assert draw.draw_text('world', (1, 2), 3, 'node') == \
        ['t', 'world', (1, 2), 3, 'node']


def test_draw_content_inline():
    t = tree.Tree('A:10')
    drawer1 = draw.DrawerFull(t, zoom=(10, 10))
    assert list(drawer1.draw_content_inline(t, (0, 0))) == [
        ['t', '10', (0, 0.5), 5.0, 'length']]
    drawer2 = draw.DrawerFull(t, zoom=(0.1, 0.1))
    assert list(drawer2.draw_content_inline(t, (0, 0))) == []


def test_draw_tree():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)

    drawer = draw.DrawerFull(t, zoom=(10, 10))
    elements = list(drawer.draw())
    assert elements == [
        ['l', (0, 1.25), (1.0, 1.25)],
        ['r', (0, 0, 751.0, 3.0), 'node', 'F', {}, []],
        ['l', (1.0, 1.25), (101.0, 1.25)],
        ['l', (101.0, 0.5), (101.0, 2.0)],
        ['t', '1e+02', (1.0, 1.25), 12.5, 'length'],
        ['r', (1.0, 0, 750.0, 3.0), 'node', 'A', {}, [0]],
        ['l', (101.0, 0.5), (301.0, 0.5)],
        ['t', '2e+02', (101.0, 0.5), 5.0, 'length'],
        ['r', (101.0, 0, 200.0, 1.0), 'node', 'B', {}, [0, 0]],
        ['t', 'B', (301.2, 0.7692307692307692), 0.7142857142857143, 'name'],
        ['l', (101.0, 2.0), (451.0, 2.0)],
        ['l', (451.0, 1.5), (451.0, 2.5)],
        ['t', '3.5e+02', (101.0, 2.0), 10.0, 'length'],
        ['r', (101.0, 1.0, 650.0, 2.0), 'node', 'E', {}, [0, 1]],
        ['l', (451.0, 1.5), (701.0, 1.5)],
        ['t', '2.5e+02', (451.0, 1.5), 5.0, 'length'],
        ['r', (451.0, 1.0, 250.0, 1.0), 'node', 'C', {}, [0, 1, 0]],
        ['t', 'C', (701.2, 1.7692307692307692), 0.7142857142857143, 'name'],
        ['l', (451.0, 2.5), (751.0, 2.5)],
        ['t', '3e+02', (451.0, 2.5), 5.0, 'length'],
        ['r', (451.0, 2.0, 300.0, 1.0), 'node', 'D', {}, [0, 1, 1]],
        ['t', 'D', (751.2, 2.769230769230769), 0.7142857142857143, 'name']]

    drawer_circ = draw.DrawerCircFull(t, zoom=(10, 10))
    elements_circ = list(drawer_circ.draw())
    assert elements_circ == [
        ['l', (0.0, -0.0), (0.8660254037844385, -0.5000000000000002)],
        ['s',
        (0, -3.141592653589793, 751.0, 6.283185307179586),
        'node', 'F', {}, []],
        ['l',
        (0.8660254037844385, -0.5000000000000002),
        (87.46856578222828, -50.50000000000002)],
        ['c',
        (-50.50000000000002, -87.46856578222828),
        (50.49999999999995, 87.46856578222834),
        1],
        ['t', '1e+02', (0.8660254037844385, -0.5000000000000002), 300.0, 'length'],
        ['s',
        (1.0, -3.141592653589793, 750.0, 6.283185307179586),
        'node', 'A', {}, [0]],
        ['l',
        (-50.50000000000002, -87.46856578222828),
        (-150.50000000000006, -260.67364653911596)],
        ['t', '2e+02', (-50.50000000000002, -87.46856578222828), 600.0, 'length'],
        ['s',
        (101.0, -3.141592653589793, 200.0, 2.0943951023931953),
        'node', 'B', {}, [0, 0]],
        ['t',
        'B',
        (12.128101160955802, -300.9557262492768),
        450.29494701453706, 'name'],
        ['l',
        (50.500000000000036, 87.46856578222828),
        (225.50000000000014, 390.57745710678176)],
        ['c',
        (451.0, -1.0014211682118912e-13),
        (-225.4999999999999, 390.5774571067819),
        0],
        ['t', '3.5e+02', (50.500000000000036, 87.46856578222828), 750.0, 'length'],
        ['s',
        (101.0, -1.0471975511965979, 650.0, 4.1887902047863905),
        'node', 'E', {}, [0, 1]],
        ['l', (451.0, -1.0014211682118912e-13), (701.0, -1.5565326805244695e-13)],
        ['t',
        '2.5e+02',
        (451.0, -1.0014211682118912e-13),
        535.7142857142857, 'length'],
        ['s',
        (451.0, -1.0471975511965979, 250.0, 2.0943951023931953),
        'node', 'C', {}, [0, 1, 0]],
        ['t',
        'C',
        (592.6472879833091, 374.76743728081397),
        1048.6935476983072, 'name'],
        ['l',
        (-225.49999999999972, 390.57745710678194),
        (-375.49999999999955, 650.3850782421137)],
        ['t', '3e+02', (-225.49999999999972, 390.57745710678194), 900.0, 'length'],
        ['s',
        (451.0, 1.0471975511965974, 300.0, 2.0943951023931953),
        'node', 'D', {}, [0, 1, 1]],
        ['t',
        'D',
        (-665.1545664706911, 349.10004683927934),
        1123.4933727837783, 'name']]


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
    t = tree.loads('(a:2,b:3,c:4)d;')
    drawer = draw.DrawerFull(t, zoom=(10, 10))
    assert drawer.node_size(t) == Size(5, 3)
    assert drawer.content_size(t) == Size(1, 3)
    assert drawer.children_size(t) == Size(4, 3)


def test_stack():
    b1 = Box(x=0, y= 0, dx=10, dy=5)
    b2 = Box(x=0, y= 5, dx=20, dy=10)
    b3 = Box(x=0, y=15, dx= 5, dy=3)
    b4 = Box(x=5, y=15, dx= 5, dy=3)

    assert draw.stack(b1, b2) == Box(0, 0, 20, 15)
    assert draw.stack(b2, b3) == Box(0, 5, 20, 13)
    assert draw.stack(b2, b4) is None
    assert draw.stack(b1, b3) is None
    assert draw.stack(b1, draw.stack(b2, b3)) == Box(0, 0, 20, 18)
    assert draw.stack(draw.stack(b1, b2), b3) == Box(0, 0, 20, 18)
    assert draw.stack(b3, draw.stack(b1, b2)) is None


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
    t = tree.loads('(a:2,b:3,c:4)d;')
    viewport = Box(-1, -2, 10, 20)
    drawer = draw.DrawerFull(t, viewport, zoom=(10, 10))
    assert drawer.in_viewport(Box(0, 0, 1, 1))
    assert not drawer.in_viewport(Box(30, 20, 5, 5))


def test_get_node_boxes():
    t = tree.loads('((B:200,(C:250,D:300)E:350)A:100)F;')

    drawer = draw.DrawerFull(t, zoom=(10, 10))
    drawer.get_node_boxes(lambda node: node.name in ['A', 'C']) == [
        Box(x=1.0, y=0, dx=100.0, dy=3.0),
        Box(x=451.0, y=1.0, dx=250.0, dy=1.0)]


def test_get_node_at():
    t = tree.loads('((d:5,e:2)b:3,(f:4,g:3)c:1)a:2;')
    # a:2
    # ├─b:3
    # │ ├─d:5
    # │ └─e:2
    # └─c:1
    #   ├─f:4
    #   └─g:3

    drawer = draw.DrawerFull(t)
    for point, node in [
        ((-1, -1), None),
        ((0, 0), t['a']),
        ((2, 0), t['b']),
        ((6, 0), t['d']),
        ((1, 2), t['a']),
        ((2, 2), t['c']),
        ((6, 1), t['e']),
        ((6, 2), t['f']),
        ((6, 3), None),
        ((3, 3), t['g'])]:
        assert drawer.get_node_at(point) == node
