from PyQt5.QtGui import *
from PyQt5.QtCore import QRectF

import numpy as np
import re
from . import colors
import colorsys
from .utils import timeit, debug

# Pick two colors. Values from 0 to 1. See "hue" at
# http://en.wikipedia.org/wiki/HSL_and_HSV


def get_color_gradient():

    COLOR1 = 0.67
    COLOR2 = 0.3
    COLOR_INTENSITY = 0.6

    def gradient(hue):
        min_lightness = 0.35
        max_lightness = 0.85
        base_value = COLOR_INTENSITY

        # each gradient must contain 100 lightly descendant colors
        colors = []
        def rgb2hex(rgb): return '#%02x%02x%02x' % rgb
        l_factor = (max_lightness-min_lightness) / 100.
        l = min_lightness
        while l <= max_lightness:
            l += l_factor
            rgb = rgb2hex(
                tuple([int(x*255) for x in colorsys.hls_to_rgb(hue, l, base_value)]))
            colors.append(rgb)
        return colors

    def color_scale():
        colors = []
        for c in gradient(COLOR1):
            color = QColor(c)
            colors.append(color)
        colors.append(QColor("white"))
        for c in reversed(gradient(COLOR2)):
            color = QColor(c)
            colors.append(color)
        return colors

    return color_scale()


GRADIENT = get_color_gradient()


def get_arc_path(rect1, rect2, rad_angles):
    angles = list(map(np.degrees, rad_angles))
    path = QPainterPath()
    span = angles[-1] - angles[0]
    if 0 and span < 0.01:  # solves precision problems drawing small arcs
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
                 "max_height", "max_width",
                 "only_if_leaf",
                 ]

    def __repr__(self):
        print(type(self.__hash__()))
        return "'%s' (%s)" % (self.__class__, hex(int(self.__hash__())))

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

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
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

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
        painter.save()
        painter.scale(zoom_factor, zoom_factor)
        painter.translate(-self.img_rad*2, -self.img_rad)

        # r1 = QRectF(0, 0, (self.img_rad)*2, (self.img_rad)*2)
        # painter.setPen(QColor("blue"))
        # painter.drawRect(r1)
        step = (self.width) / float(len(self.values))
        offset = 0
        for v in self.values:
            # color = random_color(l=self.h, s=0.7, h=v)

            color = GRADIENT[int(v*200)]

            r1 = QRectF(-offset, -offset,
                        (self.img_rad+offset)*2, (self.img_rad+offset)*2)
            offset += step

            r2 = QRectF(-offset, -offset,
                        (self.img_rad+offset)*2, (self.img_rad+offset)*2)

            # if self.node.name == 'aaaaaaaaac':
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
            # path = get_arc_path(r1, r2, [span/2, -span/2])
            path = get_arc_path(
                r1, r2, [self.arc_start-self.arc_center, self.arc_end-self.arc_center])
            painter.drawPath(path)

        painter.restore()


class HeatmapFace(Face):
    __slots__ = ['rect_width', 'rect_height',
                 'rect_label', "fgcolor", 'bgcolor', 'values']

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

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
        painter.save()
        painter.scale(zoom_factor, zoom_factor)
        x = 0
        for v in self.values:
            color = colors.random_color(l=0.5, s=0.5)
            painter.fillRect(QRectF(x, y, self.rect_width,
                                    self.rect_height), QColor(color))
            painter.setPen(QColor("black"))
            painter.drawRect(QRectF(x, y, self.rect_width, self.rect_height))
            x += self.rect_width
        painter.restore()


class RectFace(Face):
    __slots__ = ['rect_width', 'rect_height', 'rect_label',
                 'rect_fgcolor', 'rect_bgcolor', "fgcolor", 'bgcolor']

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

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
        painter.save()
        painter.scale(zoom_factor, zoom_factor)
        painter.setPen(QColor(self.fgcolor))
        if self.bgcolor:
            painter.fillRect(QRectF(x, y, self.rect_width,
                                    self.rect_height), QColor(self.bgcolor))
            painter.setPen(QColor("black"))
            painter.drawRect(QRectF(x, y, self.rect_width, self.rect_height))
        else:
            painter.drawRect(QRectF(x, y, self.rect_width, self.rect_height))
        painter.restore()


class TextFace(Face):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor',
                 'fstyle', 'tight_text', "_text_size", "min_fsize"]

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

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
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
            # painter.drawText(x, y+self._height(), self.text)
        painter.restore()

    def _get_font(self):
        italic = (self.fstyle == "italic")
        return QFont(self.ftype, pointSize=self.fsize, italic=italic)


