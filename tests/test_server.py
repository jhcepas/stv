#!/usr/bin/env python3

"""
Test the functionality of server.py.

The backend server must be running for the tests to run properly.

To run with pytest, but you can run interactively too if you want.
"""

import sys
from os.path import abspath, dirname
sys.path.insert(0, f'{abspath(dirname(__file__))}/..')

from contextlib import contextmanager
import urllib.request as req
import urllib.error
import json

urlbase = 'http://localhost:5000/'


# Helper functions.

def request(*args, **kwargs):
    "Return the json response from a url, accessed by basic authentication."
    mgr = req.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, urlbase, 'admin', 'abc')
    opener = req.build_opener(req.HTTPBasicAuthHandler(mgr))
    headers = {'Content-Type': 'application/json'}
    r = req.Request(urlbase + args[0], *args[1:], **kwargs, headers=headers)
    return json.loads(opener.open(r).read().decode('utf8'))


def get(*args, **kwargs):
    assert 'data' not in kwargs, 'Error: requests with data should be POST'
    return request(*args, **kwargs, method='GET')


def post(*args, **kwargs):
    assert 'data' in kwargs, 'Error: POST requests must have data'
    return request(*args, **kwargs, method='POST')


def put(*args, **kwargs):
    return request(*args, **kwargs, method='PUT')


def delete(*args, **kwargs):
    return request(*args, **kwargs, method='DELETE')


def jdumps(obj):
    return json.dumps(obj).encode('utf8')


def add_test_user(fields=None):
    try:
        get('id/users/test_user')
        raise Exception('test_user already exists.')
    except urllib.error.HTTPError as e:
        pass

    data = {
        'username': 'test_user',
        'name': 'Random User', 'password': 'booo'}
    if fields:
        data.update(fields)

    return post('users', data=jdumps(data))


def del_test_user():
    uid = get('id/users/test_user')['id']
    return delete('users/%s' % uid)


@contextmanager
def test_user(fields=None):
    add_test_user(fields)
    try:
        yield
    finally:
        del_test_user()


def add_test_tree(fields=None):
    try:
        get('id/trees/test_tree')
        raise Exception('tree "test_tree" already exists.')
    except urllib.error.HTTPError as e:
        pass

    data = {
        'name': 'test_tree',
        'description': 'This is an empty descritpion.',
        'newick': '(b)a;'}
    if fields:
        data.update(fields)

    return post('trees', data=jdumps(data))


def del_test_tree():
    pid =  get('id/trees/test_tree')['id']
    return delete('trees/%s' % pid)


@contextmanager
def test_tree(fields=None):
    add_test_tree(fields)
    try:
        yield
    finally:
        del_test_tree()


# The tests.

def test_not_found():
    try:
        url = urlbase + 'nonexistent'
        req.urlopen(url)
        raise Exception('We should not have found that url: %s' % url)
    except urllib.error.HTTPError as e:
        assert (e.getcode(), e.msg) == (404, 'NOT FOUND')


def test_unauthorized():
    try:
        url = urlbase + 'users/1'
        req.urlopen(req.Request(url, method='DELETE'))
        raise Exception('We should not have access to that url: %s' % url)
    except urllib.error.HTTPError as e:
        assert (e.getcode(), e.msg) == (401, 'UNAUTHORIZED')


def test_auth_basic():
    put('trees/1', data=jdumps({'name': 'Auth tested tree'}))
    # If we are not authenticated, that request will raise an error.


def test_auth_bearer():
    data = jdumps({'username': 'admin',
                    'password': 'abc'})
    res = post('login', data=data)
    auth_txt = 'Bearer ' + res['token']
    r = req.Request(urlbase + 'users', headers={'Authorization': auth_txt})
    req.urlopen(r)

    # If we are not authenticated, the request will raise an error.


def test_get_users():
    res = get('users')
    assert type(res) == list
    assert all(x in res[0] for x in 'id username name'.split())
    assert res[0]['id'] == 1
    assert res[0]['username'] == 'admin'


def test_get_trees():
    res = get('trees')
    assert type(res) == list
    keys = 'id name description owner readers'.split()
    assert all(x in res[0] for x in keys)
    assert res[0]['id'] == 1
    assert res[0]['owner'] == 1


