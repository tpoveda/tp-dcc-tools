from __future__ import annotations

import os
import glob
from typing import Tuple, List, Iterator, Dict

import maya.api.OpenMaya as OpenMaya

from tp.core import log
from tp.common.python import helpers, path, jsonio
from tp.maya.api import curves
from tp.maya.om import nodes as om_nodes

CURVE_FILE_EXTENSION = 'curve'
CURVES_ENV_VAR = 'TPDCC_CURVES_PATHS'
_PATHS_CACHE = dict()

logger = log.tpLogger


def update_cache(force: bool = False):
	"""
	Function that handles the update of cached curves.

	:param bool force: whether to force the update of the cache event if the cache is already initialized.
	"""

	if _PATHS_CACHE and not force:
		return

	for root in iterate_root_paths():
		for shape_path in glob.glob(path.join_path(root, '*.{}'.format(CURVE_FILE_EXTENSION))):
			_PATHS_CACHE[os.path.splitext(path.basename(shape_path))[0]] = {'path': shape_path}


def clear_cache():
	"""
	Clears the cache of available curves.
	"""

	_PATHS_CACHE.clear()


def iterate_root_paths() -> Iterator[str]:
	"""
	Generator function that iterates over all root locations defined by TP_RIGTOOLKIT_SHAPES_PATHS environment variable.

	:return: iterated root paths.
	:rtype: Iterator[str]:
	"""

	for root in os.environ.get(CURVES_ENV_VAR, '').split(os.pathsep):
		if not root or not path.exists(root):
			continue
		yield root


def iterate_curve_paths() -> Iterator[str]:
	"""
	Generator function that iterates over all curve paths.

	:return: iterated curve paths.
	:rypte: Iterator[str]
	"""

	update_cache()
	for curve_info in _PATHS_CACHE.values():
		yield curve_info['path']


def iterate_names() -> Iterator[str]:
	"""
	Generator function which iterates over all available curve names.

	:return: iterated curve names.
	:rtype: Iterator[str]
	..info:: curves are source from all the root location specified by the CURVES_ENV_VAR environment variable.
	"""

	update_cache()
	for curve_name in _PATHS_CACHE.keys():
		yield curve_name


def names() -> List[str]:
	"""
	List all the curve names available.

	:return:  list of curve names.
	:rtype: List[str]
	..info:: curves are source from all the root location specified by the CURVES_ENV_VAR environment variable.
	"""

	return list(iterate_names())


def find_curve_path_by_name(curve_name: str) -> str:
	"""
	Returns curve path of the curve with given name
	
	:param str curve_name: name of the curve we want to retrieve path of. 
	:return: curve path.
	:rtype: str
	"""

	update_cache()

	if _PATHS_CACHE:
		return _PATHS_CACHE.get(curve_name, dict()).get('path', '')


def load_curve(curve_name: str, folder_path: str) -> Dict:
	"""
	Loads the curve with the given name and located in the given directory.

	:param str curve_name: name of the curve to load.
	:param str folder_path: absolute directory where the curve file is located.
	:return: loaded curve data.
	:rtype: Dict
	"""

	curve_path = path.join_path(folder_path, '.'.join([curve_name, CURVE_FILE_EXTENSION]))
	return jsonio.read_file(curve_path)


def load_from_lib(curve_name: str) -> Dict:
	"""
	Loads the data from the given curve name in library.

	:param str curve_name: name of the curve to load data of.
	:return: curve data.
	:rtype: Dict
	:raises MissingCurveFromLibrary: if the given curve name does not exist in the library of curves.
	"""

	update_cache()

	curve_data = _PATHS_CACHE.get(curve_name)
	if not curve_data:
		raise MissingCurveFromLibrary('Curve name {} does not exist in the library'.format(curve_name))

	data = curve_data.get('data')
	if not data:
		data = jsonio.read_file(curve_data['path'])
		curve_data['data'] = data

	return data


def load_and_create_from_lib(
		curve_name: str, parent: OpenMaya.MObject | None = None) -> tuple[OpenMaya.MObject, list[OpenMaya.MObject]]:
	"""
	Loads and creates the curve from curves library. If parent is given, shape node will be parented under it.

	:param str curve_name: curve library name to load and create.
	:param OpenMaya.MObject parent: optional curve parent.
	:return: tuple with the MObject of the parent and a list representing the MObjects of the created shapes.
	:rtype: tuple(OpenMaya.MObject, list(OpenMaya.MObject))
	"""

	new_data = load_from_lib(curve_name)
	return curves.create_curve_shape(new_data, parent=parent)


