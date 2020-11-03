from collections import defaultdict
import numpy as np

from .utils import timeit
from . import (layout, layout_circular, layout_rect, gui, links)
from .common import _fnh, _fnw

import math

class TreeImage(object):
    def __init__(self, root_node, tree_style):
        self.tree_style = tree_style
        self.root_node = root_node
        self.scale = tree_style.scale
        self.root_open = 0

        self.cached_prepostorder = None
        self.cached_preorder = None
        self.cached_content = None

        # FIXME: explain what they contain and what for
        self.img_data = None
        self.leaf_apertures = None
        self.width = 0.0
        self.height = 0.0
        self.break_points = None

        self.link_paths = []
        self.circ_collision_paths = None
        self.rect_collision_paths = None

        self.initialize()
        self.set_leaf_aperture()
        self.adjust_dimensions()
        self.adjust_apertures()
        self.adjust_branch_lengths()
        self.update_collision_paths()

    @timeit
    def set_leaf_aperture(self, nodeid=None, factor=None):
        if self.leaf_apertures is None:
            circle_aperture = math.radians(self.tree_style.arc_span)
            even_aperture =  circle_aperture / float(len(self.cached_leaves))
            self.leaf_apertures = np.array([even_aperture]*len(self.cached_leaves))
        elif nodeid:
            start = self.cached_content[nodeid][0]
            end = self.cached_content[nodeid][1]
            current_aperture = self.leaf_apertures[start:end].sum()

            if 1:
                step = current_aperture * 0.10

                if factor > 0 and current_aperture + step > 360:
                    step = 360 - current_aperture
                elif factor < 0 and current_aperture - step < 0:
                    step = current_aperture
                increment = step / (end-start)
                reduction = step / (len(self.leaf_apertures) - (end-start))
                if factor < 0:
                    increment = increment * -1
                    reduction = reduction * -1
                self.leaf_apertures[start:end] += increment
                self.leaf_apertures[end:] -= reduction
                self.leaf_apertures[:start] -= reduction
            else:
                if factor > 0 :
                    new_aperture = current_aperture + (current_aperture * 0.10)
                else:
                    new_aperture = current_aperture - (current_aperture * 0.10)

                if new_aperture > 350:
                    new_aperture = 359
                elif new_aperture < 1:
                    new_aperture = 0.0001

                increment = new_aperture / (end-start)
                reduction = (360 - new_aperture)/ (len(self.leaf_apertures) - (end-start))


                self.leaf_apertures[start:end] = increment
                self.leaf_apertures[end:] = reduction
                self.leaf_apertures[:start] = reduction

    def adjust_dimensions(self):
        self.img_data = layout.get_empty_matrix(len(self.cached_preorder))

        layout.update_node_dimensions(img_data=self.img_data,
                                      cached_prepostorder=self.cached_prepostorder,
                                      cached_preorder=self.cached_preorder,
                                      scale=self.scale,
                                      force_topology=self.tree_style.force_topology)
    @timeit
    def adjust_apertures(self):
        if self.tree_style.mode == 'r':
            layout_rect.update_rect_positions(img_data=self.img_data,
                                              cached_prepostorder=self.cached_prepostorder,
                                              cached_preorder=self.cached_preorder,
                                              leaf_apertures=self.leaf_apertures)

        elif self.tree_style.mode == "c":
            layout_circular.update_node_angles(img_data=self.img_data,
                                               arc_start=self.tree_style.arc_start,
                                               cached_prepostorder=self.cached_prepostorder,
                                               cached_preorder=self.cached_preorder,
                                               leaf_apertures=self.leaf_apertures)


    def adjust_branch_lengths(self, adjust_fn=None):
        if not adjust_fn:
            adjust_fn = layout.default_adjust_branch
        #adjust_fn(self)

        self.root_open = 0.0
        self.scale = 1.0
        aligned_region_width = 100

        if self.tree_style.mode == 'c':
            #aligned_region_width = layout.compute_aligned_region_width(self)
            max_leaf_radius = layout_circular.update_node_radius(self.img_data,
                                                                 self.cached_prepostorder, self.cached_preorder,
                                                                 self.scale, self.root_open)

            # set image total size
            self.width = (max_leaf_radius + aligned_region_width) * 2
            self.height = self.width
            self.radius = (max_leaf_radius + aligned_region_width, max_leaf_radius + aligned_region_width)
        elif self.tree_style.mode == 'r':
            self.adjust_apertures()
            self.width = self.img_data[0][_fnw]
            self.height = self.img_data[0][_fnh]


    def update_collision_paths(self):
        if self.tree_style.mode == 'c':
            self.circ_collision_paths = defaultdict(lambda: [None, None])
        elif self.tree_style.mode == 'r':
            self.rect_collision_paths = defaultdict(lambda: [None, None])

    @timeit
    def initialize(self):
        self.cached_prepostorder = []
        self.cached_preorder = []
        self.cached_leaves = []
        node_id = 0
        leaf_id = 0
        for post, node in self.root_node.iter_prepostorder():
            if not post:
                node._id = node_id
                self.cached_prepostorder.append(node._id)
                node_id += 1
                self.cached_preorder.append(node)
                if node.is_leaf():
                    leaf_id += 1
                    self.cached_leaves.append(node._id)
                # for func in self.tree_style.layout_fn:
                #     func(node)
            else:
                self.cached_prepostorder.append(-node._id)
