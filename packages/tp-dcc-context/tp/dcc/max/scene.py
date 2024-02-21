import enum

from tp.dcc.abstract import scene


class FileExtensions(enum.IntEnum):
    """
    Enumerator that defines available file extensions for 3ds Max
    """

    max = 0


class FnScene(scene.AFnScene):

    __slots__ = ()
    __extensions__ = FileExtensions
