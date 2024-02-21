#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions related with Python file input/output
"""

import os
import json
import errno
import fnmatch
import zipfile
from collections import OrderedDict

import yaml
import yamlordereddictloader

from tp.bootstrap import log

logger = log.bootstrapLogger

# update yaml to properly support the storage of OrderedDicts
yaml.add_representer(OrderedDict, lambda self, data:  self.represent_mapping('tag:yaml.org,2002:map', data.items()))


def ensure_folder_exists(path, permissions=None, placeholder=False):
    """
    Returns whether a given folder exists in a safe way.

    :return: True if given folder exists; False otherwise.
    :rtype: bool
    """

    permissions = permissions or 0o775
    if not os.path.exists(path):
        try:
            os.makedirs(path, permissions)
            if placeholder:
                place_path = os.path.join(path, 'placeholder')
                if not os.path.exists(place_path):
                    with open(place_path, 'wt') as fh:
                        fh.write('Automatically generated placeholder file')
                        fh.write("The reason why this file exists is due to source control system's which do not "
                                 "handle empty folders.")
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                logger.error(f'Unknown error occurred while making paths: {path}', exc_info=True)
                raise


def load_json(file_path):
    """
    Function that loads and returns the data of JSON file.

    :param str file_path: absolute path to JSON file.
    :return: content of the file.
    :rtype: dict
    """

    try:
        data = json.load(file_path)
    except (TypeError, AttributeError):
        with open(file_path) as f:
            data = json.load(f)

    return data


def save_json(data, file_path, **kwargs):
    """
    Saves given data to a JSON file.

    :param dict data: JSON compatible dictionary to save.
    :param str file_path: absolute file path to save the data.
    :param dict kwargs: keyword arguments for JSON dump.
    :return: True if the save operation was successfull; False otherwise.
    :rtype: bool
    """

    ensure_folder_exists(os.path.dirname(file_path))
    with open(file_path, 'w') as f:
        json.dump(data, f, **kwargs)

    logger.debug(f'----> file correct saved to: {file_path}')

    return True


def load_yaml(file_path, maintain_order=True):
    """
    Function that loads and returns the data of YAML file.

    :param str file_path: absolute path to YAML file.
    :param bool maintain_order: whether to maintain the order of the returned dictionary or not.
    :return: content of the file.
    :rtype: dict
    """

    with open(file_path, 'r') as yaml_file:
        if maintain_order:
            data = yaml.load(yaml_file, Loader=yamlordereddictloader.Loader)
        else:
            data = yaml.safe_load(yaml_file)

    return data


def save_yaml(data, file_path, **kwargs):
    """
    Saves given data to a YAML file.

    :param dict data: YAML compatible dictionary to save.
    :param str file_path: absolute file path to save the data.
    :param dict kwargs: keyword arguments for YAML dump.
    :return: True if the save operation was successfull; False otherwise.
    :rtype: bool
    """

    ensure_folder_exists(os.path.dirname(file_path))
    if 'indent' not in kwargs:
        kwargs['indent'] = 4
    with open(file_path, 'w') as f:
        yaml.dump(data, f, **kwargs)

    logger.debug(f'----> file correct saved to: {file_path}')

    return True


def zip_dir(directory, output_path, filters=None):
    """
    Creatse a zip file from a given directory recursively.

    :param str directory: directory to save .zip into.
    :param str output_path: .zip output path.
    :param tuple(str) filters: a tuple of fnmatch compatible filters.
    :return: True if the zip file was created successfully; False otherwise.
    :rtype: bool
    """

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as ziph:
        for root, dirs, files in os.walk(directory):
            if any(fnmatch.fnmatch(root, filter_name) for filter_name in filters):
                continue
            for f in files:
                if any(fnmatch.fnmatch(f, filter_name) for filter_name in filters):
                    continue
                full_path = os.path.join(root, f)
                ziph.write(full_path, arcname=full_path[len(directory) + 1:])
        if os.path.exists(output_path):
            return True

    return False
