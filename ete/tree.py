"""
Tree utilities.

Class to represent a tree (which is a node connected to other nodes) and
functions to read, write and validate.

The text representation of the trees are expected to be in the newick format:
https://en.wikipedia.org/wiki/Newick_format
"""


class Tree(object):
    def __init__(self, content='', childs=None):
        self.name = ''
        self.length = None
        self.properties = {}
        if not content.startswith('('):
            if content:
                self.content = content.rstrip(';')
            self.childs = childs or []
        else:
            assert not childs, 'init with newick is not compatible with childs'
            t = read(content)
            self.content = t.content
            self.childs = t.childs

    @property
    def content(self):
        length_str = ':%g' % self.length if self.length is not None else ''
        pairs_str = ':'.join('%s=%s' % kv for kv in self.properties.items())
        props_str = '[&&NHX:%s]' % pairs_str if pairs_str else ''
        return self.name + length_str + props_str

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
        return "Tree('%s', [%s])" % (self.content, childs_reprs)

    def __str__(self, are_last=None):
        are_last = are_last or []
        line = get_branches_repr(are_last) + (self.content or '<empty>')
        return '\n'.join([line] +
            [node.__str__(are_last + [False]) for node in self.childs[:-1]] +
            [node.__str__(are_last + [True])  for node in self.childs[-1:]])


class NewickError(Exception):
    pass



def read(tree_text):
    "Return tree from its newick representation"
    if not tree_text.endswith(';'):
        raise NewickError('text ends with no ";"')

    if tree_text[0] == '(':
        nodes, pos = read_nodes(tree_text, 0)
    else:
        nodes, pos = [], 0

    content, _ = read_content(tree_text, pos)

    return Tree(content, nodes)


def read_nodes(nodes_text, pos=0):
    "Return a list of nodes and the position in the text where they end"
    # nodes_text looks like '(a,b,c)', where any element can be a list of nodes
    invalid_chars_in_content = ',();'

    if nodes_text[pos] != '(':
        raise NewickError('nodes text starts with no "("')

    nodes = []
    while nodes_text[pos] != ')':
        pos += 1
        if pos >= len(nodes_text):
            raise NewickError('nodes text ends missing a matching ")"')

        if nodes_text[pos] == '(':
            childs, pos = read_nodes(nodes_text, pos)
        else:
            childs = []

        content, pos_new = read_content(nodes_text, pos)
        if any(c in content for c in invalid_chars_in_content):
            raise NewickError(
                'invalid format between positions %d and %d' % (pos, pos_new))
        pos = pos_new

        nodes.append(Tree(content, childs))

    return nodes, pos + 1


def read_content(text, pos):
    "Return content starting at position pos in the text, and where it ends"
    end = pos
    while end < len(text) and text[end] not in ',);':
        end += 1
    return text[pos:end], end


def is_valid(tree_text):
    return (tree_text.find(';') == len(tree_text) - 1 and
        has_correct_parenthesis(tree_text) and
        has_correct_brakets(tree_text))


def has_correct_parenthesis(tree_text):
    # () can be arbitrarily nested but have to be balanced.
    valid_chars_before_open_parenthesis = '(,'

    n_open_parenthesis = 0
    previous = ''
    for c in tree_text:
        if c == '(':
            if previous not in valid_chars_before_open_parenthesis:
                return False
            n_open_parenthesis += 1
        elif c == ')':
            n_open_parenthesis -= 1
            if n_open_parenthesis < 0:
                return False
        previous = c

    if n_open_parenthesis != 0:
        return False

    return True


def has_correct_brakets(tree_text):
    # [] start with '[&&NHX:', cannot nest, and cannot contain ',' or ')'.
    invalid_chars_in_brakets = ',)'
    valid_chars_after_close_braket = ',);'  # yes, almost the same
    braket_opening = '[&&NHX:'

    open_braket = False
    for i, c in enumerate(tree_text):
        if c == '[':
            if open_braket:
                return False
            if tree_text[i:i+len(braket_opening)] != braket_opening:
                return False
            open_braket = True
        elif c == ']':
            if not open_braket:
                return False
            if tree_text[i+1] not in valid_chars_after_close_braket:
                return False
            open_braket = False
        elif open_braket and c in invalid_chars_in_brakets:
            return False

    if open_braket:
        return False

    return True


def read_fields(content):
    """Return the name, length, and properties from the content of a node

    Example:
      'abc:123[&&NHX:x=foo:y=bar]' -> ('abc', 123, {'x': 'foo', 'y': 'bar'})
    """
    properties_pos = content.find('[')
    if properties_pos != -1:
        name_length = content[:properties_pos]
        properties = read_properties(content[properties_pos:])
    else:
        name_length = content
        properties = {}

    if ':' in name_length:
        name, length_text = name_length.split(':', 1)
        length = float(length_text)
    else:
        name, length = name_length, None

    return name, length, properties


def read_properties(text):
    """Return a dict with the properties read from the text in NHX format

    Example: '[&&NHX:x=foo:y=bar]' -> {'x': 'foo', 'y': 'bar'}
    """
    try:
        assert text.startswith('[&&NHX:') and text.endswith(']'), \
            'properties not contained between "[&&NHX:" and "]"'
        pairs = text[len('[&&NHX:'):-1].split(':')
        return dict(pair.split('=', 1) for pair in pairs)
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


def write(node):
    "Return newick representation from tree"
    childs_text = ','.join(write(n).rstrip(';') for n in node.childs)
    return ('(%s)' % childs_text if childs_text else '') + node.content + ';'
