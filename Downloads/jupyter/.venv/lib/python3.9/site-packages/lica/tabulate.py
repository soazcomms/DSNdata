# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# --------------------

import tabulate
from .misc import group


def paging(cursor, headers, page_size=10):
    """
    Pages query output and displays in tabular format
    """
    for rows in group(page_size, cursor):
        print(tabulate.tabulate(rows, headers=headers, tablefmt="grid"))
        if len(rows) == page_size:
            input("Press Enter to continue [Ctrl-C to abort] ...")
