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
    assert draw.draw_text((1, 2), 'hello') == ['t', 1, 2, 10, 2, 'hello']


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
        draw.draw_text((0, 0), 'hello')]
    assert draw.drawn_size(elements) == Size(10, 5)
    print('<-', elements)
    print('->', draw.drawn_size(elements))


def test_store_sizes():
    tree_text = '((B:2,(C:2.5,D:3)E:3.5)A:1)F;'
    t = tree.read(tree_text)
    assert not hasattr(t, 'content_size') and not hasattr(t, 'childs_size')

    draw.store_sizes(t)
    for node in t:
        assert hasattr(node, 'content_size') and hasattr(node, 'childs_size')

    assert t.content_size == Size(103, 6)
    assert t.childs_size == Size(759, 18)

    assert draw.node_size(t) == Size(862, 18)


def test_draw_content():
    t = tree.Tree('A:10')
    draw.store_sizes(t)
    print('<-', t)
    print('->', list(draw.draw_content(t)))
    assert list(draw.draw_content(t)) == [
        ['l', 0, 3, 1000.0, 3], ['t', 1001.0, 0, 2, 2, 'A']]


def test_draw_tree():
    tree_text = '((B:200,(C:250,D:300)E:350)A:100)F;'
    t = tree.read(tree_text)
    draw.store_sizes(t)
    print(list(draw.draw(t)))
    assert list(draw.draw(t)) == [
        ['l', 0, 9.0, 100, 9.0], ['t', 101, 6.0, 2, 2, 'F'],
        ['l', 103, 9.0, 103, 9.0],
        ['l', 103, 9.0, 10103.0, 9.0], ['t', 10104.0, 6.0, 2, 2, 'A'],
        ['l', 10106.0, 9.0, 10106.0, 3.0],
        ['l', 10106.0, 3.0, 30106.0, 3.0], ['t', 30107.0, 0.0, 2, 2, 'B'],
        ['l', 10106.0, 9.0, 10106.0, 12.0],
        ['l', 10106.0, 12.0, 45106.0, 12.0], ['t', 45107.0, 9.0, 2, 2, 'E'],
        ['l', 45109.0, 12.0, 45109.0, 9.0],
        ['l', 45109.0, 9.0, 70109.0, 9.0], ['t', 70110.0, 6.0, 2, 2, 'C'],
        ['l', 45109.0, 12.0, 45109.0, 15.0],
        ['l', 45109.0, 15.0, 75109.0, 15.0], ['t', 75110.0, 12.0, 2, 2, 'D']]
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
