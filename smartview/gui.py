
from . import drawer
from . import drawer_noqt
import json
import os

from . import layout
from .common import *
from .utils import timeit, debug

import time
from multiprocessing import Pool, Queue, Process
import numpy as np
import bottle

import signal
import math
from collections import defaultdict

from PyQt5 import QtCore
from PyQt5.QtGui import *

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtOpenGL import *

from OpenGL import GL

import random

import logging
logger = logging.getLogger("smartview")


_QApp = None
GUI_TIMEOUT = None
OPENGL = False  # experimental


def exit_gui(a, b):
    _QApp.exit(0)


def start_app():
    global _QApp

    if not _QApp:
        _QApp = QApplication(["ETE"])


def display(tree_image, win_name="ETE", donotshow=False, zoom_factor=1):
    """ Interactively shows a tree."""
    global _QApp

    if not _QApp:
        _QApp = QApplication([win_name])

    #mainapp = TiledGUI(tree_image, zoom_factor=zoom_factor)
    mainapp = TreeGUI(tree_image, zoom_factor=zoom_factor)
    if donotshow:
        return
    if win_name:
        mainapp.setObjectName(win_name)
    mainapp.show()

    # Restore Ctrl-C behavior
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if GUI_TIMEOUT is not None:
        signal.signal(signal.SIGALRM, exit_gui)
        signal.alarm(GUI_TIMEOUT)

    _QApp.exec_()


class Painter(object):
    def __init__(self):
        self.stack = []

    def drawRect(self, x, y, w, h, fgcolor, bgcolor):
        self.stack.append(["r", x, y, w, h])

    def drawLine(self, x1, y1, x2, y2, color):
        self.stack.append(["l", x1, y1, x2, y2, color])


def start_server(tree_image):
    app = bottle.Bottle()

    @app.error(405)
    def method_not_allowed(res):
        if bottle.request.method == 'OPTIONS':
            new_res = bottle.HTTPResponse()
            new_res.set_header('Access-Control-Allow-Origin', '*')
            return new_res
        res.headers['Allow'] += ', OPTIONS'
        return bottle.request.app.default_error_handler(res)

    @app.hook('after_request')
    def enable_cors():
        """
        You need to add some headers to each request.
        Don't use the wildcard '*' for Access-Control-Allow-Origin in production.
        """
        bottle.response.headers['Access-Control-Allow-Origin'] = '*'
        bottle.response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
        bottle.response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

    @app.get("/get_scene_region/<scene>/", method=['GET', 'OPTIONS'])
    def get_scene_region(scene):
        print('  --> scene:', scene)
        zoom, x, y, w, h = map(float, scene.split(','))
        target_tree_scene = QRectF(x, y, w, h)

        zoom = max(0.00001, zoom)

        t1 = time.time()
        bottle.response.content_type = 'application/json'
        ii = QImage(1000, 1000, QImage.Format_ARGB32_Premultiplied)
        ii.fill(QColor(Qt.white).rgb())
        pp = QPainter()
        pp.begin(ii)
        painter = Painter()

        terminal_nodes = drawer_noqt.draw_tree_scene_region(pp, painter, tree_image,
                                                            zoom, target_tree_scene)
        pp.end()
        # return json.dumps({"items": [["r", 10, 10, 200, 200]]})

        # TODO: call here drawer.py draw_aligned_panel_region() and send the
        # results to pixi.

        print("web return:", time.time() - t1,
              len(painter.stack), len(terminal_nodes))
        return json.dumps({"items": painter.stack})

    @app.get("/static/<filepath:path>")
    def webfile(filepath):
        import pathlib
        basepath = os.path.join(pathlib.Path().absolute(), 'pixigui')
        print(os.path.join(basepath, filepath))
        return bottle.static_file(filepath, root=basepath)

    bottle.run(app, address="localhost", port=8090, debug=True, reload=True)


