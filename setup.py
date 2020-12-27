#!/usr/bin/env python3

from setuptools import setup
from glob import glob
from Cython.Build import cythonize

setup(
    name='ete',
    version='4.0',
    description='Visualization of huge trees with smart zooming',
    author='Jaime Huerta-Cepas, Jordi Burguet-Castell ',
    author_email='jhcepas@gmail.com, jordi.burguet.castell@gmail.com',
    license='GPLv3',
    url='http://etetoolkit.org',
    packages=['ete'],
    ext_modules = cythonize('ete/*.pyx', language_level='3'),
    scripts=glob('scripts/*.py'),
    data_files=[
        ('server', glob('scripts/static/*.*')),
        ('server/external', glob('scripts/static/external/*')),
        ('sql', glob('scripts/*.sql')),
        ('examples', glob('examples/*'))])
