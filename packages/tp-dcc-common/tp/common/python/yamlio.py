#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility methods related to write/read YAML files
"""

from __future__ import annotations

import os
from typing import Dict

import yaml
import yaml.representer

from tp.core import log
from tp.common.python import yamlordereddictloader

logger = log.tpLogger


def validate_yaml(dictionary: Dict) -> bool:
    """
    Validates whether the given dictionary can be dumped into a YAML file.

    :param Dict dictionary: dictionary to store.
    :return: True if the dictionary is valid; False otherwise.
    :rtype: bool
    """

    try:
        yaml.dump(dictionary)
        return True
    except Exception:
        return False


def write_to_file(data: Dict, filename: str, **kwargs) -> str | None:
    """
    Writes data to YAML file.

    :param Dict data: data to store into YAML file.
    :param str filename: name of the YAML file we want to store data into.
    :return: file name of the stored file.
    :rtype: str
    """

    indent = kwargs.pop('indent', 2)
    dumper = kwargs.pop('Dumper', None)
    kwargs['default_flow_style'] = kwargs.pop('default_flow_style', False)
    kwargs['width'] = kwargs.pop('width', 200)

    try:
        with open(filename, 'w') as yaml_file:
            if not dumper:
                try:
                    yaml.safe_dump(data, yaml_file, indent=indent, **kwargs)
                except yaml.representer.RepresenterError:
                    yaml.dump(data, yaml_file, indent=indent, **kwargs)
            else:
                yaml.dump(data, yaml_file, indent=indent, Dumper=dumper, **kwargs)
    except IOError:
        logger.error('Data not saved to file {}'.format(filename))
        return None

    logger.debug('File correctly saved to: {}'.format(filename))

    return filename


def read_file(filename: str, maintain_order: bool = False) -> Dict | None:
    """
    Returns data from YAML file.

    :param str filename: name of YAML file we want to read data from.
    :param bool maintain_order: whether to maintain the order of the returned dictionary or not.
    :return: data read from YAML file as dictionary.
    :return: Dict or None
    """

    if os.stat(filename).st_size == 0:
        return None
    else:
        try:
            with open(filename, 'r') as yaml_file:
                if maintain_order:
                    data = yaml.load(yaml_file, Loader=yamlordereddictloader.Loader)
                else:
                    data = yaml.safe_load(yaml_file)
        except Exception as exc:
            logger.warning('Could not read {} : {}'.format(filename, exc))
            return None

    return data
