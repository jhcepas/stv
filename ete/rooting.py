"""
Unrooting, rooting and rerooting.
"""

from .tree import Tree, update_metrics, update_branch_height


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

    old_root = root
    for i in node_id:
        new_root = old_root.children.pop(i)
        new_root.parent = None
        new_root.children.append(old_root)
        old_root.parent = new_root
        update_metrics(old_root)
        update_metrics(new_root)
        old_root = new_root

    return old_root


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

    update_branch_height(node.parent)


def remove(node):
    "Remove the given node from its tree"
    assert node.parent, 'cannot remove the root'

    parent = node.parent
    parent.children.remove(node)

    while parent:
        update_metrics(parent)
        parent = parent.parent
