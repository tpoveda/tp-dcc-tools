from __future__ import annotations

import os
import copy
import typing
import inspect
from typing import List, Dict

from tp.core import log
from tp.common.python import decorators, yamlio
from tp.common import plugin
from tp.preferences.interfaces import crit

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.core import errors, component
from tp.libs.rig.crit.descriptors import component as descriptor_component

logger = log.rigLogger

if typing.TYPE_CHECKING:
    from tp.common.plugin import PluginFactory
    from tp.libs.rig.crit.core.rig import Rig
    from tp.libs.rig.crit.meta.component import CritComponent


@decorators.add_metaclass(decorators.Singleton)
class ComponentsManager:
    """
    Singleton class that manages and registers a collection of component classes. This class handles the creation and
    returning of component instances and descriptors.
    """

    def __init__(self):
        super(ComponentsManager, self).__init__()

        self._components = {}
        self._descriptors = {}
        self._manager = None										# type: PluginFactory
        self._preferences_interface = crit.crit_interface()

    @property
    def components(self) -> Dict:
        return self._components

    @property
    def descriptors(self) -> Dict:
        return self._descriptors

    def refresh(self):
        """
        Refreshes registered components by clearing the manager and rediscovering the components again.
        """

        self._components.clear()
        self._descriptors.clear()
        self._manager = plugin.PluginFactory(
            interface=component.Component, plugin_id='ID', name='CritComponentManager')

        self.discover_components()

    def discover_components(self):
        """
        Searches the component library based on the environment variable CRIT_COMPONENTS_PATHS
        """

        self._manager.register_paths_from_env_var(consts.COMPONENTS_ENV_VAR_KEY, package_name='crit')
        component_paths = self._preferences_interface.user_components_paths()
        self._manager.register_paths(component_paths, package_name='crit')
        descriptor_paths = os.environ.get(consts.DESCRIPTORS_ENV_VAR_KEY, '').split(os.pathsep)
        for descriptor_path in descriptor_paths + component_paths:
            for root, dirs, files in os.walk(descriptor_path):
                for file_name in files:
                    if not file_name.endswith(consts.DESCRIPTOR_EXTENSION):
                        continue
                    descriptor_base_name = file_name.split(os.extsep)[0]
                    if descriptor_base_name in self._descriptors:
                        continue
                    descriptor_path = os.path.join(root, file_name)
                    cache = self._load_descriptor_from_path(descriptor_path)
                    self._descriptors[cache['type']] = {'path': descriptor_path, 'data': cache}

        for class_obj in self._manager.plugins('crit'):
            class_id = class_obj.ID if hasattr(class_obj, 'ID') else None
            if not class_id:
                class_obj.ID = class_obj.__name__
                class_id = class_obj.ID
            class_path = inspect.getfile(class_obj)
            if class_id in self._components:
                continue
            self._components[class_id] = {
                'object': class_obj,
                'path': class_path,
                'descriptor': class_id
            }

    def components_paths(self) -> List[str]:
        """
        Returns all registered components paths.

        :return: list of paths.
        :rtype: List(str)
        """

        return self._manager.paths('crit')

    def component_data(self, component_type: str) -> Dict | None:
        """
        Returns the component data stored within manager.

        :param str component_type: component type to get data of.
        :return: component data {'object': ...', 'path': str, 'descriptor': str}
        :rtype: Dict or None
        """

        return self._components.get(component_type)

    def load_component_descriptor(self, component_type: str) -> Dict:
        """
        Loads teh descriptor file for the component of the given type already registered.

        :param str component_type: component type to load.
        :return: component data loaded from component descriptor file.
        :rtype: Dict
        :raises ValueError: if component with given type is not already registered.
        """

        if component_type not in self._descriptors:
            raise ValueError(
                'Requested Component is not available. Requested: {}; Available: {}'.format(
                    component_type, self._descriptors.keys()))

        try:
            descriptor_data = self._descriptors[self._components[component_type]['descriptor']]
            return copy.deepcopy(descriptor_data['data'])
        except ValueError:
            logger.error(f'Failed to load component descriptor: {component_type}', exc_info=True)
            raise ValueError(f'Failed to load component descriptor: {component_type}')

    def initialize_component_descriptor(self, component_type: str) -> descriptor_component.ComponentDescriptor | None:
        """
        Initializes the component descriptor of given type.

        :param str component_type: component type to initialize.
        :return: initialized component descriptor.
        :rtype: descriptor_component.ComponentDescriptor or None
        """

        descriptor_data = self.load_component_descriptor(component_type)
        component_data = self.component_data(component_type)
        if not descriptor_data:
            logger.error(
                f'Was not possible to initialize component descriptor for "{component_type}". No descriptor data found')
            return None
        if not component_data:
            logger.error(
                f'Was not possible to initialize component descriptor for "{component_type}". No component data found')
            return None

        return descriptor_component.load_descriptor(descriptor_data, descriptor_data, path=component_data.get('path'))

    def find_component_by_type(self, component_type: str):
        """
        Finds and returns the component class from the manager.

        :param str component_type: component type to find and return.
        :return: found component class of given type.
        :rtype: tp.rigtoolkit.crit.lib.maya.core.component.Component or None
        :raises ValueError: if component with given type was not found.
        """

        try:
            return self._components[component_type]['object']
        except KeyError:
            raise ValueError(
                'Component requested is not available. Requested: {}; Available: {}'.format(
                    component_type, self._components.keys()))

    def from_meta_node(self, rig: Rig, meta: CritComponent) -> component.Component:
        """
        Creates a new component instance and attaches it to given rig.

        :param Rig rig: rig to which the new component will be attached.
        :param CritComponent meta: metadata for the new component.
        :return: new component initialized with the given metadata.
        :rtype: component.Component
        :raises errors.CritMissingRootTransform: if the given metadata does not have a root transform.
        """

        root = meta.root_transform()
        if not root:
            raise errors.CritMissingRootTransform(meta.fullPathName())

        component_type = meta.attribute(consts.CRIT_COMPONENT_TYPE_ATTR).asString()
        new_component = self.find_component_by_type(component_type)
        new_component = new_component(rig, meta=meta)

        return new_component

    def _load_descriptor_from_path(self, descriptor_path: str) -> Dict | None:
        """
        Internal function that tries to load a component descriptor from given path.

        :param str descriptor_path: absolute file path pointing to a descriptor file.
        :return: descriptor contents or None if the descriptor is not valid.
        :rtype: Dict or None
        """

        try:
            return yamlio.read_file(descriptor_path)
        except ValueError:
            logger.error(f'Failed to load component descriptor: {descriptor_path}', exc_info=True)
            raise ValueError(f'Failed to load component descriptor: {descriptor_path}')
