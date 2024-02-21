from __future__ import annotations

import enum

from tp.maya.api import spaceswitch


MPARENT_ATTR_NAME = 'tpMetaParent'
MCHILDREN_ATTR_NAME = 'tpMetaChildren'


# ======================================================================================================================
# MetaClasses Types
# ======================================================================================================================

RIG_TYPE = 'noddleRig'
COMPONENT_TYPE = 'noddleComponent'
ANIM_COMPONENT_TYPE = 'noddleAnimComponent'
BASE_LAYER_TYPE = 'noddleLayer'
COMPONENTS_LAYER_TYPE = 'noddleComponentsLayer'
INPUT_LAYER_TYPE = 'noddleInputLayer'
OUTPUT_LAYER_TYPE = 'noddleOutputLayer'
REGIONS_LAYER_TYPE = 'noddleRegionsLayer'
SKELETON_LAYER_TYPE = 'noddleSkeletonLayer'
RIG_LAYER_TYPE = 'noddleRigLayer'
XGROUP_LAYER_TYPE = 'noddleXGroupLayer'
GEOMETRY_LAYER_TYPE = 'noddleGeometryLayer'
LAYER_TYPES = (
    COMPONENTS_LAYER_TYPE,
    INPUT_LAYER_TYPE,
    OUTPUT_LAYER_TYPE,
    REGIONS_LAYER_TYPE,
    SKELETON_LAYER_TYPE,
    RIG_LAYER_TYPE,
    XGROUP_LAYER_TYPE,
    GEOMETRY_LAYER_TYPE
)
CONTROL_PANEL_TYPE = 'controlPanel'

# ======================================================================================================================
# Names for Standard Transform Local Attributes
# ======================================================================================================================

TRANSFORM_ATTRS = ('translate', 'rotate', 'scale')

# ======================================================================================================================
# MetaData Attribute Names
# ======================================================================================================================

