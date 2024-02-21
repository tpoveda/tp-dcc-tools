#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility module that contains useful utilities functions for PySide
"""

from __future__ import annotations

import os
import sys
import struct
import inspect
import contextlib
from typing import Callable, List, Iterator, Type

from tp.core import log, dcc
from tp.common.python import helpers
from tp.common.resources import color

logger = log.tpLogger

QT_ERROR_MESSAGE = 'Qt.py is not available and Qt related functionality will not be available!'

QT_AVAILABLE = True
_QT_TEST_AVAILABLE = True
try:
    from Qt.QtCore import Qt, Signal, QObject, QPoint, QRect, QSize, QTimer
    from Qt.QtWidgets import (
        QApplication, QLayout, QVBoxLayout, QHBoxLayout, QWidget, QFrame, QLabel, QPushButton, QSizePolicy, QMessageBox,
        QInputDialog, QFileDialog, QMenu, QMenuBar, QGraphicsDropShadowEffect, QTreeWidget, QTreeWidgetItem,
        QTreeWidgetItemIterator, QMainWindow
    )
    from Qt.QtGui import QFontDatabase, QPixmap, QIcon, QColor, QCursor, QGuiApplication, QScreen
    from Qt import QtGui
    from Qt import QtCompat
    from Qt import __binding__
    from tp.common.qt import dpi
except ImportError as e:
    QT_AVAILABLE = False
    logger.warning(f'Impossible to load Qt libraries. Qt dependant functionality will be disabled: {e}')
try:
    from Qt import QtTest
except ImportError:
    _QT_TEST_AVAILABLE = False

if QT_AVAILABLE:
    if __binding__ == 'PySide2':
        try:
            import shiboken2 as shiboken
        except ImportError:
            from PySide2 import shiboken2 as shiboken
    elif __binding__ == 'PySide6':
        try:
            import shiboken6 as shiboken
        except ImportError:
            from PySide6 import shiboken6 as shiboken
    elif __binding__ == 'PySide':
        try:
            import shiboken
        except ImportError:
            try:
                from Shiboken import shiboken
            except ImportError:
                try:
                    from PySide import shiboken
                except Exception:
                    pass

MAX_INT = 2 ** (struct.Struct('i').size * 8 - 1) - 1

UI_EXTENSION = '.ui'
QWIDGET_SIZE_MAX = (1 << 24) - 1
FLOAT_RANGE_MIN = 0.1 + (-MAX_INT - 1.0)
FLOAT_RANGE_MAX = MAX_INT + 0.1
INT_RANGE_MIN = -MAX_INT
INT_RANGE_MAX = MAX_INT
CURRENT_DIR = os.path.expanduser('~')

if helpers.is_python3():
    long = int


def is_pyqt():
    """
    Returns True if the current Qt binding is PyQt
    :return: bool
    """

    return 'PyQt' in __binding__


def is_pyqt4():
    """
    Retunrs True if the currente Qt binding is PyQt4
    :return: bool
    """

    return __binding__ == 'PyQt4'


def is_pyqt5():
    """
    Retunrs True if the currente Qt binding is PyQt5
    :return: bool
    """

    return __binding__ == 'PyQt5'


def is_pyside():
    """
    Returns True if the current Qt binding is PySide
    :return: bool
    """

    return __binding__ == 'PySide'


def is_pyside2():
    """
    Returns True if the current Qt binding is PySide2
    :return: bool
    """

    return __binding__ == 'PySide2'


def is_pyside6():
    """
    Returns True if the current Qt binding is PySide6
    :return: bool
    """

    return __binding__ == 'PySide6'


def get_ui_library():
    """
    Returns the library that is being used
    """

    try:
        import PyQt5
        qt = 'PyQt5'
    except ImportError:
        try:
            import PyQt4
            qt = 'PyQt4'
        except ImportError:
            try:
                import PySide2
                qt = 'PySide2'
            except ImportError:
                try:
                    import PySide
                    qt = 'PySide'
                except ImportError:
                    raise ImportError("No valid Gui library found!")
    return qt


def wrapinstance(ptr, base=None):
    if ptr is None:
        return None

    ptr_type = long if helpers.is_python2() else int

    ptr = ptr_type(ptr)
    if 'shiboken' in globals():
        if base is None:
            qObj = shiboken.wrapInstance(ptr_type(ptr), QObject)
            meta_obj = qObj.metaObject()
            cls = meta_obj.className()
            super_cls = meta_obj.superClass().className()
            if hasattr(QtGui, cls):
                base = getattr(QtGui, cls)
            elif hasattr(QtGui, super_cls):
                base = getattr(QtGui, super_cls)
            else:
                base = QWidget
        try:
            return shiboken.wrapInstance(ptr_type(ptr), base)
        except Exception:
            from PySide.shiboken import wrapInstance
            return wrapInstance(ptr_type(ptr), base)
    elif 'sip' in globals():
        base = QObject
        return shiboken.wrapinstance(ptr_type(ptr), base)
    else:
        print('Failed to wrap object ...')
        return None


def unwrapinstance(object):
    """
    Unwraps objects with PySide
    """

    if helpers.is_python2():
        return long(shiboken.getCppPointer(object)[0])
    else:
        return int(shiboken.getCppPointer(object)[0])


@contextlib.contextmanager
def app():
    """
    Context to create a Qt app
    >>> with with qtutils.app():
    >>>     w = QWidget(None)
    >>>     w.show()
    :return:
    """

    app_ = None
    is_app_running = bool(QApplication.instance())
    if not is_app_running:
        app_ = QApplication(sys.argv)
        install_fonts()

    yield None

    if not is_app_running:
        sys.exit(app_.exec_())


def install_fonts(fonts_path):
    """
    Install all the fonts in the given directory path
    :param fonts_path: str
    """

    if not os.path.isdir(fonts_path):
        return

    font_path = os.path.abspath(fonts_path)
    font_data_base = QFontDatabase()
    for filename in os.listdir(font_path):
        if filename.endswith('.ttf'):
            filename = os.path.join(font_path, filename)
            result = font_data_base.addApplicationFont(filename)
            if result > 0:
                logger.debug('Added font {}'.format(filename))
            else:
                logger.debug('Impossible to add font {}'.format(filename))


def ui_path(cls):
    """
    Returns the UI path for the given widget class
    :param cls: type
    :return: str
    """

    name = cls.__name__
    ui_path = inspect.getfile(cls)
    dirname = os.path.dirname(ui_path)

    ui_path = dirname + '/resource/ui' + name + UI_EXTENSION
    if not os.path.exists(ui_path):
        ui_path = dirname + '/ui/' + name + UI_EXTENSION
    if not os.path.exists(ui_path):
        ui_path = dirname + '/' + name + UI_EXTENSION

    return ui_path


def load_widget_ui(widget, path=None):
    """
    Loads UI of the given widget
    :param widget: QWidget or QDialog
    :param path: str
    """

    if not path:
        path = ui_path(widget.__class__)

    cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(path))
        widget.ui = QtCompat.loadUi(path, widget)
    except Exception as e:
        pass
        # tpPyUtils.logger.debug('{} | {}'.format(e, traceback.format_exc()))
    finally:
        os.chdir(cwd)


def compat_ui_loader(ui_file, widget=None):
    """
    Loads GUI from .ui file using compat module
    In some DCCs, such as 3ds Max this function does not work properly. In those cases use load_ui function
    :param ui_file: str, path to the UI file
    :param widget: parent widget
    """

    if not ui_file:
        ui_file = ui_path(widget.__class__)

    ui = QtCompat.loadUi(ui_file)
    if not widget:
        return ui
    else:
        for member in dir(ui):
            if not member.startswith('__') and member != 'staticMetaObject':
                setattr(widget, member, getattr(ui, member))
        return ui


def signal_names(class_obj: Type) -> List[str]:
    """
    Returns a list with all signal names of a class.

    :param Type class_obj: class to get signals from.
    :return: list of signal names.
    :rtype: List[str]
    """

    result = [x for x in vars(class_obj).items() if isinstance(x[1], Signal)]
    if class_obj.__base__ and class_obj.__base__ != QObject:
        result.extend(signal_names(class_obj.__base__))

    return result


def safe_disconnect_signal(signal):
    """
    Disconnects given signal in a safe way
    :param signal: Signal
    """

    try:
        signal.disconnect()
    except Exception:
        pass


def safe_delete_later(widget):
    """
    calls the deleteLater method on the given widget, but only
    in the necessary Qt environment
    :param widget: QWidget
    """

    if __binding__ in ('PySide', 'PyQt4'):
        widget.deleteLater()


def show_info(parent, title, info):
    """
    Show a info QMessageBox with the given info
    :return:
    """

    return QMessageBox.information(parent, title, info)


def show_question(parent, title, question):
    """
    Show a question QMessageBox with the given question text
    :param question: str
    :return:
    """

    flags = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    return QMessageBox.question(parent, title, question, flags)


def show_warning(parent, title, warning):
    """
    Shows a warning QMessageBox with the given warning text
    :param parent: QWidget
    :param title: str
    :param warning: str
    :return:
    """

    return QMessageBox.warning(parent, title, warning)


def show_error(parent, title, error):
    """
    Show a error QMessageBox with the given error
    :return:
    """

    return QMessageBox.critical(parent, title, error)


def clear_layout(layout):
    """
    Removes all the widgets added in the given layout
    :param layout: QLayout
    """

    while layout.count():
        child = layout.takeAt(0)
        if child.widget() is not None:
            child.widget().deleteLater()
        elif child.layout() is not None:
            clear_layout(child.layout())

    # for i in reversed(range(layout.count())):
    #     item = layout.itemAt(i)
    #     if item:
    #         w = item.widget()
    #         if w:
    #             w.setParent(None)


def clear_stack_widget(stack_widget):
    """
    Clears all the widgets stacked in the given stack widget
    :param stack_widget: QStackWidget
    """

    for i in range(stack_widget.count(), 0, -1):
        widget = stack_widget.widget(i)
        stack_widget.removeWidget(widget)
        widget.deleteLater()


def layout_items(layout):
    """
    Returns the items from the given layout and returns them
    :param layout: QLayout, layout to retrieve items from
    :return: list(QWidgetItem)
    """

    return [layout.itemAt(i) for i in range(layout.count())]


def layout_widgets(layout):
    """
    Returns the widgets from the given layout and returns them
    :param layout: QLayout, layout to retrieve widgets from
    :return: list(QWidget)
    """

    return [layout.itemAt(i).widget() for i in range(layout.count())]


def image_to_clipboard(path):
    """
    Copies the image at path to the system's global clipboard
    :param path: str
    """

    image = QtGui.QImage(path)
    clipboard = QApplication.clipboard()
    clipboard.setImage(image, mode=QtGui.QClipboard.Clipboard)


def get_horizontal_separator():
    v_div_w = QWidget()
    v_div_l = QVBoxLayout()
    v_div_l.setAlignment(Qt.AlignLeft)
    v_div_l.setContentsMargins(0, 0, 0, 0)
    v_div_l.setSpacing(0)
    v_div_w.setLayout(v_div_l)
    v_div = QFrame()
    v_div.setMinimumHeight(30)
    v_div.setFrameShape(QFrame.VLine)
    v_div.setFrameShadow(QFrame.Sunken)
    v_div_l.addWidget(v_div)
    return v_div_w


def get_rounded_mask(width, height, radius_tl=10, radius_tr=10, radius_bl=10, radius_br=10):
    region = QtGui.QRegion(0, 0, width, height, QtGui.QRegion.Rectangle)

    # top left
    round = QtGui.QRegion(0, 0, 2 * radius_tl, 2 * radius_tl, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(0, 0, radius_tl, radius_tl, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    # top right
    round = QtGui.QRegion(width - 2 * radius_tr, 0, 2 * radius_tr, 2 * radius_tr, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(width - radius_tr, 0, radius_tr, radius_tr, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    # bottom right
    round = QtGui.QRegion(
        width - 2 * radius_br, height - 2 * radius_br, 2 * radius_br, 2 * radius_br, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(width - radius_br, height - radius_br, radius_br, radius_br, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    # bottom left
    round = QtGui.QRegion(0, height - 2 * radius_bl, 2 * radius_bl, 2 * radius_br, QtGui.QRegion.Ellipse)
    corner = QtGui.QRegion(0, height - radius_bl, radius_bl, radius_bl, QtGui.QRegion.Rectangle)
    region = region.subtracted(corner.subtracted(round))

    return region


def distance_point_to_line(p, v0, v1):
    """
    Returns the distance from the given point to line created by the two given v0 and v1 points
    :param p: QPoint
    :param v0: QPoint
    :param v1: QPoint
    :return:
    """

    v = QtGui.QVector2D(v1 - v0)
    w = QtGui.QVector2D(p - v0)
    c1 = QtGui.QVector2D.dotProduct(w, v)
    c2 = QtGui.QVector2D.dotProduct(v, v)
    b = c1 * 1.0 / c2
    pb = v0 + v.toPointF() * b
    return QtGui.QVector2D(p - pb).length()


def qhash(inputstr):
    if helpers.is_string(inputstr):
        instr = inputstr
    else:
        return -1

    h = 0x00000000
    for i in range(0, len(instr)):
        h = (h << 4) + ord(instr[i])
        h ^= (h & 0xf0000000) >> 23
        h &= 0x0fffffff
    return h


def get_focus_widget():
    """
    Gets the currently focused widget
    :return: variant, QWidget || None
    """

    return QApplication.focusWidget()


def clear_focus_widgets():
    """
    Clears focus if widgets have clearFocus property.
    """

    focus_widget = QApplication.focusWidget()
    if focus_widget is not None and focus_widget.property("clearFocus"):
        focus_widget.clearFocus()


def get_squared_length(point):
    """
    Returns the squared length of a point.

    :param QPoint point: point.
    :return: point square length.
    :rtype: int

    ..note:: higher performance than length (at the cost of accuracy).
    """

    return point.dotProduct(point, point)


def window_offset(window):
    """
    Returns the window offset.

    :param QMainWindow window: window widget.
    :return: window offset.
    :rtype: int
    """

    return window.pos() - window.mapToGlobal(QPoint(0, 0))


def widget_center(widget: QWidget) -> QPoint:
    """
    Returns the center of the given widget.

    :param QWidget widget: widget whose center we want to retrieve.
    :return: widget center.
    :rtype: QPoint
    """

    return QPoint(int(widget.width() * 0.5), int(widget.height() * 0.5))


def get_widget_at_mouse():
    """
    Returns the widget under the mouse.

    :return: widget located over the mouse. If no widget found, None will be returned.
    :rtype: QWidget or None
    """

    current_pos = QtGui.QCursor().pos()
    return QApplication.widgetAt(current_pos)


def get_widgets_at(pos):
    """
    Returns all widgets underneath the given mouse position.

    :param QPoint pos: mouse cursor position.
    :return: list of all widgets under given mouse position.
    :rtype: list(QWidget)
    """

    widgets = list()
    widget_at = QApplication.widgetAt(pos)

    widgets_statuses = list()
    while widget_at:
        widgets.append((widget_at, widget_at.mapFromGlobal(pos)))
        # make widget invisible to further enquiries
        widgets_statuses.append((widget_at, widget_at.testAttribute(Qt.WA_TransparentForMouseEvents)))
        widget_at.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        widget_at = QApplication.widgetAt(pos)

    # restore attribute
    for widget in widgets_statuses:
        widget[0].setAttribute(Qt.WA_TransparentForMouseEvents, widget[1])

    return widgets


def get_widget_cursor(widget):
    """
    Returns the position of the cursor relative to the given widget.

    :param QWidget widget: qt widget.
    :return: cursor position.
    :rtype: QPoint
    """

    return widget.mapFromGlobal(QCursor.pos())


def is_valid_widget(widget):
    """
    Checks if a widget is a valid in the backend.

    :param QWidget widget: widget to check validity of.
    :return: True if the widget still has a valid C++ object, False otherwise.
    :rtype: bool
    """

    if widget is None:
        return False

    # Added try because some Dccs (such as Houdini) does not includes shiboken library by default
    # TODO: When Houdini app class implemented, add cleaner way
    try:
        if not shiboken.isValid(widget):
            return False
    except Exception:
        return True

    return True


def is_widget_visible(widget: QWidget) -> bool:
    """
    Returns whether given widget is visible.

    :param QWidget widget: widget to check visibility of.
    :return: True if widget is visible; False otherwise.
    :rtype: bool
    """

    if not widget.visibleRegion().isEmpty():
        return True

    return False


def close_and_cleanup(widget):
    """
    Call close and deleteLater on a widget safely
    NOTE: Skips the close call if the widget is already not visible
    :param widget: QWidget, widget to delete and close
    """
    if is_valid_widget(widget):
        if widget.isVisible():
            widget.close()
        widget.deleteLater()


def close_widgets_with_title(title: str, parent: None | QWidget = None):
    """
    Closes all widgets with given title.

    :param str title: widget title.
    :param QWidget | None = None parent: optional parent widget. If not given, current main window will be used.
    """

    parent = parent or dcc.main_window()
    if not parent:
        return
    for child in [ch for ch in parent.findChildren(QWidget) if ch.windowTitle() == title]:
        close_and_cleanup(child)


def close_widgets_of_class(widget_class: type, parent: None | QWidget = None):
    """
    Closes all widgets with given title.

    :param type widget_class: widget class to find.
    :param QWidget | None = None parent: optional parent widget. If not given, current main window will be used.
    """

    parent = parent or dcc.main_window()
    if not parent:
        return
    for child in [ch for ch in parent.findChildren(widget_class)]:
        close_and_cleanup(child)


def get_string_input(message, title='Rename', old_name=None, parent=None):
    """
    Shows a Input dialog to allow the user to input a new string
    :param message: str, mesage to show in the dialog
    :param title: str, title of the input dialog
    :param old_name: str (optional): old name where are trying to rename
    :return: str, new name
    """

    dialog = QInputDialog(parent)
    flags = dialog.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint

    if not old_name:
        comment, ok = dialog.getText(None, title, message, flags=flags)
    else:
        comment, ok = dialog.getText(None, title, message, text=old_name, flags=flags)

    comment = comment.replace('\\', '_')

    if ok:
        return str(comment)


def get_comment(text_message='Add Comment', title='Save', comment_text='', parent=None):
    """
    Shows a comment dialog to allow user to input a new comment
    :param parent: QwWidget
    :param text_message: str, text to show before message input
    :param title: str, title of message dialog
    :param comment_text: str, default text for the commment
    :return: str, input comment write by the user
    """

    comment_dialog = QInputDialog()
    flags = comment_dialog.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    if is_pyside2() or is_pyqt5():
        comment, ok = comment_dialog.getMultiLineText(parent, title, text_message, flags=flags, text=comment_text)
    else:
        comment, ok = comment_dialog.getText(parent, title, text_message, flags=flags, text=comment_text)
    if ok:
        return comment


def get_file(directory, filters=None, dialog_title=None, parent=None):
    """
    Show an open file dialog
    :param directory: str, root directory
    :param parent: QWidget
    :return: str, selected folder or None if no folder is selected
    """

    file_dialog = QFileDialog(parent)
    if directory:
        file_dialog.setDirectory(directory)
    directory = file_dialog.getOpenFileName(parent, caption=dialog_title or '', filter=filters)
    directory = helpers.force_list(directory)
    if directory:
        return directory


def get_folder(directory=None, title='Select Folder', show_files=False, parent=None):
    """
    Shows a open folder dialog
    :param directory: str, root directory
    :param title: str, select folder dialog title
    :param parent: QWidget
    :return: str, selected folder or None if no folder is selected
    """

    file_dialog = QFileDialog(parent)
    if show_files:
        file_dialog.setFileMode(QFileDialog.DirectoryOnly)
        file_dialog.setOption(QFileDialog.ShowDirsOnly, False)
    if directory:
        file_dialog.setDirectory(directory)
    directory = file_dialog.getExistingDirectory(parent, title)
    if directory:
        return directory


def get_permission(message=None, cancel=True, title='Permission', parent=None):
    """
    Shows a permission message box
    :param message: str, message to show to the user
    :param cancel: bool, Whether the user can cancel the operation or not
    :param title: str, title of the window
    :param parent: QWidget
    :return: bool
    """

    message_box = QMessageBox(parent=parent)
    message_box.setWindowTitle(title)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    if message:
        message_box.setText(message)
    if cancel:
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    else:
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    message_box.setWindowFlags(flags)
    result = message_box.exec_()

    if result == QMessageBox.Yes:
        return True
    elif result == QMessageBox.No:
        return False
    elif result == QMessageBox.Cancel:
        return None

    return None


def get_save_permission(message, file_path=None, title='Permission', parent=None):
    """
    Shows a save path message box
    :param message: str, message to show to the user
    :param file_path: str, path you want to save
    :param title: str, title of the window
    :param parent: QWidget
    :return: bool
    """

    message_box = QMessageBox(parent=parent)
    message_box.setWindowTitle(title)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    if file_path:
        path_message = 'Path: {}'.format(file_path)
        message_box.setInformativeText(path_message)
    message_box.setWindowFlags(flags)
    save = message_box.addButton('Save', QMessageBox.YesRole)
    no_save = message_box.addButton('Do not save', QMessageBox.NoRole)
    cancel = message_box.addButton('Cancel', QMessageBox.RejectRole)
    message_box.exec_()

    if message_box.clickedButton() == save:
        return True
    elif message_box.clickedButton() == no_save:
        return False
    elif message_box.clickedButton() == cancel:
        return None

    return None


def get_line_layout(title, parent, *widgets):
    """
    Returns a QHBoxLayout with all given widgets added to it
    :param parent: QWidget
    :param title: str
    :param widgets: list<QWidget>
    :return: QHBoxLayout
    """

    layout = QHBoxLayout()
    layout.setContentsMargins(1, 1, 1, 1)
    if title and title != '':
        label = QLabel(title, parent)
        layout.addWidget(label)
    for w in widgets:
        if isinstance(w, QWidget):
            layout.addWidget(w)
        elif isinstance(w, QLayout):
            layout.addLayout(w)

    return layout


def get_column_layout(*widgets):
    """
    Returns a QVBoxLayout with all given widgets added to it
    :param widgets: list<QWidget>
    :return: QVBoxLayout
    """

    layout = QVBoxLayout()
    for w in widgets:
        if isinstance(w, QWidget):
            layout.addWidget(w)
        elif isinstance(w, QLayout):
            layout.addLayout(w)

    return layout


def get_top_level_widget(w):
    widget = w
    while True:
        parent = widget.parent()
        if not parent:
            break
        widget = parent

        return widget


def is_modifier():
    """
    Returns True if either the Alt key or Control key is down
    :return: bool
    """

    return is_alt_modifier() or is_control_modifier()


def is_alt_modifier():
    """
    Return True if the Alt key is down
    :return: bool
    """

    modifiers = QApplication.keyboardModifiers()
    return modifiers == Qt.AltModifier


def is_control_modifier():
    """
    Returns True if the Control key is down
    :return: bool
    """

    modifiers = QApplication.keyboardModifiers()
    return modifiers == Qt.ControlModifier


def is_shift_modifier():
    """
    Returns True if the Shift key is down
    :return: bool
    """

    modifiers = QApplication.keyboardModifiers()
    return modifiers == Qt.ShiftModifier


def to_qt_object(long_ptr, qobj=None):
    """
    Returns an instance of the Maya UI element as a QWidget
    """

    if not qobj:
        qobj = QWidget

    return wrapinstance(long_ptr, qobj)


def critical_message(message, parent=None):
    """
    Shows a critical message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.critical(parent, 'Critical Error', message)


