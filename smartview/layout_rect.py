from .common import *
from .utils import timeit

# TODO: cover scenario where internal nodes are higher than all children!
@timeit
def update_rect_positions(img_data, cached_prepostorder,
                            cached_preorder,
                            leaf_apertures):

    current_y = 0.0
    current_x = 0.0
    root_visited = False

    for nid in cached_prepostorder:
        postorder = nid < 0 or nid == 0 and root_visited
        if nid == 0:
            root_visited = True
        node = cached_preorder[abs(nid)]
        dim = img_data[node._id]

        # calculate node width, could this be cached so it is not recalculated
        # in post and pre order?
        # wtop = max(dim[_btw], dim[_blen]) + dim[_brw]
        # wbot = max(dim[_bbw], dim[_blen]) + dim[_brw]
        # node_width = max(wtop, wbot)
        node_width = dim[_blen]

        if postorder:
            if len(node.children) > 1:
                # If node has more than 1 children, set vertical center to the
                # middle of all their siblings
                ycen_0 = img_data[node.children[0]._id][_ycenter]
                ycen_1 = img_data[node.children[-1]._id][_ycenter]
                node_ycenter = ycen_0 + ((ycen_1 - ycen_0) / 2.0)
                node_ystart = img_data[node.children[0]._id][_ystart]
                node_yend = img_data[node.children[-1]._id][_yend]
            else:
                # Otherwise just set the same rotation as the single child
                node_ycenter = img_data[node.children[0]._id][_ycenter]
                node_ystart = img_data[node.children[0]._id][_ystart]
                node_yend = img_data[node.children[0]._id][_yend]

            dim[_ystart] = node_ystart
            dim[_yend] = node_yend
            dim[_ycenter] = node_ycenter
            dim[_xend] = current_x
            dim[_fnh] = node_yend - node_ystart
            for ch in node.children:
                dim[_fnw] = max(dim[_fnw], img_data[ch._id][_fnw])
                #dim[_fnh] += img_data[ch._id][_fnh]

            dim[_fnw] += node_width
            current_x -= node_width
        else:
            if dim[_is_leaf]:
                dim[_ystart] = current_y
                dim[_yend] = current_y + dim[_nht] + dim[_nhb] + dim[_bh]
                dim[_ycenter] = current_y + dim[_nht] + dim[_bh]/2.0

                current_y += dim[_nht] + dim[_nhb] + dim[_bh]
                # increase hz
                dim[_xend] = current_x + node_width
                dim[_fnw] = node_width  # full node width (node and its children)
                dim[_fnh] = dim[_yend] - dim[_ystart]  # full node height
            else:
                current_x += node_width



# @timeit
# def compute_rect_collision_paths(tree_image):
#     """ collision paths in the un-transformed scene"""
#     collision_paths = []
#     img_data = tree_image.img_data
#     for nid, dim in enumerate(img_data):
#         node = tree_image.cached_preorder[nid]
#         ystart = dim[_ystart]
#         yend = dim[_yend]
#         xend = dim[_xend]
#         xstart = img_data[dim[_parent]][_xend]
#         path = QtGui.QPainterPath()
#         fpath= QtGui.QPainterPath()
#         path.addRect(xstart, ystart, xend-xstart, yend-ystart)
#         fpath.addRect(xstart, ystart, dim[_fnw], dim[_fnh])
#         collision_paths.append([path, fpath])
#     return collision_paths

# def get_rect_collision_paths(dim, parentdim, zoom_factor):
#     ystart = dim[_ystart] * zoom_factor
#     yend = dim[_yend] * zoom_factor
#     xend = dim[_xend] * zoom_factor
#     xstart = parentdim[_xend] * zoom_factor
#     path = QtGui.QPainterPath()
#     fpath= QtGui.QPainterPath()
#     path.addRect(xstart, ystart, xend-xstart, yend-ystart)
#     fpath.addRect(xstart, ystart,
#                   dim[_fnw] * zoom_factor,
#                   dim[_fnh] * zoom_factor)
#     return path, fpath
