# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

# --------------------
# System wide imports
#  -------------------

import os
import sqlite3

# ---------------------
# Third party libraries
# ---------------------

import decouple


def open_database(path=None, env_var=None):
    if path is None:
        path = decouple.config(env_var)
    if not os.path.exists(path):
        raise IOError("No SQLite3 Database file found in {0}. Exiting ...".format(path))
    return sqlite3.connect(path), path
