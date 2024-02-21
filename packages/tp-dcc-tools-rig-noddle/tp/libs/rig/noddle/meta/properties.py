from __future__ import annotations

from overrides import override

from tp.maya import api
from tp.maya.meta import metaproperty

from tp.libs.rig.noddle import consts


class CommonProperty(metaproperty.MetaProperty):
    """
    Base property class for any properties that can be added to anything.
    """

    ID = 'noddleCommonProperty'
    DEFAULT_NAME = 'common_property'

    @staticmethod
    @override
    def inherited_classes():
        return CommonProperty.__subclasses__()


class ExportProperty(CommonProperty):
    """
    Property that marks whether and object should be exported.
    """

    ID = 'noddleExportProperty'
    DEFAULT_NAME = 'export_property'

    @staticmethod
    @override
    def inherited_classes():
        return ExportProperty.__subclasses__()

    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(name=consts.NODDLE_EXPORT_ATTR, type=api.kMFnNumericBoolean),
            )
        )

        return attrs

    @override
    def act(self):
        return self.data()[consts.NODDLE_EXPORT_ATTR]


class JointProperty(metaproperty.MetaProperty):
    """
    Property that marks a scene object as a joint.
    """

    ID = 'noddleJointProperty'
    DEFAULT_NAME = 'joint_property'

    @staticmethod
    @override
    def inherited_classes():
        return JointProperty.__subclasses__()


class RegionMarkupProperty(JointProperty):
    """
    Property that marks an object as part of a rigging region.
    Must always be made in pairs, one for the root and one for the end joint of the rigging region.
    """

    ID = 'noddleRigMarkupProperty'
    DEFAULT_NAME = 'rig_markup_property'
    MULTI_ALLOWED = True

    @override
    def meta_attributes(self) -> list[dict]:
        attrs = super().meta_attributes()

        attrs.extend(
            (
                dict(name=consts.NODDLE_SIDE_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_REGION_NAME_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_REGION_TAG_ATTR, type=api.kMFnDataString),
                dict(name=consts.NODDLE_REGION_GROUP_ATTR, type=api.kMFnDataString),
            )
        )

        return attrs
