"""
Tests for tree-related functions. To run with pytest.
"""

import os
PATH = os.path.abspath(f'{os.path.dirname(__file__)}/..')

import sys
sys.path.insert(0, PATH)

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
(a:b)c;
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
    assert not node1.children
    assert node2.name == '' and node2.length == 22 and node2.properties == {}
    assert node2.content == ':22'
    assert not node2.children
    assert node3.name == 'node3' and node3.length == -1
    assert node3.properties == {}
    assert node3.content == 'node3'
    assert node3.children == [node1, node2]

    t = tree.Tree('(b:2,c:3,(e:4[&&NHX:k1=v1:k2=v2],),)a;')
    assert t.content == 'a' and len(t.children) == 4
    node_b = t.children[0]
    assert node_b.content == 'b:2' and not node_b.children
    node_c = t.children[1]
    assert node_c.content == 'c:3' and not node_c.children
    node_d = t.children[2]
    assert node_d.content == '' and len(node_d.children) == 2
    node_e = node_d.children[0]
    assert node_e.content == 'e:4[&&NHX:k1=v1:k2=v2]' and not node_e.children
    node_f = node_d.children[1]
    assert node_f.content == '' and not node_f.children
    node_g = t.children[3]
    assert node_g.content == '' and not node_g.children


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
        assert len(t.children) == len(tr.children)


def test_str():
    node1 = tree.Tree('node1:3.1416[&&NHX:k1=v1:k2=v2]')
    node2 = tree.Tree(':22')
    node3 = tree.Tree('node3', [node1, node2])
    assert str(node3) == """
node3
├─node1:3.1416[&&NHX:k1=v1:k2=v2]
└─:22
""".strip()


def test_iter():
    for tree_text in good_trees:
        t = tree.loads(tree_text)
        visited_nodes = set()
        visited_leaves = set()
        for node in t:
            assert type(node) == tree.Tree
            assert node not in visited_nodes and node not in visited_leaves
            visited_nodes.add(node)
            if node.is_leaf:
                visited_leaves.add(node)
        assert len(visited_nodes) == sum(1 for node in t)
        assert len(visited_leaves) == t.size[1]


def test_loads():
    # See if we read good trees without throwing exceptions.
    for tree_text in good_trees:
        t = tree.loads(tree_text)

    # Do more exhaustive tests on a single tree.
    t = tree.loads('(b:2,c:3,(e:4[&&NHX:k1=v1:k2=v2],),)a;')
    assert t.content == 'a' and len(t.children) == 4
    node_b = t.children[0]
    assert node_b.content == 'b:2' and not node_b.children
    node_c = t.children[1]
    assert node_c.content == 'c:3' and not node_c.children
    node_d = t.children[2]
    assert node_d.content == '' and len(node_d.children) == 2
    node_e = node_d.children[0]
    assert node_e.content == 'e:4[&&NHX:k1=v1:k2=v2]' and not node_e.children
    node_f = node_d.children[1]
    assert node_f.content == '' and not node_f.children
    node_g = t.children[3]
    assert node_g.content == '' and not node_g.children


def test_read_nodes():
    # See if we read good lists of nodes without throwing exceptions.
    for tree_text in good_trees:
        last_parenthesis = tree_text.rfind(')')
        if last_parenthesis != -1:
            nodes_text = tree_text[:last_parenthesis+1]
            nodes, _ = tree.read_nodes(nodes_text)

    # Do more exhaustive tests on a single list of nodes.
    nodes, pos = tree.read_nodes('(b:2,c:3,(e:4[&&NHX:k1=v1:k2=v2],),)a;', 9)
    assert pos == 9 + len('(e:4[&&NHX:k1=v1:k2=v2],)')
    assert len(nodes) == 2
    assert nodes[0].content == 'e:4[&&NHX:k1=v1:k2=v2]' and not nodes[0].children
    assert nodes[1].content == '' and not nodes[1].children


def test_read_content():
    tree_text = '(a:11[&&NHX:x=foo:y=bar],b:22,,()c,(d[&&NHX:z=foo]));'
    t = tree.loads(tree_text)
    assert (t.name == '' and t.length == -1 and t.properties == {} and
        t.content == '')
    t1 = t.children[0]
    assert (t1.name == 'a' and t1.length == 11 and
        t1.properties == {'x': 'foo', 'y': 'bar'} and
        t1.content == 'a:11[&&NHX:x=foo:y=bar]' and t1.children == [])
    t2 = t.children[1]
    assert (t2.name == 'b' and t2.length == 22 and t2.properties == {} and
        t2.content == 'b:22' and t2.children == [])
    td = t.children[-1].children[-1]
    assert (td.name == 'd' and td.length == -1 and
        td.properties == {'z': 'foo'} and td.content == 'd[&&NHX:z=foo]')


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
    # Good trees should be read without throwing any exception.
    for tree_text in good_trees:
        tree.loads(tree_text)

    # Bad trees should all throw exceptions.
    for tree_text in bad_trees:
        with pytest.raises(tree.NewickError):
            tree.loads(tree_text)


