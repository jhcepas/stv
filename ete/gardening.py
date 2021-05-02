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
    if not node.parent:
        return node

    future_root = split_branch(node)

    old_root, node_id = get_root_id(future_root)

    current = old_root  # current root, which will change in each iteration
    for child_pos in node_id:
        current = rehang(current, child_pos)

    if len(old_root.children) == 1:
        join_branch(old_root)

    return current  # which is now future_root


def split_branch(node):
    "Add an intermediate parent to the given node and return it"
    parent = node.parent

    parent.children.remove(node)  # detach from parent

    intermediate = Tree('', children=[node])  # create intermediate node

    if node.length >= 0:  # split length between the new and old nodes
        node.length = intermediate.length = node.length / 2

    if 'support' in node.properties:  # copy support if it has it
        intermediate.properties['support'] = node.properties['support']

    parent.children.append(intermediate)

    update_size(node)
    update_size(intermediate)

    return intermediate


def get_root_id(node):
    "Return the root of the tree of which node is part of, and its node_id"
    # For the returned  (root, node_id)  we have  root[node_id] == node
    positions = []
    current, parent = node, node.parent
    while parent:
        positions.append(parent.children.index(current))
        current, parent = parent, parent.parent
    return current, positions[::-1]


def rehang(node, child_pos):
    "Rehang node on its child at position child_pos and return it"
    child = node.children.pop(child_pos)

    child.parent = node.parent  # swap parenthood
    child.children.append(node)

    swap_branch_properties(child, node)  # to reflect the new parenthood

    update_size(node)   # since their total length till the furthest leaf and
    update_size(child)  # their total number of leaves will have changed

    return child  # which is now the parent of its previous parent


def swap_branch_properties(n1, n2):
    "Swap between nodes n1 and n2 their branch-related properties"
    # The branch properties of a node reflect its relation w.r.t. its parent.

    # "length" (a data attribute) is a branch property -> swap
    n1.length, n2.length = n2.length, n1.length

    # "support" (in the properties dictionary) is a branch property -> swap
    swap_property(n1, n2, 'support')


def swap_property(n1, n2, pname):
    "Swap property pname between nodes n1 and n2"
    p1 = n1.properties.pop(pname, None)
    p2 = n2.properties.pop(pname, None)
    if p1:
        n2.properties[pname] = p1
    if p2:
        n1.properties[pname] = p2


def join_branch(node):
    "Substitute node for its only child"
    assert len(node.children) == 1, 'cannot join branch with multiple children'

    child = node.children[0]

    if 'support' in node.properties or 'support' in child.properties:
        assert node.properties.get('support') == child.properties.get('support')

    if node.length > 0:
        child.length += node.length  # restore total length

    parent = node.parent
    parent.children.remove(node)
    parent.children.append(child)


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
        if not node.is_leaf:
            try:
                node.properties['support'] = float(node.name)
                node.name = ''
            except ValueError:
                pass
