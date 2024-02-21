from __future__ import annotations

from typing import Any

from overrides import override
from Qt.QtCore import Qt, Signal
from Qt.QtWidgets import QWidget, QLineEdit, QTextBrowser, QPushButton
from Qt.QtGui import (
    QFocusEvent, QMouseEvent, QDragEnterEvent, QDragMoveEvent, QDropEvent, QValidator, QIntValidator, QDoubleValidator
)

from tp.common.qt import validators, dpi, contexts, consts, qtutils
from tp.common.qt.widgets import layouts, labels


def line_edit(
        text: str = '', read_only: bool = False, placeholder_text: str = '', tooltip: str = '',
        parent: QWidget | None = None) -> BaseLineEdit:
    """
    Creates a basic line edit widget.

    :param str text: default line edit text.
    :param bool read_only: whether line edit is read only.
    :param str placeholder_text: line edit placeholder text.
    :param str tooltip: line edit tooltip text.
    :param QWidget parent: parent widget.
    :return: newly created combo box.
    :rtype: BaseLineEdit
    """

    new_line_edit = BaseLineEdit(text=text, parent=parent)
    new_line_edit.setReadOnly(read_only)
    new_line_edit.setPlaceholderText(str(placeholder_text))
    if tooltip:
        new_line_edit.setToolTip(tooltip)

    return new_line_edit


def text_browser(parent=None):
    """
    Creates a text browser widget.

    :param QWidget parent: parent widget.
    :return: newly created text browser.
    :rtype: QTextBrowser
    """

    new_text_browser = QTextBrowser(parent=parent)

    return new_text_browser


class BaseLineEdit(QLineEdit):

    textModified = Signal(str)
    textChanged = Signal(str)
    mousePressed = Signal(QMouseEvent)
    mouseMoved = Signal(QMouseEvent)
    mouseReleased = Signal(QMouseEvent)

    def __init__(
            self, text: str = '', enable_menu: bool = False, placeholder: str = '', tooltip: str = '',
            edit_width: int | None = None, fixed_width: int | None = None, menu_vertical_offset: int = 20,
            parent: QWidget | None = None):
        super().__init__(parent)

        self._value: str | None = None
        self._text_changed_before: str | None = None
        self._enter_pressed: bool = False

        self._setup_validator()

        if edit_width:
            self.setFixedWidth(dpi.dpi_scale(edit_width))
        if fixed_width:
            self.setFixedWidth(dpi.dpi_scale(fixed_width))
        self.setPlaceholderText(str(placeholder))
        self.setToolTip(tooltip)

        self.set_value(text)

        self.textEdited.connect(self._on_text_edited)
        self.textModified.connect(self._on_text_modified)
        self.editingFinished.connect(self._on_editing_finished)
        super().textChanged.connect(self._on_text_changed)
        self.returnPressed.connect(self._on_return_pressed)

        self._before_finished = self.value()

    @override
    def focusInEvent(self, arg__1: QFocusEvent) -> None:
        self._before_finished = self.value()
        super().focusInEvent(arg__1)

    @override
    def mousePressEvent(self, arg__1: QMouseEvent) -> None:
        self.mousePressed.emit(arg__1)
        super().mousePressEvent(arg__1)

    @override
    def mouseMoveEvent(self, arg__1: QMouseEvent) -> None:
        self.mouseMoved.emit(arg__1)
        super().mouseMoveEvent(arg__1)

    @override
    def mouseReleaseEvent(self, arg__1: QMouseEvent) -> None:
        self.mouseReleased.emit(arg__1)
        super().mouseReleaseEvent(arg__1)

    def value(self) -> Any:
        """
        Returns line edit internal value.

        :return: line edit value.
        :rtype: Any
        """

        return self._value

    def set_value(self, value: Any, update_text: bool = True):
        """
        Updates value of the line edit.

        :param Any value: line edit value.
        :param bool update_text: whether to update UI text or only internal text value.
        """

        self._value = value

        if update_text:
            with contexts.block_signals(self):
                self.setText(str(value))

    def _setup_validator(self):
        """
        Internal function that setup line edit validator.
        It should be overriden by subclasses.
        """

        pass

    def _before_after_state(self) -> tuple[Any, Any]:
        """
        Internal function that returns the before and after state of the line edit.

        :return: before and after state.
        :rtype: tuple[Any, Any]
        """

        return self._before_finished, self.value()

    def _on_text_edited(self, value: str):
        """
        Internal callback function that is called each time text is edited by the user.
        Updates internal value without updating UI (UI is already updated).

        :param str value: new line edit text.
        """

        self.set_value(value, update_text=False)

    def _on_text_modified(self, value: str):
        """
        Internal callback function that is called each time text is modified by the user (on return or switching out of
        the text box).
        Updates internal value without updating UI (UI is already updated).

        :param str value: text modified value.
        """

        self.set_value(value, update_text=False)

    def _on_editing_finished(self):
        """
        Internal callback function that is called when text edit if finished.
        """

        before, after = self._before_after_state()
        if before != after and not self._enter_pressed:
            self._before_finished = after
            self.textModified.emit(after)

        self._enter_pressed = False

    def _on_text_changed(self, text: str):
        """
        Internal callback function that is called each time text is changed by the user.

        :param str text: new text.
        """

        self._text_changed_before = text

        if not self.hasFocus():
            self._before_finished = text

    def _on_return_pressed(self):
        """
        Internal callback function that is called when return is pressed by the user.
        """

        before, after = self._before_after_state()
        if before != after:
            self.textModified.emit(after)
            self._enter_pressed = True


