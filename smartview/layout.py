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
    #print 'SIZE', len(matrix[0]), MATRIX_FIELDS
    matrix = np.zeros((nnodes,MATRIX_FIELDS), dtype="float64")
    return matrix
    #return [[0.0]*MATRIX_FIELDS for n in xrange(nnodes)]

@timeit
def update_node_dimensions(img_data, cached_prepostorder, cached_preorder,
                           scale=1.0, force_topology=False):
    prev_id = 0
    root_visited = False
    for nid in cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0: root_visited = True
        if postorder:
            # leaves are never visited in postorder, so enything here is an internal node
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
        fw = f._width() + f.margin_right + f.margin_left
        fh = f._height() + f.margin_top + f.margin_bottom

        # correct dimenstions in case face is rotated
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
        if nid == 0: root_visited = True
        dim = tree_image.img_data[abs(nid)]
        if postorder:
            current_w -= dim[_baw]
        else:
            if dim[_is_leaf]:
                max_w = max(current_w + dim[_baw], max_w)
            else:
                current_w += dim[_baw]
    return max_w



