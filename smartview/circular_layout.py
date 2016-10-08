import math
from utils import timeit

from common import *
from colors import *

def iter_prepostorder(prepostorder):
    root_visited = False 
    for nid in prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0: root_visited = True
        yield postorder, nid

def get_min_radius(rect_width, rect_height, parent_radius, radians):
    radius = math.hypot(parent_radius+rect_width, rect_height)        
    if radians < R90:
        # converts to radians
        adjacent = rect_height / math.tan(radians)
        radius = max(radius, math.hypot(adjacent+rect_width, rect_height))
    return radius

def get_node_end_radius(parent_radius, dim, scale):
    lw = dim[_bh]/2.0
    htop = max(dim[_bth]+lw, dim[_brh]/2.0)
    hbot = max(dim[_bbh]+lw, dim[_brh]/2.0)
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

def get_optimal_circular_scale_GOOD(tree_image, optimization_level="med", root_opening_factor=0.0):
    """ Returns the minimum branch scale necessary to display all faces avoiding extra (dashed) branche lines
    """
    imgdata = tree_image.img_data
    n2minradius = {}
    n2sumdist = {}
    n2sumwidth = {}

    rad_start = len(tree_image.cached_leaves)/(2*math.pi)
    scaled_nodes = []

    levelnodes = [tree_image.root_node]
    nextlevelnodes = []
    level_counter = 0
    cdist = {}
    while levelnodes:
        if len(scaled_nodes) < 2**10:
            scaled_nodes.extend(levelnodes)
            for n in levelnodes:
                cdist[n] = cdist[n.up] if n.up else 0
                cdist[n] += n.dist
        else:
            break

        for n in levelnodes:
            nextlevelnodes.extend(n.children)
        levelnodes = nextlevelnodes
        nextlevelnodes = []
        level_counter += 1

    root_scale = rad_start / max(cdist.values())
    for n in scaled_nodes:
        imgdata[n._id][_blen] *= root_scale

    print "ROOT OPEN ----------------------", rad_start, "root_opening"


    # Calculate min node radius at scale 1
    for nid, dim in enumerate(imgdata):
        parent_radius = n2minradius[dim[_parent]] if nid > 0 else 0

        radius, node_width, node_height_top, node_height_bot = get_node_end_radius(parent_radius, dim, scale=None)

        n2minradius[nid] = radius
        # versed sine: the little extra line needed to complete the
        # radius.
        #vs = radius - (parent_radius + xoffset + node_width)


        n2sumwidth[nid] = n2sumwidth.get(dim[_parent], 0) + node_width
        n2sumdist[nid] = n2sumdist.get(dim[_parent], 0) + dim[_blen]

    most_distant = max(n2sumdist.values())
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

    # if not img.allow_face_overlap:
    #     aligned_h = [(n2i[node].heights[5], node) for node in visited_nodes]
    #     aligned_h.sort(reverse=True, key=lambda x: x[0])
    #     maxh, maxh_node = aligned_h[0]
    #     angle = n2i[maxh_node].angle_span
    #     rad, off = get_min_radius(1, maxh, angle, 0.0001)
    #     min_alg_scale = None
    #     for node in visited_nodes:
    #         if n2i[node].heights[5]:
    #             new_scale = (rad - (n2sumwidth[node] + root_opening)) / n2sumdist[node]
    #             min_alg_scale = min(new_scale, min_alg_scale) if min_alg_scale is not None else new_scale
    #     if min_alg_scale is not None and min_alg_scale > best_scale:
    #         best_scale = min_alg_scale

    # if root_opening:
    #     n2i[root_node].nodeRegion.adjust(root_opening, 0, root_opening, 0)
    #     n2i[root_node].fullRegion.adjust(root_opening, 0, root_opening, 0)
    #     n2i[root_node].xoff = root_opening
    #     #n2i[root_node].widths[0] += root_opening

    return best_scale, rad_start, max_rad, most_distant

