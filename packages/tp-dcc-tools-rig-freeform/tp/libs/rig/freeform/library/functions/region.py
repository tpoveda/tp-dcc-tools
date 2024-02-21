from __future__ import annotations

from tp.maya import api
from tp.maya.cmds import joint
from tp.maya.meta import metaproperty
from tp.libs.rig.freeform import consts
from tp.libs.rig.freeform.meta import properties


def create_region(
        root_joint: api.Joint, end_joint: api.Joint, side: str, region: str, group: str, com_object: str,
        com_region: str, com_weight: float, validate_joint_check: bool = True) -> tuple[bool, str]:

    valid_check = True
    if validate_joint_check:
        valid_check = joint.is_joint_below_hierarchy(end_joint.fullPathName(), root_joint.fullPathName())

    markup_exists = check_markup_exists(root_joint, end_joint, side, region)
    if valid_check and not markup_exists and root_joint and end_joint:
        add_region_properties_to_joint(
            root_joint, side, region, tag='root', group=group, com_object=com_object, com_region=com_region,
            com_weight=com_weight)
        add_region_properties_to_joint(
            end_joint, side, region, tag='end', group=group, com_object=com_object, com_region=com_region,
            com_weight=com_weight)
    else:
        error_message = 'Markup already exists on joints.' if markup_exists else 'Cannot find picked joints'
        error_message = error_message if valid_check else 'Root and End joints cannot create a joint chain.'
        return False, error_message

    return True, ''


def change_region_root_joint(
        side: str, region: str, old_root: api.Joint, new_root: api.Joint, end_joint: api.Joint) -> bool:
    valid_check = joint.is_joint_below_hierarchy(
        end_joint.fullPathName(), new_root.fullPathName()) if old_root and new_root else False
    if not valid_check:
        return False

    markup_properties = region_markup_meta_nodes([old_root])
    for markup in matching_markup(markup_properties, side, region):
        markup.disconnect(old_root)
        markup.connect_node(new_root)

    return True


def change_region_end_joint(
        side: str, region: str, root_joint: api.Joint, old_end: api.Joint, new_end: api.Joint) -> bool:
    valid_check = joint.is_joint_below_hierarchy(
        new_end.fullPathName(), root_joint.fullPathName()) if old_end and new_end else False
    if not valid_check:
        return False

    markup_properties = region_markup_meta_nodes([old_end])
    for markup in matching_markup(markup_properties, side, region):
        markup.disconnect(old_end)
        markup.connect_node(new_end)

    return True

def add_region_properties_to_joint(
        joint: api.Joint, side: str, region: str, tag: str, group: str, com_object: str, com_region: str,
        com_weight: float):
    """
    Internal function that adds a RegionMarkupProperty into the given node object.

    :param api.Joint joint: joint we want to add region markup property to.
    :param str side: name of the side.
    :param str region: name of the region.
    :param str tag: whether we are adding a root or end property.
    :param str group: name of the group.
    :param str com_object: name of the COM object.
    :param str com_region: name of the COM region.
    :param float com_weight: weight of the COM.
    """

    rig_property = metaproperty.add_property(joint, properties.RegionMarkupProperty)
    rig_property.set_data({
        consts.SIDE_ATTR: side, consts.REGION_ATTR: region, consts.TAG_ATTR: tag, consts.GROUP_ATTR: group,
        consts.COM_OBJECT_ATTR: com_object, consts.COM_REGION_ATTR: com_region, consts.COM_WEIGHT_ATTR: com_weight
    })


def region_markup_meta_nodes(joints: list[api.Joint]) -> list[properties.RegionMarkupProperty]:
    return metaproperty.properties(joints, properties.RegionMarkupProperty)


def check_markup_exists(root_joint: api.Joint, end_joint: api.Joint, side: str, region: str) -> bool:
    markup_properties = region_markup_meta_nodes([root_joint, end_joint])
    return True if matching_markup(markup_properties, side, region) else False


def matching_markup(
        properties_list: list[properties.RegionMarkupProperty],
        side: str, region: str) -> list[properties.RegionMarkupProperty]:
    """
    Internal function that returns the scene network rig markup node that matches the info given in the region model.

    :param list[properties.RegionMarkupProperty] properties_list:
    :param str side: name of the side.
    :param str region: name of the region.
    :return: list of region markup nodes that matches the side and value of the given region.
    :rtype: list[properties.RegionMarkupProperty]
    """

    markup_network_nodes: list[properties.RegionMarkupProperty] = []
    for markup_network in properties_list:
        if markup_network.attribute(consts.SIDE_ATTR).value() == side and \
                markup_network.attribute(consts.REGION_ATTR).value() == region:
            markup_network_nodes.append(markup_network)

    return markup_network_nodes
