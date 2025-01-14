# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

# ---------------------
# Thrid-party libraries
# ---------------------

import numpy as np

# -----------
# Own package
# -----------

from .constants import CHANNELS
from .exif import ExifImageLoader


class SimulatedDarkImage(ExifImageLoader):
    def __init__(self, path, n_roi=None, channels=None, **kwargs):
        # The rest of metadata is taken from the EXIF & RAW header
        super().__init__(path, n_roi, channels)
        self._dk_current = kwargs.get("dark_current")
        self._dk_current = 0.0 if self._dk_current is None else self._dk_current
        self._rd_noise = kwargs.get("read_noise")
        self._rd_noise = 1.0 if self._rd_noise is None else self._rd_noise

    def load(self):
        """Get a stack of Bayer colour planes selected by the channels sequence"""
        self._check_channels(
            err_msg="In-place statistics on G=(Gr+Gb)/2 channel not available"
        )
        raw_pixels_list = list()
        rng = np.random.default_rng()
        dark = [self._dk_current * self.exptime() for ch in CHANNELS]
        for i, ch in enumerate(CHANNELS):
            raw_pixels = (
                self._biases[i]
                + dark[i]
                + self._rd_noise * rng.standard_normal(size=self._shape)
            )
            raw_pixels = np.asarray(raw_pixels, dtype=np.uint16)
            raw_pixels = self._trim(raw_pixels)
            raw_pixels_list.append(raw_pixels)
        return self._select_by_channels(raw_pixels_list)