NODDLE_ID_ATTR = 'noddleId'
NODDLE_VERSION_ATTR = 'noddleVersion'
NODDLE_NAME_ATTR = 'noddleName'
NODDLE_SIDE_ATTR = 'noddleSide'
NODDLE_IS_NODDLE_ATTR = 'noddleIsNoddle'
NODDLE_IS_ROOT_ATTR = 'noddleIsRoot'
NODDLE_IS_ENABLED_ATTR = 'noddleEnabled'
NODDLE_ROOT_TRANSFORM_ATTR = 'noddleRootTransform'
NODDLE_RIG_CONFIG_ATTR = 'noddleConfig'
NODDLE_CONTROL_DISPLAY_LAYER_ATTR = 'noddleControlDisplayLayer'
NODDLE_ROOT_SELECTION_SET_ATTR = 'noddleRootSelectionSet'
NODDLE_CONTROL_SELECTION_SET_ATTR = 'noddleControlSelectionSet'
NODDLE_JOINT_SELECTION_SET_ATTR = 'noddleJointSelectionSet'
NODDLE_SKELETON_SELECTION_SET_ATTR = 'noddleSkeletonSelectionSet'
NODDLE_EXTRA_NODES_ATTR = 'noddleExtraNodes'
NODDLE_CONNECTOR_ATTR = 'noddleConnector'
NODDLE_CONNECTORS_ATTR = 'noddleConnectors'
NODDLE_CONNECTOR_START_ATTR = 'noddleConnectorStart'
NODDLE_CONNECTOR_END_ATTR = 'noddleConnectorEnd'
NODDLE_CONNECTOR_ATTRIBUTE_HOLDER_ATTR = 'noddleConnectorAttrHolder'
NODDLE_SETTING_NODES_ATTR = 'noddleSettingNodes'
NODDLE_SETTING_NODE_ATTR = 'noddleSettingNode'
NODDLE_SETTING_NAME_ATTR = 'noddleSettingName'
NODDLE_TAGGED_NODE_ATTR = 'noddleTaggedNode'
NODDLE_TAGGED_NODE_SOURCE_ATTR = 'noddleTaggedNodeSource'
NODDLE_TAGGED_NODE_ID_ATTR = 'noddleTaggedNodeId'
NODDLE_IS_COMPONENT_ATTR = 'noddleIsComponent'
NODDLE_IS_INPUT_ATTR = 'noddleIsInput'
NODDLE_IS_OUTPUT_ATTR = 'noddleIsOutput'
NODDLE_INPUTS_ATTR = 'noddleInputs'
NODDLE_OUTPUTS_ATTR = 'noddleOutputs'
NODDLE_INPUT_NODE_ATTR = 'noddleInputNode'
NODDLE_INPUT_ID_ATTR = 'noddleInputId'
NODDLE_IS_INPUT_ROOT_ATTR = 'noddleIsInputRoot'
NODDLE_OUTPUT_NODE_ATTR = 'noddleOutputNode'
NODDLE_OUTPUT_ID_ATTR = 'noddleOutputId'
NODDLE_SOURCE_INPUTS_ATTR = 'noddleSourceInputs'
NODDLE_SOURCE_INPUT_ATTR = 'noddleSourceInput'
NODDLE_SOURCE_INPUT_CONSTRAINT_NODES_ATTR = 'noddleConstraintNodes'
NODDLE_JOINTS_ATTR = 'noddleCritJoints'
NODDLE_JOINT_ATTR = 'noddleJoint'
NODDLE_JOINT_ID_ATTR = 'noddleJointId'
NODDLE_REGIONS_ATTR = 'noddleCritRegions'
NODDLE_REGION_NAME_ATTR = 'noddleRegionName'
NODDLE_REGION_SIDE_ATTR = 'noddleRegionSide'
NODDLE_REGION_TAG_ATTR = 'noddleRegionTag'
NODDLE_REGION_GROUP_ATTR = 'noddleRegionGroup'
NODDLE_REGION_START_JOINT_ATTR = 'noddleRegionStartJoint'
NODDLE_REGION_END_JOINT_ATTR = 'noddleRegionEndJoint'
NODDLE_CONTROL_MODE_ATTR = 'noddleControlMode'
NODDLE_CONTROLS_ATTR = 'noddleCritControls'
NODDLE_CONTROL_NODE_ATTR = 'noddleControlNode'
NODDLE_CONTROL_ID_ATTR = 'noddleControlId'
NODDLE_CONTROL_SRTS_ATR = 'noddleSrts'
NODDLE_COMPONENT_TYPE_ATTR = 'noddleComponentType'
NODDLE_CONTAINER_ATTR = 'noddleContainer'
NODDLE_HAS_SKELETON_ATTR = 'noddleHasSkeleton'
NODDLE_HAS_POLISHED_ATTR = 'noddleHasPolished'
NODDLE_HAS_RIG_ATTR = 'noddleHasRig'
NODDLE_REQUIRES_PIVOT_SHAPE_ATTR = 'noddleRequiresPivotShape'
NODDLE_PIVOT_COLOR_ATTR = 'noddlePivotColor'
NODDLE_PIVOT_SHAPE_ATTR = 'noddlePivotShape'
NODDLE_PIVOT_NODE_ATTR = 'noddlePivotNode'
NODDLE_DISPLAY_AXIS_SHAPE_ATTR = 'noddleDisplayAxisShape'
NODDLE_COMPONENT_GROUP_ATTR = 'noddleComponentGroup'
NODDLE_COMPONENT_DESCRIPTOR_ATTR = 'noddleComponentDescriptor'
NODDLE_COMPONENT_GROUPS_ATTR = 'noddleComponentGroups'
NODDLE_COMPONENT_GROUP_NAME_ATTR = 'noddleGroupName'
NODDLE_GROUP_COMPONENTS_ATTR = 'noddleGroupComponents'
NODDLE_EXPORT_ATTR = 'noddleExport'
NODDLE_BIND_TRANSLATE_ATTR = 'noddleBindTranslate'
NODDLE_BIND_ROTATE_ATTR = 'noddleBindRotate'

# ======================================================================================================================
# Component Descriptor Attribute Names
# ======================================================================================================================

