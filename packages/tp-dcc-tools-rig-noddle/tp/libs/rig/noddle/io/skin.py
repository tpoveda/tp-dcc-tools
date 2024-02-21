from __future__ import annotations

from overrides import override

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.maya import api
from tp.libs.rig.skinner import core as skinner
from tp.preferences.interfaces import noddle
from tp.libs.rig.noddle.io import abstract
from tp.libs.rig.noddle.functions import files, deformer

logger = log.rigLogger


class SkinManager(abstract.AbstractIOManager):

    DATA_TYPE = OpenMaya.MFn.kSkinClusterFilter
    EXTENSION = 'sknr'

    def __init__(self):
        super().__init__()

        self._prefs = noddle.noddle_interface()
        self._file_format = self._prefs.skin_file_format()
        if self._file_format not in ['json', 'pickle']:
            logger.error(f'{self}: invalid skin file format: {self._file_format}')
            raise ValueError

    @property
    def path(self) -> str:
        """
        Getter method that returns absolute file where skn file will be exported.

        :return: skin file path.
        :rtype: str
        """

        return self.asset.weights.skin

    @classmethod
    def export_all(cls):
        """
        Exports all skin cluster weights located under asset geometry group to asset skin folder.
        """

        skin_manager = cls()
        for deformer_node in deformer.list_deformer_paths(cls.DATA_TYPE, skin_manager.character.geometry_group()):
            print('gogogogo', deformer_node)

    @classmethod
    def import_all(cls):
        """
        Imports all skin weights for asset.
        """

        skin_manager = cls()
        logger.info(f'{skin_manager}: Importing weights...')
        for geo_name in skin_manager.versioned_files:
            if not cmds.objExists(geo_name):
                logger.warning(f'{skin_manager}: Object {geo_name} no longer exists, skipping...')
                continue
            skin_manager.import_single(api.node_by_name(geo_name))

    @override(check_signature=False)
    def base_name(self, geometry_node: api.DagNode) -> str:
        return geometry_node.fullPathName(partial_name=True, include_namespace=False)

    @override(check_signature=False)
    def latest_file(self, geometry_node: api.DagNode) -> str:
        return files.latest_file(
            self.base_name(geometry_node), directory=self.path, extension=self.EXTENSION, full_path=True)

    def import_single(self, geometry_node: api.DagNode):
        """
        Import skin cluster for given geometry.

        :param api.DagNode geometry_node: name of the geometry to import.
        """

        latest_file = self.latest_file(geometry_node)
        if not latest_file:
            logger.warning(f'{self}: No saved skin weights found for {geometry_node}')
            return

        try:
            skinner.importSkin([geometry_node.fullPathName()], filePaths=[latest_file])
            logger.info(f'{self}: Imported {geometry_node} weights: {latest_file}')
        except Exception:
            logger.exception(f'{self}: Failed to import skin weights for: {geometry_node}', exc_info=True)
