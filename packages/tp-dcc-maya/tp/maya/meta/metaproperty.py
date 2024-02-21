from __future__ import annotations

from typing import Type

import maya.cmds as cmds

from tp.core import log
from tp.common.python import helpers
from tp.maya import api
from tp.maya.meta import base, utils

AFFECTED_BY_ATTR_NAME = 'affectedBy'

logger = log.tpLogger


def properties_dict(node: api.DGNode):
    """
    Returns all properties from a scene node and store them in a dict.

    :param base.DGNode node: node we want to get properties from.
    :return: dictionary of all properties found, keyed by the type of the property.
    :rtype: dict[type, MetaProperty]
    """

    property_dict = dict()
    if utils.is_in_network(node):
        network = [base.create_meta_node_from_node(api.node_by_name(x)) for x in cmds.listConnections(
            '{}.{}'.format(node.fullPathName(), AFFECTED_BY_ATTR_NAME), type='network')]
        property_list = [x for x in network if MetaProperty in type(x).mro()]
        for property_found in property_list:
            property_dict.setdefault(type(property_found), list())
            property_dict[type(property_found)].append(property_found)

    return property_dict


def all_properties(node: api.DGNode):
    """
    Returns all properties from given node as a list.

    :param base.DGNode node: node to get all properties from.
    :return: list of meta properties instances connected to given node.
    :rtype: list(MetaProperty).
    """

    property_dict = properties_dict(node)
    properties_list = []
    for properties in property_dict.values():
        properties_list += properties

    return properties_list


def validate_property_type(property_type: Type[MetaProperty]) -> Type[MetaProperty]:
    return property_type


def properties(nodes: list[api.DGNode], property_type: Type[MetaProperty]) -> list[MetaProperty]:
    """
    Returns all properties for given Maa nodes.

    :param list[api.DGNode] nodes: list of Maya nodes we want to get properties from.
    :param type property_type: type of property to get.
    :return: list of properties found.
    :rtype: list[MetaProperty].
    """

    valid_type = validate_property_type(property_type)
    found_properties = []
    for node in nodes:
        new_properties = properties_dict(node).get(valid_type, [])
        found_properties = found_properties + new_properties if new_properties else found_properties

    return found_properties


def property(node: api.DGNode, property_type: Type[MetaProperty]) -> MetaProperty | None:
    return helpers.first_in_list(properties([node], property_type), None)


def add_property(node: api.DGNode | api.DagNode, property_type: Type[MetaProperty]) -> MetaProperty | None:
    """
    Adds a property to the given Maya scene object.

    :param api.DGNode or api.DagNode node: node we want to add property to.
    :param Type[MetaProperty property_type: type of the property to add.
    :return: property added.
    :rtype: MetaProperty or None
    """

    if property_type.MULTI_ALLOWED or not properties_dict(node).get(property_type):
        node_namespace = node.namespace()
        new_property = property_type(namespace=node_namespace)
        new_property.connect_node(node)
        new_property.on_add(node)
        return new_property

    return None


# def add_property_by_name(node_name, module_type_name):
# 	"""
# 	Adds a property to a maya scene object from a string tuple.
#
# 	:param pm.nt.PyNode node_name: Maya node name to add property to.
# 	:param tuple module_type_name:  (module_name, type_name) tuple of the property to add.
# 	"""
#
# 	module_name = helpers.first_in_list(module_type_name)
# 	type_name = helpers.index_in_list(module_type_name, 1)
# 	node_class = getattr(sys.modules[module_name], type_name)
#
# 	if node_class.multi_allowed or not properties_dict(node_name).get(node_class):
# 		py_namespeac = node_name.namespace()
# 		node_class(namespace = py_namespace).connect_node(node_name)


