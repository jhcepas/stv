"""
Test the functionality of rooting.py. To run with pytest.
"""

import sys
from os.path import abspath, dirname
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

from ete import tree
from ete import rooting


def load_sample_tree():
    return tree.loads('((d,e)b,(f,g)c)a;')
    # a
    # ├─b
    # │ ├─d
    # │ └─e
    # └─c
    #   ├─f
    #   └─g


def strip(text):
    # Helps compare tree visualizations.
    indent = next(len(line) - len(line.lstrip())
        for line in text.splitlines() if line.strip())
    return '\n'.join(line[indent:].rstrip()
        for line in text.splitlines() if line.strip())


def test_sort():
    t = load_sample_tree()

    t2 = tree.copy(t)
    rooting.sort(t2)
    assert str(t2) == str(t)

    rooting.sort(t2, reverse=True)
    assert str(t2) == strip("""
        a
        ├─c
        │ ├─g
        │ └─f
        └─b
          ├─e
          └─d
    """)

    t3 = tree.loads('((f,g)b,c,d,((j,k)h,i)e)a;')
    rooting.sort(t3, key=lambda node: len(node.children))
    assert str(t3) == strip("""
        a
        ├─c
        ├─d
        ├─b
        │ ├─f
        │ └─g
        └─e
          ├─i
          └─h
            ├─j
            └─k
""")


def test_root_at():
    t = load_sample_tree()

    t = rooting.root_at(t[0,1])
    assert str(t) == strip("""
        e
        └─b
          ├─d
          └─a
            └─c
              ├─f
              └─g
    """)


    t = rooting.root_at(t['d'])
    assert str(t) == strip("""
        d
        └─b
          ├─a
          │ └─c
          │   ├─f
          │   └─g
          └─e
    """)

    t = rooting.root_at(t['c'])
    assert str(t) == strip("""
        c
        ├─f
        ├─g
        └─a
          └─b
            ├─e
            └─d
    """)

    t = rooting.root_at(t['a'])
    assert str(t) == strip("""
        a
        ├─b
        │ ├─e
        │ └─d
        └─c
          ├─f
          └─g
    """)


def test_get_root_id():
    t = load_sample_tree()

    for node_name, node_id in [
            ('a', []),
            ('b', [0]),
            ('c', [1]),
            ('d', [0,0]),
            ('e', [0,1]),
            ('f', [1,0]),
            ('g', [1,1])]:
        node = t[node_name]
        assert rooting.get_root_id(node) == (t, node_id)
        assert node == t[node_id]


def test_move():
    t = load_sample_tree()

    rooting.move(t['b'])
    assert str(t) == strip("""
        a
        ├─c
        │ ├─f
        │ └─g
        └─b
          ├─d
          └─e
    """)


def test_remove():
    t = load_sample_tree()

    rooting.remove(t['c'])
    assert str(t) == strip("""
        a
        └─b
          ├─d
          └─e
    """)

    rooting.remove(t['d'])
    assert str(t) == strip("""
        a
        └─b
          └─e
    """)