class TreeCanvas(QOpenGLWidget):
    def __init__(self, tree_image, zoom_factor):
        super().__init__()
        self.tree_image = tree_image
        self.zoom_factor = zoom_factor
        self.matrix = QTransform()
        self.tree_click_pos = None
        self.meta_click_pos = None

        self.scene_start = QPoint(0, 0)
        self.meta_start = QPoint(0, 0)
        self.tree_panel_percent = 0.2
        self.tree_panel_endx = None
        self.adjust_panels()

        self.format = QGLFormat()
        self.format.setSamples(4)
        self.setMouseTracking(True)

    def initializeGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        print(": init-------------------------------------------------")

    def adjust_panels(self):
        r = self.geometry()
        self.tree_panel_endx = r.width() * self.tree_panel_percent
        #print("endx", self.tree_panel_endx)

    def keyPressEvent(self, e):
        print("Key press")
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        key = e.key()
        debug("key Release", key)
        super().keyReleaseEvent(e)

    def mouseReleaseEvent(self, e):
        release_pos = e.pos()
        if self.tree_click_pos is not None and self.tree_click_pos != release_pos:
            diff = self.tree_click_pos - release_pos
            self.scene_start -= diff
        elif self.meta_click_pos is not None and self.meta_click_pos != release_pos:
            diff = self.meta_click_pos - release_pos
            self.meta_start -= diff
            self.scene_start -= QPoint(0, diff.y())

        self.tree_click_pos = None
        self.meta_click_pos = None

        self.update()
        print("Release", e.pos())
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        self.meta_click_pos = None
        self.tree_click_pos = None
        if e.x() < self.tree_panel_endx:
            self.tree_click_pos = e.pos()
        else:
            self.meta_click_pos = e.pos()

        print("Press", e.pos())
        return super().mousePressEvent(e)

    def resizeEvent(self, e):
        print("resize")
        print(self.geometry())
        self.adjust_panels()
        return super().resizeEvent(e)

    def wheelEvent(self, e):
        print("wheel")
        mouse_pos = e.pos()
        if mouse_pos.x() > self.tree_panel_endx:
            # if zooming is initiated from the meta panel, assume the end x
            # position of the tree panel as anchoring point
            mouse_pos = QPoint(self.tree_panel_endx, mouse_pos.y())

        factor = (-e.angleDelta().y() / 360.0)
        if abs(factor) >= 1:
            factor = 0.0

        scale_factor = 1 - factor

        self.zoom(mouse_pos, scale_factor)
        self.update()

    def zoom(self, mouse_pos, scale_factor):
        print("mouse pos zoom", mouse_pos)
        self.zoom_factor *= scale_factor
        dis = (mouse_pos - self.scene_start) * (scale_factor - 1)
        self.scene_start -= dis

    def paintGL(self):
        print("Painting")
        pp = QPainter(self)
        pp.beginNativePainting()
        pp.setRenderHint(QPainter.Antialiasing)
        pp.setRenderHint(QPainter.TextAntialiasing)
        pp.setRenderHint(QPainter.SmoothPixmapTransform)
        r = self.geometry()

        tree_scene_width = (self.width() * self.tree_panel_percent)
        aligned_panel_startx = tree_scene_width
        height = self.height()

        if self.scene_start.x() >= 0:
            xstart = 0
            tree_scene_width -= self.scene_start.x()
        else:
            xstart = -1 * self.scene_start.x()

        if self.scene_start.y() >= 0:
            ystart = 0
            height -= self.scene_start.y()
        else:
            ystart = -1 * self.scene_start.y()

        tree_scene_rect = QRectF(xstart, ystart, tree_scene_width, height)

        print("tree scene rect:", tree_scene_rect)
        pp.setPen(QColor('green'))
        pp.drawLine(aligned_panel_startx, 0, aligned_panel_startx, height)
        pp.save()
        pp.translate(self.scene_start.x(), self.scene_start.y())
        terminal_nodes = drawer.draw_tree_scene_region(pp, self.tree_image,
                                                       self.zoom_factor, tree_scene_rect)
        pp.setPen(QColor('red'))
        pp.drawRect(xstart+1, ystart+1, tree_scene_width-2, height-2)
        pp.restore()

        pp.save()

        pp.translate(aligned_panel_startx, self.scene_start.y())
        meta_scene_width = (self.width() * (1-self.tree_panel_percent))
        if self.meta_start.x() >= 0:
            meta_scene_xstart = 0
            meta_scene_width -= self.meta_start.x()
        else:
            meta_scene_xstart = -1 * self.meta_start.x()

        meta_scene_rect = QRectF(
            meta_scene_xstart, ystart, meta_scene_width, height)
        drawer.draw_aligned_panel_region(
            pp, terminal_nodes, self.tree_image, self.zoom_factor, meta_scene_rect)
        pp.restore()
        pp.endNativePainting()


class TreeGUI(QMainWindow):
    def __init__(self, tree_image, zoom_factor=1, *args):
        self.tree_image = tree_image
        QMainWindow.__init__(self, *args)
        # self.showMaximized()
        self.setGeometry(0, 0, 600, 600)

        self.canvas = TreeCanvas(self.tree_image, 1.0)
        self.splitter = QSplitter()
        self.setCentralWidget(self.splitter)
        self.splitter.insertWidget(0, self.canvas)