NODDLE_DESCRIPTOR_CACHE_INFO_ATTR = 'noddleDefCacheInfo'
NODDLE_DESCRIPTOR_CACHE_DEFORM_DAG_ATTR = 'noddleDescriptorCacheSkeletonLayerDag'
NODDLE_DESCRIPTOR_CACHE_DEFORM_SETTINGS_ATTR = 'noddleDescriptorCacheSkeletonLayerSettings'
NODDLE_DESCRIPTOR_CACHE_DEFORM_METADATA_ATTR = 'noddleDescriptorCacheSkeletonLayerMetadata'
NODDLE_DESCRIPTOR_CACHE_INPUT_DAG_ATTR = 'noddleDescriptorCacheInputLayerDag'
NODDLE_DESCRIPTOR_CACHE_INPUT_SETTINGS_ATTR = 'noddleDescriptorCacheInputLayerSettings'
NODDLE_DESCRIPTOR_CACHE_INPUT_METADATA_ATTR = 'noddleDescriptorCacheInputLayerMetadata'
NODDLE_DESCRIPTOR_CACHE_OUTPUT_DAG_ATTR = 'noddleDescriptorCacheOutputLayerDag'
NODDLE_DESCRIPTOR_CACHE_OUTPUT_SETTINGS_ATTR = 'noddleDescriptorCacheOutputLayerSettings'
NODDLE_DESCRIPTOR_CACHE_OUTPUT_METADATA_ATTR = 'noddleDescriptorCacheOutputLayerMetadata'
NODDLE_DESCRIPTOR_CACHE_RIG_DAG_ATTR = 'noddleDescriptorCacheRigLayerDag'
NODDLE_DESCRIPTOR_CACHE_RIG_DG_ATTR = 'noddleDescriptorCacheRigLayerDg'
NODDLE_DESCRIPTOR_CACHE_RIG_SETTINGS_ATTR = 'noddleDescriptorCacheRigLayerSettings'
NODDLE_DESCRIPTOR_CACHE_RIG_METADATA_ATTR = 'noddleDescriptorCacheRigLayerMetadata'
NODDLE_DESCRIPTOR_CACHE_SPACE_SWITCHING_ATTR = 'noddleDescriptorCacheSpaceSwitching'
NODDLE_DESCRIPTOR_CACHE_ATTR_NAMES = (
    NODDLE_DESCRIPTOR_CACHE_INFO_ATTR,
    NODDLE_DESCRIPTOR_CACHE_DEFORM_DAG_ATTR,
    NODDLE_DESCRIPTOR_CACHE_DEFORM_SETTINGS_ATTR,
    NODDLE_DESCRIPTOR_CACHE_DEFORM_METADATA_ATTR,
    NODDLE_DESCRIPTOR_CACHE_INPUT_DAG_ATTR,
    NODDLE_DESCRIPTOR_CACHE_INPUT_SETTINGS_ATTR,
    NODDLE_DESCRIPTOR_CACHE_INPUT_METADATA_ATTR,
    NODDLE_DESCRIPTOR_CACHE_OUTPUT_DAG_ATTR,
    NODDLE_DESCRIPTOR_CACHE_OUTPUT_SETTINGS_ATTR,
    NODDLE_DESCRIPTOR_CACHE_OUTPUT_METADATA_ATTR,
    NODDLE_DESCRIPTOR_CACHE_RIG_DAG_ATTR,
    NODDLE_DESCRIPTOR_CACHE_RIG_DG_ATTR,
    NODDLE_DESCRIPTOR_CACHE_RIG_SETTINGS_ATTR,
    NODDLE_DESCRIPTOR_CACHE_RIG_METADATA_ATTR,
    NODDLE_DESCRIPTOR_CACHE_SPACE_SWITCHING_ATTR
)

# ======================================================================================================================
# Descriptor attribute expression constants
# ======================================================================================================================

