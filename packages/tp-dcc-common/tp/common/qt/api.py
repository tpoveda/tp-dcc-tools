from __future__ import annotations

from Qt import QtCompat
from Qt.QtCore import (
    Qt, Signal, Property, QObject, QPoint, QPointF, QRect, QRectF, QSize, QSizeF, QItemSelectionModel,
    QAbstractListModel, QAbstractTableModel, QAbstractItemModel, QStringListModel, QModelIndex, QPersistentModelIndex,
    QEvent, QMimeData, QTimer, QRegularExpression, QMargins, QSortFilterProxyModel, QPropertyAnimation,
    QAbstractAnimation,QEasingCurve, QSequentialAnimationGroup, QThread, QThreadPool, QStandardPaths, QFile, QFileInfo,
    QUrl, QByteArray, QBuffer, QLine, QLineF, QLocale, QChildEvent, QTimerEvent, QSettings, QRegExp, QDataStream,
    QIODevice
)
from Qt.QtWidgets import (
    QApplication, QSizePolicy, QWidget, QFrame, QDialog, QButtonGroup, QMenu, QAction, QActionGroup, QMenuBar, QToolBar,
    QSplitter, QDockWidget, QPlainTextEdit, QDialogButtonBox, QShortcut, QListWidget, QListView, QTreeWidget,
    QTreeWidgetItem, QTreeWidgetItemIterator, QTreeView, QTableWidget, QTableView, QGraphicsDropShadowEffect,
    QWhatsThis, QAbstractItemView, QLabel, QScrollArea, QSpacerItem, QCommonStyle, QItemDelegate, QStyle, QComboBox,
    QStyledItemDelegate, QFormLayout, QListWidgetItem, QToolButton, QWidgetItem, QWidgetAction, QFileDialog,
    QPushButton, QLineEdit, QAbstractScrollArea, QGraphicsOpacityEffect, QVBoxLayout, QHBoxLayout, QGridLayout,
    QMainWindow, QStatusBar, QTextEdit, QTextBrowser, QTableWidgetItem, QCheckBox, QCompleter, QGraphicsObject,
    QGraphicsScene, QGraphicsView, QStackedWidget, QMessageBox, QInputDialog, QProgressBar, QGroupBox, QFileSystemModel,
    QGraphicsProxyWidget, QMdiArea, QMdiSubWindow, QGraphicsColorizeEffect, QTabWidget, QTabBar, QRadioButton, QSpinBox,
    QDoubleSpinBox, QSlider, QLayout, QStyleOptionViewItem, QHeaderView, QGraphicsSceneMouseEvent, QGraphicsItem,
    QToolTip, QGraphicsSceneDragDropEvent, QGraphicsSceneHelpEvent, QGraphicsSceneContextMenuEvent,
    QGraphicsSceneHoverEvent, QRubberBand, QScrollBar, QStyleOptionGraphicsItem, QGraphicsBlurEffect, QGraphicsPathItem,
    QAbstractSpinBox, QGraphicsTextItem, QOpenGLWidget, QUndoView, QUndoGroup, QUndoStack, QUndoCommand,
    QStyleOptionComboBox
)
from Qt.QtGui import (
    QCursor, QKeySequence, QFont, QFontMetrics, QFontMetricsF, QColor, QIcon, QPixmap, QImage, QPen, QBrush, QPainter,
    QPainterPath, QRadialGradient, QPalette, qRgba, qAlpha, QClipboard, QSyntaxHighlighter, QTextCharFormat, QPolygon,
    QPolygonF, QIntValidator, QDoubleValidator, QRegularExpressionValidator, QTransform, QImageReader, QDrag, QMovie,
    QContextMenuEvent, QShowEvent, QKeyEvent, QFocusEvent, QMoveEvent, QEnterEvent, QCloseEvent, QMouseEvent,
    QPaintEvent, QExposeEvent, QHoverEvent, QHelpEvent, QHideEvent, QInputEvent, QWheelEvent, QDropEvent,
    QDragMoveEvent, QDragEnterEvent, QResizeEvent, QActionEvent, QDesktopServices, QTextCursor, QTextDocument,
    QVector2D, QVector3D, QVector4D, QFontDatabase, QStandardItem, QStandardItemModel, QTextBlockFormat, QLinearGradient
)

