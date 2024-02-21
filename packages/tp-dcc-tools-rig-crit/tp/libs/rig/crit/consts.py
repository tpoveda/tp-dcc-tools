from __future__ import annotations

from tp.maya.api import spaceswitch


# ======================================================================================================================
# MetaClasses Types
# ======================================================================================================================

RIG_TYPE = 'critRig'
COMPONENT_TYPE = 'critComponent'
ANIM_COMPONENT_TYPE = 'critAnimComponent'
COMPONENTS_LAYER_TYPE = 'critComponentsLayer'
GUIDE_LAYER_TYPE = 'critGuideLayer'
INPUT_LAYER_TYPE = 'critInputLayer'
OUTPUT_LAYER_TYPE = 'critOutputLayer'
REGIONS_LAYER_TYPE = 'critRegionsLayer'
SKELETON_LAYER_TYPE = 'critSkeletonLayer'
RIG_LAYER_TYPE = 'critRigLayer'
XGROUP_LAYER_TYPE = 'critXGroupLayer'
GEOMETRY_LAYER_TYPE = 'critGeometryLayer'
LAYER_TYPES = (
    COMPONENTS_LAYER_TYPE,
    INPUT_LAYER_TYPE,
    OUTPUT_LAYER_TYPE,
    GUIDE_LAYER_TYPE,
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

CRIT_ID_ATTR = 'critId'
CRIT_VERSION_ATTR = 'critVersion'
CRIT_NAME_ATTR = 'critName'
CRIT_SIDE_ATTR = 'critSide'
CRIT_IS_CRIT_ATTR = 'critIsCrit'
CRIT_IS_ROOT_ATTR = 'critIsRoot'
CRIT_IS_ENABLED_ATTR = 'critEnabled'
CRIT_ROOT_TRANSFORM_ATTR = 'critRootTransform'
CRIT_RIG_CONFIG_ATTR = 'critConfig'
CRIT_CONTROL_DISPLAY_LAYER_ATTR = 'critControlDisplayLayer'
CRIT_ROOT_SELECTION_SET_ATTR = 'critRootSelectionSet'
CRIT_CONTROL_SELECTION_SET_ATTR = 'critControlSelectionSet'
CRIT_JOINT_SELECTION_SET_ATTR = 'critJointSelectionSet'
CRIT_SKELETON_SELECTION_SET_ATTR = 'critSkeletonSelectionSet'
CRIT_BUILD_SCRIPT_CONFIG_ATTR = 'critBuildScriptConfig'
CRIT_EXTRA_NODES_ATTR = 'critExtraNodes'
CRIT_CONNECTOR_ATTR = 'critConnector'
CRIT_CONNECTORS_ATTR = 'critConnectors'
CRIT_CONNECTOR_START_ATTR = 'critConnectorStart'
CRIT_CONNECTOR_END_ATTR = 'critConnectorEnd'
CRIT_CONNECTOR_ATTRIBUTE_HOLDER_ATTR = 'critConnectorAttrHolder'
CRIT_SETTING_NODES_ATTR = 'critSettingNodes'
CRIT_SETTING_NODE_ATTR = 'critSettingNode'
CRIT_SETTING_NAME_ATTR = 'critSettingName'
CRIT_TAGGED_NODE_ATTR = 'critTaggedNode'
CRIT_TAGGED_NODE_SOURCE_ATTR = 'critTaggedNodeSource'
CRIT_TAGGED_NODE_ID_ATTR = 'critTaggedNodeId'
CRIT_IS_COMPONENT_ATTR = 'critIsComponent'
CRIT_IS_GUIDE_ATTR = 'critIsGuide'
CRIT_IS_INPUT_ATTR = 'critIsInput'
CRIT_IS_OUTPUT_ATTR = 'critIsOutput'
CRIT_COMPONENT_TYPE_ATTR = 'critComponentType'
CRIT_CONTAINER_ATTR = 'critContainer'
CRIT_HAS_GUIDE_ATTR = 'critHasGuide'
CRIT_HAS_SKELETON_ATTR = 'critHasSkeleton'
CRIT_HAS_POLISHED_ATTR = 'critHasPolished'
CRIT_HAS_RIG_ATTR = 'critHasRig'
CRIT_LAYER_TYPE_ATTR = 'critLayerType'
CRIT_GUIDE_SHAPE_ATTR = 'critGuideShape'
CRIT_GUIDE_SNAP_PIVOT_ATTR = 'critGuideSnapPivot'
CRIT_GUIDE_SHAPE_PRIMARY_ATTR = 'critGuideShapePrimary'
CRIT_REQUIRES_PIVOT_SHAPE_ATTR = 'critRequiresPivotShape'
CRIT_PIVOT_COLOR_ATTR = 'critPivotColor'
CRIT_PIVOT_SHAPE_ATTR = 'critPivotShape'
CRIT_PIVOT_NODE_ATTR = 'critPivotNode'
CRIT_DISPLAY_AXIS_SHAPE_ATTR = 'critDisplayAxisShape'
CRIT_COMPONENT_GROUP_ATTR = 'critComponentGroup'
CRIT_COMPONENT_DESCRIPTOR_ATTR = 'critComponentDescriptor'
CRIT_AUTO_ALIGN_ATTR = 'critAutoAlign'
CRIT_AUTO_ALIGN_AIM_VECTOR_ATTR = 'critAutoAlignAimVector'
CRIT_AUTO_ALIGN_UP_VECTOR_ATTR = 'critAutoAlignUpVector'
CRIT_MIRROR_ATTR = 'critMirror'
CRIT_MIRROR_BEHAVIOUR_ATTR = 'critMirrorBehaviour'
CRIT_GUIDES_ATTR = 'critGuides'
CRIT_INPUTS_ATTR = 'critInputs'
CRIT_OUTPUTS_ATTR = 'critOutputs'
CRIT_GUIDE_NODE_ATTR = 'critGuideNode'
CRIT_GUIDE_ID_ATTR = 'critGuideId'
CRIT_GUIDE_SRTS_ATTR = 'critSrts'
CRIT_GUIDE_SHAPE_NODE_ATTR = 'critShapeNode'
CRIT_GUIDE_SOURCE_GUIDES_ATTR = 'critSourceGuides'
CRIT_GUIDE_SOURCE_GUIDE_ATTR = 'critSourceGuide'
CRIT_GUIDE_SOURCE_GUIDE_CONSTRAINT_NODES_ATTR = 'critConstraintNodes'
CRIT_GUIDE_MIRROR_ROTATION_ATTR = 'critGuideMirrorRotation'
CRIT_GUIDE_AUTO_ALIGN_ATTR = 'critGuideAutoAlign'
CRIT_GUIDE_AIM_VECTOR_ATTR = 'critGuideAimVector'
CRIT_GUIDE_UP_VECTOR_ATTR = 'critGuideUpVector'
CRIT_GUIDE_VISIBILITY_ATTR = 'critGuideVisibility'
CRIT_GUIDE_CONTROL_VISIBILITY_ATTR = 'critGuideControlVisibility'
CRIT_GUIDE_PIN_SETTINGS_ATTR = 'critPinSettings'
CRIT_GUIDE_PIN_PINNED_ATTR = 'critPinned'
CRIT_GUIDE_PIN_PINNED_CONSTRAINTS_ATTR = 'critPinnedConstraints'
CRIT_GUIDE_CONNECTORS_GROUP_ATTR = 'critGuideConnectorsGroup'
CRIT_GUIDE_LIVE_LINK_NODES_ATTR = 'critLiveLinkNodes'
CRIT_GUIDE_IS_LIVE_LINK_ACTIVE_ATTR = 'critIsLiveLinkActive'
CRIT_GUIDE_DG_GRAPH_ATTR = 'critDGGraph'
CRIT_GUIDE_DG_GRAPH_ID_ATTR = 'critDGGraphId'
CRIT_GUIDE_DG_GRAPH_NODES_ATTR = 'critDGGraphNodes'
CRIT_GUIDE_DG_GRAPH_NODE_ID_ATTR = 'critDGGraphNodeId'
CRIT_GUIDE_DG_GRAPH_NODE_ATTR = 'critDGGraphNode'
CRIT_GUIDE_DG_GRAPH_NAME_ATTR = 'critDGGraphName'
CRIT_GUIDE_DG_GRAPH_METADATA_ATTR = 'critDGGraphMetaData'
CRIT_GUIDE_DG_GRAPH_INPUT_NODE_ATTR = 'critDGGraphInputNode'
CRIT_GUIDE_DG_GRAPH_OUTPUT_NODE_ATTR = 'critDGGraphOutputNode'
CRIT_INPUT_NODE_ATTR = 'critInputNode'
CRIT_INPUT_ID_ATTR = 'critInputId'
CRIT_IS_INPUT_ROOT_ATTR = 'critIsInputRoot'
CRIT_OUTPUT_NODE_ATTR = 'critOutputNode'
CRIT_OUTPUT_ID_ATTR = 'critOutputId'
CRIT_GUIDE_OFFSET_NODE_NAME_ATTR = 'critGuideOffset'
CRIT_GUIDE_OFFSET_ATTR_NAME_ATTR = 'critGuideOffset'
CRIT_INPUT_OFFSET_ATTR_NAME_ATTR = 'critInputGuideOffset'
CRIT_INPUT_GUIDE_OFFSET_NODE_NAME_ATTR = 'critInputGuideOffset'
CRIT_GUIDE_OFFSET_TRANSFORMS_ATTR = 'critTransforms'
CRIT_GUIDE_OFFSET_TRANSFORM_ID_ATTR = 'critTransformId'
CRIT_GUIDE_OFFSET_TRANSFORM_LOCAL_MATRIX_ATTR = 'critLocalMatrix'
CRIT_GUIDE_OFFSET_TRANSFORM_WORLD_MATRIX_ATTR = 'critWorldMatrix'
CRIT_GUIDE_OFFSET_TRANSFORM_PARENT_MATRIX_ATTR = 'critParentMatrix'
CRIT_SOURCE_INPUTS_ATTR = 'critSourceInputs'
CRIT_SOURCE_INPUT_ATTR = 'critSourceInput'
CRIT_SOURCE_INPUT_CONSTRAINT_NODES_ATTR = 'critConstraintNodes'
CRIT_JOINTS_ATTR = 'critCritJoints'
CRIT_JOINT_ATTR = 'critJoint'
CRIT_JOINT_ID_ATTR = 'critJointId'
CRIT_REGIONS_ATTR = 'critCritRegions'
CRIT_REGION_NAME_ATTR = 'critRegionName'
CRIT_REGION_SIDE_ATTR = 'critRegionSide'
CRIT_REGION_START_JOINT_ID_ATTR = 'critRegionStartJointId'
CRIT_REGION_END_JOINT_ID_ATTR = 'critRegionEndJointId'
CRIT_CONTROL_MODE_ATTR = 'critControlMode'
CRIT_CONTROLS_ATTR = 'critCritControls'
CRIT_CONTROL_NODE_ATTR = 'critControlNode'
CRIT_CONTROL_ID_ATTR = 'critControlId'
CRIT_CONTROL_SRTS_ATR = 'critSrts'
CRIT_SPACE_SWITCHING_ATTR = 'critSpaceSwitching'
CRIT_SPACE_SWITCH_CONTROL_NAME_ATTR = 'critSpaceControlAttrName'
CRIT_SPACE_SWITCH_DRIVEN_NODE_ATTR = 'critSpaceDrivenNode'

# ======================================================================================================================
# Component Descriptor Attribute Names
# ======================================================================================================================

CRIT_DESCRIPTOR_CACHE_INFO_ATTR = 'critDefCacheInfo'
CRIT_DESCRIPTOR_CACHE_GUIDE_DAG_ATTR = 'critDescriptorCacheGuideLayerDag'
CRIT_DESCRIPTOR_CACHE_GUIDE_DG_ATTR = 'critDescriptorCacheGuideLayerDg'
CRIT_DESCRIPTOR_CACHE_GUIDE_SETTINGS_ATTR = 'critDescriptorCacheGuideLayerSettings'
CRIT_DESCRIPTOR_CACHE_GUIDE_METADATA_ATTR = 'critDescriptorCacheGuideLayerMetadata'
CRIT_DESCRIPTOR_CACHE_DEFORM_DAG_ATTR = 'critDescriptorCacheDeformLayerDag'
CRIT_DESCRIPTOR_CACHE_DEFORM_SETTINGS_ATTR = 'critDescriptorCacheDeformLayerSettings'
CRIT_DESCRIPTOR_CACHE_DEFORM_METADATA_ATTR = 'critDescriptorCacheDeformLayerMetadata'
CRIT_DESCRIPTOR_CACHE_INPUT_DAG_ATTR = 'critDescriptorCacheInputLayerDag'
CRIT_DESCRIPTOR_CACHE_INPUT_SETTINGS_ATTR = 'critDescriptorCacheInputLayerSettings'
CRIT_DESCRIPTOR_CACHE_INPUT_METADATA_ATTR = 'critDescriptorCacheInputLayerMetadata'
CRIT_DESCRIPTOR_CACHE_OUTPUT_DAG_ATTR = 'critDescriptorCacheOutputLayerDag'
CRIT_DESCRIPTOR_CACHE_OUTPUT_SETTINGS_ATTR = 'critDescriptorCacheOutputLayerSettings'
CRIT_DESCRIPTOR_CACHE_OUTPUT_METADATA_ATTR = 'critDescriptorCacheOutputLayerMetadata'
CRIT_DESCRIPTOR_CACHE_RIG_DAG_ATTR = 'critDescriptorCacheRigLayerDag'
CRIT_DESCRIPTOR_CACHE_RIG_DG_ATTR = 'critDescriptorCacheGuideLayerDg'
CRIT_DESCRIPTOR_CACHE_RIG_SETTINGS_ATTR = 'critDescriptorCacheRigLayerSettings'
CRIT_DESCRIPTOR_CACHE_RIG_METADATA_ATTR = 'critDescriptorCacheRigLayerMetadata'
CRIT_DESCRIPTOR_CACHE_SPACE_SWITCHING_ATTR = 'critDescriptorCacheSpaceSwitching'
CRIT_DESCRIPTOR_CACHE_ATTR_NAMES = (
    CRIT_DESCRIPTOR_CACHE_INFO_ATTR,
    CRIT_DESCRIPTOR_CACHE_GUIDE_DAG_ATTR,
    CRIT_DESCRIPTOR_CACHE_GUIDE_DG_ATTR,
    CRIT_DESCRIPTOR_CACHE_GUIDE_SETTINGS_ATTR,
    CRIT_DESCRIPTOR_CACHE_GUIDE_METADATA_ATTR,
    CRIT_DESCRIPTOR_CACHE_DEFORM_DAG_ATTR,
    CRIT_DESCRIPTOR_CACHE_DEFORM_SETTINGS_ATTR,
    CRIT_DESCRIPTOR_CACHE_DEFORM_METADATA_ATTR,
    CRIT_DESCRIPTOR_CACHE_INPUT_DAG_ATTR,
    CRIT_DESCRIPTOR_CACHE_INPUT_SETTINGS_ATTR,
    CRIT_DESCRIPTOR_CACHE_INPUT_METADATA_ATTR,
    CRIT_DESCRIPTOR_CACHE_OUTPUT_DAG_ATTR,
    CRIT_DESCRIPTOR_CACHE_OUTPUT_SETTINGS_ATTR,
    CRIT_DESCRIPTOR_CACHE_OUTPUT_METADATA_ATTR,
    CRIT_DESCRIPTOR_CACHE_RIG_DAG_ATTR,
    CRIT_DESCRIPTOR_CACHE_RIG_DG_ATTR,
    CRIT_DESCRIPTOR_CACHE_RIG_SETTINGS_ATTR,
    CRIT_DESCRIPTOR_CACHE_RIG_METADATA_ATTR,
    CRIT_DESCRIPTOR_CACHE_SPACE_SWITCHING_ATTR
)

# ======================================================================================================================
# Non Publishable Attributes
# ======================================================================================================================

ATTRIBUTES_TO_SKIP_PUBLISH = [CRIT_ID_ATTR, 'metaNode', spaceswitch.TP_CONSTRAINTS_ATTR_NAME]

# ======================================================================================================================
# Extensions
# ======================================================================================================================

DESCRIPTOR_EXTENSION = '.descriptor'
TEMPLATE_EXTENSION = '.template'
GRAPH_EXTENSION = '.dgGraph'

# ======================================================================================================================
# Descriptor Keys
# ======================================================================================================================

VERSION_DESCRIPTOR_KEY = 'descriptorVersion'
PARENT_DESCRIPTOR_KEY = 'parent'
CONNECTIONS_DESCRIPTOR_KEY = 'connections'
DAG_DESCRIPTOR_KEY = 'dag'
DG_DESCRIPTOR_KEY = 'dg'
SETTINGS_DESCRIPTOR_KEY = 'settings'
NAME_DESCRIPTOR_KEY = 'name'
SIDE_DESCRIPTOR_KEY = 'side'
TYPE_DESCRIPTOR_KEY = 'type'
ENABLED_DESCRIPTOR_KEY = 'enabled'
METADATA_DESCRIPTOR_KEY = 'metadata'
SPACE_SWITCH_DESCRIPTOR_KEY = 'spaceSwitching'
NAMING_PRESET_DESCRIPTOR_KEY = 'namingPreset'
INPUT_LAYER_DESCRIPTOR_KEY = 'inputLayer'
OUTPUT_LAYER_DESCRIPTOR_KEY = 'outputLayer'
GUIDE_LAYER_DESCRIPTOR_KEY = 'guideLayer'
RIG_LAYER_DESCRIPTOR_KEY = 'rigLayer'
SKELETON_LAYER_DESCRIPTOR_KEY = 'skeletonLayer'
GUIDE_MARKING_MENU_DESCRIPTOR_KEY = 'markingMenuGuide'
SKELETON_MARKING_MENU_DESCRIPTOR_KEY = 'markingMenuSkeleton'
RIG_MARKING_MENU_DESCRIPTOR_KYE = 'markingMenuRig'
ANIM_MARKING_MENU_DESCRIPTOR_KEY = 'markingMenuAnim'
DEFAULT_GUIDE_MARKING_MENU = 'critDefaultGuideMenu'
DEFAULT_SKELETON_MARKING_MENU = 'critDefaultSkeletonMenu'
DEFAULT_RIG_MARKING_MENU = 'critDefaultRigMenu'
LAYER_DESCRIPTOR_KEYS = (
    INPUT_LAYER_DESCRIPTOR_KEY,
    OUTPUT_LAYER_DESCRIPTOR_KEY,
    GUIDE_LAYER_DESCRIPTOR_KEY,
    RIG_LAYER_DESCRIPTOR_KEY,
    SKELETON_LAYER_DESCRIPTOR_KEY
)
DESCRIPTOR_KEYS_TO_SKIP_UPDATE = (
    GUIDE_LAYER_DESCRIPTOR_KEY,
    INPUT_LAYER_DESCRIPTOR_KEY,
    OUTPUT_LAYER_DESCRIPTOR_KEY,
    SKELETON_LAYER_DESCRIPTOR_KEY,
    RIG_LAYER_DESCRIPTOR_KEY,
    SPACE_SWITCH_DESCRIPTOR_KEY
)

# ======================================================================================================================
# Naming Preset Keys
# ======================================================================================================================

DEFAULT_PRESET_NAME = 'CRIT'
DEFAULT_BUILTIN_PRESET_NAME = 'crit'

# ======================================================================================================================
# Environment Variable Keys
# ======================================================================================================================

COMPONENTS_ENV_VAR_KEY = 'CRIT_COMPONENTS_PATHS'
DESCRIPTORS_ENV_VAR_KEY = 'CRIT_DESCRIPTORS_PATHS'
TEMPLATES_ENV_VAR_KEY = 'CRIT_TEMPLATES_PATHS'
GRAPHS_ENV_VAR_KEY = 'CRIT_GRAPHS_PATHS'

# ======================================================================================================================
# Guide Visibility State Types
# ======================================================================================================================

GUIDE_PIVOT_STATE = 0
GUIDE_CONTROL_STATE = 1
GUIDE_PIVOT_CONTROL_STATE = 2

# ======================================================================================================================
# Mirror Behaviour Types
# ======================================================================================================================

MIRROR_BEHAVIOURS_TYPES = ['Behaviour', 'Relative']

# ======================================================================================================================
# Build States
# ======================================================================================================================

NOT_BUILT_STATE = 0
GUIDES_STATE = 1
CONTROL_VIS_STATE = 2
SKELETON_STATE = 3
RIG_STATE = 4
POLISH_STATE = 5

# ======================================================================================================================
# Build Script Function Types
# ======================================================================================================================

GUIDE_FUNCTION_TYPE = 0
SKELETON_FUNCTION_TYPE = 1
RIG_FUNCTION_TYPE = 2
POLISH_FUNCTION_TYPE = 3
DELETE_GUIDE_LAYER_FUNCTION_TYPE = 4
DELETE_SKELETON_LAYER_FUNCTION_TYPE = 5
DELETE_RIG_LAYER_FUNCTION_TYPE = 6
DELETE_COMPONENT_FUNCTION_TYPE = 7
DELETE_COMPONENTS_FUNCTION_TYPE = 8
DELETE_RIG_FUNCTION_TYPE = 9
BUILD_SCRIPT_FUNCTIONS_MAPPING = {
    GUIDE_FUNCTION_TYPE: ('pre_guide_build', 'post_guide_build'),
    SKELETON_FUNCTION_TYPE: ('pre_skeleton_build', 'post_skeleton_build'),
    RIG_FUNCTION_TYPE: ('pre_rig_build', 'post_rig_build'),
    POLISH_FUNCTION_TYPE: ('pre_polish', 'post_polish_build'),
    DELETE_GUIDE_LAYER_FUNCTION_TYPE: ('pre_delete_guide_layer', None),
    DELETE_SKELETON_LAYER_FUNCTION_TYPE: ('pre_delete_skeleton_layer', None),
    DELETE_RIG_LAYER_FUNCTION_TYPE: ('pre_delete_rig_layer', None),
    DELETE_COMPONENT_FUNCTION_TYPE: ('pre_delete_component', None),
    DELETE_COMPONENTS_FUNCTION_TYPE: ('pre_delete_components', None),
    DELETE_RIG_FUNCTION_TYPE: ('pre_delete_rig', None)
}

# ======================================================================================================================
# Guide Alignment Default Aim/Up Vectors
# ======================================================================================================================

DEFAULT_AIM_VECTOR = (1.0, 0.0, 0.0)
DEFAULT_UP_VECTOR = (0.0, 1.0, 0.0)

# ======================================================================================================================
# Default Guide Pivot Color
# ======================================================================================================================

DEFAULT_GUIDE_PIVOT_COLOR = (1.0, 1.0, 0.0)
