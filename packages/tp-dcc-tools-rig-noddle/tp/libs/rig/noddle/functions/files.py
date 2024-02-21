from __future__ import annotations

import os
import shutil

from tp.core import log, dcc
from tp.common.python import path
from tp.preferences.interfaces import noddle

logger = log.rigLogger


def create_empty_scene(new_path: str) -> bool:
	"""
	Copies empty scenes four CRIT assets directory to the given path.

	:param str new_path:
	:return: True if the create empty scene operation was successful; False otherwise.
	:rtype: bool
	:raises IOError: if source path does not exist.
	"""

	if path.is_file(new_path):
		return False

	noddle_interface = noddle.noddle_interface()
	source_path = path.join_path(noddle_interface.empty_scenes_path(), f'EmptyScene_Maya{dcc.version_name()}.ma')
	logger.debug(f'Copying file "{source_path}" to "{new_path}"')
	if not path.is_file(source_path):
		raise IOError(f'Maya empty scene path does not exist: "{source_path}"')
	try:
		shutil.copy2(source_path, new_path)
	except Exception:
		logger.exception(f'Failed to copy scene "{source_path}"')

	return True


def versioned_files(directory: str, extension: str = '', split_char: str = '.') -> dict[str, list[str]]:
	"""
	Returns a dictionary containing all versioned files ordered by versions. The expected versioned file format is:
		[FILE NAME][SPLIT CHAR][VERSION].[EXTENSION] -> MyRig.0000.ma.

	:param str directory: path where versioned files are located.
	:param str extension: optional filter extension for the versioned files to retrieve.
	:param str split_char: character used to split the file name from the version sub string.
	:return: dictionary containing file names as keys and a list of files with that version as values.
	:rtype: dict[str, list[str]]
	"""

	files_dict = dict()
	all_files = [item for item in os.listdir(directory) if path.is_file(path.join_path(directory, item))]
	if extension:
		all_files = [item for item in all_files if item.endswith(f'.{extension}')]
	for found_file in all_files:
		split_file = found_file.split(split_char)[0]
		if  split_file not in files_dict:
			files_dict[split_file] = [found_file]
		else:
			files_dict[split_file].append(found_file)

	# sort items for each key
	for key, value in files_dict.items():
		files_dict[key] = sorted(value)

	return files_dict


def latest_file(
		name: str, directory: str, extension: str = '', full_path: bool = True, split_char: str = '.') -> str | None:
	"""
	Returns the latest version of the versioned file with the given name located in the given directory.

	:param str name: name of the versioned file to retrieve.
	:param str directory: directory where the versioned file to retrieve is located.
	:param str extension: optional filter extension for the versioned files to retrieve.
	:param bool full_path: whether to return a relative path for the version file or an absolute path.
	:param str split_char: character used to split the file name from the version sub string.
	:return: latest versioned file path.
	:rtype: str or None
	"""

	files_dict = versioned_files(directory, extension=extension, split_char=split_char)
	if name not in files_dict:
		return None

	return files_dict[name][-1] if not full_path else path.join_path(directory, files_dict[name][-1])


def new_versioned_file(
		name: str, directory: str, extension: str = '', full_path: bool = True, split_char: str = '.') -> str:
	"""
	Returns the name for the new version file with given name and in the given directory.

	:param str str name: name of the versioned file whose next version we want to retrieve.
	:param str directory: directory where the versioned file is located.
	:param str extension: optional filter extension for the versioned files to retrieve.
	:param bool full_path: whether to return a relative path for the version file or an absolute path.
	:param str split_char: character used to split the file name from the version sub string.
	:return: new versioned file path.
	:rtype: str
	"""

	files_dict = versioned_files(directory, extension=extension, split_char=split_char)
	new_version = int(files_dict[name][-1].split(split_char)[-2]) + 1 if name in files_dict else 0
	new_file_name = f'{name}{split_char}{str(new_version).zfill(4)}{split_char}{extension}'

	return new_file_name if not full_path else path.join_path(directory, new_file_name)
