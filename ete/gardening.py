"""
Tree-related operations.

Sorting, changing the root to a node, moving branches, removing (prunning)...
"""

# "Arboriculture" may be more precise than "gardening", but it's a mouthful :)

from ete.tree import Tree, update_size


def sort(tree, key=None, reverse=False):
    "Sort the tree in-place"
    key = key or (lambda node: (node.size[1], node.size[0], node.name))
    for node in tree.children:
        sort(node, key, reverse)
    tree.children.sort(key=key, reverse=reverse)


def root_at(node):
    "Return the tree of which node is part of, rerooted at the given node"
    root, node_id = get_root_id(node)

    parent = node.parent
    if not parent:
        return node

    # Add an empty parent to the node.
    i = parent.children.index(node)
    parent.children.pop(i)
    intermediate_node = Tree(':0', children=[node])
    parent.children.insert(i, intermediate_node)
    intermediate_node.parent = parent

    # Go from the actual root towards the goal node, switching contents.
    current = root
    for i in node_id:
        new = current.children.pop(i)

        new.parent, current.parent = None, new
        new.length, current.length = current.length, new.length

        new_support = new.properties.get('support')
        current_support = current.properties.get('support')
        if current_support:
            new.properties['support'] = current_support
        elif 'support' in new.properties:
            del new.properties['support']

        if new_support:
            current.properties['support'] = new_support
        elif 'support' in current.properties:
            del current.properties['support']

        new.children.append(current)

        update_size(current)
        update_size(new)

        current = new

    return current


def get_root_id(node):
    "Return the root of the tree of which node is part of, and its node_id"
    # For the returned  (root, node_id)  we have  root[node_id] == node
    positions = []
    current_root, parent = node, node.parent
    while parent:
        positions.append(parent.children.index(current_root))
        current_root, parent = parent, parent.parent
    return current_root, positions[::-1]


def move(node, shift=1):
    "Change the position of the current node with respect to its parent"
    assert node.parent, 'cannot move the root'

    siblings = node.parent.children
    pos_old = siblings.index(node)
    pos_new = (pos_old + shift) % len(siblings)
    siblings[pos_old], siblings[pos_new] = siblings[pos_new], siblings[pos_old]


def remove(node):
    "Remove the given node from its tree"
    assert node.parent, 'cannot remove the root'

    parent = node.parent
    parent.children.remove(node)

    while parent:
        update_size(parent)
        parent = parent.parent


def standardize(tree):
    "Transform from a tree not following strict newick conventions"
    if tree.length == -1:
        tree.length = 0
        update_size(tree)

    for node in tree:
        try:
            node.properties['support'] = float(node.name)
            node.name = ''
        except ValueError:
            pass