class TiledGUI(QMainWindow):
    def __init__(self, tree_image, zoom_factor=1, *args):
        self.tree_image = tree_image
        QMainWindow.__init__(self, *args)
        # self.showMaximized()

        self.splitter = QSplitter()
        self.setCentralWidget(self.splitter)

        self.TILE_W = CONFIG["tilesize"]
        self.TILE_H = CONFIG["tilesize"]
        self.views = []

        self.current_view = self.create_view(zoom_factor=zoom_factor)
        self.view = self.views[self.current_view]
        self.splitter.insertWidget(0, self.view)
        # if tree_image.tree_style.mode == "c":
        #     cx, cy = [x/2.0 for x in [self.view.img_w, self.view.img_h]]
        # elif tree_image.tree_style.mode == "r":
        #     cx, cy = [0, 0]
        # self.view.centerOn(cx, cy)
        # self.view.update_tile_view()
        # self.view._fit_to_window()

    def create_view(self, zoom_factor):
        if zoom_factor is None:
            x_zoom_factor = self.width() / self.tree_image.width
            y_zoom_factor = self.height() / self.tree_image.height
            zoom_factor = round(min(x_zoom_factor, y_zoom_factor), 6)

        view = TiledTreeView(self.tree_image, self.TILE_W,
                             self.TILE_H, 1)

        # view.setViewport(QtOpenGL.QGLWidget())

        view.init()
        view.gui = self
        view.info_w = QLabel(parent=view)
        view.info_w.setGeometry(0, 0, 1024, 20)
        _font = QFont("Arial", 14)
        _font.setWeight(75)
        view.info_w.setFont(_font)
        view.info_w.setStyleSheet(
            "background-color: rgba(255, 255, 255, 150);")
        self.views.append(view)
        return len(self.views)-1

    def keyReleaseEvent(self, e):
        key = e.key()
        debug("captured in GUI", key)
        QMainWindow.keyReleaseEvent(self, e)


