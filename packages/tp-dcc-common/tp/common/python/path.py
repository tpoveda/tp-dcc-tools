#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility methods related to string paths
"""

from __future__ import annotations

import os
import sys
import uuid
import stat
import time
import glob
import string
import shutil
import tempfile
import traceback
import contextlib
from typing import Tuple, List, Dict, Iterator

from tp.core import log
from tp.common.python import name, folder, osplatform, helpers, win32, strings

SEPARATOR = '/'
BAD_SEPARATOR = '\\'
PATH_SEPARATOR = '//'
SERVER_PREFIX = '\\'
RELATIVE_PATH_PREFIX = './'
BAD_RELATIVE_PATH_PREFIX = '../'
WEB_PREFIX = 'https://'

# We use one separator depending if we are working on Windows (nt) or other operative system
NATIVE_SEPARATOR = (SEPARATOR, BAD_SEPARATOR)[os.name == 'nt']

logger = log.tpLogger


@contextlib.contextmanager
def cd(new_dir: dir, cleanup: bool = lambda: True):
    prev_dir = os.getcwd()
    os.chdir(os.path.expanduser(new_dir))
    try:
        yield
    finally:
        os.chdir(prev_dir)
        cleanup()


@contextlib.contextmanager
def temp_dir():
    dir_path = tempfile.mkdtemp()

    def cleanup():
        shutil.rmtree(dir_path)
    with cd(dir_path, cleanup):
        yield dir_path


def normalize_path(path: str) -> str:
    """
    Normalizes a path to make sure that path only contains forward slashes.

    :param str path: path to normalize.
    :return: normalized path.
    :rtype: str
    """

    return path.replace(BAD_SEPARATOR, SEPARATOR).replace(PATH_SEPARATOR, SEPARATOR).rstrip('/')


def normalize_paths(paths: List[str]) -> List[str]:
    """
    Normalize all the given paths into a consistent format.

    :param List[str] paths: paths to normalize.
    :return: list of normalized paths.
    :rtype: List[str]
    """

    return [normalize_path(path) for path in paths]


def clean_path(path: str) -> str:
    """
    Cleans a path. Useful to resolve problems with slashes.

    :param str path: path to clean.
    :return: cleaned path.
    :rtype: str
    """

    if not path:
        return ''

    # We convert '~' Unix character to user's home directory
    path = os.path.expanduser(str(path))

    # Remove spaces from path and fixed bad slashes
    path = normalize_path(path.strip())

    # Fix server paths
    is_server_path = path.startswith(SERVER_PREFIX)
    while SERVER_PREFIX in path:
        path = path.replace(SERVER_PREFIX, PATH_SEPARATOR)
    if is_server_path:
        path = PATH_SEPARATOR + path

    # Fix web paths
    if not path.find(WEB_PREFIX) > -1:
        path = path.replace(PATH_SEPARATOR, SEPARATOR)

    return path


def touch_path(path: str, remove: bool = False):
    """
    Makes ssure given file or directory is valid to use. This will mark files as writable, and validate
    the directory exists to write to if the file does not exist.

    :param str path: absolute path to given file or directory.
    :param bool remove: whether file should be removed if it exists.
    """

    directory_path = os.path.dirname(path)
    if os.path.exists(directory_path):
        if os.path.isfile(path):
            os.chmod(path, stat.S_IWRITE)
            if remove:
                os.remove(path)
                time.sleep(.002)
    else:
        os.makedirs(directory_path)


def real_path(path: str) -> str:
    """
    Returns the canonical path of the given path and resolves any symbolic link.

    :param str path: returns the real path of the given one.
    :return: canonic path with resolved symbolic links.
    :rtype: str
    """

    return normalize_path(os.path.expanduser(os.path.realpath(path)))


def join_path(*args: str) -> str | None:
    """
    Appends given paths together.

    :param str args: tuple with paths to join.
    :return: joined path.
    :rtype: str or None
    """

    if not args:
        return None

    if len(args) == 1:
        return args[0]

    paths_to_join = [clean_path(str(path)) for path in args]
    joined_path = clean_path(os.sep.join(paths_to_join))

    return joined_path


def set_windows_slashes(directory: str) -> str:
    """
    Set all the slashes in a name, so they use Windows slashes (\).

    :param str directory: directory path to set Windows slashes to.
    :return: path with Windows slashes.
    :rtype: str
    """

    return directory.replace('/', '\\').replace('//', '\\')


def split_path(path: str, remove_extension_dot: bool = False) -> Tuple[str, str, str]:
    """
    Split the given path into directory, basename and extension.

    :param str path: path to split.
    :param bool remove_extension_dot: whether to remove the start dot from the extension.
    :return: tuple containing the directory path, file path and extension.
    :rtype: Tuple[str, str, str]
    """

    path = normalize_path(path)
    filename, extension = os.path.splitext(path)
    if remove_extension_dot:
        extension = extension[1:]

    return os.path.dirname(filename), os.path.basename(filename), extension


def get_relative_path(path, start):
    """
    Gets a relative path from a start path
    :param path: str, path to get relative path
    :param start: str, Start path to calculate the relative path from
    """

    # if os.path.splitext(start)[-1]:
    #     start = clean_path(os.path.dirname(start))
    # rel_path = clean_path(os.path.relpath(path, start))
    #
    # # TODO: Check if this is correct
    # if not rel_path.startswith('../'):
    #     rel_path = './' + rel_path
    #
    # return rel_path

    rpath = start

    for i in range(0, 3):

        rpath = os.path.dirname(rpath)
        token = os.path.relpath(rpath, start)

        rpath = normalize_path(rpath)
        token = normalize_path(token)

        if rpath.endswith("/"):
            rpath = rpath[:-1]

        path = path.replace(rpath, token)

    return path


def relative_to(root, b):
    """
    Returns the relative path without '..'

    :param str root: main root path
    :param str b: child path which contains the root.
    :return: relative path.
    :rtype: str or None
    """

    def _iter_parents(path):
        """
        Internal generator function that iterates each parent folder.

        :param str path: path to iterate.
        :return: generator(str)
        """

        drive, p = os.path.splitdrive(path)
        parent = os.path.dirname(p)
        base_name = os.path.basename(p)
        fragments = [os.path.basename(parent), base_name]
        while parent not in (u"/", "", "\\"):
            yield join_path(drive, parent), os.path.sep.join(fragments).replace("\\", "/")
            parent = dirname(parent)
            fragments.insert(0, basename(parent))

    if dirname(b) == root:
        return basename(b)

    previous = ''
    for absolute_parent, relative in _iter_parents(b):
        if absolute_parent == root:
            return previous
        previous = relative

    return None


def get_absolute_path(path, start):
    """
    Gets an absolute path from a start path
    :param path: str, path to get absolute path
    :param start: str, Start path to calculate the absolute path from
    """

    path = path.replace('\\', '/')
    if not os.path.isdir(start):
        start = os.path.dirname(start).replace('\\', '/')
    else:
        start = start.replace('\\', '/')

    return os.path.abspath(os.path.join(start, path)).replace('\\', '/')


def get_absolute_file_paths(root_directory):
    """
    Returns a generator with all absolute paths on a folder (and sub folders)
    :param root_directory: str, directory to start looking
    """

    for root, _, files in os.walk(root_directory):
        for f in files:
            yield os.path.abspath(os.path.join(root, f))


def get_immediate_subdirectories(root_directory):
    """
    Returns a list with intermediate subdirectories of root directory
    :param root_directory: str, directory to start looking
    """

    return [
        os.path.join(
            root_directory, name) for name in os.listdir(root_directory) if os.path.isdir(
            os.path.join(root_directory, name))
    ]


def get_extension(path):
    """
    Returns the exctension of a file path (wihtout the period)
    :param path: str, valid path to a file
    :return: str
    """

    return os.path.splitext(path)[1][1:]


def shorten_path(path: str, length: int = 50) -> str:
    """
    Truncates the inner path first depending on length.

    :param str path: path to truncate.
    :param int length: path lenght.
    :return: truncated path.
    :rtype: str
    """

    _split_path = os.path.normpath(path).split(os.sep)
    ellipsis_len = 3
    result_len = len(_split_path[0]) + 1 + len(_split_path[-1]) + 1
    mid_str = os.sep.join(_split_path[1:-1])
    if len(mid_str) + result_len < length:
        return path

    result_len += ellipsis_len
    result = _split_path[0] + os.sep + '...' + mid_str[result_len + len(mid_str) - length:] + os.sep + _split_path[-1]

    return os.path.normpath(result)


def exists(directory):
    """
    Returns true if the given path exists
    :param directory: str
    :return: bool
    """

    if not directory:
        return False

    try:
        stat = os.stat(directory)
        if stat:
            return True
    except Exception:
        return False

    return os.path.exists(directory)


def has_extension(path, file_extension):
    """
    Checks if a given file path has a specific given file extension
    :param path: str, file path
    :param file_extension: str, valid file extension
    :return: bool, True if the extension of the given path matches the given extension, False otherwise
    """

    return True if get_extension(path=path) == file_extension else False


def files(
        root: str, file_extension: str | None = None, recursive: bool = False, full_path: bool = False,
        stdout: bool = False) -> List[str] | None:
    """
    Returns all files from a given directory.

    :param str root: path to get directories from.
    :param str file_extension: file extension of files to search for.
    :param bool recursive: True if the function will search deeper than one level of files.
    :param str full_path: the output of the path will be the full path if True.
    :param stdout: print results in Python output if True.
    :return: list of files.
    :rtype: List[str] or None
    """

    def _out(data):
        for i in data:
            print(i)
            print('Found {0} files'.format(len(data)))

    if len(root):
        root = clean_path(root)
        found_directories = [d for d in os.listdir(root) if is_dir(root, d)]
        if file_extension:
            if full_path:
                found_files = [clean_path(os.path.abspath(os.path.join(root, f))) for
                         f in os.listdir(root) if is_file(root, f) and has_extension(f, file_extension)]
            else:
                found_files = [f for f in os.listdir(root) if is_file(root, f) and has_extension(f, file_extension)]
        else:
            if full_path:
                found_files = [
                    clean_path(os.path.abspath(os.path.join(root, f))) for f in os.listdir(root) if is_file(root, f)]
            else:
                found_files = [f for f in os.listdir(root) if is_file(root, f)]

        if len(found_directories) and recursive:
            more_files = [files(os.path.join(root, d), file_extension, recursive, full_path) for d in found_directories]
            if len(more_files):
                for chunk in more_files:
                    found_files.extend(chunk)

        output = [clean_path(p) for p in found_files]
        if stdout:
            _out(output)

        return output

    return None


def file_name_no_extension(file_path: str) -> str:
    """
    Returns file name without extension.

    :param str file_path: file path with extension.
    :return: file name without extension.
    :rtype: str
    """

    return os.path.splitext(os.path.basename(file_path))[0]


def files_in_directory(directory: str, include_extension: bool = True) -> List[str]:
    """
    Returns all files in the given directory.

    :param str directory: director to search files from.
    :param bool include_extension: whether to include extensions.
    :return: list of file paths.
    :rtype: List[str]
    """

    found_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    return found_files if include_extension else [file_name_no_extension(f) for f in found_files]


def files_by_extension(directory: str, extensions: List[str], sort: bool = True):
    """
    Returns lal the files include in the given directory that matches the given extensions list.

    :param str directory: directory to search and return file names from.
    :param List[str] extensions: list of extensions to search without the fullstop ('json', 'yaml', 'fbx', ...).
    :param bool sort: whether sort files by name.
    :return: list of files.
    :rtype: List[str]
    """

    found_files = []
    if not os.path.isdir(directory):
        return found_files

    for extension in extensions:
        for file_path in glob.glob(os.path.join(directory, f'*.{extension}')):
            found_files.append(os.path.basename(file_path))

    if sort:
        found_files.sort()

    return found_files


def directories(directory: str, absolute: bool = False, sort: bool = True) -> List[str]:
    """
    Reutns all directors in the given directory.

    :param str directory: directory to look into.
    :param bool absolute: whether to return the full path or just the directory names.
    :param bool sort: whether to sort directories by name.
    :return: list of directory names or paths.
    :rtype: List[str]
    """

    result = []
    for directory_name in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, directory_name)):
            result.append(directory_name if not absolute else os.path.join(directory, directory_name))

    if sort:
        result.sort()

    return result


def basename(directory, with_extension=True):
    """
    Get the last part of a directory name
    For example, C:/test/rig.py will return rig.py if with_extension is True of rig if with_extension is False
    :param directory: str
    :param with_extension: bool, Whether to return the file name with extension or not
    :return: variant, str || bool (if fails)
    """

    from tp.common.python import fileio

    try:
        base_name = os.path.basename(directory)
        if not with_extension:
            base_name = fileio.remove_extension(base_name)

        return base_name
    except Exception:
        return False


def dirname(directory):
    """
    Given a directory path, this will return the path above the last child path in the path
    For example, C:/test/rig.py will return C:/test
    :param directory: str,
    :return: variant, str || bool (if fails)
    """

    try:
        return os.path.dirname(directory)
    except Exception:
        return False


def unique_path_name(directory, padding=0):
    """
    Add padding to the given path name if it is not unique
    :param directory: str, diretory name including path

    :param padding: int, where the padding should start



    :return: str, new unique directory with path
    """

    unique_path = FindUniquePath(directory)
    unique_path.set_padding(padding)

    return unique_path.get()


def unique_file_name(file_path: str, count_limit: str = 500) -> str:
    """
    Returns a unique file name if a name already exists by adding a number to the end of the file.

    :param str file_path: full path to a file name with an extension.
    :param int count_limit: limit number of loops to try finding a unique file name.
    :return: unique file path.
    :rtype: str
    """

    count = 0

    while os.path.exists(file_path):
        directory_path = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        file_name_no_ext = os.path.splitext(file_name)[0]
        file_extension = os.path.splitext(file_name)[-1]
        name_numberless, number, padding = strings.trailing_number()


def get_common_path(path1, path2):
    """
    Returns path that is common in both given paths
    :param path1: str
    :param path2: str
    :return: str, common path shared by both given paths
    """

    path1 = clean_path(path1)
    path2 = clean_path(path2)

    split_path1 = path1.split('/')
    split_path2 = path2.split('/')

    first_list = split_path1
    second_list = split_path2

    found = list()
    for i in range(len(first_list)):
        if len(second_list) <= i:
            break
        if first_list[i] == second_list[i]:
            found.append(first_list[i])
        if first_list[i] != second_list[i]:
            break

    found = string.join(found, '/')

    return found


def remove_common_path(path1, path2):
    """
    Removes path that is common in both given paths
    :param path1: str
    :param path2: str
    :return: str, path without the path shared by both given paths
    """

    path1 = clean_path(path1)
    path2 = clean_path(path2)

    split_path1 = path1.split('/')
    split_path2 = path2.split('/')

    skip = True
    new_path = list()

    for i in range(len(split_path2)):
        if skip:
            if len(split_path1) > i:
                if split_path1[i] != split_path2[i]:
                    skip = False
            if (len(split_path1) - 1) < i:
                skip = False
        if not skip:
            new_path.append(split_path2[i])

    new_path = '/'.join(new_path)

    return new_path


def remove_common_path_at_beginning(path1, path2):
    """
    Removes path that is similar on both given paths at the beginning of both of them
    :param path1: str
    :param path2: str
    :return: str
    """

    path2 = path2 or ''

    value = path2.find(path1)
    sub_part = None

    if value > -1 and value == 0:
        sub_part = path2[len(path1):]
    if sub_part:
        if sub_part.startswith('/'):
            sub_part = sub_part[1:]

    return sub_part


def is_dir(directory, path=None):
    """
    Checks if the given directory is a directory or not
    :param directory: str
    :param path: str
    :return: bool
    """

    if not directory:
        return False

    if path is not None:
        directory = join_path(directory, path)

    try:
        mode = os.stat(directory)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            return True
    except Exception:
        return False

    return False


def is_file(file_path, path=None):
    """
    Checks if the given path is an existing file
    :param file_path: str
    :return: bool
    """

    if not file_path:
        return False

    if path is not None:
        file_path = join_path(file_path, path)

    try:
        mode = os.stat(file_path)[stat.ST_MODE]
        if stat.S_ISREG(mode):
            return True
    except Exception:
        return False

    return False


def move(path1, path2):
    """
    Move the folder or file pointed by path1 under the directory path2
    :param path1: str, file or folder including path
    :param path2: str, path where path1 should move to
    :return: bool, Whether the move operation was successful
    """

    try:
        shutil.move(path1, path2)
    except Exception:
        logger.warning('Failed to move {0} to {1}'.format(path1, path2))
        return False

    return True


def rename(directory, name, make_unique=False):
    """
    Renames given with a new name
    :param directory: str, full path to the diretory we want to rename
    :param name: str, new name of the folder we want to rename
    :param make_unique: bool, Whether to add a number to the folder name to make it unique
    :return: str, path of the renamed folder
    """

    base_name = basename(directory=directory)
    if base_name == name:
        return

    parent_path = dirname(directory=directory)
    rename_path = join_path(parent_path, name)

    if make_unique:
        rename_path = unique_path_name(directory=rename_path)

    if is_dir(rename_path) or is_file(rename_path):
        return False

    try:
        os.chmod(directory, 0o777)
        message = 'rename: {0} >> {1}'.format(directory, rename_path)
        logger.info(message)
        os.rename(directory, rename_path)
    except Exception:
        logger.error('{}'.format(traceback.format_exc()))
        return False

    return rename_path


def get_user_data_dir(appname=None, appauthor=None, version=None, roaming=False):
    r"""
    Based on appdirs user_data_dir function

    Returns the full path to the user-specific data directory
    :param appname: str or None, name of the application. If None, the system directory is returned
    :param appauthor: str, name of the author or distributing body for this application. Typically is the owning
        company name. Only used in Windows.
    :param version: str, optional version path element to append to the path. You might want to use this if you
        want multiple versions of you app to be able to run independently. If used, this would typically be
        "<major>.<minor>". Only is applied if app_name is present.
    :param roaming: bool, True to use the Windows roaming appdata directory. That means that for users on a a
        Windows network setup for roaming profiles, this user data will be synced on login. See
        <http://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx> for a discussion of issues.
    :return: str

    Typical user data directories are:
        Mac OS X:               ~/Library/Application Support/<AppName>
        Unix:                   ~/.local/share/<AppName>    # or in $XDG_DATA_HOME, if defined
        Win XP (not roaming):   C:\Documents and Settings\<username>\Application Data\<AppAuthor>\<AppName>
        Win XP (roaming):       C:\Documents and Settings\<user>\Local Settings\Application Data\<AppAuthor>\<AppName>
        Win 7  (not roaming):   C:\Users\<username>\AppData\Local\<AppAuthor>\<AppName>
        Win 7  (roaming):       C:\Users\<username>\AppData\Roaming\<AppAuthor>\<AppName>

    For Unix, we follow the XDG spec and support $XDG_DATA_HOME.
    That means, by default "~/.local/share/<AppName>".
    """

    system = osplatform.get_sys_platform()

    if system == "win32":
        if appauthor is None:
            appauthor = appname
        const = roaming and "CSIDL_APPDATA" or "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(win32.get_win_folder(const))
        if appname:
            if appauthor is not False:
                path = os.path.join(path, appauthor, appname)
            else:
                path = os.path.join(path, appname)
    elif system == 'darwin':
        path = os.path.expanduser('~/Library/Application Support/')
        if appname:
            path = os.path.join(path, appname)
    else:
        path = os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share"))
        if appname:
            path = os.path.join(path, appname)
    if appname and version:
        path = os.path.join(path, version)

    return path


def iterate_parent_path(child_path: str) -> Iterator[str]:
    """
    Generator function that walks up directory structure starting at the child path.

    :param str child_path: child path directory.
    :return: list of parent path directories.
    :rtype: Iterator[str]
    """

    current_path = child_path
    while os.path.split(current_path)[1]:
        current_path = os.path.split(current_path)[0]
        yield current_path


def find_parent_directory(child_path: str, parent_folder_name: str) -> str | None:
    """
    Recursively walks up the directory structure and returns the first instance of the given parent folder.

    :param str child_path: child path directory.
    :param str parent_folder_name: folder name to find.
    :return: first instance of the folder once found.
    :rtype: str or None
    """

    found_path = None
    for parent_path in iterate_parent_path(child_path):
        if os.path.split(parent_path)[-1] == parent_folder_name:
            found_path = parent_path
            break

    return found_path


def find_first_in_paths(filename: str, paths: List[str]) -> str:
    """
    Given a file name or path fragment, returns the first occurrence of a file with that name in the given
    list of paths.

    :param str filename: file name to find.
    :param List[str] paths: list of paths to search in.
    :return: found first occurrence.
    :rtype: str
    :raises Exception: if no path was found.
    """

    for found_path in paths:
        loc = os.path.join(found_path, filename)
        if os.path.exists(loc):
            return loc

    raise Exception(f'File "{filename}" cannot be found in the given paths!')


def find_first_in_env(filename: str, env_var_name: str):
    """
    Given a file name or path fragment, returns the full path to the first matching file found in the given environment
    variable.

    :param str filename: file name to find.
    :param str env_var_name: environment variable name.
    :return: found first occurrence.
    :rtype: str
    """

    return find_first_in_paths(filename, os.environ[env_var_name].split(os.pathsep))


def find_first_in_path_env(filename: str):
    """
    Given a file name or path fragment, returns the full path to the first matching file found in the PATH environment
    variable.

    :param str filename: file name to find.
    :return: found first occurrence.
    """

    return find_first_in_env(filename, 'PATH')


def find_first_in_sys_path(filename: str):
    """
    Given a file name or path fragment, returns the full path to the first matching file found in the "sys.path" paths.

    :param str filename: file name to find.
    :return: found first occurrence.
    """

    return find_first_in_paths(filename, sys.path)


class FindUniquePath(name.FindUniqueString, object):
    def __init__(self, directory):
        if not directory:
            directory = folder.current_working_directory()

        self.parent_path = self._get_parent_path(directory)
        _basename = basename(directory=directory)

        super(FindUniquePath, self).__init__(_basename)

    def _get_scope_list(self):
        return folder.get_files_and_folders(directory=self.parent_path)

    def _search(self):
        name = super(FindUniquePath, self)._search()
        return join_path(self.parent_path, name)

    def _get_parent_path(self, directory):
        return dirname(directory)


class DirectoryPath(helpers.ObjectDict):

    def __init__(
            self, path: str | None = None, id: str | None = None, alias: str | None = None, pref : Dict | None = None):

        kwargs = {}
        if pref:
            kwargs = pref
        else:
            kwargs['id'] = id or str(uuid.uuid4())[:6]
            kwargs['path'] = normalize_path(path)
            kwargs['alias'] = alias or basename(path)
        if not kwargs['path'] and kwargs['pref'] is None:
            raise Exception('"pref" or "path" must be set for DirectoryPath')

        super().__init__(**kwargs)

    def __eq__(self, other):
        if isinstance(other, str):
            return normalize_path(other) == normalize_path(self.path)
        if isinstance(other, DirectoryPath):
            return normalize_path(other.path) == normalize_path(self.path)

        return super().__eq__(other)

    def serialize(self) -> Dict:
        """
        Returns serialized data.

        :return: serialized data.
        :rtype: Dict
        """

        return self