def warning_message(message, parent=None):
    """
    Shows a warning message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.warning(parent, 'Warning', message)


def info_message(message, parent=None):
    """
    Shows a warning message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.setText(message)
    message_box.exec_()


def about_message(message, parent=None):
    """
    Shows an about message
    :param message: str
    :param parent: QWidget
    """

    parent = None
    message_box = QMessageBox(parent)
    flags = message_box.windowFlags() ^ Qt.WindowContextHelpButtonHint | Qt.WindowStaysOnTopHint
    message_box.setWindowFlags(flags)
    message_box.about(parent, 'About', message)


def change_button_color(
        button,
        text_color=200, bg_color=68, hi_color=68,
        hi_text=255, hi_background=[97, 132, 167],
        ds_color=[255, 128, 128],
        mode='common',
        toggle=False, hover=True, destroy=False,
        ds_width=1):

    text_color = helpers.to_3_list(text_color)
    bg_color = helpers.to_3_list(bg_color)
    hi_color = helpers.to_3_list(hi_color)
    hi_text = helpers.to_3_list(hi_text)
    ds_color = helpers.to_3_list(ds_color)

    if toggle and button.isChecked():
        bg_color = hi_color
    if hover:
        hv_color = map(lambda a: a + 20, bg_color)
    else:
        hv_color = bg_color

    text_hex = color.convert_2_hex(text_color)
    bg_hex = color.convert_2_hex(bg_color)
    hv_hex = color.convert_2_hex(hv_color)
    hi_hex = color.convert_2_hex(hi_color)
    ht_hex = color.convert_2_hex(hi_text)
    hb_hex = color.convert_2_hex(hi_background)
    ds_hex = color.convert_2_hex(ds_color)

    if mode == 'common':
        button.setStyleSheet('color: ' + text_hex + ' ; background-color: ' + bg_hex)
    elif mode == 'button':
        if not destroy:
            button.setStyleSheet(
                'QPushButton{'
                'background-color: ' + bg_hex + '; color:  ' + text_hex + '; border-style:solid; border-width: ' + str(
                    ds_width) + 'px; border-color:' + ds_hex + '; border-radius: 0px;}' + 'QPushButton:hover{'
                'background-color: ' + hv_hex + '; color:  ' + text_hex + '; border-style:solid; border-width: ' + str(
                    ds_width) + 'px; border-color:' + ds_hex + '; border-radius: 0px;}' + 'QPushButton:pressed{'
                'background-color: ' + hi_hex + '; color: ' + text_hex + '; border-style:solid; border-width: ' + str(
                    ds_width) + 'px; border-color:' + ds_hex + '; border-radius: 0px;}')
        else:
            button_style = 'QPushButton{background-color: ' + bg_hex + '; color:  ' + text_hex + ' ; border: black 0px}'
            button_style += 'QPushButton:hover{background-color: ' + hv_hex + '; color:  ' + text_hex
            button_style += ' ; border: black 0px}' + 'QPushButton:pressed{background-color: ' + hi_hex + '; color: '
            button_style += text_hex + '; border: black 2px}'
            button.setStyleSheet(button_style)
    elif mode == 'window':
        button_style = 'color: ' + text_hex + ';' + 'background-color: ' + bg_hex + ';' + 'selection-color: '
        button_style += ht_hex + ';' + 'selection-background-color: ' + hb_hex + ';'
        button.setStyleSheet(button_style)


