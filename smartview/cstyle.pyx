from checkers import *

cdef class cNodeStyle(object):
    cdef public int hz_line_type
    cdef public int vt_line_type
    cdef public int hz_line_width
    cdef public int vt_line_width
    cdef public int size
    cdef public int collapse


    def __cinit__(self):
        self.hz_line_type = 0
        self.vt_line_type = 0
        self.hz_line_width = 0
        self.vt_line_width = 0
        self.size = 0
        self.collapse = 0

        def __repr__(self):
            return "NodeStyle (%s)" %(hex(self.__hash__()))

    # #attrs = dict([[e[0], e[1]] for e in NODE_STYLE_DEFAULT])
    # def __getattr__(self, attr_name):
    #     try:
    #         return NODE_STYLE_DEFAULT[attr_name]
    #     except KeyError:
    #         raise ValueError("'%s' attribute is not supported" % attr_name)

    # def __getitem__(self, name):
    #     return getattr(self, name)

    # def __setitem__(self, name, value):
    #     return setattr(self, name, value)


class NodeStyle(cNodeStyle):
    __slots__ = ["fgcolor", "bgcolor", "vt_line_color", "hz_line_color", "shape"]

    def __init__(self):

        self.fgcolor = None
        self.bgcolor = None
        self.vt_line_color = "black"
        self.hz_line_color = "black"
        self.shape = "squared"
