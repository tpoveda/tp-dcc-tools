#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains commands for tpRigToolkit-rigtoolbox for Maya
"""

import maya.api.OpenMaya

from tp.core import command


class SetSkinWeights(command.DccCommand):
    """
    Creates a new curve from the library of shapes
    """

    id = 'tpDcc-dccs-maya-commands-setSkinWeights'
    creator = 'Tomas Poveda'
    is_undoable = True

    _skin_cluster = None
    _mesh_path = None
    _mesh_components = None
    _influences_array = None
    _old_weights = None

    def run(self, skin_cluster=None, mesh_path=None, mesh_components=None, influences_array=None, weights_array=None):

        self._skin_cluster = skin_cluster
        self._mesh_path = mesh_path
        self._mesh_components = mesh_components
        self._influences_array = influences_array

        skin_weights = self._get_skin_weights(skin_cluster, mesh_path, mesh_components, influences_array)
        self._old_weights = str(list(skin_weights))

        skin_cluster.setWeights(mesh_path, mesh_components, influences_array, weights_array, False)

    def undo(self):
        if self._old_weights and self._skin_cluster:
            weights_array = maya.api.OpenMaya.MDoubleArray()
            for i in self._old_weights[1:-1].split(','):
                weights_array.append(float(i))
            self._skin_cluster.setWeights(
                self._mesh_path, self._mesh_components, self._influences_array, weights_array, False)

    def _get_skin_weights(self, skin_cluster, mesh_path, mesh_components, influences_array):
        weights = skin_cluster.getWeights(mesh_path, mesh_components, influences_array)

        return weights
