import math
# Aliases used to access the tree image matrix

# dimensions
(
# bool
    _is_leaf,

# unit32?
    _parent, _max_leaf_idx,

#?
    _btw, _bth, # branch-top face width and height
    _bbw, _bbh, # branch-bottom face width and height
    _brw, _brh, # branch-right face width and height
    # NOTE: we can't use branch-right for the moment. TODO: Figure out why.

    _bfw, _bfh, # branch-float face width and height
    _baw, _bah, # branch-aligned face width and height
    _nht, _nhb, # node height top and bottom

# needs float64
    _blen, _bh, # branch length and branch stroke height
    _fnw, _fnh, # total full-node width and height (incl. children)
) = list(range(19))

# position
(_rad, _acenter, _astart, _aend) = list(range(19, 23))  # for circular view
(_xend, _ycenter, _ystart, _yend) = list(range(19, 23)) # for rectangular view

MATRIX_FIELDS = 23

# Other

# FIXME: what do those codes mean? Why those and not others?
FACEPOS2CODE = {
    "branch-top": 0,
    "branch-bottom": 1,
    "branch-right": 2,
    "float": 3,
    "aligned": 4}
FACE_POS_INDEXES = sorted(FACEPOS2CODE.values())



CONFIG = {
    "debug": False,
    "timeit": False,
}

R90 = math.pi/2.0
R180 = math.pi
R270 = 3 * R90
R360 = 2 * math.pi

__all__ = ["_btw","_bth","_bbw","_bbh","_brw","_brh","_bfw","_bfh","_baw","_bah",
           "_blen","_bh","_nht","_nhb","_fnw","_fnh",
           "_rad", "_acenter","_astart","_aend",
           "_xend","_ycenter", "_ystart","_yend",
           "_parent", "_max_leaf_idx", "_is_leaf",
           "FACE_POS_INDEXES", "FACEPOS2CODE",
           "MATRIX_FIELDS","CONFIG", "R90", "R180", "R270",
           "R360", "printmem"]

def printmem(text=""):

    import gc
    gc.collect()

    import os
    print("MEMORY:", text)
    os.system("ps aux|grep layout|grep -v grep|awk '{print $6}'")

    #raw_input('stop'+text)


if __name__ == "__main__":
    for name in __all__:
        print("#define %s %s" %(name, globals()[name]))
