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

import logging

# ---------------------
# Thrid-party libraries
# ---------------------

import numpy as np

# ------------------------
# Own modules and packages
# ------------------------

from ..loader import ImageLoaderFactory

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger(__name__)

# -------
# Classes
# -------


class ImageStatistics:
    def __init__(self):
        '''Should not be used to instantiate directly'''
        self._pixels = None
        self._bias = None
        self._dark = None
        self._mean = None
        self._min = None
        self._max = None
        self._variance = None
        self._median = None
        self._factory = ImageLoaderFactory()

    @classmethod
    def from_path(cls, path, n_roi, channels, bias=None, dark=None):
        obj = cls()
        obj._image = obj._factory.image_from(path, n_roi, channels)
        obj._configure(bias, dark)
        return obj

    @classmethod
    def attach(cls, loader, bias=None, dark=None):
        obj = cls()
        obj._image = loader
        obj._configure(bias, dark)
        return obj

    def _configure(self, bias, dark):
        if self._bias is not None:
            return
        channels = self._image.channels()
        n_roi = self._image.n_roi()
        N = len(channels)
        if bias is None:
            try:
                bias = self._image.black_levels()
                self._bias = np.array(
                    self._image.black_levels()).reshape(N, 1, 1)
            except Exception:
                log.warn("No luck using embedded image black levels as bias")
                self._bias = np.full((N, 1, 1), 0)
        elif type(bias) is str:
            self._bias = self._factory.image_from(bias, n_roi, channels).load()
        elif type(bias) is float:
            self._bias = np.full((N, 1, 1), bias)
        if dark is not None:
            self._dark = dark * self._image.exptime()
            log.info("Bias level per channel: %s. Dark count is %.02g",
                     self._bias.reshape(-1), self._dark)
        else:
            log.info("Bias level per channel: %s.", self._bias.reshape(-1))

    def loader(self):
        '''access to underying image loader for extra methods such as image.exptime()'''
        return self._image

    def run(self):
        if self._dark is not None:
            self._pixels = self._image.load().astype(dtype=np.float32, copy=False) - \
                self._bias - self._dark  # Stack of image color planes, cropped by ROI
        else:
            self._pixels = self._image.load().astype(
                dtype=np.float32, copy=False) - self._bias

    def name(self):
        return self._image.name()

    def pixels(self):
        return self._pixels

    def mean(self):
        if self._mean is None:
            self._mean = np.mean(self._pixels,  axis=(1, 2))
        return self._mean

    def variance(self):
        if self._variance is None:
            self._variance = np.var(self._pixels, axis=(
                1, 2), dtype=np.float64, ddof=1)
        return self._variance

    def std(self):
        if self._variance is None:
            self._variance = np.var(self._pixels, axis=(
                1, 2), dtype=np.float64, ddof=1)
        return np.sqrt(self._variance)

    def median(self):
        if self._median is None:
            self._median = np.median(self._pixels,  axis=(1, 2))
        return self._median

    def min(self):
        if self._min is None:
            self._min = np.min(self._pixels,  axis=(1, 2))
        return self._min

    def max(self):
        if self._max is None:
            self._max = np.max(self._pixels,  axis=(1, 2))
        return self._max


class ImagePairStatistics(ImageStatistics):
    '''Analize Image im pairs to remove Fixed Pattern Noise in the variance'''

    def __init__(self):
        super().__init__()
        self._diff = None
        self._pair_mean = None
        self._pair_variance = None

    @classmethod
    def from_path(cls, path_a, path_b, n_roi, channels, bias=None, dark=None):
        obj = cls()
        obj._image = obj._factory.image_from(path_a, n_roi, channels)
        obj._configure(bias, dark)
        obj._image_b = obj._factory.image_from(path_b, n_roi, channels)
        return obj

    def run(self):
        super().run()
        if self._dark is not None:
            self._pixels_b = self._image_b.load().astype(
                np.float32, copy=False) - self._bias - self._dark
        else:
            self._pixels_b = self._image_b.load().astype(
                np.float32, copy=False) - self._bias

    def names(self):
        '''Like name() but returns'''
        return self._image.name(), self._image_b.name()

    def pair_mean(self):
        '''Mean of pair of images'''
        if not self._pair_mean:
            self._pair_mean = np.mean(
                (self._pixels + self._pixels_b),  axis=(1, 2)) / 2
        return self._mean

    def adj_pair_variance(self):
        '''variance of pair adjusted by a final 1/2 factor'''
        if not self._pair_variance:
            self._pair_variance = np.var(
                (self._pixels - self._pixels_b), axis=(1, 2), dtype=np.float64, ddof=1) / 2
        return self._pair_variance
