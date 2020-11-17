#!/usr/bin/env python3

"""
Keep the data of users and trees, and present a REST api to talk
to the world.

REST call examples:
  GET    /users       Get all users
  GET    /users/{id}  Get the user information identified by "id"
  POST   /users       Create a new user
  PUT    /users/{id}  Update the user information identified by "id"
  DELETE /users/{id}  Delete user by "id"
"""

# The structure that we want to follow is:
#
# user
#   id: int
#   username: str
#   name: str
#   password: str
#   trees_owner: list of ints (tree ids)
#   trees_reader: list of ints (tree ids)
#
# tree
#   id: int
#   owner: int (user id)
#   name: str
#   description: str
#   newick: str
#   readers: list of ints (user ids)


import os
from functools import partial
from contextlib import contextmanager
from flask import Flask, request, jsonify, g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from flask_restful import Resource, Api
from flask_cors import CORS
import sqlalchemy
from itsdangerous import TimedJSONWebSignatureSerializer as JSONSigSerializer
from werkzeug.security import generate_password_hash, check_password_hash

import tree
import draw


db = None  # call initialize() to fill these up
serializer = None  # this one is used for the token auth


# Set up the authentication (see https://flask-httpauth.readthedocs.io/).

auth_basic = HTTPBasicAuth()
auth_token = HTTPTokenAuth('Bearer')
auth = MultiAuth(auth_basic, auth_token)

@auth_basic.verify_password
def verify_password(username, password):
    res = dbget('id,password', 'users where username=?', username)
    if len(res) == 1:
        g.user_id = res[0]['id']
        return check_password_hash(res[0]['password'], password)
    else:
        return False

@auth_token.verify_token
def verify_token(token):
    try:
        g.user_id = serializer.loads(token)
        return True
    except:
        return False


# Customized exception.

class InvalidUsage(Exception):
    def __init__(self, message, status_code=400):
        super().__init__()
        self.message = 'Error: ' + message
        self.status_code = status_code


# REST api.

class Login(Resource):
    def post(self):
        "Return info about the user if successfully logged"
        data = get_fields(required=['username', 'password'])
        username = data['username']
        fields = 'id,name,password'

        res = dbget(fields, 'users where username=?', username)
        if len(res) == 0:
            raise InvalidUsage('bad user/password', 401)
        r0 = res[0]

        if not check_password_hash(r0['password'], data['password']):
            raise InvalidUsage('bad user/password', 401)

        token = serializer.dumps(r0['id']).decode('utf8')
        return {'id': r0['id'],
                'username': username,
                'name': r0['name'],
                'token': token}


class Users(Resource):
    def get(self, user_id=None):
        "Return info about the user (or all users if no id given)"
        if user_id is None:
            return [get_user(uid) for uid in sorted(dbget0('id', 'users'))]
        else:
            return get_user(user_id)

    @auth.login_required
    def post(self):
        "Add user"
        admin_id = 1
        if g.user_id != admin_id:
            raise InvalidUsage('no permission to add', 403)

        data = get_fields(required=['username', 'password'],
            valid_extra=['name'])

        data['password'] = generate_password_hash(data['password'])
        data.setdefault('name', 'Random User')

        cols, vals = zip(*data.items())
        try:
            qs = '(%s)' % ','.join('?' * len(vals))
            dbexe('insert into users %r values %s' % (tuple(cols), qs), vals)
        except sqlalchemy.exc.IntegrityError as e:
            raise InvalidUsage('database exception adding user: %s' % e)

        uid = dbget0('id', 'users where username=?', data['username'])
        return {'message': 'ok', 'id': uid}, 201

    @auth.login_required
    def put(self, user_id):
        "Modify user"
        admin_id = 1
        if g.user_id not in [user_id, admin_id]:
            raise InvalidUsage('no permission to modify', 403)

        data = get_fields(
            valid_extra=['username', 'name', 'password'])

        if 'password' in data:
            data['password'] = generate_password_hash(data['password'])

        cols, vals = zip(*data.items())
        qs = ','.join('%s=?' % x for x in cols)
        res = dbexe('update users set %s where id=%d' % (qs, user_id), vals)

        if res.rowcount != 1:
            raise InvalidUsage('unknown user id %d' % user_id, 409)

        return {'message': 'ok'}

    @auth.login_required
    def delete(self, user_id):
        "Delete user and all references to her"
        admin_id = 1
        if g.user_id not in [user_id, admin_id]:
            raise InvalidUsage('no permission to delete', 403)

        with shared_connection([dbget0, dbexe]) as [get0, exe]:
            res = exe('delete from users where id=?', user_id)
            if res.rowcount != 1:
                raise InvalidUsage('unknown user id %d' % user_id, 409)

            exe('delete from user_owned_trees where id_user=?', user_id)
            exe('delete from user_reader_trees where id_user=?', user_id)

            for tid in get0('id', 'trees where owner=?', user_id):
                del_tree(tid)
            # NOTE: we could instead move them to a list of orphaned trees.

        return {'message': 'ok'}


