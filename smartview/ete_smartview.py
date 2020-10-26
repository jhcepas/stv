"""
Run ETE.

It can run in interactive mode (which I do not think is working now)
or as a web server.

As a web server it will listen in port 8090 and answer to requests
like "/get_scene_region/2,0,81,797,900" (zoom, x, y, w, h) with scenes
to be drawn (which include tree branches and associated images --
though the last part is not ready yet).
"""

import bottle
from random import randint
from json import dumps
import time
import logging
from .alg import SparseAlg, TreeAlignment, Alg, DiskHashAlg
from .utils import colorify
from . import common
from .main import TreeImage, gui
from .face_noqt import RectFace, TextFace, AttrFace, LabelFace, CircleLabelFace, GradientFace, HeatmapArcFace, HeatmapFace, SeqMotifFace
from .style import TreeStyle, add_face_to_node
from .ctree import Tree
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter as fmt
import numpy as np
import random
import sys
import pyximport
pyximport.install()

#from .. import Tree


# Create a custom logger
logger = logging.getLogger("smartview")
logger.setLevel(10)

# Create handlers
c_handler = logging.StreamHandler(sys.stdout)

# Create formatters and add it to handlers
c_format = logging.Formatter('%(levelname)s - %(message)s')
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

DESC = """
Smartview: explore large trees interactively
"""
MATRIX = None
ALG = None
BLOCK_SEQ_FACE = None
N2LEAVES = None
N2CONTENT = None


def get_args():
    "Return the parsed command line arguments"
    parser = ArgumentParser(description=__doc__, formatter_class=fmt)
    add = parser.add_argument  # shortcut

    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("-t", "--tree",
        help="file with the tree (- to read from stdin)")
    inputs.add_argument("-s", "--size", type=int,
        help="random tree size (for testing purposes)")
    add("-a", "--alg", help="Bind alignment")
    add("-m", "--mode", default='r', choices=['c', 'r'],
        help="drawing mode (c: cicular, r: rectangular)")
    add("-b", "--branch_mode", help="")
    add("--scale", type=float)
    add("--nwformat", type=int, default=0, choices=list(range(10)) + [100],
        help="newick format (0-9,100)")
    circ_layout = parser.add_argument_group("tree layout options")
    circ_layout.add_argument("--arc_span", type=float, default=360, help="in degrees")
    circ_layout.add_argument("--arc_start", type=float, default=0, help="in degrees")

    add("-z", "--zoom_factor", type=float, help="initial zoom level")
    add("-l", "--layout", help="layout function to use", default="basic_layout")
    add("--debug", action="store_true", help="enable debug mode")
    add("--track_mem", action="store_true", help="tracks memory usage")
    add("--profile", action="store_true", help="tracks cpu time")
    add("--timeit", action="store_true", help="tracks memory usage")
    add("--nogui", action="store_true")
    add("--ultrametric", action="store_true", help="convert to untrametric")
    add("--standardize", action="store_true", help="stand")
    add("--logscale", action="store_true", help="log scale")
    add("--midpoint", action="store_true", help="stand")
    add("--randbranches", action="store_true", help="stand")
    add("--softrandbranches", action="store_true", help="stand")
    add("-C", "--cmode", action="store_true")
    add("--tilesize", type=int, default=800)
    add("--heatmap", action="store_true")
    return parser.parse_args()


def link_to_table():
    pass


nameF = AttrFace("name", fsize=11, fgcolor='royalBlue', ftype='Arial')
nameF2 = AttrFace("name", fsize=16, fgcolor='indianred', ftype='Arial')
nameF3 = AttrFace("name", fsize=8, fgcolor='grey', ftype='Arial')
#nameF.margin_right = 10
distF = AttrFace("dist", fsize=10, fgcolor="grey", formatter="%0.3g")
supportF = AttrFace("support", fsize=16)
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


def alg_layout(node):
    if ALG and node in ALG:
        # add_face_to_node(TextFace(node.name), node,
        #                 column=9, position="aligned")
        add_face_to_node(BLOCK_SEQ_FACE, node, column=10, position="aligned")


def test_layout(node):
    node.img_style.size = 1
    # f.margin_left=20
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


def crouded_layout(node):
    if node.is_leaf():
        add_face_to_node(nameF, node, column=0, position="branch-right")
        add_face_to_node(nameF2, node, column=0, position="branch-right")
        add_face_to_node(nameF3, node, column=1, position="branch-right")

    else:
        if MATRIX is not None:
            hface = HeatmapArcFace(MATRIX[node._id], 100, 0.8)
            add_face_to_node(hface, node, column=0, position="aligned")

        if node.name:
            add_face_to_node(nameF, node, column=0, position="branch-top")
        add_face_to_node(distF, node, column=0, position="branch-bottom")
        add_face_to_node(
            TextFace(str(N2LEAVES[node]), fsize=13), node, column=0, position="branch-top")
#        add_face_to_node(TextFace("%0.2f" % n2dist[n], fsize=13), node, column=0, position="branch-top")
#            add_face_to_node(nameF, node, column=0, position="aligned")


def basic_layout(node):
    if node.is_leaf():
        add_face_to_node(nameF, node, column=0, position="branch-right")
    else:
        if node.name:
            add_face_to_node(distF, node, column=0, position="branch-bottom")
            #add_face_to_node(nameF, node, column=0, position="branch-top")


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
        add_face_to_node(
            TextFace(str(N2LEAVES[node]), fsize=13), node, column=0, position="branch-top")
