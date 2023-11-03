from __future__ import annotations

import os
import json
import timeit
import typing

from overrides import override

from tp.core import log
from tp.common.qt import api as qt
from tp.common.python import jsonio
from tp.tools.rig.noddle.builder.graph import registers
from tp.tools.rig.noddle.builder.graph.core import serializable, history, clipboard, node, edge
from tp.tools.rig.noddle.builder.graph.graphics import scene

if typing.TYPE_CHECKING:
    from tp.tools.rig.noddle.builder.graph.graphics.view import GraphicsView

logger = log.rigLogger


class Scene(serializable.Serializable):

    class Signals(qt.QObject):
        fileNameChanged = qt.Signal(str)
        modified = qt.Signal()
        itemSelected = qt.Signal()
        itemsDeselected = qt.Signal()
        itemDragEntered = qt.Signal(qt.QDragEnterEvent)
        itemDropped = qt.Signal(qt.QDropEvent)
        fileLoadFinished = qt.Signal()

    def __init__(self):
        super().__init__()

        self._signals = Scene.Signals()
        self._file_name: str = ''
        self._has_been_modified = False
        self._items_are_being_deleted = False
        self._scene_width = self._scene_height = 64000
        self._is_executing = False
        self._nodes: list[node.Node] = []
        self._edges: list[edge.Edge] = []
        self._edge_type = edge.Edge.Type.BEZIER
        self._graphics_scene: scene.GraphicsScene | None = None
        self._last_selected_items: list[qt.QGraphicsItem] = []

        self._setup_ui()

        self._history = history.SceneHistory(self)
        self._clipboard = clipboard.SceneClipboard(self)

        self._setup_signals()

    @classmethod
    def class_from_node_data(cls, node_data: dict) -> type:
        """
        Returns class based on node serialized data.

        :param dict node_data: node serialized data.
        :return: node class.
        :rtype: type
        """

        node_id = node_data.get('node_id')
        return registers.node_class_from_id(node_id) if node_id else node.Node

    @property
    def signals(self) -> Scene.Signals:
        return self._signals

    @property
    def graphics_scene(self) -> scene.GraphicsScene:
        return self._graphics_scene

    @property
    def view(self) -> GraphicsView:
        return self._graphics_scene.views()[0]

    @property
    def history(self) -> history.SceneHistory:
        return self._history

    @property
    def file_name(self) -> str:
        return self._file_name

    @file_name.setter
    def file_name(self, value: str):
        self._file_name = value
        self.signals.fileNameChanged.emit(self._file_name)

    @property
    def file_base_name(self) -> str:
        return os.path.basename(self.file_name) if self.file_name else ''

    @property
    def has_been_modified(self) -> bool:
        return self._has_been_modified

    @has_been_modified.setter
    def has_been_modified(self, flag: bool):
        self._has_been_modified = flag
        self.signals.modified.emit()

    @property
    def nodes(self) -> list[node.Node]:
        return self._nodes

    @property
    def edges(self) -> list[edge.Edge]:
        return self._edges

    @property
    def selected_items(self) -> list[qt.QGraphicsItem]:
        return self._graphics_scene.selectedItems()

    @property
    def selected_nodes(self) -> list[node.Node]:
        return [found_node for found_node in self._nodes if found_node.graphics_node.isSelected()]

    @property
    def selected_edges(self) -> list[edge.Edge]:
        return [found_edge for found_edge in self._edges if found_edge.graphics_edge.isSelected()]

    @property
    def edge_type(self) -> edge.Edge.Type:
        return self._edge_type

    @override
    def serialize(self) -> dict:
        nodes: list[dict] = []
        edges: list[dict] = []
        for n in self._nodes:
            nodes.append(n.serialize())
        for e in self._edges:
            if not e.start_socket or not e.end_socket:
                continue
            edges.append(e.serialize())

        return {
            'id': self.uid,
            'vars': [],
            'scene_width': self._scene_width,
            'scene_height': self._scene_height,
            'nodes': nodes,
            'edges': edges,
            'edge_type': self._edge_type.name
        }

    def item_at(self, position: qt.QPoint) -> qt.QGraphicsItem | None:
        """
        Returns item at given position.

        :param qt.QPoint position: position to get item at.
        :return: found position item at given position.
        :rtype: qt.QGraphicsItem or None
        """

        return self.view.itemAt(position)

    def set_history_init_point(self):
        """
        Sets history initial point.
        """

        logger.debug(f'Store initial scene history (Size: {self.history.size})')
        self._history.store_history(self._history.SCENE_INIT_DESCRIPTION)

    def add_node(self, node_to_add: node.Node):
        """
        Adds given node to the list of scene nodes.

        :param node.Node node_to_add: node instance to add to the scene.
        ..note:: this function does not add node view into the graphics view
        """

        self._nodes.append(node_to_add)

    def remove_node(self, node_to_remove: node.Node):
        """
        Removes given node from list of scene nodes.

        :param node.Node node_to_remove: node instance to remove from scene.
        ..note:: this function does not remove node view from the graphics view
        """

        self._nodes.remove(node_to_remove)

    def add_edge(self, edge_to_add: edge.Edge):
        """
        Adds given edge to the list of scene edges.

        :param edge.Edge edge_to_add: node instance to add to the scene.
        ..note:: this function does not add edge view into the graphics view
        """

        self._edges.append(edge_to_add)

    def remove_edge(self, edge_to_remove: edge.Edge):
        """
        Removes given edge from list of scene edges.

        :param edge.Edge edge_to_remove: node instance to remove from scene.
        ..note:: this function does not remove edge view from the graphics view
        """

        self._edges.remove(edge_to_remove)

    def spawn_node_from_data(self, node_id: int, json_data: dict, position: qt.QPointF) -> node.Node | None:
        try:
            new_node = registers.node_class_from_id(node_id)(self)
            if node_id == 100:      # function
                new_node.title = json_data.get('title')
                new_node.func_signature = json_data.get('func_signature', '')
            new_node.set_position(position.x(), position.y())
            self.history.store_history('Created Node {0}'.format(new_node.as_str(name_only=True)))
            return new_node
        except Exception:
            logger.exception('Failed to instance node', exc_info=True)

    def copy_selected(self):
        """
        Copies selected nodes into clipboard.
        """

        if not self.selected_nodes:
            logger.warning('No nodes selected to copy')
            return

        try:
            data = self._clipboard.serialize_selected(delete=False)
            str_data = json.dumps(data, indent=4)
            qt.QApplication.clipboard().setText(str_data)
        except Exception:
            logger.exception('Copy exception', exc_info=True)

    def cut_selected(self):
        """
        Cuts selected nodes into clipboard.
        """

        if not self.selected_nodes:
            logger.warning('No nodes selected to cut')
            return

        try:
            data = self._clipboard.serialize_selected(delete=True)
            str_data = json.dumps(data, indent=4)
            qt.QApplication.clipboard().setText(str_data)
            self._last_selected_items.clear()
        except Exception:
            logger.exception('Cut exception', exc_info=True)

    def paste_from_clipboard(self):
        """
        Paste nodes from clipboard
        """

        raw_data = qt.QApplication.clipboard().text()
        try:
            data = json.loads(raw_data)
        except ValueError:
            logger.error('Invalid JSON paste data')
            return

        if 'nodes' not in data.keys():
            logger.warning('Clipboard JSON does not contains any nodes')
            return

        self._clipboard.deserialize_data(data)

    def delete_selected(self, store_history: bool = True):
        """
        Deletes selected nodes from scene.

        :param bool store_history: whether to store operation within scene history stack.
        """

        self._items_are_being_deleted = True
        try:
            for node in self.selected_nodes:
                node.remove()
            for edge in self.selected_edges:
                edge.remove()
        except Exception:
            logger.exception('Failed to delete selected items')
        self._items_are_being_deleted = False

        if store_history:
            self.history.store_history('Item deleted', set_modified=True)

        self.signals.itemsDeselected.emit()

    def save_to_file(self, file_path: str):
        """
        Saves current scene into a file in disk.

        :param str file_path: path where scene should be stored.
        """

        try:
            jsonio.write_to_file(self.serialize(), file_path, sort_keys=False)
            logger.info(f'Saved build {file_path}')
            self.file_name = file_path
            self.has_been_modified = False
            self.signals.modified.emit()
        except Exception:
            logger.exception('Failed to save build', exc_info=True)

    def load_from_file(self, file_path: str):
        """
        Loads scene contents from file in disk.

        :param str file_path: absolute file path pointing to valid scene contents file.
        """

        try:
            self.clear()
            start_time = timeit.default_timer()
            data = jsonio.read_file(file_path, maintain_order=True)
            self.deserialize(data)
            logger.info("Rig build loaded in {0:.2f}s".format(timeit.default_timer() - start_time))
            self.history.clear()
            self._executor.reset_stepped_execution()
            self.file_name = file_path
            self.has_been_modified = False
            self.set_history_init_point()
            self.signals.fileLoadFinished.emit()
        except Exception:
            logger.exception('Failed to load scene build file', exc_info=True)

    def clear(self):
        """
        Removes all nodes from scene.
        """

        while self._nodes:
            self._nodes[0].remove(silent=True)
        self.has_been_modified = False

    def _setup_ui(self):
        """
        Internal function that setup scene widgets.
        """

        self._graphics_scene = scene.GraphicsScene(self)
        self._graphics_scene.set_scene_size(self._scene_width, self._scene_height)

    def _setup_signals(self):
        """
        Internal function that setup scene signals.
        """

        self._graphics_scene.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """
        Internal callback function that is called each time scene selection changes.
        """

        # Ignore selection update if rubberband dragging, item deletion is in progress
        if any([self.view.rubberband_dragging_rect, self._items_are_being_deleted]):
            return

        current_selection = self.graphics_scene.selectedItems()
        if current_selection == self._last_selected_items:
            return

        # No current selection and existing previous selection (To avoid resetting selection after cut operation)
        if not current_selection:
            self.history.store_history('Deselected everything', set_modified=False)
            self.signals.itemsDeselected.emit()
        else:
            self.history.store_history('Selection changed', set_modified=False)
            self.signals.itemSelected.emit()

        self._last_selected_items = current_selection
