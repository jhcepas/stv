# Overview

There are two main parts of the Tree Explorer:

* A module (`ete`) that handles trees and their graphical
  representation.
* A server (`server.py`) that exposes those graphical capabilities for
  a set of trees loaded in memory, and also serves a gui to explore
  the trees interactively by making use of that api.


## Project layout

The principal files of the project are:

```sh
ete/  # the module directory
    tree.pyx  # the Tree class and newick parser
    draw.py  # drawing classes and functions to represent a tree
scripts/
    server.py  # http server that exposes an api to interact with trees
    static/
        gui.html  # entry point for the interactive visualization (html)
        js/
            gui.js  # entry point for the interactive visualization (js)
```

For a more detailed view, see the [detailed layout](detailed_layout.md).
