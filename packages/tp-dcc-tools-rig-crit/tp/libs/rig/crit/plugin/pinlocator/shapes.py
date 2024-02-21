#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains predefined shapes used by Pin Locator used by CRIT
"""

from __future__ import print_function, division, absolute_import

import maya.api.OpenMaya as OpenMaya
import maya.api.OpenMayaRender as OpenMayaRender


def make_ball():
    points = list()
    p1 = 1.0 / 2.0
    p2 = 0.5 / 2.0

    for x in (1, -1):
        points.append((x*p1, -p2, -p2))
        points.append((x*p1, +p2, -p2))
        points.append((x*p1, +p2, +p2))
        points.append((x*p1, -p2, +p2))

        points.append((-p2, x*p1, -p2))
        points.append((+p2, x*p1, -p2))
        points.append((+p2, x*p1, +p2))
        points.append((-p2, x*p1, +p2))

        points.append((-p2, -p2, x*p1))
        points.append((+p2, -p2, x*p1))
        points.append((+p2, +p2, x*p1))
        points.append((-p2, +p2, x*p1))

        for y in (1, -1):
            points.append((-p2, x*+p2, y*+p1))
            points.append((+p2, x*+p2, y*+p1))
            points.append((+p2, x*+p1, y*+p2))
            points.append((-p2, x*+p1, y*+p2))

            points.append((x*+p2, -p2, y*+p1))
            points.append((x*+p2, +p2, y*+p1))
            points.append((x*+p1, +p2, y*+p2))
            points.append((x*+p1, -p2, y*+p2))

            points.append((x*+p2, y*+p1, -p2))
            points.append((x*+p2, y*+p1, +p2))
            points.append((x*+p1, y*+p2, +p2))
            points.append((x*+p1, y*+p2, -p2))

    tris = list()
    for x in (1, -1):
        for y in (1, -1):
            for z in (1, -1):
                tris.append((x*-p1, y*-p2, z*p2))
                tris.append((x*-p2, y*-p1, z*p2))
                tris.append((x*-p2, y*-p2, z*p1))

    return {'quads': points, OpenMayaRender.MUIDrawManager.kTriangles: tris}


def make_pyramid():
    return {
        'quads': [
            (-0.5, 0, +0.5),
            (+0.5, 0, +0.5),
            (+0.5, 0, -0.5),
            (-0.5, 0, -0.5),
        ],

        OpenMayaRender.MUIDrawManager.kTriangles: [
            (-0.5, 0, +0.5),
            (-0.5, 0, -0.5),
            (+0.0, 1, -0.0),

            (+0.5, 0, +0.5),
            (+0.5, 0, -0.5),
            (+0.0, 1, -0.0),

            (-0.5, 0, -0.5),
            (+0.5, 0, -0.5),
            (+0.0, 1, -0.0),

            (+0.5, 0, +0.5),
            (-0.5, 0, +0.5),
            (+0.0, 1, -0.0),
        ]
    }


def make_orbit():
    """
    # A slightly larger shape that can sit around the others. Useful for things like pivots.
    """

    def make_box(x, y, z):
        s = 1/6.0
        box = [
            (-s, -s, +s),   # top
            (+s, -s, +s),
            (+s, -s, -s),
            (-s, -s, -s),

            (-s, +s, +s),   # bottom
            (+s, +s, +s),
            (+s, +s, -s),
            (-s, +s, -s),

            (-s, -s, +s),   # left
            (-s, +s, +s),
            (-s, +s, -s),
            (-s, -s, -s),

            (+s, -s, +s),   # right
            (+s, +s, +s),
            (+s, +s, -s),
            (+s, -s, -s),

            (-s, +s, +s),   # front
            (+s, +s, +s),
            (+s, -s, +s),
            (-s, -s, +s),

            (-s, +s, -s),   # back
            (+s, +s, -s),
            (+s, -s, -s),
            (-s, -s, -s),
        ]

        result = list()
        for vx, vy, vz in box:
            result.append((vx + x, vy + y, vz + z))
        return result

    boxes = list()
    boxes.extend(make_box(-1, 0, 0))
    boxes.extend(make_box(+1, 0, 0))
    boxes.extend(make_box(0, 0, +1))
    boxes.extend(make_box(0, 0, -1))

    return {'quads': boxes}


def convert_shape(shape):
    geometry = shape['geometry']
    lines = geometry.setdefault(OpenMayaRender.MUIDrawManager.kLines, list())

    # add edge lines for quads.
    if 'quads' in geometry:
        quads = geometry['quads']
        for i in range(0, len(quads), 4):
            lines.append(quads[i+0])
            lines.append(quads[i+1])
            lines.append(quads[i+1])
            lines.append(quads[i+2])
            lines.append(quads[i+2])
            lines.append(quads[i+3])
            lines.append(quads[i+3])
            lines.append(quads[i+0])

    # add edge lines for tris.
    if OpenMayaRender.MUIDrawManager.kTriangles in geometry:
        tris = geometry[OpenMayaRender.MUIDrawManager.kTriangles]
        for i in range(0, len(tris), 3):
            lines.append(tris[i+0])
            lines.append(tris[i+1])
            lines.append(tris[i+1])
            lines.append(tris[i+2])
            lines.append(tris[i+2])
            lines.append(tris[i+0])

    # convert quads to tris.
    if 'quads' in geometry:
        tris = geometry.setdefault(OpenMayaRender.MUIDrawManager.kTriangles, [])
        quads = geometry.pop('quads')

        for i in range(0, len(quads), 4):
            tris.append(quads[i+0])
            tris.append(quads[i+1])
            tris.append(quads[i+2])

            tris.append(quads[i+2])
            tris.append(quads[i+3])
            tris.append(quads[i+0])

    for key, data in geometry.items():
        array = OpenMaya.MPointArray()
        for point in data:
            array.append(OpenMaya.MPoint(*point))

        geometry[key] = array

    return shape


SHAPES = [
    {
        'name': 'Ball',
        'geometry': make_ball(),
    },
    {
        'name': 'Pyramid',
        'geometry': make_pyramid(),
    },
    {
        'name': 'Pivot',
        'geometry': make_orbit(),
    }
]
SHAPES = [convert_shape(shape) for shape in SHAPES]
