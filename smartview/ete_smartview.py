from __future__ import absolute_import
from __future__ import print_function
import sys
import random
import math
import numpy as np
from argparse import ArgumentParser
from .ctree import Tree
#from .. import Tree
from .style import TreeStyle, add_face_to_node
from .face import  RectFace, TextFace, AttrFace, LabelFace, CircleLabelFace, GradientFace, HeatmapArcFace, HeatmapFace
from .main import TreeImage, gui
from . import common
from .common import *

DESC = """
Smartview 0.1
"""
MATRIX = None

def populate_args(parser):
    parser.add_argument("-t", dest="src_trees", type=str, help="target_tree", nargs="+")
    parser.add_argument("-s", dest="size", type=int, help="size")
    parser.add_argument("-z", dest="zoom_factor", type=float, help="initial zoom level")
    parser.add_argument("-l", dest="layout", type=str, help="layout function to use", default="basic_layout")
    parser.add_argument("--debug", dest="debug", action="store_true", help="enable debug mode")
    parser.add_argument("--mem", dest="track_mem", action="store_true", help="tracks memory usage")
    parser.add_argument("--profile", dest="profile", action="store_true", help="tracks cpu time")
    parser.add_argument("--timeit", dest="track_time", action="store_true", help="tracks memory usage")
    parser.add_argument("--nogui", dest="nogui", action="store_true")
    parser.add_argument("--ultrametric", dest="ultrametric", action="store_true", help="convert to untrametric")
    parser.add_argument("--standardize", dest="standardize", action="store_true", help="stand")
    parser.add_argument("-C", dest="cmode", action="store_true")
    parser.add_argument("--tilesize", dest="tilesize", type=int, default=800)
    parser.add_argument("--polardist", dest="polardist", type=float, default=0)
    parser.add_argument("--scale", dest="scale", type=float, default=None)
    parser.add_argument("--newick_format", dest="nwformat", type=int, default=0)
    parser.add_argument("--heatmap", dest="heatmap", action="store_true")
    


nameF = AttrFace("name", fsize=10, fgcolor='royalBlue', ftype='Arial')
nameF2 = AttrFace("name", fsize=16, fgcolor='indianred', ftype='Arial')
nameF3 = AttrFace("name", fsize=8, fgcolor='grey', ftype='Arial')
#nameF.margin_right = 10
distF = AttrFace("dist", fsize=12)
supportF = AttrFace("support", fsize=12)
labelF = LabelFace(70)
labelF.fill_color = "thistle"
labelF2 = LabelFace(70)
labelF2.fill_color = "indianred"

circleF = CircleLabelFace(attr="support", solid=True, color="blue")

hola = TextFace("hola")
mundo = TextFace("mundo", fsize=7, fgcolor="grey")
ornot = TextFace("ornot", fsize=6, fgcolor="steelblue")
rectF = RectFace(100, 100, bgcolor="indianred")
f = RectFace(20, 10, bgcolor="pink")
f2 = RectFace(120, 10, bgcolor="blue")
f3 = RectFace(20, 10, bgcolor="green")
f4 = RectFace(20, 10, bgcolor="indianred")
f5 = RectFace(20, 10, bgcolor="steelblue")

gradF = GradientFace(width=50, node_attr="custom")
gradF.only_if_leaf = True

def real_layout(node):
    if node.is_leaf():
        add_face_to_node(nameF, node, column=0, position="branch-right")
        #add_face_to_node(f5, node, column=1, position="branch-right")

        #add_face_to_node(labelF, node, column=2, position="branch-right")
        #add_face_to_node(labelF2, node, column=3, position="branch-right")
        #add_face_to_node(f5, node, column=1, position="aligned")
        #add_face_to_node(nameF, node, column=1, position="aligned")

        # if random.random()>0.5:
        #     add_face_to_node(labelF, node, column=3, position="aligned")
        #     add_face_to_node(labelF2, node, column=4, position="aligned")
        # else:
        #     add_face_to_node(labelF2, node, column=3, position="aligned")
        #     add_face_to_node(labelF, node, column=4, position="aligned")

        add_face_to_node(distF, node, column=0, position="branch-top")
        add_face_to_node(supportF, node, column=1, position="branch-bottom")
    elif node.up:
        if node.name:
            add_face_to_node(nameF, node, column=0, position="branch-top")
        #add_face_to_node(distF, node, column=0, position="branch-bottom")
        add_face_to_node(supportF, node, column=1, position="branch-bottom")

        #add_face_to_node(circleF, node, column=5, position="branch-right")
    add_face_to_node(gradF, node, column=10, position="branch-right")

    
def test_layout(node):
    node.img_style.size = 1
    #f.margin_left=20
    add_face_to_node(f, node, column=0, position="branch-right")
    add_face_to_node(f, node, column=0, position="branch-right")
    #add_face_to_node(rectF, node, column=1, position="branch-right")
    if node.is_leaf():
        add_face_to_node(nameF, node, column=2, position="branch-right")
    else:
        if node.name:
            add_face_to_node(nameF, node, column=0, position="branch-top")

    add_face_to_node(hola, node, column=1, position="branch-top")
    add_face_to_node(ornot, node, column=1, position="branch-bottom")
    add_face_to_node(mundo, node, column=2, position="branch-bottom")
    add_face_to_node(mundo, node, column=1, position="branch-bottom")

