from __future__ import annotations

import os

from tp.core import log
from tp.common.python import jsonio

from tp.libs.rig.noddle.io import abstract
from tp.libs.rig.noddle.functions import files, rigs

logger = log.rigLogger


class ControlsShapeManager(abstract.AbstractIOManager):

    DATA_TYPE = 'controls'
    EXTENSION = 'curves'

    def __init__(self):
        super().__init__()

    @property
    def path(self) -> str:
        return self.asset.controls

    def base_name(self) -> str:
        return f'{self.asset.name}_{self.DATA_TYPE}'

    def new_file(self) -> str:
        return files.new_versioned_file(self.base_name(), directory=self.path, extension=self.EXTENSION)

    def latest_file(self) -> str:
        return files.latest_file(self.base_name(), self.path, extension=self.EXTENSION, full_path=True)

    @classmethod
    def export_asset_shapes(cls):
        """
        Exports all shapes of current active rig asset.
        """

        manager = cls()
        data_dict = {}
        all_controls = rigs.list_controls()
        if not all_controls:
            logger.warning('No controls to save')
            return

        for control_id, control in all_controls.items():
            data_dict[control_id] = control.serializeFromScene()['shape']

        export_path = manager.new_file()
        jsonio.write_to_file(data_dict, export_path)
        logger.info(f'Exported control shapes: "{export_path}"')

    @classmethod
    def import_asset_shapes(cls):
        """
        Imports all shapes from the latest controls versioned file and updates all rig control shapes.
        """

        manager = cls()
        latest_file = manager.latest_file()
        if not latest_file or not os.path.isfile(latest_file):
            return

        all_controls = rigs.list_controls()

        data = jsonio.read_file(latest_file)
        for control_id, shape_data in data.items():
            found_control = all_controls.get(control_id)
            if not found_control:
                continue
            found_control.add_shape_from_data(shape_data, replace=True, maintain_colors=True)

        logger.info(f'Imported control shapes: "{latest_file}"')