NODDLE_DESCRIPTOR_ATTR_EXPR_SELF_TOKEN = '@{self}'
NODDLE_DESCRIPTOR_ATTR_EXPR_INHERIT_TOKEN = '@{inherit}'
NODDLE_DESCRIPTOR_ATTR_EXPR_REGEX_PATTERN = r'(?:\@{(.*)\})'


# ======================================================================================================================
# Non Publishable Attributes
# ======================================================================================================================

ATTRIBUTES_TO_SKIP_PUBLISH = [NODDLE_ID_ATTR, 'metaNode', spaceswitch.TP_CONSTRAINTS_ATTR_NAME]

# ======================================================================================================================
# Extensions
# ======================================================================================================================

DESCRIPTOR_EXTENSION = '.descriptor'

# ======================================================================================================================
# Descriptor Keys
# ======================================================================================================================

VERSION_DESCRIPTOR_KEY = 'descriptorVersion'
PARENT_DESCRIPTOR_KEY = 'parent'
HOOK_DESCRIPTOR_KEY = 'hook'
CONNECTIONS_DESCRIPTOR_KEY = 'connections'
DAG_DESCRIPTOR_KEY = 'dag'
DG_DESCRIPTOR_KEY = 'dg'
SETTINGS_DESCRIPTOR_KEY = 'settings'
NAME_DESCRIPTOR_KEY = 'name'
SIDE_DESCRIPTOR_KEY = 'side'
TYPE_DESCRIPTOR_KEY = 'type'
ENABLED_DESCRIPTOR_KEY = 'enabled'
METADATA_DESCRIPTOR_KEY = 'metadata'
NAMING_PRESET_DESCRIPTOR_KEY = 'namingPreset'
SPACE_SWITCH_DESCRIPTOR_KEY = 'spaceSwitching'
INPUT_LAYER_DESCRIPTOR_KEY = 'inputLayer'
OUTPUT_LAYER_DESCRIPTOR_KEY = 'outputLayer'
RIG_LAYER_DESCRIPTOR_KEY = 'rigLayer'
SKELETON_LAYER_DESCRIPTOR_KEY = 'skeletonLayer'
SKELETON_MARKING_MENU_DESCRIPTOR_KEY = 'markingMenuSkeleton'
RIG_MARKING_MENU_DESCRIPTOR_KYE = 'markingMenuRig'
ANIM_MARKING_MENU_DESCRIPTOR_KEY = 'markingMenuAnim'
DEFAULT_SKELETON_MARKING_MENU = 'noddleDefaultSkeletonMenu'
DEFAULT_RIG_MARKING_MENU = 'noddleDefaultRigMenu'
LAYER_DESCRIPTOR_KEYS = (
    INPUT_LAYER_DESCRIPTOR_KEY,
    OUTPUT_LAYER_DESCRIPTOR_KEY,
    RIG_LAYER_DESCRIPTOR_KEY,
    SKELETON_LAYER_DESCRIPTOR_KEY
)
DESCRIPTOR_KEYS_TO_SKIP_UPDATE = (
    INPUT_LAYER_DESCRIPTOR_KEY,
    OUTPUT_LAYER_DESCRIPTOR_KEY,
    SKELETON_LAYER_DESCRIPTOR_KEY,
    RIG_LAYER_DESCRIPTOR_KEY,
)

# ======================================================================================================================
# Naming Preset Keys
# ======================================================================================================================

DEFAULT_PRESET_NAME = 'Noddle'
DEFAULT_BUILTIN_PRESET_NAME = 'noddle'

# ======================================================================================================================
# Environment Variable Keys
# ======================================================================================================================

COMPONENTS_ENV_VAR_KEY = 'NODDLE_COMPONENTS_PATHS'
DESCRIPTORS_ENV_VAR_KEY = 'NODDLE_DESCRIPTORS_PATHS'

# ======================================================================================================================
# Build States
# ======================================================================================================================

NOT_BUILT_STATE = 0
SKELETON_STATE = 1
RIG_STATE = 2
POLISH_STATE = 3

# ======================================================================================================================
# Build Script Function Types
# ======================================================================================================================

