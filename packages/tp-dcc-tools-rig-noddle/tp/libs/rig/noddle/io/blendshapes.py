from __future__ import annotations

from overrides import override

import maya.cmds as cmds

from tp.core import log
from tp.common.python import jsonio

from tp.libs.rig.noddle.io import abstract
from tp.libs.rig.noddle.functions import files

logger = log.rigLogger


class BlendShapesManager(abstract.AbstractIOManager):

    DATA_TYPE = 'blendShape'
    EXTENSION = 'shape'

    @property
    def path(self) -> str:
        return self.asset.data.blendshapes

    @classmethod
    def import_all(cls):

        manager = cls()
        for bs_name in manager.versioned_files.keys():
            manager.import_single(bs_name)

    @override(check_signature=False)
    def base_name(self, bs_name: str) -> str:
        return str(bs_name)

    @override(check_signature=False)
    def latest_file(self, bs_name: str, full_path: bool = False) -> str:
        return files.latest_file(self.base_name(bs_name), self.path, extension=self.EXTENSION, full_path=full_path)

    def mapping(self) -> dict:
        """
        Returns mapping data from asset blenshapes mapping file.

        :return: mapping data.
        :rtype :dict
        """

        return jsonio.read_file(self.asset.mapping.blendshapes)

    def mapped_geometry(self, bs_name: str) -> str:
        """
        Returns the name of the geometry that maps to the given blendshape name.

        :param str bs_name: name of the blendshape whose mapping geometry name we want to retrieve.
        :return: geometry name.
        :rtype: str
        """

        bs_name = str(bs_name)
        print(self.mapping())
        return self.mapping().get(bs_name, '')

    def import_single(self, bs_name: str) -> bool:
        """
        Imports a single blenshape file.

        :param str bs_name: name of the blendshape file to import.
        :return: True if the import blendshape operation was successful; False otherwise.
        :rtype: bool
        """

        bs_name = str(bs_name)
        latest_path = self.latest_file(bs_name, full_path=True)
        if not latest_path:
            logger.warning(f'{self}: no saved blendshape found: {bs_name}')
            return False

        geometry = self.mapped_geometry(bs_name)
        if not geometry:
            logger.error(f'{self}: mapping missing for {bs_name}')
            return False
        if not cmds.objExists(geometry):
            logger.warning(f'{self}: geometry {geometry} for blendshape {bs_name} no longer exists, skipping...')
            return False

        if bs_name not in [node for node in cmds.listRelatives(cmds.listHistory(geometry), type=self.DATA_TYPE) or list()]:
            shape_node = cmds.blendShape(geometry, n=bs_name, frontOfChain=True)
        else:
            shape_node = bs_name

        try:
            cmds.blendShape(shape_node, edit=True, ip=latest_path)
            logger.info(f'{self}: Imported blendshape: {latest_path}')
            return True
        except RuntimeError:
            logger.exception(f'{self}: Failed to import blendshape: {latest_path}', exc_info=True)

        return False
