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

    future_root = add_intermediate(node)

    old_root, node_id = get_root_id(future_root)

    current = old_root  # current root, which will change in each iteration
    for child_pos in node_id:
        current = rehang(current, child_pos)

    if len(old_root.children) == 1:
        substitute(old_root, old_root.children[0])

    return current


def add_intermediate(node):
    "Add an intermediate parent to the given node and return it"
    parent = node.parent

    parent.children.remove(node)  # detach from parent

    intermediate = Tree('', children=[node])  # create intermediate node
    intermediate.parent = parent

    if node.length >= 0:  # split length between the new and old nodes
        node.length = intermediate.length = node.length / 2

    parent.children.append(intermediate)

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
    # Swap parenthood.
    child = node.children.pop(child_pos)
    child.children.append(node)
    node.parent, child.parent = child, node.parent

    swap_branch_properties(node, child)  # so they reflect the rehanging
    # The branch properties of a node reflect its relation wrt its parent.

    update_size(node)   # since their total length till the furthest leaf and
    update_size(child)  # their total number of leaves will have changed

    return child  # which is now the parent of its previous parent


def swap_branch_properties(n1, n2):
    "Swap between nodes n1 and n2 all their branch properties"
    # "length" (encoded as a data attribute) is a branch property -> swap
    n1.length, n2.length = n2.length, n1.length

    # "name" (also a data attribute) is a node property -> don't swap

    # "support" (encoded in the properties dict) is a branch property -> swap
    s1, s2 = n1.properties.get('support'), n2.properties.get('support')
    n1.properties.pop('support', None)
    n2.properties.pop('support', None)
    if s1:
        n2.properties['support'] = s1
    if s2:
        n1.properties['support'] = s2

    # And that's it. I don't know of any other standard branch properties.


def substitute(old, new):
    "Substitute old node for new node in the tree where the old node was"
    if old.length > 0:
        new.length += old.length  # add its length to the new if it has any

    parent = old.parent
    parent.children.remove(old)
    parent.children.append(new)
    new.parent = parent


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