def test_layout2(node):
    #f.margin_left=20
    add_face_to_node(f, node, column=0, position="branch-right")
    add_face_to_node(f, node, column=0, position="branch-right")
    add_face_to_node(rectF, node, column=1, position="branch-right")

    add_face_to_node(f, node, column=1, position="branch-top")
    add_face_to_node(f, node, column=1, position="branch-bottom")
    add_face_to_node(f2, node, column=2, position="branch-bottom")
    add_face_to_node(f3, node, column=1, position="branch-bottom")

def basic_layout(node):
    if node.is_leaf():
        add_face_to_node(nameF, node, column=0, position="branch-right")
    else:
        if node.name:
            add_face_to_node(nameF, node, column=0, position="branch-top")

def stacked_layout(node, dim=None):
    if node.is_leaf():
        add_face_to_node(nameF, node, column=0, position="branch-right")
        add_face_to_node(nameF2, node, column=0, position="branch-right")
        add_face_to_node(nameF3, node, column=1, position="branch-right")
        if MATRIX is not None: 
            hface = HeatmapArcFace(MATRIX[node._id], 100, 0.5)
            add_face_to_node(hface, node, column=0, position="aligned")
            hface = HeatmapFace(MATRIX[node._id], 10, 10)
            add_face_to_node(hface, node, column=2, position="branch-right")

    else:
        if MATRIX is not None: 
            hface = HeatmapArcFace(MATRIX[node._id], 100, 0.8)
            add_face_to_node(hface, node, column=0, position="aligned")

        if node.name:
            add_face_to_node(nameF, node, column=0, position="branch-top")
        add_face_to_node(distF, node, column=0, position="branch-bottom")
        add_face_to_node(TextFace(str(n2leaves[node]), fsize=13), node, column=0, position="branch-top")
#        add_face_to_node(TextFace("%0.2f" % n2dist[n], fsize=13), node, column=0, position="branch-top")
#            add_face_to_node(nameF, node, column=0, position="aligned")

def rect_layout(node):
    if node.is_leaf():
        add_face_to_node(rectF, node, column=0, position="branch-right")

def clean_layout(node):
    pass

def run(args):
    global n2leaves
    common.CONFIG["debug"] = args.debug
    common.CONFIG["timeit"] = args.track_time
    common.CONFIG["C"] = args.cmode
    common.CONFIG["tilesize"] = args.tilesize

    if args.track_mem:
        from guppy import hpy
        h = hpy()
        h.setref()

    if args.size:
        t1 = Tree()
        t1.populate(args.size, random_branches=True)
        for n in t1.traverse():
            n.dist = random.randint(1, 99)/100.0
            n.dist = 1.0
        t2 = Tree()
        t2.populate(args.size, random_branches=True)
        for n in t2.traverse():
            n.dist = random.randint(1, 15)/100.0
        #t = t1 + t2
        t = t1
    elif args.src_trees:
        t = Tree(args.src_trees[0], format=args.nwformat)

    print ("annotating")
    n2leaves = {}
    precount = 0
    for post, n in t.iter_prepostorder():
        if post:
            n2leaves[n] = sum([n2leaves[ch] for ch in n.children])
        else:
            n._id = precount
            precount += 1
            if not n.children:
                n2leaves[n] = 1

    printmem("after tree load")

    if args.standardize:
        t.standardize()

    if args.ultrametric:
        #min_rad = len(t)/(2*math.pi)
        #t.convert_to_ultrametric(tree_length=min_rad, strategy="log", logbase=1000)
        t.convert_to_ultrametric(strategy='balanced')

    if args.heatmap:
        global MATRIX
        MATRIX = np.random.rand(precount+1, 10)

    if args.polardist:
        #node, mdist = t.get_farthest_leaf()
        d = 1
        node2pdist = {}
        for post, node in t.iter_prepostorder():
            if post:
                d -= node.dist
            else:
                if node.dist == 0:
                    node2pdist[node] = 0.0
                else:
                    c = d * args.polardist
                    #print node.dist / c
                    node2pdist[node] = node.dist / c

                if not node.is_leaf():
                    d += node.dist
        for n in t.traverse():
            n.dist = node2pdist[n]

    # for n in t.traverse():
    #     n.support = random.randint(5,25)

    ts = TreeStyle()


    ts.layout_fn = globals()[args.layout]
    ts.mode = "c"
    ts.arc_span = 360
    ts.arc_start = -90
    if args.scale:
        ts.scale = args.scale

    gui.start_app() # need to have a QtApp initiated for some operations

    tree_image = TreeImage(t, ts)

    print("Tree image created", len(tree_image.cached_leaves))
    if args.profile:
        import cProfile, pstats, StringIO
        pr = cProfile.Profile()
        pr.enable()

    if not args.nogui:
        gui.display(tree_image, zoom_factor=args.zoom_factor)

    if args.profile:
        pr.disable()
        s = StringIO.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print (s.getvalue())

    if args.track_mem:
        print (repr(t))
        print (h.heap())


def main():
    parser = ArgumentParser()
    populate_args(parser)
    args = parser.parse_args()
    run(args)
