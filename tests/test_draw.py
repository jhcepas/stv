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
    assert draw.draw_line((1, 2), (3, 4)) == ['l', 1, 2, 3, 4]
    assert draw.draw_rect(Rect(1, 2, 3, 4)) == ['r', 1, 2, 3, 4]
    assert draw.draw_text((1, 2), 3, 'hello') == ['t', 1, 2, 3, 'hello']
    assert draw.draw_name((1, 2), 3, 'world') == ['tn', 1, 2, 3, 'world']
    assert draw.draw_length((1, 2), 3, 'again') == ['tl', 1, 2, 3, 'again']


def test_drawn_size():
    rects = [
        Rect(-3, -1, 6, 2),
        Rect(-1, -5, 3, 10)]
    assert draw.drawn_size(rects) == Size(6, 10)
    print('<-', rects)
    print('->', draw.drawn_size(rects))

    elements = [
        draw.draw_line((1, 2), (3, 4)),
        draw.draw_rect(Rect(2, -1, 3, 3)),
        draw.draw_text((0, 0), 1.5, 'hello')]
    assert draw.drawn_size(elements) == Size(5, 5)
    print('<-', elements)
    print('->', draw.drawn_size(elements))


def test_store_sizes():
    tree_text = '((B:2,(C:2.5,D:3)E:3.5)A:1)F;'
    t = tree.loads(tree_text)
    assert not hasattr(t, 'content_size') and not hasattr(t, 'childs_size')

    draw.store_sizes(t)
    for node in t:
        assert hasattr(node, 'content_size') and hasattr(node, 'childs_size')

    assert t.content_size == Size(100, 8)
    assert t.childs_size == Size(750, 24)

    assert draw.node_size(t) == Size(850, 24)


def test_draw_content_inline():
    t = tree.Tree('A:10')
    draw.store_sizes(t)
    print('<-', t)
    print('->', list(draw.draw_content_inline(t)))
    assert list(draw.draw_content_inline(t)) == [
        ['r', 0, 0.0, 5.333333333333333, 4.0]]
    assert list(draw.draw_content_inline(t, zoom=2)) == [
        ['tl', 0, 0.0, 4.0, '10']]


def test_draw_tree():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.loads(tree_text)
    draw.store_sizes(t)
    elements = list(draw.draw(t))
    print(elements)
    assert [x for x in elements if not x[0] == 'a'] == [
        ['l', 0, 12.0, 100, 12.0],
        ['l', 100, 12.0, 100, 12.0],
        ['l', 100, 12.0, 10100.0, 12.0],
        ['r', 100, 8.0, 13.333333333333334, 4.0],
        ['l', 10100.0, 12.0, 10100.0, 4.0],
        ['l', 10100.0, 4.0, 30100.0, 4.0],
        ['r', 10100.0, 0.0, 13.333333333333334, 4.0],
        ['tn', 30101.0, 1.3333333333333333, 4.0, 'B'],
        ['l', 10100.0, 12.0, 10100.0, 16.0],
        ['l', 10100.0, 16.0, 45100.0, 16.0],
        ['r', 10100.0, 12.0, 18.666666666666668, 4.0],
        ['l', 45100.0, 16.0, 45100.0, 12.0],
        ['l', 45100.0, 12.0, 70100.0, 12.0],
        ['r', 45100.0, 8.0, 18.666666666666668, 4.0],
        ['tn', 70101.0, 9.333333333333334, 4.0, 'C'],
        ['l', 45100.0, 16.0, 45100.0, 20.0],
        ['l', 45100.0, 20.0, 75100.0, 20.0],
        ['r', 45100.0, 16.0, 13.333333333333334, 4.0],
        ['tn', 75101.0, 17.333333333333332, 4.0, 'D']]
    print('<-', tree_text)
    print(t)
    print('->', list(draw.draw(t)))


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
