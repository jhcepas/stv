from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QFontMetrics, QPainterPath
from PyQt5.QtCore import QRectF
import numpy as np
from colors import random_color
import colorsys



# Pick two colors. Values from 0 to 1. See "hue" at
# http://en.wikipedia.org/wiki/HSL_and_HSV
def get_color_gradient():

    COLOR1= 0.4
    COLOR2= 0.97
    COLOR_INTENSITY = 0.6

    def gradient(hue):
        min_lightness = 0.35 
        max_lightness = 0.85
        base_value = COLOR_INTENSITY

        # each gradient must contain 100 lightly descendant colors
        colors = []   
        rgb2hex = lambda rgb: '#%02x%02x%02x' % rgb
        l_factor = (max_lightness-min_lightness) / 100.
        l = min_lightness
        while l<=max_lightness:
            l += l_factor
            rgb =  rgb2hex(tuple(map(lambda x: int(x*255), 
                                     colorsys.hls_to_rgb(hue, l, base_value))))
            colors.append(rgb)
        return colors

    def color_scale():
        colors = []
        for c in  gradient(COLOR1):
            color=QColor(c)
            colors.append(color)
        colors.append(QColor("white"))
        for c in  reversed(gradient(COLOR2)):
            color=QColor(c)
            colors.append(color)
        return colors 

    return color_scale()

GRADIENT = get_color_gradient()

def get_arc_path(rect1, rect2, rad_angles):
    angles = map(np.degrees, rad_angles)
    path = QPainterPath()
    span = angles[-1] - angles[0]
    if 0 and span < 0.01: # solves precision problems drawing small arcs
        path.arcMoveTo(rect1, -angles[0])
        i1 = path.currentPosition()
        path.arcMoveTo(rect1, -angles[-1])
        i2 = path.currentPosition()
        path.arcMoveTo(rect2, -angles[0])
        o1 = path.currentPosition()
        path.arcMoveTo(rect2, -angles[-1])
        o2 = path.currentPosition()

        path.moveTo(i1)
        path.lineTo(i2)
        path.lineTo(o2)
        path.lineTo(o1)
        path.closeSubpath()
    else:
        path.arcMoveTo(rect1, -angles[0])
        i1 = path.currentPosition()

        path.arcMoveTo(rect2, -angles[-1])
        o2 = path.currentPosition()

        path.moveTo(i1)

        path.arcTo(rect1, -angles[0], -span)
        path.lineTo(o2)
        path.arcTo(rect2, -angles[-1], span)
        path.closeSubpath()
    return path



class Face(object):
    __slots__ = ["node",
                 "arc_start",
                 "arc_end",
                 "arc_center",
                 "img_rad",
                 "type",
                 "margin_left", "margin_right", "margin_top", "margin_bottom",
                 "opacity",
                 "rotation", "rotable",
                 "hz_align", "vt_align",
                 "bgcolor", "outter_bgcolor",
                 "border_top", "border_bottom", "border_left", "border_right",
                 "fill_color",
                 "outter_border_top", "outter_border_bottom", "outter_border_left", "outter_border_right",
                 "max_height","max_width",
                 "only_if_leaf",
    ]
    def __repr__(self):
        print type(self.__hash__())
        return "'%s' (%s)" %(self.__class__, hex(int(self.__hash__())))

    def __init__(self):
        self.only_if_leaf = None
        self.node = None
        self.type = None
        self.arc_start = None
        self.arc_end = None
        self.arc_center = None
        self.img_rad = None
        self.margin_top = 0
        self.margin_bottom = 0
        self.margin_left = 0
        self.margin_right = 0
        self.opacity = 1.0
        self.rotation = 0
        self.rotable = False
        self.hz_align = 0
        self.vt_align = 0
        self.bgcolor = None
        self.outter_bgcolor = None
        self.border_top = (None, None, None)
        self.border_bottom = (None, None, None)
        self.border_left = (None, None, None)
        self.border_right = (None, None, None)
        self.outter_border_top = (None, None, None)
        self.outter_border_bottom = (None, None, None)
        self.outter_border_left = (None, None, None)
        self.outter_border_right = (None, None, None)
        self.fill_color = None
        self.max_height = None
        self.max_width = None

    def _width(self):
        pass

    def _height(self):
        pass

    def _draw(self, painter, x, y, zoom_factor):
        pass

    def _pre_draw(self):
        pass

    def _size(self):
        pass




