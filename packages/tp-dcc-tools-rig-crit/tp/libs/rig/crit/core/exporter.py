from __future__ import annotations

import typing
from typing import Any

from tp.common.python import decorators

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.core.rig import Rig


class ExporterPlugin:
    """
    Plugin interface for handling exporting of CRIT rigs.
    """

    ID = ''

    @decorators.abstractmethod
    def export_settings(self) -> Any:
        """
        Returns the export settings instance which will be used in the `export` function.
        This function must be overridden by subclasses.

        :return: export settings.
        :rtype: Any
        """

        raise NotImplementedError

    @decorators.abstractmethod
    def export(self, rig: Rig, export_options: Any) -> str:
        """
        Function that holds all export logic.
        This function must be overridden by subclasses.

        :param Rig rig: rig instance to export.
        :param Any export_options: export options for this exporter to use.
        :return: export path.
        :rtype: str
        """

        raise NotImplementedError
