#!/usr/bin/env python3

"""
Tests for drawing trees.

To run with pytest, but you can run interactively too if you want.
"""

import sys
from os.path import abspath, dirname
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

from ete import tree, draw
Size, Rect = draw.Size, draw.Rect


def test_draw_elements():
    assert draw.draw_line((1, 2), (3, 4)) == \
        ['l', 1, 2, 3, 4]
    assert draw.draw_rect(Rect(1, 2, 3, 4)) == \
        ['r', 1, 2, 3, 4]
    assert draw.draw_text(Rect(1, 2, 3, 4), 'hello') == \
        ['t', 1, 2, 3, 4, 'hello']
    assert draw.draw_name(Rect(1, 2, 3, 4), 'world') == \
        ['tn', 1, 2, 3, 4, 'world']
    assert draw.draw_label(Rect(1, 2, 3, 4), 'again') == \
        ['tl', 1, 2, 3, 4, 'again']


def test_store_sizes():
    tree_text = '((B:2,(C:2.5,D:3)E:3.5)A:1)F;'
    t = tree.loads(tree_text)
    assert not hasattr(t, 'content_size') and not hasattr(t, 'childs_size')

    draw.store_sizes(t)
    for node in t:
        assert hasattr(node, 'content_size') and hasattr(node, 'childs_size')

    assert t.content_size == Size(1, 24)
    assert t.childs_size == Size(7.5, 24)

    assert draw.node_size(t) == Size(8.5, 24)


def test_draw_content_inline():
    t = tree.Tree('A:10')
    draw.store_sizes(t)
    drawer1 = draw.DrawerCool()
    print('<-', t)
    print('->', list(drawer1.draw_content_inline(t)))
    assert list(drawer1.draw_content_inline(t)) == [
        ['tl', 0, 4.0, 10.0, 4.0, '10']]
    print('<-', t, 'zoom=(0.1, 0.1)')
    drawer2 = draw.DrawerCool(zoom=(0.1, 0.1))
    print('->', list(drawer2.draw_content_inline(t)))
    assert list(drawer2.draw_content_inline(t)) == [
        ['r', 0, 0.0, 10.0, 4.0]]


def test_draw_tree():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)
    draw.store_sizes(t)
    drawer = draw.DrawerCool()
    elements = list(drawer.draw(t))
    print(elements)
    assert elements == [
        ['l', 0, 12.0, 1, 12.0],
        ['l', 1, 12.0, 1, 12.0],
        ['l', 1, 12.0, 101.0, 12.0],
        ['tl', 1, 12.0, 100.0, 12.0, '1e+02'],
        ['l', 101.0, 12.0, 101.0, 4.0],
        ['l', 101.0, 4.0, 301.0, 4.0],
        ['tl', 101.0, 4.0, 200.0, 4.0, '2e+02'],
        ['tn', 303.0, 5.333333333333333, 0, 4.0, 'B'],
        ['a', 'tn', 101.0, 0.0, 0, 4.0, 'B'],
        ['r', 301.0, 0, 0, 0],
        ['l', 101.0, 12.0, 101.0, 16.0],
        ['l', 101.0, 16.0, 451.0, 16.0],
        ['tl', 101.0, 16.0, 350.0, 8.0, '3.5e+02'],
        ['l', 451.0, 16.0, 451.0, 12.0],
        ['l', 451.0, 12.0, 701.0, 12.0],
        ['tl', 451.0, 12.0, 250.0, 4.0, '2.5e+02'],
        ['tn', 703.0, 13.333333333333332, 0, 4.0, 'C'],
        ['a', 'tn', 451.0, 8.0, 0, 4.0, 'C'],
        ['r', 701.0, 8, 0, 0],
        ['l', 451.0, 16.0, 451.0, 20.0],
        ['l', 451.0, 20.0, 751.0, 20.0],
        ['tl', 451.0, 20.0, 300.0, 4.0, '3e+02'],
        ['tn', 753.0, 21.333333333333332, 0, 4.0, 'D'],
        ['a', 'tn', 451.0, 16.0, 0, 4.0, 'D'],
        ['r', 751.0, 16, 0, 0]]
    print('<-', tree_text)
    print(t)
    print('->', list(drawer.draw(t)))


def test_intersects():
    r1 = Rect(0, 0, 10, 20)
    r2 = Rect(-5, 0, 10, 20)
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
                rects.append(Rect(x, y, w, h))
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
