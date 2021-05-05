# Overview

There are two main parts of the Tree Explorer:

* A module (`ete`) that handles trees and their graphical
  representation.
* A server (`server.py`) that exposes as an api those graphical capabilities
  for a set of trees loaded in memory, and also serves a gui to explore
  the trees interactively by making use of that api.

The module and the server are written in python. For efficiency
reasons, the `tree` submodule is written in
[cython](https://cython.org/), which makes the parser about twice as
fast while making the final tree take about half the memory.

The server acts as a *backend* to the requests made by the *frontend*,
which is written in javascript.


## Project Layout

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
