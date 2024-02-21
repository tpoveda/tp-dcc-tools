from __future__ import annotations

import os
import typing
import numbers
from typing import Any, Callable

from tp.core import log
from tp.common.qt import api as qt
from tp.common.python import modules

logger = log.rigLogger

if typing.TYPE_CHECKING:
    from tp.common.nodegraph.core.node import BaseNode


DATA_TYPES_REGISTER = {}
NODES_REGISTER = {}
FUNCTIONS_REGISTER = {}
NODES_QUEUE = {}
FUNCTIONS_QUEUE = {}


def register_node(node_id: str, node_class: type):
    """
    Register node with given ID.

    :param str node_id: ID of the node to register.
    :param type node_class: class of the node to register.
    """

    if node_id in NODES_QUEUE:
        logger.error(f'Node with ID {node_id} is already registered as {node_class}')
        raise InvalidNodeRegistrationError

    NODES_QUEUE[node_id] = node_class


def register_function(
        func: Callable, source_data_type: dict, inputs: dict | None = None, outputs: dict | None = None,
        default_values: list[list[Any]] | None = None, nice_name: str | None = None, subtype: dict | None = None,
        category: str = 'General', docstring: str = '', icon: str = 'func.png'):
    """
    Registers given function.

    :param callable func: function to call.
    :param dict source_data_type: source data type.
    :param dict or None inputs: dictionary representing the inputs of the function node.
    :param dict or None outputs: dictionary representing the outputs of the function node.
    :param list[list[Any]] or None default_values: dictionary representing the default values of inputs.
    :param nice_name: node nice name.
    :param subtype: optional source subtype.
    :param category: optional node category
    :param docstring: optional function docstring.
    :param icon: optional icon name.
    :raises ValueError: if given source data type is not valid.
    """

    inputs = inputs or {}
    outputs = outputs or {}
    default_values = default_values if default_values is not None else []

    if source_data_type:
        if isinstance(source_data_type, dict):
            dt_name = DataType.type_name(source_data_type)
        else:
            logger.error(f'Invalid data type passed to register function: {source_data_type}')
            raise ValueError
    else:
        dt_name = 'UNBOUND'

    if source_data_type:
        source_class = source_data_type.get('class')
        if source_class:
            signature = f'{source_class.__module__}.{source_class.__name__}.{func.__name__}'
        else:
            signature = f'{func.__module__}.{func.__name__}'
    else:
        signature = f'{func.__module__}.{func.__name__}'
    if subtype:
        signature = f'{signature}({subtype})'

    func_dict = {
        'ref': func,
        'inputs': inputs,
        'outputs': outputs,
        'doc': docstring,
        'icon': icon,
        'nice_name': nice_name,
        'category': category,
        'default_values': default_values
    }

    FUNCTIONS_QUEUE.setdefault(dt_name, {})
    FUNCTIONS_QUEUE[dt_name][signature] = func_dict


def node_class_from_id(node_id: int) -> type:
    """
    Returns node class that matches given ID.

    :param int node_id: node ID.
    :return: node class.
    :rtype: type
    :raises NodeIDNotFoundError: if given node ID was not found within register.
    """

    if node_id not in NODES_REGISTER:
        logger.error(f'Node ID {node_id} was not found within register: {NODES_REGISTER}')
        raise NodeIDNotFoundError

    return NODES_REGISTER[node_id]


def function_from_signature(signature: str) -> dict | None:

    for dt_func_map in FUNCTIONS_REGISTER.values():
        if signature in dt_func_map:
            return dt_func_map[signature]

    return None


def load_plugins(extra_plugin_paths: list[str] | None = None):
    """
    Loads Noddle Rig editor plugins
    """

    logger.info('Loading Noddle Rig Editor plugins...')

    NODES_QUEUE.clear()
    FUNCTIONS_QUEUE.clear()
    # DATA_TYPES_REGISTER.clear()
    # NODES_REGISTER.clear()
    # FUNCTIONS_REGISTER.clear()

    DataType.register_basic_types()

    success_count = 0
    plugin_paths = []

    editor_plugin_paths = os.environ.get('TPDCC_NODEGRAPH_NODE_PATHS', '').split(os.pathsep)
    if not editor_plugin_paths:
        logger.warning('No NodeGraph node paths to register found')
        return

    editor_plugin_paths.extend(extra_plugin_paths or [])

    for editor_plugin_path in editor_plugin_paths:
        plugin_files = []
        if not os.path.isdir(editor_plugin_path):
            continue
        for file_name in os.listdir(editor_plugin_path):
            pass
            if not file_name.endswith('.py') or not file_name.startswith('node_'):
                continue
            plugin_files.append(file_name)
        if 'node_function.py' in plugin_files:
            plugin_files.insert(0, plugin_files.pop(plugin_files.index('node_function.py')))
        if 'node_character.py' in plugin_files:
            plugin_files.insert(0, plugin_files.pop(plugin_files.index('node_character.py')))
        plugin_paths.extend([os.path.join(editor_plugin_path, file_name) for file_name in plugin_files])

    for plugin_path in plugin_paths:
        plugin_name = os.path.splitext(os.path.basename(plugin_path))[0]
        plugin_module = modules.import_module(plugin_path)
        try:
            plugin_module.register_plugin(register_node, register_function, DataType.register_data_type)
            success_count += 1
        except Exception:
            logger.exception(f'Failed to register plugin: {plugin_name}', exc_info=True)

    # Register nodes.
    for node_id, node_class in NODES_QUEUE.items():
        NODES_REGISTER[node_id] = node_class
        logger.debug(f'Registered node { node_id}::{node_class}')
    NODES_QUEUE.clear()

    # Register functions.
    for dt_name in FUNCTIONS_QUEUE.keys():
        if dt_name not in FUNCTIONS_REGISTER.keys():
            FUNCTIONS_REGISTER[dt_name] = {}
        for signature, func_dict in FUNCTIONS_QUEUE[dt_name].items():
            FUNCTIONS_REGISTER[dt_name][signature] = func_dict
            logger.debug(f'Function registered {dt_name}::{signature}')
    FUNCTIONS_QUEUE.clear()

    logger.info(f'Successfully loaded {success_count} plugins')


