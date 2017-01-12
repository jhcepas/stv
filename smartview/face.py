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
                 "only_if_leaf", # unsure this is needed... Prevents rendering in collapsed nodes
                 "painter",
                 "min_size",
    ]
    def __repr__(self):
        print type(self.__hash__())
        return "'%s' (%s)" %(self.__class__, hex(int(self.__hash__())))

    def __init__(self):
        self.only_if_leaf = None
        self.node = None
        self.painter = None
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
        """ x,y: left corner. zoom_factor = scaling factor under used"""
        pass

    def _pre_draw(self):
        pass


class RectFace(Face):
    __slots__ = ['rect_width', 'rect_height', 'rect_label', 'rect_fgcolor', 'rect_bgcolor', "fgcolor", 'bgcolor']

    def __init__(self, width, height, fgcolor="steelblue",
                 bgcolor="steelblue"):
        Face.__init__(self)

        self.rect_width = width
        self.rect_height = height
        self.rect_fgcolor = fgcolor
        self.rect_bgcolor = bgcolor

    def _height(self):
        return self.rect_height

    def _width(self):
        return self.rect_width

    def _draw(self, x, y, zoom_factor):
        self.painter.draw_rect(x, y, self.rect_width, self.rect_height, self.rect_fgcolor, self.rect_bgcolor)
        #painter.draw_text(self.rect_label, self.)

class EllipseFace(Face):
    __slots__ = ["x_radius", "y_radius"]

    def __init__(self, x_radius, y_radius, color, bgcolor):
        Face.__init__(self)
        self.x_radius = x_radius
        self.y_radius = y_radius
        self.ellipse_fgcolor = color
        self.ellipse_bgcolor = color

    def _width(self):
        return self.x_radius * 2.0

    def _height(self):
        return self.y_radius * 2.0

    def _draw(self, painter, x, y, zoom_factor):
        self.painter.draw_ellipse(x, y, self._width(), self._height())

class DiamondFace(Face):
    __slots__ = ["x_radius", "y_radius"]

    def __init__(self, x_radius, y_radius, color, bgcolor):
        Face.__init__(self)
        self.x_radius = x_radius
        self.y_radius = y_radius
        self.ellipse_fgcolor = color
        self.ellipse_bgcolor = color

    def _width(self):
        return self.x_radius * 2.0

    def _height(self):
        return self.y_radius * 2.0

    def _draw(self, painter, x, y, zoom_factor):
        self.painter.draw_ellipse(x, y, self._width(), self._height())

class TextFace(Face):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor', 'fstyle', 'tight_text', "_text_size"]

    @property
    def text(self):
        return self._text

    def __init__(self, text, ftype="Courier", fsize=10, fgcolor="black",
                 fstyle='normal', tight_text=False, min_size=(4,4)):
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
        self.min_size = min_size

    def _width(self):
        self._update_text_size()
        return self._text_size[0]

    def _height(self):
        self._update_text_size()
        return self._text_size[1]


    def _draw(self, x, y, zoom_factor):
        if zoom_factor * self._height() < self.min_size[1]:
            self.painter.draw_rect(x, y, self._width(), self._height(), "grey", "white")
        else:
            self.painter.draw_rect(x, y, self._width(), self._height(), "grey", None)
            self.painter.set_font(self.ftype, self.fsize)
            self.painter.draw_text(x, y, self._width(), self._height(), self.text, self.ftype, self.fsize)

    def _update_text_size(self):
        self._text_size = self.painter.get_text_size(self.text, self.ftype, self.fsize)


class AttrFace(TextFace):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor', 'fstyle', 'tight_text', "_text_size"]

    @property
    def text(self):
        return str(getattr(self.node, self._text)).strip()

    def __init__(self, attribute, ftype="Courier", fsize=10, fgcolor="black", fstyle='normal', tight_text=False, min_size=(4,4)):
        Face.__init__(self)
        self._text = attribute
        self.ftype = ftype
        self.fsize = fsize
        self.fgcolor = fgcolor
        self.fstyle = fstyle
        self.tight_text = tight_text
        self._text_size = None
        self.rotable = True
        self.min_size = min_size


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

