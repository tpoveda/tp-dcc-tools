from __future__ import annotations

import typing

from tp.core import log
from tp.maya import api
from tp.maya.meta import base
from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.functions import attributes, nodes

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.meta.animcomponent import AnimComponent

logger = log.rigLogger


class Hook(api.DagNode):

    def __repr__(self) -> str:
        return f'Hook({self})'

    def __eq__(self, other: Hook):
        if not isinstance(other, Hook):
            raise TypeError(f'Cannot compare Hook and {type(other)}')
        return self.handle() == other.handle()

    @classmethod
    def create(cls, anim_component: AnimComponent, node: api.DagNode, name: str) -> Hook:
        """
        Creates a new hook instance attached to the given animation component.

        :param AnimComponent anim_component: animation component this will be attached into.
        :param api.DagNode node: node that will be wrapped by the hook.
        :param str name: name of the hook.
        :return: newly created hook instance.
        :rtype: Hook
        """

        hook_transform = nodes.create(
            'transform', [anim_component.indexed_name(), name], anim_component.side(), suffix='hook')
        hook_transform.setParent(anim_component.out_group())
        _, point_constraint_nodes = api.build_constraint(
            hook_transform,
            drivers={'targets': ((node.fullPathName(partial_name=True, include_namespace=False), node),)},
            constraint_type='point'
        )
        _, orient_constraint_nodes = api.build_constraint(
            hook_transform,
            drivers={'targets': ((node.fullPathName(partial_name=True, include_namespace=False), node),)},
            constraint_type='orient'
        )

        new_hook = cls(node=hook_transform.object())
        attributes.add_meta_parent_attribute([new_hook])
        new_hook.addAttribute('object', type=api.kMFnMessageAttribute)
        new_hook.addAttribute('children', type=api.kMFnMessageAttribute)
        new_hook.addAttribute('utilNodes', type=api.kMFnMessageAttribute, isArray=True)
        node.message.connect(new_hook.attribute('object'))
        new_hook.attribute(consts.MPARENT_ATTR_NAME).connect(
            anim_component.attribute('outHooks').nextAvailableDestElementPlug())
        for util_node in point_constraint_nodes + orient_constraint_nodes:
            util_node.message.connect(new_hook.attribute('utilNodes').nextAvailableDestElementPlug())

        return new_hook

    @property
    def component(self) -> AnimComponent:
        """
        Components this hook belongs to.

        :return: component instance.
        :rtype: AnimComponent
        """

        return base.MetaBase(node=list(self.attribute(consts.MPARENT_ATTR_NAME).destinationNodes())[0].object())

    @property
    def index(self) -> int:
        """
        Index of this hook.

        :return: hook index.
        :rtype: int
        """

        return self.component.out_hooks().index(self)

    def add_output(self, anim_component: AnimComponent):
        """
        Link given component to this hook though the in hook attribute of the component.

        :param AnimComponent anim_component: child component of the component this hook is
            attached to.
        """

        self.attribute('children').connect(anim_component.attribute('inHook'))
        logger.info(f'{self.fullPathName(partial_name=True, include_namespace=False)} --> {anim_component}')
