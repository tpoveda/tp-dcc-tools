from __future__ import annotations

import copy
import collections

from overrides import override

from tp.common.python import helpers
from tp.maya import api
from tp.maya.om import utils

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.descriptors import attributes


class DGNodeDescriptor(helpers.ObjectDict):
    """
    DG Node descriptor class.
    """

    @classmethod
    def deserialize(cls, data: dict) -> DGNodeDescriptor:
        """
        Given a valid descriptor dictionary recursively converts all children to descriptors and returns the
        deserialized descriptor.

        :param dict data: data to deserialize.
        :return: deserialized descriptor instance.
        :rtype: DGNodeDescriptor
        """

        return cls(**data)

    def copy(self) -> DGNodeDescriptor:
        """
        Returns a copy of this descriptor.

        :return: descriptor copy instance.
        :rtype: DGNodeDescriptor
        """

        return self.deserialize(self)

    def attribute(self, attribute_name: str) -> attributes.AttributeDescriptor | None:
        """
        Returns descriptor attribute instance with given name.

        :param str attribute_name: name of the descriptor attribute to get.
        :return: attribute descriptor instance.
        :rtype: attributes.AttributeDescriptor or None
        """

        for attr in self.get('attributes', []):
            if attr['name'] == attribute_name:
                return attr

        return None


class TransformDescriptor(DGNodeDescriptor):
    """
    Transform descriptor class with the following data:
        {
            "name": "nodeName",
            "translation": [0,0,0],
            "rotation": [0,0,0,1],
            "rotateOrder": 0,
            "shape": "cube",
            "id": "myId",
            "children": [],
            "color": [0,0,0],
            "worldMatrix": [],
            "shapeTransform": {"translate": [0,0,0], "rotate": [0,0,0,1], "scale": [1,1,1]}
        }
    """

    DEFAULTS = {
        'name': 'control',
        'children': [],
        'parent': None,
        'noddleType': 'transform',
        'type': 'transform',
        'rotateOrder': 0,
        'translate': [0.0, 0.0, 0.0],
        'rotate': [0.0, 0.0, 0.0, 1.0],
        'scale': [1.0, 1.0, 1.0]
    }

    def __init__(self, *args, **kwargs):

        defaults = copy.deepcopy(self.DEFAULTS)
        if args:
            defaults.update(args[0])
        defaults.update(kwargs)

        # ensure type compatibility
        for name in ('translate', 'rotate', 'scale', 'matrix', 'worldMatrix'):
            existing_data = defaults.get(name)
            if existing_data is not None:
                defaults[name] = tuple(existing_data)

        # convert attributes dictionaries to attribute descriptor instances
        new_attrs: list[attributes.AttributeDescriptor] = defaults.get('attributes', [])
        attr_instances = []
        attr_names = set()
        for new_attr in new_attrs:
            if new_attr['name'] in attr_names:
                continue
            attr_names.add(new_attr['name'])
            attr_instances.append(attributes.attribute_class_for_descriptor(new_attr))
        defaults['attributes'] = attr_instances

        super().__init__(defaults)

    @property
    def translate(self):
        return api.Vector(self['translate'])

    @translate.setter
    def translate(self, value):
        self['translate'] = tuple(value)

    @property
    def rotate(self):
        rotation = self['rotate']
        if len(rotation) == 3:
            return api.EulerRotation(rotation, self.get('rotateOrder', api.consts.kRotateOrder_XYZ))
        return api.Quaternion(rotation)

    @rotate.setter
    def rotate(self, value):
        self['rotate'] = tuple(value)

    @property
    def scale(self):
        return api.Vector(self['scale'])

    @scale.setter
    def scale(self, value):
        self['scale'] = tuple(value)

    @property
    def matrix(self):
        return api.Matrix(self['matrix'])

    @matrix.setter
    def matrix(self, value):
        self['matrix'] = tuple(value)

    @property
    def worldMatrix(self):
        return api.Matrix(self['worldMatrix'])

    @worldMatrix.setter
    def worldMatrix(self, value):
        self['worldMatrix'] = tuple(value)

    @override
    def copy(self) -> TransformDescriptor:
        """
        Overrides copy function to return a descriptor instance.

        :return: copied descriptor instance.
        :rtype: TransformDescriptor
        """

        return self.deserialize(self, parent=self.parent)

    @classmethod
    def deserialize(cls, data: dict, parent: TransformDescriptor | None = None) -> TransformDescriptor:
        """
        Given a valid descriptor dictionary recursively converts all children to descriptors and returns the
        deserialized descriptor.

        :param dict data: data to deserialize.
        :param TransformDescriptor parent: optional parent transform descriptor.
        :return: deserialized descriptor instance.
        :rtype: TransformDescriptor
        """

        new_instance = cls(**data)

        # update children to make sure they have this transform descriptor defined as parent
        new_instance.children = [cls.deserialize(
            child, parent=new_instance.id) for child in new_instance.get('children', [])]
        new_instance.parent = parent

        return new_instance

    def iterate_children(self, recursive: bool = True) -> collections.Iterator[TransformDescriptor]:
        """
        Generator function that iterates recursively over all children of this transform descriptor instance.

        :param bool recursive: whether to iterate children recursively.
        :return: iterated transform descriptor instances.
        :rtype: collections.Iterator[TransformDescriptor]
        """

        for child in iter(self.get('children', list())):
            yield child
            if recursive:
                for sub_child in child.iterate_children(recursive=recursive):
                    yield sub_child

    def delete_child(self, child_id: str) -> bool:
        """
        Deletes a child transform for this transform descriptor.

        :param str child_id: ID of the child to delete.
        :return: True if the delete child operation was successful; False otherwise.
        :rtype: bool
        """

        children = list()
        deleted = False
        for child in self.iterate_children(recursive=False):
            if child.id != child_id:
                children.append(child)
            else:
                deleted = True
        self['children'] = children

        return deleted

    def local_transformation_matrix(
            self, translate: bool = True, rotate: bool = True, scale: bool = True) -> api.TransformationMatrix:
        """
        Returns the local transformation matrix for the current descriptor.

        :param bool translate: whether to include the translation part in the returned matrix.
        :param bool rotate: whether to include the rotation part in the returned matrix.
        :param bool scale: whether to include the scale part in the returned matrix.
        :return: descriptor transformation matrix.
        :rtype: api.TransformationMatrix
        """

        local_matrix = self.get('matrix')
        if local_matrix is None:
            transformation_matrix = api.TransformationMatrix(api.Matrix())
            transformation_matrix.reorderRotation(utils.int_to_mtransform_rotation_order(self.get('rotateOrder', ())))
            return transformation_matrix

        transformation_matrix = api.TransformationMatrix(api.Matrix(local_matrix))
        transformation_matrix.reorderRotation(utils.int_to_mtransform_rotation_order(self.get('rotateOrder', ())))
        if not translate:
            transformation_matrix.setTranslation(api.Vector(), api.kObjectSpace)
        if not rotate:
            transformation_matrix.setRotation(api.Quaternion())
        if not scale:
            transformation_matrix.setScale(api.Vector(1.0, 1.0, 1.0), api.kWorldSpace)

        return transformation_matrix

    def transformation_matrix(self, translate: bool = True, rotate: bool = True, scale: bool = True):
        """
        Returns the world transformation matrix for the current descriptor.

        :param bool translate: whether to include the translation part in the returned matrix.
        :param bool rotate: whether to include the rotation part in the returned matrix.
        :param bool scale: whether to include the scale part in the returned matrix.
        :return: descriptor transformation matrix.
        :rtype: api.TransformationMatrix
        """

        transformation_matrix = api.TransformationMatrix(api.Matrix())
        if translate:
            transformation_matrix.setTranslation(api.Vector(self.get('translate', (0.0, 0.0, 0.0))), api.kWorldSpace)
        if rotate:
            transformation_matrix.setRotation(api.Quaternion(self.get('rotate', (0.0, 0.0, 0.0))))
            transformation_matrix.reorderRotation(utils.int_to_mtransform_rotation_order(self.get('rotateOrder', ())))
        if scale:
            transformation_matrix.setScale(self.get('scale', (1.0, 1.0, 1.0)), api.kWorldSpace)

        return transformation_matrix


