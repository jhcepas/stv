#!/usr/bin/env python3

"""
Tests for tree-related functions.

To run with pytest, but you can run interactively too if you want.
"""

import os
PATH = os.path.abspath(f'{os.path.dirname(__file__)}/..')

import sys
sys.path.insert(0, PATH)

import random
from tempfile import TemporaryFile

import pytest

from ete import tree

good_trees = """\
;
a;
(a);
(a,b);
(,(dfd)gg);
((B:0.2,(C:0.3,D:0.4)E:0.5)A:0.1)F;
(,,(,));
(A,B,(C,D));
(A, (B, C), (D, E));
(A,B,(C,D)E)F;
(:0.1,:0.2,(:0.3,:0.4):0.5);
(:0.1,:0.2,(:0.3,:0.4):0.5):0.6;
(A:0.1,B:0.2,(C:0.3,D:0.4):0.5);
(A:0.1,B:0.2,(C:0.3,D:0.4)E:0.5)F;
((B:0.2,(C:0.3,D:0.4)E:0.5)A:0.1)F;
([&&NHX:p1=v1:p2=v2],c);
((G001575.1:0.243,G002335.1:0.2)42:0.041,G001615.1:0.246)'100.0:d__Bacteria';
(a,(b)'the_answer_is_''yes''');
""".splitlines()

bad_trees = """\
()
(();
)(;
(a,[(b,c)]);
(d,[]]);
(()());
(()a());
((),a());
([]);
([&&NHX:a,b]);
([&&NHX:a)b];
([&&NX:p1=v1:p2=v2],c);
([&&NHX:p1=v1|p2=v2],c);
""".splitlines()


good_contents = """\
Abeillia:1[&&NHX:taxid=1507328:name=Abeillia:rank=species:sci_name=Abeillia]
1:1[&&NHX:taxid=1507327:name=Abeillia - 1507327:rank=genus:sci_name=Abeillia]
GB_GCA_001771575.1:0.243
'100.0:f__XYB2-FULL-48-7':0.078
""".splitlines()


def test_constructor():
    node1 = tree.Tree('node1:3.1416[&&NHX:k1=v1:k2=v2]')
    node2 = tree.Tree(':22')
    node3 = tree.Tree('node3', [node1, node2])

    assert node1.name == 'node1'
    assert node1.length == 3.1416
    assert node1.properties == {'k1': 'v1', 'k2': 'v2'}
    assert node1.content == 'node1:3.1416[&&NHX:k1=v1:k2=v2]'
    assert not node1.childs
    assert node2.name == '' and node2.length == 22 and node2.properties == {}
    assert node2.content == ':22'
    assert not node2.childs
    assert node3.name == 'node3' and node3.length is None
    assert node3.properties == {}
    assert node3.content == 'node3'
    assert node3.childs == [node1, node2]

    t = tree.Tree('(b:2,c:3,(e:4[&&NHX:k1=v1:k2=v2],),)a;')
    assert t.content == 'a' and len(t.childs) == 4
    node_b = t.childs[0]
    assert node_b.content == 'b:2' and not node_b.childs
    node_c = t.childs[1]
    assert node_c.content == 'c:3' and not node_c.childs
    node_d = t.childs[2]
    assert node_d.content == '' and len(node_d.childs) == 2
    node_e = node_d.childs[0]
    assert node_e.content == 'e:4[&&NHX:k1=v1:k2=v2]' and not node_e.childs
    node_f = node_d.childs[1]
    assert node_f.content == '' and not node_f.childs
    node_g = t.childs[3]
    assert node_g.content == '' and not node_g.childs


def test_repr():
    # A simple example.
    node1 = tree.Tree('node1:3.1416[&&NHX:k1=v1:k2=v2]')
    node2 = tree.Tree(':22')
    node3 = tree.Tree('node3', [node1, node2])
    assert repr(node3) == ("Tree('node3', "
        "[Tree('node1:3.1416[&&NHX:k1=v1:k2=v2]', []), "
        "Tree(':22', [])])")

    # See if we recover trees from their representations (playing with eval).
    for tree_text in good_trees:
        t = tree.loads(tree_text)
        tr = eval(repr(t), {'Tree': tree.Tree})  # tree recovered from its repr
        assert t.name == tr.name and t.length == tr.length
        assert t.properties == tr.properties
        assert t.content == tr.content
        assert len(t.childs) == len(tr.childs)

    print(repr(node3))  # so we see it when running interactively


def test_str():
    node1 = tree.Tree('node1:3.1416[&&NHX:k1=v1:k2=v2]')
    node2 = tree.Tree(':22')
    node3 = tree.Tree('node3', [node1, node2])
    assert str(node3) == """
node3
|- node1:3.1416[&&NHX:k1=v1:k2=v2]
`- :22
""".strip()
    print(node3)  # so we see it when running interactively


def test_iter():
    for tree_text in good_trees:
        print('<-', tree_text)
        t = tree.loads(tree_text)
        print('Nodes:')
        for node in t:
            print(' ', node.content or '<empty>')
        print()


