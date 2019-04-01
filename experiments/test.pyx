cdef class Tree(object):
    cdef public char* name 
    cdef public double dist
    cdef public double support
    cdef public object children
    cdef public object up
    def __cinit__(self):
        self.children = []

        
class Tree2(Tree):
    __slots__ = ["a", "b", "c", "d"]
    def __init__(self):
        self.a = 1
        self.b = 1
        self.c = 1
        self.d = 1
    
    def hello(self):
        print(1)

        
class Tree3(object):
    __slots__ = ["name", "dist", "support", "children", "up"]
    def __init__(self):
        self.name = None
        self.dist = 1.0
        self.support = 1.0
        self.children = []
        self.up = None

        
nodes = []

d =  {}
sample = {
        "name ":"N",
        "dist": 1.0,
        "up": None,
        "children ": None,
        "support" : 1.0,
        "_id ": 10,
        "_name ":"N",
        "_dist": 1.0,
        "_up": None,
         #"_children": [],
        "_support": 1.0,        
     }

import time

for x in xrange(1999999):
    t = Tree3()
    t.name = time.ctime()
    nodes.append(t)

    # for k in sample:
    #     d[(x, k)] = sample[k]
    #     d[(x, "_children")] = []
    
raw_input("exit")        
