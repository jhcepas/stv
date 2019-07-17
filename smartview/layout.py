import math
from collections import defaultdict, deque
import bisect
import numpy as np

from .utils import timeit
from .common import *

def get_empty_matrix(nnodes):
    '''Returns an empty matrix prepared to allocated all data for a tree image of
    "nnodes"
    '''
    #matrix = np.zeros(nnodes, dtype="int8,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,int32,float64,float64,float64,float64,float64,float64,float64,float64")
    matrix = np.zeros((nnodes,MATRIX_FIELDS), dtype="float32")
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
            #if precompute_faces:
            #  face_pos_sizes = compute_face_dimensions(node, node._temp_faces)
            #  dim[_btw:_bah+1] = face_pos_sizes
            dim[_blen] = node.dist if not force_topology else 1.0
            dim[_bh] = max(node.img_style.hz_line_width, 1.0)
            dim[_parent] = node.up._id if nid > 0 else 0
            dim[_is_leaf] = 1 # assumes it is a leaf, fixed in postorder for internal nodes
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

def by_size2(tree_image, stop=None):
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
                tree_image.img_data[ch._id][_blen] = n.dist * 20
        elif n2leaves[n] >= stop:
            for ch in n.children:
                tree_image.img_data[ch._id][_blen] = n.dist * 10
        else:
            for ch in n.children:
                tree_image.img_data[n._id][_blen] =  n.dist * 3
@timeit
def by_size(tree_image, stop=None):
    if stop is None:
        stop = 100

    root = tree_image.root_node.copy('newick')
    distances = []
    nleaves = 0
    for count, n in enumerate(root.traverse('preorder')):
        distances.append(n.dist)
        if not n.children:
            nleaves += 1
        n._id = count

    
    median_dist = np.median(distances)
    min_dist = np.median(distances)
    scale = 10.0 / min_dist

    # minimum distance to allocate 3 pixels per terminal node
    angle = tree_image.tree_style.arc_span / float(nleaves)
    theta = math.radians(angle/2.0)
    
    min_sep = 3.0 / math.sin(theta)

    init_zoom_factor = min_sep / 1080
    print "INIT ZOOM FACTOR", init_zoom_factor


    # angle = tree_image.tree_style.arc_span / nleaves
    # theta = (angle * math.pi) / 180
    # min_sep = 3 / math.sin(theta)

    n2leaves = root.get_cached_content()
    while True:
        for nleaves, leaf in enumerate(root.get_leaves(is_leaf_fn=lambda x: len(n2leaves[x])<=stop)):
            dim = tree_image.img_data[n._id]

            # if dim[_fnh] > R180:
            #     node_height = 999999999
            # else:
            #     node_height = ((math.sin(dim[_fnh]/2.0) * dim[_fnw]) * 2)

            # scale = ((stop*3) / node_height)


            for ch in leaf.get_children():
                for n in ch.traverse():
                    tree_image.img_data[n._id][_blen] = n.dist * scale
                ch.detach()
        print "scale used:", scale
        print "leaves processed:", nleaves
        print "new size of tree:", len(root)
        print "----------------"
        scale = scale * 10
        n2leaves = root.get_cached_content()
        if len(n2leaves[root]) < stop:
            print 'break'
            break
    for nleaves, n in enumerate(root.traverse()):
        tree_image.img_data[n._id][_blen] = n.dist * scale
    print "scale used:", scale
    print "leaves processed:", nleaves
    print "new size of tree:", len(root)
    print "----------------"