def change_border_style(btn):
    button_style = 'QPushButton{border-style:solid; border-width: 2px; border-color: red ; border-radius: 1px;}'
    button_style += 'QPushButton:hover{border-style:solid; border-width: 2px; border-color: red ; border-radius: 1px;}'
    button_style += 'QPushButton:pressed' \
                    '{border-style:solid; border-width: 2px; border-color: red ; border-radius: 1px;}'
    btn.setStyleSheet(button_style)


def create_flat_button(
        icon=None, icon_size=None,
        name='', text=200,
        background_color=[54, 51, 51],
        ui_color=68,
        border_color=180,
        push_col=120,
        checkable=True,
        w_max=None, w_min=None,
        h_max=None, h_min=None,
        policy=None,
        tip=None, flat=True,
        hover=True,
        destroy_flag=False,
        context=None,
):

    btn = QPushButton()
    btn.setText(name)
    btn.setCheckable(checkable)
    if icon:
        if isinstance(icon, QIcon):
            btn.setIcon(icon)
        else:
            btn.setIcon(QIcon(icon))
    btn.setFlat(flat)
    if flat:
        change_button_color(button=btn, text_color=text, bg_color=ui_color, hi_color=background_color,
                            mode='button', hover=hover, destroy=destroy_flag, ds_color=border_color)
        btn.toggled.connect(lambda: change_button_color(button=btn, text_color=text, bg_color=ui_color,
                                                        hi_color=background_color, mode='button', toggle=True,
                                                        hover=hover, destroy=destroy_flag, ds_color=border_color))
    else:
        change_button_color(button=btn, text_color=text, bg_color=background_color,
                            hi_color=push_col, mode='button', hover=hover, destroy=destroy_flag, ds_color=border_color)

    if w_max:
        btn.setMaximumWidth(w_max)
    if w_min:
        btn.setMinimumWidth(w_min)
    if h_max:
        btn.setMaximumHeight(h_max)
    if h_min:
        btn.setMinimumHeight(h_min)
    if icon_size:
        btn.setIconSize(QSize(*icon_size))
    if policy:
        btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
    if tip:
        btn.setToolTip(tip)
    if context:
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(context)

    return btn


