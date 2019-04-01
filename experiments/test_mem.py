from guppy import hpy
import time
from array import array

class Test(object):
    __slots__ = ['a0','a1','a2','a3','a4','a5','a6','a7','a8', 'a9']            
    def __init__(self):
        self.a0 = 10.0
        self.a1 = 10.0
        self.a2 = 10.0
        self.a3 = 10.0
        self.a4 = 10.0
        self.a5 = 10.0
        self.a6 = 10.0
        self.a7 = 10.0
        self.a8 = 10.0
        self.a9 = 10.0
        
def access_all_obj(items):
    t1 = time.time()
    for j in items:
        a = j.a0
        a = j.a2
        a = j.a4
        a = j.a6
        a = j.a8
    print 'obj access', time.time()-t1

def access_all_obj_slow(items):
    t1 = time.time()
    for j in items:
        a = getattr(j, "a0")
        a = getattr(j, "a2")
        a = getattr(j, "a4")
        a = getattr(j, "a6")
        a = getattr(j, "a8")
    print 'obj access', time.time()-t1
    
def access_all_list(items, label = "list"):
    t1 = time.time()
    for j in items:
        a = j[0]
        a = j[2]
        a = j[4]
        a = j[6]
        a = j[8]
    print label, 'access item time:', time.time()-t1

h = hpy()
h.setref()
items_list = [[10.0] * 10 for i in xrange(2000000)]
items_tuple = [tuple([10.0] * 10) for i in xrange(2000000)]
items_array = [array('f', [10.0]*10) for i in xrange(2000000)]
items_obj = [Test() for i in xrange(2000000)]
print h.heap()
access_all_obj(items_obj)
access_all_list(items_list, "list")
access_all_list(items_tuple, "tuple")
access_all_list(items_array, "array")