def instancer(cls):
    return cls()


class RegisterError(Exception):
    pass


class InvalidDataTypeRegistrationError(RegisterError):
    pass


class InvalidNodeRegistrationError(RegisterError):
    pass


class NodeIDNotFoundError(RegisterError):
    pass


@instancer
class DataType:
    EXEC = {'class': type(None), 'color': qt.QColor("#FFFFFF"), 'label': '', 'default': None}
    STRING = {'class': str, 'color': qt.QColor("#A203F2"), 'label': 'Name', 'default': ''}
    NUMERIC = {'class': numbers.Complex, 'color': qt.QColor("#DEC017"), 'label': 'Number', 'default': 0.0}
    BOOLEAN = {'class': bool, 'color': qt.QColor("#C40000"), 'label': 'Condition', 'default': False}
    LIST = {'class': list, 'color': qt.QColor("#0BC8F1"), 'label': 'List', 'default': []}

    def __getattr__(self, item: str):
        if item in DATA_TYPES_REGISTER:
            return DATA_TYPES_REGISTER[item]
        else:
            logger.error(f'Unregistered data type: {item}')
            raise KeyError

    @classmethod
    def basic_types(cls):
        return [(dt, desc) for dt, desc in cls.__dict__.items() if isinstance(desc, dict)]

    @classmethod
    def register_basic_types(cls):
        logger.debug('Registering base data types')
        for type_name, type_dict in cls.basic_types():
            DATA_TYPES_REGISTER[type_name] = type_dict

    @classmethod
    def is_type_registered(cls, type_name: str) -> bool:
        """
        Returns whether given type name is already registered.

        :param str type_name: type name to check.
        :return: True if given type name is already registered; False otherwise.
        :rtype: bool
        """

        return type_name in DATA_TYPES_REGISTER.keys()

    @classmethod
    def register_data_type(
            cls, type_name: str, type_class: type, color: qt.QColor, label: str = 'custom_data',
            default_value: Any = None, raise_existence_exception: bool = False):
        if cls.is_type_registered(type_name):
            if not raise_existence_exception:
                return
            logger.error(f'Datatype {type_name} is already registered')
            raise InvalidDataTypeRegistrationError

        type_dict = {
            'class': type_class,
            'color': color if isinstance(color, qt.QColor) else qt.QColor(color),
            'label': label,
            'default': default_value}
        DATA_TYPES_REGISTER[type_name] = type_dict

    @classmethod
    def runtime_types(cls, names: bool = False, classes: bool = False) -> list[dict]:
        result = []

        # TODO: A datatype should be define by itself whether is runtime
        runtime_types = [cls.LIST['class']]
        if 'COMPONENT' in DATA_TYPES_REGISTER:
            runtime_types.append(DATA_TYPES_REGISTER['COMPONENT']['class'])
        if 'CONTROL' in DATA_TYPES_REGISTER:
            runtime_types.append(DATA_TYPES_REGISTER['CONTROL']['class'])
        runtime_types = tuple(runtime_types)

        for type_name, type_desc in DATA_TYPES_REGISTER.items():
            if issubclass(type_desc['class'], runtime_types):
                if names:
                    result.append(type_name)
                elif classes:
                    result.append(type_desc['class'])
                else:
                    result.append(DATA_TYPES_REGISTER[type_name])

        return result

    @classmethod
    def type_name(cls, data_type_dict: dict) -> str:
        try:
            type_name = [dt_name for dt_name, desc in DATA_TYPES_REGISTER.items() if desc == data_type_dict][0]
            return type_name
        except IndexError:
            logger.exception(f'Failed to find datatype for class {data_type_dict["class"]}')
            raise IndexError

    @classmethod
    def type_from_name(cls, type_name) -> dict:
        try:
            return DATA_TYPES_REGISTER[type_name]
        except KeyError:
            logger.error(f'Unregistered data type: {type_name}')
            raise
