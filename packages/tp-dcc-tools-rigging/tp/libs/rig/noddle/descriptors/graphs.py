from __future__ import annotations

from tp.common.python import helpers

from tp.libs.rig.noddle.descriptors import nodes as descriptor_nodes


class NamedGraph(helpers.ObjectDict):
    """
    Wrapper class that contains a network of dependency graph nodes and its internal connections.
    """

    @classmethod
    def from_data(cls, graph_data: dict) -> NamedGraph:
        """
        Transforms the given data into a set of joint and attribute descriptor classes.

        :param dict graph_data: list of dictionaries where each dictionary is a named graph.
        :return: new named graph descriptor instance.
        :rtype: NamedGraph
        """

        graph_id = graph_data.get('id', '')

        return cls({
            'id': graph_id,
            'name': graph_data.get('name', graph_id),
            'nodes': [descriptor_nodes.DGNodeDescriptor(i) for i in graph_data.get('nodes', list())],
            'connections': graph_data.get('connections', list()),
            'inputs': graph_data.get('inputs', dict()),
            'outputs': graph_data.get('outputs', dict()),
            'metaData': graph_data.get('metaData', dict())
        })

    @property
    def graph_id(self) -> str:
        """
        Returns the graph ID.

        :return: graph ID.
        """

        return self['id']

    @graph_id.setter
    def graph_id(self, value: str):
        """
        Sets the ID for this graph.

        :param str value: graph ID.
        """

        self['id'] = value

    @property
    def name(self) -> str:
        """
        Returns the graph name.

        :return: graph name.
        :rtype: str
        """

        return self['name']

    @name.setter
    def name(self, value: str):
        """
        Sets graph name.

        :param str value: graph name.
        """

        self['name'] = value

    @property
    def nodes(self) -> list[descriptor_nodes.DGNodeDescriptor]:
        """
        Returns the DG nodes for this graph.

        :return: list of dg node descriptors.
        :rtype: list[descriptor_nodes.DGNodeDescriptor]
        """

        return self['nodes']

    @property
    def inputs(self) -> dict:
        """
        Returns graph inputs.

        :return: inputs dictionary.
        :rtype: dict
        """

        return self.get('inputs', dict())

    @property
    def outputs(self) -> dict:
        """
        Returns graph outputs.

        :return: inputs dictionary.
        :rtype: dict
        """

        return self.get('outputs', dict())

    @property
    def connections(self) -> list[dict]:
        """
        Returns the graph internal connections.

        :return: list of graph connections.
        :rtype: list[dict]
        """

        return self['connections']

    def node(self, node_id: str) -> descriptor_nodes.DGNodeDescriptor | None:
        """
        Returns graph node with given ID.

        :param str node_id: ID of the graph node to retrieve.
        :return: found graph node descriptor.
        :rtype: descriptor_nodes.DGNodeDescriptor or None
        """

        for node_descriptor in self.nodes:
            if node_descriptor.id == node_id:
                return node_descriptor

        return None


class NamedGraphs(list):
    """
    Class that wraps a list of NamedGraph instances
    """

    @classmethod
    def from_data(cls, layer_data: dict) -> NamedGraphs:
        """
        Transforms the given data into a set of joint and attribute descriptor classes.

        :param dict layer_data: list of dictionaries where each dictionary is a named graph.
        :return: new named graph descriptor instance.
        :rtype: NamedGraphs
        """

        return cls([NamedGraph.from_data(i) for i in layer_data])

    def graph(self, graph_id: str) -> NamedGraph | None:
        """
        Returns the graph descriptor with given ID.

        :param str graph_id: ID of the graph to retrieve.
        :return: found graph descriptor with given ID.
        :rtype: NamedGraph or None
        """

        for graph_descriptor in self:
            if graph_descriptor.id == graph_id:
                return graph_descriptor

        return None