def create_vertical_line():
    """
    Creates and returns a new vertical line
    :return: QFrame
    """

    line_frame = QFrame()
    line_frame.setFrameShape(QFrame.VLine)
    line_frame.setFrameShadow(QFrame.Sunken)

    return line_frame


def create_horizontal_line():
    """
    Creates and returns a new horizontal line
    :return: QFrame
    """

    line_frame = QFrame()
    line_frame.setFrameShape(QFrame.HLine)
    line_frame.setFrameShadow(QFrame.Sunken)

    return line_frame


def get_or_create_menu(menu_bar, menu_title):
    """
    Creates a new menu in the given menubar with the given menubar or return Menu object if the a menu
    with the given name already exists in the menu bar
    :param menu_bar: QMenuBar or QMenu
    :param menu_title: str
    :return: QMenu
    """

    for child in menu_bar.findChildren(QMenu):
        if child.title() == menu_title:
            return child

    menu = QMenu(menu_bar)
    menu.setObjectName(menu_title)
    menu.setTitle(menu_title)

    return menu


def recursively_set_menu_actions_visibility(menu: QMenu, state: bool):
    """
    Recursively sets the visible state of all actions of the given menu.

    :param QMenu menu: menu to edit actions visibility of.
    :param bool state: new visibility status.
    """

    for action in menu.actions():
        sub_menu = action.menu()
        if sub_menu:
            recursively_set_menu_actions_visibility(sub_menu, state)
        elif action.isSeparator():
            continue
        if action.isVisible() != state:
            action.setVisible(state)

    if any(action.isVisible() for action in menu.actions()) and menu.isVisible() != state:
        menu.menuAction().setVisible(state)


