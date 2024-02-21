from __future__ import annotations

import timeit
import typing

import maya.cmds as cmds

from tp.maya.cmds import gui

from tp.bootstrap import log
from tp.libs.rig.crit.core import project, asset, rig
from tp.libs.rig.crit.functions import assets

if typing.TYPE_CHECKING:
    from tp.libs.rig.crit.meta.rig import CritRig


class Build:

    def __init__(self, asset_type: str, asset_name: str, existing_rig: CritRig | None = None):

        cmds.scriptEditorInfo(e=True, sr=True)
        cmds.file(new=True, force=True)

        try:
            self._asset_type = asset_type
            self._asset_name = asset_name
            self._existing_rig = existing_rig

            self.logger = log.get_logger('.'.join([__name__, '_'.join([asset_type, asset_name])]))

            self._project = project.Project.get()
            if not self._project:
                self.logger.warning('Project is not set')
                return

            self._start_time = timeit.default_timer()
            self.logger.info('Initializing new build...')

            # set the asset and import model and latest skeleton file
            self._asset = asset.Asset(self._project, asset_name, asset_type)
            self.import_model()
            self.import_skeleton()

            # create character component
            self._rig = rig.Rig(meta=self._existing_rig or None)
            self._rig.start_session(self._asset_name)

            self.run()
            self.post()

            self.logger.info('Build finished in {0:.2f}s'.format(timeit.default_timer() - self._start_time))
        except Exception:
            self.logger.exception('Something went wrong during building process', exc_info=True)
        finally:
            cmds.scriptEditorInfo(edit=True, suppressResults=False)

    @property
    def project(self) -> project.Project:
        return self._project

    @property
    def asset(self) -> asset.Asset:
        return self._asset

    @property
    def rig(self) -> rig.Rig:
        return self._rig

    @property
    def start_time(self) -> float:
        return self._start_time

    def import_model(self):
        assets.import_model()

    def import_skeleton(self):
        assets.import_skeleton()

    def pre(self):
        pass

    def run(self):
        pass

    def post(self):
        cmds.select(clear=True)
        gui.set_xray_joints(True)
        # cmds.viewFit(self.character.root_control().group.fullPathName())
        # self.character.geometry_group().overrideEnabled.set(True)
        # self.character.geometry_group().overrideColor.set(1)
