from tp.dcc import abstract
from tp.dcc.abstract import node


class FnNode(node.AFnNode):

    __slots__ = ()
    __array_index_type__ = abstract.ArrayIndexType.OneBased
