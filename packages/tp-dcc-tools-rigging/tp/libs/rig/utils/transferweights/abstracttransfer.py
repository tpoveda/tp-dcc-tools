from __future__ import annotations

import abc

from tp.dcc import mesh, skin as skin_ctx
from tp.common.python import decorators


class AbstractTransfer(abc.ABC):
    """
    Abstract base class that handles weight transfer behaviour.
    """

    __slots__ = ('_mesh', '_skin', '_vertex_indices', '_vertex_map')
    __title__ = ''

    def __init__(self, *args):
        super().__init__()

        self._skin: skin_ctx.Skin | None = None
        self._mesh: mesh.Mesh | None = None
        self._vertex_indices: list[int] = []
        self._vertex_map: dict[int, int] = {}

        num_args = len(args)
        if num_args == 1:
            skin_fn = args[0]
            if not isinstance(skin_fn, skin_ctx.Skin):
                raise TypeError(f'{self.class_name}() expects a valid skin ({type(skin_ctx.Skin).__name__} given)!')
            # Store all vertex elements.
            self._skin = skin_fn
            self._mesh = mesh.Mesh(self._skin.intermediate_object())
            self._vertex_indices = list(range(self._skin.num_control_points()))
            self._vertex_map = dict(enumerate(self._vertex_indices))
        elif num_args == 2:
            skin_fn = args[0]
            if not isinstance(skin_fn, skin_ctx.Skin):
                raise TypeError(f'{self.class_name}() expects a valid skin ({type(skin_fn).__name__} given)!')
            # Inspect vertex elements type and store vertex elements
            vertex_indices = args[1]
            if not isinstance(vertex_indices, (list, tuple, set)):
                raise TypeError(f'{self.class_name}() expects a valid list ({type(vertex_indices).__name__} given)!')
            self._skin = skin_fn
            self._mesh = mesh.Mesh(self._skin.intermediate_object())
            self._vertex_indices = vertex_indices
            self._vertex_map = dict(enumerate(self._vertex_indices))
        else:
            raise TypeError(f'AbstractTransfer() expects 1 or 2 arguments ({num_args}s given)!')

    @decorators.classproperty
    def class_name(cls) -> str:
        """
        Getter method that returns the name of this class.

        :return: class name.
        :rtype: str
        """

        return cls.__name__

    @decorators.classproperty
    def title(cls) -> str:
        """
        Getter mtehod that returns the name of this class.

        :return: transfer class name.
        :rtype: str
        """

        return cls.__title__

    @property
    def skin(self) -> skin_ctx.Skin:
        """
        Getter method that returns the skin context object.

        :return: skin context object.
        :rtype: skin.Skin
        """

        return self._skin

    @property
    def mesh(self) -> mesh.Mesh:
        """
        Getter method that returns the mesh context object.

        :return: mesh context object.
        :rtype: mesh.Mesh
        """

        return self._mesh

    @property
    def vertex_indices(self) -> list[int]:
        """
        Getter method that returns the vertex index dataset.

        :return: list of vertex indices.
        :rtype: list[int]
        """

        return self._vertex_indices

    @property
    def vertex_map(self) -> dict[int, int]:
        """
        Getter method that returns the vertex local to global map.

        :return: vertex local to global map.
        :rtype: dict[int, int]
        """

        return self._vertex_map

    @abc.abstractmethod
    def transfer(self, other_skin: skin_ctx.Skin, vertex_indices: list[int]):
        """
        Transfers the weights from this skin to the given one.

        :param  skin_ctx.Skin other_skin: skin to transfer weights to.
        :param list[int] vertex_indices: vertex indices to transfer skin weights for.
        """

        pass