class TiledTreeView(QGraphicsView):
    """Fake Scene containing tiles corresponding to actual items at a
    given zoom size
    """

    def __init__(self, tree_image, tile_w, tile_h, zoom_factor=None):
        self.threads = {}
        self.zoom_factor = np.float64(zoom_factor)
        self.tree_image = tree_image
        self.tree_mode = tree_image.tree_style.mode
        self.tile_w = tile_w
        self.tile_h = tile_h
        self.current_mouse_pos = QPointF(0, 0)
        self._scene = QGraphicsScene()
        QGraphicsView.__init__(self, self._scene)
        print("INIT SCENE", self._scene.sceneRect())
        self._scene.setSceneRect(0, 0, tree_image.width, tree_image.height)
        # This flag prevents updating tiles every single time that a
        # resize event is emitted.
        self.NO_TILE_UPDATE = False

        self.setMouseTracking(True)
        # self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor("#EEEEEE")))

        self.highlighter = None
        self.selector = None

    def init(self):
        # self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        # print len(self._scene.items())
        list(map(lambda x: self._scene.removeItem(x), list(self._scene.items())))

        self.highlighter = QGraphicsPathItem()
        self.highlighter.setZValue(100)
        self.highlighter.setPen(QColor("red"))
        # self.highlighter.setBrush(QBrush(QColor("#dddddd")))
        self.highlighter.setOpacity(0.4)
        self._scene.addItem(self.highlighter)

        #self.selector = AreaSelectorItem()
        # self._scene.addItem(self.selector)
        # self.selector.setZValue(110)

        self.img_w = self.tree_image.width * self.zoom_factor
        self.img_h = self.tree_image.height * self.zoom_factor

        # def nonedict():
        #     return defaultdict(lambda: None)
        # self.tiles = defaultdict(nonedict)

        # Create and adjust the tiled scene rectangle
        #self.setSceneRect(0, 0, self.img_w, self.img_h)
        # self.adjust_sceneRect()

    def update_tile_view(self):
        # self.adjust_sceneRect()
        self.setFocus()
        self.widgets = []

        # Get the dimensions of current viewport
        vrect = self.visibleRegion().boundingRect()

        match = self.mapToScene(vrect)
        srect = match.boundingRect()
        print(self._scene.sceneRect())
        print(vrect)
        print(srect)
        self.info_w.setText("#Leaves:<span style='color:blue'>%s</span>  -  #Nodes:<span style='color:red'>%s</span>  -  Zoom:%0.10f  -  BScale:%0.2f  -  Scene Region:%0.1f,%0.1f,%0.1f,%0.1f" %
                            ('{:,}'.format(len(self.tree_image.cached_leaves)),
                             '{:,}'.format(
                                 len(self.tree_image.cached_preorder)),
                             self.zoom_factor,
                             self.tree_image.scale,
                             srect.x(), srect.y(), srect.width(), srect.height(),
                             ))
        self.info_w.repaint()

        tile_rect = [srect.x(), srect.y(), srect.width(), srect.height()]
        img = drawer.get_tile_img(
            self.tree_image, self.zoom_factor, self.tree_mode, tile_rect)

        pix = QPixmap(img.width(), img.height())
        print("Pixmap size::", pix.width(), pix.height())
        pix = pix.fromImage(img)
        tile_item = self._scene.addPixmap(pix)
        tile_item.setPos(srect.topLeft())
        self._scene.addRect(self._scene.sceneRect(), QColor("red"))
        print("SCENE Rect", self._scene.sceneRect())

    def calculate_tile(self, current_zoom, new_zoom):
        # absolute mouse_position on the visible rectangle
        viewport = self.viewport()
        mouse_pos = viewport.mapFromGlobal(QCursor.pos())

        # transform pos to current scene view
        scene_x = self.scene_rect.x()+mouse_pos.x()
        scene_y = self.scene_rect.y()+mouse_pos.x()

        scene_x /= current_zoom
        scene_y /= current_zoom

        new_scene_x = scene_x * new_zoom
        new_scene_y = scene_y * new_zoom

        vrect = viewport.rect()

        scene_mouse_pos = self.mapToScene(mouse_pos) / current_zoom_factor
        next_scene_mouse_pos = scene_mouse_pos * next_zoom_factor

        # Distance from mouse to screen center
        center_dist = QPointF(mouse_pos - vrect.center())

        new_center = next_scene_mouse_pos - center_dist
        return new_center

        # self.adjust_sceneRect()
        self.setFocus()
        self.widgets = []

        # Get the dimensions of the visible area
        vrect = self.visibleRegion().boundingRect()

        scene_size = w, h

        match = self.mapToScene(vrect)
        srect = match.boundingRect()
        print(self._scene.sceneRect())
        print(vrect)
        print(srect)
        self.info_w.setText("#Leaves:<span style='color:blue'>%s</span>  -  #Nodes:<span style='color:red'>%s</span>  -  Zoom:%0.10f  -  BScale:%0.2f  -  Scene Region:%0.1f,%0.1f,%0.1f,%0.1f" %
                            ('{:,}'.format(len(self.tree_image.cached_leaves)),
                             '{:,}'.format(
                                 len(self.tree_image.cached_preorder)),
                             self.zoom_factor,
                             self.tree_image.scale,
                             srect.x(), srect.y(), srect.width(), srect.height(),
                             ))
        self.info_w.repaint()

        tile_rect = [srect.x(), srect.y(), srect.width(), srect.height()]
        img = drawer.get_tile_img(
            self.tree_image, self.zoom_factor, self.tree_mode, tile_rect)

        pix = QPixmap(img.width(), img.height())
        print("Pixmap size::", pix.width(), pix.height())
        pix = pix.fromImage(img)
        tile_item = self._scene.addPixmap(pix)
        tile_item.setPos(srect.topLeft())
        self._scene.addRect(self._scene.sceneRect(), QColor("red"))
        print("SCENE Rect", self._scene.sceneRect())

    def resizeEvent(self, e):
        """ Update viewport size and reload tiles """
        QGraphicsView.resizeEvent(self, e)
        # self.show_fake_tiles()
        if not self.NO_TILE_UPDATE:
            self.update_tile_view()

    def keyPressEvent(self, e):
        if (e.modifiers() & Qt.ControlModifier):
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.NoDrag)

        QGraphicsView.keyPressEvent(self, e)

    def _mousefocuscenter(self, current_zoom_factor, next_zoom_factor):

        viewport = self.viewport()
        mouse_pos = viewport.mapFromGlobal(QCursor.pos())
        vrect = viewport.rect()

        scene_mouse_pos = self.mapToScene(mouse_pos) / current_zoom_factor
        next_scene_mouse_pos = scene_mouse_pos * next_zoom_factor

        # Distance from mouse to screen center
        center_dist = QPointF(mouse_pos - vrect.center())

        new_center = next_scene_mouse_pos - center_dist
        return new_center

    # @timeit
    def _get_node_under_mouse(self):
        viewport = self.viewport()
        mouse_pos = viewport.mapFromGlobal(QCursor.pos())
        scene_mouse_pos = self.mapToScene(mouse_pos)

        if self.tree_image.tree_style.mode == "c":
            collision_paths = self.tree_image.circ_collision_paths
            M = QTransform()
            M.scale(self.zoom_factor, self.zoom_factor)
            M.translate(self.tree_image.radius[-1], self.tree_image.radius[-1])
        elif self.tree_image.tree_style.mode == "r":
            collision_paths = self.tree_image.rect_collision_paths
            M = QTransform()
            M.scale(self.zoom_factor, self.zoom_factor)

        img_data = self.tree_image.img_data
        curr = 0
        end = len(collision_paths)
        iters = 0
        match = None

        while curr < end:
            if not collision_paths[curr][0]:
                curr += 1
                continue
            path = M.map(collision_paths[curr][0])
            fpath = M.map(collision_paths[curr][1])
            if path.contains(scene_mouse_pos):
                dim = self.tree_image.img_data[curr]
                angle = (dim[_aend] - dim[_astart])
                return curr, path, fpath

            if not img_data[curr][_is_leaf] and not fpath.contains(scene_mouse_pos):
                curr = int(img_data[curr][_max_leaf_idx] + 1)
            elif not img_data[curr][_is_leaf]:
                end = img_data[curr][_max_leaf_idx] + 1
                curr += 1
            else:
                curr += 1

        return None, None, None

    @timeit
    def _fit_to_window(self):
        self._zoom_area(0, 0, self.tree_image.width*self.zoom_factor,
                        self.tree_image.height*self.zoom_factor)

    def _zoom(self, factor):
        c = self._mousefocuscenter(self.zoom_factor, self.zoom_factor*factor)
        self.zoom_factor *= factor
        self.init()
        self.centerOn(c)
        self.update_tile_view()

    def _zoom_area(self, x, y, w, h):
        viewport = self.viewport()
        vrect = QRectF(viewport.rect())
        scene_area = QRectF(x, y, w, h)
        if w > h:
            factor = vrect.width() / scene_area.width()
        else:
            factor = vrect.height() / scene_area.height()
        orig_pos = scene_area.center()
        self.zoom_factor *= factor

        self.init()
        self.centerOn(orig_pos*factor)
        self.update_tile_view()

    def keyReleaseEvent(self, e):
        if not (e.modifiers() & Qt.ControlModifier):
            self.setDragMode(QGraphicsView.ScrollHandDrag)

        key = e.key()
        if key == Qt.Key_Left:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()+20)
            self.update_tile_view()
        elif key == Qt.Key_Right:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-20)
            self.update_tile_view()
        elif key == Qt.Key_Up:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()+20)
            self.update_tile_view()
        elif key == Qt.Key_Down:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-20)
            self.update_tile_view()
        # Z
        elif key == 90:
            self._zoom(2.0)
        # X
        elif key == 88:
            self._zoom(0.5)

        # P
        elif key == 80:
            self.scale(2, 2)
        # O
        elif key == 79:
            self.scale(0.5, 0.5)

        # W
        elif key == 87:
            self._fit_to_window()

        # 1
        elif key == 49:
            self.tree_image.adjust_branch_lengths(layout.real)
            self.tree_image.update_collision_paths()
            self.update_tile_view()
            self._fit_to_window()

        # 2
        elif key == 50:
            self.tree_image.adjust_branch_lengths(layout.by_size)
            self.tree_image.update_collision_paths()
            self.update_tile_view()
            self._fit_to_window()

        # 3
        elif key == 51:
            self.tree_image.adjust_branch_lengths(layout.by_size_new)
            self.tree_image.update_collision_paths()
            self.update_tile_view()
            self._fit_to_window()

        # L(abels)
        elif key == 76:
            self.tree_image.tree_style.show_labels ^= True
            self.tree_image.update_collision_paths()
            self.update_tile_view()
        logger.debug("PRESSED %s" % key)
        QGraphicsView.keyReleaseEvent(self, e)

    def mouseReleaseEvent(self, e):

        if (e.modifiers() & Qt.ControlModifier):
            mouse_pos = self.viewport().mapFromGlobal(QCursor.pos())
            curr_pos = self.mapToScene(mouse_pos)
            x = min(self.selector.startPoint.x(), curr_pos.x())
            y = min(self.selector.startPoint.y(), curr_pos.y())
            w = max(self.selector.startPoint.x(), curr_pos.x()) - x
            h = max(self.selector.startPoint.y(), curr_pos.y()) - y
            self.selector.setActive(False)
            if self.selector.startPoint == curr_pos:
                self.selector.setVisible(False)
            else:
                self._zoom_area(x, y, w, h)
        else:
            self.update_tile_view()
        QGraphicsView.mouseReleaseEvent(self, e)

    def mouseMoveEvent(self, e):
        if (e.modifiers() & Qt.ControlModifier):
            mouse_pos = self.viewport().mapFromGlobal(QCursor.pos())
            curr_pos = self.mapToScene(mouse_pos)
            if self.selector.isActive():
                x = min(self.selector.startPoint.x(), curr_pos.x())
                y = min(self.selector.startPoint.y(), curr_pos.y())
                w = max(self.selector.startPoint.x(), curr_pos.x()) - x
                h = max(self.selector.startPoint.y(), curr_pos.y()) - y
                self.selector.setRect(x, y, w, h)
        else:
            nid, path, fpath = self._get_node_under_mouse()
            if nid is not None:
                self.highlighter.setPath(fpath)
                self.highlighter.show()
                # print path.boundingRect().height()*self.zoom_factor
                # print fpath.boundingRect().height()*self.zoom_factor, fpath.boundingRect().height()
                # print "--"
            else:
                self.highlighter.hide()
        QGraphicsView.mouseMoveEvent(self, e)

    def mousePressEvent(self, e):
        if (e.modifiers() & Qt.ControlModifier):
            mouse_pos = self.viewport().mapFromGlobal(QCursor.pos())
            curr_pos = self.mapToScene(mouse_pos)

            x, y = curr_pos.x(), curr_pos.y()
            self.selector.setRect(x, y, 0, 0)
            self.selector.startPoint = QtCore.QPointF(x, y)
            self.selector.setActive(True)
            self.selector.setVisible(True)

        QGraphicsView.mousePressEvent(self, e)

    def mouseDoubleClickEvent(self, e):
        nid, path, fpath = self._get_node_under_mouse()
        if fpath:
            r = fpath.boundingRect()
            self._zoom_area(r.x(), r.y(), r.width(), r.height())

    def wheelEvent(self, e):
        factor = (-e.angleDelta().y() / 360.0)
        # print(e.pixelDelta())
        # print(e.angleDelta())

        if abs(factor) >= 1:
            factor = 0.0

        # if factor < 0:
        #     factor = 1.25
        # else:
        #     factor = 0.75

        # Ctrl+Shift
        if (e.modifiers() & Qt.ControlModifier) and (e.modifiers() & Qt.ShiftModifier):
            pass
        # Ctrl+Alt
        elif (e.modifiers() & Qt.ControlModifier) and (e.modifiers() & Qt.AltModifier):
            pass
        # Ctrl
        elif e.modifiers() & Qt.ControlModifier:
            #print("Control:", factor)
            self.adjust_apertures(factor)

        # Shift
        elif e.modifiers() & Qt.ShiftModifier:
            pass
        # Default
        else:
            scale_factor = 1 - factor
            self._zoom(scale_factor)

    def adjust_apertures(self, factor):
        nid, path, fpath = self._get_node_under_mouse()
        if nid is not None:
            center = self._mousefocuscenter(self.zoom_factor, self.zoom_factor)
            self.tree_image.set_leaf_aperture(nodeid=nid, factor=factor*-1)
            self.tree_image.update_apertures()
            # self.tree_image.update_matrix()
            self.init()
            self.centerOn(center)
            self.update_tile_view()

    # def adjust_sceneRect(self):
    #     viewport = self.viewport()
    #     vrect = viewport.rect()
    #     viewRect = self.mapToScene(vrect).boundingRect()
    #     w = max((viewRect.width(), self.img_w))
    #     h = max((viewRect.height(), self.img_h))
    #     self.setSceneRect(-w, -h, w*2, h*2)

    # @timeit
    # def update_tile_view_old(self):
    #     self.adjust_sceneRect()
    #     self.setFocus()
    #     self.widgets = []
    #     TILE_CACHE_COL = 0
    #     TILE_CACHE_ROW = 0

    #     ## Get visible scene region
    #     vrect = self.visibleRegion().boundingRect()
    #     match = self.mapToScene(vrect)
    #     srect = match.boundingRect()

    #     self.info_w.setText("Leaves:%07d  -  Zoom:%0.10f  -  Branch Scale:%0.2f  -  Scene Region:%0.1f,%0.1f,%0.1f,%0.1f"%\
    #                         (len(self.tree_image.cached_leaves),
    #                          self.zoom_factor,
    #                          self.tree_image.scale,
    #                          srect.x(), srect.y(), srect.width(), srect.height(),
    #                         ))
    #     self.info_w.repaint()

    #     # Calculate grid of tiles necessary to draw
    #     p1 = srect.topLeft()
    #     p2 = srect.bottomRight()
    #     col_start = int((p1.x()) / self.tile_w)
    #     row_start = int((p1.y()) / self.tile_h)
    #     col_end = int((p2.x()) / self.tile_w)
    #     row_end = int((p2.y()) / self.tile_h)

    #     # Add cache tiles to the visisble tile grid
    #     col_start = max((0, col_start - TILE_CACHE_COL))
    #     col_end = min((self.max_cols-1, col_end + TILE_CACHE_COL))
    #     row_start = max((0, row_start - TILE_CACHE_ROW))
    #     row_end = min((self.max_rows-1, row_end + TILE_CACHE_ROW))
    #     vtiles = 0
    #     for row in range(row_start, row_end + 1):
    #         for col in range(col_start, col_end + 1):
    #             coord = (row, col)
    #             if coord in self.visible_tiles:
    #                 continue

    #             _tile_w, _tile_h = self.tile_w, self.tile_h
    #             x = col * _tile_w
    #             y = row * _tile_h

    #             # Correct tile size to stop at img boundaries
    #             if x + _tile_w > self.img_w:
    #                 _tile_w = self.img_w - x
    #             if y + _tile_h > self.img_h:
    #                 _tile_h = self.img_h - y

    #             if not _tile_w or not _tile_h:
    #                 continue

    #             tile_rect = [x, y, _tile_w, _tile_h]

    #             if not self.tiles[row][col]:
    #                 img = drawer.get_tile_img(self.tree_image, self.zoom_factor, self.tree_mode, tile_rect)
    #                 pix = QPixmap(img.width(), img.height())
    #                 pix = pix.fromImage(img)
    #                 tile_item = self._scene.addPixmap(pix)
    #                 tile_item.setPos(x, y)

    #                 self.tiles[row][col] = tile_item

    #                 ## temp pixmap
    #                 #pixmap = QPixmap(_tile_w, _tile_h)
    #                 #pixmap.fill(QColor("#ddd"))
    #                 #item = self.scene().addPixmap(pixmap)
    #                 #item.setPos(x, y)
    #                 vtiles +=1
    #                 if CONFIG["debug"]:
    #                     border = self._scene.addRect(tile_item.boundingRect())
    #                     border.setPos(x, y)
    #                     pen = QPen(QColor("lightgrey"))
    #                     pen.setStyle(Qt.DashLine)
    #                     border.setPen(pen)

    # def update_tile_view2(self):
    #     self.setFocus()
    #     self.widgets = []
    #     TILE_CACHE_COL = 0
    #     TILE_CACHE_ROW = 0

    #     ## Get visible scene region
    #     vrect = self.visibleRegion().boundingRect()
    #     match = self.mapToScene(vrect)
    #     srect = match.boundingRect()

    #     self.info_w.setText("Zoom:%s Scale:%0.2f Region:%s,%s,%s,%s"%\
    #                         (self.zoom_factor, self.tree_image.scale,
    #                          srect.x(), srect.y(), srect.width(), srect.height(),
    #                         ))
    #     self.info_w.repaint()

    #     # Calculate grid of tiles necessary to draw
    #     p1 = srect.topLeft()
    #     p2 = srect.bottomRight()
    #     col_start = int((p1.x()) / self.tile_w)
    #     row_start = int((p1.y()) / self.tile_h)
    #     col_end = int((p2.x()) / self.tile_w)
    #     row_end = int((p2.y()) / self.tile_h)

    #     # Add cache tiles to the visisble tile grid
    #     col_start = max((0, col_start - TILE_CACHE_COL))
    #     col_end = min((self.max_cols-1, col_end + TILE_CACHE_COL))
    #     row_start = max((0, row_start - TILE_CACHE_ROW))
    #     row_end = min((self.max_rows-1, row_end + TILE_CACHE_ROW))

    #     tile_imgs = []
    #     for row in range(row_start, row_end + 1):
    #         for col in range(col_start, col_end + 1):
    #             coord = (row, col)
    #             if coord in self.visible_tiles:
    #                 continue

    #             _tile_w, _tile_h = self.tile_w, self.tile_h
    #             x = col * _tile_w
    #             y = row * _tile_h

    #             # Correct tile size to stop at img boundaries
    #             if x + _tile_w > self.img_w:
    #                 _tile_w = self.img_w - x
    #             if y + _tile_h > self.img_h:
    #                 _tile_h = self.img_h - y

    #             if not _tile_w or not _tile_h:
    #                 continue

    #             tile_rect = [x, y, _tile_w, _tile_h]

    #             if not self.tiles[row][col]:
    #                 img = TileImage(self.tree_image, self.zoom_factor, tile_rect, row, col)
    #                 tile_imgs.append(img)

    #     Qt.QtConcurrent.map(tile_imgs, TileImage.render_tile)
    #     for img in tile_imgs:
    #         pix = QPixmap(img.width(), img.height())
    #         pix = pix.fromImage(img)
    #         tile_item = self._scene.addPixmap(pix)
    #         tile_item.setPos(img.scene_rect.x(), img.scene_rect.y())
    #         self.tiles[img.row][img.col] = tile_item

    # def update_tile_view2(self):
    #     #self.adjust_sceneRect()
    #     #self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
    #     for t in self.threads.keys():
    #         t.exit()

    #     self.setFocus()
    #     self.widgets = []
    #     TILE_CACHE_COL = 0
    #     TILE_CACHE_ROW = 0

    #     ## Get visible scene region
    #     vrect = self.visibleRegion().boundingRect()
    #     match = self.mapToScene(vrect)
    #     srect = match.boundingRect()

    #     self.info_w.setText("Zoom:%s Scale:%0.2f Region:%s,%s,%s,%s"%\
    #                         (self.zoom_factor, self.tree_image.scale,
    #                          srect.x(), srect.y(), srect.width(), srect.height(),
    #                         ))
    #     self.info_w.repaint()

    #     # Calculate grid of tiles necessary to draw
    #     p1 = srect.topLeft()
    #     p2 = srect.bottomRight()
    #     col_start = int((p1.x()) / self.tile_w)
    #     row_start = int((p1.y()) / self.tile_h)
    #     col_end = int((p2.x()) / self.tile_w)
    #     row_end = int((p2.y()) / self.tile_h)

    #     # Add cache tiles to the visisble tile grid
    #     col_start = max((0, col_start - TILE_CACHE_COL))
    #     col_end = min((self.max_cols-1, col_end + TILE_CACHE_COL))
    #     row_start = max((0, row_start - TILE_CACHE_ROW))
    #     row_end = min((self.max_rows-1, row_end + TILE_CACHE_ROW))

    #     for row in range(row_start, row_end + 1):
    #         for col in range(col_start, col_end + 1):
    #             coord = (row, col)
    #             if coord in self.visible_tiles:
    #                 continue

    #             _tile_w, _tile_h = self.tile_w, self.tile_h
    #             x = col * _tile_w
    #             y = row * _tile_h

    #             # Correct tile size to stop at img boundaries
    #             if x + _tile_w > self.img_w:
    #                 _tile_w = self.img_w - x
    #             if y + _tile_h > self.img_h:
    #                 _tile_h = self.img_h - y

    #             if not _tile_w or not _tile_h:
    #                 continue

    #             tile_rect = [x, y, _tile_w, _tile_h]

    #             if not self.tiles[row][col]:
    #                 # pixmap = QPixmap(_tile_w, _tile_h)
    #                 # pixmap.fill(QColor("red"))
    #                 # item = self.scene().addPixmap(pixmap)
    #                 # item.setPos(x, y)
    #                 t = TileThread(self, tile_rect, row, col)
    #                 self.threads[t] = [x, y, row, col, self.zoom_factor]
    #                 QObject.connect(t, SIGNAL( "jobFinished( PyQt_PyObject )" ), self.addimg)
    #                 t.start()

    # def addimg(self, args):
    #     img, thread = args
    #     if thread in self.threads:
    #         x, y, row, col, zoom = self.threads[thread]
    #         if zoom == self.zoom_factor:
    #             pix = QPixmap(img.width(), img.height())
    #             pix = pix.fromImage(img)
    #             tile_item = self._scene.addPixmap(pix)
    #             tile_item.setPos(x, y)
    #             self.tiles[row][col] = tile_item

    #             if CONFIG["debug"]:
    #                 border = self._scene.addRect(tile_item.boundingRect())
    #                 border.setPos(x, y)
    #                 pen = QPen(QColor("lightgrey"))
    #                 pen.setStyle(Qt.DashLine)
    #                 border.setPen(pen)


