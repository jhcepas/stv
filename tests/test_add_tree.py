#!/usr/bin/env python3

"""
Tests for add_tree.py.

To run with pytest, but you can run interactively too if you want.
"""

import sys
import os
PATH = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, f'{PATH}/..')
from tempfile import NamedTemporaryFile

import pytest


def exec(command):
    print(command)
    assert os.system(command) == 0


def test_add_trees_to_db():
    path_trees = f''
    with NamedTemporaryFile() as fp:
        exec(f'sqlite3 {fp.name} < {PATH}/create_tables.sql')
        exec(f'sqlite3 {fp.name} < {PATH}/sample_data.sql')

        exec(f'{PATH}/add_tree.py --db {fp.name} --name with_test '
                f'{PATH}/example_tree_data/HmuY.aln2.tree')

        add_all(db=fp.name)

        with pytest.raises(AssertionError):
            exec(f'{PATH}/add_tree.py --db {fp.name} nonexistent_file')


def add_all(db):
    path_trees = f'{PATH}/example_tree_data'
    for fname in ['aves.tree', 'bac120_r95.tree', 'HmuY.aln2.tree']:
        cmd = f'{PATH}/add_tree.py --db {db} --no-verify {path_trees}/{fname}'
        exec(cmd)
        with pytest.raises(AssertionError):
            exec(cmd)
            # the second time should fail because of repeated name


def main():
    tests = [f for name, f in globals().items() if name.startswith('test_')]
    try:
        for f in tests:
            run(f)
    except (KeyboardInterrupt, EOFError):
        pass


def run(f):
    while True:
        answer = input('Run %s ? [y/N] ' % f.__name__).lower()
        if answer in ['y', 'n', '']:
            break
    if answer.startswith('y'):
        f()



if __name__ == '__main__':
    main()
