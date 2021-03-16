#!/usr/bin/env python3

"""
Convert from strange newick formats.
"""

import sys
from os.path import abspath, dirname, exists
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

import re
import random
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter as fmt

from ete import tree


def main():
    args = get_args()

    print(f'Loading tree from {args.treefile} ...')
    try:
        t = tree.load(open(args.treefile))
        sample_nodes = get_sample_nodes(t)
    except (FileNotFoundError, tree.NewickError, ValueError) as e:
        sys.exit(f'Problem with newick file "{args.treefile}": {e}')

    convert_fn = get_convert_fn(sample_nodes)

    if convert_fn:
        fname = args.output or (args.treefile.rsplit('.', 1)[0] + '_norm.tree')
        if exists(fname):
            sys.exit(f'Output file already exists: {fname}')

        print(args.treefile, '->', fname)

        for node in t:
            convert_fn(node)

        tree.dump(t, open(fname, 'wt'))
    else:
        print('Tree is not in a known weird format. Not converting.')


def get_args():
    "Return the command-line arguments"
    parser = ArgumentParser(description=__doc__, formatter_class=fmt)
    add = parser.add_argument  # shortcut
    add('treefile', help='file with the tree in newick format')
    add('-o', '--output', default='', help='output file')
    return parser.parse_args()


def get_sample_nodes(t, k=10):
    "Return a list of internal nodes and a list of leaves"
    internals = [n for n in t if not n.is_leaf and not n == t]
    leaves = [n for n in t if n.is_leaf and not n == t]
    return random.sample(internals, k), random.sample(leaves, k)


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
                    node.length = -1
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