class MetaProperty(base.MetaBase):
    """
    Base class for properties. Intended to store data.
    """

    MULTI_ALLOWED = False
    PRIORITY = 0

    @staticmethod
    def inherited_classes():
        """
        Returns all classes that inherit off of this class.

        :return: List of all class types that inherit this class.
        :rtype: list[type]
        """

        class_list = MetaProperty.__subclasses__()
        for c in MetaProperty.__subclasses__():
            class_list += c.inherited_classes()

        return class_list

    def on_add(self, node: api.DGNode):
        """
        Function that is called when a node is connected to a meta property.

        :param api.DGNode node: node connected.
        """

        return None

    def act(self):
        """
        Performs the action for the specific node.
        """

        return None

    def act_post(self, asset, event_args, **kwargs):
        """
        Performs the post action for the specific node.

        :param asset:
        :param event_args:
        :param kwargs:
        :return:
        """

        return None

    def data(self):
        """
        Returns a dictionary with the data from the list of attributes in the property node.

        :return: meta property data.
        :rtype: dict
        """

        data_dict = dict()
        for attr in self.iterateExtraAttributes():
            data_dict[attr.name().split('.')[-1]] = attr.value()

        return data_dict

    def set_data(self, kwargs):
        """
        Sets meta property attributes based on given dictionary.

        :param dict kwargs: meta property data.
        """

        for attr_name, attr_value in kwargs.items():
            attr_found = self.attribute(attr_name)
            if not attr_found:
                logger.warning('Was not possible to set data attribute name: {}'.format(attr_name))
                continue
            attr_found.set(attr_value)

    def compare(self, data):
        """
        Compares two different meta properties based on their data.

        :param dit data: data dictionary to compare agains.
        :return: True if if passed data is the same as this meta property instance data; False otherwise.
        :rtype: bool
        """

        return self.data() == data

    def disconnect(self, node):
        """
        Disconnects the property from given node connected to it.
        """

        for destination_plug in self.message.destinations():
            destination_node = destination_plug.node()
            if destination_node == node:
                self.message.disconnect(destination_plug)

    def disconnect_all(self):
        """
        Disconnects the property from any node connected to it.
        """

        self.message.disconnectAll()

    def downstream(self, check_type):
        """
        Returns the first network node by following the .message attribute connections.

        :param str check_type: meta node instance type to search.
        :return: first found meta node instance that matches given type.
        """

        return base.find_meta_node_from_node(self, check_type, attribute='message')

    def upstream(self, check_type):
        """
        Returns the first network node by following the children attribute connection.

        :param str check_type: meta node instance type to search.
        :return: first found meta node instance that matches given type.
        """

        return base.find_meta_node_from_node(self, check_type, attribute=AFFECTED_BY_ATTR_NAME)

    def connections(self, node_type=None, attribute_name=None):
        """
        Returns all connections from the network node message attribute.

        :param str or None node_type: optional filter connections by type.
        :param str or None attribute_name: optional attribute name to get connections from. Defaults to message.
        :return: list of nodes.
        :rtype: list(tp.maya.api.base.DGNode)
        """

        found_nodes = list()
        if self.exists():
            attribute_name = '{}.{}'.format(self.fullPathName(), attribute_name or 'message')
            filter_out = cmds.listConnections(attribute_name, type='nodeGraphEditorInfo') or list()
            connected_nodes = cmds.listConnections(attribute_name, type=node_type) if node_type else cmds.listConnections(attribute_name)
            found_nodes = [api.node_by_name(x) for x in connected_nodes or list() if x not in filter_out]

        return found_nodes

    def connect_node(self, node, attribute_name=None):
        """
        Connects a single node to this network node.

        :param tp.maya.api.base.DGNode node: node to connect.
        :param str attribute_name: optional attribute name.
        """

        if not utils.is_in_network(node):
            cmds.addAttr(node.fullPathName(), ln=AFFECTED_BY_ATTR_NAME, dt='stringArray', m=True)

        if node not in self.connections(attribute_name=attribute_name):
            connect_attr = node.affectedBy[len(node.affectedBy)]
            for x in range(len(node.affectedBy)):
                if not cmds.listConnections(node.affectedBy[x].name()):
                    connect_attr = node.affectedBy[x]
                    break

            if not attribute_name:
                self.message.connect(connect_attr)
            else:
                self.attribute(attribute_name).connect(connect_attr)


class CommonMetaProperty(MetaProperty):
    """
    Base class property for any properties that can be added to anything.
    """

    @staticmethod
    def inherited_classes():
        """
        Returns all classes that inherit off of this class.

        :return: List of all class types that inherit this class.
        :rtype: list[type]
        """

        return CommonMetaProperty.__subclasses__()

    def on_add(self, node):
        pass
