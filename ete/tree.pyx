"""
Class to represent trees (which are nodes connected to other nodes) and
functions to read and write them.

The text representation of the trees are expected to be in the newick format:
https://en.wikipedia.org/wiki/Newick_format
"""

from collections import namedtuple


class NewickError(Exception):
    pass

LENGTH_FORMAT = '%g'  # format used to represent the length as a string


cdef class Tree:
    cdef public str name
    cdef public double length
    cdef public dict properties
    cdef public Children children
    cdef public Tree parent
    cdef public (double, double) size  # sum of lenghts, number of leaves

    def __init__(self, content='', children=None):
        self.parent = None
        if not content.startswith('('):
            self.init_normal(content.rstrip(';'), children)
            # the rstrip() avoids ambiguity when the full tree is just ";"
        else:
            if children:
                raise NewickError('init from newick cannot have children')
            self.init_from_newick(content)

    def init_normal(self, content, children):
        self.content = content
        self.children = Children(self, children or [])
        update_size(self)

    def init_from_newick(self, tree_text):
        tree = loads(tree_text)
        self.content = tree.content
        self.children = Children(self, tree.children)
        self.size = tree.size

    @property
    def content(self):
        return content_repr(self)

    @content.setter
    def content(self, content):
        self.name, self.length, self.properties = get_content_fields(content)

    @property
    def is_leaf(self):
        return not self.children

    def walk(self):
        return walk(self)

    def copy(self):
        return copy(self)

    def __iter__(self):
        "Yield all the nodes of the tree in preorder"
        yield self
        for node in self.children:
            yield from node

    def __getitem__(self, node_id):
        "Return the node that matches the given node_id, or None"
        if type(node_id) == str:  # node_id can be the name of a node
            return next((node for node in self if node.name == node_id), None)
        elif type(node_id) == int:  # or the index of a child
            return self.children[node_id]
        else:                       # or a list/tuple of the (sub-sub-...)child
            node = self
            for i in node_id:
                node = node.children[i]
            return node

    def __repr__(self):
        children_reprs = ', '.join(repr(node) for node in self.children)
        return 'Tree(%r, [%s])' % (self.content, children_reprs)

    def __str__(self):
        return to_str(self)


cdef class Children(list):
    "A list that automatically sets the parent of its elements"

    cdef public Tree parent

    def __init__(self, parent, nodes=()):
        super().__init__(nodes)
        self.parent = parent
        for node in nodes:
            node.parent = self.parent

    def append(self, node):
        super().append(node)
        node.parent = self.parent

    def __iadd__(self, nodes):
        for node in nodes:
            node.parent = self.parent
        return super().__iadd__(nodes)


def to_str(tree, are_last=None):
    "Return a string with a visual representation of the tree"
    are_last = are_last or []
    line = get_branches_repr(are_last) + (tree.content or '<empty>')
    return '\n'.join([line] +
        [to_str(node, are_last + [False]) for node in tree.children[:-1]] +
        [to_str(node, are_last + [True])  for node in tree.children[-1:]])


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


def update_size(node):
    sumlengths, nleaves = get_size(node.children)
    node.size = (abs(node.length) + sumlengths, max(1, nleaves))


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


# Position on the tree: current node, number of visited children.
TreePos = namedtuple('TreePos', 'node nch')

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
        return tuple(branch.nch for branch in self.visiting[:-1])

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


def copy(tree):
    "Return a copy of the tree"
    return Tree(tree.content, children=[copy(node) for node in tree.children])


# Functions that depend on the tree being represented in Newick format.

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

        pos = skip_spaces_and_comments(nodes_text, pos)

        if nodes_text[pos] == '(':
            children, pos = read_nodes(nodes_text, pos)
        else:
            children = []

        content, pos = read_content(nodes_text, pos)

        nodes.append(Tree(content, children))

    return nodes, pos+1


def skip_spaces_and_comments(text, int pos):
    "Return position in text after pos and after all whitespaces and comments"
    while pos < len(text) and text[pos] in ' \t\r\n[':
        if text[pos] == '[':
            if text[pos+1] == '&':  # special annotation
                return pos
            else:
                pos = text.find(']', pos+1)  # skip comment
        pos += 1  # skip whitespace and comment endings
    return pos


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
                return text[start:pos].replace("''", "'"), pos
            pos += 2
        else:
            pos += 1

    raise NewickError(f'unfinished quoted name: {text[start:]}')


def get_content_fields(content):
    """Return name, length, properties from the content (as a newick) of a node

    Example:
      'abc:123[&&NHX:x=foo:y=bar]' -> ('abc', 123, {'x': 'foo', 'y': 'bar'})
    """
    cdef double length
    if content.startswith("'"):
        name, pos = read_quoted_name(content, 0)
        pos = skip_spaces_and_comments(content, pos+1)
    else:
        name, pos = read_content(content, 0, endings=':[')

    if pos < len(content) and content[pos] == ':':
        pos = skip_spaces_and_comments(content, pos+1)
        length_txt, pos = read_content(content, pos, endings='[ ')
        try:
            length = float(length_txt)
        except ValueError:
            raise NewickError('invalid number %r in %r' % (length_txt, content))
    else:
        length = -1

    pos = skip_spaces_and_comments(content, pos)

    if pos < len(content) and content[pos] == '[':
        pos_end = content.find(']', pos+1)
        properties = get_properties(content[pos+1:pos_end])
    elif pos >= len(content):
        properties = {}
    else:
        raise NewickError('malformed content: %r' % content)

    return name, length, properties


def get_properties(text):
    """Return a dict with the properties extracted from the text in NHX format

    Example: '&&NHX:x=foo:y=bar' -> {'x': 'foo', 'y': 'bar'}
    """
    try:
        assert text.startswith('&&NHX:'), 'unknown annotation (not "&&NHX")'
        return dict(pair.split('=') for pair in text[len('&&NHX:'):].split(':'))
    except (AssertionError, ValueError) as e:
        raise NewickError('invalid NHX format (%s) in text %r' % (e, text))


def content_repr(node):
    "Return content of a node as represented in newick format"
    length_str = f':{LENGTH_FORMAT}' % node.length if node.length >= 0 else ''
    pairs_str = ':'.join('%s=%s' % kv for kv in node.properties.items())
    props_str = f'[&&NHX:{pairs_str}]' if pairs_str else ''
    return quote(node.name) + length_str + props_str


def quote(name, escaped_chars=" \t\r\n()[]':;,"):
    "Return the name quoted if it has any characters that need escaping"
    if any(c in name for c in escaped_chars):
        return "'%s'" % name.replace("'", "''")  # ' escapes to '' in newicks
    else:
        return name


def dumps(tree):
    "Return newick representation from tree"
    children_text = ','.join(dumps(node).rstrip(';') for node in tree.children)
    return (f'({children_text})' if tree.children else '') + tree.content + ';'


def dump(tree, fp):
    fp.write(dumps(tree))
