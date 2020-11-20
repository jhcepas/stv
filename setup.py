#!/usr/bin/env python3

from setuptools import setup
from glob import glob

setup(
    name='ete',
    version='4.0',
    description='Visualization of huge trees with smart zooming',
    author='Jaime Huerta-Cepas, Jordi Burguet-Castell ',
    author_email='jhcepas@gmail.com, jordi.burguet.castell@gmail.com',
    license='GPLv3',
    url='http://etetoolkit.org',
    packages=['ete'],
    data_files=[
        ('server', glob('ete/static/gui.*')),
        ('server/external', glob('ete/static/external/*')),
        ('sql', glob('tests/*.sql')),
        ('example_tree_data', glob('tests/example_tree_data/*'))])