def transform_by_level(tree_image):
    imgdata = tree_image.img_data
    min_absolute_rad = (len(tree_image.cached_leaves))/(2*math.pi)
    _, max_levels =  tree_image.root_node.get_farthest_leaf(topology_only=True)

    levelnodes = [tree_image.root_node]
    prev_rad = 0.0
    level_counter = 0

    correct_levels = max_levels/2
    radinc = min_absolute_rad/correct_levels
    steps = []
    for stop in xrange(1, int(correct_levels)):
        steps.append([stop, radinc])
    print steps
    colors = random_color(num=len(steps))
    for stop, rad_start in steps:
        scaled_nodes = []
        nextlevelnodes = []

        cdist = {}
        while levelnodes:
            if level_counter <= stop:
                scaled_nodes.extend(levelnodes)
                for n in levelnodes:
                    cdist[n] = cdist.get(n, 0.0) 
                    cdist[n] += imgdata[n._id][_blen]
            else:
                break

            for n in levelnodes:
                nextlevelnodes.extend(n.children)
            levelnodes = nextlevelnodes
            nextlevelnodes = []
            level_counter += 1

        prev_rad += rad_start
        root_scale = rad_start / max(cdist.values())
        print "SCALED", len(scaled_nodes), root_scale, rad_start, max(cdist.values())
        if root_scale > 1:
            linecolor = colors.pop()
            for n in scaled_nodes:
                n.img_style.hz_line_color = linecolor
                imgdata[n._id][_blen] *= root_scale

def adjust_branch_lengths(tree_image):
    img_data = tree_image.img_data
    min_absolute_rad = (len(tree_image.cached_leaves))/(2*math.pi)
    root_node = tree_image.root_node
    n2leaves = {}
    for n in root_node.traverse("postorder"):
        if n.children:
            n2leaves[n] = sum([n2leaves[ch] for ch in n.children])
        else:
            n2leaves[n] = 1
        n.support = n2leaves[n]

    starts = [root_node]
    breaks = [500]
    for stop in breaks: 
        new_starts = []
        for root in starts: 
            colors = random_color(num=len(starts))
            def is_leaf(_node):
                if n2leaves[_node] <= stop or len(_node.children) > 1000:
                    return True
                else:
                    return False

            root.convert_to_ultrametric(tree_length=10, is_leaf_fn=is_leaf, strategy="log", logbase=10)
            cdist = {}
            angle_span = img_data[root._id][_aend]-img_data[root._id][_astart]
            print len(root)
            for n in root.iter_descendants(is_leaf_fn=is_leaf):
                if is_leaf(n):
                    new_starts.append(n)
                cdist[n] = cdist.get(n, 0.0)
                cdist[n] += n.dist
            if cdist:
                expected_rad = ((n2leaves[root] / angle_span) / len(breaks))
                root_scale =  expected_rad / max(cdist.values())
                if root_scale > 1:
                    linecolor = colors.pop()
                    for n in cdist:
                        n.img_style.hz_line_color = linecolor
                        img_data[n._id][_blen] = n.dist * root_scale
                        n.dist = n2leaves[n]
                print "SCALED", len(cdist), "nodes, using scale", root_scale
        starts = new_starts


def adjust_branch_lengths2(tree_image):
    img_data = tree_image.img_data
    root = tree_image.root_node
    n2leaves = {}
    for n in root.traverse("postorder"):
        if n.children:
            n2leaves[n] = sum([n2leaves[ch] for ch in n.children])
        else:
            n2leaves[n] = 1
        n.support = n2leaves[n]

    stop = 100
    #colors = random_color(num=len(starts))

    def is_leaf(_node):
        if n2leaves[_node] <= stop or len(_node.children) > 50:
            return True
        else:
            return False
        
    def is_leaf(_node):
        aspan = img_data[_node._id][_astart] - img_data[_node._id][_aend]
        if aspan / n2leaves[_node] < min_angle:
            return True
        else:
            return False
        
    min_absolute_rad = (n2leaves[root]/(2*math.pi))
    scale, min_absolute_rad, most_d = get_optimal_circular_scale(tree_image)
    min_angle = math.acos(10/min_absolute_rad)
    
    print min_absolute_rad
    #root.convert_to_ultrametric(tree_length=min_absolute_rad, is_leaf_fn=is_leaf, strategy="log", logbase=10)
    # print root.get_farthest_leaf()
    
    # for node in root.iter_descendants(is_leaf_fn=is_leaf):
    #     print "Setting"
    #     node.img_style.hz_line_color = "blue"
    #     if is_leaf(node):
    #         node.img_style.hz_line_color = "red"
    #         optimize_scale(node, tree_image)
    for node in root.traverse():
        img_data[node._id][_blen] = node.dist

            
