from __future__ import annotations

import os
import typing

from tp.core import log
from tp.common import plugin
from tp.common.python import helpers, strings
from tp.preferences.interfaces import crit
from tp.maya.cmds import helpers as maya_helpers

from tp.libs.rig.crit import consts
from tp.libs.rig.crit.core import namingpresets, components, buildscript, templates, exporter

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.core.rig import Rig
    from tp.libs.rig.crit.descriptors.component import ComponentDescriptor

logger = log.rigLogger


def initialize_naming_preset_manager(preference_interface, reload: bool = False):
    """
    Initializes Naming preset manager.

    :param preference_interface: CRIT preference interface instance.
    :param bool reload: whether to force reload of the naming preset manager if it is already initialized
    """

    if reload or Configuration.NAMING_PRESET_MANAGER is None:
        presets_manager = namingpresets.PresetsManager()
        hierarchy = preference_interface.naming_preset_hierarchy()
        presets_manager.load_from_hierarchy(hierarchy)
        Configuration.NAMING_PRESET_MANAGER = presets_manager


def initialize_template_manager(reload: bool = False):
    """
    Initializes CRIT templates manager.

    :param bool reload: whether to force reload of the templates manager if it is already initialized
    """

    if reload or Configuration.TEMPLATES_MANAGER is None:
        templates_manager = templates.TemplatesManager()
        templates_manager.discover_templates()
        Configuration.TEMPLATES_MANAGER = templates_manager


def initialize_components_manager(reload: bool = False):
    """
    Initializes CRIT components manager.

    :param bool reload: whether to force reload of components manager if it is already initialized
    """

    if reload or Configuration.COMPONENTS_MANAGER is None:
        components_manager = components.ComponentsManager()
        components_manager.refresh()
        Configuration.COMPONENTS_MANAGER = components_manager


def initialize_build_scripts_manager(preference_interface, reload: bool = False):
    """
    Initializes CRIT build scripts manager.

    :param preference_interface: CRIT preference interface instance.
    :param bool reload: whether to force reload of the naming preset manager if it is already initialized
    """

    if reload or Configuration.BUILD_SCRIPTS_MANAGER is None:
        build_scripts_manager = plugin.PluginFactory(
            interface=buildscript.BaseBuildScript, plugin_id='ID', package_name='crit')
        paths = os.getenv(Configuration.BUILD_SCRIPTS_VAR, '').split(os.pathsep)
        paths += preference_interface.user_build_script_paths()
        helpers.add_to_environment('TPDCC_BASE_PATHS', paths)
        build_scripts_manager.register_paths_from_env_var(Configuration.BUILD_SCRIPTS_VAR, package_name='crit')
        build_scripts_manager.register_paths(preference_interface.user_build_script_paths(), package_name='crit')
        build_scripts_manager.load_all_plugins(package_name='crit')
        Configuration.BUILD_SCRIPTS_MANAGER = build_scripts_manager


def initialize_exporter_registry(preference_interface, reload: bool = False):
    """
    Initializes CRIT exporter manager.

    :param preference_interface: CRIT preference interface instance.
    :param bool reload: whether to force reload of the exporter manager if it is already initialized
    """

    if reload or Configuration.EXPORTER_MANAGER is None:
        exporter_manager = plugin.PluginFactory(interface=exporter.ExporterPlugin, plugin_id='ID', package_name='crit')
        exporter_manager.register_paths_from_env_var(Configuration.EXPORT_PLUGIN_VAR, package_name='crit')
        exporter_manager.register_paths(preference_interface.exporter_plugin_paths(), package_name='crit')
        Configuration.EXPORTER_MANAGER = exporter_manager


