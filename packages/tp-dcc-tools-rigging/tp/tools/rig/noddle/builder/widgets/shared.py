from __future__ import annotations

import enum

from overrides import override

from tp.common.qt import api as qt
from tp.common.resources import api as resources


class ScrollWidget(qt.QWidget):
    def __init__(self, border:int = 0, **kwargs):
        super().__init__(**kwargs)

        self._content = qt.QWidget(parent=self)
        self._scroll_area = qt.QScrollArea(parent=self)
        self._scroll_area.setWidget(self._content)
        self._scroll_area.setWidgetResizable(True)

        self._content_layout = qt.vertical_layout()
        self._content.setLayout(self._content_layout)

        main_layout = qt.vertical_layout(margins=(0, 0, 0, 0))
        self.setLayout(main_layout)
        main_layout.addWidget(self._scroll_area)

        if not border:
            self._scroll_area.setFrameShape(qt.QFrame.NoFrame)

    @property
    def content_layout(self) -> qt.QVBoxLayout:
        return self._content_layout

    @override
    def resizeEvent(self, event: qt.QResizeEvent) -> None:
        self._scroll_area.resizeEvent(event)

    def add_widget(self, widget: qt.QWidget):
        """
        Adds widget to scroll layout.

        :param qt.QWidget widget: widget to add.
        """

        self._content_layout.addWidget(widget)

    def add_layout(self, layout: qt.QLayout):
        """
        Adds layout to scroll layout.

        :param qt.QLayout layout: layout to add.
        """

        self._content_layout.addLayout(layout)


class PathWidget(qt.QWidget):

    class Mode(enum.IntEnum):

        EXISTING_DIR = 0
        EXISTING_FILE = 1
        SAVE_FILE = 2

    def __init__(
            self, mode: Mode = Mode.EXISTING_DIR, default_path: str = '', label_text: str = '', dialog_label: str = '',
            parent: qt.QWidget | None = None):
        super().__init__(parent=parent)

        self._mode = mode
        self._default_path = default_path
        self._label_text = label_text
        self._dialog_label = dialog_label

        self._setup_widgets()
        self._setup_layouts()
        self._setup_signals()

    @property
    def line_edit(self) -> qt.QLineEdit:
        return self._line_edit

    @property
    def browse_button(self) -> qt.QPushButton:
        return self._browse_button

    def add_widget(self, widget: qt.QWidget):
        """
        Adds widget to main layout.

        :param qt.QWidget widget: widget to add.
        """

        self._main_layout.addWidget(widget)

    def _setup_widgets(self):
        """
        Internal function that creates all UI widgets.
        """

        self._label = qt.label(self._label_text, parent=self)
        self._line_edit = qt.line_edit(self._default_path, parent=self)
        self._browse_button = qt.base_button(icon=resources.icon('folder'), parent=self)

    def _setup_layouts(self):
        """
        Internal function that creates all UI layouts and add all widgets to them.
        """

        self._main_layout = qt.horizontal_layout(margins=(0, 0, 0, 0))
        self.setLayout(self._main_layout)

        self._main_layout.addWidget(self._label)
        self._main_layout.addWidget(self._line_edit)
        self._main_layout.addWidget(self._browse_button)

    def _setup_signals(self):
        """
        Internal function that creates all signal connections.
        """

        self._browse_button.clicked.connect(self._on_browse_button_clicked)

    def _on_browse_button_clicked(self):
        """
        Internal callback function that is called each time Browse button is clicked by the user.
        """

        def _existing_dir():
            self._dialog_label = self._dialog_label or 'Set directory'
            path = qt.QFileDialog.getExistingDirectory(None, self._dialog_label, self._line_edit.text())
            if path:
                self._line_edit.setText(path)

        def _existing_file():
            self._dialog_label = self._dialog_label or 'Select existing file'
            path, _ = qt.QFileDialog.getOpenFileName(None, self._dialog_label, self._line_edit.text())
            if path:
                self._line_edit.setText(path)

        def _save_file():
            self._dialog_label = self._dialog_label or 'Select save file'
            path, _ = qt.QFileDialog.getSaveFileName(None, self._dialog_label, self._line_edit.text())
            if path:
                self._line_edit.setText(path)

        if self._mode == PathWidget.Mode.EXISTING_DIR:
            _existing_dir()
        elif self._mode == PathWidget.Mode.EXISTING_FILE:
            _existing_file()
        elif self._mode == PathWidget.Mode.SAVE_FILE:
            _save_file()
