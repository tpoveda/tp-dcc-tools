#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tp-dcc-bootstrap
"""

import os
import sys
import inspect
from distutils.util import strtobool

from tp.bootstrap import log
from tp.bootstrap.utils import env

logger = log.bootstrapLogger


def root_path():
    """
    Returns the root directory.

    :return tp-dcc tools repository root path.
    :rtype: str
    """

    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def register_vendors():
    """
    Function that register vendor folder within sys.path.
    """

    vendor_path = os.path.join(os.path.dirname(os.path.dirname(root_path())), 'vendor')
    if os.path.isdir(vendor_path) and vendor_path not in sys.path:
        sys.path.append(vendor_path)


def init(**kwargs):
    """
    Initializes tp-dcc packages manager.

    :param dict kwargs: keyword arguments.
    :return: tp-dcc Package Manager instance.
    :rtype: tpDccPackagesManager
    :raises ValueError: if TPDCC_TOOLS_ROOT environment variable is not defined.
    """

    # Make sure tp-dcc-tools Python paths have been set up
    root_path = os.path.abspath(os.environ.get('TPDCC_TOOLS_ROOT', ''))
    root_path = root_path or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # bootstrap_path = os.path.abspath(os.path.join(root_path, 'packages', 'tp-dcc-bootstrap'))
    # if not bootstrap_path:
    #     raise ValueError('tp-dcc-tools framework is missing "TPDCC_TOOLS_ROOT" environment variable.')
    # elif not os.path.isdir(bootstrap_path):
    #     raise ValueError(f'Failed to find valid tp-dcc-tools bootstrap folder. Found "{bootstrap_path}"')
    # if bootstrap_path not in sys.path:
    #     sys.path.append(bootstrap_path)

    packages_folder_path = kwargs.get('packages_folder_path', '')
    package_version_file = kwargs.get('package_version_file', '')
    custom_sys_paths = kwargs.get('custom_sys_paths', list())
    dev = bool(strtobool(os.getenv('TPDCC_ENV_DEV', 'False')))
    deps_path = kwargs.get('dependencies_path', None) or os.getenv('TPDCC_DEPS_ROOT', None)

    if not package_version_file:
        if env.application() == 'standalone':
            package_version_file = 'package_version_standalone.config'
        elif env.application() == 'maya':
            package_version_file = 'package_version_maya.config'
        elif env.application() == '3dsmax':
            package_version_file = 'package_version_3dsmax.config'
        elif env.application() == 'mobu':
            package_version_file = 'package_version_mobu.config'
        elif env.application() == 'houdini':
            package_version_file = 'package_version_houdini.config'
        elif env.application() == 'blender':
            package_version_file = 'package_version_blender.config'
        elif env.application() == 'unreal':
            package_version_file = 'package_version_unreal.config'

    logger.debug('Bootstrap init paths:')
    logger.debug(f'\tPackages Root Path: {root_path}')
    logger.debug(f'\tDependencies Root Path: {root_path}')
    logger.debug(f'\tPackages Folder Path: {packages_folder_path}')
    logger.debug(f'\tPackages Version File Path: {package_version_file}')
    logger.debug(f'\tCustom Sys Paths: {custom_sys_paths}')

    # Register dependency paths
    register_vendors()

    if deps_path and os.path.isdir(deps_path):
        py_folder = 'py2' if env.is_python2() else 'py3'
        py_deps_folders = [
            os.path.join(deps_path, env.application(), py_folder),
            os.path.join(deps_path, env.application()),
            os.path.join(deps_path, py_folder),
        ]
        for dep_folder in py_deps_folders:
            if not os.path.isdir(dep_folder) or dep_folder in sys.path:
                continue
            logger.debug(f'Dependencies Path {dep_folder} registered into sys.path.successfully!')
            sys.path.insert(0, dep_folder)

        if deps_path not in sys.path:
            sys.path.append(deps_path)

    # import here to make sure that bootstrapping vendor paths are already included within sys.path
    from tp.bootstrap import consts, api

    # logger.debug('Registering packages paths into sys.path ...')
    # packages_paths = list()
    # # for now, we do not use virtual environments
    # # venv_folder = os.path.join(root_path, f'venv{sys.version_info[0]}')
    # # logger.debug(f'Looking packages within virtual environment folder: "{venv_folder}"')
    # # if os.path.isdir(venv_folder):
    # #     packages_paths = env.get_venv_linked_packages_paths(venv_folder)
    # #     logger.debug(f'Found packages ({len(packages_paths)}) within virtual environment folder: {packages_paths}')
    # packages_paths.extend(custom_sys_paths)
    # logger.debug(f'Registering follow package paths into sys.path: {packages_paths}')
    # for package_path in packages_paths:
    # 	if package_path and os.path.isdir(package_path) and package_path not in sys.path:
    # 		sys.path.append(package_path)
    # 		logger.debug(f'Package Path {package_path} registered into sys.path.successfully!')

    # create package manager and resolve (initialize) packages
    package_manager = api.current_package_manager()
    if package_manager is None:

        # Setup environment variables related with tp-dcc-tools framework
        if packages_folder_path and os.path.isdir(packages_folder_path):
            os.environ[consts.PACKAGES_FOLDER_PATH] = packages_folder_path
        if package_version_file:
            os.environ[consts.TPDCC_PACKAGE_VERSION_FILE] = package_version_file
        logger.debug('Setting up environment variables related with bootstrapping process ...')
        logger.debug(f'\t{consts.PACKAGES_FOLDER_PATH}: {os.environ.get(consts.PACKAGES_FOLDER_PATH, "")}')
        logger.debug(f'\t{consts.TPDCC_PACKAGE_VERSION_FILE}: {os.environ.get(consts.TPDCC_PACKAGE_VERSION_FILE, "")}')

        # Resolve package manager
        logger.debug('Creating tp-dcc framework environment ...')
        logger.debug(f'\tRoot Path: {root_path}')
        logger.debug(f'\tDev Mode: {dev}')
        package_manager = api.package_manager_from_path(root_path, dev=dev)
        logger.debug(f'Created tp-dcc environment instance: {package_manager}')
        logger.debug('Resolving tp-dcc environment:')
        logger.debug(f'\tResolver: {package_manager.resolver}')
        logger.debug(f'\tEnvironment configuration file: {package_manager.resolver.environment_path()}')
        logger.info('\n\n' + '=' * 80)
        logger.info('tp-dcc Framework')
        logger.info('\n' + '=' * 80 + '\n')
        package_manager.resolver.resolve_from_path(package_manager.resolver.environment_path())

    return package_manager


def shutdown():

    # import here to make sure that bootstrapping vendor paths are already included within sys.path
    from tp.bootstrap import api

    current_env = api.current_package_manager()
    if not current_env:
        logger.debug('No tp-dcc framework environment found to set shutdown.')
        return False

    logger.info('\n\n' + '=' * 80)
    logger.info('tp-dcc Framework')
    logger.info('\n' + '=' * 80 + '\n')

    logger.debug(f'Shutting down tp-dcc framework environment: {current_env}')
    logger.debug(f'\tRoot Path: {current_env.root_path}')
    logger.debug(f'\tDev: {current_env.is_dev()}')

    current_env.shutdown()
    api.set_current_package_manager(None)

    log.LogsManager().clear_logs()


register_vendors()
