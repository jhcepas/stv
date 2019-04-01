from ete3.smartview.face import Face, AttrFace
import numpy

class A(object):
    __slots__ = ["btop", "bbot", "bright", "balg", "bfloat"]

import sys
a = A()

nnodes = 1000000
nfaces = 1

f= AttrFace("hello")
facesize = sys.getsizeof(f)
listsize = sys.getsizeof([])
entrysize = sys.getsizeof([Face(), 9, 9, 9, 9, 9])
print "list of lists", (((entrysize + facesize) * nfaces)+listsize)  * nnodes

containersize = sys.getsizeof(a)
face_pos = numpy.array([object(), 9, 9, 9, 9])
npentrysize = face_pos.nbytes

print "__slots__ + numpy ", (((npentrysize + facesize) * nfaces) + containersize) * nnodes

print "array only", (((npentrysize + facesize) * nfaces)) * nnodes


from guppy import hpy
h = hpy()
h.setref()
a = [ [A(),2,3,4,5,6],  [A(),2,3,4,5,6] , [A(),2,3,4,5,6],  [A(),2,3,4,5,6],  [A(),2,3,4,5,6]]
b = numpy.array(a, dtype="object")
print b.nbytes
h = h.heap()
print h 

