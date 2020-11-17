"""
Run ETE, smartview version: explore large trees interactively.

It can run as a Qt app (not working at the moment) or as a web server.

As a web server it will listen in port 8090 and answer to requests
like "/get_scene_region/2,0,81,797,900" (zoom, x, y, w, h) with scenes
to be drawn (which include tree branches and associated images --
though the last part is not ready yet).
"""

import sys
import random
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter as fmt
import pyximport
pyximport.install()

import logging
logger = logging.getLogger("smartview")
logger.setLevel('DEBUG')
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logger.addHandler(log_handler)

import numpy as np

from . import layout
from .align import SparseAlign, TreeAlignment, Align, DiskHashAlign
from .utils import blue
from . import common
from .main import TreeImage, gui
from .style import TreeStyle
from .ctree import Tree


MATRIX = None
ALIGN = None
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
    add("-a", "--align", help="bind alignment")
    add("-m", "--mode", default='r', choices=['c', 'r'],
        help="drawing mode (c: cicular, r: rectangular)")
    add("-b", "--branch_mode", help="")
    add("--scale", type=float)
    add("--nwformat", type=int, default=0, choices=list(range(10)) + [100],
        help="newick format (0-9,100)")
    circ_layout = parser.add_argument_group("tree layout options")
    circ_layout.add_argument("--arc_span", type=float, default=360, help="in degrees")
    circ_layout.add_argument("--arc_start", type=float, default=0, help="in degrees")

    add("-z", "--zoom", type=float, help="initial zoom level")
    add("-l", "--layout", default="basic")
    add("--layouts-path", default=".", help="path for plugins / extra layouts")
    add("--debug", action="store_true", help="enable debug mode")
    add("--track_mem", action="store_true", help="tracks memory usage")
    add("--profile", action="store_true", help="tracks cpu time")
    add("--timeit", action="store_true", help="tracks memory usage")
    add("--qt-gui", action="store_true")
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


def main():
    args = get_args()

    global N2LEAVES, N2CONTENT, ALIGN, MATRIX, BLOCK_SEQ_FACE

    common.CONFIG["debug"] = args.debug
    common.CONFIG["timeit"] = args.timeit
    common.CONFIG["C"] = args.cmode
    common.CONFIG["tilesize"] = args.tilesize

    if args.track_mem:
        from guppy import hpy
        h = hpy()
        h.setref()

    logger.info(blue("Building ETE tree"))

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
    logger.info(blue("Loaded tree: %d leaves and %d nodes" %
                         (N2LEAVES[t], precount)))

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

    ts.layouts = layout.load_layouts('layouts')
    print(ts.layouts)
    ts.layouts_path = args.layouts_path
    ts.layout_fns.append(ts.layouts[args.layout])

    if args.align:
        global ALIGN, BLOCK_SEQ_FACE
        try:
            #align_dict = seqio.load_fasta(args.align)
            #align_dict = Align(args.align)
            align_dict = DiskHashAlign(200, "align.db")
            align_dict.load_fasta(args.align)
            ALIGN = TreeAlignment(align_dict, N2CONTENT)
            #ALIGN.load_seqs(t, align_dict)
            # BLOCK_SEQ_FACE = face.SeqMotifFace(
            #     ALIGN, seqtype='aa', seq_format="seq", gap_format="blank", poswidth=3, total_width=None)
            #ts.layout_fns.append(layout_align)
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

    if args.qt_gui:
        gui.display(tree_image, zoom_factor=args.zoom)
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
