import time
from json import dumps
from random import randint
from bottle import Bottle, request, response, run
app = Bottle()


@app.error(405)
def method_not_allowed(res):
    if request.method == 'OPTIONS':
        new_res = bottle.HTTPResponse()
        new_res.set_header('Access-Control-Allow-Origin', '*')
        return new_res
    res.headers['Allow'] += ', OPTIONS'
    return request.app.default_error_handler(res)


@app.hook('after_request')
def enable_cors():
    """
    You need to add some headers to each request.
    Don't use the wildcard '*' for Access-Control-Allow-Origin in production.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
    print 'OK'


@app.get("/get_svg", method=['GET', 'OPTIONS'])
def get_svg():
    t1 = time.time()
    svg = []
    for i in range(5000):
        x, y, r = randint(0, 1000), randint(0, 1000), randint(2, 3)
        svg.append(
            '<circle cx="%s" cy="%s" r="%s" stroke="black" stroke-width="3" fill="red" />' % (x, y, r))
    data = {"svg": '\n'.join(svg)}
    response.content_type = 'application/json'
    print time.time() - t1
    return dumps(data)


@app.get("/random_scene/", method=['GET', 'OPTIONS'])
def get_svg():
    t1 = time.time()
    circles = []
    for i in range(5000):
        x, y, r = randint(0, 1000), randint(0, 1000), randint(2, 3)
        circles.append([x, y, r])
    data = {"circles": circles}
    response.content_type = 'application/json'
    print time.time() - t1
    return dumps(data)


run(app, host="localhost", port=8090, debug=True, reload=True)
