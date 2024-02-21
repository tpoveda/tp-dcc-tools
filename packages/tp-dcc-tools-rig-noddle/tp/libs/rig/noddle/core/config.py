from __future__ import annotations

import typing

from tp.common.python import strings
from tp.maya.cmds import helpers as maya_helpers
from tp.preferences.interfaces import noddle
from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.core import namingpresets, components

if typing.TYPE_CHECKING:
    from tp.common.naming.manager import NameManager
    from tp.libs.rig.noddle.core.rig import Rig
    from tp.libs.rig.noddle.descriptors.component import ComponentDescriptor


def initialize_naming_preset_manager(preference_interface, reload: bool = False):
    """
    Initializes Naming preset manager.

    :param preference_interface: Noddle preference interface instance.
    :param bool reload: whether to force reload of the naming preset manager if it is already initialized
    """

    if reload or Configuration.NAMING_PRESET_MANAGER is None:
        presets_manager = namingpresets.PresetsManager()
        hierarchy = preference_interface.naming_preset_hierarchy()
        presets_manager.load_from_hierarchy(hierarchy)
        Configuration.NAMING_PRESET_MANAGER = presets_manager


def initialize_components_manager(reload: bool = False):
    """
    Initializes Noddle components manager.

    :param bool reload: whether to force reload of components manager if it is already initialized
    """

    if reload or Configuration.COMPONENTS_MANAGER is None:
        components_manager = components.ComponentsManager()
        components_manager.refresh()
        Configuration.COMPONENTS_MANAGER = components_manager


