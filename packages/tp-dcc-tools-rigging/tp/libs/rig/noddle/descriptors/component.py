from __future__ import annotations

import copy
import json
import pprint

from overrides import override

from tp.common.python import helpers

from tp.libs.rig.noddle import consts
from tp.libs.rig.noddle.descriptors import layers

# Descriptor layer to scene attribute mapping names.
SCENE_LAYER_ATTR_TO_DESCRIPTOR = {
    consts.INPUT_LAYER_DESCRIPTOR_KEY: [
        consts.NODDLE_DESCRIPTOR_CACHE_INPUT_DAG_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_INPUT_SETTINGS_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_INPUT_METADATA_ATTR,
        ''
    ],
    consts.OUTPUT_LAYER_DESCRIPTOR_KEY: [
        consts.NODDLE_DESCRIPTOR_CACHE_OUTPUT_DAG_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_OUTPUT_SETTINGS_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_OUTPUT_METADATA_ATTR,
        ''
    ],
    consts.SKELETON_LAYER_DESCRIPTOR_KEY: [
        consts.NODDLE_DESCRIPTOR_CACHE_DEFORM_DAG_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_DEFORM_SETTINGS_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_DEFORM_METADATA_ATTR,
        ''
    ],
    consts.RIG_LAYER_DESCRIPTOR_KEY: [
        consts.NODDLE_DESCRIPTOR_CACHE_RIG_DAG_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_RIG_SETTINGS_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_RIG_METADATA_ATTR,
        consts.NODDLE_DESCRIPTOR_CACHE_RIG_DG_ATTR,
    ]
}


def migrate_to_latest_version(descriptor_data: dict, original_descriptor: dict | None = None):
    """
    Migrates descriptor schema from an old version to the latest one.

    :param dict descriptor_data: descriptor data as a raw dictionary.
    :param dict or None original_descriptor: original descriptor.
    :return: translated descriptor data to the latest schema.
    :rtype: dict
    """

    # expect rig layer to come from the base descriptor not the scene, so keep original rig data
    if original_descriptor:
        descriptor_data[consts.RIG_LAYER_DESCRIPTOR_KEY] = original_descriptor.get(
            consts.RIG_LAYER_DESCRIPTOR_KEY, {})

    return descriptor_data


def load_descriptor(descriptor_data: dict, original_descriptor: dict, path: str | None = None) -> ComponentDescriptor:
    """
    Loads descriptor instance from given data.

    :param dict descriptor_data: descriptor data.
    :param dict original_descriptor: original descriptor.
    :param str or None path: optional descriptor path.
    :return: component descriptor instance.
    :rtype: ComponentDescriptor
    """

    latest_data = migrate_to_latest_version(descriptor_data, original_descriptor=original_descriptor)
    return ComponentDescriptor(data=latest_data, original_descriptor=copy.deepcopy(original_descriptor), path=path)


def parse_raw_descriptor(descriptor_data: dict) -> dict:
    """
    Function that parses the given descriptor data by transforming strings into dictionaries and by removing
    all descriptor keys that are empty.

    :param dict descriptor_data: descriptor data usually retrieved from current scene.
    :return: cleanup descriptor data.
    :rtype: dict
    """

    translated_data = {}

    for k, v in descriptor_data.items():
        if not v:
            continue
        if k == 'info':
            translated_data.update(json.loads(v))
            continue
        # elif k == consts.SPACE_SWITCH_DESCRIPTOR_KEY:
        #     translated_data[consts.SPACE_SWITCH_DESCRIPTOR_KEY] = json.loads(v)
        #     continue
        dag, settings, metadata = (
            v[consts.DAG_DESCRIPTOR_KEY] or '[]',
            v[consts.SETTINGS_DESCRIPTOR_KEY] or ('{}' if k == consts.RIG_LAYER_DESCRIPTOR_KEY else '[]'),
            v[consts.METADATA_DESCRIPTOR_KEY] or '[]'
        )
        translated_data[k] = {
            consts.DAG_DESCRIPTOR_KEY: json.loads(dag),
            consts.SETTINGS_DESCRIPTOR_KEY: json.loads(settings),
            consts.METADATA_DESCRIPTOR_KEY: json.loads(metadata)
        }

    return translated_data


