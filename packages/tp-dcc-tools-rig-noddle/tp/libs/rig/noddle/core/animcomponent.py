from __future__ import annotations

import typing

from tp.libs.rig.noddle.core import component
from tp.libs.rig.noddle.meta import animcomponent as meta_component
from tp.libs.rig.noddle.descriptors import component as descriptor_component

if typing.TYPE_CHECKING:
    from tp.libs.rig.noddle.core.rig import Rig


class AnimComponent(component.Component):

    def __init__(
            self, rig: Rig, descriptor: descriptor_component.ComponentDescriptor | None = None,
            meta: meta_component.NoddleAnimComponent | None = None):
        super().__init__(rig=rig, descriptor=descriptor, meta=meta)

