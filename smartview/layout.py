import math
from collections import defaultdict

import numpy as np

from .utils import timeit
from .common import *

def get_empty_matrix(nnodes):
    '''Returns an empty matrix prepared to allocated all data for a tree image of
    "nnodes"
    '''
    #matrix = np.zeros(nnodes, dtype="int8,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,float64,float64,float64,float64,float64,float64,float64,float64")
    matrix = np.zeros((nnodes,MATRIX_FIELDS), dtype="float64")
    return matrix


@timeit
def update_node_dimensions(img_data, cached_prepostorder, cached_preorder,
                           scale=1.0, force_topology=False):
    prev_id = 0
    root_visited = False
    for nid in cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0: root_visited = True
        if postorder:
            # leaves are never visited in postorder, so anything here is an internal node
            dim = img_data[abs(nid)]
            dim[_is_leaf] = 0
            dim[_max_leaf_idx] = prev_id
        else:
            dim = img_data[nid]
            node = cached_preorder[nid]
            face_pos_sizes = compute_face_dimensions(node, node._temp_faces)
            dim[_btw:_bah+1] = face_pos_sizes
            dim[_blen] = node.dist if not force_topology else 1.0
            dim[_bh] = max(node.img_style.hz_line_width, 1.0)
            dim[_parent] = node.up._id if nid > 0 else 0
            dim[_is_leaf] = 1 # assume leaf, fixed in postorder
            dim[_max_leaf_idx] = nid
            prev_id = nid

def compute_face_dimensions(node, facegrid):
    if facegrid is None:
        facegrid = []
    listdict = lambda: defaultdict(list)
    cols_w = defaultdict(listdict)
    cols_h = defaultdict(listdict)
    for index, (f, pos, row, col, _, _) in enumerate(facegrid):
        f.node = node
        fw, fh = f._size()
        fw += f.margin_right + f.margin_left
        fh += f.margin_top + f.margin_bottom

        # correct dimensions in case face is rotated
        if f.rotation:
            if f.rotation == 90 or f.rotation == 270:
                fw, fh = fh, fw
            elif f.rotation == 180:
                pass
            else:
                x0 =  fw / 2.0
                y0 =  fh / 2.0
                theta = (f.rotation * math.pi) / 180
                trans = lambda x, y: (x0+(x-x0) * math.cos(theta) + (y-y0) * math.sin(theta),
                                      y0-(x-x0) * math.sin(theta) + (y-y0) * math.cos(theta))
                coords = (trans(0,0), trans(0,fh), trans(fw,0), trans(fw,fh))
                x_coords = [e[0] for e in coords]
                y_coords = [e[1] for e in coords]
                fw = max(x_coords) - min(x_coords)
                fh = max(y_coords) - min(y_coords)

        facegrid[index][4] = fw
        facegrid[index][5] = fh
        # Update overal grid data
        cols_w[pos][col].append(fw)
        cols_h[pos][col].append(fh)
    # Calculate total facegrid size
    face_pos_sizes = []
    for fpos in FACE_POS_INDEXES:
        total_w = sum([max(v) for v in cols_w[fpos].values()]) if fpos in cols_w else 0.0
        total_h = max([sum(v) for v in cols_h[fpos].values()]) if fpos in cols_h else 0.0
        face_pos_sizes.extend((total_w, total_h))
    return face_pos_sizes

def compute_aligned_region_width(tree_image):
    current_w = 0.0
    max_w = 0.0
    root_visited = False
    for nid in tree_image.cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0:
            root_visited = True
        dim = tree_image.img_data[abs(nid)]
        if postorder:
            current_w -= dim[_baw]
        else:
            if dim[_is_leaf]:
                max_w = max(current_w + dim[_baw], max_w)
            else:
                current_w += dim[_baw]
    return max_w

def adjust_branch_lengths_by_size(tree_image, stop=None):
    if stop is None:
        stop = 100
    n2leaves = {}
    root = tree_image.root_node
    for n in root.traverse("postorder"):
        if n.children:
            n2leaves[n] = sum([n2leaves[ch] for ch in n.children])
        else:
            n2leaves[n] = 1

        if n2leaves[n] >= stop*3:
            for ch in n.children: 
                tree_image.img_data[ch._id][_blen] = n.dist * 1000
        elif n2leaves[n] >= stop*2:
            for ch in n.children: 
                tree_image.img_data[ch._id][_blen] = n.dist * 500
        elif n2leaves[n] >= stop:
            for ch in n.children: 
                tree_image.img_data[ch._id][_blen] = n.dist * 250
        else:
            for ch in n.children: 
                tree_image.img_data[n._id][_blen] =  n.dist * 1.5


def adjust_branch_lengths_by_size2(tree_image, stop=4):
    n2level = {}
    root = tree_image.root_node
    for n in root.traverse("preorder"):
        if n.up:
            n2level[n] = n2level[n.up] + 1
        else:
            n2level[n] = 0

        if n2level[n] <= stop:
            tree_image.img_data[n._id][_blen] = n.dist * 1000
            print n2level[n], stop, n.dist
        else:
            tree_image.img_data[n._id][_blen] =  n.dist * 1.5


        
def adjust_branch_lengths_by_size3(tree_image, stop=20, sca=2):
    n2dist = {}
    
    root = tree_image.root_node
    leaf, maxd = root.get_farthest_leaf()
    distances = [n.dist for n in root.iter_descendants()]
    print maxd, min(distances), max(distances), '-----------------------'
    for n in root.traverse("preorder"):
    
        if n.up:
            fbranch = n.dist
            parent_branch = n2dist[n.up]
            n2dist[n] = parent_branch + fbranch
            if parent_branch >= sca:
                scale1 = 0
                scale2 = fbranch
            else:
                scale1 =  max(0.0,  fbranch - (sca - parent_branch))
                scale2 = fbranch - scale1
            blen = (scale1 * 1000) + (scale2 * 1)
            if len(n) > 500:
                print n2dist[n], scale1, scale2, blen, len(n)
            tree_image.img_data[n._id][_blen] = blen
        else:
            tree_image.img_data[n._id][_blen] = 20
            n2dist[n] = 0