class ComponentDescriptor(helpers.ObjectDict):
    """
    Class that describes a component.
    Used by the component setup methods and is the fallback data when the component has yet to be created in the scene.
    """

    VERSION = '1.0'

    def __init__(
            self, data: dict | None = None, original_descriptor: ComponentDescriptor | dict | None = None,
            path: str | None = None):

        data = data or {}
        data[consts.VERSION_DESCRIPTOR_KEY] = self.VERSION
        data[consts.INPUT_LAYER_DESCRIPTOR_KEY] = layers.InputLayerDescriptor.from_data(
            data.get(consts.INPUT_LAYER_DESCRIPTOR_KEY, {}))
        data[consts.OUTPUT_LAYER_DESCRIPTOR_KEY] = layers.OutputLayerDescriptor.from_data(
            data.get(consts.OUTPUT_LAYER_DESCRIPTOR_KEY, {}))
        data[consts.SKELETON_LAYER_DESCRIPTOR_KEY] = layers.SkeletonLayerDescriptor.from_data(
            data.get(consts.SKELETON_LAYER_DESCRIPTOR_KEY, {}))
        data[consts.RIG_LAYER_DESCRIPTOR_KEY] = layers.RigLayerDescriptor.from_data(
            data.get(consts.RIG_LAYER_DESCRIPTOR_KEY, {}))
        data[consts.PARENT_DESCRIPTOR_KEY] = data.get(consts.PARENT_DESCRIPTOR_KEY, [])
        data[consts.HOOK_DESCRIPTOR_KEY] = data.get(consts.HOOK_DESCRIPTOR_KEY, '')
        data[consts.CONNECTIONS_DESCRIPTOR_KEY] = data.get(consts.CONNECTIONS_DESCRIPTOR_KEY, {})

        super().__init__(data)

        self.path = path or ''
        self.original_descriptor = {}
        self.original_descriptor = ComponentDescriptor(original_descriptor) if original_descriptor is not None else {}

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}> {self.name}'

    @property
    def input_layer(self) -> layers.InputLayerDescriptor | None:
        return self[consts.INPUT_LAYER_DESCRIPTOR_KEY]

    @property
    def output_layer(self) -> layers.OutputLayerDescriptor | None:
        return self[consts.OUTPUT_LAYER_DESCRIPTOR_KEY]

    @property
    def skeleton_layer(self) -> layers.SkeletonLayerDescriptor | None:
        return self[consts.SKELETON_LAYER_DESCRIPTOR_KEY]

    @property
    def rig_layer(self) -> layers.RigLayerDescriptor | None:
        return self[consts.RIG_LAYER_DESCRIPTOR_KEY]

    @override(check_signature=False)
    def update(self, kwargs: dict):

        self[consts.INPUT_LAYER_DESCRIPTOR_KEY].update(kwargs.get(consts.INPUT_LAYER_DESCRIPTOR_KEY, {}))
        self[consts.OUTPUT_LAYER_DESCRIPTOR_KEY].update(kwargs.get(consts.OUTPUT_LAYER_DESCRIPTOR_KEY, {}))
        self[consts.SKELETON_LAYER_DESCRIPTOR_KEY].update(kwargs.get(consts.SKELETON_LAYER_DESCRIPTOR_KEY, {}))
        self[consts.RIG_LAYER_DESCRIPTOR_KEY].update(kwargs.get(consts.RIG_LAYER_DESCRIPTOR_KEY, {}))
        self._update_space_switching(kwargs.get(consts.SPACE_SWITCH_DESCRIPTOR_KEY, []))
        for k, v in kwargs.items():
            if k not in consts.DESCRIPTOR_KEYS_TO_SKIP_UPDATE:
                self[k] = v

    def serialize(self) -> dict:
        """
        Serializes the contents of the descriptor.

        :return: serialized descriptor.
        :rtype: dict
        """

        data = {}

        for k, v in self.items():
            if k in ('original_descriptor', 'path'):
                continue
            data[k] = v

        return data

    def to_json(self, template: bool = False) -> str:
        """
        Returns the string version of this descriptor.

        :param bool template: whether to return the version template of the descriptor.
        :return: descriptor as a string.
        :rtype: str
        """

        return json.dumps(self.to_template() if template else self.serialize())

    def to_scene_data(self) -> dict:
        """
        Returns a dictionary with the component data.

        :return: component dictionary data.
        :rtype: dict
        """

        serialized_data = self.serialize()

        output_data = {}

        for layer_key, [dag_layer_attr_name, settings_attr_name, metadata_attr_name, dg_attr_name] in \
                SCENE_LAYER_ATTR_TO_DESCRIPTOR.items():
            layer_data = serialized_data.get(layer_key, {})
            output_data[dag_layer_attr_name] = json.dumps(layer_data.get(consts.DAG_DESCRIPTOR_KEY, []))
            output_data[settings_attr_name] = json.dumps(
                layer_data.get(
                    consts.SETTINGS_DESCRIPTOR_KEY, [] if layer_key != consts.RIG_LAYER_DESCRIPTOR_KEY else {}))
            output_data[metadata_attr_name] = json.dumps(layer_data.get(consts.METADATA_DESCRIPTOR_KEY, []))
            if dg_attr_name:
                output_data[dg_attr_name] = json.dumps(layer_data.get(consts.DG_DESCRIPTOR_KEY, []))

        info_data = {}
        for key in (
                consts.NAME_DESCRIPTOR_KEY, consts.SIDE_DESCRIPTOR_KEY, consts.CONNECTIONS_DESCRIPTOR_KEY,
                consts.PARENT_DESCRIPTOR_KEY, consts.HOOK_DESCRIPTOR_KEY, consts.VERSION_DESCRIPTOR_KEY,
                consts.TYPE_DESCRIPTOR_KEY, consts.SKELETON_MARKING_MENU_DESCRIPTOR_KEY,
                consts.RIG_MARKING_MENU_DESCRIPTOR_KYE, consts.ANIM_MARKING_MENU_DESCRIPTOR_KEY,
                consts.NAMING_PRESET_DESCRIPTOR_KEY):
            info_data[key] = serialized_data.get(key, '')

        output_data[consts.NODDLE_DESCRIPTOR_CACHE_INFO_ATTR] = json.dumps(info_data)

        return output_data
    
    def pprint(self):
        """
        Pretty prints the current descriptor.
        """

        pprint.pprint(dict(self.serialize()))

    def _update_space_switching(self, spaces):
        pass
