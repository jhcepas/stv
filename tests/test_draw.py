"""
Tests for drawing trees. To run with pytest.
"""

import sys
from os.path import abspath, dirname
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

from ete import tree, draw
Size, Box = draw.Size, draw.Box


def test_draw_elements():
    assert draw.draw_rect(Box(1, 2, 3, 4)) == \
        ['r', '', 1, 2, 3, 4, '', {}]
    assert draw.draw_asec(Box(1, 2, 3, 4)) == \
        ['s', '', 1, 2, 3, 4, '', {}]
    assert draw.draw_line((1, 2), (3, 4)) == \
        ['l', 1, 2, 3, 4]
    assert draw.draw_arc((1, 2), (3, 4), True) == \
        ['c', 1, 2, 3, 4, 1]
    assert draw.draw_text((1, 2), 3, 'hello') == \
        ['t', '', 1, 2, 3, 'hello']
    assert draw.draw_text((1, 2), 3, 'world', 'node') == \
        ['t', 'node', 1, 2, 3, 'world']


def test_draw_content_inline():
    t = tree.Tree('A:10')
    drawer1 = draw.DrawerFull(zoom=(10, 10))
    assert list(drawer1.draw_content_inline(t, (0, 0))) == [
        ['t', 'length', 0, 0.5, 5.0, '10']]
    drawer2 = draw.DrawerFull(zoom=(0.1, 0.1))
    assert list(drawer2.draw_content_inline(t, (0, 0))) == []


def test_draw_tree():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)
    drawer = draw.DrawerFull(zoom=(10, 10))
    elements = list(drawer.draw(t))
    assert elements == [
        ['l', 0, 1.25, 1.0, 1.25],
        ['r', 'node', 0, 0, 751.0, 3.0, 'F', {}],
        ['l', 1.0, 1.25, 101.0, 1.25],
        ['l', 101.0, 0.5, 101.0, 2.0],
        ['t', 'length', 1.0, 1.25, 12.5, '1e+02'],
        ['r', 'node', 1.0, 0, 750.0, 3.0, 'A', {}],
        ['l', 101.0, 0.5, 301.0, 0.5],
        ['t', 'length', 101.0, 0.5, 5.0, '2e+02'],
        ['r', 'node', 101.0, 0, 200.0, 1.0, 'B', {}],
        ['t', 'name', 301.2, 0.7692307692307692, 0.7142857142857143, 'B'],
        ['l', 101.0, 2.0, 451.0, 2.0],
        ['l', 451.0, 1.5, 451.0, 2.5],
        ['t', 'length', 101.0, 2.0, 10.0, '3.5e+02'],
        ['r', 'node', 101.0, 1.0, 650.0, 2.0, 'E', {}],
        ['l', 451.0, 1.5, 701.0, 1.5],
        ['t', 'length', 451.0, 1.5, 5.0, '2.5e+02'],
        ['r', 'node', 451.0, 1.0, 250.0, 1.0, 'C', {}],
        ['t', 'name', 701.2, 1.7692307692307692, 0.7142857142857143, 'C'],
        ['l', 451.0, 2.5, 751.0, 2.5],
        ['t', 'length', 451.0, 2.5, 5.0, '3e+02'],
        ['r', 'node', 451.0, 2.0, 300.0, 1.0, 'D', {}],
        ['t', 'name', 751.2,2.769230769230769, 0.7142857142857143, 'D']]


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
    drawer = draw.DrawerFull(zoom=(10, 10))
    assert drawer.node_size(t) == Size(5, 3)
    assert drawer.content_size(t) == Size(1, 3)
    assert drawer.children_size(t) == Size(4, 3)
