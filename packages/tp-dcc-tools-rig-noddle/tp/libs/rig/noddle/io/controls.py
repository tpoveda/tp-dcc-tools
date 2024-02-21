from __future__ import annotations


from tp.libs.rig.noddle.io import abstract


class ControlsShapeManager(abstract.AbstractIOManager):

    DATA_TYPE = 'controls'
    EXTENSION = 'crvs'

    def __init__(self):
        super().__init__()

    @classmethod
    def import_asset_shapes(cls):
        pass
