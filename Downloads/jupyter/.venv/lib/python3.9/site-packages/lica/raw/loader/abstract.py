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

from .constants import CHANNELS, LABELS
from .roi import NormRoi


class AbstractImageLoader:
    def __init__(self, path, n_roi=None, channels=None, azotea=False):
        self._path = path
        self._n_roi = NormRoi(0.0, 0.0, 1.0, 1.0) if n_roi is None else n_roi
        self._full_image = (
            True if (self._n_roi.width == 1 and self._n_roi.height == 1) else False
        )
        self._channels = CHANNELS if channels is None else channels
        self._shape = None
        self._roi = None
        self._name = None
        self._metadata = dict()
        self._azotea = azotea  # To enforce AZOTEA metadata is present

    # -----------------------------
    # To be used in derived classes
    # -----------------------------

    def _check_channels(self, err_msg):
        if "G" in self._channels:
            raise NotImplementedError(err_msg)

    def _trim(self, pixels):
        """Default version for 2D not debayered images"""
        if not self._full_image:
            roi = self._roi
            y0 = roi.y0
            y1 = roi.y1
            x0 = roi.x0
            x1 = roi.x1
            pixels = pixels[y0:y1, x0:x1]  # Extract ROI
        return pixels

    def _select_by_channels(self, initial_list):
        output_list = list()
        for ch in self._channels:
            if ch == "G":
                # This assumes that initial list is a pixel array list
                aver_green = (initial_list[1] + initial_list[2]).astype(np.float32) / 2
                output_list.append(aver_green)
            else:
                i = CHANNELS.index(ch)
                output_list.append(initial_list[i])
        return np.stack(output_list)

    # ----------
    # Public API
    # ----------

    def label(self, i):
        return LABELS[i]

    def metadata(self):
        """Returns a metadata dictionary¡"""
        raise NotImplementedError

    def name(self):
        return self.metadata()["name"]

    def exptime(self):
        """Useul for image list sorting by exposure time"""
        return float(self.metadata()["exposure"])

    def shape(self):
        """Already debayered"""
        if not self._shape:
            self.metadata()
        return self._shape

    def channels(self):
        """Already debayered"""
        return self._channels

    def n_roi(self):
        return self._n_roi

    def roi(self):
        if self._roi is None:
            self.metadata()
        return self._roi

    def cfa_pattern(self):
        """Returns the Bayer pattern as RGGB, BGGR, GRBG, GBRG strings"""
        raise NotImplementedError

    def saturation_levels(self):
        raise NotImplementedError

    def black_levels(self):
        raise NotImplementedError

    def load(self):
        """Load a stack of Bayer colour planes selected by the channels sequence"""
        raise NotImplementedError

    def statistics(self):
        """In-place statistics calculation for RPi Zero"""
        raise NotImplementedError
