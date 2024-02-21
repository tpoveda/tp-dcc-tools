from __future__ import annotations

import abc

from tp.dcc.abstract import base


class AFnFbx(base.AFnBase):
    """
    Overloads of AFnBase function set class to handle behaviour for DCC FBX operations.
    """

    __slots__ = ()

    @abc.abstractmethod
    def set_mesh_export_params(self, **kwargs):
        """
        Adopts the mesh export settings from the given keyword arguments.

        :param dict kwargs: mesh export keyword arguments.
        """

        pass

    @abc.abstractmethod
    def set_anim_export_params(self, **kwargs):
        """
        Adopts the animation export settings from the given keyword arguments.

        :param dict kwargs: animation export keyword arguments.
        """

        pass

    @abc.abstractmethod
    def export_selection(self, file_path: str) -> bool:
        """
        Exports active selection to the given file path.

        :param str file_path: FBX file path to export.
        :return: True if export selection operation was successful; False otherwise.
        :rtype: bool
        """

        pass
