from __future__ import annotations

from collections import namedtuple

from overrides import override

from tp.core import log
from tp.dcc import scene, node, skin
from tp.common.qt import api as qt
from tp.common.resources import api as resources
from tp.libs.rig.utils.transferweights import closestpoint

logger = log.rigLogger


ClipboardItem = namedtuple('ClipboardItem', ('skin', 'influences', 'selection'))


class TransferSkinWeightsView(qt.FramelessWindow):

    WINDOW_SETTINGS_PATH = 'tp/tools/rig/transferskinweights'

    def __init__(self, parent: qt.QWidget | None = None):
        super().__init__(title='Transfer Skin Weights', parent=parent)

        self._scene = scene.Scene()
        self._clipboard: list[ClipboardItem] = []

        self._methods = [
            closestpoint.ClosestPoint
        ]

    @property
    def scene(self) -> scene.Scene:
        """
        Getter method that returns the scene context.

        :return: scene context.
        :rtype: scene.Scene
        """

        return self._scene

    @property
    def clipboard(self) -> list[ClipboardItem]:
        """
        Getther method that reutnrs the clipboard items.

        :return: list of clipboard items.
        :rtype: list[ClipboardItem]
        """

        return self._clipboard

    @override
    def setup_ui(self):
        super().setup_ui()

        main_layout = self.main_layout()

        self._main_splitter = qt.QSplitter(qt.Qt.Horizontal, parent=self)
        self._main_splitter.setHandleWidth(6)
        self._main_splitter.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)

        self._clipboard_widget = qt.widget(layout=qt.vertical_layout(spacing=2), parent=self)
        self._clipboard_title = qt.divider('Clipboard', alignment=qt.Qt.AlignCenter, parent=self)
        self._clipboard_table_widget = qt.QTableWidget(parent=self)
        self._clipboard_table_widget.setColumnCount(3)
        self._clipboard_table_widget.setHorizontalHeaderLabels(['Name', 'Points', ''])
        self._clipboard_table_widget.setStyleSheet("""QTableWidget::item { height: 24px; }""")
        self._clipboard_table_widget.setEditTriggers(qt.QTableWidget.NoEditTriggers)
        self._clipboard_table_widget.setAlternatingRowColors(True)
        self._clipboard_table_widget.setSelectionMode(qt.QTableWidget.SingleSelection)
        self._clipboard_table_widget.setSelectionBehavior(qt.QTableWidget.SelectRows)
        horizontal_header = self._clipboard_table_widget.horizontalHeader()
        horizontal_header.setHighlightSections(False)
        horizontal_header.setMinimumSectionSize(24)
        horizontal_header.setStretchLastSection(False)
        # horizontal_header.resizeSection(2, 24)
        # horizontal_header.resizeSection(1, 100)
        horizontal_header.setSectionResizeMode(0, qt.QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(1, qt.QHeaderView.Fixed)
        horizontal_header.setSectionResizeMode(2, qt.QHeaderView.Fixed)
        vertical_header = self._clipboard_table_widget.verticalHeader()
        vertical_header.setDefaultSectionSize(24)
        vertical_header.setMinimumSectionSize(24)
        vertical_header.setStretchLastSection(False)
        # vertical_header.setSectionResizeMode(qt.QHeaderView.Fixed)
        method_layout = qt.horizontal_layout(spacing=2)
        self._method_label = qt.label('Method: ', parent=self)
        self._method_combo = qt.combobox(
            items=['Closest Point', 'Inverse Distance', 'Point on Surface', 'Skin Wrap'], parent=self)
        self._method_combo.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Preferred)
        method_layout.addWidget(self._method_label)
        method_layout.addWidget(self._method_combo)
        self._clipboard_widget.layout().addWidget(self._clipboard_title)
        self._clipboard_widget.layout().addWidget(self._clipboard_table_widget)
        self._clipboard_widget.layout().addLayout(method_layout)

        self._influences_widget = qt.widget(layout=qt.vertical_layout(spacing=2), parent=self)
        self._influences_title = qt.divider('Influences', alignment=qt.Qt.AlignCenter, parent=self)
        self._influences_list_widget = qt.QListWidget(parent=self)
        self._influences_list_widget.setStyleSheet("""QListWidget::item { height: 24px; }""")
        self._influences_list_widget.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAlwaysOff)
        self._influences_list_widget.setEditTriggers(qt.QListWidget.NoEditTriggers)
        self._influences_list_widget.setAlternatingRowColors(True)
        self._influences_list_widget.setSelectionBehavior(qt.QListWidget.SelectRows)
        self._influences_list_widget.setViewMode(qt.QListWidget.ListMode)
        self._influences_list_widget.setUniformItemSizes(True)
        self._influences_list_widget.setItemAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter | qt.Qt.AlignCenter)
        self._create_skin_button = qt.base_button('Create Skin', parent=self)
        self._influences_widget.layout().addWidget(self._influences_title)
        self._influences_widget.layout().addWidget(self._influences_list_widget)
        self._influences_widget.layout().addWidget(self._create_skin_button)

        buttons_layout = qt.horizontal_layout(spacing=2)
        self._extract_weights_button = qt.base_button('Extract Weights', parent=self)
        self._transfer_weights_button = qt.base_button('Transfer Weights', parent=self)
        buttons_layout.addWidget(self._extract_weights_button)
        buttons_layout.addWidget(self._transfer_weights_button)

        main_layout.addWidget(self._main_splitter)
        main_layout.addWidget(qt.divider(parent=self))
        main_layout.addLayout(buttons_layout)

        self._main_splitter.addWidget(self._clipboard_widget)
        self._main_splitter.addWidget(self._influences_widget)

    @override
    def setup_signals(self):
        super().setup_signals()

        self._clipboard_table_widget.itemSelectionChanged.connect(
            self._on_clipboard_table_widget_item_selection_changed)
        self._extract_weights_button.clicked.connect(self._on_extract_button_clicked)
        self._create_skin_button.clicked.connect(self._on_create_skin_button_clicked)
        self._transfer_weights_button.clicked.connect(self._on_transfer_weights_button_clicked)

    def clipboard_count(self) -> int:
        """
        Returns the number of clipboard items.

        :return: clipboard items count.n
        :rtype: int
        """

        return len(self._clipboard)

    def current_clipboard_item(self) -> ClipboardItem | None:
        """
        Returns the current clipboard item.

        :return: current clipboard item.
        :rtype: ClipboardItem or None
        """

        row = self._current_row()
        clipboard_count = self.clipboard_count()
        if 0 <= row < clipboard_count:
            return self._clipboard[row]

        return None

    def current_method(self) -> int:
        """
        Returns the current remapping algorithm index to apply.

        :return: selected remapping algorithm index.
        """

        return self._method_combo.currentIndex()

    def refresh(self):
        """
        Resets the influence list widget with the current clipboard's item used influences.
        """

        clipboard_item = self.current_clipboard_item()
        self._influences_list_widget.clear()
        if clipboard_item is None:
            return

        if not clipboard_item.skin.is_valid():
            return

        for influence_name in clipboard_item.influences.values():
            item = self._create_list_widget_item(influence_name)
            self._influences_list_widget.addItem(item)

        self._influences_list_widget.setCurrentRow(0)

    def _create_table_widget_item(self, text: str) -> qt.QTableWidgetItem:
        """
        Internal function that creates a table widget item from the given text.

        :param str text: table widget item text.
        :return: newly created table widget item instance.
        :rtype: qt.QTableWidgetItem
        """

        item = qt.QTableWidgetItem(text)
        item.setTextAlignment(qt.Qt.AlignCenter)
        return item

    def _create_list_widget_item(self, text: str) -> qt.QListWidgetItem:
        """
        Internal function that creates a list widget item from the given text.

        :param str text: list widget item text.
        :return: newly created list widget item instance.
        :rtype: qt.QListWidgetItem
        """

        item = qt.QListWidgetItem(text)
        item.setTextAlignment(qt.Qt.AlignCenter)
        return item

    def _current_row(self) -> int:
        """
        Returns the current selected row index.

        :return: current selected row index.
        :rtype: int
        """

        return self._clipboard_table_widget.selectionModel().currentIndex().row()

    def _add_row(self, skin_fn: skin.Skin):
        """
        Internal function that creates a new row based on the given skinning context object.

        :param skin.Skin skin_fn: skin context instance.
        :raises TypeError: if given skin deformer is not valid!
        """

        if not skin_fn.is_valid():
            raise TypeError('_add_row() expects a valid skin deformer!')

        vertex_indices = skin_fn.selection()
        num_vertex_indices = len(vertex_indices)
        if num_vertex_indices == 0:
            vertex_indices = skin_fn.vertices()

        # Get used influence names.
        influences = skin_fn.influences()
        used_influence_ids = skin_fn.used_influence_ids(*vertex_indices)
        used_influences = {
            influence_id: influences[influence_id].absolute_name() for influence_id in used_influence_ids}

        # Define clipboard items.
        clipboard_item = ClipboardItem(skin=skin_fn, selection=vertex_indices, influences=used_influences)
        self._clipboard.append(clipboard_item)

        # Create items and parent them to cells.
        shape = node.Node(skin_fn.shape())
        item1 = self._create_table_widget_item(shape.name())
        item2 = self._create_table_widget_item(str(len(vertex_indices)))
        delete_button = qt.base_button(icon=resources.icon('delete'), parent=self)
        delete_button.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding)
        delete_button.clicked.connect(self._on_delete_button_clicked)
        row_index = self._clipboard_table_widget.rowCount()
        self._clipboard_table_widget.insertRow(row_index)
        self._clipboard_table_widget.setItem(row_index, 0, item1)
        self._clipboard_table_widget.setItem(row_index, 1, item2)
        self._clipboard_table_widget.setCellWidget(row_index, 2, delete_button)

        self._clipboard_table_widget.selectRow(row_index)

    def _select_row(self, row: int):
        """
        Internal function that selects the given row from the clipboard table widget.

        :param int row: table widget row index to select.
        """

        row_count = self._clipboard_table_widget.rowCount()
        if 0 <= row < row_count:
            self._clipboard_table_widget.selectRow(row)

    def _remove_row(self, row: int):
        """
        Internal function that removes the given row from the clipboard table widget.

        :param int row: table widget row index to delete.
        """

        self._clipboard_table_widget.clearSelection()
        self._clipboard_table_widget.removeRow(row)
        del self._clipboard[row]
        self._select_row(row - 1)

    def _on_clipboard_table_widget_item_selection_changed(self):
        """
        Internal callback function that is called each time clipboard item is selected.
        Handles the refresh of the influences list.
        """

        self.refresh()

    def _on_extract_button_clicked(self):
        """
        Internal callback function that is called when extract button is clicked by the user.
        Handles the extract of skin weights from the active selection.
        """

        selection = self._scene.active_selection()
        skin_fn = skin.Skin()
        for obj in selection:
            success = skin_fn.try_set_object(obj)
            if not success:
                continue
            self._add_row(skin_fn)

    def _on_delete_button_clicked(self):
        """
        Internal callback function that is called each time Delete button is clicked by the item.
        Handles the deletion of the associated table row.
        """

        sender = self.sender()
        remove_at = self._clipboard_table_widget.indexAt(sender.pos()).row()
        self._remove_row(remove_at)

    def _on_create_skin_button_clicked(self):
        """
        Internal callback function that is called when Create Skin button is clicked by the user.
        Handles the creation of the skin deformer from the current influences.
        """

        selection = self._scene.active_selection()
        selection_count = len(selection)
        if selection_count == 0:
            logger.warning('Invalid selection!')
            return

        clipboard_item = self.current_clipboard_item()
        if clipboard_item is None:
            logger.warning('Invalid clipboard selection!')
            return

        # Check if mesh is already skinned
        mesh = selection[0]
        skin_fn = skin.Skin()
        success = skin_fn.try_set_object(mesh)
        if success:
            logger.warning('Selected mesh already has a skin!')
            return

        # Create new skin and add influences
        skin_fn = skin.Skin.create(mesh)
        skin_fn.set_max_influences(clipboard_item.skin.max_influences())
        influences = list(clipboard_item.influences.values())
        skin_fn.add_influence(*influences)

        # Transfer weights to new skin
        instance = closestpoint.ClosestPoint(clipboard_item.skin, clipboard_item.selection)
        instance.transfer(skin_fn, skin_fn.vertices())

    def _on_transfer_weights_button_clicked(self):
        """
        Internal callback function that is called when Transfer Weights button is clicked by the user.
        Applies selected weights to the active selection.
        """

        selection = self._scene.active_selection()
        selection_count = len(selection)
        if selection_count != 1:
            logger.warning('Unable to apply weights to active selection!')
            return

        clipboard_item = self.current_clipboard_item()
        if clipboard_item is None:
            logger.warning('Invalid clipboard selection!')
            return

        mesh = selection[0]
        other_skin = skin.Skin()
        success = other_skin.try_set_object(mesh)
        if not success:
            return

        current_method = self.current_method()
        cls = self._methods[current_method]
        instance = cls(clipboard_item.skin, clipboard_item.selection)
        instance.transfer(other_skin, other_skin.selection() or other_skin.vertices())