class IntLineEdit(BaseLineEdit):
    def __init__(
            self, text: str = '', enable_menu: bool = False, placeholder: str = '', tooltip: str = '',
            edit_width: int | None = None, fixed_width: int | None = None, menu_vertical_offset: int = 20,
            parent: QWidget | None = None):
        super().__init__(
            text=text, enable_menu=enable_menu, placeholder=placeholder, tooltip=tooltip, edit_width=edit_width,
            fixed_width=fixed_width, menu_vertical_offset=menu_vertical_offset, parent=parent)

    @classmethod
    def convert_value(cls, value: Any) -> int:
        """Converts given value to a compatible integer line edit value.

        :param Any value: value to convert.
        :return: float line edit compatible value.
        :rtype: int
        """

        result = 0
        if value == '0.0' or value == '-':
            return result
        elif value != '':
            try:
                result = int(float(value))
            except ValueError:
                pass

        return result

    @override(check_signature=False)
    def value(self) -> int:
        return super().value() or 0

    @override(check_signature=False)
    def set_value(self, value: int, update_text: bool = True):
        self._value = self.convert_value(value)
        if update_text:
            self.blockSignals(True)
            self.setText(str(self.value()))
            self.blockSignals(False)

    @override
    def _setup_validator(self):
        self.setValidator(QIntValidator())

    @override(check_signature=False)
    def _on_text_modified(self, value: float):

        value = self.convert_value(value)
        self.blockSignals(True)
        self.setText(str(int(float(value))))
        self.clearFocus()
        self.blockSignals(False)


class FloatLineEdit(BaseLineEdit):
    def __init__(
            self, text: str = '', enable_menu: bool = False, placeholder: str = '', tooltip: str = '',
            edit_width: int | None = None, fixed_width: int | None = None, menu_vertical_offset: int = 20,
            rounding: int = 3, parent: QWidget | None = None):

        self._rounding = rounding

        super().__init__(
            text=text, enable_menu=enable_menu, placeholder=placeholder, tooltip=tooltip, edit_width=edit_width,
            fixed_width=fixed_width, menu_vertical_offset=menu_vertical_offset, parent=parent)

    @classmethod
    def convert_value(cls, value: Any) -> float:
        """Converts given value to a compatible float line edit value.

        :param Any value: value to convert.
        :return: float line edit compatible value.
        :rtype: float
        """

        result = 0.0
        if value == '.':
            return result
        elif value != '':
            try:
                result = float(value)
            except ValueError:
                pass

        return result

    @override
    def focusOutEvent(self, arg__1: QFocusEvent) -> None:
        self._on_text_modified(self.value())
        super().focusOutEvent(arg__1)

    @override
    def clearFocus(self) -> None:
        super().clearFocus()
        self.setText(str(round(self.value(), self._rounding)))

    @override(check_signature=False)
    def value(self) -> float:
        return super().value() or 0.0

    @override(check_signature=False)
    def set_value(self, value: float, update_text: bool = True):
        self._value = self.convert_value(value)
        if update_text:
            self.blockSignals(True)
            self.setText(str(round(self.value(), self._rounding)))
            self.blockSignals(False)

    @override
    def _setup_validator(self):
        self.setValidator(QDoubleValidator())

    @override(check_signature=False)
    def _on_text_modified(self, value: float):

        value = self.convert_value(value)
        self.blockSignals(True)
        self.setText(str(round(value, self._rounding)))
        self.clearFocus()
        self.blockSignals(False)

    @override
    def _before_after_state(self) -> tuple[Any, Any]:
        before_finished, value = super()._before_after_state()
        return float(before_finished), float(value)


