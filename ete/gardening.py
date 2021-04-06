"""
Tree-related operations.

Sorting, changing the root to a node, moving branches, removing (prunning)...
"""

# "Arboriculture" may be more precise than "gardening", but it's a mouthful!

from ete.tree import Tree, update_metrics, update_branch_height


def sort(tree, key=None, reverse=False):
    "Sort the tree in-place"
    key = key or (lambda node: (node.size[1], node.size[0], node.name))
    for node in tree.children:
        sort(node, key, reverse)
    tree.children.sort(key=key, reverse=reverse)
    update_branch_height(tree)


def root_at(node):
    "Return the tree of which node is part of, rerooted at the given node"
    root, node_id = get_root_id(node)

    current_root = root
    for i in node_id:
        new_root = current_root.children.pop(i)
        new_root.parent = None
        new_root.children.append(current_root)
        current_root.parent = new_root
        update_metrics(current_root)
        update_metrics(new_root)
        current_root = new_root

    return current_root


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

    parent = node.parent
    while parent:
        update_branch_height(parent)
        parent = parent.parent


def remove(node):
    "Remove the given node from its tree"
    assert node.parent, 'cannot remove the root'

    parent = node.parent
    parent.children.remove(node)

    while parent:
        update_metrics(parent)
        parent = parent.parent


def standardize(tree):
    "Transform from a tree not following strict newick conventions"
    if tree.length == -1 and not tree.name:
        tree.length = 0
        update_metrics(tree)

    for node in tree:
        try:
            node.properties['support'] = float(node.name)
            node.name = ''
        except ValueError:
            pass
