from common import *
import math
import time
from colors import *
import numpy as np
cimport numpy as np

# "ctypedef" assigns a corresponding compile-time type to DTYPE_t. For
# every type in the numpy module there's a corresponding compile-time
# type with a _t-suffix.
ctypedef np.float64_t DTYPE_t


cdef get_min_radius(double rect_width, double rect_height, double parent_radius, double radians):
    cdef double radius, adjacent, R90
    radius = math.hypot(parent_radius+rect_width, rect_height)        
    if radians < R90:
        # converts to radians
        adjacent = rect_height / math.tan(radians)
        radius = max(radius, math.hypot(adjacent+rect_width, rect_height))
    return radius

cdef get_node_end_radius(double parent_radius, dim, double scale):
    cdef htop, hbot, branch, wtop, wbot, aperture_top, aperture_bot, rad_top, rad_bot

    
    htop = max(dim[_bth] + (dim[_bh]/2.0), dim[_brh]/2.0, dim[_bh]/2.0)
    hbot = max(dim[_bbh] + (dim[_bh]/2.0), dim[_brh]/2.0, dim[_bh]/2.0)
    if scale:
        branch = dim[_blen] * scale
        wtop = max(dim[_btw], branch) + dim[_brw]
        wbot = max(dim[_bbw], branch) + dim[_brw]
    else:
        wtop = dim[_btw] + dim[_brw]
        wbot = dim[_bbw] + dim[_brw]

    aperture_top = dim[_acenter] - dim[_astart]
    aperture_bot = dim[_aend] - dim[_acenter]

    rad_top = get_min_radius(wtop, htop, parent_radius, aperture_top)
    rad_bot = get_min_radius(wbot, hbot, parent_radius, aperture_bot)

    radius = max(rad_top, rad_bot)
    return radius, max(wtop, wbot), htop, hbot


def adjust_branch_lengths(tree_image):
    t1 = time.time()
    img_data = tree_image.img_data
    #min_absolute_rad = (len(tree_image.cached_leaves))/(2*math.pi)
    root = tree_image.root_node
    n2leaves = root.get_cached_content(container_type=list)
    starts = [root]
    colors = random_color(num=len(starts))
    stop = 500
    def is_leaf(_node):
        if len(n2leaves[_node]) <= stop or len(_node.children) > stop:
            return True
        else:
            return False
        
    root.convert_to_ultrametric(tree_length=10, is_leaf_fn=is_leaf)
    cdist = {}
    angle_span = img_data[root._id][_aend]-img_data[root._id][_astart]
    for n in root.iter_descendants(is_leaf_fn=is_leaf):
        cdist[n] = cdist.get(n, 0.0) 
        cdist[n] += n.dist
    expected_rad = len(n2leaves[root]) / angle_span
    root_scale =  expected_rad / max(cdist.values())
    if root_scale > 1:
        linecolor = colors.pop()
        for n in cdist:
            n.img_style.hz_line_color = linecolor
            img_data[n._id][_blen] = n.dist * root_scale
            n.dist = len(n2leaves[n])
    print "SCALED", len(cdist), "nodes, using scale", root_scale
    print "TIME adjusting branches", time.time() - t1