def optimize_scale(root, tree_image):
    """ Returns the minimum branch scale necessary to display all faces avoiding extra (dashed) branche lines
    """
    imgdata = tree_image.img_data

    n2minradius = {}
    n2sumdist = {}
    n2sumwidth = {}

    # Calculate min node radius at scale 1
    for node in root.traverse("preorder"):
        nid = node._id
        dim = imgdata[nid]        
        parent_radius = n2minradius.get(dim[_parent], root.dist)
        radius, node_width, node_height_top, node_height_bot = get_node_end_radius(parent_radius, dim, scale=None)
        n2minradius[nid] = radius
        n2sumwidth[nid] = n2sumwidth.get(dim[_parent], 0) + node_width
        n2sumdist[nid] = n2sumdist.get(dim[_parent], 0) + node.dist
            
    best_scale = None
    max_rad = 0.0    
    for node in root.traverse("preorder"):
        nid = node._id
        dim = imgdata[nid]        
        ndist = node.dist
        if best_scale is None:
            best_scale = (n2minradius[nid] - n2sumwidth[nid]) / ndist if ndist else 0.0
        else:
            # Whats the expected radius of this node?
            current_rad = (n2sumdist[nid] * best_scale) + (n2sumwidth[nid])

            # If still too small, it means we need to increase scale.
            if current_rad < n2minradius[nid]:
                best_scale = (n2minradius[nid] - (n2sumwidth[nid])) / n2sumdist[nid] if n2sumdist[nid] else 0.0
        max_rad = max(max_rad, (n2sumdist[nid] * best_scale) + (n2sumwidth[nid]))

    best_scale = max(100, best_scale)
    print "setting best scale", best_scale 
    for node in root.traverse("preorder"):
        node.dist *= best_scale
        node.img_style.hz_line_color = "blue"
        imgdata[node._id][_blen] = node.dist
        
    return best_scale, max_rad
    

def cannotbe(tree_image):
    n2leaves = {}
    stop = 500
    root = tree_image.root_node
    for n in root.traverse("postorder"):        
        if n.children:
            n2leaves[n] = sum([n2leaves[ch] for ch in n.children])
        else:
            n2leaves[n] = 1
        n.support = n2leaves[n]
        
    for n in root.traverse(is_leaf_fn=lambda x:n2leaves[x]<stop):
        n.dist = n2leaves[n]
        tree_image.img_data[n._id][_blen] = n.dist

        
@timeit
def get_optimal_circular_scale(tree_image, optimization_level="med", root_opening_factor=0.0):
    """ Returns the minimum branch scale necessary to display all faces avoiding extra (dashed) branche lines
    """
    cannotbe(tree_image)
    #adjust_branch_lengths(tree_image)
    
    imgdata = tree_image.img_data

    n2minradius = {}
    n2sumdist = {}
    n2sumwidth = {}

    # Calculate min node radius at scale 1
    for nid, dim in enumerate(imgdata):
        parent_radius = n2minradius[dim[_parent]] if nid > 0 else 0
        radius, node_width, node_height_top, node_height_bot = get_node_end_radius(parent_radius, dim, scale=None)        
        n2minradius[nid] = radius
        n2sumwidth[nid] = n2sumwidth.get(dim[_parent], 0) + node_width
        n2sumdist[nid] = n2sumdist.get(dim[_parent], 0) + dim[_blen]
            
    most_distant = max(n2sumdist.values())
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
            
    
    return best_scale,  max_rad, most_distant

def get_optimal_scale(root, tree_image):
    img_data = tree_image.img_data
    n2minradius = {}
    n2sumdist = {}
    n2sumwidth = {}

    # Calculate min node radius at scale 1
    for node in root.traverse("preorder"):
        nid = node._id
        dim = img_data[nid]
        parent_radius = n2minradius.get(dim[_parent], 0.0)
        radius, node_width, node_height_top, node_height_bot = get_node_end_radius(parent_radius, dim, scale=None)        
        n2minradius[nid] = radius
        n2sumwidth[nid] = n2sumwidth.get(dim[_parent], 0) + node_width
        n2sumdist[nid] = n2sumdist.get(dim[_parent], 0) + dim[_blen]
            
    most_distant = max(n2sumdist.values())
    if most_distant == 0:
        return 0.0
    
    best_scale = None
    max_rad = 0.0    
    for node in root.traverse("preorder"):
        nid = node._id
        dim = img_data[nid]
        ndist = dim[_blen]
        if best_scale is None:
            best_scale = (n2minradius[nid] - n2sumwidth[nid]) / ndist if ndist else 0.0
        else:
            # Whats the expected radius of this node?
            current_rad = (n2sumdist[nid] * best_scale) + (n2sumwidth[nid])

            # If still too small, it means we need to increase scale.
            if current_rad < n2minradius[nid]:
                best_scale = (n2minradius[nid] - (n2sumwidth[nid])) / n2sumdist[nid] if n2sumdist[nid] else 0.0

        max_rad = max(max_rad, (n2sumdist[nid] * best_scale) + (n2sumwidth[nid]))
                    
    return best_scale, max_rad

