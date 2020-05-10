from collections import namedtuple
import re
from .face import Face

from .checkers import *
from .common import *

__all__  = ["TreeStyle"]


#NODE_STYLE_DEFAULT = dict([(cols[0], cols[1]) for cols in NODE_STYLE_CHECKER])
TREE_STYLE_CHECKER = {
    "mode": lambda x: x.lower() in set(["c", "r"]),
    }

# _faces and faces are registered to allow deepcopy to work on nodes
#VALID_NODE_STYLE_KEYS = set([i[0] for i in NODE_STYLE_DEFAULT]) | set(["_faces"])
                                   
                      
class TreeStyle(object):
    """ 
    .. versionadded:: 2.1

    .. currentmodule:: ete3

    Contains all the general image properties used to render a tree

    **-- About tree design --**

    :param None layout_fn: Layout function used to dynamically control
      the aspect of nodes. Valid values are: None or a pointer to a method,
      function, etc.
    
    **-- About tree shape --**
        
    :param "r" mode: Valid modes are 'c'(ircular)  or 'r'(ectangular).

    :param 0 orientation: If 0, tree is drawn from left-to-right. If
       1, tree is drawn from right-to-left. This property only makes
       sense when "r" mode is used.
    
    :param 0 rotation: Tree figure will be rotate X degrees (clock-wise
       rotation).
    
    :param 1 min_leaf_separation: Min separation, in pixels, between
      two adjacent branches

    :param 0 branch_vertical_margin: Leaf branch separation margin, in
      pixels. This will add a separation of X pixels between adjacent
      leaf branches. In practice, increasing this value work as
      increasing Y axis scale.

    :param 0 arc_start: When circular trees are drawn, this defines the
      starting angle (in degrees) from which leaves are distributed
      (clock-wise) around the total arc span (0 = 3 o'clock).

    :param 359 arc_span: Total arc used to draw circular trees (in
      degrees).

    :param 0 margin_left: Left tree image margin, in pixels.
    :param 0 margin_right: Right tree image margin, in pixels.
    :param 0 margin_top: Top tree image margin, in pixels.
    :param 0 margin_bottom: Bottom tree image margin, in pixels.

    **-- About Tree branches --**

    :param None scale: Scale used to draw branch lengths. If None, it will 
      be automatically calculated. 

    :param "mid" optimal_scale_level: Two levels of automatic branch
      scale detection are available: :attr:`"mid"` and
      :attr:`"full"`. In :attr:`full` mode, branch scale will me
      adjusted to fully avoid dotted lines in the tree image. In other
      words, scale will be increased until the extra space necessary
      to allocated all branch-top/bottom faces and branch-right faces
      (in circular mode) is covered by real branches. Note, however,
      that the optimal scale in trees with very unbalanced branch
      lengths might be huge. If :attr:`"mid"` mode is selected (as it is by default),
      optimal scale will only satisfy the space necessary to allocate
      branch-right faces in circular trees. Some dotted lines
      (artificial branch offsets) will still appear when
      branch-top/bottom faces are larger than branch length. Note that
      both options apply only when :attr:`scale` is set to None
      (automatic).

    :param 0.25 root_opening_factor: (from 0 to 1). It defines how much the center of
      a circular tree could be opened when adjusting optimal scale, referred
      to the total tree length. By default (0.25), a blank space up to 4
      times smaller than the tree width could be used to calculate the
      optimal tree scale. A 0 value would mean that root node should
      always be tightly adjusted to the center of the tree.
    
    :param True complete_branch_lines_when_necessary: True or False.
      Draws an extra line (dotted by default) to complete branch lengths when the space to cover is larger than the branch itself.
        
    :param 2 extra_branch_line_type:  0=solid, 1=dashed, 2=dotted
    
    :param "gray" extra_branch_line_color": RGB code or name in
      :data:`SVG_COLORS`
    
    :param False force_topology: Convert tree branches to a fixed length, thus allowing to
      observe the topology of tight nodes

    :param True draw_guiding_lines: Draw guidelines from leaf nodes
      to aligned faces
    
    :param 2 guiding_lines_type: 0=solid, 1=dashed, 2=dotted.
    
    :param "gray" guiding_lines_color: RGB code or name in :data:`SVG_COLORS` 

    **-- About node faces --**

    :param False allow_face_overlap: If True, node faces are not taken
      into account to scale circular tree images, just like many other
      visualization programs. Overlapping among branch elements (such
      as node labels) will be therefore ignored, and tree size
      will be a lot smaller. Note that in most cases, manual setting
      of tree scale will be also necessary.
    
    :param True draw_aligned_faces_as_table: Aligned faces will be
      drawn as a table, considering all columns in all node faces.

    :param True children_faces_on_top: When floating faces from
      different nodes overlap, children faces are drawn on top of
      parent faces. This can be reversed by setting this attribute
      to false.

    **-- Addons --**

    :param False show_border: Draw a border around the whole tree

    :param True show_scale: Include the scale legend in the tree
      image

    :param False show_leaf_name: Automatically adds a text Face to
      leaf nodes showing their names

    :param False show_branch_length: Automatically adds branch
      length information on top of branches

    :param False show_branch_support: Automatically adds branch
      support text in the bottom of tree branches

    **-- Tree surroundings --**
    
    The following options are actually Face containers, so graphical
    elements can be added just as it is done with nodes. In example,
    to add tree legend:
    
       ::

          TreeStyle.legend.add_face(CircleFace(10, "red"), column=0)
          TreeStyle.legend.add_face(TextFace("0.5 support"), column=1)
    
    :param aligned_header: a :class:`FaceContainer` aligned to the end
      of the tree and placed at the top part.

    :param aligned_foot: a :class:`FaceContainer` aligned to the end
      of the tree and placed at the bottom part.

    :param legend: a :class:`FaceContainer` with an arbitrary number of faces
      representing the legend of the figure. 
    :param 4 legend_position=4: TopLeft corner if 1, TopRight
      if 2, BottomLeft if 3, BottomRight if 4
    
    :param title: A Face container that can be used as tree title

    """

    def __repr__(self):
        return "TreeStyle (%s)" %(hex(self.__hash__()))
    
    def set_layout_fn(self, layout):
        self._layout_handler = []
        if type(layout) not in set([list, set, tuple, frozenset]):
            self._layout_handler.append(layout)
        else:
            for ly in layout:
                # Validates layout function
                if (type(ly) == types.FunctionType or type(ly) == types.MethodType or ly is None):
                    self._layout_handler.append(layout)
                else:
                    import layouts 
                    try:
                        self._layout_handler.append(getattr(layouts, ly))
                    except Exception:
                        raise ValueError ("Required layout is not a function pointer nor a valid layout name.")
 
    def get_layout_fn(self):
        return self._layout_handler

    layout_fn = property(get_layout_fn, set_layout_fn)

    def __init__(self):
        # :::::::::::::::::::::::::
        # TREE SHAPE AND SIZE
        # :::::::::::::::::::::::::
        
        # Valid modes are : "c" or "r"
        self.mode = "r"

        # Applies only for circular mode. It prevents aligned faces to
        # overlap each other by increasing the radius. 
        self.allow_face_overlap = False

        # Layout function used to dynamically control the aspect of
        # nodes
        self._layout_handler = []
        
        # 0= tree is drawn from left-to-right 1= tree is drawn from
        # right-to-left. This property only has sense when "r" mode
        # is used.
        self.orientation = 0 

        # Tree rotation in degrees (clock-wise rotation)
        self.rotation = 0 
       
        # Scale used to convert branch lengths to pixels. If 'None',
        # the scale will be automatically calculated.
        self.scale = None

        # How much the center of a circular tree can be opened,
        # referred to the total tree length.
        self.root_opening_factor = 0.25
            
        # mid, or full
        self.optimal_scale_level = "mid" 
        
        # Min separation, in pixels, between to adjacent branches
        self.min_leaf_separation = 1 

        # Leaf branch separation margin, in pixels. This will add a
        # separation of X pixels between adjacent leaf branches. In
        # practice this produces a Y-zoom in.
        self.branch_vertical_margin = 0

        # When circular trees are drawn, this defines the starting
        # angle (in degrees) from which leaves are distributed
        # (clock-wise) around the total arc. 0 = 3 o'clock
        self.arc_start = 0 

        # Total arc used to draw circular trees (in degrees)
        self.arc_span = 340

        # Margins around tree picture
        self.margin_left = 1
        self.margin_right = 1
        self.margin_top = 1
        self.margin_bottom = 1

        # :::::::::::::::::::::::::
        # TREE BRANCHES
        # :::::::::::::::::::::::::

        # When top-branch and bottom-branch faces are larger than
        # branch length, branch line can be completed. Also, when
        # circular trees are drawn, 
        self.complete_branch_lines_when_necessary = True
        self.extra_branch_line_type = 2 # 0 solid, 1 dashed, 2 dotted
        self.extra_branch_line_color = "gray" 

        # Convert tree branches to a fixed length, thus allowing to
        # observe the topology of tight nodes
        self.force_topology = False

        # Draw guidelines from leaf nodes to aligned faces
        self.draw_guiding_lines = True

        # Format and color for the guiding lines
        self.guiding_lines_type = 2 # 0 solid, 1 dashed, 2 dotted
        self.guiding_lines_color = "gray"

        # :::::::::::::::::::::::::
        # FACES
        # :::::::::::::::::::::::::

        # Aligned faces will be drawn as a table, considering all
        # columns in all node faces.
        self.draw_aligned_faces_as_table = True
        self.aligned_table_style = 0 # 0 = full grid (rows and
                                     # columns), 1 = semigrid ( rows
                                     # are merged )

        # When floating faces from different nodes overlap, children
        # faces are drawn on top of parent faces. This can be reversed
        # by setting this attribute to false.
        self.children_faces_on_top = True

        # :::::::::::::::::::::::::
        # Addons
        # :::::::::::::::::::::::::

        # Draw a border around the whole tree
        self.show_border = False

        # Draw the scale 
        self.show_scale = True

        # Initialize aligned face headers
        self.aligned_header = FaceContainer()
        self.aligned_foot = FaceContainer()

        self.show_leaf_name = True
        self.show_branch_length = False
        self.show_branch_support = False

        self.legend = FaceContainer()
        self.legend_position = 2

        self.show_labels = False

        self.title = FaceContainer()

        # PRIVATE values
        self._scale = None
        
        self.__closed__ = 1


    def __setattr__(self, attr, val):
        if hasattr(self, attr) or not getattr(self, "__closed__", 0):
            if TREE_STYLE_CHECKER.get(attr, lambda x: True)(val):
                object.__setattr__(self, attr, val)
            else:
                raise ValueError("[%s] wrong type" %attr)
        else:
            raise ValueError("[%s] option is not supported" %attr)


def add_face_to_node(face, node, column, row=None, position="branch-right"):
    """ 
    .. currentmodule:: ete3.treeview.faces

    Adds a Face to a given node. 

    :argument face: A :class:`Face` instance

    .. currentmodule:: ete3

    :argument node: a tree node instance (:class:`Tree`, :class:`PhyloTree`, etc.)
    :argument row: An integer number starting from 0
    :argument column: An integer number starting from 0
    :argument "branch-right" position: Possible values are
      "branch-right", "branch-top", "branch-bottom", "float", "float-behind" and "aligned".
    """ 
    try:
        poscode = FACEPOS2CODE[position]
    except KeyError:
        raise ValueError("face position not in %s" %list(FACEPOS2CODE.keys()))
    
    if isinstance(face, Face):
        # Faces container
        # [Face, pos, col, row, fw, fh]
        f = [face, poscode, row, column, 0, 0]
        if node._temp_faces is None:
            node._temp_faces = [f]
        else:
            node._temp_faces.append(f)
    else:
        raise ValueError("not a Face instance")
    return face
         
class FaceContainer(list):
    def add_face(self, face, row, column):        
        self.__append__([face, row, column, 0, 0])