@timeit
def by_size_new(tree_image, stop=None):
    opt_size = 200
    root = tree_image.root_node

    n2leaves = {}
    n2rootdist = {}
    n2farthest = {}
    n2scale = {}
    for post,  n in root.iter_prepostorder():
        if post:
            if n.children:
                n2leaves[n] = sum([n2leaves[ch] for ch in n.children])
                n2farthest[n] = n.dist + max(n2farthest[ch] for ch in n.children)
        else:
            if not n.children:
                n2leaves[n] = 1
                n2farthest[n] = n.dist
                
            if n.up:
                n2rootdist[n] = n2rootdist[n.up] + n.dist
            else:
                n2rootdist[n] = 1


    seeds = [root]
    while seeds:
        seed = seeds.pop()
        if not seed.children:
            continue
        sorted_leaves = [(n2leaves[seed], seed)]
        while len(sorted_leaves) < opt_size:
            if sorted_leaves[-1][0] <= opt_size:
                break
            size, largest = sorted_leaves.pop()
            for ch in largest.children:
                    bisect.insort_left(sorted_leaves, (n2leaves[ch], ch))

        if sorted_leaves:
            leaves = [i[1] for i in sorted_leaves]
            dist, most_dist = sorted([(n2rootdist[lf], lf) for lf in leaves])[-1]

            aperture = tree_image.img_data[seed._id][_fnh]
            if aperture < R180:
                hyp = (n2leaves[seed] * 1) / math.sin(aperture/ 2.0)
                #hyp = (len(leaves) * 1) / math.sin(aperture/ 2.0)
            else:
                hyp = (n2leaves[seed] * 1)
                #hyp = (len(leaves) * 1)

            if seed is root:
                dist = max([n2rootdist[lf] for lf in leaves])
                clade_scale = hyp / dist
                n2scale[seed] = dist * clade_scale
            else:
                dist = max([n2rootdist[lf] for lf in leaves])

                diff = dist - n2rootdist[seed]

                current_rad = n2scale[seed]
                if current_rad >= hyp:
                    clade_scale = 500 / diff
                else:
                    clade_scale = (hyp-current_rad) / diff 


            print 'node_size:', n2leaves[seed], 'nodeRootdist:', n2rootdist[seed], 'scale', clade_scale
            for n in seed.traverse(is_leaf_fn=lambda x: x in leaves):
                for ch in n.children: 
                    tree_image.img_data[ch._id][_blen] = ch.dist * clade_scale
                    n2scale[ch] = n2scale[n] + (ch.dist * clade_scale)
                    
            seeds.extend([lf for lf in leaves if n2leaves[lf]> opt_size ])
        else:
            aperture = tree_image.img_data[seed._id][_fnh]
            if aperture < R180:
                hyp = (n2leaves[seed] * 3) / math.sin(aperture/ 2.0)
            else:
                hyp = (n2leaves[seed] * 3)


            dist = max([n2rootdist[lf] for lf in seed])
            diff = dist - n2rootdist[seed]

            current_rad = n2scale[seed]
            if current_rad >= hyp:
                clade_scale = 500 / diff
            else:
                clade_scale = (hyp-current_rad) / diff 

            for n in seed.traverse():
                for ch in n.children:
                    tree_image.img_data[ch._id][_blen] = ch.dist * clade_scale

    for dim in tree_image.img_data:
         dim[_blen] *= 0.1

def by_level(tree_image, stop=None):
    if stop is None:
        stop = 4

    n2level = {}

    root = tree_image.root_node
    n2leaves = root.get_cached_content()
    for n in root.traverse("preorder"):
        if n.up:
            n2level[n] = n2level[n.up] + 1
        else:
            n2level[n] = 0

        if n2level[n] <= stop:
            tree_image.img_data[n._id][_blen] = n.dist * 1000
        else:
            tree_image.img_data[n._id][_blen] =  n.dist * 1.5

def by_scale(tree_image, stop=20, sca=10):
    n2dist = {}

    root = tree_image.root_node
    leaf, maxd = root.get_farthest_leaf()
    distances = [n.dist for n in root.iter_descendants()]

    scale_ranges = [(maxd/4, 100), (maxd/3, 16), (maxd/2, 16), (maxd**maxd, 1)]

    #print maxd, min(distances), max(distances), '-----------------------'
    for n in root.traverse("preorder"):
        if n.up:
            fbranch = n.dist
            parent_branch = n2dist[n.up]
            n2dist[n] = parent_branch + fbranch
            blen = 0
            current_pos = parent_branch
            for scamax, sca in scale_ranges:
                if current_pos <= scamax:
                    offset = min(scamax, current_pos + fbranch)
                    current_pos += offset
                    blen += offset * sca

            tree_image.img_data[n._id][_blen] = blen
        else:
            tree_image.img_data[n._id][_blen] = maxd/2
            n2dist[n] = 0

def by_islands(tree_image, stop=None):
    if stop is None:
        stop = 150

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
                tree_image.img_data[ch._id][_blen] = n.dist * 20
        elif n2leaves[n] >= stop:
            for ch in n.children:
                tree_image.img_data[ch._id][_blen] = n.dist * 10
        else:
            for ch in n.children:
                tree_image.img_data[n._id][_blen] =  n.dist * 3

def real(tree_image, stop=None):
    root = tree_image.root_node
    #distances = [n.dist for n in root.iter_descendants()]
    #scale = 10 / min(distances)

    for n in root.traverse("preorder"):
        tree_image.img_data[n._id][_blen] =  n.dist

default_adjust_branch=by_size_new
