from PyQt5 import QtCore
from PyQt5 import Qt
from PyQt5.QtGui import *
from PyQt5.QtCore import *

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
        if not painter and surface:
            self.pp = QPainter(surface)
        elif painter:
            self.pp = painter
        else:
            pass

    def save(self):
        self.pp.save()

    def restore(self):
        self.pp.restore()

    def set_pen(self, color, bgcolor, penwidth=0):
        self.set_brush(bgcolor)
        if not color:
            self.pp.setPen(Qt.NoPen)
        else:
            #QPen(const QBrush & brush, qreal width, Qt::PenStyle style = Qt::SolidLine, Qt::PenCapStyle cap = Qt::SquareCap, Qt::PenJoinStyle join = Qt::BevelJoin)
            pen = QPen(QColor(color))
            pen.setWidthF(penwidth)
            self.pp.setPen(pen)

    def set_brush(self, color):
        if not color:
            self.pp.setBrush(Qt.NoBrush)
        else:
            self.pp.setBrush(QColor(color))

    def set_font(self, fonttype, fontsize):
        font = QFont(fonttype, fontsize)
        self.pp.setFont(font)

    def draw_line(self, x1, y1, x2, y2, color="black", penwidth=0):
        self.set_pen(color, None, penwidth)
        z = self.zoom_factor
        self.pp.drawLine(x1*z, y1*z, x2*z, y2*z)
        #self.pp.drawLine(x1, y1, x2, y2)

    def draw_rect(self, x1, y1, w, h, color="black", bgcolor=None, penwidth=0):
        self.set_pen(color, bgcolor, penwidth)
        self.pp.drawRect(x1, y1, w, h)

    def draw_arc(self):
        pass

    def draw_ellipse(self, cx, cy, r1, r2):
        self.pp.drawEllipse(cx, cy, r1, r2)

    def draw_text(self, x, y, w, h, text, ftype, fsize):
        self.set_font(ftype, fsize)
        if w and h:
            r = QRectF(x, y, w, h)
            self.pp.drawText(r, text)
        else:
            self.pp.drawText(x, y, text)

    def draw_path(self):
        pass

    def draw_curve(self):
        pass

    def get_text_size(self, text, fonttype, fontsize):
        font = QFont(fonttype, fontsize)
        fm = QFontMetrics(font)
        #tx_w = fm.width(text)
        textr = fm.boundingRect(text)
        return (textr.width(), textr.height())
