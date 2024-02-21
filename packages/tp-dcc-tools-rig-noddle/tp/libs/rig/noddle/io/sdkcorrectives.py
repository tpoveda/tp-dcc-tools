from __future__ import annotations


from tp.libs.rig.noddle.io import abstract


class SdkCorrectivesManager(abstract.AbstractIOManager):

    DATA_TYPE = 'corrective'
    EXTENSION = 'json'

    @classmethod
    def import_all(cls):
        pass
