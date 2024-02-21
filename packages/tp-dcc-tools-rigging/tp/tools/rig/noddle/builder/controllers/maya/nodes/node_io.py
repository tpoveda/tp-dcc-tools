from __future__ import annotations

from typing import Callable

from tp.libs.rig.noddle import io
from tp.tools.rig.noddle.builder import api


def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):

    register_function(
        io.SkinManager.import_all, None,
        nice_name='Import Skin Weights', category='Data')
    register_function(
        io.NgLayers2Manager.import_all, None,
        nice_name='Import NgLayers2', category='Data')
    register_function(
        io.ControlsShapeManager.import_asset_shapes, None,
        nice_name='Import Control Shapes', category='Data')
    register_function(
        io.BlendShapesManager.import_all, None,
        nice_name='Import BlendShapes', category='Data')
    register_function(
        io.DrivenPoseManager.import_all, None,
        nice_name='Import Driven Poses', category='Data')
    register_function(
        io.PsdManager.import_all, None,
        nice_name='Import PSD', category='Data')
    register_function(
        io.SdkCorrectivesManager.import_all, None,
        nice_name='Import SDK Correctives', category='Data')
    register_function(
        io.DeltaMushManager.import_all, None,
        inputs={'Character': api.DataType.CHARACTER},
        nice_name='Import DeltaMush', category='Data')
