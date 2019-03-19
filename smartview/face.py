from PyQt5.QtGui import QColor, QPen, QBrush, QFont
from PyQt5.QtCore import QRectF

from colors import random_color

class Face(object):
    __slots__ = ["node",
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

    def _draw(self, painter, x, y, zoom_factor):
        painter.setPen(QColor(self.fgcolor))
        if self.bgcolor:
            painter.fillRect(QRectF(x, y, self.rect_width, self.rect_height), QColor(self.bgcolor))
        else:
            painter.drawRect(QRectF(x, y, self.rect_width, self.rect_height))

class TextFace(Face):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor', 'fstyle', 'tight_text', "_text_size", "min_fsize"]

    # def __repr__(self):
    #     return "Text Face [%s] (%s)" %(self.text, hex(self.__hash__()))

    courier = 72./96.
    
    @property
    def text(self):
        return self._text
    
    def __init__(self, text, ftype="Courier", fsize=10, fgcolor="black",
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
        if self._text_size is None:
            self._update_text_size()
        return self._text_size[0]
        
    def _height(self):
        if self._text_size is None:
            self._update_text_size()
        return self._text_size[1]
           
    def _draw(self, painter, x, y, zoom_factor):
        if zoom_factor * self._height() < self.min_fsize * self.courier:
            r = QRectF(x, y, self._width(), self._height())
            painter.setPen(QPen(QColor(self.fgcolor)))
            painter.setOpacity(0.25)
            painter.drawRect(r)
        else:
            painter.setFont(self._get_font())
            r = QRectF(x, y, self._width(), self._height())
            painter.drawText(r, self.text)

    def _get_font(self):
        italic = self.fstyle == "italic"
        return QFont(self.ftype, pointSize=self.fsize, italic=italic)
                
    def _update_text_size(self):
        # fm = QFontMetrics(self._get_font())
        # tx_w = fm.width(self.text)
        # textr = fm.boundingRect(self.text)
        # self._text_size = (tx_w, textr.height())

        self._text_size = (self.fsize*len(self.text)*self.courier, self.fsize*self.courier)

class AttrFace(TextFace):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor', 'fstyle', 'tight_text', "_text_size", "min_fsize"]

    @property
    def text(self):
        return str(getattr(self.node, self._text))
    
    def __init__(self, attribute, ftype="Courier", fsize=10, fgcolor="black", fstyle='normal', tight_text=False, min_fsize=4):
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
        return self._width()
    
    def _draw(self, painter, x, y, zoom_factor):

        if self.solid:
            painter.setBrush(QColor(self.color))
            painter.drawEllipse(x, y, self._width(), self._height())
        else:
            painter.setPen(QPen(QColor(self.color)))
            painter.drawEllipse(x, y, self._width(), self._height())



    
    
    