def test(*args):
    print(("done", args))


# class TileThread(QThread):
#     def __init__(self, view, tile_rect, row, col):
#         QThread.__init__(self)
#         self.view = view
#         self.tile_rect = tile_rect
#         self.row = row
#         self.col = col

#     def run(self):
#         self.img = drawer.get_tile_img(
#             self.view.tree_image, self.view.zoom_factor, self.view.tree_mode, self.tile_rect)
#         self.emit(SIGNAL("jobFinished( PyQt_PyObject )"), [self.img, self])

#         #pix = QPixmap(img.width(), img.height())
#         #pix = pix.fromImage(img)
#         #tile_item = view._scene.addPixmap(pix)
#         #x, y, w, h = tile_rect
#         #tile_item.setPos(x, y)
#         #self.view.tiles[self.row][self.col] = tile_item
#         # if CONFIG["debug"]:
#         #    border = view._scene.addRect(tile_item.boundingRect())
#         #    border.setPos(x, y)
#         #    pen = QPen(QColor("lightgrey"))
#         #    pen.setStyle(Qt.DashLine)
#         #    border.setPen(pen)


# class TileImage(QImage):
#     def __init__(self, tree_image, zoom_factor, scene_rect, row, col):
#         self.tree_image = tree_image
#         self.zoom_factor = zoom_factor
#         self.scene_rect = QRectF(*scene_rect)

