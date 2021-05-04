ETE (Environment for Tree Exploration) is a tool for phylogenetic
trees manipulation, analysis and visualization. It also supports
clustering trees or any other tree-like data structure.

In addition to the tree manipulation and drawing modules (`ete.tree`
and `ete.draw`), it includes a server that manages users and trees,
exposes a REST api and serves an interactive gui accessible from your
web browser. It is described further below.


# Installing

## Prerequisites

The tree and drawing modules just need [Python
3](https://www.python.org/downloads/) and
[Cython](https://cython.org/).

To use the server, you need in addition the following python modules:

* flask, flask-cors, flask-httpauth, flask-restful, flask-compress
* sqlalchemy


# Module

To create the module `tree` you need to first compile it with Cython:

```sh
python setup.py build_ext --inplace
```

After that, you will only need to run that command if you ever change
the source files (`ete/tree.pyx`).


# Server

The server is intended to be run as a backend to serve trees. It
exposes a REST api to consult, create and change users and trees. It
also provides methods to draw and manipulate interactively the trees,
which are used in the interactive gui that it serves at
`http://localhost:5000/static/gui.html`.


## Initializing

The default sql engine that it uses is [sqlite](https://www.sqlite.org/),
with a local file named `trees.db`. It can easily be changed to any other
(and should for scalability purposes).

You can run the backend directly with:

```sh
./server.py
```

which will start it in debug mode.

When running the backend the first time, it will create and initialize the
database (by using the files `create_tables.sql` and `sample_data.sql`,
and using the tool `add_tree.py` to add the trees from the `examples`
directory).

For a more serious usage, you can run it for example with
[gunicorn](https://gunicorn.org/), as in:

```sh
gunicorn server:app
```

which will listen locally, or use `-b 0.0.0.0:5000` to listen to exterior
connections too.


## Tests

You can run the set of tests in the `tests` directory with:

```sh
pytest-3
```

which will run all the functions that start with `test_` in the
`test_*.py` files. You can also use the contents of those files to
see examples of how to use ete.


## Api

The REST api has (at least) the following endpoints:

```text
/users
/users/<id>
/trees
/trees/<id>
/trees/<id>/newick
/trees/<id>/size
/trees/<id>/draw
/info
/id/users/<username>
/id/trees/<name>
/login
```

They all support the GET method to request information. To **create** *users*
or *trees* use the POST method on the `/users` and `/trees`
endpoints. To **modify** their values use the PUT method. To **delete** them
use the DELETE method.

The `/info` endpoint returns information about the currently logged user. The
`/id` endpoint is useful to retrieve user and tree ids from usernames and
tree names.

Some of the endpoints and methods will require to be authenticated to use them.
You can use a registered user and password with Basic Authentication or Token
Authentication to access (you must use the `/login` endpoint first for that).

All the requests must send the information as json (with the
`Content-Type: application/json` header). The responses are also json-encoded.

Most calls contain the *key* (property name) `message` in the response. If
the request was successful, its value will be `ok`. If not, it will include
the text `Error:` with a description of the kind of error.

When creating a user or a profile an additional property `id` is returned,
with the id of the created object.

Finally, when using token authentication, the returned object contains the
properties `id`, `username`, `name`, and (most importantly) `token`
with the values referring to the successfully logged user. The value of
`token` must be used in subsequent calls, with the header
`Authorization: Bearer <token>`, to stay logged as the same user.


### Example calls

You can use [http](https://httpie.io/) (which is like `curl` if you prefer,
with a modern syntax) to test the backend with commands like:

```sh
http localhost:5000/trees/1

http -a guest:123 POST localhost:5000/trees name=test newick='(a:1,b:2)c;'

http -a guest:123 DELETE localhost:5000/users/2

http POST localhost:5000/login username=guest password=123
```

To keep on going with bearer authentication, take the returned token and use
it in the next calls like:

```sh
http localhost:5000/info Authorization:"Bearer $token"
```


# License

This program is licensed under the GPL v3. See the [project
license](docs/license.md) for further details.
