from __future__ import annotations

from tp.maya import api

from tp.common.python import helpers


def attribute_class_for_type(attr_type: int) -> type:
    """
    Returns the specific attribute type for given type.

    :param int attr_type: attribute type to get descriptor class of.
    :return: attribute descriptor class to use.
    :rtype: type
    """

    return ATTRIBUTE_TYPES.get(attr_type, AttributeDescriptor)


def attribute_class_for_descriptor(descriptor: AttributeDescriptor) -> AttributeDescriptor:
    """
    Returns an attribute descriptor instance for the given descriptor attribute data.

    :param dict descriptor: attribute descriptor data.
    :return: newly created attribute descriptor instance.
    :rtype: AttributeDescriptor
    """

    attr_descriptor_type = descriptor.get('type', -1)
    instance = attribute_class_for_type(attr_descriptor_type)

    return instance(descriptor)


class AttributeDescriptor(helpers.ObjectDict):
    """
    Wrapper class to handle Maya types to dictionary storage. Each key requires a Maya data type that will be either
    returned or converted back to a JSON compatible data type.

    :keyword str name: name of the attribute.
    :keyword int or float or str or iterable value: current value matching that of the type.
    :keyword int or float or str or iterable default: default value matching that of the type.
    :keyword int Type: attribute mfn number. see: :ref:`tp.maya.api.attributetypes.
    :keyword float softMin:
    :keyword float softMax:
    :keyword int or float min: whether this is a numeric attribute then it is the minimum number.
    :keyword int or float max: whether this is a numeric attribute then it ist he maximum number.
    :keyword bool locked: Lock state.
    :keyword bool channelBox: whether this attribute displays in the channel box.
    :keyword bool keyable: whether this attribute  can be keyed.
    """

    @property
    def value(self):
        return self['value']

    @value.setter
    def value(self, value):
        self['value'] = value

    @property
    def default(self):
        return self['default']

    @default.setter
    def default(self, value):
        self['default'] = value

    @property
    def softMin(self):
        return self['softMin']

    @softMin.setter
    def softMin(self, value):
        self['softMin'] = value

    @property
    def softMax(self):
        return self['softMax']

    @softMax.setter
    def softMax(self, value):
        self['softMax'] = value

    @property
    def min(self):
        return self['min']

    @min.setter
    def min(self, value):
        self['min'] = value

    @property
    def max(self):
        return self['max']

    @max.setter
    def max(self, value):
        self['max'] = value


class VectorAttributeDescriptor(AttributeDescriptor):

    @property
    def value(self):
        return api.Vector(self['value'])

    @value.setter
    def value(self, value):
        self['value'] = tuple(value)

    @property
    def default(self):
        return api.Vector(self['default'])

    @default.setter
    def default(self, value):
        self['default'] = tuple(value)

    @property
    def softMin(self):
        return api.Vector(self['softMin'])

    @softMin.setter
    def softMin(self, value):
        self['softMin'] = tuple(value)

    @property
    def softMax(self):
        return api.Vector(self['softMax'])

    @softMax.setter
    def softMax(self, value):
        self['softMax'] = tuple(value)

    @property
    def min(self):
        return api.Vector(self['min'])

    @min.setter
    def min(self, value):
        self['min'] = tuple(value)

    @property
    def max(self):
        return api.Vector(self['max'])

    @max.setter
    def max(self, value):
        self['max'] = tuple(value)


ATTRIBUTE_TYPES = {
    api.kMFnNumericBoolean: AttributeDescriptor,
    api.kMFnNumericByte: AttributeDescriptor,
    api.kMFnNumericShort: AttributeDescriptor,
    api.kMFnNumericInt: AttributeDescriptor,
    api.kMFnNumericDouble: AttributeDescriptor,
    api.kMFnNumericFloat: AttributeDescriptor,
    api.kMFnNumericAddr: AttributeDescriptor,
    api.kMFnNumericChar: AttributeDescriptor,
    api.kMFnNumeric2Double: AttributeDescriptor,
    api.kMFnNumeric2Float: AttributeDescriptor,
    api.kMFnNumeric2Int: AttributeDescriptor,
    api.kMFnNumeric2Short: AttributeDescriptor,
    api.kMFnNumeric3Double: VectorAttributeDescriptor,
    api.kMFnNumeric3Float: VectorAttributeDescriptor,
    api.kMFnNumeric3Int: AttributeDescriptor,
    api.kMFnNumeric3Short: AttributeDescriptor,
    api.kMFnNumeric4Double: AttributeDescriptor,
    api.kMFnUnitAttributeDistance: AttributeDescriptor,
    api.kMFnUnitAttributeAngle: AttributeDescriptor,
    api.kMFnUnitAttributeTime: AttributeDescriptor,
    api.kMFnkEnumAttribute: AttributeDescriptor,
    api.kMFnDataString: AttributeDescriptor,
    api.kMFnDataMatrix: AttributeDescriptor,
    api.kMFnDataFloatArray: AttributeDescriptor,
    api.kMFnDataDoubleArray: AttributeDescriptor,
    api.kMFnDataIntArray: AttributeDescriptor,
    api.kMFnDataPointArray: AttributeDescriptor,
    api.kMFnDataVectorArray: AttributeDescriptor,
    api.kMFnDataStringArray: AttributeDescriptor,
    api.kMFnDataMatrixArray: AttributeDescriptor,
    api.kMFnMessageAttribute: AttributeDescriptor
}
