# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

# -------------------
# System wide imports
# -------------------

import os
import glob
import datetime
import itertools

# ---------
# Constants
# ---------

# ------------------
# Auxiliar functions
# ------------------


def file_paths(input_dir, files_filter):
    """Given a directory and a file filter, returns full path list"""
    file_list = [
        os.path.join(input_dir, fname)
        for fname in glob.iglob(files_filter, root_dir=input_dir)
    ]
    if not file_list:
        raise OSError("File list is empty, review the directory path or filter")
    return file_list


def chop(string, sep=None):
    """Chop a list of strings, separated by sep and
    strips individual string items from leading and trailing blanks"""
    chopped = tuple(elem.strip() for elem in string.split(sep))
    if len(chopped) == 1 and chopped[0] == "":
        chopped = tuple()
    return chopped


def measurements_session_id() -> int:
    """returns a unique session Id for meassurements"""
    return int(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S"))


def group(n: int, iterable):
    iterable = iter(iterable)
    return iter(lambda: list(itertools.islice(iterable, n)), [])
