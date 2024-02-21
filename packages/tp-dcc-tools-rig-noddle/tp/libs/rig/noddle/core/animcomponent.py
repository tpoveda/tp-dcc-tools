from __future__ import annotations

import typing
from typing import Iterable

from overrides import override

from tp.maya import api
from tp.libs.rig.noddle.core import component, nodes
from tp.libs.rig.noddle.meta import layers, animcomponent as meta_component
from tp.libs.rig.noddle.descriptors import component as descriptor_component
from tp.libs.rig.noddle.functions import outliner

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.core.rig import Rig
    from tp.libs.rig.noddle.core.nodes import ControlNode


class AnimComponent(component.Component):

    def __init__(
            self, rig: Rig, descriptor: descriptor_component.ComponentDescriptor | None = None,
            meta: meta_component.NoddleAnimComponent | None = None):
        super().__init__(rig=rig, descriptor=descriptor, meta=meta)

    @override(check_signature=False)
    def create(
            self, parent: layers.NoddleComponentsLayer | None = None) -> meta_component.NoddleAnimComponent:

        meta_node = super().create(parent=parent)

        self.set_outliner_color(17)

        return meta_node

    def attach_to_skeleton(self) -> bool:
        """
        Attaches component joints into rig skeleton.

        :return: True if attach to skeleton process was completed successfully; False otherwise.
        :rtype: bool
        """

        skeleton_layer = self.skeleton_layer()
        rig_layer = self.rig_layer()
        rig_skeleton_layer = self.rig.skeleton_layer()
        if not skeleton_layer or not rig_skeleton_layer:
            self.logger.warning('Rig skeleton is not built.')
            return False

        self.logger.info(f'{self} attaching to skeleton...')
        component_joints = list(skeleton_layer.iterate_joints())
        rig_joints = rig_skeleton_layer.find_joints(*[joint.id() for joint in component_joints])
        for component_joint, rig_joint in zip(component_joints, rig_joints):
            if not rig_joint:
                self.logger.warning(f'Rig joint with ID "{component_joint.id()}" not found in rig skeleton')
                continue
            if not self.rig.configuration.ignore_existing_constraints_on_skeleton_attachment:
                found_parent_constraint: api.DGNode | None = None
                for _, destination_plug in rig_joint.iterateConnections(source=False):
                    node = destination_plug.node()
                    if node and node.apiType() == api.kParentConstraint:
                        found_parent_constraint = node
                        break
                if found_parent_constraint:
                    self.logger.info(f'Replacing {rig_joint} attachment to {component_joint}')
                    found_parent_constraint.delete()
            _, constraint_nodes = api.build_constraint(
                rig_joint, drivers={'targets': (
                    (component_joint.fullPathName(partial_name=True, include_namespace=False), component_joint),)},
                constraint_type='parent', maintainOffset=True)
            rig_layer.add_extra_nodes(constraint_nodes)

        return True

    def detach_from_skeleton(self) -> bool:
        """
        Detaches component joints from rig skeleton.

        :return: True if detach from skeleton process was completed successfully; False otherwise.
        :rtype: bool
        """

        skeleton_layer = self.skeleton_layer()
        rig_skeleton_layer = self.rig.skeleton_layer()
        if not skeleton_layer or not rig_skeleton_layer:
            self.logger.warning('Rig skeleton is not built.')
            return False

        rig_joints_parent_constraints = set()
        component_joints_parent_constraints = set()

        for rig_joint in rig_skeleton_layer.iterate_joints():
            for _, destination_plug in rig_joint.iterateConnections(source=False):
                node = destination_plug.node()
                if node and node.apiType() == api.kParentConstraint:
                    rig_joints_parent_constraints.add(node)
        for component_joint in skeleton_layer.iterate_joints():
            for _, destination_plug in component_joint.iterateConnections(destination=False):
                node = destination_plug.node()
                if node and node.apiType() == api.kParentConstraint:
                    component_joints_parent_constraints.add(node)

        common_constraints = rig_joints_parent_constraints.intersection(component_joints_parent_constraints)
        self.logger.info(f'Deleting ({len(common_constraints)}) constraints: {common_constraints}')
        for constraint_node in common_constraints:
            constraint_node.delete()

        self.logger.info(f'{self} detached from skeleton.')

    def set_outliner_color(self, color: int | str | Iterable[float, float, float]):
        """
        Sets the color of the animatable component root control within outliner panel.

        :param int or str or Iterable[float, float, float] color: outliner color to set.
        """

        outliner.set_color(self.root_transform(), color)

    def scale_controls(self, scale_dict: dict[ControlNode, float]):
        """
        Scale given controls shapes.

        :param dict[ControlNode, float] scale_dict: dictionary with controls as values and their scale values as keys.
        """

        clamped_size = 1.0
        if self.rig and self.rig.clamped_size() > 1.0:
            clamped_size = self.rig.clamped_size()

        for found_control, factor in scale_dict.items():
            found_control.scale_shapes(clamped_size, factor=factor)