SKELETON_FUNCTION_TYPE = 0
RIG_FUNCTION_TYPE = 1
POLISH_FUNCTION_TYPE = 2
DELETE_SKELETON_LAYER_FUNCTION_TYPE = 3
DELETE_RIG_LAYER_FUNCTION_TYPE = 4
DELETE_COMPONENT_FUNCTION_TYPE = 5
DELETE_COMPONENTS_FUNCTION_TYPE = 6
DELETE_RIG_FUNCTION_TYPE = 7
BUILD_SCRIPT_FUNCTIONS_MAPPING = {
    SKELETON_FUNCTION_TYPE: ('pre_skeleton_build', 'post_skeleton_build'),
    RIG_FUNCTION_TYPE: ('pre_rig_build', 'post_rig_build'),
    POLISH_FUNCTION_TYPE: ('pre_polish', 'post_polish_build'),
    DELETE_SKELETON_LAYER_FUNCTION_TYPE: ('pre_delete_skeleton_layer', None),
    DELETE_RIG_LAYER_FUNCTION_TYPE: ('pre_delete_rig_layer', None),
    DELETE_COMPONENT_FUNCTION_TYPE: ('pre_delete_component', None),
    DELETE_COMPONENTS_FUNCTION_TYPE: ('pre_delete_components', None),
    DELETE_RIG_FUNCTION_TYPE: ('pre_delete_rig', None)
}

# ======================================================================================================================
# Names
# ======================================================================================================================


class CharacterMembers(enum.Enum):
    top_node = "rig"
    control_rig = "control_rig"
    geometry = "geometry_grp"
    deformation_rig = "deformation_rig"
    locators = "locators_grp"
    world_space = "c_world_space_loc"
    util_group = "util_grp"


# ======================================================================================================================
# Colors
# ======================================================================================================================


