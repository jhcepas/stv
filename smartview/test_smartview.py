#!/usr/bin/env python3

"""
Test the functionality of smartview.

The backend server must be running for the tests to run properly.

To run with pytest, but you can run interactively too if you want.
"""

from contextlib import contextmanager
import urllib.request as req
import urllib.error
import json

urlbase = 'http://localhost:8090/'



# Helper functions.

def request(*args, **kwargs):
    "Return the json response from a url"
    headers = {'Content-Type': 'application/json'}
    r = req.Request(urlbase + args[0], *args[1:], **kwargs, headers=headers)
    return json.loads(urllib.request.urlopen(r).read().decode('utf8'))


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


# The tests.

def test_root():
    html = urllib.request.urlopen(urlbase).read().decode('utf8')
    assert html.startswith('<!DOCTYPE html>')
    print(html)


def test_get_scene_region():
    response = get('get_scene_region/1,0,0,10,10/')
    assert type(response) == dict and 'items' in response
    for item in response['items']:
        assert item[0] in 'rlt'
    print(response)


def test_get_size():
    response = get('size/')
    assert type(response) == dict
    assert 'width' in response and 'height' in response
    print(response)


def test_get_layouts():
    response = get('layouts/')
    assert type(response) == list
    assert response == [
        'real', 'align', 'test', 'crouded', 'basic', 'stacked', 'tol',
        'rect', 'clean']
    print(response)



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