def test_read_fields():
    for tree_text in good_contents:
        fields = tree.read_fields(tree_text)
        assert len(fields) == 3

    for tree_text in good_trees:
        t = tree.loads(tree_text)
        for node in t:
            content = node.content
            fields = tree.read_fields(content)
            assert len(fields) == 3


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
        t = tree.loads(tree_text)
        t_text = tree.dumps(t)
        assert t_text == tree_text
        assert tree.dumps(tree.Tree(tree_text)) == tree_text
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
    # Read bigger trees in example files and see if we do not throw exceptions.
    for fname in ['aves.tree', 'bac120_r95.tree', 'HmuY.aln2.tree']:
        tree.load(open(f'{PATH}/examples/{fname}'))


def test_tree_size():
    assert tree.loads('(a:4)c:2;').size == (6, 1)
    assert tree.loads('(a:4,b:5)c:2;').size == (7, 2)


def test_copy():
    for tree_text in good_trees:
        t1 = tree.loads(tree_text)
        t2 = tree.copy(t1)
        assert sum(1 for n in t1) == sum(1 for n in t2)  # same number of nodes
        for n1, n2 in zip(t1, t2):
            assert n1 != n2  # they are not the same python object
            assert n1.content == n2.content  # but they do look identical


def test_length_format():
    t = tree.loads('(a:0.000001,b:1.3e34)c:234.34;')

    assert tree.dumps(t) == '(a:1e-06,b:1.3e+34)c:234.34;'

    tree.LENGTH_FORMAT = '%f'
    assert tree.dumps(t) == \
        '(a:0.000001,b:12999999999999999868938755134980096.000000)c:234.340000;'

    tree.LENGTH_FORMAT = '%.2f'
    assert tree.dumps(t) == \
        '(a:0.00,b:12999999999999999868938755134980096.00)c:234.34;'

    tree.LENGTH_FORMAT = '%E'
    assert tree.dumps(t) == '(a:1.000000E-06,b:1.300000E+34)c:2.343400E+02;'


def test_getitem():
    t = tree.loads('((d:8,e:7)b:6,(f:5,g:4)c:3)a:2;')
    assert t['a'] == t
    assert t['f'] == t.children[1].children[0]
    assert t['z'] is None

    assert t['b'] == t[0] == t[[0]] == t[0,]
    assert t['d'] == t[0,0] == t[[0,0]] == t[0][0] == t[lambda n: n.length == 8]
    assert t['g'] == t[1,1] == t[lambda n: n.is_leaf and n.length < 5]
    assert t['f'] == t[-1,0] == t[-1,-2]

    with pytest.raises(IndexError):
        t[2]

    for indices in [(0, 3), (5,), (0, 0, 0)]:
        with pytest.raises(IndexError):
            t[indices]


def test_walk():
    t = tree.loads('((d,e)b,(f,g)c)a;')
    # For reference, this is what t looks like (using print(t)):
    # a
    # ├─b
    # │ ├─d
    # │ └─e
    # └─c
    #   ├─f
    #   └─g

    # Normal walk (pre-post order).
    # When nodes are visited first, they either have descendants or are leaves.
    # When nodes are visited last (coming back), their descendants are empty.
    steps = []
    for node, node_id, first in t.walk():
         steps.append((node.name, node_id, first))
    assert steps == [
        ('a', [], True),
        ('b', [0], True),  # first time visiting internal node b
        ('d', [0,0], True),  # first (and only) time visiting leaf node d
        ('e', [0,1], True),
        ('b', [0], False),  # last time visiting b
        ('c', [1], True),
        ('f', [1,0], True),
        ('g', [1,1], True),
        ('c', [1], False),
        ('a', [], False)]

    # Prunning the tree while we walk.
    steps = []
    for node, node_id, first in t.walk():
        steps.append((node.name, node_id[:], first))
        if node.name == 'b':
            node_id[:] = [None]  # do not follow the descendants of b
    assert steps == [
        ('a', [], True),
        ('b', [0], True),  # node_id has been set to [None] in the loop
        ('c', [1], True),  # so we skip all the descendants of b
        ('f', [1,0], True),
        ('g', [1,1], True),
        ('c', [1], False),
        ('a', [], False)]