#        add_face_to_node(TextFace("%0.2f" % n2dist[n], fsize=13), node, column=0, position="branch-top")
#            add_face_to_node(nameF, node, column=0, position="aligned")


def tol_layout(node, dim=None):
    nameF = TextFace(node.name, fgcolor="indianRed", fsize=16)
    # if node.rank:
    #     rankF = TextFace(node.sci_name, fgcolor="orange", fsize=10)
    distF = TextFace("%0.2f" % node.dist, fgcolor="#888888", fsize=8)
    sizeF = TextFace(" (size: %d)" % N2LEAVES[node], fsize=8)

    add_face_to_node(distF, node, column=0, position="branch-bottom")
    if node.is_leaf():
        add_face_to_node(nameF, node, column=0, position="branch-right")
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
            add_face_to_node(sizeF, node, column=1, position="branch-bottom")


def rect_layout(node):
    if node.is_leaf():
        add_face_to_node(rectF, node, column=0, position="branch-right")


def clean_layout(node):
    pass


def main():
    args = get_args()

    global N2LEAVES, N2CONTENT, ALG, MATRIX, BLOCK_SEQ_FACE

    common.CONFIG["debug"] = args.debug
    common.CONFIG["timeit"] = args.timeit
    common.CONFIG["C"] = args.cmode
    common.CONFIG["tilesize"] = args.tilesize

    if args.track_mem:
        from guppy import hpy
        h = hpy()
        h.setref()

    logger.info(colorify("Building ETE tree", "lblue"))

    if args.size:
        t1 = Tree()
        t1.populate(args.size/2, random_branches=True)
        t2 = Tree()
        t2.populate(args.size/2, random_branches=True)
        t = t1 + t2
    elif args.tree:
        try:
            t = Tree(args.tree, format=args.nwformat)
        except FileNotFoundError as e:
            sys.exit(e)

    if args.midpoint:
        t.set_outgroup(t.get_midpoint_outgroup())

    if args.standardize:
        t.standardize()

    if args.randbranches:
        for n in t.children[0].traverse():
            n.dist = random.randint(1, 99)/100.0
        for n in t.children[1].traverse():
            n.dist = random.randint(1, 15)/100.0

    if args.softrandbranches:
        for n in t.traverse():
            n.dist = random.randint(50, 80)/100.0

    N2LEAVES = {}
    precount = 0
    for post, n in t.iter_prepostorder():
        if post:
            N2LEAVES[n] = sum([N2LEAVES[ch] for ch in n.children])
        else:
            n._id = precount
            if not n.name:
                n.name = "Node:%06d" % (n._id)
            precount += 1
            if not n.children:
                N2LEAVES[n] = 1
    logger.info(colorify("Loaded tree: %d leaves and %d nodes" %
                         (N2LEAVES[t], precount), "lblue"))

    N2CONTENT = t.get_cached_content()

    if args.ultrametric:
        #min_rad = len(t)/(2*math.pi)
        #t.convert_to_ultrametric(tree_length=min_rad, strategy="log", logbase=1000)
        t.convert_to_ultrametric(strategy='balanced')

    if args.heatmap:
        global MATRIX
        MATRIX = np.random.rand(precount+1, 10)
        # #MATRIX.sort()
        # for post, n in t.iter_prepostorder():
        #     if post:
        #         mean = np.array([MATRIX[ch._id] for ch in n.children]).mean(axis=0)
        #         MATRIX[n._id] = mean
        #         #print(MATRIX[n._id])
        MATRIX[n.children[0]._id] = np.array(
            [1, 1, 1, 1, 1, 0.1, 0.1, 0.1, 0.1, 0.1])
        MATRIX[n.children[-1]._id] = np.array(
            [0.1, 0.1, 0.1, 0.1, 0.1, 1, 1, 1, 1, 1])

        for n in t.iter_descendants():
            for ch in n.children:
                rand = np.array([1-(random.randint(0, 1)/10.)
                                 for x in range(10)])
                MATRIX[ch._id] = MATRIX[n._id] * rand

    ts = TreeStyle()

    ts.layout_fn = globals()[args.layout]
    if args.alg:
        global ALG, BLOCK_SEQ_FACE
        try:
            #alg_dict = seqio.load_fasta(args.alg)
            #alg_dict = Alg(args.alg)
            alg_dict = DiskHashAlg(200, "alg.db")
            alg_dict.load_fasta(args.alg)
            ALG = TreeAlignment(alg_dict, N2CONTENT)
            #ALG.load_seqs(t, alg_dict)
            BLOCK_SEQ_FACE = SeqMotifFace(
                ALG, seqtype='aa', seq_format="seq", gap_format="blank", poswidth=3, total_width=None)
            ts.layout_fn.append(alg_layout)
        except FileNotFoundError as e:
            sys.exit(e)

    ts.mode = args.mode
    ts.arc_span = args.arc_span
    ts.arc_start = args.arc_start
    if args.scale:
        for n in t.traverse():
            n.dist *= args.scale
    elif args.logscale:
        for n in t.traverse():
            n.dist = np.log(1+n.dist) * 10
            n.dist = 5
    gui.start_app()  # need to have a QtApp initiated for some operations

    tree_image = TreeImage(t, ts)

    if args.profile:
        import cProfile
        import pstats
        import io
        pr = cProfile.Profile()
        pr.enable()

    if not args.nogui:
        gui.display(tree_image, zoom_factor=args.zoom_factor)
    else:
        gui.start_server(tree_image)

    if args.profile:
        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    if args.track_mem:
        print(repr(t))
        print(h.heap())


if __name__ == '__main__':
    main()
