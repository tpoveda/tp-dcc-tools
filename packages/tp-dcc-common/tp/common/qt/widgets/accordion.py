"""
Collapsible accordion widget similar to Maya Attribute Editor
"""

from __future__ import annotations

from typing import Type, Any

from overrides import override
from Qt.QtCore import Qt, Signal, QObject, QPoint, QRect, QMimeData, QEvent
from Qt.QtWidgets import QApplication, QWidget, QGroupBox, QScrollArea
from Qt.QtGui import (
    QCursor, QColor, QPixmap, QPalette, QIcon, QPen, QBrush, QPainter, QDrag, QPolygon, QPainterPath, QDragEnterEvent,
    QDragMoveEvent, QDropEvent, QMouseEvent, QPaintEvent
)

from tp.core import log, dcc
from tp.common.qt.widgets import layouts
from tp.preferences.interfaces import core

logger = log.tpLogger


class AccordionStyle:
    BOXED = 1
    ROUNDED = 2
    SQUARE = 3
    MAYA = 4


class AccordionDragDrop:
    NO_DRAG_DROP = 0
    INTERNAL_MOVE = 1


class AccordionItem(QGroupBox):

    trigger = Signal(bool)

    def __init__(self, accordion: AccordionWidget, title: str, widget: QWidget, icon: QIcon | None = None):
        super(AccordionItem, self).__init__(parent=accordion)

        self._accordion_widget = accordion
        self._widget = widget
        self._icon = icon
        self._rollout_style = AccordionStyle.ROUNDED if not dcc.is_maya() else AccordionStyle.MAYA
        self._drag_drop_mode = AccordionDragDrop.NO_DRAG_DROP
        self._collapsed = False
        self._collapsible = True
        self._clicked = False
        self._custom_data = {}
        self._theme_prefs = core.theme_preference_interface()

        layout = layouts.vertical_layout(spacing=0, margins=(6, 12, 6, 6))
        layout.addWidget(widget)

        self.setAcceptDrops(True)
        self.setLayout(layout)
        self.setTitle(title)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_show_menu)

    @property
    def accordion_widget(self) -> AccordionWidget:
        return self._accordion_widget

    @property
    def widget(self) -> QWidget:
        return self._widget

    @property
    def rollout_style(self) -> int:
        return self._rollout_style

    @rollout_style.setter
    def rollout_style(self, value: int):
        self._rollout_style = value

    @property
    def drag_drop_mode(self) -> int:
        return self._drag_drop_mode

    @drag_drop_mode.setter
    def drag_drop_mode(self, value: int):
        self._drag_drop_mode = value

    @property
    def collapsible(self) -> bool:
        return self._collapsible

    @collapsible.setter
    def collapsible(self, flag: bool):
        self._collapsible = flag

    @override
    def enterEvent(self, event: QEvent) -> None:
        self.accordion_widget.leaveEvent(event)
        event.accept()

    @override
    def leaveEvent(self, event: QEvent) -> None:
        self.accordion_widget.enterEvent(event)
        event.accept()

    @override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self._drag_drop_mode:
            return
        source = event.source()
        if source != self and source.parent() == self.parent() and isinstance(source, AccordionItem):
            event.acceptProposedAction()

    @override
    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if not self._drag_drop_mode:
            return
        source = event.source()
        if source != self and source.parent() == self.parent() and isinstance(source, AccordionItem):
            event.acceptProposedAction()

    @override
    def dropEvent(self, event: QDropEvent) -> None:
        widget = event.source()
        layout = self.parent().layout()
        layout.insertWidget(layout.indexOf(self), widget)
        self._accordion_widget.emit_items_reordered()

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self.drag_drop_rect().contains(event.pos()):
            pixmap = QPixmap.grabWidget(self, self.rect())
            mime_data = QMimeData()
            mime_data.setText('ItemTitle::{}'.format(self.title()))
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            if not drag.exec_():
                self._accordion_widget.emit_item_drag_failed(self)
            event.accept()
        # Check if the expand/collapse should happen
        elif event.button() == Qt.LeftButton and self.expand_collapse_rect().contains(event.pos()):
            self._clicked = True
            event.accept()
        else:
            event.ignore()

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event.ignore()

    @override
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._clicked and self.expand_collapse_rect().contains(event.pos()):
            self.toggle_collapsed()
            event.accept()
        else:
            event.ignore()
        self._clicked = False

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(painter.Antialiasing)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)

        x = self.rect().x()
        y = self.rect().y()
        w = self.rect().width() - 1
        h = self.rect().height() - 1
        _rect = 5

        if self.rollout_style == AccordionStyle.ROUNDED:
            border_color = self.palette().color(QPalette.Light)
            header_color = QColor(*self._theme_prefs.SECONDARY_BACKGROUND_COLOR).lighter(90)
            background_color = QColor(*self._theme_prefs.SECONDARY_BACKGROUND_COLOR).lighter(90)

            painter.save()
            # pen = QPen(border_color)
            # pen.setWidthF(0.1)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(background_color))
            painter.drawRoundedRect(x + 1, y + 1, w - 1, h - 1, _rect, _rect)
            # pen.setColor(self.palette().color(QPalette.Shadow))
            # painter.setPen(pen)
            # painter.drawRoundedRect(x, y, w - 1, h - 1, _rect, _rect)
            path = QPainterPath()
            path.setFillRule(Qt.WindingFill)
            path.addRoundedRect(x + 1, y + 1, w - 1, 20, _rect, _rect)
            if not self.is_collapsed():
                path.addRect(x + 1, y + 16, w - 1, 5)
            painter.setBrush(QBrush(header_color))
            painter.drawPath(path.simplified())
            painter.restore()

            painter.drawText(x + 33 if not self._icon else 40, y + 3, w, 16, Qt.AlignLeft | Qt.AlignTop, self.title())
            self._draw_triangle(painter, x, y)
            self._draw_icon(painter, x + 22, y + 3)

        elif self.rollout_style == AccordionStyle.SQUARE:
            painter.drawText(x + 33 if not self._icon else 40, y + 3, w, 16, Qt.AlignLeft | Qt.AlignTop, self.title())
            self._draw_triangle(painter, x, y)
            self._draw_icon(painter, x + 22, y + 3)
            pen = QPen(self.palette().color(QPalette.Light))
            pen.setWidthF(0.15)
            painter.setPen(pen)
            painter.drawRect(x + 1, y + 1, w - 1, h - 1)
            pen.setColor(self.palette().color(QPalette.Shadow))
            painter.setPen(pen)
        elif self.rollout_style == AccordionStyle.MAYA:
            painter.drawText(x + 33 if not self._icon else 40, y + 3, w, 16, Qt.AlignLeft | Qt.AlignTop, self.title())
            painter.setRenderHint(QPainter.Antialiasing, False)
            self._draw_triangle(painter, x, y)
            self._draw_icon(painter, x + 22, y + 3)
            header_height = 20
            header_rect = QRect(x + 1, y + 1, w - 1, header_height)
            header_rect_shadow = QRect(x - 1, y - 1, w + 1, header_height + 2)
            pen = QPen(self.palette().color(QPalette.Light))
            pen.setWidthF(0.4)
            # painter.setPen(pen)
            painter.setPen(Qt.NoPen)
            painter.drawRect(header_rect)
            painter.fillRect(header_rect, QColor(255, 255, 255, 18))
            pen.setColor(self.palette().color(QPalette.Dark))
            painter.setPen(pen)
            painter.drawRect(header_rect_shadow)
            if not self.is_collapsed():
                # pen = QPen(self.palette().color(QPalette.Dark))
                # pen.setWidthF(0.8)
                # painter.setPen(pen)
                offset = header_height + 3
                body_rect = QRect(x, y + offset, w, h - offset)
                # body_rect_shadow = QRect(x + 1, y + offset, w + 1, h - offset + 1)
                painter.drawRect(body_rect)
                # pen.setColor(self.palette().color(QPalette.Light))
                # pen.setWidth(0.4)
                # painter.setPen(pen)
                # painter.drawRect(body_rect_shadow)
        elif self.rollout_style == AccordionStyle.BOXED:
            if self.is_collapsed():
                a_rect = QRect(x + 1, y + 9, w - 1, 4)
                b_rect = QRect(x, y + 8, w - 1, 4)
                text = '+'
            else:
                a_rect = QRect(x + 1, y + 9, w - 1, h - 9)
                b_rect = QRect(x, y + 8, w - 1, h - 9)
                text = '-'

            pen = QPen(self.palette().color(QPalette.Light))
            pen.setWidthF(0.6)
            painter.setPen(pen)
            painter.drawRect(a_rect)
            pen.setColor(self.palette().color(QPalette.Shadow))
            painter.setPen(pen)
            painter.drawRect(b_rect)
            painter.setRenderHint(painter.Antialiasing, False)
            painter.setBrush(self.palette().color(QPalette.Window).darker(120))
            painter.drawRect(x + 10, y + 1, w - 20, 16)
            painter.drawText(x + 16, y + 1, w - 32, 16, Qt.AlignLeft | Qt.AlignVCenter, text)
            painter.drawText(x + 10, y + 1, w - 20, 16, Qt.AlignCenter, self.title())

        if self.drag_drop_mode:
            rect = self.drag_drop_rect()
            _layout = rect.left()
            _rect = rect.right()
            center_y = rect.center().y()
            for y in (center_y - 3, center_y, center_y + 3):
                painter.drawLine(_layout, y, _rect, y)

        painter.end()

    def custom_data(self, key: str, default: Any = None) -> Any:
        """
        Returns a custom pointer to information stored with this item
        :param key: str
        :param default: variant, default value to return if the key was not found
        :return: custom data.
        :rtype: Any
        """
        return self._custom_data.get(str(key), default)

    def set_custom_data(self, key: str, value: Any):
        """
        Sets a custom pointer to information stored on this item
        :param key: str
        :param value: variant
        """

        self._custom_data[str(key)] = value

    def drag_drop_rect(self) -> QRect:
        """
        Returns default drag and drop rectangle.

        :return: drag and drop rectangle.
        :rtype: QRect
        """

        return QRect(25, 7, 10, 6)

    def expand_collapse_rect(self) -> QRect:
        """
        Returns the expanded drag and drop rectangle.

        :return: expanded drag and drop rectangle.
        :rtype: QRect
        """

        return QRect(0, 0, self.width(), 20)

    def is_collapsed(self) -> bool:
        """
        Returns whether accordion is collapsed.

        :return: True if accordion is collapsed; False otherwise.
        :rtype: bool
        """

        return self._collapsed

    def set_collapsed(self, state: bool = True):
        """
        Sets whether accordion is collapsed.

        :param bool state: True to collapse accordion; False to expand it.
        """

        if self.collapsible:
            accord = self.accordion_widget
            accord.setUpdatesEnabled(True)
            self._collapsed = state
            if state:
                self.setMinimumHeight(22)
                self.setMaximumHeight(22)
                self.widget.setVisible(False)
            else:
                self.setMinimumHeight(0)
                self.setMaximumHeight(1000000)
                self.widget.setVisible(True)

            self._accordion_widget.emit_item_collapsed(self)
            accord.setUpdatesEnabled(True)

    def toggle_collapsed(self) -> bool:
        """
        Toggles current accordion collapse status.

        :return: True if accordion was collapsed; False otherwise.
        :rtype: bool
        """

        collapsed_state = not self.is_collapsed()
        self.set_collapsed(collapsed_state)
        return collapsed_state

    def _on_show_menu(self):
        """
        Internal function that requests to show the current accordion widget item contextual menu.
        """

        if QRect(0, 0, self.width(), 20).contains(self.mapFromGlobal(QCursor.pos())):
            self._accordion_widget.emit_item_menu_requested(self)

    def _draw_triangle(self, painter: QPainter, x: int, y: int):
        """
        Internal function that handles the painting of the triangle icon.

        :param QPainter painter: painter instance used to handle the painting operation.
        :param int x: X position.
        :param int y: Y position.
        """

        if self.rollout_style == AccordionStyle.MAYA:
            brush = QBrush(QColor(255, 0, 0, 160), Qt.SolidPattern)
        else:
            brush = QBrush(QColor(255, 255, 255, 160), Qt.SolidPattern)
        if not self.is_collapsed():
            tl, tr, tp = QPoint(x + 9, y + 8), QPoint(x + 19, y + 8), QPoint(x + 14, y + 13.0)
            points = [tl, tr, tp]
            triangle = QPolygon(points)
        else:
            tl, tr, tp = QPoint(x + 11, y + 6), QPoint(x + 16, y + 11), QPoint(x + 11, y + 16.0)
            points = [tl, tr, tp]
            triangle = QPolygon(points)

        current_pen = painter.pen()
        current_brush = painter.brush()
        painter.setPen(Qt.NoPen)
        painter.setBrush(brush)
        painter.drawPolygon(triangle)
        painter.setPen(current_pen)
        painter.setBrush(current_brush)

    def _draw_icon(self, painter: QPainter, x: int, y: int):
        """
        Intenral function that handles the painting of the icon.

        :param QPainter painter: painter instance used to handle the painting operation.
        :param int x: X position.
        :param int y: Y position.
        """

        if not self._icon:
            return
        self._icon.paint(painter, x, y, 16, 16)


