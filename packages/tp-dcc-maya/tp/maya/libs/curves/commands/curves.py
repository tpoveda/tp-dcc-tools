from __future__ import annotations

from overrides import override
import maya.cmds as cmds
import maya.api.OpenMaya as OpenMaya

from tp.maya.api import command
from tp.maya.libs import curves
from tp.maya.om import nodes


class CreateCurveFromLibrary(command.MayaCommand):
    """
    Command that handles the creation of a NURBS cruve from curves library.
    """

    id = 'tp.maya.curves.createFromLib'
    is_undoable = True

    _parent: OpenMaya.MObjectHandle | None = None
    _new_parent = False
    _shape_nodes: list[OpenMaya.MObjectHandle] = []

    @override
    def resolve_arguments(self, arguments: dict) -> dict | None:
        curve_type: str | None = arguments.get('curve_type', None)
        if not curve_type:
            raise ValueError(f'Curve type is not a valid one: "{curve_type}"')

        parent: OpenMaya.MObject | None = arguments.get('parent', None)
        if parent is not None:
            handle = OpenMaya.MObjectHandle(parent)
            if not handle.isValid() or not handle.isAlive():
                self.cancel(f'Parent no longer exists within the scene: "{parent}"')
            self._parent = handle
            arguments['parent'] = handle
        else:
            self._new_parent = True
            arguments['parent'] = None

        return arguments

    @override(check_signature=False)
    def do(
            self, curve_type: str | None = None,
            parent: OpenMaya.MObjectHandle | None = None) -> tuple[OpenMaya.MObject, list[OpenMaya.MObject]]:

        parent_mobject, shape_nodes = curves.load_and_create_from_lib(
            curve_type, parent=parent.object() if parent is not None else None)
        self._parent = OpenMaya.MObjectHandle(parent_mobject)
        self._shape_nodes = map(OpenMaya.MObjectHandle, shape_nodes)

        return parent_mobject, shape_nodes

    @override
    def undo(self):
        if self._new_parent:
            if self._parent.isValid() and self._parent.isAlive():
                cmds.delete(nodes.name(self._parent.object()))
        elif self._shape_nodes:
            cmds.delete([nodes.name(i.object()) for i in self._shape_nodes if i.isValid() and i.isAlive()])


class CreateCurveFromFilePath(command.MayaCommand):
    """
    Command that handles the creation of a NURBS curve from a folder path.
    """

    id = 'tp.maya.curves.createFromFilePath'
    is_undoable = True

    _parent: OpenMaya.MObjectHandle | None = None
    _new_parent = False
    _shape_nodes: list[OpenMaya.MObjectHandle] = []

    @override
    def resolve_arguments(self, arguments: dict) -> dict | None:
        curve_type: str | None = arguments.get('curve_type', None)
        if not curve_type:
            raise ValueError(f'Curve type is not a valid one: "{curve_type}"')

        parent: OpenMaya.MObject | None = arguments.get('parent', None)
        if parent is not None:
            handle = OpenMaya.MObjectHandle(parent)
            if not handle.isValid() or not handle.isAlive():
                self.cancel(f'Parent no longer exists within the scene: "{parent}"')
            self._parent = handle
            arguments['parent'] = handle
        else:
            self._new_parent = True
            arguments['parent'] = None

        return arguments

    @override(check_signature=False)
    def do(
            self, curve_type: str | None = None, parent: OpenMaya.MObjectHandle | None = None,
            folder_path: str | None = None) -> tuple[OpenMaya.MObject, list[OpenMaya.MObject]]:

        parent_mobject, shape_nodes = curves.load_and_create_from_path(
            curve_type, folder_path, parent=parent.object() if parent is not None else None)
        self._parent = OpenMaya.MObjectHandle(parent_mobject)
        self._shape_nodes = map(OpenMaya.MObjectHandle, shape_nodes)

        return parent_mobject, shape_nodes

    @override
    def undo(self):
        if self._new_parent:
            if self._parent.isValid() and self._parent.isAlive():
                cmds.delete(nodes.name(self._parent.object()))
        elif self._shape_nodes:
            cmds.delete([nodes.name(i.object()) for i in self._shape_nodes if i.isValid() and i.isAlive()])
