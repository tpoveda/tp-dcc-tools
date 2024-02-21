from __future__ import annotations

import typing

from tp.core import log
from tp.common.python import decorators

from tp.libs.rig.noddle.core import asset
from tp.libs.rig.noddle.functions import files, rigs

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.core.rig import Rig


logger = log.rigLogger


class AbstractIOManager:
    """
    Abstract class to implement import/export asset data managers
    """

    DATA_TYPE = None
    EXTENSION = None

    def __init__(self):
        super().__init__()

        self._asset = asset.Asset.get()
        self._rig = rigs.get_build_rig()
        if not self._asset:
            logger.error('Asset is not set!')
            raise RuntimeError
        self._versioned_files = files.versioned_files(self.path, extension=self.EXTENSION)

    @decorators.abstractproperty
    def path(self) -> str:
        """
        Returns the asset subdirectory.

        :return: asset path.
        :rtype: str
        """

        pass

    @decorators.abstractmethod
    def base_name(self) -> str:
        """
        Returns the base name for versioned file.

        :return: base name.
        :rtype: str
        """

        pass

    @decorators.abstractmethod
    def new_file(self) -> str:
        """
        Returns path to new file version.

        :return: new file version.
        :rtype: str
        """

        pass

    @decorators.abstractmethod
    def latest_file(self) -> str:
        """
        Returns path to the latest versioned file.

        :return: latest version file path.
        :rtype: str
        """

        pass

    @property
    def asset(self) -> asset.Asset:
        return self._asset

    @property
    def rig(self) -> Rig:
        return self._rig

    @property
    def versioned_files(self) -> dict[str, list[str, str]]:
        return self._versioned_files
