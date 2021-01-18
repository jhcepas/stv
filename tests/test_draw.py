#!/usr/bin/env python3

"""
Tests for drawing trees.

To run with pytest, but you can run interactively too if you want.
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
    assert draw.draw_text(Box(1, 2, 3, 4), 'hello') == \
        ['t', '', 1, 2, 3, 4, 'hello']
    assert draw.draw_text(Box(1, 2, 3, 4), 'world', 'node') == \
        ['t', 'node', 1, 2, 3, 4, 'world']


def test_draw_content_inline():
    t = tree.Tree('A:10')
    drawer1 = draw.DrawerFull(zoom=(10, 10))
    print('<-', t)
    print('->', list(drawer1.draw_content_inline(t)))
    assert list(drawer1.draw_content_inline(t)) == [
        ['t', 'length', 0, 0.5, 10.0, 0.5, '10']]
    print('<-', t, 'zoom=(0.1, 0.1)')
    drawer2 = draw.DrawerFull(zoom=(0.1, 0.1))
    print('->', list(drawer2.draw_content_inline(t)))
    assert list(drawer2.draw_content_inline(t)) == []


def test_draw_tree():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)
    drawer = draw.DrawerFull(zoom=(10, 10))
    elements = list(drawer.draw(t))
    print(elements)
    assert elements == [
        ['l', 0, 1.25, 1.0, 1.25],
        ['r', 'node', 0, 0, 751.0, 3.0, 'F', {}],
        ['l', 1.0, 1.25, 101.0, 1.25],
        ['l', 101.0, 0.5, 101.0, 2.0],
        ['t', 'length', 1.0, 1.25, 100.0, 1.25, '1e+02'],
        ['r', 'node', 1.0, 0, 750.0, 3.0, 'A', {}],
        ['l', 101.0, 0.5, 301.0, 0.5],
        ['t', 'length', 101.0, 0.5, 200.0, 0.5, '2e+02'],
        ['r', 'node', 101.0, 0, 200.0, 1.0, 'B', {}],
        ['t', 'name', 301.2, 0.6666666666666666, -1, 0.5, 'B'],
        ['l', 101.0, 2.0, 451.0, 2.0],
        ['l', 451.0, 1.5, 451.0, 2.5],
        ['t', 'length', 101.0, 2.0, 350.0, 1.0, '3.5e+02'],
        ['r', 'node', 101.0, 1.0, 650.0, 2.0, 'E', {}],
        ['l', 451.0, 1.5, 701.0, 1.5],
        ['t', 'length', 451.0, 1.5, 250.0, 0.5, '2.5e+02'],
        ['r', 'node', 451.0, 1.0, 250.0, 1.0, 'C', {}],
        ['t', 'name', 701.2, 1.6666666666666665, -1, 0.5, 'C'],
        ['l', 451.0, 2.5, 751.0, 2.5],
        ['t', 'length', 451.0, 2.5, 300.0, 0.5, '3e+02'],
        ['r', 'node', 451.0, 2.0, 300.0, 1.0, 'D', {}],
        ['t', 'name', 751.2, 2.6666666666666665, -1, 0.5, 'D']]

    print('<-', tree_text)
    print(t)
    print('->', list(drawer.draw(t)))


def test_intersects():
    r1 = Box(0, 0, 10, 20)
    r2 = Box(-5, 0, 10, 20)
    assert draw.intersects(r1, r2)

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

    for i in range(len(rects) - 1):
        r1 = rects[i]
        print(f'{r1} intersects...')
        for j in range(i + 1, len(rects)):
            r2 = rects[j]
            print(f'    {r2} -> ', draw.intersects(r1, r2))

    assert draw.intersects(rects[0], rects[1])
    assert not draw.intersects(rects[1], rects[2])
    assert draw.intersects(rects[2], rects[3])


def test_size():
    t = tree.loads('(a:2,b:3,c:4)d;')
    drawer = draw.DrawerFull(zoom=(10, 10))
    assert drawer.node_size(t) == (5, 3)
    assert drawer.content_size(t) == (1, 3)
    assert drawer.children_size(t) == (4, 3)



def main():
    tests = [f for name, f in globals().items() if name.startswith('test_')]
    try:
        for f in tests:
            run(f)
    except (KeyboardInterrupt, EOFError):
        pass


def run(f):
    while True:
        answer = input('Run %s ? [y/N] ' % f.__name__).lower()
        if answer in ['y', 'n', '']:
            break
    if answer.startswith('y'):
        f()



if __name__ == '__main__':
    main()
