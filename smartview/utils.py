import re
import time

import logging
logger = logging.getLogger("smartview")


def ansi(n):
    "Return function that escapes text with ANSI color n."
    return lambda txt: '\x1b[%dm%s\x1b[0m' % (n, txt)

black, red, green, yellow, blue, magenta, cyan, white = map(ansi, range(30, 38))


def timeit(f):
    def a_wrapper_accepting_arguments(*args, **kargs):
        t0 = time.time()
        ret = f(*args, **kargs)
        dt = time.time() - t0
        logger.debug("%s %s seconds" % (green(f.__name__), red("%0.6f" % dt)))
        return ret
    return a_wrapper_accepting_arguments