class Trees(Resource):
    # TODO: Decide if we are going to use the 'readers' associated to each tree
    # to limit the access to them. In that case, we would need to add
    #   @auth.login_required
    # here, and also check that g.user_id is a reader (or the owner, or admin).
    def get(self, tree_id=None):
        "Return info about the tree (or all trees if no id given)"
        if tree_id is None:
            return [get_tree(pid) for pid in dbget0('id', 'trees')]
        elif request.url_rule.rule == '/trees/<int:tree_id>':
            return get_tree(tree_id)
        elif request.url_rule.rule == '/trees/<int:tree_id>/draw':
            viewport = get_viewport(request.args)
            t = add_tree(tree_id)
            z = float(request.args.get('z', 1))
            return list(draw.draw(t, viewport=viewport, zoom=z))
        elif request.url_rule.rule == '/trees/<int:tree_id>/size':
            t = add_tree(tree_id)
            width, height = draw.node_size(t)
            return {'width': width, 'height': height}
        else:
            raise InvalidUsage('unknown tree GET request')

    @auth.login_required
    def post(self):
        "Add tree"
        data = get_fields(
            required=['name', 'description', 'newick'],
            valid_extra=['owner'])

        if 'owner' not in data:
            data['owner'] = g.user_id

        admin_id = 1
        if g.user_id not in [data['owner'], admin_id]:
            raise InvalidUsage('owner set different from current user')

        tree_id = None  # will be filled later if it all works
        with shared_connection([dbget0, dbexe]) as [get0, exe]:
            cols, vals = zip(*data.items())
            try:
                qs = '(%s)' % ','.join('?' * len(vals))
                exe('insert into trees %r values %s' % (tuple(cols), qs),
                    vals)
            except sqlalchemy.exc.IntegrityError as e:
                raise InvalidUsage('database exception adding tree: %s' % e)

            tree_id = get0('id', 'trees where name=?', data['name'])[0]

            exe('insert into user_owned_trees values (%d, %d)' %
                (data['owner'], tree_id))

        return {'message': 'ok', 'id': tree_id}, 201

    @auth.login_required
    def put(self, tree_id):
        "Modify tree"
        if dbcount('trees where id=?', tree_id) != 1:
            raise InvalidUsage('unknown tree id %d' % tree_id)

        admin_id = 1
        if g.user_id not in [get_owner(tree_id), admin_id]:
            raise InvalidUsage('no permission to modify tree')

        data = get_fields(valid_extra=[
            'addReaders','delReaders',
            'id', 'name', 'description', 'newick'])

        add_readers(tree_id, data.pop('addReaders', None))
        del_readers(tree_id, data.pop('delReaders', None))
        if not data:
            return {'message': 'ok'}

        cols, vals = zip(*data.items())
        qs = ','.join('%s=?' % x for x in cols)
        res = dbexe('update trees set %s where id=%d' % (qs, tree_id), vals)

        if res.rowcount != 1:
            raise InvalidUsage('unknown tree id %d' % tree_id, 409)

        return {'message': 'ok'}

    @auth.login_required
    def delete(self, tree_id):
        "Delete tree and all references to it"
        if dbcount('trees where id=?', tree_id) != 1:
            raise InvalidUsage('unknown tree id %d' % tree_id, 409)

        admin_id = 1
        if g.user_id not in [get_owner(tree_id), admin_id]:
            raise InvalidUsage('no permission to delete tree', 403)

        del_tree(tree_id)
        return {'message': 'ok'}


