from __future__ import annotations

import os
import sys
import inspect

from Qt.QtWidgets import QApplication

from tp.core import log
from tp.preferences.interfaces import noddle
from tp.common.resources import api as resources
from tp.bootstrap.core import exceptions, package

logger = log.tpLogger


def startup(_: package.Package):
    """
    This function is automatically called by tpDcc packages Manager when environment setup is initialized.
    """

    logger.info('Loading tp-dcc-tools-rigging package...')

    root_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    # Make sure QApplication instance exists before registering resources
    app = QApplication.instance() or QApplication(sys.argv)
    resources_path = os.path.join(os.path.dirname(root_path), 'resources')
    resources.register_resource(resources_path, key='tp-dcc-tools-rigging')

    # Update Noddle preferences
    noddle_interface = noddle.noddle_interface()
    noddle_interface.upgrade_assets()


def shutdown(bootstrap_package: package.Package):
    """
    Shutdown function that is called during tpDcc framework shutdown.
    This function is called at the end of tpDcc framework shutdown.

    :param Package bootstrap_package: package instance.
    """

    logger.info('Shutting down tp-dcc-tools-rigging package...')

    if not bootstrap_package:
        raise exceptions.MissingPackage(package)
