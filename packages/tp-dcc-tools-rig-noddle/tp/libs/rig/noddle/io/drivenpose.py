from __future__ import annotations


from tp.libs.rig.noddle.io import abstract


class DrivenPoseManager(abstract.AbstractIOManager):

    DATA_TYPE = 'pose'
    EXTENSION = 'json'

    @classmethod
    def import_all(cls):
        pass
