from Qt.QtWidgets import QFileDialog

import maya.cmds as cmds

from tp.core import log
from tp.common.python import path

from tp.libs.rig.noddle.core import asset

logger = log.rigLogger


def browse_model():

    current_asset = asset.Asset.get()
    if not current_asset:
        logger.warning('No active asset set!')
        return ''

    model_path = QFileDialog.getOpenFileName(
        None,
        'Select model file',
        current_asset.path,
        'Maya (*.ma *mb);;Maya ASCII (*.ma);;Maya Binary(*.mb);;All Files (*.*)',
        'Maya (*.ma *mb)')[0]
    if not model_path:
        return ''

    return model_path


def import_model(browse_if_not_found: bool = False) -> str:
    """
    Imports model of the current active asset.

    :param bool browse_if_not_found: whether to show a browse window if not model file is defined within current
        active asset metadata file.
    :return: imported model absolute path.
    :rtype: str
    """

    current_asset = asset.Asset.get()
    if not current_asset:
        logger.warning('No active asset set!')
        return ''

    model_path = current_asset.model_path
    if not path.is_file(model_path) and not browse_if_not_found:
        logger.warning(f'Invalid model file path: "{model_path}"')
        return ''

    if not path.is_file(model_path):
        model_path = browse_model()
        current_asset.set_data('model', model_path)
    if not path.is_file(model_path):
        logger.warning(f'Invalid model file path: "{model_path}"')
        return ''

    try:
        result = cmds.file(
            model_path, i=True, force=True, ignoreVersion=True, preserveReferences=True, returnNewNodes=True)
        cmds.viewFit(result, animate=True)
    except RuntimeError as err:
        logger.exception(f'Failed to load model file: "{model_path}"')
        raise err

    logger.info(f'Imported model: "{model_path}"')

    return model_path


def reference_model(browse_if_not_found: bool = False) -> str:
    """
    References model of the current active asset.

    :param bool browse_if_not_found: whether to show a browse window if not model file is defined within current
        active asset metadata file.
    :return: references model absolute path.
    :rtype: str
    """

    current_asset = asset.Asset.get()
    if not current_asset:
        logger.warning('No active asset set!')
        return ''

    model_path = current_asset.model_path
    if not path.is_file(model_path) and not browse_if_not_found:
        logger.warning(f'Invalid model file path: "{model_path}"')
        return ''

    if not path.is_file(model_path):
        model_path = browse_model()
        current_asset.set_data('model', model_path)
    if not path.is_file(model_path):
        logger.warning(f'Invalid model file path: "{model_path}"')
        return ''

    try:
        result = cmds.file(
            model_path, r=True, force=True, ignoreVersion=True, preserveReferences=True, returnNewNodes=True)
        cmds.viewFit(result, animate=True)
    except RuntimeError as err:
        logger.exception(f'Failed to reference model file: "{model_path}"')
        raise err

    logger.info(f'Referenced model: "{model_path}"')

    return model_path


def import_skeleton() -> str:
    """
    Imports skeleton of the current active asset.

    :return: imported skeleton absolute path.
    :rtype: str
    """

    current_asset = asset.Asset.get()
    if not current_asset:
        logger.warning('No active asset set!')
        return ''

    latest_skeleton_path = current_asset.latest_skeleton_path
    try:
        result = cmds.file(
            latest_skeleton_path, i=True, force=True, ignoreVersion=True, preserveReferences=True, loadReferenceDepth='none',
            returnNewNodes=True, defaultNamespace=True)
        cmds.viewFit(result, animate=True)
    except RuntimeError as err:
        logger.exception(f'Failed to load skeleton file: "{latest_skeleton_path}"')
        raise err

    logger.info(f'Imported skeleton: "{latest_skeleton_path}"')

    return latest_skeleton_path
