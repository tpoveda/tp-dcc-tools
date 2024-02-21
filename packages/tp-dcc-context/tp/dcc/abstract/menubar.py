from __future__ import annotations

import abc
from typing import Iterator, Any

from tp.dcc.abstract import base


class AFnMenuBar(base.AFnBase):
    """
    Overloads of AFnBase function set class to handle behaviour for menu bars within DCCs.
    """

    __slots__ = ()

    @abc.abstractmethod
    def main_menu_bar(self) -> Any:
        """
        Returns main menu bar instance.

        :return: main menu bar.
        :rtype: Any
        """

        pass

    @abc.abstractmethod
    def iterate_menus(self) -> Iterator[Any]:
        """
        Generator function that yields all menus within main menu.

        :return: iterated menus.
        :rtype: Iterator[Any]
        """

        pass

    @abc.abstractmethod
    def menu_title(self, menu: Any, strip_ampersand: bool = False) -> str:
        """
        Returns the title of the given menu.

        :param Any menu: menu instance to get title of.
        :param bool strip_ampersand: whether to strip ampersand from menu.
        :return: menu title.
        :rtype: str
        """

        pass

    def find_menus_by_title(self, title: str) -> list[Any]:
        """
        Returns a list of menus with the given title.

        :param str title: title to filter menus by.
        :return: found menus with given title.
        :rtype: list[Any]
        """

        return [x for x in self.iterate_menus() if self.menu_title(x, strip_ampersand=True) == title]

    def has_menu(self, title: str) -> bool:
        """
        Returns whether menu with given title exists.

        :param str title: title to check menu existence by.
        :return: True if menu with given title exists; False otherwise.
        :rtype: bool
        """

        return bool(self.find_menus_by_title(title))

    @abc.abstractmethod
    def remove_menu(self, menu: Any):
        """
        Removes the given menu from menu bar.

        :param Any menu: menu to delete.
        """

        pass

    def remove_menus_by_title(self, title: str):
        """
        Removes all menus with the matching title.

        :param str title: title to delete menus from.
        """

        for menu in self.find_menus_by_title(title):
            self.remove_menu(menu)