#         self.row = row
#         self.col = col
#         QImage.__init__(self, self.scene_rect.width(), self.scene_rect.height(),
#                         QImage.Format_ARGB32_Premultiplied)
#         self.fill(QColor(Qt.white).rgb())

#     def render_tile(self):
#         target_rect = QRectF(0, 0, self.scene_rect.width(),
#                              self.scene_rect.height())
#         pp = QPainter()
#         pp.begin(self)
#         pp.setRenderHint(QPainter.Antialiasing)
#         pp.setRenderHint(QPainter.TextAntialiasing)
#         pp.setRenderHint(QPainter.SmoothPixmapTransform)
#         # Prevent drawing outside target_rect boundaries
#         pp.setClipRect(target_rect, Qt.IntersectClip)
#         # Transform space of coordinates: I want source_rect.top_left() to be
#         # translated as 0,0
#         matrix = QTransform().translate(-self.scene_rect.left(), -self.scene_rect.top())
#         pp.setWorldTransform(matrix, True)

#         drawer.draw_region_circ(self.tree_image, pp,
#                                 self.zoom_factor, self.scene_rect)
#         pp.end()


# class AreaSelectorItem(QGraphicsRectItem):
#     def __init__(self, parent=None):
#         self.Color = QColor("blue")
#         self._active = False
#         QGraphicsRectItem.__init__(self, 0, 0, 0, 0)
#         if parent:
#             self.setParentItem(parent)

#     def paint(self, p, option, widget):
#         p.setPen(self.Color)
#         p.setBrush(QBrush(QtCore.Qt.NoBrush))
#         p.drawRect(self.rect().x(), self.rect().y(),
#                    self.rect().width(), self.rect().height())
#         return
#         # Draw info text
#         font = QFont("Arial", 13)
#         text = "%d selected." % len(self.get_selected_nodes())
#         textR = QFontMetrics(font).boundingRect(text)
#         if self.rect().width() > textR.width() and \
#                 self.rect().height() > textR.height()/2 and 0:  # OJO !!!!
#             p.setPen(QPen(self.Color))
#             p.setFont(QFont("Arial", 13))
#             p.drawText(self.rect().bottomLeft().x(),
#                        self.rect().bottomLeft().y(), text)
#         print("painted")

#     def setActive(self, state):
#         self._active = bool(state)

#     def isActive(self):
#         return self._active
