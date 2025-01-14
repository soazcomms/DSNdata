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

from jinja2 import Environment, PackageLoader


def render_from(package, template: str, context: dict) -> str:
    return (
        Environment(loader=PackageLoader(package, package_path="templates"))
        .get_template(template)
        .render(context)
    )
