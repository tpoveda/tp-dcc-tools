"""
Module that contains functions related with FRAG objects serialization.
"""

from collections import OrderedDict

from yaml import emitter, serializer, representer, resolver

from tp.core import dcc
from tp.common.python import helpers


class CritDumper(emitter.Emitter, serializer.Serializer, representer.SafeRepresenter, resolver.Resolver):
    def __init__(self,  stream, default_style=None, default_flow_style=False, canonical=None, indent=None, width=None,
                 allow_unicode=None, line_break=None, encoding=None, explicit_start=None, explicit_end=None,
                 version=None, tags=None, sort_keys=True):
        emitter.Emitter.__init__(self, stream, canonical=canonical, indent=indent, width=width,
                                 allow_unicode=allow_unicode, line_break=line_break)
        serializer.Serializer.__init__(self, encoding=encoding, explicit_start=explicit_start,
                                       explicit_end=explicit_end, version=version, tags=tags)
        representer.SafeRepresenter.__init__(self, default_style=default_style, default_flow_style=default_flow_style,
                                             sort_keys=sort_keys)
        resolver.Resolver.__init__(self)


CritDumper.ignore_aliases = lambda *args: True
CritDumper.add_representer(helpers.ObjectDict, CritDumper.represent_dict)
CritDumper.add_representer(OrderedDict, lambda dumper, data: dumper.represent_mapping(
    'tag:yaml.org,2002:map', data.items()))
if dcc.is_maya():
    from tp.libs.rig.crit.descriptors import attributes, component, nodes, layers, graphs, spaceswitch
    descriptor_classes = [
        component.ComponentDescriptor,
        attributes.AttributeDescriptor,
        attributes.VectorAttributeDescriptor,
        nodes.TransformDescriptor,
        nodes.ControlDescriptor,
        nodes.JointDescriptor,
        nodes.GuideDescriptor,
        nodes.InputDescriptor,
        nodes.OutputDescriptor,
        layers.LayerDescriptor,
        layers.GuideLayerDescriptor,
        layers.InputLayerDescriptor,
        layers.OutputLayerDescriptor,
        layers.SkeletonLayerDescriptor,
        layers.RigLayerDescriptor, graphs.NamedGraph,
        spaceswitch.SpaceSwitchDescriptor,
        spaceswitch.SpaceSwitchDriverDescriptor
    ]
    for descriptor_class in descriptor_classes:
        CritDumper.add_representer(descriptor_class, CritDumper.represent_dict)
    CritDumper.add_representer(graphs.NamedGraphs, CritDumper.represent_list)
