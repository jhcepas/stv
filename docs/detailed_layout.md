# Detailed Layout

There are several parts to the project.

The module `ete` can be used independently of the rest of the code. It
has submodules to create trees and parse newicks (`tree.pyx`), create
a graphical representation of trees (`draw.py`), do tree-related
operations (`gardening.py`), and parse trees in nexus files
(`nexus.py`).

The `scripts` directory contains an http server based on
[flask](https://flask.palletsprojects.com/). It manages trees that are
stored in an [sqlite](https://www.sqlite.org/) database that is
located at `scripts/instace/trees.db`. It also manages users and has a
way to deal with permissions related to managing the trees (though
that part will be unnecessary if the users are managed elsewhere). It
exposes thru an api all the operations that can be done to manage and
represent the trees.

The server also provides access to `gui.html`, which shows a gui on
the browser to explore the trees. It uses the code in `gui.js` and all
the other imported js modules in the same directory.

It also server an entry page with a short description and an easy way
to upload new trees, `upload_tree.html` (which uses `upload_tree.js`).

Finally, there are test for the different python code in `tests`, and
examples of trees in `examples`.

```sh
readme.rst
setup.py
ete/
    tree.pyx
    draw.py
    gardening.py  # tree-related operations
    nexus.py  # functions to handle trees in the nexus format
    __init__.py  # allow "import ete"
scripts/
    server.py
    add_tree.py  # add a tree to the sqlite database from a newick file
    dump_trees.py  # write to files all the existing trees in the database
    create_tables.sql  # create the tables in the database
    sample_data.sql  # fill the database with some examples
    static/  # files served for the gui and uploading
        gui.html
        gui.css
        upload_tree.html  # landing page with the upload tree interface
        upload_tree.css
        icon.png
        logo.jpg
        js/
            gui.js
            menu.js  # initialize of the dat.gui menus
            draw.js  # call to the api to get drawing items and convert to svg
            minimap.js  # handle the current tree view on the minimap
            zoom.js
            drag.js
            download.js
            contextmenu.js  # what happens when one right-clicks on the tree
            events.js  # hotkeys, mouse events
            search.js
            collapse.js
            label.js
            tag.js
            api.js  # handle calls to the server's api
            upload_tree.js  # read given trees and upload them to the server
        external/  # where we keep a copy of external libraries
            readme.md  # description of where to find them
            dat.gui.min.js
            sweetalert2.min.js
tests/  # tests for the existing functionality, to run with pytest
    test_tree.py
    test_draw.py
    test_server.py
    test_gardening.py
    test_nexus.py
    test_add_tree.py
examples/
    HmuY.aln2.tree  # newick with support instead of name for internal nodes
    HmuY.aln2  # alignment file corresponding to HmuY.aln2.tree (unused!)
    GTDB_bact_r95.tree  # newick file with bacterias
    aves.tree  # newick with the aves part of the ncbi tree
```