def test_add_del_user():
    res = add_test_user()
    assert res['message'] == 'ok'

    res = del_test_user()
    assert res['message'] == 'ok'


def test_add_del_tree():
    res = add_test_tree()
    assert res['message'] == 'ok'

    res = del_test_tree()
    assert res['message'] == 'ok'


def test_change_user():
    with test_user():
        uid = get('id/users/test_user')['id']
        assert get('users/%s' % uid)['name'] == 'Random User'

        res = put('users/%s' % uid, data=jdumps({'name': 'Newman'}))
        assert res['message'] == 'ok'

        assert get('users/%s' % uid)['name'] == 'Newman'


def test_change_tree():
    with test_tree():
        tid = get('id/trees/test_tree')['id']
        assert get('trees/%s' % tid)['name'] == 'test_tree'

        res = put('trees/%s' % tid, data=jdumps({'description': 'changed'}))
        assert res['message'] == 'ok'

        assert get('trees/%s' % tid)['description'] == 'changed'


def test_add_del_readers():
    with test_user():
        uid = get('id/users/test_user')['id']
        with test_tree():
            tid = get('id/trees/test_tree')['id']
            res = put('trees/%s' % tid,
                data=jdumps({'addReaders': [uid]}))
            assert res['message'] == 'ok'

            assert uid in get('trees/%s' % tid)['readers']

            res = put('trees/%s' % tid,
                data=jdumps({'delReaders': [uid]}))
            assert res['message'] == 'ok'


def test_get_info():
    assert get('info') == get('users/1')


def test_existing_user():
    with test_user():
        try:
            data = jdumps({
                'username': 'test_user', 'name': 'Random User',
                'password': 'booo'})  # duplicated user
            post('users', data=data)
        except urllib.error.HTTPError as e:
            assert e.code == 400
            res = json.loads(e.file.read())
            assert res['message'].startswith('Error: database exception adding user')


def test_missing_username_in_new_user():
    try:
        data = jdumps({
            'name': 'Random User', 'password': 'booo'})  # missing: username
        post('users', data=data)
    except urllib.error.HTTPError as e:
        assert e.code == 400
        res = json.loads(e.file.read())
        assert res['message'].startswith('Error: must have the fields')


def test_adding_invalid_fields_in_new_user():
    try:
        data = jdumps({'username': 'test_user',
            'name': 'Random User', 'password': 'booo',
            'invalid': 'should not go'})  # invalid
        post('users', data=data)
    except urllib.error.HTTPError as e:
        assert e.code == 400
        res = json.loads(e.file.read())
        assert res['message'].startswith('Error: can only have the fields')


def test_change_password():
    with test_user():
        # Change password.
        uid = get('id/users/test_user')['id']
        password_new = 'new_shiny_password'
        data = jdumps({'password': password_new})
        put('users/%s' % uid, data=data)

        # Use new password to connect.
        mgr = req.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, urlbase, 'test_user', password_new)
        opener = req.build_opener(req.HTTPBasicAuthHandler(mgr))
        headers = {'Content-Type': 'application/json'}
        r = req.Request(urlbase + 'users/%s' % uid, headers=headers,
            method='PUT', data=jdumps({'name': 'Re-logged and changed name'}))
        res = json.loads(opener.open(r).read().decode('utf8'))
        assert res['message'] == 'ok'
        # If we are not authenticated, that request will raise an error.


def test_get_unknown_tree():
    nonexistent_tree_id = 22342342
    for endpoint in ['', '/newick', '/draw', '/size']:
        try:
            get(f'trees/{nonexistent_tree_id}{endpoint}')
        except urllib.error.HTTPError as e:
            assert e.code == 404
            res = json.loads(e.file.read())
            assert res['message'].startswith('Error: unknown tree id')


def test_get_known_tree():
    assert get('trees/1/newick').endswith(';')

    elements = get('trees/1/draw')
    assert all(x[0] in ['r', 'rn', 'ro', 'tl', 'tn', 'l', 'a'] for x in elements)

    assert set(get('trees/1/size').keys()) == {'width', 'height'}


def test_get_drawers():
    assert type(get('/trees/drawers')) == list



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
