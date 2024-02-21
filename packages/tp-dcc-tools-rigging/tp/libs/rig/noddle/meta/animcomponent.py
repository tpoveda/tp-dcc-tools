from __future__ import annotations

from tp.core import log
from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.meta import component

logger = log.tpLogger


class NoddleAnimComponent(component.NoddleComponent):

    ID = consts.ANIM_COMPONENT_TYPE


