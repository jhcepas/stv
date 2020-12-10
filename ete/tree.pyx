"""
Tree utilities.

Class to represent a tree (which is a node connected to other nodes) and
functions to read, write and validate.

The text representation of the trees are expected to be in the newick format:
https://en.wikipedia.org/wiki/Newick_format
"""


class NewickError(Exception):
    pass


class Tree:
    def __init__(self, content='', childs=None):
        self.name = ''
        self.length = None
        self.properties = {}
        if not content.startswith('('):  # normal case
            self.content = content.rstrip(';')
            self.childs = childs or []
        else:                            # newick case
            if childs:
                raise NewickError(f'newick {content} incompatible with childs')
            t = loads(content)
            self.content = t.content
            self.childs = t.childs

    @property
    def content(self):
        length_str = ':%g' % self.length if self.length is not None else ''
        pairs_str = ':'.join('%s=%s' % kv for kv in self.properties.items())
        props_str = '[&&NHX:%s]' % pairs_str if pairs_str else ''
        return quote(self.name) + length_str + props_str

    @content.setter
    def content(self, content):
        self.name, self.length, self.properties = read_fields(content)

    def __iter__(self):
        "Yield all the nodes of the tree with root at the current node"
        yield self
        for node in self.childs:
            yield from node

    def __repr__(self):
        childs_reprs = ', '.join(repr(c) for c in self.childs)
        return 'Tree(%r, [%s])' % (self.content, childs_reprs)

    def __str__(self, are_last=None):
        are_last = are_last or []
        line = get_branches_repr(are_last) + (self.content or '<empty>')
        return '\n'.join([line] +
            [node.__str__(are_last + [False]) for node in self.childs[:-1]] +
            [node.__str__(are_last + [True])  for node in self.childs[-1:]])



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
            childs, pos = read_nodes(nodes_text, pos)
        else:
            childs = []

        content, pos = read_content(nodes_text, pos)

        nodes.append(Tree(content, childs))

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

    raise NewickError('unfinished quoted name: %s' % text[start:])


def read_fields(content):
    """Return the name, length, and properties from the content of a node

    Example:
      'abc:123[&&NHX:x=foo:y=bar]' -> ('abc', 123, {'x': 'foo', 'y': 'bar'})
    """
    if content.startswith("'"):
        name, pos = read_quoted_name(content, 0)
    else:
        name, pos = read_content(content, 0, endings=':[')

    if pos < len(content) and content[pos] == ':':
        length_txt, pos = read_content(content, pos+1, endings='[')
        length = float(length_txt)
    else:
        length = None

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


def get_branches_repr(are_last):
    """Return a text line representing the open branches according to are_last

    are_last is a list of bools. It says at each level if we are the last node.
    The line has ' ' or '|' for each level, and '`' or '|' at the end.

    Example (with more spaces for clarity):
      [True , False, True , True , True ] ->
      '|             |      |      `-   '
    """
    if len(are_last) == 0:
        return ''

    prefix = ''.join('   ' if is_last else '|  ' for is_last in are_last[:-1])
    return prefix + ('`- ' if are_last[-1] else '|- ')


def quote(name, escaped_chars=" \t\r\n()[]':;,"):
    "Return the name quoted if it has any characters that need escaping"
    if any(c in name for c in escaped_chars):
        return "'%s'" % name.replace("'", "''")  # ' escapes to '' in newicks
    else:
        return name


def dumps(node):
    "Return newick representation from tree"
    childs_text = ','.join(dumps(n).rstrip(';') for n in node.childs)
    return ('(%s)' % childs_text if childs_text else '') + node.content + ';'


def dump(node, fp):
    fp.write(dumps(node))