def load_and_create_from_path(
		curve_name: str, folder_path: str,
		parent: OpenMaya.MObject | None = None) -> Tuple[OpenMaya.MObject | None, List[OpenMaya.MObject]]:
	"""
	Loads and creates the NURBS curve from the file located in the given path.

	:param str curve_name: name of the curve to load and create.
	:param str folder_path: absolute directory where the curve file is located.
	:param OpenMaya.MObject or None parent: optional parent for the NURBS curve to parent under.
	:return: tuple containing the MObject of the parent and a list of MObjects representing the created shapes.
	:rtype: Tuple[OpenMaya.MObject or NOne, List[OpenMaya.MObject]]
	"""

	curve_data = load_curve(curve_name, folder_path)
	return curves.create_curve_shape(curve_data, parent=parent)


def save_to_directory(
		node: OpenMaya.MObject, directory: str, name: str | None, override: bool = True,
		save_matrix: bool = False, normalize: bool = True) -> Tuple[Dict, str]:
	"""
	Saves the given transform node into the given directory.

	:param OpenMaya.MObject node: Maya object representing the transform node to save curves of.
	:param str directory: absolute path where curve file will be saved.
	:param str or None name: name of the file to create. If not given, the name of the node will be used.
	:param bool override: whether to force override the library shape if it already exists.
	:param bool save_matrix: whether to save matrix information.
	:param bool normalize: whether to normalize curve data, so it fits in first Maya grid quadrant.
	:return: tuple containing the save curve data and the save path.
	:rtype: Tuple[Dict, str]
	:raises ValueError: if we try to save a curve that already exists and override argument is False
	"""

	name = name or om_nodes.name(node, partial_name=True, include_namespace=False)
	name = name if name.endswith(f'.{CURVE_FILE_EXTENSION}') else '.'.join([name, CURVE_FILE_EXTENSION])
	if not override and name in names():
		raise ValueError(f'Curve with name "{name}" already exists in the curves library!')

	data = curves.serialize_transform_curve(node, normalize=normalize)
	if not save_matrix:
		for curves_shape in data:
			data[curves_shape].pop('matrix', None)

	save_path = path.join_path(directory, name)

	jsonio.write_to_file(data, save_path)
	_PATHS_CACHE[os.path.splitext(name)[0]] = {'path': path, 'data': data}

	return data, save_path


def save_to_lib(
		node: OpenMaya.MObject | None = None, name: str | None = None, override: bool = True,
		save_matrix: bool = False, normalize: bool = True) -> Tuple[Dict, str]:
	"""
	Saves the given transform node shapes into the curve library, using the first library directory defined within
	CURVES_ENV_VAR environment variable.

	:param OpenMaya.MObject node: Maya object representing the transform node to save curves of.
	:param str name: name of the file to create. If not given, the name of the node will be used.
	:param bool override: whether to force override the library shape if it already exists.
	:param bool save_matrix: whether to save matrix information.
	:param bool normalize: whether to normalize curve data, so it fits in first Maya grid quadrant.
	:return: tuple containing the save curve data and the save path.
	:rtype: Tuple[Dict, str]
	:raises ValueError: if no node to save curves from is given.
	"""

	node = node or helpers.first_in_list(om_nodes.selected_nodes(OpenMaya.MFn.kTransform))
	if not node:
		raise ValueError('No node to save curves')
	directory = os.environ.get(CURVES_ENV_VAR, '').split(os.pathsep)[0]
	return save_to_directory(node, directory, name, override=override, save_matrix=save_matrix, normalize=normalize)


def rename_curve(curve_name: str, new_name: str):
	"""
	Renames a shape from the library, using the first library directory defined within CURVES_ENV_VAR environment
	variable.

	:param str curve_name: name of the curve to rename.
	:param str new_name: new curve name.
	:return: new curve path.
	:rtype: str
	"""

	curve_path = find_curve_path_by_name(curve_name)
	if not path.exists(curve_path):
		logger.warning(f'Curve file not found: "{curve_path}"')
		return ''

	new_path = path.join_path(path.dirname(curve_path), '.'.join([new_name, CURVE_FILE_EXTENSION]))
	if path.is_dir(new_path):
		logger.warning(f'Cannot rename curve, because filename already exists: "{new_path}"')
		return ''

	os.rename(curve_path, new_path)
	old_data = _PATHS_CACHE.get(curve_name)
	old_data['path'] = new_path
	_PATHS_CACHE[new_name] = old_data
	del _PATHS_CACHE[curve_name]

	return new_path


def delete_curve(curve_name: str) -> bool:
	"""
	Deletes curve with given name from library, using the first library directory defined within CURVES_ENV_VAR
	environment variable.

	:param str curve_name: name of the curve to delete.
	:return: True if the delete curve operation was successful; False otherwise.
	:rtype: bool
	"""

	curve_path = find_curve_path_by_name(curve_name)
	if not curve_path:
		logger.warning(f'Curve file not found: "{curve_path}"')
		return False

	os.remove(curve_path)
	if curve_name in _PATHS_CACHE:
		del _PATHS_CACHE[curve_name]

	return True


class MissingCurveFromLibrary(Exception):

	pass
