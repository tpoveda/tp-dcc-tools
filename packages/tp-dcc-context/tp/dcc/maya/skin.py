from __future__ import annotations

from typing import Iterator, Any

from overrides import override

import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.dcc import node
from tp.dcc.abstract import skin
from tp.maya.om import dagpath, plugs, plugmutators, skin as skin_utils

logger = log.tpLogger


class MayaSkin(node.FnNode, skin.AbstractSkin):
    """
    Overload of skin.AbstractSkin used to interface with skinning in Maya.
    """

    __slots__ = ('_transform', '_shape', '_intermediate_object')
    __color_set_name__ = 'paintWeightsColorSet1'
    __color_ramp__ = '1,0,0,1,1,1,0.5,0,0.8,1,1,1,0,0.6,1,0,1,0,0.4,1,0,0,1,0,1'

    def __init__(self, *args, **kwargs):

        self._transform = OpenMaya.MObjectHandle()
        self._shape = OpenMaya.MObjectHandle()
        self._intermediate_object = OpenMaya.MObjectHandle()

        super().__init__(*args, **kwargs)

    @classmethod
    @override(check_signature=False)
    def create(cls, mesh: OpenMaya.MObject, skin_name: str | None = None) -> MayaSkin:
        """
        Creates a skin and assigns it to the given mesh.

        :param OpenMaya.MObject mesh: mesh to apply skin to.
        :param str skin_name: optional name for the skin name.
        :return: newly created skin.
        :rtype: MayaSkin
        """

        skin_utils.clear_intermediate_objects(mesh)
        skin_utils.lock_transform(mesh)

        mesh_name = dagpath.dag_path(mesh).fullPathName()
        skin_cluster_kwargs = {'type': 'skinCluster'}
        if skin_name:
            skin_cluster_kwargs['name'] = skin_name
        skin_cluster = cmds.deformer(mesh_name, **skin_cluster_kwargs)[0]
        return cls(skin_cluster)

    @override(check_signature=False)
    def set_object(self, obj: str | OpenMaya.MObject | OpenMaya.MDagPath):
        skin_cluster = dagpath.find_deformer_by_type(obj, OpenMaya.MFn.kSkinClusterFilter)
        super().set_object(skin_cluster)
        transform, shape, intermediate_object = dagpath.decompose_deformer(skin_cluster)
        self._transform = OpenMaya.MObjectHandle(transform)
        self._shape = OpenMaya.MObjectHandle(shape)
        self._intermediate_object = OpenMaya.MObjectHandle(intermediate_object)

    @override(check_signature=False)
    def transform(self) -> OpenMaya.MObject:
        """
        Returns the transform node associated with this skin.

        :return: skin transform node.
        :rtype: OpenMaya.MObject
        """

        return self._transform.object()

    @override(check_signature=False)
    def shape(self) -> OpenMaya.MObject:
        """
        Returns teh shape node associated with this skin.

        :return: skin shape node.
        :rtype: OpenMaya.MObject
        """

        return self._shape.object()

    @override(check_signature=False)
    def intermediate_object(self) -> OpenMaya.MObject:
        """
        Returns the intermediate object associated with this skin.

        :return: intermediate object.
        :rtype: OpenMaya.MObject
        """

        return self._intermediate_object.object()

    @override(check_signature=False)
    def iterate_vertices(self) -> Iterator[int]:
        """
        Returns a generator that yields vertex indices.

        :return: iterated vertex indices.
        :rtype: Iterator[int]
        """

        return range(self.num_control_points())

    def component(self) -> OpenMaya.MObject | None:
        """
        Returns the component selection for the associated shape.

        :return: component selection for the associated shape.
        :rtype: OpenMaya.MObject or None
        """

        shape = self.shape()
        components = [
            component for (dag_path, component) in
            dagpath.iterate_active_component_selection() if dag_path.node() == shape]
        num_components = len(components)
        return components[0] if num_components == 1 else OpenMaya.MObject.kNullObj

    @override
    def is_partially_selected(self) -> bool:
        return self.is_selected() or self.shape() in self.scene.active_selection()

    @override(check_signature=False)
    def iterate_selection(self) -> Iterator[int]:
        """
        Returns a generator that yields the selected vertex elements.

        :return: iterated selected vertex elements.
        :rtype: Iterator[int]
        """

        component = self.component()
        if not component.hasFn(OpenMaya.MFn.kMeshVertComponent):
            return iter([])

        # Iterate through component.
        fn_component = OpenMaya.MFnSingleIndexedComponent(component)
        for i in range(fn_component.elementCount):
            yield fn_component.element(i)

    @override(check_signature=False)
    def set_selection(self, vertices: list[int]):
        """
        Updates the active selection with the given supplied vertex elements.

        :param list[int] vertices: vertex elements to select.
        """

        dag_path = OpenMaya.MDagPath.getAPathTo(self.shape())

        # Create mesh component.
        fn_component = OpenMaya.MFnSingleIndexedComponent()
        component = fn_component.create(OpenMaya.MFn.kMeshVertComponent)
        fn_component.addElements(vertices)

        # Update selection list.
        selection = OpenMaya.MSelectionList()
        selection.add((dag_path, component))
        OpenMaya.MGlobal.setActiveSelectionList(selection)

    @override
    def iterate_soft_selection(self) -> Iterator[dict[int, float]]:
        """
        Returns a generator that yields selected vertex-weight pairs.

        :return: iterated selected vertex-weight pairs.
        :rtype: Iterator[dict[int, float]]
        """

        component = self.component()
        if not component.hasFn(OpenMaya.MFn.kMeshVertComponent):
            return iter([])

        # Iterate through component and check if element has weights.
        fn_component = OpenMaya.MFnSingleIndexedComponent(component)
        for i in range(fn_component.elementCount):
            if fn_component.hasWeights:
                yield fn_component.element(i), fn_component.weight(i)
            else:
                yield fn_component.element(i), 1.0

    @classmethod
    def is_plugin_loaded(cls) -> bool:
        """
        Returns whether the plugin for color display is loaded.

        :return: True if plugin for color display is loaded; False otherwise.
        :rtype: bool
        """

        return cmds.pluginInfo('TransferPaintWeightsCmd', query=True, loaded=True)

    @override
    def show_colors(self):
        """
        Enables color feedback for the associated mesh.
        """

        if not self.is_plugin_loaded():
            logger.debug('show_colors() requires the TransferPaintWeightsCmd.mll plugin!')
            return

        # Check if this instance supports vertex colors.
        shape = self.shape()
        if not shape.hasFn(OpenMaya.MFn.kMesh):
            logger.debug(f'show_colors() expects a mesh ({shape.apiTypeStr} given)!')
            return

        # Check if intermediate object has color set.
        intermediate_object = self.intermediate_object()
        fn_mesh = OpenMaya.MFnMesh(intermediate_object)
        color_set_names = fn_mesh.getColorSetNames()
        if self.__color_set_name__ not in color_set_names:
            fn_mesh.createColorSet(self.__color_set_name__, False)
            fn_mesh.setCurrentColorSetName(self.__color_set_name__)

        # Set shape attributes.
        fn_mesh.setObject(shape)
        full_path_name = fn_mesh.fullPathName()
        cmds.setAttr(f'{full_path_name}.displayImmediate', 0)
        cmds.setAttr(f'{full_path_name}.displayVertices', 0)
        cmds.setAttr(f'{full_path_name}.displayEdges', 0)
        cmds.setAttr(f'{full_path_name}.displayBorders', 0)
        cmds.setAttr(f'{full_path_name}.displayCenter', 0)
        cmds.setAttr(f'{full_path_name}.displayTriangles', 0)
        cmds.setAttr(f'{full_path_name}.displayUVs', 0)
        cmds.setAttr(f'{full_path_name}.displayNonPlanar', 0)
        cmds.setAttr(f'{full_path_name}.displayInvisibleFaces', 0)
        cmds.setAttr(f'{full_path_name}.displayColors', 1)
        cmds.setAttr(f'{full_path_name}.vertexColorSource', 1)
        cmds.setAttr(f'{full_path_name}.materialBlend', 0)
        cmds.setAttr(f'{full_path_name}.displayNormal', 0)
        cmds.setAttr(f'{full_path_name}.displayTangent', 0)
        cmds.setAttr(f'{full_path_name}.currentColorSet', '', type='string')

    @override
    def hide_colors(self):
        """
        Disables color feedback for the associated mesh.
        """

        if not self.is_plugin_loaded():
            logger.debug('hide_colors() requires the TransferPaintWeightsCmd.mll plugin!')
            return

        # Check if this instance supports vertex colors.
        shape = self.shape()
        if not shape.hasFn(OpenMaya.MFn.kMesh):
            logger.debug(f'hide_colors() expects a mesh ({shape.apiTypeStr} given)!')
            return

        # Reset shape attributes and delete color set.
        fn_mesh = OpenMaya.MFnMesh(shape)
        full_path_name = fn_mesh.fullPathName()
        cmds.setAttr(f'{full_path_name}.displayColors', 0)
        cmds.setAttr(f'{full_path_name}.vertexColorSource', 1)

        intermediate_object = self.intermediateObject()
        fn_mesh.setObject(intermediate_object)
        color_set_names = fn_mesh.getColorSetNames()
        if self.__color_set_name__ in color_set_names:
            fn_mesh.deleteColorSet(self.__color_set_name__)

    @override
    def refresh_colors(self):
        """
        Forces the vertex color display to redraw.
        """

        if not self.is_plugin_loaded():
            logger.debug('invalidateColors() requires the TransferPaintWeightsCmd.mll plugin!')
            return

        # Check if this instance belongs to a mesh.
        intermediate_object = self.intermediateObject()
        if not intermediate_object.hasFn(OpenMaya.MFn.kMesh):
            logger.debug(f'refresh_colors() expects a mesh ({intermediate_object.apiTypeStr} given)!')
            return

        # Check if colour set is active.
        fn_mesh = OpenMaya.MFnMesh(intermediate_object)
        mesh_name = fn_mesh.fullPathName()
        current_color_set = fn_mesh.currentColorSetName()
        skin_cluster_name = f'{self.namespace()}:{self.name()}'
        if current_color_set == self.__color_set_name__:
            cmds.dgdirty(f'{skin_cluster_name}.paintTrans')
            cmds.transferPaintWeights(f'{skin_cluster_name}.paintWeights', mesh_name, colorRamp=self.__color_ramp__)

    @override
    def iterate_influences(self) -> Iterator[tuple[int, Any]]:
        """
        Returns a generator that yields the influence id-objects pairs from the skin.

        :return: iterated influence id-objects pairs from the skin.
        :rtype: Iterator[tuple[int, Any]]
        """

        return skin_utils.iterate_influences(self.object())

    @override
    def num_influences(self) -> int:
        """
        Returns the number of influences in use by this skin.

        :return: number of influences.
        :rtype: int
        """

        matrix_plug = plugs.find_plug(self.object(), 'matrix')
        return matrix_plug.numConnectedElements()

    @override
    def add_influence(self, *influences: Any | list[Any]):
        """
        Adds an influence to this skin.

        :param Any or list[Any] influences: influence(s) to add.
        """

        node_fn = node.Node()
        for influence in influences:
            success = node_fn.try_set_object(influence)
            if success:
                skin_utils.add_influence(self.object(), node_fn.object())
            else:
                logger.warning(f'Unable to locate influence: {influence}')
                continue

    @override
    def remove_influence(self, *influence_ids: int | list[int]):
        """
        Removes an influence from this skin.

        :param int or list[int] influence_ids: influence IDs to remove.
        """

        for influence_id in influence_ids:
            skin_utils.remove_influence(self.object(), influence_id)

    @override
    def max_influences(self) -> int:
        """
        Returns the number of maximum influences for this skin.

        :return: maximum number of influences.
        :rtype: int
        """

        max_influences_plug = plugs.find_plug(self.object(), 'maxInfluences')
        return plugmutators.value(max_influences_plug)

    @override
    def set_max_influences(self, count: int):
        """
        Updates the maximum number of influences for this skin.

        :param int count: new maximum number of influences.
        """

        maintain_max_influences_plug = plugs.find_plug(self.object(), 'maintainMaxInfluences')
        plugmutators.set_value(maintain_max_influences_plug, True)
        max_influences_plug = plugs.find_plug(self.object(), 'maxInfluences')
        plugmutators.set_value(max_influences_plug, count)

    @override
    def select_influence(self, influence_id: int):
        """
        Selects the influence with given index.

        :param int influence_id: index of the influence to select.
        """

        skin_utils.select_influence(self.object(), influence_id)

    @override
    def iterate_vertex_weights(self, *indices: int | list[int]) -> Iterator[tuple[int, dict[int, float]]]:
        """
        Returns a generator that yields vertex-weights pairs from this node.

        :param int or list[int] indices: indices to iterate. If not given, all weights will be yielded.
        :return: iterated vertex-weights pairs from this node.
        :rtype: Iterator[tuple[int, dict[int, float]]]
        """

        return skin_utils.iterate_weights_list(self.object(), vertex_indices=indices)

    @override
    def apply_vertex_weights(self, vertex_weights: dict[int, dict[int, float]]):
        """Assigns the given vertex weights to this skin.

        :param dict[int, dict[int, float]] vertex_weights: vertex weights to apply.
        """

        skin_utils.set_weight_list(self.object(), vertex_weights)
