# API

The server exposes a [RESTful
API](https://en.wikipedia.org/wiki/Representational_state_transfer#Applied_to_web_services),
with the following endpoints (defined in `server.py:add_resources`):

```sh
/trees  # get info about all the existing trees
/trees/<string:tree_id>  # get info about the given tree
/trees/<string:tree_id>/draw  # get graphical elements to draw the tree
/trees/<string:tree_id>/newick  # get newick representation
/trees/<string:tree_id>/size  # get inner width and height of the full tree
/trees/<string:tree_id>/properties  # extra ones defined in any node
/trees/<string:tree_id>/nodecount  # total count of nodes and leaves
/trees/<string:tree_id>/search  # search for nodes
/trees/<string:tree_id>/sort  # sort branches
/trees/<string:tree_id>/root_at  # change root to a given node
/trees/<string:tree_id>/move  # move branch
/trees/<string:tree_id>/remove  # prune branche
/trees/<string:tree_id>/rename  # change the name of a node
/trees/<string:tree_id>/reload  # load from the the original newick
/login  # get a bearer token for further token authentication
/users  # get info about all users
/users/<int:user_id>  # get info about the given user
/drawers  # get a list of existing drawers
/drawers/<string:name>  # get info about a drawer
/info  # get information about the currently-logged user
/id/<path:path>  # translate between ids and names
```

This api can be directly queried with the browser (for some endpoints
that accept a GET request), or with tools such as
[curl](https://curl.se/) or [httpie](https://httpie.io/).

The frontend uses those endpoints to draw and manipulate the trees. It
works as a web application, which mainly translates the list of
graphical items coming from `/trees/<string:tree_id>/draw` into svgs.

It is possible to use the same backend and write a different frontend
(as a desktop application, or in a different language, or using a
different graphics library like [PixiJS](https://www.pixijs.com/))
while still taking advantage of all the optimizations done for the
drawing.