class AttrFace(TextFace):
    __slots__ = ['_text', 'fsize', 'ftype', 'fgcolor',
                 'fstyle', 'tight_text', "_text_size", "min_fsize"]

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

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
        pass


class GradientFace(Face):
    __slots__ = ["width", "node_attr",
                 "max_value", "min_value", "center_value"]

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
        self.fill_color = colors.random_color(h=0.3, s=0.5, l=value)

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
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

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):

        if self.solid:
            painter.setBrush(QColor(self.color))
            painter.drawEllipse(x, y, self._width(), self._height())
        else:
            painter.setPen(QPen(QColor(self.color)))
            painter.drawEllipse(x, y, self._width(), self._height())


class SeqMotifFace(Face):
    """
    Creates a face based on an amino acid or nucleotide sequence and a
    list of motif regions.

    :param None seq: a text string containing an aa or nt sequence. If
        not provided, ``seq`` and ``compactseq`` motif modes will not be
        available.

    :param None motifs: a list of motif regions referred to original
        sequence. Each motif is defined as a list containing the
        following information:

        ::

          motifs = [[seq.start, seq.end, shape, width, height, fgcolor, bgcolor, text_label],
                   [seq.start, seq.end, shape, width,
                       height, fgcolor, bgcolor, text_label],
                   ...
                  ]

        Where:

         * **seq.start:** Motif start position referred to the full sequence (1-based)
         * **seq.end:** Motif end position referred to the full sequence (1-based)
         * **shape:** Shape used to draw the motif. Available values are:

            * ``o`` = circle or ellipse
            * ``>``  = triangle (base to the left)
            * ``<``  = triangle (base to the left)
            * ``^``  = triangle (base at bottom)
            * ``v``  = triangle (base on top )
            * ``<>`` = diamond
            * ``[]`` = rectangle
            * ``()`` = round corner rectangle
            * ``line`` = horizontal line
            * ``blank`` = blank space

            * ``seq`` = Show a color and the corresponding letter of each sequence position
            * ``compactseq`` = Show a thinh vertical color line for each sequence position

         * **width:** total width of the motif (or sequence position width if seq motif type)
         * **height:** total height of the motif (or sequence position height if seq motif type)
         * **fgcolor:** color for the motif shape border
         * **bgcolor:** motif background color. Color code or name can be preceded with the "rgradient:" tag to create a radial gradient effect.
         * **text_label:** a text label in the format 'FontType|FontSize|FontColor|Text', for instance, arial|8|white|MotifName""

    :param line gap_format: default shape for the gaps between motifs
    :param blockseq seq_format: default shape for the seq regions not covered in motifs
    """
    AA2IMG = {}
    for aa, color in colors.aabgcolors.items():
        ii = QImage(20, 20, QImage.Format_ARGB32_Premultiplied)
        ii.fill(QColor(color).rgb())
        AA2IMG[aa] = ii

    BLOCK = QImage(10, 10, QImage.Format_ARGB32_Premultiplied)
    BLOCK.fill(QColor("white"))

    def __init__(self, node2seq, seqtype="aa",
                 gap_format="line", seq_format="()",
                 posheight=10, poswidth=10, total_width=None,
                 fgcolor='slategrey', bgcolor='slategrey', gapcolor='black'):

        Face.__init__(self)
        self.node2seq = node2seq
        self.scale_factor = 1
        self.overlaping_motif_opacity = 0.5
        self.adjust_to_text = False

        self.gap_format = gap_format
        self.seq_format = seq_format

        self.posheight = posheight
        self.poswidth = poswidth
        self.total_width = total_width

        self.fgcolor = fgcolor
        self.bgcolor = bgcolor

        _pp = QPainter(self.BLOCK)
        _pp.setPen(QColor(self.bgcolor))
        _pp.setBrush(QColor(self.bgcolor))
        _pp.drawRoundedRect(0, 0, 10, 10, 3, 3)
        _pp.end()

    def get_chunks(self, seq):
        chunks = []
        pos = 0
        for reg in re.split('([^-]+)', seq):
            if not reg.startswith("-"):
                typ = self.seq_format
            else:
                typ = self.gap_format
            chunks.append((pos, pos+len(reg)-1, typ))
            pos += len(reg)

        return chunks

    def _width(self):
        seq = self.node2seq[self.node]
        return self.poswidth * len(seq)

    def _height(self):
        return self.posheight

    def _size(self):
        return self._width(), self._height()

    def _draw(self, painter, x, y, zoom_factor, w=None, h=None):
        sequence = self.node2seq[self.node]        
        
        max_visiable_pos = int(np.ceil(w / self.poswidth))
        sequence = sequence[0:max_visiable_pos]
        chunks = self.get_chunks(sequence)
        #print('------------------------', max_visiable_pos, orig_len, w, self.poswidth)
                
        painter.save()
        painter.translate(x, y)

        if self.total_width:
            real_w = len(sequence) * self.poswidth
            xfactor = (self.total_width) / real_w
        else:
            xfactor = 1

        #painter.scale(xfactor, zoom_factor)

        painter.setPen(QColor(self.fgcolor))
        painter.setBrush(QColor(self.bgcolor))

        for index, (seq_start, seq_end, typ) in enumerate(chunks):

            # this are the actual coordinates mapping to the sequence
            w = ((seq_end - seq_start) + 1) * self.poswidth

            if typ == "-" or typ == "line":
                painter.drawLine(0, h/2, w, h/2)
            elif typ == " " or typ == "blank":
                pass
            elif typ == "o":
                painter.drawEllipse(0, 0, w, h)
            elif typ == ">":
                pass
            elif typ == "v":
                pass
            elif typ == "<":
                pass
            elif typ == "^":
                pass
            elif typ == "<>":
                pass
            elif typ == "[]":
                painter.drawRect(0, 0, w, h)
            elif typ == "()":
                pass
                # painter.drawRoundedRect(0, 0, w, h, 3, 3)
                painter.drawImage(0, 0, self.BLOCK, sw=w, sh=h)
            elif typ == "seq" and sequence:
                self._draw_sequence(painter, sequence[seq_start:seq_end+1],
                                    poswidth=self.poswidth, posheight=self.posheight)
            else:
                raise ValueError("Unknown Seq type: %s" % typ)

            painter.translate(w, 0)

            # if name and i:
            #     family, fsize, fcolor, text = name.split("|")
            #     #qfmetrics = QFontMetrics(qfont)
            #     #txth = qfmetrics.height()
            #     #txtw = qfmetrics.width(text)
            #     txt_item = TextLabelItem(text, w, h,
            #                              fsize=fsize, ffam=family, fcolor=fcolor)
            #     # enlarges circle domains to fit text
            #     #if typ == "o":
            #     #    min_r = math.hypot(txtw/2.0, txth/2.0)
            #     #    txtw = max(txtw, min_r*2)

            #     #y_txt_start = (max_h/2.0) - (h/2.0)
            #     txt_item.setParentItem(i)
            #     #txt_item.setPos(0, ystart)

            # if i:
            #     i.setParentItem(self.item)
            #     i.setPos(xstart, ystart)

            #     if bg:
            #         if bg.startswith("rgradient:"):
            #             bg = bg.replace("rgradient:", "")
            #             try:
            #                 c1, c2 = bg.split("|")
            #             except ValueError:
            #                 c1, c2 = bg, "white"
            #             rect = i.boundingRect()
            #             gr = QRadialGradient(rect.center(), rect.width()/2)
            #             gr.setColorAt(0, QColor(c2))
            #             gr.setColorAt(1, QColor(c1))
            #             color = gr
            #         else:
            #             color = QColor(bg)
            #         try:
            #             i.setBrush(color)
            #         except:
            #             pass

            #     if fg:
            #         i.setPen(QColor(fg))

            #     if opacity < 1:
            #         i.setOpacity(opacity)

            # max_x_pos = max(max_x_pos, xstart + w)
            # current_seq_end = max(seq_end, current_seq_end)

        painter.restore()

    def _draw_sequence(self, p, seq, seqtype="aa", poswidth=10, posheight=10,
                       draw_text=False):

        x, y = 0, 0
        for letter in seq:
            # letter = letter.upper()
            if draw_text and poswidth >= 8:
                # , max(1, poswidth), posheight)
                p.drawImage(x, 0, self.AA2IMG[letter])
                qfont.setPixelSize(min(posheight, poswidth))
                p.setFont(qfont)
                p.setBrush(QBrush(QColor("black")))
                qfont = QFont("Courier")
                p.drawText(x, 0, poswidth, posheight,
                           Qt.AlignCenter | Qt.AlignVCenter,
                           letter)
            elif letter == "-" or letter == ".":
                pass
                # p.drawImage(x, 0, self.AA2IMG['-'])#, max(1, poswidth), posheight)
            else:
                p.drawImage(x, 0, self.AA2IMG[letter],
                            sw=poswidth, sh=posheight)

            x += poswidth
        return x, posheight