from tp.common.resources import api as resources
from tp.common.qt import consts
from tp.common.qt.mvc import Model
from tp.common.qt.contexts import block_signals, application
from tp.common.qt.dpi import dpi_scale, dpi_scale_divide, dpi_multiplier, margins_dpi_scale, size_by_dpi, point_by_dpi
from tp.common.qt.qtutils import (
    get_widget_at_mouse, compat_ui_loader, clear_layout, to_qt_object, set_stylesheet_object_name, process_ui_events,
    clear_focus_widgets, get_or_create_menu, single_shot_timer, safe_tree_widget_iterator, safe_disconnect_signal,
    safe_delete_later, restore_cursor, layout_items, layout_widgets, update_widget_sizes, update_widget_style,
    signal_names, current_screen_geometry, available_screen_rect, close_widgets_with_title, close_widgets_of_class,
    center_widget_on_screen, center_window_on_screen, iterate_children, iterate_parents
)
from tp.common.qt.models.datasources import BaseDataSource
from tp.common.qt.models.listmodel import BaseListModel
from tp.common.qt.models.tablemodel import BaseTableModel
from tp.common.qt.models.treemodel import BaseTreeModel
from tp.common.qt.widgets.layouts import (
    vertical_layout, horizontal_layout, grid_layout, form_layout, box_layout, flow_layout, graphics_linear_layout,
    vertical_graphics_linear_layout, horizontal_graphics_linear_layout
)
from tp.common.qt.widgets.frames import BaseFrame, CollapsableFrame, CollapsableFrameThin
from tp.common.qt.widgets.labels import (
    label, h1_label, h2_label, h3_label, h4_label, h5_label, clipped_label, icon_label, BaseLabel
)

from tp.common.qt.widgets.frameless import FramelessWindow, FramelessWindowThin
from tp.common.qt.widgets.comboboxes import combobox, BaseComboBox, ComboBoxRegularWidget
from tp.common.qt.widgets.lineedits import (
    line_edit, text_browser, BaseLineEdit, StringLineEditWidget, FloatLineEditWidget, IntLineEditWidget
)
from tp.common.qt.widgets.dividers import divider, Divider, DividerLayout, LabelDivider
from tp.common.qt.widgets.buttons import (
    styled_button, base_button, regular_button, rounded_button, shadowed_button, tool_button, left_aligned_button,
    BaseButton, BasePushButton, BaseToolButton, IconMenuButton, OkCancelButtons, LeftAlignedButton
)
from tp.common.qt.widgets.listviews import ExtendedListView
from tp.common.qt.widgets.tableviews import BaseTableView, ExtendedTableView
from tp.common.qt.widgets.treeviews import BaseTreeView, ExtendedTreeView
from tp.common.qt.widgets.menus import menu, searchable_menu, extended_menu
from tp.common.qt.widgets.popups import (
    show_question, show_save, show_warning, show_combo, show_multi_choice, input_dialog
)
from tp.common.qt.widgets.search import SearchLineEdit
from tp.common.qt.widgets.groupedtreewidget import GroupedTreeWidget
from tp.common.qt.widgets.linetabwidget import LineTabWidget
from tp.common.qt.widgets.stack import sliding_opacity_stacked_widget, StackItem
from tp.common.qt.widgets.checkboxes import checkbox, checkbox_widget, BaseCheckBoxWidget
from tp.common.qt.widgets.toolbars import FlowToolBar
from tp.common.qt.widgets.accordion import AccordionWidget, AccordionStyle
from tp.common.qt.widgets.directories import PathWidget
from tp.common.qt.widgets.radiobuttongroup import RadioButtonGroup


def widget(layout: QLayout, parent: QWidget | None = None) -> QWidget:
    """
    Returns a new widget instance with the given layout.

    :param QLayout layout: widget layout.
    :param QWidget or None parent: optional parent widget.
    :return: newly created widget.
    :rtype: QWidget
    """

    new_widget = QWidget(parent=parent)
    new_widget.setLayout(layout)

    return new_widget


# from tp.common.qt.base import widget, frame, BaseWidget, BaseFrame, ScrollWidget
# from tp.common.qt.widgets.buttons import (button, base_button, base_push_button,axis_button, ButtonStyles)
# from tp.common.qt.widgets.checkboxes import checkbox
# from tp.common.qt.widgets.directory import open_folder_widget, open_file_widget, save_file_widget, PathWidget
# from tp.common.qt.widgets.comboboxes import (
# 	combobox, searchable_combobox, combobox_widget, searchable_combobox_widget, bool_combobox
# )
# from tp.common.qt.widgets.search import search_widget
# from tp.common.qt.widgets.accordion import AccordionWidget, AccordionStyle
