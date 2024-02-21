from __future__ import annotations


from tp.libs.rig.noddle.io import abstract


class NgLayers2Manager(abstract.AbstractIOManager):

    DATA_TYPE = 'ng_layers2'
    EXTENSION = 'layers'

    @classmethod
    def import_all(cls):
        pass
