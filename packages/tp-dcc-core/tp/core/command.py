#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains DCC command implementation
"""

from __future__ import annotations

import sys
import time
import inspect
import traceback
from typing import Any
from collections import deque
from abc import ABCMeta, abstractmethod

from overrides import override

from tp.core import log, exceptions, dcc, output
from tp.common.python import decorators, osplatform
from tp.common import plugin


logger = log.tpLogger


def execute(command_id: str, **kwargs) -> Any:
    """
    Executes given DCC command with given ID.

    :param str command_id: DCC command ID to execute.
    :return: DCC command result.
    :rtype: Any
    """

    return CommandRunner().run(command_id, **kwargs)


@decorators.add_metaclass(ABCMeta)
class DccCommandInterface:
    """
    DCC command metaclass interface. Each DCC command MUST implement this interface.
    """

    class ArgumentParser(dict):
        def __getattr__(self, item):
            result = self.get(item)
            if result:
                return result

            return super().__getattribute__(item)

    id: str | None = None
    creator = ''
    is_undoable = False
    is_enabled = True
    UI_DATA = {'icon': '', 'tooltip': '', 'label': '', 'color': '', 'backgroundColor': ''}

    def __init__(self, stats: CommandStats | None = None):
        self._stats = stats
        self._arguments = DccCommandInterface.ArgumentParser()
        self._return_result = None
        self._warning = ''
        self.initialize()

    @property
    def stats(self) -> CommandStats | None:
        return self._stats

    @stats.setter
    def stats(self, value: CommandStats):
        self._stats = value

    @property
    def arguments(self) -> DccCommandInterface.ArgumentParser:
        return self._arguments

    def initialize(self):
        """
        Function that should be overridden by subclasses.
        Intended to be used as a replacement for the code that should be initialized witin __init__ function.
        """

        pass

    @abstractmethod
    def do(self, **kwargs: dict) -> Any:
        """
        Executes the command functionality. This function only supports keyword arguments, so every argument MUST have
        a default value.

        :param dict kwargs: dictionary with key value pairs. Any kind of type is supported (even DCC specific types).
        :return: command run result.
        :rtype: Any
        """

        raise NotImplementedError('abstract command DCC function run not implemented!')

    def undo(self):
        """
        If the command is undoable this function is call to reverse the operation done by run function.
        """

        pass

    def run(self) -> Any:
        """
        Runs `do` function with the current arguments.

        :return: command run result.
        :rtype: Any
        """

        return self.do(**self._arguments)

    def run_arguments(self, **arguments) -> Any:
        """
        Runs `do function with given arguments.

        :param arguments: key , value pairs corresponding to arguments for `do` function.
        :return: command run result.
        :rtype: Any
        """

        self.parse_arguments(arguments)
        return self.run()

    def parse_arguments(self, arguments: dict):
        """
        Parses given arguments, so they are ready to be passed to the command `do` function.

        :param dict arguments: arguments as dictionary.
        """

        kwargs = self._arguments
        kwargs.update(arguments)
        result = self.resolve_arguments(DccCommandInterface.ArgumentParser(**kwargs)) or {}
        kwargs.update(result)

    def resolve_arguments(self, arguments: dict) -> dict | None:
        """
        Function that is called before running the command. Useful to valid incoming command arguments before executing
        the command.

        :param dict arguments: key, value pairs of commands being passed to the run command function
        :return: dictionary with the same key value pairs as the arguments param.
        :rtype: dict or None
        """

        return arguments


class DccCommand(DccCommandInterface):

    is_enabled = True
    use_undo_chunk = True           # whether to chunk all operations in `do`
    disable_queue = False           # whether to disable the undo queue in `do`

    @override
    def initialize(self):
        self.prepare_command()

    @override
    def do(self, **kwargs: dict) -> Any:
        raise NotImplementedError

    def prepare_command(self):
        """
        Prepares command so it can be executed.
        """

        func_args = inspect.getfullargspec(self.run)
        args = func_args.args[1:]
        defaults = func_args.defaults or tuple()
        if len(args) != len(defaults):
            raise ValueError('Command run function({}) must only use keyword arguments.'.format(self.id))
        elif args and defaults:
            arguments = self.ArgumentParser(zip(args, defaults))
            self._arguments = arguments
            return arguments

        return self.ArgumentParser()

    def description(self) -> str:
        """
        Returns the description of the command. Class doc is used by default.

        :return: command description.
        :rtype: str
        """

        return self.__doc__

    def has_argument(self, name: str) -> bool:
        """
        Returns whether this command supports given argument.

        :param str name: argument name.
        :return: True if command supports given arguments; False otherwise.
        :rtype: bool
        """

        return name in self._arguments

    def parse_arguments(self, arguments: dict) -> bool:
        """
        Parses given command arguments and prepares them for the command to use.

        :param dict arguments: arguments to parse.
        :return: True if the parse arguments operation was successful; False otherwise.
        :rtype: bool
        """

        kwargs = self._arguments
        kwargs.update(arguments)
        result = self.resolve_arguments(self.ArgumentParser(**kwargs)) or {}
        kwargs.update(result)

        return True

    def requires_warning(self) -> bool:
        """
        Returns whether this command requires warning.

        :return: True if command has warning; False otherwise.
        :rtype: bool
        """

        return True if self._warning else False

    def warning_message(self) -> str:
        """
        Returns command warning message.

        :return: warning message.
        :rtype: str
        """

        return self._warning

    def display_warning(self, message: str):
        """
        Sets display warning message to show.

        :param str message: warning message.
        """

        self._warning = message

    def cancel(self, msg: str | None = None):
        """
        Raises user cancel error.

        :param str or None msg: optional message to show.
        :raises exceptions.CommandCancel: when cancelling command execution.
        """

        raise exceptions.CommandCancel(msg)


class CommandStats:
    def __init__(self, command: DccCommand):
        self._command = command
        self._start_time = 0.0
        self._end_time = 0.0
        self._execution_time = 0.0

        self._info = {}

        self._init()

    @property
    def start_time(self) -> float:
        return self._start_time

    @start_time.setter
    def start_time(self, value: float):
        self._start_time = value

    @property
    def end_time(self) -> float:
        return self._end_time

    @end_time.setter
    def end_time(self, value: float):
        self._end_time = value

    @property
    def execution_time(self) -> float:
        return self._execution_time

    def _init(self):
        """
        Internal function that initializes info for the command and its environment.
        """

        self._info.update({
            'name': self._command.__class__.__name__,
            'creator': self._command.creator,
            'module': self._command.__class__.__module__,
            'filepath': inspect.getfile(self._command.__class__),
            'id': self._command.id,
            'application': dcc.name()
        })
        self._info.update(osplatform.machine_info())

    def start(self):
        """
        Starts the execution of the command.
        """

        self._start_time = time.time()

    def finish(self, trace: str | None = None):
        """
        Function that is called when plugin finishes its execution.

        :param str or None trace: optional trace stack.
        """

        self._end_time = time.time()
        self._execution_time = self._end_time - self._start_time
        self._info['executionTime'] = self._execution_time
        self._info['lastUsed'] = self._end_time
        if trace:
            self._info['traceback'] = trace


class MetaCommandRunner(type):
    """
    Command runner singleton class that returns runner class based on current DCC.
    """

    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            if dcc.is_maya():
                from tp.maya.api import command
                cls._instance = type.__call__(command.MayaCommandRunner, *args, **kwargs)
            else:
                cls._instance = type.__call__(BaseCommandRunner, *args, **kwargs)

        return cls._instance


class BaseCommandRunner:
    def __init__(self, interface: type | None = None, register_env: str = 'TPDCC_COMMAND_LIB'):
        interface = interface or DccCommand
        self._undo_stack: deque[DccCommand] = deque()
        self._redo_stack: deque[DccCommand] = deque()
        self._manager = plugin.PluginFactory(interface, plugin_id='id')
        self._manager.register_paths_from_env_var(register_env, package_name='tp-dcc')

    @property
    def undo_stack(self) -> deque:
        return self._undo_stack

    @property
    def redo_stack(self) -> deque:
        return self._redo_stack

    def commands(self) -> list[DccCommand]:
        return self._manager.plugins()

    def manager(self) -> plugin.PluginFactory:
        return self._manager

    def run(self, command_id: str, **kwargs: dict) -> Any:
        """
        Run the command with given ID.

        :param str command_id: ID of the command to run.
        :param Dict kwargs: keyword arguments for the command execution.
        :return: command run result.
        :rtype: Any
        """

        command_to_run = self.find_command(command_id)
        if not command_to_run:
            raise ValueError(f'No command found with given id "{command_id}"')

        command_to_run = command_to_run(CommandStats(command_to_run))
        if not command_to_run.is_enabled:
            return
        try:
            command_to_run.parse_arguments(kwargs)
            if command_to_run.requires_warning():
                output.display_warning(command_to_run.warning_message())
                return
        except exceptions.CommandCancel:
            return
        except Exception:
            raise

        exc_tb, exc_type, exc_value = None, None, None
        result = None
        try:
            result = self._run(command_to_run)
        except exceptions.CommandCancel:
            self._undo_stack.remove(command_to_run)
            command_to_run.stats.finish(None)
            return result
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            raise
        finally:
            tb = None
            if exc_type and exc_value and exc_tb:
                tb = traceback.format_exception(exc_type, exc_value, exc_tb)
            elif command_to_run.is_undoable:
                self._undo_stack.append(command_to_run)
            command_to_run.stats.finish(tb)

            return result

    def undo_last(self) -> bool:
        """
        Undoes last executed command.
        :return: True if the undo operation was successful; False otherwise.
        :rtype: bool
        """

        if not self._undo_stack:
            return False

        command_to_undo = self._undo_stack[-1]
        if command_to_undo is not None and command_to_undo.is_undoable:
            command_to_undo.undo()
            self._redo_stack.append(command_to_undo)
            self._undo_stack.remove(command_to_undo)
            return True

        return False

    def redo_last(self) -> Any:
        """
        Redoes last undo command.

        :return: redo command result.
        :rtype: Any
        """

        exc_tb, exc_type, exc_value = None, None, None
        result = None
        if self._redo_stack:
            command_to_redo = self._redo_stack.pop()
            if command_to_redo is not None:
                try:
                    command_to_redo.stats = CommandStats(command_to_redo)
                    result = self._run(command_to_redo)
                except exceptions.CommandCancel:
                    self._undo_stack.remove(command_to_redo)
                    command_to_redo.stats.finish(None)
                    raise
                except Exception:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    raise
                finally:
                    tb = None
                    if exc_type and exc_value and exc_tb:
                        tb = traceback.format_exception(exc_type, exc_value, exc_tb)
                    elif command_to_redo.is_undoable:
                        self._undo_stack.append(command_to_redo)
                    command_to_redo.stats.finish(tb)

        return result

    def find_command(self, command_id: str) -> type[DccCommand] | None:
        """
        Returns registered command by its ID.

        :param str command_id: ID of the command to find.
        :return: found command.
        :rtype: type or None
        """

        return self._manager.get_plugin_from_id(command_id)

    def command_help(self, command_id: str) -> str:
        """
        Returns the command help of the given command.

        :param str command_id: ID of the command to get help of.
        :return: command help.
        :rtype: str
        """

        command = self.find_command(command_id)
        if not command:
            return ''

        doc_help = inspect.getdoc(command)
        run_help = inspect.getdoc(command.run)

        return f"""
        Class: {command.__name__}
        {doc_help}
        Run:
        {run_help}
        """

    def flush(self):
        """
        Clears the undo/redo history of the command.
        """

        self._undo_stack.clear()
        self._redo_stack.clear()

    def cancel(self, msg: str):
        """
        Cancels command execution.

        :param str msg: cancel message.
        """

        raise exceptions.CommandCancel(msg)

    def _run(self, command_to_run: DccCommand) -> Any:
        """
        Internal function that executes given command.

        :param DccCommand command_to_run: command to run.
        :return: command run result.
        :rtype: Any
        """

        result = command_to_run.do(**command_to_run.arguments)
        command_to_run._return_result = result

        return result


@decorators.add_metaclass(MetaCommandRunner)
class CommandRunner:
    """
    Command runner class
    """

    pass
