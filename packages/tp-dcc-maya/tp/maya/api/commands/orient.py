from __future__ import annotations

import typing
from typing import Any

from overrides import override
import maya.api.OpenMaya as OpenMaya

from tp.maya import api
from tp.maya.api import command
from tp.maya.om import mathlib
from tp.maya.meta import base
from tp.libs.rig.utils.maya import align

if typing.TYPE_CHECKING:
    from tp.maya.meta.planeorient import PlaneOrientMeta


class OrientNodesCommand(command.MayaCommand):

    id = 'tp.maya.nodes.orient'
    is_undoable = True
    use_undo_chunk = True

    _transform_cache: list[tuple[api.OpenMaya.MObjectHandle, list[api.Vector, api.Vector, api.Vector]]] = []

    @override
    def resolve_arguments(self, arguments: dict) -> dict | None:
        nodes = arguments.get('nodes', [])
        if not nodes:
            self.cancel('No valid nodes passed to command')
        elif len(nodes) < 2:
            self.cancel('Must pass at least 2 nodes to command')

        return arguments

    @override(check_signature=False)
    def do(
            self, nodes: list[api.DagNode] | None = None, primary_axis: api.OpenMaya.MVector = mathlib.X_AXIS_VECTOR,
            secondary_axis: api.OpenMaya.MVector = mathlib.Y_AXIS_VECTOR,
            world_up_axis: api.OpenMaya.MVector | None = None, skip_end: bool = True) -> Any:

        self._transform_cache.clear()
        for node in nodes:
            transform = [
                node.translation(space=api.kTransformSpace),
                node.rotation(space=api.kTransformSpace, as_quaternion=False),
                node.scale(space=api.kObjectSpace)]
            if node.hasFn(api.kNodeTypes.kJoint):
                transform.append(node.attribute('jointOrient').value())
            self._transform_cache.append((node.handle(), transform))

        if not nodes:
            return False

        align.orient_nodes(nodes, primary_axis, secondary_axis, world_up_axis=world_up_axis, skip_end=skip_end)

        return True

    @override
    def undo(self):
        for handle, transform in self._transform_cache:
            if not handle.isValid() or not handle.isAlive():
                continue

            # Un-parent children
            node = api.node_by_object(handle.object())
            children = node.children(node_types=(api.kNodeTypes.kJoint, api.kNodeTypes.kTransform))
            for child in children:
                child.setParent(None)

            # Reapply original transform
            child.setTranslation(transform[0], space=api.kTransformSpace)
            child.setRotation(transform[1], space=api.kTransformSpace)
            child.setScale(transform[2])
            if len(transform) == 4:
                child.attribute('jointOrient').set(transform[3])

            # Re-parent children
            for child in children:
                child.setParent(node)


class PlaneOrientCreateCommand(command.MayaCommand):

    id = 'tp.maya.planeOrient.create'
    is_undoable = True
    use_undo_chunk = True

    _handle: PlaneOrientMeta | None = None

    @override(check_signature=False)
    def do(self, **kwargs: dict) -> PlaneOrientMeta:

        print('creating plane through command ...')

        meta_node = base.create_meta_node_by_type('tpPlaneOrient')
        self._handle = meta_node.handle()
        return meta_node

    def undo(self):
        if not self._handle.isValid() or not self._handle.isAlive():
            return

        meta_node = base.meta_node_by_handle(self._handle)
        if meta_node is None:
            return

        meta_node.delete()


class PlaneOrientAlignCommand(command.MayaCommand):

    id = 'tp.maya.planeOrient.align'
    is_undoable = True
    use_undo_chunk = True

    _modifier: api.DGModifier | None = None
    _handle: OpenMaya.MObjectHandle | None = None
    _transform_cache: list[tuple[OpenMaya.MObjectHandle, list[api.Vector, api.Vector, api.Vector]]] = []

    @override
    def resolve_arguments(self, arguments: dict) -> dict | None:
        if not arguments.get('meta_node'):
            self.cancel('No meta node given')
        self._handle = arguments.get('meta_node').handle()

        return arguments

    @override(check_signature=False)
    def do(self, meta_node: PlaneOrientMeta | None = None, skip_end: bool = False) -> bool:
        if not self._handle.isValid() or not self._handle.isAlive():
            return False

        meta_node: PlaneOrientMeta = base.meta_node_by_handle(self._handle)
        nodes = meta_node.nodes()
        for node in nodes:
            transform = [
                node.translation(space=api.kTransformSpace),
                node.rotation(space=api.kTransformSpace, as_quaternion=False),
                node.scale(space=api.kObjectSpace)
            ]
            if node.hasFn(api.kNodeTypes.kJoint):
                transform.append(node.attribute('jointOrient').value())
            self._transform_cache.append((node.handle(), transform))
        if not nodes:
            return False

        meta_node.project_and_align(skip_end=skip_end)

        return True

    @override
    def undo(self):
        for handle, transform in self._transform_cache:
            if not handle.isValid() or not handle.isValid():
                continue
            node = api.node_by_object(handle.object())
            children = node.children(node_types=(api.kNodeTypes.kJoint, api.kNodeTypes.kTransform))
            for child in children:
                child.setParent(None)
            node.setTranslation(transform[0], space=api.kTransformSpace)
            node.setRotation(transform[1], space=api.kTransformSpace)
            node.setScale(transform[2])
            if len(transform) == 4:
                node.attribute('jointOrient').set(transform[3])
            for child in children:
                child.setParent(node)
