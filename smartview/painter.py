from PyQt4 import QtCore
from PyQt4.QtGui import *
from PyQt4.QtCore import *

class SmartPainter(object):
    def __init__(self):
        self.line = []
        self.arcs = []
        self.text = []
        self.ellipse = []
        self.lines = []

    def set_pen(self):
        pass

    def set_brush(self):
        pass

    def draw_line(self, x1, y1, x2, y2, color='black', width=1, cap=None):
        #print [x1, y1, x2, y2, color, width, cap]
        self.lines.append([x1, y1, x2, y2, color, width, cap])

    def draw_rect(self):
        pass

    def draw_arc(self):
        pass

    def draw_ellipse(self):
        pass

    def draw_text(self):
        pass


class QETEPainter(object):
    def __init__(self, surface, painter=None):
        if not painter:
            self.p = QPainter(surface)

    def save(self):
        pass

    def restore(self):
        pass

    def set_pen(self, color, stroke, cap):
        pass

    def set_brush(self, color, gradient=None):
        pass

    def draw_line(self, x1, y1, x2, y2):
        self.p.drawLine(x1, y1, x2, y2)

    def draw_rect(self):
        pass

    def draw_arc(self):
        pass

    def draw_ellipse(self):
        pass

    def draw_text(self, text, fsize, fcolor='black', ftype=None, fstyle=None):
        pass

    def draw_path(self):
        pass

    def draw_curve(self):
        pass
