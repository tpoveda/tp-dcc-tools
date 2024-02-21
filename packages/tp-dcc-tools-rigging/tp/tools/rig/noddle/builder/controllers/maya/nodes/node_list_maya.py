from __future__ import annotations

from typing import Any, Callable

from tp.tools.rig.noddle.builder import api


def item_from_list(in_list: list[Any], index: int) -> Any:
    return in_list[int(index)]


def register_plugin(register_node: Callable, register_function: Callable, register_data_type: Callable):

    register_function(
        item_from_list, api.DataType.LIST,
        inputs={'List': api.DataType.LIST, 'Index': api.DataType.NUMERIC}, outputs={'Item': api.DataType.CONTROL},
        default_values=[[], 0], nice_name='Get Control', subtype='control', category='List')
    register_function(
        item_from_list, api.DataType.LIST,
        inputs={'List': api.DataType.LIST, 'Index': api.DataType.NUMERIC}, outputs={'Item': api.DataType.COMPONENT},
        default_values=[[], 0], nice_name='Get Component', subtype='component', category='List')
    register_function(
        item_from_list, api.DataType.LIST,
        inputs={'List': api.DataType.LIST, 'Index': api.DataType.NUMERIC},
        outputs={'Item': api.DataType.ANIM_COMPONENT}, default_values=[[], 0], nice_name='Get AnimComponent',
        subtype='animcomponent', category='List')