class HeatmapArcFace(Face):
    __slots__ = ['width', 'values', 'h']

    def __init__(self, values, width, h):
        Face.__init__(self)

        self.width = width
        self.values = values
        self.h = h

    def _height(self):
        return 1

    def _width(self):
        return self.width

    def _size(self):
        return self.width, 1

    def _draw(self, painter, x, y, zoom_factor):
        painter.save()
        painter.scale(zoom_factor, zoom_factor)
        painter.translate(-self.img_rad*2, -self.img_rad)

        # r1 = QRectF(0, 0, (self.img_rad)*2, (self.img_rad)*2)
        # painter.setPen(QColor("blue"))
        # painter.drawRect(r1)
        step = (self.width) / float(len(self.values))
        offset = 0
        for v in self.values:
            #color = random_color(l=self.h, s=0.7, h=v)

            color = GRADIENT[int(v*200)]

            r1 = QRectF(-offset, -offset,
                        (self.img_rad+offset)*2, (self.img_rad+offset)*2)
            offset += step

            r2 = QRectF(-offset, -offset,
                        (self.img_rad+offset)*2, (self.img_rad+offset)*2)

            #if self.node.name == 'aaaaaaaaac':
                 # painter.setPen(QColor("green"))
                 # painter.drawRect(r2)
                 # painter.setPen(QColor("yellow"))
                 # painter.drawRect(r1)

            if self.node.children:
                painter.setOpacity(0.5)

            painter.setPen(QColor("#777777"))
            painter.setBrush(QColor(color))


            # if 'aaaaaaaaac' in self.node.get_leaf_names():
            #     painter.setBrush(QColor(random_color(h=0.9)))
            #     painter.setPen(QColor("#777777"))

            span = self.arc_end - self.arc_start
            #path = get_arc_path(r1, r2, [span/2, -span/2])
            path = get_arc_path(r1, r2, [self.arc_start-self.arc_center, self.arc_end-self.arc_center])
            painter.drawPath(path)

        painter.restore()



class HeatmapFace(Face):
    __slots__ = ['rect_width', 'rect_height', 'rect_label', "fgcolor", 'bgcolor', 'values']

    def __init__(self, values, width, height, label=None, fgcolor="steelblue",
                 bgcolor="steelblue"):
        Face.__init__(self)

        self.rect_width = width
        self.rect_height = height
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.rect_label = label
        self.values = values

    def _height(self):
        return self.rect_height

    def _width(self):
        return self.rect_width * len(self.values)

    def _size(self):
        return self.rect_width * len(self.values), self.rect_height

    def _draw(self, painter, x, y, zoom_factor):
        painter.save()
        painter.scale(zoom_factor, zoom_factor)
        x = 0
        for v in self.values:
            color = random_color(l=0.5, s=0.5)
            painter.fillRect(QRectF(x, y, self.rect_width, self.rect_height), QColor(color))
            painter.setPen(QColor("black"))
            painter.drawRect(QRectF(x, y, self.rect_width, self.rect_height))
            x += self.rect_width
        painter.restore()


class RectFace(Face):
    __slots__ = ['rect_width', 'rect_height', 'rect_label', 'rect_fgcolor', 'rect_bgcolor', "fgcolor", 'bgcolor']

    def __init__(self, width, height, label=None, fgcolor="steelblue",
                 bgcolor="steelblue"):
        Face.__init__(self)

        self.rect_width = width
        self.rect_height = height
        self.rect_fgcolor = fgcolor
        self.rect_bgcolor = bgcolor
        self.rect_label = label
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor

    def _height(self):
        return self.rect_height

    def _width(self):
        return self.rect_width

    def _size(self):
        return self.rect_width, self.rect_height

    def _draw(self, painter, x, y, zoom_factor):
        painter.save()
        painter.scale(zoom_factor, zoom_factor)
        painter.setPen(QColor(self.fgcolor))
        if self.bgcolor:
            painter.fillRect(QRectF(x, y, self.rect_width, self.rect_height), QColor(self.bgcolor))
            painter.setPen(QColor("black"))
            painter.drawRect(QRectF(x, y, self.rect_width, self.rect_height))
        else:
            painter.drawRect(QRectF(x, y, self.rect_width, self.rect_height))
        painter.restore()