class JointDescriptor(TransformDescriptor):
    """
    Joint descriptor class
    """

    DEFAULTS = {
        'name': 'joint',
        'id': '',
        'children': [],
        'parent': None,
        'noddleType': 'joint',
        'translate': [0.0, 0.0, 0.0],
        'rotate': [0.0, 0.0, 0.0, 1.0],
        'scale': [1.0, 1.0, 1.0],
        'rotateOrder': 0
    }


class InputDescriptor(TransformDescriptor):
    """
    Input descriptor class
    """

    DEFAULTS = {
        'name': 'input',
        'id': '',
        'root': False,
        'children': [],
        'parent': None,
        'noddleType': 'input',
        'translate': [0.0, 0.0, 0.0],
        'rotate': [0.0, 0.0, 0.0, 1.0],
        'scale': [1.0, 1.0, 1.0],
        'rotateOrder': 0
    }


class OutputDescriptor(TransformDescriptor):
    """
    Output descriptor class
    """

    DEFAULTS = {
        'name': 'output',
        'id': '',
        'root': False,
        'children': [],
        'parent': None,
        'noddleType': 'output',
        'translate': [0.0, 0.0, 0.0],
        'rotate': [0.0, 0.0, 0.0, 1.0],
        'scale': [1.0, 1.0, 1.0],
        'rotateOrder': 0
    }


class ControlDescriptor(TransformDescriptor):
    """
    Control descriptor class
    """

    DEFAULTS = {
        'name': 'control',
        'shape': 'circle',
        'id': 'ctrl',
        'color': (),
        'children': [],
        'parent': None,
        'noddleType': 'control',
        'srts': [],
        'translate': [0.0, 0.0, 0.0],
        'rotate': [0.0, 0.0, 0.0, 1.0],
        'scale': [1.0, 1.0, 1.0],
        'rotateOrder': 0
    }


NODDLE_NODE_TYPES = {
    'transform': TransformDescriptor,
    'joint': JointDescriptor,
    'input': InputDescriptor,
    'output': OutputDescriptor,
    'control': ControlDescriptor,
}