@timeit
def update_node_radius(imgdata, cached_prepostorder,
                       cached_preorder,
                       scale, root_opening):
    max_radius = 0.0
    root_visited = False
    max_node = None
    n2sumdist = {}
    n2sumwidth = {}
    for nid in cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0: root_visited = True
        
        node = cached_preorder[abs(nid)]
        dim = imgdata[node._id]
        if not postorder:
            parent_radius = imgdata[dim[_parent]][_rad] if node._id > 0 else root_opening
            lw = dim[_bh] / 2.0
            htop = max(dim[_bth]+lw, dim[_brh]/2.0)
            hbot = max(dim[_bbh]+lw, dim[_brh]/2.0)
            dim[_nht] = htop
            dim[_nhb] = hbot

            branch = dim[_blen] * scale
            wtop = max(branch, dim[_btw]) + dim[_brw]
            wbot = max(branch, dim[_bbw]) + dim[_brw]
            node_width = max(wtop, wbot)
            
            node_end_radius = parent_radius + node_width
            #node_end_radius = math.hypot(node_end_radius, 0.5)

            dim[_rad] = node_end_radius 
            if node_end_radius > max_radius:
                max_node = nid
            
            max_radius = max(max_radius, node_end_radius)            
            if dim[_is_leaf]:
                dim[_fnw] = node_end_radius
                angle = (dim[_aend] - dim[_astart])
                dim[_fnh] = dim[_fnw] * angle
        
        else:
            dim[_fnw] = max([imgdata[ch._id][_fnw] for ch in node.children])
            dim[_fnh] = dim[_fnw] * (dim[_aend] - dim[_astart])

    return max_radius

@timeit
def compute_circ_collision_paths(tree_image):
    from .drawer import get_arc_path
    """ collision paths in the un-transformed scene"""
    collistion_paths = []
    img_data = tree_image.img_data
    
    for nid, dim in enumerate(img_data):
        node = tree_image.cached_preorder[nid]
        arc_start = dim[_astart]
        arc_end = dim[_aend]
        radius = dim[_rad]        
        parent_radius = img_data[dim[_parent]][_rad]
        angles = [arc_start]
        if not dim[_is_leaf]:
            for ch in node.children:
                angles.append(tree_image.img_data[ch._id][_acenter])
        angles.append(arc_end)
        full_path = get_arc_path(parent_radius, tree_image.radius[-1], angles)
        if dim[_baw]:
            path = full_path
        else:
            path = get_arc_path(parent_radius, radius, angles)
            
        collistion_paths.append((path, full_path))

    return collistion_paths

@timeit
def update_node_angles(img_data, cached_prepostorder,
                       cached_preorder,
                       leaf_apertures):
    # angles in qt4 are clockwise. 3 o'clock is 0
    #     270
    #180      0
    #     90
    current_angle = 0.0
    current_leaf_index = 0
    root_visited = False
    
    for nid in cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0: root_visited = True
        node = cached_preorder[abs(nid)]
        dim = img_data[node._id]
        if postorder:
            if len(node.children) > 1:
                # If node has more than 1 children, set angle_center to the
                # middle of all their siblings
                acen_0 = img_data[node.children[0]._id][_acenter]
                acen_1 = img_data[node.children[-1]._id][_acenter]                
                node_acenter = acen_0 + ((acen_1 - acen_0) / 2.0)
                node_astart = img_data[node.children[0]._id][_astart]
                node_aend = img_data[node.children[-1]._id][_aend]
            else:
                # Otherwise just set the same rotation as the single child
                node_acenter = img_data[node.children[0]._id][_acenter]
                node_astart = img_data[node.children[0]._id][_astart]
                node_aend = img_data[node.children[0]._id][_aend]

            dim[_astart] = node_astart
            dim[_aend] = node_aend
            dim[_acenter] = node_acenter
        else:
            if dim[_is_leaf]:
                angle_step = leaf_apertures[current_leaf_index]
                if angle_step < 0:
                    angle_step = 0
                current_leaf_index += 1
                dim[_astart] = current_angle
                dim[_aend] = current_angle + angle_step
                dim[_acenter] = current_angle + (angle_step/2.0)
                current_angle += angle_step



                
