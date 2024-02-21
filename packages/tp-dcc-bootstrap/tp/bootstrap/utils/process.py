#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains helper functions related with Python processes
"""

import sys
import subprocess


def subprocess_check_output(*args, **kwargs):
    """
    Calls subprocess and returns its outputs.

    :param tuple args: subprocess.Popen arguments.
    :param dict kwargs: subprocess.Popen keyword arguments.
    :return: output from subprocess.Popen communicate.
    :rtype: str
    """

    process = subprocess.Popen(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, *args, **kwargs)
    if sys.platform == 'win32':
        process.stdin.close()
    output = process.communicate()
    fail_code = process.poll()
    if fail_code:
        raise OSError(output)

    return output


def check_output(*args, **kwargs):
    """
    Function that handles sub processing safely on win32 which requires an extra flag.

    :param tuple args: subprocess.Popen arguments.
    :param dict kwargs: subprocess.Popen keyword arguments.
    :return: output from subprocess.Popen communicate.
    :rtype: str
    """
    if sys.platform == 'win32':
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE

    return subprocess_check_output(*args, **kwargs)
