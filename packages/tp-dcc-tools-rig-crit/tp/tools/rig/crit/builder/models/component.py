from __future__ import annotations

import typing
from typing import List

from tp.common.qt import api as qt
from tp.commands import crit

from tp.tools.rig.crit.builder.views import componentstree

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.core.component import Component
    from tp.tools.rig.crit.builder.models.rig import RigModel


class ComponentModel(qt.QObject):

    component_type = ''

    def __init__(self, component: Component | None = None, rig_model: RigModel | None = None):
        super().__init__()

        self._component = component
        self._rig_model = rig_model
        self._hidden = False

    @property
    def component(self) -> Component:
        return self._component

    @component.setter
    def component(self, value: Component):
        self._component = value

    @property
    def rig_model(self) -> RigModel:
        return self._rig_model

    @rig_model.setter
    def rig_model(self, value: RigModel):
        self._rig_model = value

    @property
    def name(self) -> str:
        return self._component.name()

    @name.setter
    def name(self, value: str):
        if self._component.name() == str(value):
            return
        crit.rename_component(self._component, value)

    @property
    def side(self) -> str:
        return self._component.side()

    @side.setter
    def side(self, value: str):
        if self._component.side() == str(value):
            return
        crit.set_component_side(self._component, value)

    @property
    def icon(self) -> str:
        return self._component.ICON

    @property
    def enabled(self) -> bool:
        return self._component.is_enabled()

    @enabled.setter
    def enabled(self, flag: bool):
        pass

    def display_name(self) -> str:
        """
        Returns component model display name.

        :return: display name.
        :rtype: str
        """

        return ' '.join((self.name, self.side))

    def is_hidden(self) -> bool:
        """
        Returns whether component is hidden in the scene.

        :return: True if component is hidden; False otherwise.
        :rtype: bool
        """

        return self._component.is_hidden()

    def has_children(self) -> bool:
        """
        Returns whether this component has children components attached to it.

        :return: True if component has children; False otherwise.
        :rtype: bool
        """

        return bool(list(self._component.iterate_children()))

    def has_guide(self) -> bool:
        """
        Returns whether this component guides are built.

        :return: True if component guides are built; False otherwise.
        :rtype: bool
        """

        return self._component.has_guide()

    def has_rig(self) -> bool:
        """
        Returns whether this component rig is built.

        :return: True if component rig is built; False otherwise.
        :rtype: bool
        """

        return self._component.has_rig()

    def menu_actions(self) -> List[str]:
        """
        Returns a list of command UI action IDs that will be added into the component widget context menu.

        :return: list of command UI IDs.
        :rtype: List[str]
        """

        return [
            'selectInScene', '---',
            'toggleBlackToggle', '---',
            'toggleLra', '---',
            'duplicateComponent',
            'mirrorComponents',
            'applySymmetry', '---',
            'deleteComponent']

    def create_widget(
            self, component_widget: componentstree.ComponentsTreeWidget.ComponentWidget,
            parent_widget: qt.QWidget) -> componentstree.ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget:
        """
        Creates a new settings widget for this component.

        :param componentstree.ComponentsTreeWidget.ComponentWidget component_widget: component widget this settings will
            be added to.
        :param qt.QWidget parent_widget: parent widget instance.
        :return: componentstree.ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget
        """

        return componentstree.ComponentsTreeWidget.ComponentWidget.ComponentSettingWidget(
            component_widget, component_model=self, parent=parent_widget)
