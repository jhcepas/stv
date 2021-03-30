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
        ['box', (1, 2, 3, 4), '', {}, []]
    assert draw.draw_line((1, 2), (3, 4)) == \
        ['line', (1, 2), (3, 4), '']
    assert draw.draw_arc((1, 2), (3, 4), True) == \
        ['arc', (1, 2), (3, 4), 1, '']
    assert draw.draw_text('hello', (1, 2), 3) == \
        ['text', 'hello', (1, 2), 3, '']
    assert draw.draw_text('world', (1, 2), 3, 'node') == \
        ['text', 'world', (1, 2), 3, 'node']


def test_draw_content_inline():
    t = tree.Tree('A:10')
    drawer1 = draw.DrawerFull(t, zoom=(20, 20))
    assert list(drawer1.draw_content_inline(t, (0, 0))) == [
        ['text', '10', (0, 0.5), 0.5, 'length']]
    drawer2 = draw.DrawerFull(t, zoom=(0.1, 0.1))
    assert list(drawer2.draw_content_inline(t, (0, 0))) == []


def test_draw_content_float():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)

    drawer = draw.DrawerFull(t, zoom=(10, 10))
    assert list(drawer.draw_content_float(t, (0, 0))) == []
    assert list(drawer.draw_content_float(t[0,0], (0, 0))) == [
        ['text', 'B', (200.0, 0.7692307692307692), 0.7142857142857143, 'name']]
    assert list(drawer.draw_content_float(t[0,0], (6, 7))) == [
        ['text', 'B', (6+200.0, 7+0.7692307692307692), 0.7142857142857143, 'name']]


def test_draw_collapsed():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)

    drawer = draw.DrawerCollapsed(t, zoom=(10, 10))
    assert not any(e[0] == 'b' and e[2] == 'outline' for e in drawer.draw())

    assert list(draw.DrawerCollapsed(t, zoom=(2, 2)).draw()) == [
        ['line', (0, 1.25), (1.0, 1.25), ''],
        ['line', (1.0, 1.25), (101.0, 1.25), ''],
        ['line', (101.0, 0.5), (101.0, 2.0), ''],
        ['cone', (101.0, 0, 650.0, 3.0)],
        ['text', 'E', (751.0, 2.727272727272727), 1.1363636363636362, 'name'],
        ['text', 'B', (751.0, 1.3636363636363635), 1.1363636363636362, 'name'],
        ['box', (0.0, 0.0, 751.7575757575758, 3.0), 'F', {}, []],
        ['box', (1.0, 0.0, 750.7575757575758, 3.0), 'A', {}, [0]],
        ['box', (101.0, 0, 650.7575757575758, 3.0), '(collapsed)', {}, []]]

    assert list(draw.DrawerCollapsed(t).draw()) == [
        ['cone', (0, 0, 751.0, 3.0)],
        ['text', 'F', (751.0, 2.727272727272727), 2.5, 'name'],
        ['box', (0, 0, 752.6666666666666, 3.0), '(collapsed)', {}, []]]


