#!/usr/bin/env python3

"""
Convert from strange newick formats.
"""

import sys
from os.path import abspath, dirname, basename
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

import re
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter as fmt

from ete import tree


def main():
    args = get_args()
    try:
        t = tree.load(open(args.treefile))
        assert is_informative_enough(t), 'Cannot get enough information'
    except (FileNotFoundError, tree.NewickError, AssertionError) as e:
        sys.exit(f'Problem with newick file "{args.treefile}": {e}')

    convert = get_convert_fn(get_sample_nodes(t))

    if convert:
        name = args.name or basename(args.treefile).rsplit('.', 1)[0]
        fname = name + '_converted.tree'

        print(args.treefile, '->', fname)

        for node in t:
            convert(node)
        tree.dump(t, open(fname, 'wt'))
    else:
        print('Not converting', args.treefile)


def get_args():
    "Return the command-line arguments"
    parser = ArgumentParser(description=__doc__, formatter_class=fmt)
    add = parser.add_argument  # shortcut
    add('treefile', help='file with the tree in newick format (- for stdin)')
    add('-n', '--name', default='', help='name of the tree')
    return parser.parse_args()


def is_informative_enough(t):
    return not (t.is_leaf or t.children[0] == t.children[-1] or
                t.children[0].is_leaf or t.children[-1].is_leaf)


def get_sample_nodes(t):
    "Return a set of internal nodes and a set of leaves"
    sample_internals = set()
    sample_leaves = set()

    node = t[0]
    while not node.is_leaf:
        sample_internals.add(node)
        node = node.children[-1]
    sample_leaves.add(node)

    node = t[-1]
    while not node.is_leaf:
        sample_internals.add(node)
        node = node.children[-1]
    sample_leaves.add(node)

    return sample_internals, sample_leaves


def get_convert_fn(sample_nodes):
    "Return a function to convert a node, based on how the sample nodes look"
    sample_internals, sample_leaves = sample_nodes

    if all(re.match(r'\d+\.\w+', n.name) for n in sample_leaves):
        try:
            for node in sample_internals:
                node.name == '' or float(node.name)

            def convert(node):
                if node.is_leaf:
                    taxid, name = node.name.split('.', 1)
                    node.properties['taxid'] = taxid
                    node.name = name
                else:
                    if node.name:
                        node.properties['support'] = float(node.name)
                        node.name = ''
        except ValueError:
            def convert(node):
                if node.is_leaf:
                    taxid, name = node.name.split('.', 1)
                    node.properties['taxid'] = taxid
                    node.name = name
                if node.length == 1:
                    node.length = - 1
        return convert
    elif (all('sci_name' in node.properties for node in sample_internals) and
          all('sci_name' in node.properties for node in sample_leaves)):
        def convert(node):
            node.name = node.properties.get('sci_name', '')
            if 'taxid' in node.properties:
                node.properties = {'taxid': node.properties['taxid']}
            if node.length == 1:
                node.length = -1
        return convert
    else:
        return None



if __name__ == '__main__':
    main()
