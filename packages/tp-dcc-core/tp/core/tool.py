#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains classes to define Dcc tools
"""

from __future__ import annotations

import sys
import typing
import traceback
from typing import Iterator, Any
from dataclasses import dataclass, field

from Qt.QtCore import Signal

from tp.core import log
from tp.dcc import callback
from tp.common.python import helpers, decorators
from tp.common import plugin
from tp.common.qt import api as qt

if typing.TYPE_CHECKING:
    from tp.core.managers.tools import ToolsManager

logger = log.tpLogger


@dataclass()
class UiData:
    label: str = ''
    icon: str = ''
    tooltip: str = ''
    auto_link_properties: bool = False


@dataclass()
class UiProperty:
    name: str
    value: Any = None
    default: Any = None


@dataclass()
class UiPropertyGetSet:
    getter: str
    setter: str


@dataclass()
class UiPropertyWidgetUpdate:
    save_signal: str
    getsets: list[UiPropertyGetSet] = field(default_factory=lambda: [])
    skip_children: bool = True


SUPPORT_WIDGET_TYPES = {
    qt.ComboBoxRegularWidget: UiPropertyWidgetUpdate('itemChanged', [UiPropertyGetSet('current_index', 'set_index')]),
    qt.RadioButtonGroup: UiPropertyWidgetUpdate('toggled', [UiPropertyGetSet('checked_index', 'set_checked')]),
    qt.SearchLineEdit: UiPropertyWidgetUpdate('textChanged', [UiPropertyGetSet('text', 'setText')]),
    qt.BaseLineEdit: UiPropertyWidgetUpdate('textChanged', [UiPropertyGetSet('text', 'setText')]),
    qt.StringLineEditWidget: UiPropertyWidgetUpdate('textChanged', [UiPropertyGetSet('text', 'set_text')]),
    qt.FloatLineEditWidget: UiPropertyWidgetUpdate('textChanged', [UiPropertyGetSet('value', 'set_value')]),
    qt.IntLineEditWidget: UiPropertyWidgetUpdate('textChanged', [UiPropertyGetSet('value', 'set_value')]),
    qt.QLineEdit: UiPropertyWidgetUpdate('textChanged', [UiPropertyGetSet('text', 'setText')]),
    qt.QCheckBox: UiPropertyWidgetUpdate('toggled', [UiPropertyGetSet('isChecked', 'setChecked')])
}


class Tool(qt.QObject):
    """
    Base class used by tp-dcc-tools framework to implement DCC tools that have access to tp-dcc-tools functionality.
    """

    ID: str = ''

    closed = Signal()

    def __init__(self, factory: plugin.PluginFactory, tools_manager: ToolsManager):
        super(Tool, self).__init__()

        self._factory = factory
        self._stats = plugin.PluginStats(self)
        self._tools_manager = tools_manager
        self._widgets: list[qt.QWidget] = []
        self._properties: helpers.ObjectDict[str, UiProperty] = self.setup_properties()
        self._listeners: dict[str, callable] = {}
        self._stacked_widget: qt.QStackedWidget | None = None
        self._show_warnings: bool = True
        self._block_save: bool = False
        self._closed = False
        self._callbacks = callback.FnCallback()

    @decorators.classproperty
    def id(cls) -> str:
        """
        Getter method that returns the unique ID of the tool.

        :return: tool unique ID.
        :rtype: str
        """

        return ''

    @decorators.classproperty
    def creator(cls) -> str:
        """
        Getter method that returns the name of the creator of the tool.

        :return: tool creator name.
        :rtype: str
        """

        return 'Tomi Poveda'

    @decorators.classproperty
    def ui_data(cls) -> UiData:
        """
        Getter method that returns dictionary containing ui data info.

        :return: UI data dictionary.
        :rtype: UiData
        """

        return UiData()

    @decorators.classproperty
    def tags(cls) -> list[str]:
        """
        Getter method that returns list of tags for this tool.

        :return: list of tags to identify/search this tool with/by.
        :rtype: list[str]
        """

        return []

    @property
    def stats(self) -> plugin.PluginStats:
        """
        Getter method that returns the tool stats.

        :return: tool stats.
        :rtype: plugin.PluginStats
        """

        return self._stats

    @property
    def properties(self) -> helpers.ObjectDict:
        """
        Getter method that returns dictionary containing all available UI properties for this tool.

        :return: UI properties dictionary.
        :rtype: helpers.ObjectDict
        """

        return self._properties

    @property
    def callbacks(self) -> callback.FnCallback:
        """
        Returns callback function set used by this tool, which allows to register new callbacks.

        :return: callback function set.
        :rtype: callback.FnCallback
        """

        return self._callbacks

    @staticmethod
    def widget_property_name(widget: qt.QWidget) -> str:
        """
        Returns the name of the ui property that is linked to the widget.

        :param qt.QWidget widget: widget to get link property name from.
        :return: linked property name.
        :rtype: str
        """

        return widget.property('prop')

    def execute(self, *args, **kwargs):
        """
        Main function that runs tool.
        """

        win = qt.FramelessWindow()
        win.closed.connect(self.closed.emit)
        win.set_title(self.ui_data.label)
        self._stacked_widget = qt.QStackedWidget(parent=win)
        win.main_layout().addWidget(self._stacked_widget)

        self.pre_content_setup()

        for widget in self.contents():
            self._stacked_widget.addWidget(widget)
            self._widgets.append(widget)

        self.auto_link_properties()

        self.populate_widgets()
        self.post_content_setup()
        self.update_widgets_from_properties()
        self.save_properties()

        win.show()
        win.closed.connect(self._run_teardown)

        return win

    def widgets(self) -> list[qt.QWidget]:
        """
        Returns list of tool ui widgets.

        :return: list of widgets.
        :rtype: list[qt.QWidget]
        """

        return self._widgets

    def initialize_properties(self) -> list[UiProperty]:
        """
        Returns list of properties used by tool UI.

        :return: list of UI properties.
        :rtype: list[UiProperty]
        """

        return []

    def reset_properties(self, update_widgets: bool = True):
        """Resets all UI properties and optionally updates linked widgets with those values.

        :param bool update_widgets: whether to update widgets after resetting UI propreties.
        """

        for ui_property in self.properties.values():
            ui_property.value = ui_property.default

        if update_widgets:
            self.update_widgets_from_properties()

    def setup_properties(self, properties: helpers.ObjectDict | None = None) -> helpers.ObjectDict:
        """
        Initializes all UI properties.

        :param UiPropertiesDict or None properties: optional initial properties.
        :return: dictionary containing all UI properties.
        :rtype: UiPropertiesDict
        """

        properties = properties or self.initialize_properties()
        tool_properties = helpers.ObjectDict()
        for ui_property in properties:
            tool_properties[ui_property.name] = ui_property
            if ui_property.default is None:
                ui_property.default = ui_property.value

        return tool_properties

    def auto_link_properties(self):
        """
        Auto link UI properties to widgets if allowed.
        """

        if not self.ui_data.auto_link_properties:
            return

        new_properties: list[UiProperty] = []
        names: list[str] = []

        for name, widget in self.iterate_linkable_properties(self._stacked_widget):
            skip_children = SUPPORT_WIDGET_TYPES.get(type(widget)).skip_children
            widget.setProperty('skipChildren', skip_children)
            if not self.link_property(widget, name):
                continue
            if name not in names:
                new_property = UiProperty(name)
                widget_values = self.widget_values(widget)
                for k, v in widget_values.items():
                    setattr(new_property, k, v)
                new_properties.append(new_property)
                names.append(name)

        new_props = self.setup_properties(new_properties)
        self.properties.update(new_props)

        for ui_property in new_properties:
            for listener in self._listeners.get(ui_property.name, []):
                listener(ui_property.value)

    def link_property(self, widget: qt.QWidget, ui_property_name: str) -> bool:
        """
        Links given property to widget.

        :param qt.QWidget widget: widget property belongs to.
        :param str ui_property_name: name of the ui property to link to widget.
        :return: True if property link operation was successful; False otherwise.
        :rtype: bool
        """

        if self.widget_property_name(widget) is None:
            widget.setProperty('prop', ui_property_name)
            return True

        return False

    def iterate_linkable_properties(self, widget: qt.QWidget) -> Iterator[tuple[str, qt.QWidget]]:
        """
        Generator function that yields all properties from widgets children that can be linked to UI properties.
        Returns the name of the widget and its widget instance.

        :param qt.QWidget widget: widget to get linked properties from.
        :return: iterated linkable properties.
        :rtype: Iterator[tuple[str, qt.QWidget]]
        """

        for attr in widget.__dict__:
            if type(getattr(widget, attr)) in SUPPORT_WIDGET_TYPES:
                yield attr, getattr(widget, attr)

        children = widget.children()
        for child in children:
            for attr in child.__dict__:
                if type(getattr(child, attr)) in SUPPORT_WIDGET_TYPES:
                    yield attr, getattr(child, attr)
            for grandchild in self.iterate_linkable_properties(child):
                yield grandchild

    def populate_widgets(self):
        """
        Makes the connection for all widgets linked to UI properties.
        """

        property_widgets = self.property_widgets()
        for widget in property_widgets:
            modified = False
            widget_type = type(widget)
            widget_name = self.widget_property_name(widget)
            widget_info: UiPropertyWidgetUpdate | None = SUPPORT_WIDGET_TYPES.get(widget_type)
            if widget_info:
                signal = getattr(widget, widget_info.save_signal)
                signal.connect(self.save_properties)
                modified = True

            if not modified and self._show_warnings:
                logger.warning(f'Unsupported widget: {widget}. Property: {widget_name}')

    def property_widgets(self) -> list[qt.QWidget]:
        """
        Returns a list of property widgets added to this tool.

        :return: list of widgets that are linked to a UI property.
        :rtype: list[qt.QWidget]
        """

        found_widgets: list[qt.QWidget] = []
        for child in qt.iterate_children(self._stacked_widget, skip='skipChildren'):
            if child.property('prop') is not None:
                found_widgets.append(child)

        return found_widgets

    def widgets_linked_to_property(self, property_name: str) -> list[qt.QWidget]:
        """
        Returns all widgets that are linked to the property with given name.

        :param str property_name: name of the property to get linked widgets of.
        :return: list of widgets.
        :rtype: list[qt.QWidget]
        """

        found_widgets: list[qt.QWidget] = []
        for child in qt.iterate_children(self._stacked_widget, skip='skipChildren'):
            child_property = child.property('prop')
            if child_property is None or child_property != property_name:
                continue
            found_widgets.append(child)

        return found_widgets

    def update_widget(self, widget: qt.QWidget):
        """
        Update given widget based on its linked UI property value.

        :param qt.QWidget widget: widget to update.
        """

        modified = False
        widget_type = type(widget)
        widget_name = self.widget_property_name(widget)
        widget_info: UiPropertyWidgetUpdate | None = SUPPORT_WIDGET_TYPES.get(widget_type)
        if widget_info:
            for i, getset in enumerate(widget_info.getsets):
                prop = 'value' if i == 0 else getset.getter
                value = getattr(self.properties[widget_name], prop)
                setter = getattr(widget, getset.setter)
                try:
                    setter(value)
                except TypeError as err:
                    raise TypeError(
                        f'Unable to set widget attribute method: {widget_name}; property: {getset.setter}; '
                        f'value: {value}: {err}')
                modified = True
        if not modified and self._show_warnings:
            logger.warning(f'Unsupported widget: {widget}. Property: {widget_name}')

    def update_widget_from_property(self, ui_property_name: str):
        """
        Updates widgets that are linked to property with given name.

        :param str ui_property_name: name of the UI property to update.
        """

        self._stacked_widget.setUpdatesEnabled(False)
        self._block_save = True

        property_widgets = self.widgets_linked_to_property(ui_property_name)
        for widget in property_widgets:
            self.update_widget(widget)
        for widget in property_widgets:
            widget.blockSignals(False)

        self._block_save = False
        self._stacked_widget.setUpdatesEnabled(True)

    def update_widgets_from_properties(self):
        """
        Updates all widgets to current linked property internal value.
        """

        # self.block_callbacks(True)
        self._block_save = True
        self._stacked_widget.setUpdatesEnabled(False)

        property_widgets = self.property_widgets()
        for widget in property_widgets:
            self.update_widget(widget)
        for widget in property_widgets:
            widget.blockSignals(False)

        self._stacked_widget.setUpdatesEnabled(True)
        self._block_save = False
        # self.block_callbacks(False)

    def widget_values(self, widget: qt.QWidget) -> dict[str, UiProperty]:
        """
        Returns the value of the widget based of its type.

        :param qt.QWidget widget: widget we want to return value of.
        :return:
        """

        widget_type = type(widget)
        widget_name = self.widget_property_name(widget)
        widget_info: UiPropertyWidgetUpdate | None = SUPPORT_WIDGET_TYPES.get(widget_type)
        if widget_info:
            result: dict[str, Any] = {}
            for i, getset in enumerate(widget_info.getsets):
                prop = 'value' if i == 0 else getset.getter
                result[prop] = getattr(widget, getset.getter)()

            extra_properties: dict = {}
            if isinstance(widget.property('extraProperties'), dict):
                extra_properties.update(widget.property('extraProperties'))
            for k, v in extra_properties.items():
                result[k] = getattr(widget, v)()

            return result

        if self._show_warnings:
            logger.warning(f'Unsupported widget: {widget}. Property: {widget_name}')

        return {}

    def save_properties(self):
        """
        Saves the properties from the widget into the internal UI attributes.
        """

        if self._block_save:
            return

        property_widgets = self.property_widgets()
        for widget in property_widgets:
            property_name = self.widget_property_name(widget)
            widget_values = self.widget_values(widget)
            for k, v in widget_values.items():
                setattr(self.properties[property_name], k, v)
            for listener in self._listeners.get(property_name, []):
                for k, v in widget_values.items():
                    if k == 'value':
                        listener(v)

    def update_property(self, ui_property_name: str, value: Any):
        """
        Updates UI property value with given one.
        Forces the update of all linked widgets.

        :param str ui_property_name: UI property to update value of.
        :param Any value: new property value.
        """

        if ui_property_name not in self.properties:
            return
        self.properties[ui_property_name].value = value

        self.update_widget_from_property(ui_property_name)

        for listener in self._listeners.get(ui_property_name, []):
            listener(value)

    def listen(self, ui_property_name: str, listener: callable):
        """
        Registers a listener for the given UI property name.

        :param str ui_property_name: UI property name to listen for changes.
        :param Callable listener: function that will be called when UI property internal value is updated.
        """

        self._listeners[ui_property_name] = self._listeners.get(ui_property_name, []) + [listener]

    def pre_content_setup(self):
        """
        Function that is called before tool UI is created.
        Can be override in tool subclasses.
        """

        pass

    def contents(self) -> list[qt.QWidget]:
        """
        Function that returns tool widgets.
        """

        return []

    def post_content_setup(self):
        """
        Function that is called after tool UI is created.
        Can be override in tool subclasses.
        """

        pass

    def teardown(self):
        """
        Function that shutdown tool.
        """

        self._callbacks.clear()

    def set_stylesheet(self, style):
        pass

    def run(self):
        pass

    def _execute(self, *args, **kwargs) -> Tool:
        """
        Internal function that executes tool in a safe way.
        """

        self.stats.start()
        exc_type, exc_value, exc_tb = None, None, None
        try:
            self.execute(*args, **kwargs)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            raise
        finally:
            tb = None
            if exc_type and exc_value and exc_tb:
                tb = traceback.format_exception(exc_type, exc_value, exc_tb)
            self.stats.finish(tb)

        return self

    def _run_teardown(self):
        """
        Internal function that tries to tear down the tool in a safe way.
        """

        if self._closed:
            logger.warning(f'Tool f"{self}" already closed')
            return

        try:
            self.teardown()
            self._closed = True
        except RuntimeError:
            logger.error(f'Failed to teardown tool: {self.id}', exc_info=True)
