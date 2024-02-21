from __future__ import annotations

from tp.maya import api


def bake_objects(
        nodes: list[api.DagNode | api.Joint], translate: bool = True, rotate: bool = True, scale: bool = True,
        use_settings: bool = True, **kwargs):
    raise NotImplementedError