class FolderLineEdit(BaseLineEdit):
    """
    Custom QLineEdit with drag and drop behaviour for files and folders
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)

        self.setDragEnabled(True)

    @override
    def dragEnterEvent(self, arg__1: QDragEnterEvent) -> None:
        data = arg__1.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            arg__1.acceptProposedAction()

    @override
    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        data = e.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            e.acceptProposedAction()

    @override
    def dropEvent(self, arg__1: QDropEvent) -> None:
        data = arg__1.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            self.setText(urls[0].toLocalFile())


class EditableLineEditOnClick(QLineEdit):
    """
    Custom QLineEdit that becomes editable on click or double click.
    """

    def __init__(
            self, text: str, single: bool = False, double: bool = True, pass_through_clicks: bool = True,
            upper: bool = False, parent: QWidget | None = None):
        super().__init__(text, parent=parent)

        self._upper = upper
        self._validator = validators.UpperCaseValidator()

        if upper:
            self.setValidator(self._validator)
            self.setText(text)

        self.setReadOnly(True)
        self._editing_style = self.styleSheet()
        self._default_style = 'QLineEdit {border: 0;}'
        self.setStyleSheet(self._default_style)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setProperty('clearFocus', True)

        if single:
            self.mousePressEveNT = self.edit_event
        else:
            if pass_through_clicks:
                self.mousePressEvent = self.mouse_click_pass_through
        if double:
            self.mouseDoubleClickEvent = self.edit_event
        else:
            if pass_through_clicks:
                self.mouseDoubleClickEvent = self.mouse_click_pass_through

        self.editingFinished.connect(self._on_editing_finished)

    @override
    def setText(self, arg__1: str) -> None:
        if self._upper:
            arg__1 = arg__1.upper()

        super().setText(arg__1)

    @override
    def focusOutEvent(self, arg__1: QFocusEvent) -> None:
        super().focusOutEvent(arg__1)
        self._edit_finished()

    @override
    def mousePressEvent(self, arg__1: QMouseEvent) -> None:
        arg__1.ignore()

    @override
    def mouseReleaseEvent(self, arg__1: QMouseEvent) -> None:
        arg__1.ignore()

    def edit_event(self, event: QMouseEvent):
        """
        Internal function that overrides mouse press/release event behaviour.

        :param QMouseEvent event: Qt mouse event.
        """

        self.setStyleSheet(self._editing_style)
        self.selectAll()
        self.setReadOnly(False)
        self.setFocus()
        event.accept()

    def mouse_click_pass_through(self, event: QMouseEvent):
        """
        Internal function that overrides mouse press/release event behaviour to pass through the click.

        :param QMouseEvent event: Qt mouse event.
        """

        event.ignore()

    def _edit_finished(self):
        """
        Internal function that exits from the edit mode.
        """

        self.setReadOnly(True)
        self.setStyleSheet(self._default_style)
        self.deselect()

    def _on_editing_finished(self):
        """
        Internal callback function that is called when line edit text is changed.
        """

        self._edit_finished()


class StringLineEditWidget(QWidget):
    """
    Base class that creates a label, a text box to edit and an optional button.
    """

    textChanged = Signal(str)
    textModified = Signal(str)
    editingFinished = Signal()
    returnPressed = Signal()
    mousePressed = Signal(QMouseEvent)
    mouseMoved = Signal(QMouseEvent)
    mouseReleased = Signal(QMouseEvent)
    buttonClicked = Signal()

    def __init__(
            self, label: str = '', text: str = '', placeholder_text: str = '', button_text: str | None = None,
            edit_width: int | None = None, tooltip: str = '', orientation: Qt.AlignmentFlag = Qt.Horizontal,
            label_ratio: int = 1, edit_ratio: int = 5, button_ratio: int = 1, enable_menu: bool = True,
            parent: QWidget | None = None):
        super().__init__(parent=parent)

        self._enable_menu = enable_menu
        self._label: str | None = None
        self._label: labels.BaseLabel | None = None
        self._button: QPushButton | None = None

        if orientation == Qt.Horizontal:
            self._layout = layouts.horizontal_layout(margins=(0, 0, 0, 0), spacing=consts.SPACING)
        else:
            self._layout = layouts.vertical_layout(margins=(0, 0, 0, 0), spacing=consts.SPACING)
        self.setLayout(self._layout)

        self._line_edit = self._setup_line_edit(text, placeholder_text, tooltip, edit_width, enable_menu, parent)

        if label:
            self._label = labels.BaseLabel(text=label, tooltip=tooltip, parent=parent)
            self._layout.addWidget(self._label, label_ratio)

        self._layout.addWidget(self._line_edit, edit_ratio)

        if button_text:
            self._button = QPushButton(button_text, parent=parent)
            self._layout.addWidget(self._button, button_ratio)

        self._setup_signals()

    @override
    def setDisabled(self, arg__1: bool) -> None:
        self._line_edit.setDisabled(arg__1)
        if self._label:
            self._label.setDisabled(arg__1)

    @override
    def setEnabled(self, arg__1: bool) -> None:
        self._line_edit.setEnabled(arg__1)
        if self._label:
            self._label.setEnabled(arg__1)

    @override(check_signature=False)
    def setFocus(self) -> None:
        self._line_edit.setFocus()

    @override
    def clearFocus(self) -> None:
        self._line_edit.clearFocus()

    @override
    def blockSignals(self, b: bool) -> bool:
        result = super().blockSignals(b)
        [child.blockSignals(b) for child in qtutils.iterate_children(self)]
        return result

    @override(check_signature=False)
    def update(self, *args, **kwargs) -> None:
        self._line_edit.update(*args, **kwargs)
        super().update(*args, **kwargs)

    def value(self) -> Any:
        """
        Returns line edit value.

        :return: line edit value.
        :rtype: Any
        """

        return self._line_edit.value()

    def set_value(self, value: Any):
        """
        Sets line edit value.

        :param Any value: line edit value.
        """

        self._line_edit.set_value(value)

    def set_label(self, label_text: str):
        """
        Sets label text.

        :param str label_text: label text.
        """

        if self._label is not None:
            self._label.setText(label_text)

    def set_label_fixed_width(self, width: int):
        """
        Sets fixed with of the label.

        :param int width: label fixed with.
        """

        self._label.setFixedWidth(dpi.dpi_scale(width))

    def text(self) -> str:
        """Returns line edit text.

        :return: line edit text.
        :rtype: str
        """

        return self._line_edit.text()

    def set_text(self, value: str):
        """
        Sets line edit text.

        :param str value: line edit text.
        """

        self._line_edit.setText(str(value))

    def set_text_fixed_width(self, width: int):
        """
        Sets fixed with of the line edit.

        :param int width: line edit fixed with.
        """

        self._line_edit.setFixedWidth(dpi.dpi_scale(width))

    def set_placeholder_text(self, placeholder_text: str):
        """
        Sets line edit placeholder text.

        :param str placeholder_text: line edit placeholder text.
        """

        self._line_edit.setPlaceholderText(placeholder_text)

    def select_all(self):
        """
        Selects all the text within line edit.
        """

        self._line_edit.selectAll()

    def set_validator(self, validator: QValidator):
        """
        Sets line edit validator.

        :param QValidator validator: line edit validator.
        """

        self._line_edit.setValidator(validator)

    def _setup_line_edit(
            self, text: str, placeholder: str, tooltip: str, edit_width: int | None, enable_menu: bool,
            parent: QWidget | None) -> BaseLineEdit:
        """
        Internal function that creates the line edit used to edit text.

        :param str text: initial line edit text.
        :param str placeholder: placeholder text.
        :param str tooltip: tooltip text.
        :param int edit_width: width of the line edit.
        :param bool enable_menu: whether line width menu should be enabled.
        :param QWidget or None parent: line edit parent widget.
        :return: line edit instance.
        :rtype: BaseLineEdit
        """

        return BaseLineEdit(
            text=text, placeholder=placeholder, tooltip=tooltip, edit_width=edit_width, enable_menu=enable_menu,
            parent=parent)

    def _setup_signals(self):
        """
        Internal function that connect widgets signals.
        """

        self._line_edit.textChanged.connect(self.textChanged.emit)
        self._line_edit.textModified.connect(self.textModified.emit)
        self._line_edit.editingFinished.connect(self.editingFinished.emit)
        self._line_edit.returnPressed.connect(self.returnPressed.emit)
        self._line_edit.mousePressed.connect(self.mousePressed.emit)
        self._line_edit.mouseMoved.connect(self.mouseMoved.emit)
        self._line_edit.mouseReleased.connect(self.mouseReleased.emit)

        if self._button is not None:
            self._button.clicked.connect(self.buttonClicked.emit)


class IntLineEditWidget(StringLineEditWidget):
    """Line edit that can display integer attributes.
    """

    def __init__(
            self, label: str = '', text: str = '', placeholder_text: str = '', button_text: str | None = None,
            edit_width: int | None = None, tooltip: str = '', orientation: Qt.AlignmentFlag = Qt.Horizontal,
            label_ratio: int = 1, edit_ratio: int = 5, button_ratio: int = 1, enable_menu: bool = True,
            parent: QWidget | None = None):
        super().__init__(
            label=label, text=text, placeholder_text=placeholder_text, button_text=button_text, edit_width=edit_width,
            tooltip=tooltip, orientation=orientation, label_ratio=label_ratio, edit_ratio=edit_ratio,
            button_ratio=button_ratio, enable_menu=enable_menu, parent=parent)

    @override
    def _setup_line_edit(
            self, text: str, placeholder: str, tooltip: str, edit_width: int | None, enable_menu: bool,
            parent: QWidget | None) -> BaseLineEdit:

        return IntLineEdit(
            text=text, placeholder=placeholder, tooltip=tooltip, edit_width=edit_width, enable_menu=enable_menu,
            parent=parent)

    def set_min_value(self, value: int):
        """
        Sets line edit minimum value.

        :param int value: minimum value.
        """

        validator: QIntValidator = self._line_edit.validator()
        validator.setBottom(value)

    def set_max_value(self, value: int):
        """
        Sets line edit maximum value.

        :param int value: maximum value.
        """

        validator: QIntValidator = self._line_edit.validator()
        validator.setTop(value)


class FloatLineEditWidget(StringLineEditWidget):
    """Line edit that can display float attributes.
    """

    def __init__(
            self, label: str = '', text: str = '', placeholder_text: str = '', button_text: str | None = None,
            edit_width: int | None = None, tooltip: str = '', orientation: Qt.AlignmentFlag = Qt.Horizontal,
            label_ratio: int = 1, edit_ratio: int = 5, button_ratio: int = 1, enable_menu: bool = True,
            rounding: int = 3, parent: QWidget | None = None):

        self._rounding = rounding

        super().__init__(
            label=label, text=text, placeholder_text=placeholder_text, button_text=button_text, edit_width=edit_width,
            tooltip=tooltip, orientation=orientation, label_ratio=label_ratio, edit_ratio=edit_ratio,
            button_ratio=button_ratio, enable_menu=enable_menu, parent=parent)

    @override
    def _setup_line_edit(
            self, text: str, placeholder: str, tooltip: str, edit_width: int | None, enable_menu: bool,
            parent: QWidget | None) -> BaseLineEdit:

        return FloatLineEdit(
            text=text, placeholder=placeholder, tooltip=tooltip, edit_width=edit_width, enable_menu=enable_menu,
            rounding=self._rounding, parent=parent)

    def set_min_value(self, value: float):
        """
        Sets line edit minimum value.

        :param float value: minimum value.
        """

        validator: QDoubleValidator = self._line_edit.validator()
        validator.setBottom(value)

    def set_max_value(self, value: float):
        """
        Sets line edit maximum value.

        :param float value: maximum value.
        """

        validator: QDoubleValidator = self._line_edit.validator()
        validator.setTop(value)
