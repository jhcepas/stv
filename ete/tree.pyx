"""
Class to represent trees (which are nodes connected to other nodes) and
functions to read and write them.

The text representation of the trees are expected to be in the newick format:
https://en.wikipedia.org/wiki/Newick_format
"""

from collections import namedtuple

TreePos = namedtuple('TreePos', 'node nch')
# Position on the tree: current node, number of visited children.


class NewickError(Exception):
    pass


LENGTH_FORMAT = '%g'  # format used to represent the length as a string


cdef class Tree:
    cdef public str name
    cdef public double length
    cdef public dict properties
    cdef public list children
    cdef public Tree parent
    cdef public (double, double) size  # sum of lenghts, number of leaves
    cdef public double bh  # branching height (where the branch starts)

    def __init__(self, content='', children=None):
        self.parent = None
        self.name = ''
        self.length = -1
        self.properties = {}
        if not content.startswith('('):
            self.init_normal(content.rstrip(';'), children)
            # the rstrip() avoids ambiguity when the full tree is just ";"
        else:
            if children:
                raise NewickError('init from newick cannot have children')
            self.init_from_newick(content)

    def init_normal(self, content, children):
        self.content = content
        self.children = children or []
        for node in self.children:
            node.parent = self
        update_metrics(self)

    def init_from_newick(self, tree_text):
        tree = loads(tree_text)
        self.content = tree.content
        self.children = tree.children
        for node in self.children:
            node.parent = self
        self.size = tree.size
        self.bh = tree.bh

    @property
    def content(self):
        length_str = f':{LENGTH_FORMAT}' % self.length if self.length >= 0 else ''
        pairs_str = ':'.join('%s=%s' % kv for kv in self.properties.items())
        props_str = f'[&&NHX:{pairs_str}]' if pairs_str else ''
        return quote(self.name) + length_str + props_str

    @content.setter
    def content(self, content):
        self.name, self.length, self.properties = read_fields(content)

    @property
    def is_leaf(self):
        return not self.children

    def walk(self):
        return walk(self)

    def __iter__(self):
        "Yield all the nodes of the tree in preorder"
        yield self
        for node in self.children:
            yield from node

    def __getitem__(self, node_id):
        "Return the node that matches the given node_id, or None"
        if callable(node_id):       # node_id can be a True/False function
            return next((node for node in self if node_id(node)), None)
        elif type(node_id) == str:  # or the name of a node
            return next((node for node in self if node.name == node_id), None)
        elif type(node_id) == int:  # or the index of a child
            return self.children[node_id]
        else:                       # or a list/tuple of the (sub-sub-...)child
            node = self
            for i in node_id:
                node = node.children[i]
            return node

    def __repr__(self):
        children_reprs = ', '.join(repr(c) for c in self.children)
        return 'Tree(%r, [%s])' % (self.content, children_reprs)

    def __str__(self):
        return to_str(self)



# Auxiliary functions.

def to_str(tree, are_last=None):
    "Return a string with a visual representation of the tree"
    are_last = are_last or []
    line = get_branches_repr(are_last) + (tree.content or '<empty>')
    return '\n'.join([line] +
        [to_str(n, are_last + [False]) for n in tree.children[:-1]] +
        [to_str(n, are_last + [True])  for n in tree.children[-1:]])


def get_branches_repr(are_last):
    """Return a text line representing the open branches according to are_last

    are_last is a list of bools. It says at each level if we are the last node.

    Example (with more spaces for clarity):
      [True , False, True , True , True ] ->
      '│             │      │      └─   '
    """
    if len(are_last) == 0:
        return ''

    prefix = ''.join('  ' if is_last else '│ ' for is_last in are_last[:-1])
    return prefix + ('└─' if are_last[-1] else '├─')


def quote(name, escaped_chars=" \t\r\n()[]':;,"):
    "Return the name quoted if it has any characters that need escaping"
    if any(c in name for c in escaped_chars):
        return "'%s'" % name.replace("'", "''")  # ' escapes to '' in newicks
    else:
        return name


def update_metrics(node):
    "Update the size and branching height of the given node"
    children = node.children
    sumlengths, nleaves = get_size(children)
    node.size = (abs(node.length) + sumlengths, max(1, nleaves))
    node.bh = node.size[1] / 2 + (0 if not children else
        (children[0].bh - children[-1].size[1] + children[-1].bh) / 2)


cdef (double, double) get_size(nodes):
    "Return the size of all the nodes stacked"
    # The size of a node is (sumlengths, nleaves) with sumlengths the length to
    # its furthest leaf (including itself) and nleaves its number of leaves.
    cdef double sumlengths, nleaves
    sumlengths = nleaves = 0
    for node in nodes:
        sumlengths = max(sumlengths, node.size[0])
        nleaves += node.size[1]
    return sumlengths, nleaves


def walk(tree):
    "Yield an iterator as it traverses the tree"
    it = Walker(tree)  # node iterator
    while it.visiting:
        if it.first_visit:
            yield it

            if it.node.is_leaf or not it.descend:
                it.go_back()
                continue

        if it.has_unvisited_branches:
            it.add_next_branch()
        else:
            yield it
            it.go_back()