class ColorIndex(enum.Enum):
    grey = 0
    black = 1
    dark_grey = 2
    light_grey = 3
    red = 4
    navy_glue = 5
    blue = 6
    dark_green = 7
    purple = 8
    pink = 9
    light_grown = 10
    dark_grown = 11
    dark_red = 12
    bright_red = 13
    bright_green = 14
    light_blue = 15
    white = 16
    bright_yellow = 17
    cyan = 18
    light_green = 19
    light_pink = 20
    light_orange = 21
    yellow = 22
    grass_green = 23
    brown = 24
    dirty_yellow = 25
    mid_green = 26
    navy_green = 27
    dark_cyan = 28
    dark_blue = 29
    dark_pink = 30
    mid_pink = 31

    _rgb_lookup = {1: [0.0, 0.0, 0.0],
                   2: [0.25, 0.25, 0.25],
                   3: [0.6000000238418579, 0.6000000238418579, 0.6000000238418579],
                   4: [0.6079999804496765, 0.0, 0.15700000524520874],
                   5: [0.0, 0.01600000075995922, 0.37599998712539673],
                   6: [0.0, 0.0, 1.0],
                   7: [0.0, 0.2750000059604645, 0.09799999743700027],
                   8: [0.14900000393390656, 0.0, 0.2630000114440918],
                   9: [0.7839999794960022, 0.0, 0.7839999794960022],
                   10: [0.5410000085830688, 0.28200000524520874, 0.20000000298023224],
                   11: [0.24699999392032623, 0.13699999451637268, 0.12200000137090683],
                   12: [0.6000000238418579, 0.14900000393390656, 0.0],
                   13: [1.0, 0.0, 0.0],
                   14: [0.0, 1.0, 0.0],
                   15: [0.0, 0.2549999952316284, 0.6000000238418579],
                   16: [1.0, 1.0, 1.0],
                   17: [1.0, 1.0, 0.0],
                   18: [0.3919999897480011, 0.8629999756813049, 1.0],
                   19: [0.2630000114440918, 1.0, 0.6389999985694885],
                   20: [1.0, 0.6899999976158142, 0.6899999976158142],
                   21: [0.8939999938011169, 0.675000011920929, 0.4749999940395355],
                   22: [1.0, 1.0, 0.3880000114440918],
                   23: [0.0, 0.6000000238418579, 0.32899999618530273],
                   24: [0.6299999952316284, 0.41391000151634216, 0.1889999955892563],
                   25: [0.62117999792099, 0.6299999952316284, 0.1889999955892563],
                   26: [0.40950000286102295, 0.6299999952316284, 0.1889999955892563],
                   27: [0.1889999955892563, 0.6299999952316284, 0.3653999865055084],
                   28: [0.1889999955892563, 0.6299999952316284, 0.6299999952316284],
                   29: [0.1889999955892563, 0.4050999879837036, 0.6299999952316284],
                   30: [0.43595999479293823, 0.1889999955892563, 0.6299999952316284],
                   31: [0.6299999952316284, 0.1889999955892563, 0.41391000151634216]}

    _index_lookup = {"(0.0, 0.0, 0.0)": 1,
                     "(0.25, 0.25, 0.25)": 2,
                     "(0.6000000238418579, 0.6000000238418579, 0.6000000238418579)": 3,
                     "(0.6079999804496765, 0.0, 0.15700000524520874)": 4,
                     "(0.0, 0.01600000075995922, 0.37599998712539673)": 5,
                     "(0.0, 0.0, 1.0)": 6,
                     "(0.0, 0.2750000059604645, 0.09799999743700027)": 7,
                     "(0.14900000393390656, 0.0, 0.2630000114440918)": 8,
                     "(0.7839999794960022, 0.0, 0.7839999794960022)": 9,
                     "(0.5410000085830688, 0.28200000524520874, 0.20000000298023224)": 10,
                     "(0.24699999392032623, 0.13699999451637268, 0.12200000137090683)": 11,
                     "(0.6000000238418579, 0.14900000393390656, 0.0)": 12,
                     "(1.0, 0.0, 0.0)": 13,
                     "(0.0, 1.0, 0.0)": 14,
                     "(0.0, 0.2549999952316284, 0.6000000238418579)": 15,
                     "(1.0, 1.0, 1.0)": 16,
                     "(1.0, 1.0, 0.0)": 17,
                     "(0.3919999897480011, 0.8629999756813049, 1.0)": 18,
                     "(0.2630000114440918, 1.0, 0.6389999985694885)": 19,
                     "(1.0, 0.6899999976158142, 0.6899999976158142)": 20,
                     "(0.8939999938011169, 0.675000011920929, 0.4749999940395355)": 21,
                     "(1.0, 1.0, 0.3880000114440918)": 22,
                     "(0.0, 0.6000000238418579, 0.32899999618530273)": 23,
                     "(0.6299999952316284, 0.41391000151634216, 0.1889999955892563)": 24,
                     "(0.62117999792099, 0.6299999952316284, 0.1889999955892563)": 25,
                     "(0.40950000286102295, 0.6299999952316284, 0.1889999955892563)": 26,
                     "(0.1889999955892563, 0.6299999952316284, 0.3653999865055084)": 27,
                     "(0.1889999955892563, 0.6299999952316284, 0.6299999952316284)": 28,
                     "(0.1889999955892563, 0.4050999879837036, 0.6299999952316284)": 29,
                     "(0.43595999479293823, 0.1889999955892563, 0.6299999952316284)": 30,
                     "(0.6299999952316284, 0.1889999955892563, 0.41391000151634216)": 31}

    @classmethod
    def index_to_rgb(cls, index: int) -> list[float, float, float]:
        if index == 0:
            index = 5
        return cls._rgb_lookup.value[index]

    @classmethod
    def rgb_to_index(cls, rgb):
        rgb = str(rgb)
        return cls._index_lookup.value[rgb]


class SideColor(enum.Enum):
    c = ColorIndex.index_to_rgb(ColorIndex.yellow.value)
    m = ColorIndex.index_to_rgb(ColorIndex.yellow.value)
    l = ColorIndex.index_to_rgb(ColorIndex.blue.value)
    r = ColorIndex.index_to_rgb(ColorIndex.red.value)


class RegionType(enum.Enum):
    Root = 'root'
    End = 'end'
