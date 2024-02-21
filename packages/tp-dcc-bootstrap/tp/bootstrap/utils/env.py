#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains utilities functions to interact with environment variables.
"""

import os
import sys
import math
import platform

from tp.bootstrap import log

text_type = str
binary_type = bytes

logger = log.bootstrapLogger


SEPARATOR = '/'
BAD_SEPARATOR = '\\'
PATH_SEPARATOR = '//'
SERVER_PREFIX = '\\'
RELATIVE_PATH_PREFIX = './'
BAD_RELATIVE_PATH_PREFIX = '../'
WEB_PREFIX = 'https://'


def ensure_str(s, encoding='utf-8', errors='strict'):
    """
    Function that ensures that given variable is a string.

    :param s: variable to check.
    :param str encoding: encoding to use (by default, utf-8 will be used).
    :param str errors: how errors will be treated.
    :return: string variable.
    :rtype: str
    """

    if type(s) is str:
        return s
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    elif not isinstance(s, (text_type, binary_type)):
        raise TypeError("not expecting type '%s'" % type(s))
    return s


def add_to_env(env, new_paths):
    """
    Adds the given environment paths into the given environment variable if the path is not already added to it.

    :param str env: environment variable name.
    :param list(str) new_paths: list of paths to add to given environment variable.
    """

    paths = [i for i in os.getenv(env, '').split(os.pathsep) if i]
    for p in new_paths:
        if p not in paths:
            paths.append(p)

    os.environ[ensure_str(env)] = ensure_str(os.pathsep.join(paths))


def is_python2():
    """
    Returns whether current version is Python 2

    :return: bool
    """

    return sys.version_info[0] == 2


def is_python3():
    """
    Returns whether current version is Python 3

    :return: bool
    """

    return sys.version_info[0] == 3


def is_in_maya(executable=None):
    """
    Returns whether current running executable is Maya

    :param str executable: optional executable name.
    :return: True if we are running Maya executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = ("maya", "maya.exe", "maya.bin")
    return os.path.basename(executable).endswith(ends_with_key)


def is_mac():
    """
    Returns whether current system is macOS.

    :return: True if system is macOS; False otherwise.
    :rtype: bool
    """

    plat = platform.system().lower()
    return plat.startswith(('mac', 'os', 'darwin'))


def is_windows():
    """
    Returns whether current system is Windows.

    :return: True if system is Windows; False otherwise.
    :rtype: bool
    """

    return platform.system().lower().startswith('win')


def is_linux():
    """
    Returns whether current system is Linux.

    :return: True if system is Linux; False otherwise.
    :rtype: bool
    """

    return platform.system().lower().startswith('lin')


def is_unix_based():
    """
    Returns whether current operating system is Unix based.

    :return: True if current operating system is Unix based; False otherwise.
    :rtype: bool
    """

    return is_mac() or is_linux()


def current_os():
    """
    Returns current operating system.

    :return: operating system as a string.
    :rtype: str
    """

    if is_windows():
        return 'Windows'
    elif is_mac():
        return 'Mac'
    elif is_linux():
        return 'Linux'


def is_mayapy(executable=None):
    """
    Returns whether current running executable is Mayapy.

    :param str executable: optional executable name.
    :return: True if we are running MayaPy executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = ("mayapy", "mayapy.exe")
    return os.path.basename(executable).endswith(ends_with_key)


def is_maya_batch(executable=None):
    """
    Returns whether current running executable is Maya batch.

    :param str executable: optional executable name.
    :return: True if we are running MayaBatch executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = ("mayabatch", "mayabatch.exe")
    return os.path.basename(executable).endswith(ends_with_key)


def is_maya(executable=None):
    """
    Combines all Maya executable checkers.

    :param str executable: optional executable name.
    :return: True if we are running Maya (or its variant) executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = ("maya", "maya.exe", "maya.bin", "mayapy", "mayapy.exe", "mayabatch", "mayabatch.exe")
    return os.path.basename(executable).endswith(ends_with_key)


def is_in_3dsmax(executable=None):
    """
    Returns whether current running executable is 3ds Max.

    :param str executable: optional executable name.
    :return: True if we are running 3ds Max executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = ("3dsmax", "3dsmax.exe")
    return os.path.basename(executable).endswith(ends_with_key)