def get_window_menu_bar(window=None):
    """
    Returns menu bar of given window. If not given, DCC main window will be used
    :param window: QMainWindow
    :return: QMenuBar or None
    """

    window = window or dcc.main_window()
    if not window:
        return

    if hasattr(window, 'menuBar'):
        return window.menuBar()
    else:
        menu_bars = window.findChildren(QMenuBar)
        if not menu_bars:
            return None
        return menu_bars[0]


def force_window_menu_bar(window_instance):
    """
    Forces to add a menubar into a window if it does not exists
    :param window_instance:
    """

    menu = window_instance.menuBar()
    for child in menu.children():
        if isinstance(child, QMenu):
            break
    else:
        return

    menu.setSizePolicy(menu.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
    window_instance.centralWidget().layout().insertWidget(0, menu)


def desktop_pixmap_from_rect(rect):
    """
    Generates a pixmap of the application desktop in the given rect
    :param rect: QRect
    :return: QPixmap
    """

    desktop = QApplication.instance().desktop()

    return QPixmap.grabWindow(desktop.winId(), rect.x(), rect.y(), rect.width(), rect.height())


def screens_contains_point(point):
    """
    Returns whether given point is contained in current screen
    :param point: QPoint
    :return: bool
    """

    desktop = QApplication.desktop()
    for i in range(desktop.screenCount()):
        if desktop.geometry().contains(point):
            return True

    return False


def find_coordinates_inside_screen(x, y, width, height, padding=0):
    """
    Using information of position and size, find a location of a rectangle that is inside the screen
    :param x:
    :param y:
    :param width:
    :param height:
    :param padding:
    :return:
    """

    # Only support Windows for now
    if not os.name == 'nt':
        return x, y

    from tp.common.python import win32

    monitor_adjusted = [
        (x1, y1, x2 - width - padding, y2 - height - padding
         ) for x1, y1, x2, y2 in tuple(m[1] for m in win32.active_monitor_areas())]
    location_groups = tuple(zip(*monitor_adjusted))

    x_orig = x
    y_orig = y

    if monitor_adjusted:

        # Make sure window is within monitor bounds
        x_min = min(location_groups[0])
        x_max = max(location_groups[2])
        y_min = min(location_groups[1])
        y_max = max(location_groups[3])

        if x < x_min:
            x = x_min
        elif x > x_max:
            x = x_max
        if y < y_min:
            y = y_min
        elif y > y_max:
            y = y_max

        # Check offset to find closest monitor
        monitor_offsets = {}
        for monitor_location in monitor_adjusted:
            monitor_offsets[monitor_location] = 0
            x1, y1, x2, y2 = monitor_location
            if x < x1:
                monitor_offsets[monitor_location] += x1 - x
            elif x > x2:
                monitor_offsets[monitor_location] += x - x2
            if y < y1:
                monitor_offsets[monitor_location] += y1 - y
            elif y > y2:
                monitor_offsets[monitor_location] += y - y2

        # Check the window is correctly in the monitor
        x1, y1, x2, y2 = min(monitor_offsets.items(), key=lambda d: d[1])[0]
        if x < x1:
            x = x1
        elif x > x2:
            x = x2
        if y < y1:
            y = y1
        elif y > y2:
            y = y2

    # Reverse window padding if needed
    if x != x_orig:
        x -= padding
    if y != y_orig:
        y -= padding

    return x, y


def update_widget_style(widget: QWidget):
    """
    Updates object widget style. Should be called for example when a style name changes.

    :param QWidget widget: widget to update style of.
    """

    widget.setStyle(widget.style())


def update_widget_sizes(widget: QWidget):
    """
    Updates the given widget sizes.

    :param QWidget widget: widget to update sizes of.
    """

    if not widget:
        return
    widget_layout = widget.layout()
    if widget_layout:
        widget_layout.update()
        widget_layout.activate()


def set_stylesheet_object_name(widget, name, update=True):
    """
    Sets the widget to have a specific object name used by one the stylesheets.

    :param QWidget widget: widget we want to set object name.
    :param str name: stylesheet name for the widget.
    :param bool update: whether to force the update the style of the widget after setting up the stylesheet
        object name.
    """

    widget.setObjectName(name)
    if update:
        update_widget_style(widget)


def set_shadow_effect_enabled(widget: QWidget, flag: bool) -> QGraphicsDropShadowEffect | None:
    """
    Sets shadow effect for given widget.

    :param QWidget widget: widget to set shadow effect for.
    :param bool flag: whether to enable shadow effect.
    """

    shadow_effect = None
    if flag:
        shadow_effect = widget.property('shadowEffect')
        if shadow_effect is None:
            shadow_effect = QGraphicsDropShadowEffect(widget)
            widget.setProperty('shadowEffect', shadow_effect)
            shadow_effect.setBlurRadius(dpi.dpi_scale(8))
            shadow_effect.setColor(QColor(0, 0, 0, 150))
            shadow_effect.setOffset(dpi.dpi_scale(2))
        widget.setGraphicsEffect(shadow_effect)
    else:
        widget.setGraphicsEffect(None)

    return shadow_effect


def iterate_parents(widget):
    """
    Yields all parents of the given widget
    :param widget: QWidget
    :return:
    """

    parent = widget
    while True:
        parent = parent.parentWidget()
        if parent is None:
            break

        yield parent


def iterate_children(widget: QWidget, skip: str | None = None, qobj_class: type | None = None) -> Iterator[QWidget]:
    """
    Generator function that yields all descendant widgets depth first of the given widget.

    :param QWidget widget: widget to iterate through.
    :param str or None skip: if the widget has this property, children will be skipped.
    :param type qobj_class: optional class to filter widgets by.
    :return: iterated descendants widgets.
    :rtype: Iterator[QWidget]
    """

    for child in widget.children():
        yield child
        if skip is not None and child.property(skip):
            continue
        if qobj_class is not None and not isinstance(child, qobj_class):
            continue
        for grand_child in iterate_children(widget=child, skip=skip):
            yield grand_child


def is_stackable(widget):
    """
    Returns whether given widget is stackable
    :param widget: QWidget
    :return: bool
    """

    return issubclass(widget, QWidget) and hasattr(widget, 'widget') and hasattr(widget, 'currentChanged')


def get_current_screen(global_pos=None):
    """
    Returns current screen.

    :return: current screen.
    :rtype: QScreen
    """

    global_pos = global_pos if global_pos is not None else QApplication.desktop().cursor().pos()
    try:
        screen = QApplication.screenAt(global_pos)
    except Exception:
        screen_num = QApplication.desktop().screenNumber(global_pos)
        screen = QApplication.screens()[screen_num]

    return screen


def current_screen(global_pos: QPoint | None = None) -> QScreen:
    """
    Returns current screen instance.

    :return: current screen.
    :rtype: QScreen
    """

    global_pos = global_pos if global_pos is not None else QCursor.pos()
    return QGuiApplication.screenAt(global_pos)


def current_screen_geometry() -> QRect:
    """
    Returns the current screen geometry.

    :return: screen geometry.
    :rtype: QRect
    """

    screen = current_screen()
    return screen.geometry()


def available_screen_rect() -> QRect:
    """
    Returns the current screen rectangle.

    :return: screen rectangle.
    :rtype: QRect
    """

    desktop = QApplication.desktop()
    r = QRect()
    for i in range(desktop.screenCount()):
        r = r.united(desktop.availableGeometry(i))

    return r


def contain_widget_in_screen(widget: QWidget, pos: QPoint | None = None) -> QPoint:
    """
    Contains the position of the widget within the current screen.

    :param QWidget widget: widget to check.
    :param QPoint or None pos: point to check.
    :return: widget position within widget.
    :rtype: QPoint
    """

    if not pos:
        pos = widget.mapToGlobal(QPoint(0, 0))
    else:
        pos = QPoint(pos)
    geo = current_screen_geometry()
    pos.setX(min(max(geo.x(), pos.x()), geo.right() - widget.width()))
    pos.setY(min(max(geo.y(), pos.y()), geo.bottom() - widget.height()))

    return pos


def click_under(
        pos: QPoint, under: int = 1, button: Qt.MouseButton = Qt.LeftButton,
        modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier):
    """
    Clicks under the widget.

    :param QPoint pos: cursor position.
    :param int under: number of iterations under.
    :param Qt.Button button: button to simulate click with.
    :param Qt.KeyboardModifier modifier: modifier to simulate click with.
    """

    if not _QT_TEST_AVAILABLE:
        logger.warning('QtTest module is not available in current Qt version!')
        return

    widgets = get_widgets_at(pos)
    QtTest.QTest.mouseClick(widgets[under][0], button, modifier, widgets[under][1])


def single_shot_timer(func: Callable, time: int = 0):
    """
    Calls given callable in the given time.

    :param callable func: fucntion to execute when timer is completed.
    :param int time: timer time in milliseconds to run the function.
    """

    QTimer.singleShot(time, func)


def set_cursor(cursor):
    """
    Sets current Qt application cursor.

    :param Qt.CursorShape cursor: cursor shape.
    """

    QApplication.setOverrideCursor(cursor)


def restore_cursor():
    """
    Resets the cursor back to the default one.
    """

    QApplication.restoreOverrideCursor()
    single_shot_timer(QApplication.restoreOverrideCursor)


def get_screen_color(global_pos):
    """
    Grabs the screen color of the given global position in the current active screen
    :param global_pos: QPoint
    :return: QColor
    """

    screen_num = QApplication.desktop().screenNumber(global_pos)
    screen = QApplication.screens()[screen_num]
    wid = QApplication.desktop().winId()
    img = screen.grabWindow(wid, global_pos.x(), global_pos.y(), 1, 1).toImage()

    return QColor(img.pixel(0, 0))


def set_vertical_size_policy(widget, policy):
    """
    Sets the vertical policy of the given widget
    :param widget: QtWidgets.QWidget
    :param policy: QtWidgets.QSizePolicy, new polity to apply to vertical policy
    """

    size_policy = widget.sizePolicy()
    size_policy.setVerticalPolicy(policy)
    widget.setSizePolicy(size_policy)


def set_horizontal_size_policy(widget, policy):
    """
    Sets the horizontal policy of the given widget
    :param widget: QtWidgets.QWidget
    :param policy: QtWidgets.QSizePolicy, new polity to apply to horizontal policy
    """

    size_policy = widget.sizePolicy()
    size_policy.setHorizontalPolicy(policy)
    widget.setSizePolicy(size_policy)


def set_size_hint(widget, size):
    """
    Sets the size hint of the given widget (using a monkey-patch approach)
    :param widget: QtWidgets.QWidget
    :param size: QtCore.QSize
    """

    widget.sizeHint = lambda: size


def process_ui_events():
    """
    Processes all events currently in the application events queue
    """

    QApplication.processEvents()


def get_main_qt_window():
    """
    Returns QWidget representing the top most window
    :return: QWidget
    """

    parent = QApplication.activeWindow()
    grand_parent = parent
    while grand_parent is not None:
        parent = grand_parent
        grand_parent = parent.parent()

    return parent


def center_widget_on_screen(widget: QWidget):
    """
    Centers a given QWidget on the active screen.

    :param widget: QWidget
    """

    frame_geo = widget.frameGeometry()
    screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
    center_point = QApplication.desktop().screenGeometry(screen).center()
    frame_geo.moveCenter(center_point)
    widget.move(frame_geo.topLeft())


def center_window_on_screen(main_window: QMainWindow):
    """
    Centers given window to the center of primary screen.

    :param QMainWindow main_window: main window.
    """

    center_position = main_window.pos() + QApplication.primaryScreen().geometry().center() - main_window.geometry().center()
    main_window.move(center_position)


def restore_cursor():
    """
    Restores current Qt application cursor
    """

    QApplication.restoreOverrideCursor()


def set_wait_cursor(state=True):
    """
    Sets the wait cursor as the cursor for current Qt application
    """

    if state:
        QApplication.setOverrideCursor(Qt.WaitCursor)
    else:
        restore_cursor()


def set_current_directory(path):
    """
    Updates global current directory
    :param path: str, new current directory
    """

    global CURRENT_DIR
    if os.path.isdir(path):
        CURRENT_DIR = path
    elif os.path.isfile(path):
        CURRENT_DIR = os.path.dirname(path)


def get_save_filename(title='Save File', file_dir=None, ext_filter='*', parent=None):
    """
    Opens a save file dialog
    :param title: str
    :param file_dir: str
    :param ext_filter: str
    :param parent: QWidget
    :return: str, selected file path
    """

    file_dir = file_dir or CURRENT_DIR
    file_dialog = QFileDialog.getSaveFileName(parent, title, file_dir, ext_filter)
    file_path = file_dialog[0] or None
    if file_path:
        set_current_directory(file_path)

    return file_dialog


def get_open_filename(title='Open File', file_dir=None, ext_filter='*', parent=None):
    """
    Opens an open file dialog
    :param title: str
    :param file_dir: str
    :param ext_filter: str
    :param parent: QWidget
    :return: str, selected file path
    """

    file_dir = file_dir or CURRENT_DIR
    file_dialog = QFileDialog.getOpenFileName(parent, title, file_dir, ext_filter)
    file_path = file_dialog[0] or None
    if file_path:
        set_current_directory(file_path)

    return file_dialog


def safe_tree_widget_iterator(
        item: QTreeWidget | QTreeWidgetItemIterator,
        flags: QTreeWidgetItemIterator.IteratorFlags = QTreeWidgetItemIterator.All) -> Iterator[QTreeWidgetItem]:
    """
    Custom iterator that handles the incrementing of the iterator on each loop to avoid infinite loops.

    :param QTreeWidget or QTreeWidgetItemIterator item: item to iterate.
    :param QTreeWidgetItemIterator.IteratorFlags flags: tree widget iterator flags.
    :return: iterated tree widget items.
    :rtype: Iterator[QTreeWidgetItem]
    """

    iterator = QTreeWidgetItemIterator(item, flags)
    while iterator.value():
        yield iterator.value()
        iterator += 1