def test_loads():
    # See if we read good trees without throwing exceptions.
    for tree_text in good_trees:
        t = tree.loads(tree_text)

    # Do more exhaustive tests on a single tree.
    t = tree.loads('(b:2,c:3,(e:4[&&NHX:k1=v1:k2=v2],),)a;')
    assert t.content == 'a' and len(t.childs) == 4
    node_b = t.childs[0]
    assert node_b.content == 'b:2' and not node_b.childs
    node_c = t.childs[1]
    assert node_c.content == 'c:3' and not node_c.childs
    node_d = t.childs[2]
    assert node_d.content == '' and len(node_d.childs) == 2
    node_e = node_d.childs[0]
    assert node_e.content == 'e:4[&&NHX:k1=v1:k2=v2]' and not node_e.childs
    node_f = node_d.childs[1]
    assert node_f.content == '' and not node_f.childs
    node_g = t.childs[3]
    assert node_g.content == '' and not node_g.childs


def test_read_nodes():
    # See if we read good lists of nodes without throwing exceptions.
    for tree_text in good_trees:
        last_parenthesis = tree_text.rfind(')')
        if last_parenthesis != -1:
            nodes_text = tree_text[:last_parenthesis+1]
            print('<-', nodes_text)
            nodes, _ = tree.read_nodes(nodes_text)
            print('->', nodes, '\n')

    # Do more exhaustive tests on a single list of nodes.
    nodes, pos = tree.read_nodes('(b:2,c:3,(e:4[&&NHX:k1=v1:k2=v2],),)a;', 9)
    assert pos == 9 + len('(e:4[&&NHX:k1=v1:k2=v2],)')
    assert len(nodes) == 2
    assert nodes[0].content == 'e:4[&&NHX:k1=v1:k2=v2]' and not nodes[0].childs
    assert nodes[1].content == '' and not nodes[1].childs


def test_read_content():
    tree_text = '(a:11[&&NHX:x=foo:y=bar],b:22,,()c,(d[&&NHX:z=foo]));'
    print('<-', tree_text)
    t = tree.loads(tree_text)
    print(t)
    assert (t.name == '' and t.length == None and t.properties == {} and
        t.content == '')
    t1 = t.childs[0]
    assert (t1.name == 'a' and t1.length == 11 and
        t1.properties == {'x': 'foo', 'y': 'bar'} and
        t1.content == 'a:11[&&NHX:x=foo:y=bar]' and t1.childs == [])
    t2 = t.childs[1]
    assert (t2.name == 'b' and t2.length == 22 and t2.properties == {} and
        t2.content == 'b:22' and t2.childs == [])
    td = t.childs[-1].childs[-1]
    assert (td.name == 'd' and td.length == None and
        td.properties == {'z': 'foo'} and td.content == 'd[&&NHX:z=foo]')
    print('-> Contents look good.\n')


def test_read_quoted_name():
    assert tree.read_quoted_name("'one two'", 0) == ('one two', 9)
    assert tree.read_quoted_name("'one ''or'' two'", 0) == ("one 'or' two", 16)
    assert tree.read_quoted_name("pre-quote 'start end' post-quote", 10) == \
        ('start end', 21)
    with pytest.raises(tree.NewickError):
        tree.read_quoted_name('i do not start with quote', 0)
    with pytest.raises(tree.NewickError):
        tree.read_quoted_name("'i end without a quote", 0)


def test_is_valid():
    for tree_text in good_trees:
        print('<-', tree_text)
        tree.loads(tree_text)
        print('-> is valid\n')

    for tree_text in bad_trees:
        print('<-', tree_text)
        with pytest.raises(tree.NewickError):
            tree.loads(tree_text)
        print('-> is not valid\n')

def test_read_fields():
    for tree_text in good_contents:
        print('<-', tree_text)
        fields = tree.read_fields(tree_text)
        assert len(fields) == 3
        print('->', fields, '\n')

    for tree_text in good_trees:
        t = tree.loads(tree_text)
        for node in t:
            content = node.content
            print('<-', content)
            fields = tree.read_fields(content)
            assert len(fields) == 3
            print('->', fields, '\n')


def test_quote():
    assert tree.quote(' ') == "' '"
    assert tree.quote("'") == "''''"
    quoting_unneeded = ['nothing_special', '1234']
    for text in quoting_unneeded:
        assert tree.quote(text) == text
    quoting_needed = ['i am special', 'one\ntwo', 'this (or that)']
    for text in quoting_needed:
        assert tree.quote(text) != text
        assert tree.quote(text).strip("'") == text


def test_dumps():
    for tree_text in good_trees:
        if ' ' in tree_text:
            continue  # representation of whitespaces may change and it's ok
        print('<-', tree_text)
        t = tree.loads(tree_text)
        t_text = tree.dumps(t)
        print('->', t_text)
        assert t_text == tree_text
        # NOTE: we could relax this, it is asking a bit too much really


def test_load_dump():
    for tree_text in good_trees:
        with TemporaryFile(mode='w+t') as fp:
            t1 = tree.loads(tree_text)
            tree.dump(t1, fp)
            fp.seek(0)
            t2 = tree.load(fp)
            assert repr(t1) == repr(t2)


def test_from_example_files():
    for fname in ['aves.tree', 'bac120_r95.tree', 'HmuY.aln2.tree']:
        t = tree.load(open(f'{PATH}/examples/{fname}'))
        print(t)



def create_random_tree(depth_max=8, branch_factor_max=5):
    r = lambda: random.random()  # shortcut

    name = ''.join(random.choice('abcdef') for i in range(int(r() * 10)))
    length = r() * 10
    content = '%s:%g' % (name, length)

    if depth_max < 1:
        return tree.Tree(content)

    childs = []
    for i in range(int(r() * branch_factor_max)):
        depth_max_new = depth_max - int(r() * 3)
        childs.append(create_random_tree(depth_max_new, branch_factor_max))

    return tree.Tree(content, childs)



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