def is_in_motionbuilder(executable=None):
    """
    Returns whether current running executable is MotionBuilder.

    :param str executable: optional executable name.
    :return: True if we are running MotionBulder executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = ("motionbuilder", "motionbuilder.exe")
    return os.path.basename(executable).endswith(ends_with_key)


def is_in_houdini(executable=None):
    """
    Returns whether current running executable is Houdini.

    :param str executable: optional executable name.
    :return: True if we are running Houdini executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = ("houdini", "houdinifx", "houdinicore", "happrentice")
    return os.path.basename(executable).endswith(ends_with_key)


def is_in_blender(executable=None):
    """
    Returns whether current running executable is Blender.

    :param str executable: optional executable name.
    :return: True if we are running Blender executable; False otherwise.
    :rtype: bool
    """

    try:
        import bpy
        if type(bpy.app.version) == tuple:
            return True
    except ImportError or AttributeError:
        return False


def is_in_unreal(executable=None):
    """
    Returns whether current running executable is Unreal.

    :param str executable: optional executable name.
    :return: True if we are running Unreal executable; False otherwise.
    :rtype: bool
    """

    executable = (executable or sys.executable).lower()
    ends_with_key = (
        "unreal", "unreal.exe", "ue4_editor", "ue4_editor.exe", "ue5_editor", "ue5_editor.exe", "unrealeditor.exe")
    return os.path.basename(executable).endswith(ends_with_key)


def application():
    """
    Returns the currently running application.

    :return: application manager is running on.
    """

    if any((is_in_maya(), is_mayapy(), is_maya_batch())):
        return "maya"
    elif is_in_3dsmax():
        return "3dsmax"
    elif is_in_motionbuilder():
        return "mobu"
    elif is_in_houdini():
        return "houdini"
    elif is_in_blender():
        return "blender"
    elif is_in_unreal():
        return "unreal"
    return "standalone"


def application_version(dcc_name=None):
    """
    Returns the version of the currently running application.

    :return: version as a string.
    :rtype: str
    """

    dcc_name = dcc_name or application()

    version = ''
    if dcc_name == 'maya':
        import maya.cmds
        version = int(maya.cmds.about(version=True))
    elif dcc_name == 'mobu':
        import pyfbsdk
        version =  int(2000 + math.ceil(pyfbsdk.FBSystem().Version / 1000.0))
    elif dcc_name == 'unreal':
        import unreal
        version = '.'.join(unreal.SystemLibrary.get_engine_version().split('+++')[0].split('-')[0].split('.')[:-1])

    return str(version)


def get_venv_linked_packages_paths(venv_path):
    """
    Returns all linked paths located within a created Python virtual environment.

    :param str venv_path: root folder where virtual environment folder should be located
    :return:
    """

    dependency_paths = list()

    if not os.path.isdir(venv_path):
        return dependency_paths

    packages_folder = os.path.join(venv_path, 'Lib', 'site-packages')
    if not os.path.isdir(packages_folder):
        return dependency_paths

    dependency_paths = [packages_folder]

    for file_name in os.listdir(packages_folder):
        if not file_name.endswith('.egg-link'):
            continue
        egg_path = os.path.join(packages_folder, file_name)
        with open(egg_path) as egg_file:
            dependency_path = egg_file.readline().rstrip()
            if dependency_path in dependency_paths:
                continue
            if not os.path.isdir(dependency_path):
                logger.warning(
                    f'Dependency found in egg-link file points to an invalid directory: {dependency_path}. Skipping...')
                continue
            dependency_paths.append(dependency_path)

    return dependency_paths


def clean_path(path):
    """
    Cleans a path. Useful to resolve problems with slashes

    :param str path: path we want to clean.
    :return: cleaned path.
    :rtype: str
    """

    if not path:
        return ''

    # convert '~' Unix character to user's home directory
    path = os.path.expanduser(str(path))

    # Remove spaces from path and fixed bad slashes
    path = path.replace(BAD_SEPARATOR, SEPARATOR).replace(PATH_SEPARATOR, SEPARATOR).rstrip('/')

    # fix server paths
    is_server_path = path.startswith(SERVER_PREFIX)
    while SERVER_PREFIX in path:
        path = path.replace(SERVER_PREFIX, PATH_SEPARATOR)
    if is_server_path:
        path = PATH_SEPARATOR + path

    # fix web paths
    if not path.find(WEB_PREFIX) > -1:
        path = path.replace(PATH_SEPARATOR, SEPARATOR)

    # make sure drive letter is capitalized
    drive = os.path.splitdrive(path)
    if drive:
        path = path[0].upper() + path[1:]

    return path