class Configuration:
    """
    Class that handles Noddle configuration.
    This configuration handles lot of different rig related data that can be retrieved from a file in disk or from
    metadata from a node within a scene.
    """

    NAMING_PRESET_MANAGER: namingpresets.PresetsManager | None = None
    COMPONENTS_MANAGER: components.ComponentsManager | None = None

    def __init__(self):
        super().__init__()

        self._config_cache: dict = {}
        self._current_naming_preset: namingpresets.Preset | None = None
        self._preferences_interface = noddle.noddle_interface()

        self._use_proxy_attributes = True
        self._use_containers = False
        self._blackbox = False
        self._selection_child_highlighting = False
        self._auto_align_guides = True
        self._guide_control_visibility = False
        self._guide_pivot_visibility = True
        self._ignore_existing_constraints_on_skeleton_attachment = False

        self._initialize_managers()
        self._initialize_environment()

    @classmethod
    def name_presets_manager(cls) -> namingpresets.PresetsManager:
        """
        Returns the naming presets manager used by this configuration.

        :return: naming presets manager.
        :rtype: namingpresets.PresetsManager
        """

        return cls.NAMING_PRESET_MANAGER

    @classmethod
    def components_manager(cls) -> components.ComponentsManager:
        """
        Returns the current component manager instance.

        :return: components manager instance.
        :rtype: components.ComponentsManager
        """

        return cls.COMPONENTS_MANAGER

    @property
    def preferences_interface(self):
        """
        Returns Noddle preferences interface instance.

        :return: Noddle preferences interface.
        :rtype: NoddlePreferenceInterface
        """

        return self._preferences_interface

    @property
    def current_naming_preset(self) -> namingpresets.Preset | None:
        """
        Returns current naming preset.

        :return: naming preset.
        :rtype: namingpresets.Preset or None
        """

        return self._current_naming_preset

    @property
    def use_containers(self) -> bool:
        """
        Returns whether component asset container should be created.

        :return: True to create containers; False otherwise.
        :rtype: bool
        """

        return self._use_containers

    @use_containers.setter
    def use_containers(self, flag: bool):
        """
        Sets whether component asset container should be created.

        :param bool flag: True to enable asset container; False otherwise.
        """

        self._use_containers = flag

    @property
    def blackbox(self) -> bool:
        """
        Returns whether component asset container should be black boxed.

        :return: True if component asset container should be black boxed; False otherwise.
        :rtype: bool
        """

        return self._blackbox

    @property
    def selection_child_highlighting(self) -> bool:
        """
        Returns whether selection child highlighting should be enabled when building rig controls.

        :return: True if selection child highlighting feature should be enabled; False otherwise.
        :rtype: bool
        """

        return self._selection_child_highlighting

    @selection_child_highlighting.setter
    def selection_child_highlighting(self, flag: bool):
        """
        Sets whether selection child highlighting should be enabled.

        :param bool flag: True to enable child highlighting; False to disable it.
        """

        self._selection_child_highlighting = flag

    @property
    def auto_align_guides(self) -> bool:
        """
        Returns whether auto alignment should be run when building the skeleton layer.

        :return: True if guides auto alignment should be run; False otherwise.
        :rtype: bool
        """

        return self._auto_align_guides

    @auto_align_guides.setter
    def auto_align_guides(self, flag: bool):
        """
        Sets whether auto alignment should be run when building the skeleton layer.

        :param bool flag: True to enable auto align guide feature; False to disable it.
        """

        self._auto_align_guides = flag

    @property
    def guide_control_visibility(self) -> bool:
        """
        Returns whether guide controls are visible.

        :return: True if guide controls are visible; False otherwise.
        :rtype: bool
        """

        return self._guide_control_visibility

    @guide_control_visibility.setter
    def guide_control_visibility(self, flag: bool):
        """
        Sets whether guide controls are visible.

        :param bool flag: True if guide controls are visible; False otherwise.
        """

        self._guide_control_visibility = flag

    @property
    def guide_pivot_visibility(self) -> bool:
        """
        Returns whether guide pivot is visible.

        :return: True if guide pivot is visible; False otherwise.
        :rtype: bool
        """

        return self._guide_pivot_visibility

    @guide_pivot_visibility.setter
    def guide_pivot_visibility(self, flag: bool):
        """
        Sets whether guide pivot is visible.

        :param bool flag: True if guide pivot is visible; False otherwise.
        """

        self._guide_pivot_visibility = flag

    @property
    def ignore_existing_constraints_on_skeleton_attachment(self) -> bool:
        """
        Returns whether ignore constraints when attaching components to rig skeleton.

        :return: True if constraints should be ignored while attaching components to rig skeleton; False otherwise.
        :rtype: bool
        """

        return self._ignore_existing_constraints_on_skeleton_attachment

    def update_from_cache(self, cache: dict, rig: Rig | None = None):
        """
        Updates this configuration from the given configuration dictionary.

        :param dict cache: configuration dictionary to update this configuration from.
        :param Rig or None rig: optional rig this configuration belongs to.
        """

        pass

    def update_from_rig(self, rig: Rig) -> dict:
        """
        Updates this configuration from the given scene rig instance.

        :param Rig rig: rig instance to pull configuration data from.
        :return: updated configuration dictionary.
        :rtype: dict
        """

        cache = rig.cached_configuration()
        self.update_from_cache(cache)
        return cache

    def serialize(self, rig: Rig) -> dict:
        """
        Serializes current configuration data.

        :param Rig rig: rig this configuration belongs to.
        :return: serialized data.
        :rtype: dict
        """

        cache = self._config_cache
        overrides = {}

        for setting in ('useProxyAttributes',
                        'useContainers',
                        'blackBox',
                        'requiredMayaPlugins',
                        'selectionChildHighlighting',
                        'autoAlignGuides',
                        'guidePivotVisibility',
                        'guideControlVisibility',
                        'hideControlShapesInOutliner'):
            config_state = cache.get(setting)
            current_state = None
            if hasattr(self, setting):
                current_state = getattr(self, setting)
            elif hasattr(self, strings.camel_case_to_snake_case(setting)):
                current_state = getattr(self, strings.camel_case_to_snake_case(setting))
            if current_state is not None and current_state != config_state:
                overrides[setting] = current_state

        # for build_script in self._build_scripts:
        #     properties = build_script_config.get(build_script.ID, {})
        #     overrides.setdefault('buildScripts', []).append([build_script.ID, properties])

        if self._current_naming_preset.name != consts.DEFAULT_BUILTIN_PRESET_NAME:
            overrides[consts.NAMING_PRESET_DESCRIPTOR_KEY] = self._current_naming_preset.name

        return overrides

    def find_name_manager_for_type(self, noddle_type: str, preset_name: str | None = None) -> NameManager | None:
        """
        Finds and returns the naming convention manager used to handle the nomenclature for the given type.

        :param str noddle_type: Noddle type to search for ('rig', 'module', etc).
        :param str or None preset_name: optional preset to use find the Noddle type.
        :return: naming manager instance.
        :rtype: NameManager or None
        """

        preset = self._current_naming_preset
        if preset_name:
            preset = self.NAMING_PRESET_MANAGER.find_preset(preset_name)

        return preset.find_name_manager_for_type(noddle_type)

    def set_naming_preset_by_name(self, name: str):
        """
        Sets the current naming convention preset by the given name.

        :param str name: name of the preset to set as active.
        """

        preset = self.NAMING_PRESET_MANAGER.find_preset(name)
        if preset is None:
            preset = self.NAMING_PRESET_MANAGER.find_preset(consts.DEFAULT_PRESET_NAME)

        self._current_naming_preset = preset

    def components_paths(self):
        """
        Returns all current registered components paths.

        :return: list of paths.
        :rtype: list(str)
        """

        return self.COMPONENTS_MANAGER.components_paths()

    def initialize_component_descriptor(self, component_type: str) -> ComponentDescriptor:
        """
        Initializes the component descriptor of given type.

        :param str component_type: component type (which is the class name of the component to create).
        :return: initialized component descriptor.
        :rtype: ComponentDescriptor
        """

        return self.COMPONENTS_MANAGER.initialize_component_descriptor(component_type)

    def _initialize_managers(self, force: bool = False):
        """
        Internal function handles the initialization of all the configuration managers.

        :param bool force: whether to force the reloading of the managers.
        """

        initialize_components_manager(reload=force)
        initialize_naming_preset_manager(self._preferences_interface, reload=force)

    def _initialize_environment(self):
        """
        Internal function that handles the loading and setup of Noddle preferences from settings.
        """

        self.set_naming_preset_by_name(self._config_cache.get('defaultNamingPreset', consts.DEFAULT_PRESET_NAME))

        for plugin_required in self._config_cache.get('requiredMayaPlugins', []):
            maya_helpers.load_plugin(plugin_required)
