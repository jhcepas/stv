#!/usr/bin/env python3

"""
Add a tree to the database using the newick representation that exists in
a given file.
"""

import sys
from os.path import abspath, dirname, basename
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter as fmt

import sqlite3

from ete import tree


def main():
    args = get_args()

    try:
        fin = open(args.treefile) if args.treefile != '-' else sys.stdin
        newick = fin.read().strip()

        if not args.skip_test:
            print('Verifying newick...')
            tree.loads(newick)  # discarded, but will raise exception if invalid

        with sqlite3.connect(args.db) as con:
            c = con.cursor()

            c.execute('SELECT MAX(id) FROM trees')
            tree_id = int(c.fetchone()[0] or 0) + 1

            name = args.name or get_name(args.treefile, tree_id)

            c.execute('INSERT INTO trees VALUES (?, ?, ?, ?, ?)',
                [tree_id, args.owner, name, args.description, newick])

            c.execute('INSERT INTO user_owned_trees VALUES (?, ?)',
                [args.owner, tree_id])

            for reader_id in args.readers:
                c.execute('INSERT INTO user_reader_trees VALUES (?, ?)',
                    [reader_id, tree_id])

            print(f'Added tree {name!r} with id {tree_id} to {args.db!r}.')
    except (FileNotFoundError, tree.NewickError,
            sqlite3.OperationalError, sqlite3.IntegrityError) as e:
        sys.exit(e)



def get_name(path, tree_id):
    if path != '-':  # special one used for stdin
        return basename(path).rsplit('.', 1)[0]
    else:
        return 'Tree %d' % tree_id


def get_args():
    "Return the command-line arguments"
    parser = ArgumentParser(description=__doc__, formatter_class=fmt)

    add = parser.add_argument  # shortcut
    add('treefile', help='file with the tree in newick format (- for stdin)')
    add('--db', default='trees.db', help='sqlite database file')
    add('-n', '--name', default='', help='name of the tree')
    add('-d', '--description', default='', help='description of the tree')
    add('-o', '--owner', type=int, default=1, help='id of the owner')
    add('-r', '--readers', nargs='*', metavar='READER', type=int, default=[])
    add('-s', '--skip-test', action='store_true', help='do not verify newick')

    return parser.parse_args()



if __name__ == '__main__':
    main()