class TextFace(Face):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor', 'fstyle', 'tight_text', "_text_size", "min_fsize"]

    # def __repr__(self):
    #     return "Text Face [%s] (%s)" %(self.text, hex(self.__hash__()))

    @property
    def text(self):
        return self._text

    def __init__(self, text, ftype="Arial", fsize=10, fgcolor="black",
                 fstyle='normal', tight_text=False, min_fsize=4):
        """Static text Face object

        .. currentmodule:: ete3

        :param text:     Text to be drawn
        :param ftype:    Font type, e.g. Arial, Verdana, Courier
        :param fsize:    Font size, e.g. 10,12,6, (default=10)
        :param fgcolor:  Foreground font color. RGB code or color name in :data:`SVG_COLORS`
        :param penwidth: Penwdith used to draw the text.
        :param fstyle: "normal" or "italic"

        :param False tight_text: When False, boundaries of the text are
        approximated according to general font metrics, producing slightly
        worse aligned text faces but improving the performance of tree
        visualization in scenes with a lot of text faces.
        """
        Face.__init__(self)
        self._text = text
        self.ftype = ftype
        self.fsize = fsize
        self.fgcolor = fgcolor
        self.fstyle = fstyle
        self.tight_text = tight_text
        self._text_size = None
        self.rotable = True
        self.min_fsize = min_fsize

    def _width(self):
        fm = QFontMetrics(self._get_font())
        text_rect = fm.boundingRect(self.text)
        return text_rect.width()

    def _height(self):
        fm = QFontMetrics(self._get_font())
        text_rect = fm.boundingRect(self.text)
        return text_rect.height()

    def _size(self):
        fm = QFontMetrics(self._get_font())
        text_rect = fm.boundingRect(self.text)
        return text_rect.width(), text_rect.height()

    def _draw(self, painter, x, y, zoom_factor):
        painter.save()
        painter.scale(zoom_factor, zoom_factor)
        painter.setPen(QPen(QColor(self.fgcolor)))
        r = QRectF(x, y, self._width(), self._height())
        if zoom_factor * self._height() < 4:
            painter.setOpacity(0.6)
            painter.drawRect(r)
        else:
            painter.setFont(self._get_font())
            painter.drawText(r, self.text)
            #painter.drawText(x, y+self._height(), self.text)
        painter.restore()

    def _get_font(self):
        italic = (self.fstyle == "italic")
        return QFont(self.ftype, pointSize=self.fsize, italic=italic)



class AttrFace(TextFace):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor', 'fstyle', 'tight_text', "_text_size", "min_fsize"]

    @property
    def text(self):
        return str(getattr(self.node, self._text))

    def __init__(self, attribute, ftype="Arial", fsize=10, fgcolor="black", fstyle='normal', tight_text=False, min_fsize=4):
        Face.__init__(self)
        self._text = attribute
        self.ftype = ftype
        self.fsize = fsize
        self.fgcolor = fgcolor
        self.fstyle = fstyle
        self.tight_text = tight_text
        self._text_size = None
        self.rotable = True
        self.min_fsize = fsize


class LabelFace(Face):
    __slots__ = ["width"]

    def __init__(self, width):
        Face.__init__(self)
        self.width = width

    def _width(self):
        return self.width

    def _height(self):
        return 0.0

    def _size(self):
        return self.width, 0.0

    def _draw(self, painter, x, y, zoom_factor):
        pass

class GradientFace(Face):
    __slots__ = ["width", "node_attr", "max_value", "min_value", "center_value"]

    def __init__(self, width, node_attr):
        Face.__init__(self)
        self.width = width
        self.node_attr = node_attr

    def _width(self):
        return self.width

    def _height(self):
        return 0.0

    def _size(self):
        return self.width, 0.0

    def _pre_draw(self):
        value = getattr(self.node, self.node_attr)
        self.fill_color = random_color(h=0.3, s=0.5, l=value)

    def _draw(self, painter, x, y, zoom_factor):
        pass

class CircleLabelFace(Face):
    __slots__ = ["size", "color", "solid", "value", "attr", "attr_transform"]

    def __init__(self, attr, color=None, solid=None, size=None, attr_transform=None):
        Face.__init__(self)
        self.size = size
        self.color = color
        self.attr = attr
        self.attr_transform = attr_transform
        self.solid = solid

    def _width(self):
        if self.size:
            return self.size
        else:
            v = getattr(self.node, self.attr)
            if self.attr_transform:
                return self.attr_transform(v)
            else:
                return v

    def _height(self):
        return 0.0

    def _draw(self, painter, x, y, zoom_factor):

        if self.solid:
            painter.setBrush(QColor(self.color))
            painter.drawEllipse(x, y, self._width(), self._height())
        else:
            painter.setPen(QPen(QColor(self.color)))
            painter.drawEllipse(x, y, self._width(), self._height())