class Info(Resource):
    @auth.login_required
    def get(self):
        "Return info about the currently logged user"
        return get_user(g.user_id)


class Id(Resource):
    def get(self, path):
        if not any(path.startswith(x) for x in ['users/', 'trees/']):
            raise InvalidUsage('invalid path %r' % path, 404)

        name = path.split('/', 1)[-1]
        if path.startswith('users/'):
            uids = dbget0('id', 'users where username=?', name)
            if len(uids) != 1:
                raise InvalidUsage('unknown username %r' % name)
            return {'id': uids[0]}
        elif path.startswith('trees/'):
            pids = dbget0('id', 'trees where name=?', name)
            if len(pids) != 1:
                raise InvalidUsage('unknown tree name %r' % name)
            return {'id': pids[0]}



# Auxiliary functions.

def add_tree(tree_id):
    "Add tree to app.trees and initialize it if not there, and return it"
    if tree_id in app.trees:
        return app.trees[tree_id]

    # TODO: Remove these examples and have a more graceful interface for them :)
    if tree_id == 4:  ###
        tree_text = open('../tests/example_tree_data/HmuY.aln2.tree').read().strip()
    elif tree_id == 5: ###
        tree_text = open('../tests/example_tree_data/aves.tree').read().strip()
    else:
        tree_text = dbget0('newick', 'trees where id=?', tree_id)[0]

    t = tree.read(tree_text)
    draw.store_sizes(t)
    app.trees[tree_id] = t
    return t


def get_viewport(args):
    try:
        x, y, w, h = [float(args[v]) for v in ['x', 'y', 'w', 'h']]
        assert w > 0 and h > 0, 'width and height should be > 0'
        return (x, y, w, h)
    except KeyError as e:
        return None
    except (ValueError, AssertionError) as e:
        raise InvalidUsage(f'not a valid viewport: {e}')


def dbexe(command, *args, conn=None):
    "Execute a sql command (using a given connection if given)"
    conn = conn or db.connect()
    return conn.execute(command, *args)


def dbcount(where, *args, conn=None):
    "Return the number of rows from the given table (and given conditions)"
    res = dbexe('select count(*) from %s' % where, *args, conn=conn)
    return res.fetchone()[0]


def dbget(what, where, *args, conn=None):
    "Return result of the query 'select what from where' as a list of dicts"
    res = dbexe('select %s from %s' % (what, where), *args, conn=conn)
    return [dict(zip(what.split(','), x)) for x in res.fetchall()]


def dbget0(what, where, *args, conn=None):
    "Return a list of the single column of values from get()"
    assert ',' not in what, 'Use this function to select a single column only'
    return [x[what] for x in dbget(what, where, *args, conn=conn)]


@contextmanager
def shared_connection(functions):
    "Create a connection and yield the given functions but working with it"
    with db.connect() as conn:
        yield [partial(f, conn=conn) for f in functions]


def get_user(uid):
    "Return all the fields of a given user as a dict"
    with shared_connection([dbget, dbget0]) as [get, get0]:
        users = get('id,username,name', 'users where id=?', uid)
        if len(users) == 0:
            raise InvalidUsage('unknown user id %d' % uid, 409)

        user = users[0]

        user['trees_owner'] = get0('id_tree',
            'user_owned_trees where id_user=?', uid)

        user['trees_reader'] = get0('id_tree',
            'user_reader_trees where id_user=?', uid)

    return strip(user)


def get_tree(tid):
    "Return all the fields of a given tree"
    with shared_connection([dbget, dbget0]) as [get, get0]:
        trees = get('id,owner,name,description', 'trees where id=?', tid)
        if len(trees) == 0:
            raise InvalidUsage('unknown tree id %d' % tid, 409)

        tree = trees[0]

        tree['readers'] = get0('id_user',
            'user_reader_trees where id_tree=?', tid)

    return strip(tree)