class Configuration:
    """
    Class that handles CRIT configuration.
    This configuration handles lot of different rig related data that can be retrieved from a file in disk or from
    metadata from a node within a scene.
    """

    BUILD_SCRIPTS_VAR = 'CRIT_BUILD_SCRIPTS_PATH'
    EXPORT_PLUGIN_VAR = 'CRIT_EXPORT_PLUGIN_PATH'

    NAMING_PRESET_MANAGER: namingpresets.PresetsManager | None = None
    COMPONENTS_MANAGER: components.ComponentsManager | None = None
    TEMPLATES_MANAGER: templates.TemplatesManager | None = None
    BUILD_SCRIPTS_MANAGER: plugin.PluginFactory | None = None
    EXPORTER_MANAGER: plugin.PluginFactory | None = None

    def __init__(self):
        super().__init__()

        self._config_cache: dict = {}
        self._current_naming_preset: namingpresets.Preset | None = None
        self._build_scripts: list[buildscript.BaseBuildScript] = []
        self._selection_child_highlighting = False
        self._auto_align_guides = True
        self._delete_on_fail = False
        self._preferences_interface = crit.crit_interface()
        self._single_chain_hierarchy = True
        self._guide_control_visibility = False
        self._guide_pivot_visibility = True
        self._build_skeleton_marking_menu = False
        self._guide_scale = 1.0
        self._control_scale = 1.0
        self._use_proxy_attributes = True
        self._use_containers = False
        self._blackbox = False
        self._hide_control_shapes_in_outliner = True
        self._export_plugin_overrides = self._preferences_interface.exporter_plugin_overrides()

        self._initialize_managers()
        self._initialize_environment()

    @staticmethod
    def build_script_config(rig: Rig) -> dict:
        """
        Returns the build scripts configuration data for given rig.

        :param Rig rig: rig we want to get build script config of.
        :return: build scripts configuration data.
        :rtype: dict
        """

        return rig.meta.build_script_configuration()

    @staticmethod
    def update_build_script_config(rig: Rig, config: dict[str, dict]):
        """
        Updates rig build scripts from given configuration.

        :param Rig rig: rig instance we want to update build scripts from.
        :param dict[str, dict] config: build scripts data to update.
        """

        current_config = rig.meta.build_script_configuration()
        current_config.update(config)
        rig.meta.set_build_script_configuration(current_config)

    @staticmethod
    def set_build_script_config(rig: Rig, config: dict[str, dict]):
        """
        Sets the build script configuration on the given rig.

        :param Rig rig: rig instance to set build scripts of.
        :param dict[str, dict] config: configuration data for any/all build scripts for the current rig.
        """

        rig.meta.set_build_script_configuration(config)

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

    @classmethod
    def templates_manager(cls) -> templates.TemplatesManager:
        """
        Returns the templates manager used by this configuration.

        :return: templates manager.
        :rtype: templates.TemplatesManager
        """

        return cls.TEMPLATES_MANAGER

    @property
    def preferences_interface(self):
        """
        Returns CRIT preferences interface instance.

        :return: CRIT preferences interface.
        :rtype: CritPreferenceInterface
        """

        return self._preferences_interface

    @property
    def delete_on_fail(self) -> bool:
        """
        Returns whether a component should be automatically deleted if it fails to build.

        :return: True if this feature is enabled; False otherwise.
        :rtype: bool
        """

        return self._delete_on_fail

    @property
    def current_naming_preset(self) -> namingpresets.Preset | None:
        """
        Returns current naming preset.

        :return: naming preset.
        :rtype: namingpresets.Preset or None
        """

        return self._current_naming_preset

    @property
    def build_scripts(self) -> list[buildscript.BaseBuildScript]:
        """
        Returns list of directories or Python file paths which can be run during build time.

        :return: list of build script absolute paths.
        :rtype: list[buildscript.BaseBuildScript]
        """

        return self._build_scripts

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
    def single_chain_hierarchy(self) -> bool:
        """
        Returns whether skeleton will be created under a unique chain hierarchy (so it is suitable for games).

        :return: True if skeleton will be created under a unique chain hierarchy; False otherwise.
        :rtype: bool
        """

        return self._single_chain_hierarchy

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
    def build_skeleton_marking_menu(self) -> bool:
        """
        Returns whether skeleton custom marking menu should be created.

        :return: True if skeleton custom marking menu should be created; False otherwise.
        :rtype: bool
        """

        return self._build_skeleton_marking_menu

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

    def update_from_cache(self, cache: dict, rig: Rig | None = None):
        """
        Updates this configuration from the given configuration dictionary.

        :param dict cache: configuration dictionary to update this configuration from.
        :param Rig or None rig: optional rig this configuration belongs to.
        """

        if rig is not None:
            blackbox = cache.get('blackBox')
            if blackbox is not None:
                rig.blackBox = blackbox
            guide_controls_visibility = cache.get('guideControlVisibility')
            guide_pivot_visibility = cache.get('guidePivotVisibility')
            if guide_controls_visibility is not None or guide_pivot_visibility is not None:
                control_state = -1 if guide_controls_visibility is None else consts.GUIDE_CONTROL_STATE
                guide_state = -1 if guide_pivot_visibility is None else consts.GUIDE_PIVOT_STATE
                if control_state == consts.GUIDE_PIVOT_STATE and guide_state == consts.GUIDE_PIVOT_STATE:
                    visibility_state = consts.GUIDE_PIVOT_CONTROL_STATE
                elif control_state == consts.GUIDE_CONTROL_STATE:
                    visibility_state = consts.GUIDE_CONTROL_STATE
                else:
                    visibility_state = consts.GUIDE_PIVOT_STATE
                rig.set_guide_visibility(
                    visibility_state,
                    control_value=guide_controls_visibility,
                    guide_value=guide_pivot_visibility,
                    include_root=False)

            shapes_hidden = cache.get('hideControlShapesInOutliner', None)
            if shapes_hidden is not None:
                for component in rig.iterate_components():
                    rig_layer = component.rig_layer()
                    if rig_layer is None:
                        continue
                    for control in rig_layer.iterate_controls():
                        for shape in control.iterate_shapes():
                            shape.attribute('hiddenInOutliner').set(shapes_hidden)

        try:
            preset_name = cache['namingPreset']
            self.set_naming_preset_by_name(preset_name)
        except KeyError:
            pass

        for setting, value in cache.items():
            if setting == 'buildScripts':
                self.set_build_scripts(value)
                continue
            if hasattr(self, setting):
                setattr(self, setting, value)
            elif hasattr(self, strings.camel_case_to_snake_case(setting)):
                try:
                    setattr(self, strings.camel_case_to_snake_case(setting), value)
                except Exception:
                    logger.error(f'Something went wrong while updating configuration: {setting}', exc_info=True)

    def serialize(self, rig: Rig) -> dict:
        """
        Serializes current configuration data.

        :param Rig rig: rig this configuration belongs to.
        :return: serialized data.
        :rtype: dict
        """

        cache = self._config_cache
        overrides = {}
        build_script_config = self.build_script_config(rig)

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

        for build_script in self._build_scripts:
            properties = build_script_config.get(build_script.ID, {})
            overrides.setdefault('buildScripts', []).append([build_script.ID, properties])

        if self._current_naming_preset.name != consts.DEFAULT_BUILTIN_PRESET_NAME:
            overrides[consts.NAMING_PRESET_DESCRIPTOR_KEY] = self._current_naming_preset.name

        return overrides

    def container_type(self) -> str:
        """
        Returns the default container type to use ('asset', 'set' or None).

        :return: container type.
        :rtype: str
        """

        return self._config_cache.get('defaultContainerType', 'asset')

    def find_name_manager_for_type(self, crit_type: str, preset_name: str | None = None):
        """
        Finds and returns the naming convention manager used to handle the nomenclature for the given type.

        :param str crit_type: Crit type to search for ('rig', 'module', etc).
        :param str or None preset_name: optional preset to use find the Crit type.
        :return: naming manager instance.
        :rtype: tp.common.naming.manager.NameManager or None
        """

        preset = self._current_naming_preset
        if preset_name:
            preset = self.NAMING_PRESET_MANAGER.find_preset(preset_name)

        return preset.find_name_manager_for_type(crit_type)

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

    def set_build_scripts(self, script_ids):
        """
        Sets the current build scripts that should be executed for the rigs using this configuration.

        :param list(str) script_ids: list of script IDs to set.
        """

        build_scripts_manager = self.BUILD_SCRIPTS_MANAGER
        self._build_scripts.clear()
        for build_script_id in script_ids:
            build_script = build_scripts_manager.get_loaded_plugin_from_id(build_script_id, package_name='crit')
            if build_script:
                self._build_scripts.append(build_script)

    def export_plugin_by_id(self, plugin_id: str) -> type[exporter.ExporterPlugin] | None:
        """
        Retrieves the exporter plugin class from given ID.

        :param str plugin_id: ID of the CRIT exporter plugin to retrieve.
        :return: plugin class that matches given ID.
        """

        override_plugin_id = self._export_plugin_overrides.get(plugin_id) or plugin_id
        return self.EXPORTER_MANAGER.get_plugin_from_id(override_plugin_id, package_name='crit')

    def _initialize_managers(self, force: bool = False):
        """
        Internal function handles the initialization of all the configuration managers.

        :param bool force: whether to force the reloading of the managers.
        """

        initialize_components_manager(reload=force)
        initialize_naming_preset_manager(self._preferences_interface, reload=force)
        initialize_build_scripts_manager(self._preferences_interface, reload=force)
        initialize_template_manager(reload=force)
        initialize_exporter_registry(self._preferences_interface, reload=force)

    def _initialize_environment(self):
        """
        Internal function that handles the loading and setup of CRIT preferences from settings.
        """

        # we update the cache to optimize speed
        self._config_cache = self._preferences_interface.settings().get('settings', {})

        self._selection_child_highlighting = self._config_cache.get(
            'selectionChildHighlighting', self._selection_child_highlighting)
        self._guide_control_visibility = self._config_cache.get('guideControlVisibility',
                                                                self._guide_control_visibility)
        self._guide_pivot_visibility = self._config_cache.get('guidePivotVisibility', self._guide_pivot_visibility)

        self.set_build_scripts(self._config_cache.get('buildScripts', []))
        self.set_naming_preset_by_name(self._config_cache.get('defaultNamingPreset', consts.DEFAULT_PRESET_NAME))

        for plugin_required in self._config_cache.get('requiredMayaPlugins', []):
            maya_helpers.load_plugin(plugin_required)

        self._use_proxy_attributes = self._config_cache.get('useProxyAttributes', self._use_proxy_attributes)
        self._use_containers = self._config_cache.get('useContainers', self._use_containers)
        self._blackbox = self._config_cache.get('blackBox', self._blackbox)
        self._hide_control_shapes_in_outliner = self._config_cache.get(
            'hideControlShapesInOutliner', self._hide_control_shapes_in_outliner)
