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
    def __init__(self, painter=None, surface=None):
        if not painter:
            self.pp = QPainter(surface)
        else:
            self.pp = painter

    def save(self):
        self.pp.save()

    def restore(self):
        self.pp.restore()

    def set_pen(self, color, stroke, cap):
        self.pp.setPen(QColor(color))

    def set_brush(self, color, gradient=None):
        self.pp.setBrush(QColor(color))

    def draw_line(self, x1, y1, x2, y2):
        self.pp.drawLine(x1, y1, x2, y2)

    def draw_rect(self, x1, y1, x2, y2):
        self.pp.drawRect(x1, y1, w, h)

    def draw_arc(self):
        pass

    def draw_ellipse(self, cx, cy, r1, r2):
        self.pp.drawEllipse(cx, cy, r1, r2)

    def draw_text(self, x, y, text, fsize=8, fcolor='black', ftype=None, fstyle=None):
        # set font, etc..
        self.pp.drawText(x, y, text)

    def draw_path(self):
        pass

    def draw_curve(self):
        pass
