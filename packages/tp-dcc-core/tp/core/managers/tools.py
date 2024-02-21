from __future__ import annotations

import traceback
from typing import Tuple, List, Dict, Iterator, Type, Any

from Qt.QtWidgets import QApplication, QWidget

from tp.core import log, dcc, tool
from tp.common import plugin
from tp.core.managers import menus

_TOOLS_MANAGER = None
_TOOLS_FACTORY = None

logger = log.tpLogger


class ToolsManager:
    """
    Class that handles tp-dcc-tools tools loading for Maya with the creation of DCC specific menus to open them.
    """

    TOOLS_ENV = 'TPDCC_TOOL_DEFINITION_MODULES'
    APPLICATION = 'standalone'

    def __init__(self, parent: QWidget | None = None):
        super().__init__()

        self._parent = parent
        self._menus_manager = menus.MenusManager()
        self._tools_factory = plugin.PluginFactory(
            interface=[tool.Tool], plugin_id='id', name='Tools')
        self._tools_factory.register_paths_from_env_var(self.TOOLS_ENV)
        self._tools_factory.load_all_plugins(tools_manager=self)

    @classmethod
    def current_instance(cls) -> ToolsManager | None:
        """
        Returns current toolbox instance.

        :return: tools manager instance.
        :rtype: ToolsManager or None
        """

        global _TOOLS_MANAGER
        return _TOOLS_MANAGER

    @classmethod
    def load(cls, application_name: str | None = None, parent: QWidget | None = None) -> ToolsManager:
        """
        Creates a new toolbox UI instance.

        :param str or None application_name: optional target application name.
        :param QWidget or None parent: optional parent widget.
        :return: toolbox UI instance.
        :rtype: ToolsManager
        """

        global _TOOLS_MANAGER
        global _TOOLS_FACTORY

        application_name = application_name or dcc.name()

        instance = cls.current_instance()
        if instance is not None:
            return instance

        if _TOOLS_FACTORY is None:
            _TOOLS_FACTORY = plugin.PluginFactory(interface=[ToolsManager], plugin_id='APPLICATION', name='ToolsManager')

            _TOOLS_FACTORY.register_paths_from_env_var('TPDCC_TOOLS_MANAGER_PATHS')
            _TOOLS_FACTORY.load_plugin(application_name, parent=parent)

        _TOOLS_MANAGER = _TOOLS_FACTORY.get_loaded_plugin_from_id(application_name)  # type: ToolsManager

        return _TOOLS_MANAGER

    @classmethod
    def close(cls):
        """
        Closes toolbox and all opened tools
        """

        global _TOOLS_MANAGER

        instance = cls.current_instance()
        try:
            instance.shutdown()
        except AttributeError:
            pass
        finally:
            _TOOLS_MANAGER = None

    def iterate_tool_classes(self) -> Iterator[Type]:
        """
        Returns all registered tools classes within this Tools manager.

        :return: iterated registered tools classes.
        :rtype: Iterator[Type]
        """

        for tool_class in self._tools_factory.plugins():
            yield tool_class

    def tool_classes(self) -> List[Type]:
        """
        Returns all registered tools classes within this Tools manager.

        :return: list of registered tools classes.
        :rtype: List[Type]
        """

        return list(self.iterate_tool_classes())

    def launch_tool_by_id(self, tool_id: str, package_name: str | None = None, *args: Tuple, **kwargs: Dict) -> Any:
        """
        Executes the tool plugin from the given id.

        :param str tool_id: ID of the tool to execute.
        :param str package_name: optional package name of the tool to execute.
        :param Tuple args: arguments to pass to the execute tool method.
        :param Dict kwargs: keyword arguments to pass to the execute tool method.
        :return: execute tool output.
        :rtype: Any
        """

        plugin_instance = self._tools_factory.get_loaded_plugin_from_id(tool_id, package_name=package_name)
        if not plugin_instance:
            logger.warning(f'Was not possible to launch tool: No tool with ID "{tool_id}" registered!')
            return None

        try:
            result = plugin_instance._execute(*args, **kwargs)
            logger.info(f'{plugin_instance} Execution time: {plugin_instance.stats.info["executionTime"]}')
        except Exception:
            traceback.print_exc()
            raise

        if result and dcc.is_standalone():
            app = QApplication.instance()
            app.exec_()

        return result

    def shutdown(self):
        """
        Tries to close all loaded tools.
        """

        for pkg_name, tools in self._tools_factory.loaded_plugins.items():
            for tool_instance in tools:
                logger.debug(f'Shutting down tool: {tool_instance.ID}')
                tool_instance._run_teardown()
        self._tools_factory.unload_all_plugins()