def get_owner(tree_id):
    "Return owner id of the given tree"
    return dbget0('id_user', 'user_owned_trees where id_tree=?', tree_id)


def del_tree(tid):
    "Delete a tree and everywhere where it appears referenced"
    exe = db.connect().execute
    exe('delete from trees where id=?', tid)
    exe('delete from user_owned_trees where id_tree=?', tid)
    exe('delete from user_reader_trees where id_tree=?', tid)


def strip(d):
    "Return dictionary without the keys that have empty values"
    d_stripped = {}
    for k, v in d.items():
        if v:
            d_stripped[k] = d[k]
    return d_stripped


def add_readers(tid, uids):
    "Add readers (with user id in uids) to a tree (tid)"
    if not uids:
        return
    uids_str = '(%s)' % ','.join('%d' % x for x in uids)  # -> '(u1, u2, ...)'

    if dbcount('users where id in %s' % uids_str) != len(uids):
        raise InvalidUsage('nonexisting user in %s' % uids_str)
    if dbcount('user_reader_trees '
        'where id_tree=%d and id_user in %s' % (tid, uids_str)) != 0:
        raise InvalidUsage('tried to add an existing reader')

    values = ','.join('(%d, %d)' % (uid, tid) for uid in uids)
    dbexe('insert into user_reader_trees (id_user, id_tree) values %s' % values)


def del_readers(tid, uids):
    "Remove readers (with user id in uids) from a tree (tid)"
    if not uids:
        return
    uids_str = '(%s)' % ','.join('%d' % x for x in uids)  # -> '(u1, u2, ...)'

    if dbcount('user_reader_trees '
        'where id_tree=%d and id_user in %s' % (tid, uids_str)) != len(uids):
        raise InvalidUsage('nonexisting user in %s' % uids_str)

    dbexe('delete from user_reader_trees where '
        'id_user in %s and id_tree=?' % uids_str, tid)


def get_fields(required=None, valid_extra=None):
    "Return fields and raise exception if missing required or invalid present"
    if not request.json:
        raise InvalidUsage('missing json content')

    data = request.json.copy()

    if required and any(x not in data for x in required):
        raise InvalidUsage('must have the fields %s' % required)

    valid = (required or []) + (valid_extra or [])
    if not all(x in valid for x in data):
        raise InvalidUsage('can only have the fields %s' % valid)

    return data


# App initialization.

def initialize(db_name='trees.db'):
    "Initialize the database and the flask app"
    global db, serializer
    db = sqlalchemy.create_engine('sqlite:///%s' % db_name)
    app = Flask(__name__)
    CORS(app)

    app.config['SECRET_KEY'] = os.urandom(256)
    serializer = JSONSigSerializer(app.config['SECRET_KEY'], expires_in=3600)

    api = Api(app)
    add_resources(api)

    app.trees = {}  # to keep in memory loaded trees

    @app.route('/')
    def description():
        return ('<html>\n<head>\n<title>Description</title>\n</head>\n<body>\n'
            '<pre>' + __doc__ + '</pre>\n'
            '<p>For analysis, <a href="/static/gui.html">use our gui</a>!</p>\n'
            '</body>\n</html>')

    @app.errorhandler(InvalidUsage)
    def handle_invalid_usage(error):
        response = jsonify({'message': error.message})
        response.status_code = error.status_code
        return response

    return app


def add_resources(api):
    "Add all the REST endpoints"
    add = api.add_resource  # shortcut
    add(Login, '/login')
    add(Users, '/users', '/users/<int:user_id>')
    add(Trees, '/trees',
        '/trees/<int:tree_id>',
        '/trees/<int:tree_id>/draw',
        '/trees/<int:tree_id>/size')
    add(Info, '/info')
    add(Id, '/id/<path:path>')



app = initialize()

if __name__ == '__main__':
    app.run(debug=True)

# But for production it's better if we serve it with something like:
#   gunicorn server:app