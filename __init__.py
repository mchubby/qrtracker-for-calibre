#!/usr/bin/env python
# vim:fileencoding=utf-8:ai:ts=4:sw=4:et:sts=4:tw=128:
from __future__ import (unicode_literals, division, absolute_import, print_function)
"""This package is calibre_plugins.qrcode_tracker_philidel once imported by Calibre"""

__license__ = 'GPL v3'
__copyright__ = '2016-2019, Marco77 <http://www.mobileread.com/forums/member.php?u=271721>'
__docformat__ = 'restructuredtext en'

from calibre.customize import EditBookToolPlugin

###########################################################
PLUGIN_NAME = "QRCode Tracker Filidel"
PLUGIN_DESCRIPTION = 'Inserts a generated QR code image at the end of every chapter, to help tracking reading progress.'
PLUGIN_VERSION_TUPLE = (0, 7, 1)
PLUGIN_VERSION = '.'.join([str(x) for x in PLUGIN_VERSION_TUPLE])
PLUGIN_AUTHORS = 'Marco77'
###########################################################


class QrCodeTrackerFilidelPlugin(EditBookToolPlugin):
    """Plugin Info for Calibre"""

    name = PLUGIN_NAME
    version = PLUGIN_VERSION_TUPLE
    author = PLUGIN_AUTHORS
    supported_platforms = ['windows', 'osx', 'linux']
    description = PLUGIN_DESCRIPTION
    minimum_calibre_version = (2, 61, 0)  # manifest_items_of_type()
