Overview
========

ETE (Environment for Tree Exploration) is a Python programming toolkit that
assists in the automated manipulation, analysis and visualization of
phylogenetic trees. Clustering trees or any other tree-like data structure are
also supported.


Install
=======

* Install [miniconda3](https://docs.conda.io/en/latest/miniconda.html)
* Clone this repo


Then:

```sh
conda install numpy scipy qt pyqt cython pyopengl
conda activate smartview
pip install diskhash bottle tqdm
cd stv/
pip install -e .
```


Test
====

For a quick test, run:

```sh
smartview -t examples/HmuY.aln2.tree --nogui
```

and then open http://localhost:8090/static/gui.html

**You can drag with the mouse to move scene, but zoom in and out in the web
version is only possible with keystrokes Z and X.**

For a test with an alignment:

```sh
smartview -t examples/HmuY.aln2.tree -a examples/HmuY.aln2 --nogui
```


Notes
=====

Hints about the code
--------------------

* `main.py`
  * `TreeImage` instance contains all the information to render a tree
    image.
* `layout.py` -- general functions to compute dimensions and coordinates.
* `layout_circular.py` -- functions to compute coordinates and dimensions of
  trees/nodes in circular mode
* `layout_rect.py` -- functions to compute coordinates and dimensions of
  trees/nodes in circular mode
* `drawer.py` -- general functions to draw trees based on `TreeImage` instances. Generate complete images or tiles as needed.
* `gui.py` -- a graphical user interface to browse tree images.


Implementation issues
=====================

no-overlap
----------

In order to allocate space for faces, circular trees have to expand
their radius, and the way of doing this is by increases the branch
scale. This has an annoying effect on the actual size of faces when
visualizaing, as they look too small when the whole tree is fit on
screen.

Some faces could have an special flag that prevent the layout function
to allocate space for them, so they are only shown when the zoom
allows it.

branch-right positions, however, would complicate too much the
visualization, as it would break linear transformation of coordinates
among zooming.

Could both types of faces coexist?