def get_optimal_circular_scale(tree_image, optimization_level="med", root_opening_factor=0.0):
    cdef int nid
    
    t1 = time.time()

    adjust_branch_lengths(tree_image)

    imgdata = tree_image.img_data

    n2minradius = {}
    n2sumdist = {}
    n2sumwidth = {}

    # Calculate min node radius at scale 1
    most_distant = 0
    for nid, dim in enumerate(imgdata):
        parent_radius = n2minradius[dim[_parent]] if nid > 0 else 0
        radius, node_width, nht, nhb = get_node_end_radius(parent_radius, dim, scale=0.0)        
        n2minradius[nid] = radius
        n2sumwidth[nid] = n2sumwidth.get(dim[_parent], 0) + node_width
        n2sumdist[nid] = n2sumdist.get(dim[_parent], 0) + dim[_blen]
        most_distant = max(n2sumdist[nid], most_distant)
    print time.time()-t1
    if most_distant == 0:
        return 0.0

    root_opening = 0.0
    best_scale = None
    max_rad = 0.0    
    for nid, dim in enumerate(imgdata):
        ndist = dim[_blen]
        if best_scale is None:
            best_scale = (n2minradius[nid] - n2sumwidth[nid]) / ndist if ndist else 0.0
        else:
            # Whats the expected radius of this node?
            current_rad = (n2sumdist[nid] * best_scale) + (n2sumwidth[nid] + root_opening)

            # If still too small, it means we need to increase scale.
            if current_rad < n2minradius[nid]:
                # This is a simplification of the real equation needed to
                # calculate the best scale. Given that I'm not taking into
                # account the versed sine of each parent node, the equation is
                # simpler
                if root_opening_factor:
                    best_scale = (n2minradius[nid] - (n2sumwidth[nid])) / (n2sumdist[nid] + (most_distant * root_opening_factor))
                    root_opening = most_distant * best_scale * root_opening_factor
                else:
                    best_scale = (n2minradius[nid] - (n2sumwidth[nid]) + root_opening) / n2sumdist[nid] if n2sumdist[nid] else 0.0
                
            # If the width of branch top/bottom faces is not covered, we can
            # also increase the scale to adjust it. This may produce huge
            # scales, so let's keep it optional
            if optimization_level == "full":
                min_w = max(dim[_btw], dim[_bbw])
                if min_w > ndist * best_scale:
                    best_scale = min_w / ndist

        max_rad = max(max_rad, (n2sumdist[nid] * best_scale) + (n2sumwidth[nid] + root_opening))
                    
    # Adjust scale for aligned faces
    print "Max rad,",  max_rad, root_opening
    if 0: 
        for nid, dim in enumerate(imgdata):
            current_rad = (n2sumdist[nid] * best_scale) + (n2sumwidth[nid] + root_opening)
            needed_rad = get_min_radius(dim[_baw], dim[_bah]/2, current_rad, (dim[_aend]-dim[_astart])/2) 
            if needed_rad > current_rad:

                if root_opening_factor:
                    best_scale = (needed_rad - (n2sumwidth[nid])) / (n2sumdist[nid] + (most_distant * root_opening_factor))
                    root_opening = most_distant * best_scale * root_opening_factor
                else:
                    best_scale = (needed_rad - (n2sumwidth[nid]) + root_opening) / n2sumdist[nid]
            
    print "                                   TIME optimal best scale", time.time()-t1
    return best_scale,  max_rad, most_distant


def update_node_radius(imgdata, cached_prepostorder,
                       cached_preorder,
                       scale, root_opening):
    max_radius = 0.0
    root_visited = False 
    for nid in cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0: root_visited = True
        
        node = cached_preorder[abs(nid)]
        dim = imgdata[node._id]
        if not postorder:
            parent_radius = imgdata[dim[_parent]][_rad] if node._id > 0 else root_opening
            end_radius, node_width, node_height_top, node_height_bot = get_node_end_radius(parent_radius, dim, scale)
            dim[_nht] = node_height_top
            dim[_nhb] = node_height_bot
            dim[_rad] = end_radius
            max_radius = max(max_radius, end_radius)
            if dim[_is_leaf]:
                dim[_fnw] = end_radius
                # dim[_fnh] = dim[_nht] + dim[_nhb]
                angle =  (dim[_aend] - dim[_astart])
                dim[_fnh] = dim[_fnw] * angle
        
        else:
            dim[_fnw] = max([imgdata[ch._id][_fnw] for ch in node.children])
            dim[_fnh] = dim[_fnw] * (dim[_aend] - dim[_astart])
            
    return max_radius