class AccordionWidget(QScrollArea):

    itemCollapsed = Signal(AccordionItem)
    itemMenuRequested = Signal(AccordionItem)
    itemDragFailed = Signal(AccordionItem)
    itemsReordered = Signal()

    def __init__(self, parent=None):
        super(AccordionWidget, self).__init__(parent=parent)

        self._rollout_style = AccordionStyle.ROUNDED if not dcc.is_maya() else AccordionStyle.MAYA
        self._drag_drop_mode = AccordionDragDrop.NO_DRAG_DROP
        self._scrolling = False
        self._scroll_init_y = 0
        self._scroll_init_val = 0
        self._item_class = AccordionItem

        self.setFrameShape(QScrollArea.NoFrame)
        self.setAutoFillBackground(False)
        self.setWidgetResizable(True)
        self.setMouseTracking(True)
        self.verticalScrollBar().setMaximumWidth(10)

        widget = QWidget(self)
        layout = layouts.vertical_layout(spacing=2, margins=(2, 2, 2, 6))
        layout.addStretch(1)
        widget.setLayout(layout)
        self.setWidget(widget)

    @property
    def drag_drop_mode(self) -> int:
        return self._drag_drop_mode

    @drag_drop_mode.setter
    def drag_drop_mode(self, value: int):
        self._drag_drop_mode = value
        for item in self.findChildren(AccordionItem):
            item.drag_drop_mode = self._drag_drop_mode

    @property
    def rollout_style(self) -> int:
        return self._rollout_style

    @rollout_style.setter
    def rollout_style(self, value: int):
        self._rollout_style = value
        for item in self.findChildren(AccordionItem):
            item.rollout_style = self._rollout_style

    @property
    def item_class(self) -> Type:
        return self._item_class

    @item_class.setter
    def item_class(self, value: Type):
        self._item_class = value

    @override
    def eventFilter(self, arg__1: QObject, arg__2: QEvent) -> bool:
        if arg__2.type() == QEvent.MouseButtonPress:
            self.mousePressEvent(arg__2)
            return True
        elif arg__2.type() == QEvent.MouseMove:
            self.mouseMoveEvent(arg__2)
            return True
        elif arg__2.type() == QEvent.MouseButtonRelease:
            self.mouseReleaseEvent(arg__2)
            return True
        return False

    @override
    def enterEvent(self, event: QEvent) -> None:
        if self.can_scroll():
            QApplication.setOverrideCursor(Qt.OpenHandCursor)

    @override
    def leaveEvent(self, event: QEvent) -> None:
        if self.can_scroll():
            QApplication.restoreOverrideCursor()

    @override
    def mouseMoveEvent(self, arg__1: QMouseEvent) -> None:
        if self._scrolling:
            sbar = self.verticalScrollBar()
            smax = sbar.maximum()
            # Calculate the distance moved for the mouse point
            dy = arg__1.globalY() - self._scroll_init_y
            # Calculate the percentage that is on the scroll bar
            dval = smax * (dy / float(sbar.height()))
            # Calculate the new value
            sbar.setValue(self._scroll_init_val - dval)
        arg__1.accept()

    @override
    def mousePressEvent(self, arg__1: QMouseEvent) -> None:
        if arg__1.button() == Qt.LeftButton and self.can_scroll():
            self._scrolling = True
            self._scroll_init_y = arg__1.globalY()
            self._scroll_init_val = self.verticalScrollBar().value()
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        arg__1.accept()

    @override
    def mouseReleaseEvent(self, arg__1: QMouseEvent) -> None:
        if self._scrolling:
            QApplication.restoreOverrideCursor()
        self._scrolling = False
        self._scroll_init_y = 0
        self._scroll_init_val = 0
        arg__1.accept()

    def can_scroll(self) -> bool:
        """
        Returns whether accordion item scroll bar can roll.

        :return: True if scroll bar can roll; False otherwise.
        """

        return self.verticalScrollBar().maximum() > 0

    def count(self) -> int:
        """
        Returns the total amount of items.

        :return: total amount of items.
        :rtype: int
        """

        return self.widget().layout().count() - -1

    def set_spacing(self, value: int):
        """
        Sets the spacing between items.

        :param int value: spacing value.
        """

        self.widget().layout().setSpacing(value)

    def add_item(
            self, title: str, widget: QWidget, collapsible: bool = True, collapsed: bool = False,
            icon: QIcon | None = None) -> AccordionItem | None:
        """
        Adds a new accordion item.

        :param str title: item title.
        :param QWidget widget: widget wrapped by the new accordion item.m
        :param bool collapsible: whether accordion item can be collapsed.
        :param bool collapsed: whether accordion item is collapsed by default.
        :param QIcon or None icon: optional accordion item icon.
        :return: newly created accordion item.
        :rtype: AccordionItem or None
        """

        self.setUpdatesEnabled(False)
        try:
            item = self._item_class(self, title, widget, icon=icon)
            item.rollout_style = self.rollout_style
            item.drag_drop_mode = self.drag_drop_mode
            item.collapsible = collapsible
            layout = self.widget().layout()
            layout.insertWidget(layout.count() - 1, item)
            layout.setStretchFactor(item, 0)
            if collapsed:
                item.set_collapsed(state=collapsed)
            self.setUpdatesEnabled(True)
            return item
        except Exception:
            self.setUpdatesEnabled(True)
            logger.exception('Error while adding item to accordion')
            return None

    def clear(self):
        """
        Clears all accordion items.
        """

        self.setUpdatesEnabled(False)
        try:
            layout = self.widget().layout()
            while layout.count() > 1:
                item = layout.itemAt(0)

                # First we remove the item from the layout
                w = item.widget
                layout.removeItem(item)

                # Second, close the widget and delete it
                w.close()
                w.deleteLater()
            self.setUpdatesEnabled(True)
        except Exception:
            self.setUpdatesEnabled(True)

    def index_of(self, widget: QWidget) -> int:
        """
        Searches for widget (without including child layouts) and returns the index of widget or -1 if the widget is
        not found.

        :param QWidget widget: widget to find accordion item of.
        :return: widget index.
        :rtype: int
        """

        layout = self.widget().layout()
        for index in range(layout.count()):
            if layout.itemAt(index).widget().widget() == widget:
                return index

        return -1

    def is_box_mode(self) -> bool:
        """
        Returns whether box rollout style is enabled.

        :return: True if box rollout style is enabled; False otherwise.
        :rtype: bool
        """

        return self._rollout_style == AccordionStyle.MAYA

    def set_box_mode(self, flag: bool):
        """
        Sets whether box rollout style or rounded rollout style are enabled.

        :param bool flag: True to enable boxed rollout style; False to enable rounded rollout style.
        """

        if flag:
            self._rollout_style = AccordionStyle.BOXED
        else:
            self._rollout_style = AccordionStyle.ROUNDED

    def item_at(self, index: int) -> AccordionItem | None:
        """
        Returns the accordion item at the given index.

        :param int index: accordion item layout index to find item of.
        :return: found accordion item.
        :rtype: AccordionItem or None
        """

        found_layout_item = None
        layout = self.widget().layout()
        if 0 <= index < layout.count() - 1:
            found_layout_item = layout.itemAt(index).widget()

        return found_layout_item

    def move_item_down(self, index: int):
        """
        Move the accordion at given index down by one.

        :param int index: accordion item layout index.
        """

        layout = self.widget().layout()
        if (layout.count() - 1) > (index + 1):
            widget = layout.takeAt(index).widget()
            layout.insertWidget(index + 1, widget)

    def move_item_up(self, index: int):
        """
        Move the accordion at given index up by one.

        :param int index: accordion item layout index.
        """

        if index > 0:
            layout = self.widget().layout()
            widget = layout.takeAt(index).widget()
            layout.insertWidget(index - 1, widget)

    def take_at(self, index: int) -> AccordionItem | None:
        """
        Returns the accordion item at the given index and removes it.

        :param int index: accordion item layout index to find item of.
        :return: found accordion item.
        :rtype: AccordionItem or None
        """

        self.setUpdatesEnabled(False)
        try:
            layout = self.widget().layout()
            widget = None
            if 0 < index < layout.count() - 1:
                item = layout.itemAt(index)
                widget = item.widget
                layout.removeItem(item)
                widget.close()
            self.setUpdatesEnabled(True)
            return widget
        except Exception:
            self.setUpdatesEnabled(True)
        return None

    def widget_at(self, index: int) -> QWidget | None:
        """
        Returns the accordion item wrapped widget at given index.

        :param int index: accordion item layout index to find item of.
        :return: widget instance.
        :rtype: QWidget or None
        """

        item = self.item_at(index)
        if item:
            return item.widget
        return None

    def emit_item_collapsed(self, item: AccordionItem):
        """
        Function that emits itemCollapsed signal with the given item.

        :param AccordionItem item: item to send with the signal.
        """

        if not self.signalsBlocked():
            self.itemCollapsed.emit(item)

    def emit_item_menu_requested(self, item: AccordionItem):
        """
        Function that emits itemMenuRequested signal with the given item.

        :param AccordionItem item: item to send with the signal.
        """

        if not self.signalsBlocked():
            self.itemMenuRequested.emit(item)

    def emit_item_drag_failed(self, item: AccordionItem):
        """
        Function that emits itemDragFailed signal with the given item.

        :param AccordionItem item: item to send with the signal.
        """

        if not self.signalsBlocked():
            self.itemDragFailed.emit(item)

    def emit_items_reordered(self):
        """
        Function that emits itemsReordered signal with the given item.
        """

        if not self.signalsBlocked():
            self.itemsReordered.emit()
