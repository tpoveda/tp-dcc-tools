from __future__ import annotations

from typing import Any

from tp.core import dcc, dccs


def load(data: dict | str, app: str | None = None) -> Any:
    """
    Loads menu from given dictionary, configuration file or module.

    :param dict or str data: menu data to load.
    :param str | None app: name of the application to load menu for. If not given, dcc will be automatically detected.
    :return: DCC native node menu.
    :rtype: Any
    """

    if app == dccs.Maya or dcc.is_maya():
        from tp.maya.api import menu as maya_menu
        return maya_menu.MayaMenuItem.load(data)
    elif app == dccs.Unreal or dcc.is_unreal():
        from tp.unreal.api import menu as unreal_menu
        return unreal_menu.UnrealMenuItem.load(data)


def setup(data: dict | str, app: str | None = None, backlink: bool = True, parent_native_node: Any = None) -> Any:
    """
    Setup menu from given dictionary, configuration file or module.

    :param dict or str data: menu data to load.
    :param str | None app: name of the application to load menu for. If not given, dcc will be automatically detected.
    :param bool backlink: whether to add an attribute to the DCC native node instance to this instance.
    :param Any parent_native_node: DCC native node that points to the parent menu item.
    :return: DCC native node instance that points to the newly crated menu item.
    :rtype: Any
    """

    menu_instance = load(data, app=app)
    return menu_instance.setup(parent_native_node=parent_native_node, backlink=backlink)


class MenuManager:
    """
    Class that handles the menu creation for DCCs
    """

    def __init__(self):
        super().__init__()

        self._menus = list()
