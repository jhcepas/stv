
import math
from common import *

from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import *


def get_cart_coords(radius, radians, cx, cy):
    a = (2*math.pi)-radians;
    x = math.cos(a) * radius
    y = math.sin(a) * radius
    return x+cx, -y+cy


def get_link_paths(tree_image, node_links):
    img_data = tree_image.img_data

    link_paths = []
    cx, cy = tree_image.width/2, tree_image.height/2
    
    for a, b in node_links:
        if img_data[a._id][_acenter] > img_data[b._id][_acenter]:
            a, b = b, a
        a_rad = img_data[a._id][_fnw]
        a_astart= img_data[a._id][_astart]
        a_aend= img_data[a._id][_aend]        
        a1x, a1y = get_cart_coords(a_rad, a_astart, cx, cy)
        a2x, a2y = get_cart_coords(a_rad, a_aend, cx, cy)

        b_rad = img_data[b._id][_fnw]
        b_astart= img_data[b._id][_astart]
        b_aend= img_data[b._id][_aend]        
        b1x, b1y = get_cart_coords(b_rad, b_astart, cx, cy)
        b2x, b2y = get_cart_coords(b_rad, b_aend, cx, cy)
       
        path = QPainterPath()
        path.moveTo(a2x, a2y)
        path.quadTo(cx, cy, b1x, b1y)
        
        #path.lineTo(b2x, b2y)
        path.arcTo(cx -b_rad, cy -b_rad,
                   b_rad*2, b_rad*2,
                   -math.degrees(b_astart), -math.degrees(b_aend-b_astart))
        path.quadTo(cx, cy, a1x, a1y)
        path.lineTo(a2x, a2y)
        # else:
        #     path.quadTo(cx, cy, a1x, a1y)
            
        # if a1x != a2x or a1y != a2y:
        #     path.arcTo(cx - a_rad, cy - a_rad,
        #                a_rad*2, a_rad*2,
        #                -a_astart, -(a_aend-a_astart))
                            
        link_paths.append(path)
    return link_paths
    
def draw_text_in_path(pp, text, follow_path, ftype, fcolor, fsize):
    length = follow_path.length()
    pp.setPen(get_qpen(fcolor))
    font = get_qfont(ftype, fsize, False)
    pp.setFont(font)
    fm = QFontMetrics(font)
    text_width = fm.width(text)
   
    # approx center text in path
    current_length = (length/2) - (text_width/2)
    for letter in text:
        perc = follow_path.percentAtLength(current_length)
        point = QPointF(follow_path.pointAtPercent(perc))
        angle = follow_path.angleAtPercent(perc)

        current_length += fm.width(letter)
        
        pp.save()
        pp.translate(point)
        pp.rotate(-angle)
        pp.drawText(QPoint(0, 0), letter)
        pp.restore()