def test_draw_tree():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)

    drawer = draw.DrawerFull(t, zoom=(10, 10))
    elements = list(drawer.draw())
    assert elements == [
        ['line', (0, 1.25), (1.0, 1.25), ''],
        ['line', (1.0, 1.25), (101.0, 1.25), ''],
        ['line', (101.0, 0.5), (101.0, 2.0), ''],
        ['text', '1e+02', (1.0, 1.25), 1.25, 'length'],
        ['line', (101.0, 0.5), (301.0, 0.5), ''],
        ['text', 'B', (301.0, 0.7692307692307692), 0.7142857142857143, 'name'],
        ['line', (101.0, 2.0), (451.0, 2.0), ''],
        ['line', (451.0, 1.5), (451.0, 2.5), ''],
        ['text', '3.5e+02', (101.0, 2.0), 1.0, 'length'],
        ['line', (451.0, 1.5), (701.0, 1.5), ''],
        ['text', 'C', (701.0, 1.7692307692307692), 0.7142857142857143, 'name'],
        ['line', (451.0, 2.5), (751.0, 2.5), ''],
        ['text', 'D', (751.0, 2.769230769230769), 0.7142857142857143, 'name'],
        ['box', (0.0, 0.0, 751.4761904761905, 3.0), 'F', {}, []],
        ['box', (1.0, 0.0, 750.4761904761905, 3.0), 'A', {}, [0]],
        ['box', (101.0, 1.0, 650.4761904761905, 2.0), 'E', {}, [0, 1]],
        ['box', (451.0, 2.0, 300.4761904761905, 1.0), 'D', {}, [0, 1, 1]],
        ['box', (451.0, 1.0, 250.47619047619048, 1.0), 'C', {}, [0, 1, 0]],
        ['box', (101.0, 0, 200.47619047619048, 1.0), 'B', {}, [0, 0]]]

    drawer_circ = draw.DrawerCircFull(t, zoom=(10, 10))
    elements_circ = list(drawer_circ.draw())
    assert elements_circ == [
        ['line', (0.0, -0.0), (0.8660254037844385, -0.5000000000000002), ''],
        ['line', (0.8660254037844385, -0.5000000000000002),
                (87.46856578222828, -50.50000000000002), ''],
        ['arc', (-50.50000000000002, -87.46856578222828),
                (50.49999999999995, 87.46856578222834), 1, ''],
        ['text', '1e+02', (0.8660254037844385, -0.5000000000000002), 30.0, 'length'],
        ['line', (-50.50000000000002, -87.46856578222828),
                (-150.50000000000006, -260.67364653911596), ''],
        ['text', '2e+02', (-50.50000000000002, -87.46856578222828), 60.0, 'length'],
        ['text', 'B', (12.120047972933921, -300.7558884496425), 450.29494701453706, 'name'],
        ['line', (50.500000000000036, 87.46856578222828),
                (225.50000000000014, 390.57745710678176), ''],
        ['arc', (451.0, -1.0014211682118912e-13),
                (-225.4999999999999, 390.5774571067819), 0, ''],
        ['text', '3.5e+02', (50.500000000000036, 87.46856578222828), 75.0, 'length'],
        ['line', (451.0, -1.0014211682118912e-13),
                (701.0, -1.5565326805244695e-13), ''],
        ['text', '2.5e+02', (451.0, -1.0014211682118912e-13), 53.57142857142857, 'length'],
        ['text', 'C', (592.4782499662002, 374.6605441155884), 1048.6935476983072, 'name'],
        ['line', (-225.49999999999972, 390.57745710678194),
                (-375.49999999999955, 650.3850782421137), ''],
        ['text', '3e+02', (-225.49999999999972, 390.57745710678194), 90.0, 'length'],
        ['text', 'D', (-664.9774752655604, 349.0071022048706), 1123.4933727837783, 'name'],
        ['box', (0.0, -3.141592643589793, 1499.9955818558524, 6.283185287179586), 'F', {}, []],
        ['box', (1.0, -3.141592643589793, 1498.9955818558524, 6.283185287179586), 'A', {}, [0]],
        ['box', (101.0, -1.0471975511965979, 1398.9955818558524, 4.188790194786391), 'E', {}, [0, 1]],
        ['box', (451.0, 1.0471975511965974, 1048.9955818558524, 2.0943950923931958), 'D', {}, [0, 1, 1]],
        ['box', (451.0, -1.0471975511965979, 949.1290317988714, 2.0943951023931953), 'C', {}, [0, 1, 0]],
        ['box', (101.0, -3.141592643589793, 500.1966313430248, 2.0943950923931953), 'B', {}, [0, 0]]]


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
    t = tree.loads('(a:2,b:3,c:4)d;')
    viewport = Box(-1, -2, 10, 20)
    drawer = draw.DrawerFull(t, viewport, zoom=(10, 10))
    assert drawer.in_viewport(Box(0, 0, 1, 1))
    assert not drawer.in_viewport(Box(30, 20, 5, 5))


def test_get_nodes():
    t = tree.loads('((B:200,(C:250,D:300)E:350)A:100)F;')

    drawer = draw.DrawerFull(t, zoom=(10, 10))
    drawer.get_nodes(lambda node: node.name in ['A', 'C']) == [
        ((0,), Box(x=1.0, y=0, dx=100.0, dy=3.0)),
        ((0,0,0), Box(x=451.0, y=1.0, dx=250.0, dy=1.0))]


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