class Walker:
    def __init__(self, root):
        self.visiting = [TreePos(node=root, nch=0)]
        # will look like: [(root, 2), (child2, 5), (child25, 3), (child253, 0)]
        self.descend = True

    def go_back(self):
        self.visiting.pop()
        if self.visiting:
            node, nch = self.visiting[-1]
            self.visiting[-1] = TreePos(node, nch + 1)
        self.descend = True

    @property
    def node(self):
        return self.visiting[-1].node

    @property
    def node_id(self):
        return [branch.nch for branch in self.visiting[:-1]]

    @property
    def first_visit(self):
        return self.visiting[-1].nch == 0

    @property
    def has_unvisited_branches(self):
        node, nch = self.visiting[-1]
        return nch < len(node.children)

    def add_next_branch(self):
        node, nch = self.visiting[-1]
        self.visiting.append(TreePos(node=node.children[nch], nch=0))


# Read and write.

def load(fp):
    return loads(fp.read().strip())


def loads(tree_text):
    "Return tree from its newick representation"
    if not tree_text.endswith(';'):
        raise NewickError('text ends with no ";"')

    if tree_text[0] == '(':
        nodes, pos = read_nodes(tree_text, 0)
    else:
        nodes, pos = [], 0

    content, pos = read_content(tree_text, pos)
    if pos != len(tree_text) - 1:
        raise NewickError(f'root node ends at position {pos}, before tree ends')

    return Tree(content, nodes)


def read_nodes(nodes_text, int pos=0):
    "Return a list of nodes and the position in the text where they end"
    # nodes_text looks like '(a,b,c)', where any element can be a list of nodes
    if nodes_text[pos] != '(':
        raise NewickError('nodes text starts with no "("')

    nodes = []
    while nodes_text[pos] != ')':
        pos += 1
        if pos >= len(nodes_text):
            raise NewickError('nodes text ends missing a matching ")"')

        while nodes_text[pos] in ' \t\r\n':
            pos += 1  # skip whitespace

        if nodes_text[pos] == '(':
            children, pos = read_nodes(nodes_text, pos)
        else:
            children = []

        content, pos = read_content(nodes_text, pos)

        nodes.append(Tree(content, children))

    return nodes, pos+1


def read_content(str text, int pos, endings=',);'):
    "Return content starting at position pos in the text, and where it ends"
    start = pos
    if pos < len(text) and text[pos] == "'":
        _, pos = read_quoted_name(text, pos)
    while pos < len(text) and text[pos] not in endings:
        pos += 1
    return text[start:pos], pos


def read_quoted_name(str text, int pos):
    "Return quoted name and the position where it ends"
    if pos >= len(text) or text[pos] != "'":
        raise NewickError(f'text at position {pos} does not start with "\'"')

    pos += 1
    start = pos
    while pos < len(text):
        if text[pos] == "'":
            # Newick format escapes ' as ''
            if pos+1 >= len(text) or text[pos+1] != "'":
                return text[start:pos].replace("''", "'"), pos+1
            pos += 2
        else:
            pos += 1

    raise NewickError(f'unfinished quoted name: {text[start:]}')


def read_fields(content):
    """Return the name, length, and properties from the content of a node

    Example:
      'abc:123[&&NHX:x=foo:y=bar]' -> ('abc', 123, {'x': 'foo', 'y': 'bar'})
    """
    cdef double length
    if content.startswith("'"):
        name, pos = read_quoted_name(content, 0)
    else:
        name, pos = read_content(content, 0, endings=':[')

    if pos < len(content) and content[pos] == ':':
        length_txt, pos = read_content(content, pos+1, endings='[')
        try:
            length = float(length_txt)
        except ValueError:
            raise NewickError('invalid number %r in %r' % (length_txt, content))
    else:
        length = -1

    if pos < len(content) and content[pos] == '[':
        properties = read_properties(content[pos:])
    elif pos >= len(content):
        properties = {}
    else:
        raise NewickError('malformed content: %r' % content)

    return name, length, properties


def read_properties(text):
    """Return a dict with the properties read from the text in NHX format

    Example: '[&&NHX:x=foo:y=bar]' -> {'x': 'foo', 'y': 'bar'}
    """
    try:
        assert text.startswith('[&&NHX:') and text.endswith(']'), \
            'properties not contained between "[&&NHX:" and "]"'
        pairs = text[len('[&&NHX:'):-1].split(':')
        return dict(pair.split('=') for pair in pairs)
    except (AssertionError, ValueError) as e:
        raise NewickError('invalid NHX format (%s) in text %r' % (e, text))


def dumps(tree):
    "Return newick representation from tree"
    children_text = ','.join(dumps(node).rstrip(';') for node in tree.children)
    return (f'({children_text})' if children_text else '') + tree.content + ';'


def dump(tree, fp):
    fp.write(dumps(tree))


def copy(tree):
    "Return a copy of the tree"
    return Tree(tree.content, children=[copy(node) for node in tree.children])
