#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains tpDcc log manager
"""

from __future__ import annotations

import os
import logging

main = __import__('__main__')

LOGGER_NAME = 'tp.dcc'
BOOTSTRAP_LOGGER_NAME = 'tp.dcc.bootstrap'
RIG_LOGGER_NAME = 'tp.dcc.rig'
ANIM_LOGGER_NAME = 'tp.dcc.anim'
MODEL_LOGGER_NAME = 'tp.dcc.modeling'
LOG_LEVEL_ENV_NAME = 'TPDCC_LOG_LEVEL'


def log_levels() -> map:
    """
    Returns a list with all levels available within Python logging system.

    :return: list of log levels.
    :rtype: list[str]
    """

    return map(logging.getLevelName, range(0, logging.CRITICAL + 1, 10))


def levels_dict() -> dict[str, str]:
    """
    Returns a dict with all levels available within Python logging system.

    :return: dictionary log levels.
    :rtype: dict[str, str]
    """

    return {logging.getLevelName(i): i for i in range(0, logging.CRITICAL + 1, 10)}


def global_log_level_override(log_to_override: logging.Logger):
    """
    Makes sure the global level override is set.

    :param logging.Logger log_to_override: logger to set.
    """

    global_logging_level = os.environ.get(LOG_LEVEL_ENV_NAME, 'INFO')
    env_level = levels_dict()[global_logging_level]
    current_level = log_to_override.getEffectiveLevel()
    if not current_level or current_level != env_level:
        log_to_override.setLevel(env_level)


def get_logger(name: str) -> logging.Logger:
    """
    Returns tp-dcc-tools framework log name in the form tp.dcc.tools.*

    :param str name: logger name to retrieve.
    :return: logger instance.
    :rtype: logging.Logger
    """

    if name == LOGGER_NAME:
        name = LOGGER_NAME
    elif name == BOOTSTRAP_LOGGER_NAME:
        name = BOOTSTRAP_LOGGER_NAME
    elif name.startswith('preferences.'):
        name = f'tp.dcc.preferences.{name[len("preferences."):]}'
    logger = logging.getLogger(name)
    LogsManager().add_log(logger)

    return logger


def logging_wrapper(method, source_name, *args, **kwargs):
    """
    Wrapper function to log any individual method call.

    :param fn method: method to wrap.
    :param str source_name: name to tag into the logging file for this log.
    :param list args: arguments for the method.
    :param dict kwargs: keyword arguments for the method.
    """

    def method_wrap(*args, **kwargs):
        print_args = [x for x in args if (not type(x) == dict) and (not type(x) == list)]
        tpLogger.info('{} -----> {}.{} ~~ Args:{} Kwargs:{}'.format(
            source_name, method.__module__, method.__name__, print_args, kwargs))
        return method(*args, **kwargs)

    return method_wrap, args, kwargs


def add_metaclass(metaclass):
    """
    Decorators that allows to create a class using a metaclass
    https://github.com/benjaminp/six/blob/master/six.py
    """

    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        if hasattr(cls, '__qualname__'):
            orig_vars['__qualname__'] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)

    return wrapper


class Singleton(type):
    """
    Singleton decorator as metaclass. Should be used in conjunction with add_metaclass function of this module

    @add_metaclass(Singleton)
    class MyClass(BaseClass, object):
    """

    def __new__(meta, name, bases, clsdict):
        if any(isinstance(cls, meta) for cls in bases):
            raise TypeError('Cannot inherit from singleton class')
        clsdict['_instance'] = None
        return super(Singleton, meta).__new__(meta, name, bases, clsdict)

    def __call__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance


@add_metaclass(Singleton)
class LogsManager:
    """
    Singleton class that globally handles all tp-dcc-tools framework related loggers
    """

    def __init__(self):

        self._logs = dict()
        # [%(levelname)1.1s  %(asctime)s | %(name)s | %(module)s:%(funcName)s:%(lineno)d] > %(message)s
        self.json_formatter = "%(asctime) %(name) %(processName) %(pathname)  %(funcName) %(levelname) %(lineno) %(" \
                              "module) %(threadName) %(message)"
        self.rotate_formatter = "%(asctime)s: [%(process)d - %(name)s - %(levelname)s]: %(message)s"
        self.shell_formatter = "[%(levelname)1.1s|%(name)s|%(module)s:%(funcName)s:%(lineno)s] > %(message)s"
        self.gui_formatter = "[%(name)s]: %(message)s"

    def add_log(self, logger):
        """
        Adds a logger into this manager instance.

        :param logging.Logger logger: logger instance to add.
        """

        if logger.name not in self._logs:
            self._logs[logger.name] = logger

        global_log_level_override(logger)

    def remove_log(self, logger_name):
        """
        Removes the logger instance by name.

        :param str logger_name: name of the log to remove.
        :return: True if log was removed successfully; False otherwise.
        :rtype: bool
        """

        if logger_name not in self._logs:
            return False

        del self._logs[logger_name]

        return True

    def change_level(self, logger_name, level):
        """
        Changes the logger instance level.

        :param str logger_name: name of the logger to change level of.
        :param logging.Level level: logger level.
        """

        found_log = self._logs.get(logger_name)
        if not found_log or found_log.level == level:
            return
        found_log.setLevel(level)

    def add_shell_handler(self, logger_name: str) -> logging.StreamHandler | None:
        """
        Adds a stream handler to the logger with the given name that outputs to the shell.

        :param str logger_name: name of the logger to which the handler will be added.
        :return: stream handler object that was added to the logger.
        :rtype: logging.StreamHandler or None
        """

        found_log = self._logs.get(logger_name)
        if not found_log:
            return None
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(self.shell_formatter))
        found_log.addHandler(handler)

        return handler

    def add_handler(self, logger_name, handler):
        """
        Adds a new log handler to the log with given name.

        :param str logger_name:
        :param logging.StreamHandler handler: handler to add.
        :return: added handler.
        :rtype: logging.StreamHandler or None
        """

        found_log = self._logs.get(logger_name)
        if found_log is None:
            return None

        formatter = logging.Formatter(self.shell_formatter)
        handler.setFormatter(formatter)
        found_log.addHandler(handler)

        return handler

    def remove_handlers(self, logger_name: str):
        """
        Removes all handlers from the log with given name.

        :param str logger_name: name of the log whose handlers we want to delete.
        :return: True if handlers were removed successfully; False otherwise.
        :rtype: bool
        """

        found_log = self._logs.get(logger_name)
        if found_log is None:
            return False

        found_log.handlers = []

        return True

    def clear_logs(self):
        """
        Clears all logs.
        """

        for _, found_log in self._logs.items():
            found_log.handlers = []
        self._logs.clear()


tpLogger = get_logger(LOGGER_NAME)
bootstrapLogger = get_logger(BOOTSTRAP_LOGGER_NAME)
rigLogger = get_logger(RIG_LOGGER_NAME)
animLogger = get_logger(ANIM_LOGGER_NAME)
modelLogger = get_logger(MODEL_LOGGER_NAME)
for logger in [tpLogger, bootstrapLogger, rigLogger, animLogger, modelLogger]:
    logger.propagate = False
    handlers = logger.handlers
    if not handlers:
        LogsManager().add_shell_handler(logger.name)
