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

import os
import fractions
import logging

# ---------------------
# Thrid-party libraries
# ---------------------

import rawpy
import exifread
import numpy as np

# -----------
# Own package
# -----------

from .constants import CHANNELS
from .roi import Roi
from .abstract import AbstractImageLoader

# ---------
# Constants
# ---------

log = logging.getLogger(__name__)

# ----------
# Exceptions
# ----------


class UnsupportedCFAError(ValueError):
    '''Unsupported Color Filter Array type'''

    def __str__(self):
        s = self.__doc__
        if self.args:
            s = ' {0}: {1}'.format(s, str(self.args[0]))
        s = '{0}.'.format(s)
        return s


# ----------------
# Auxiliar classes
# ----------------

class ExifImageLoader(AbstractImageLoader):

    BAYER_LETTER = ['B', 'G', 'R', 'G']
    BAYER_PTN_LIST = ('RGGB', 'BGGR', 'GRBG', 'GBRG')
    CFA_OFFSETS = {
        # Esto era segun mi entendimiento
        'RGGB': {'R': {'x': 0, 'y': 0}, 'Gr': {'x': 1, 'y': 0}, 'Gb': {'x': 0, 'y': 1}, 'B': {'x': 1, 'y': 1}},
        'BGGR': {'R': {'x': 1, 'y': 1}, 'Gr': {'x': 1, 'y': 0}, 'Gb': {'x': 0, 'y': 1}, 'B': {'x': 0, 'y': 0}},
        'GRBG': {'R': {'x': 1, 'y': 0}, 'Gr': {'x': 0, 'y': 0}, 'Gb': {'x': 1, 'y': 1}, 'B': {'x': 0, 'y': 1}},
        'GBRG': {'R': {'x': 0, 'y': 1}, 'Gr': {'x': 0, 'y': 0}, 'Gb': {'x': 1, 'y': 1}, 'B': {'x': 1, 'y': 0}},
    }

    def __init__(self, path, n_roi=None, channels=None):
        super().__init__(path, n_roi, channels)
        self._shape = None
        self._raw_shape = None
        self._color_desc = None
        self._cfa = None
        self._biases = None
        self._white_levels = None
        self._raw()  # read raw metadata first to get image size
        self._exif()  # read exif metadata

    def _raw_metadata(self, img):
        '''To be used in teh context of an image context manager'''
        self._color_desc = img.color_desc.decode('utf-8')
        self._cfa = ''.join([self.BAYER_LETTER[img.raw_pattern[row, column]]
                             for row in (1, 0) for column in (1, 0)])
        self._biases = img.black_level_per_channel
        self._white_levels = img.camera_white_level_per_channel
        self._metadata['pedestal'] = self.black_levels()
        self._metadata['bayerpat'] = self._cfa
        self._metadata['colordesc'] = self._color_desc
        self._raw_shape = (img.sizes.raw_height, img.sizes.raw_width)

    def _raw(self):
        with rawpy.imread(self._path) as img:
            #log.info(" -----> LibRaw I/O [init] for %s", os.path.basename(self._path))
            self._raw_metadata(img)

    def _exif(self):
        with open(self._path, 'rb') as f:
            #log.info(" -----> EXIF I/O [init] for %s", os.path.basename(self._path))
            exif = exifread.process_file(f, details=True)
        if not exif:
            raise ValueError('Could not open EXIF metadata')
        # EXIF image size ias incorrectly reported and we have to read it from rawpy directly
        width = self._raw_shape[1]
        height = self._raw_shape[0]
        self._shape = (height//2, width//2)
        self._name = os.path.basename(self._path)
        self._roi = Roi.from_normalized_roi(
            width, height, self._n_roi, already_debayered=False)
        # General purpose metadata
        self._metadata['name'] = self._name
        self._metadata['roi'] = str(self._roi)
        self._metadata['channels'] = ' '.join(self._channels)
        # Metadata coming from EXIF
        for key in ('Image DateTime', 'EXIF DateTimeOriginal'):
            datetime = exif.get(key)
            if datetime:
                break
        self._metadata['datetime'] = datetime
        self._metadata['exposure'] = fractions.Fraction(
            str(exif.get('EXIF ExposureTime', 0)))
        self._metadata['width'] = self._shape[1]
        self._metadata['height'] = self._shape[0]
        self._metadata['iso'] = str(exif.get('EXIF ISOSpeedRatings'))
        self._metadata['camera'] = str(exif.get('Image Model')).strip()
        self._metadata['focal_length'] = fractions.Fraction(
            str(exif.get('EXIF FocalLength', 0)))
        self._metadata['f_number'] = fractions.Fraction(
            str(exif.get('EXIF FNumber', 0)))
        self._metadata['maker'] = str(exif.get('Image Make'))
        # Useless fo far ...
        self._metadata['note'] = str(exif.get('EXIF MakerNote'))
        self._metadata['log-gain'] = None  # Not known until load time
        # Not usually available in EXIF headers
        self._metadata['xpixsize'] = None
        # Not usually available in EXIF headers
        self._metadata['ypixsize'] = None
        # using an heuristic based on file names
        self._metadata['imagetyp'] = None

    # ----------
    # Public API
    # ----------

    def metadata(self):
        return self._metadata

    def cfa_pattern(self):
        '''Returns the Bayer pattern as RGGB, BGGR, GRBG, GBRG strings'''
        if self._color_desc != 'RGBG':
            raise UnsupportedCFAError(self._color_desc)
        return self._cfa

    def saturation_levels(self):
        self._check_channels(
            err_msg="saturation_levels on G=(Gr+Gb)/2 channel not available")
        if self._white_levels is None:
            raise NotImplementedError(
                "saturation_levels for this image not available using LibRaw")
        return tuple(self._white_levels[CHANNELS.index(ch)] for ch in self._channels)

    def black_levels(self):
        self._check_channels(
            err_msg="black_levels on G=(Gr+Gb)/2 channel not available")
        return tuple(self._biases[CHANNELS.index(ch)] for ch in self._channels)

    def load(self):
        '''Load a stack of Bayer colour planes selected by the channels sequence'''
        with rawpy.imread(self._path) as img:
            raw_pixels_list = list()
            for channel in CHANNELS:
                x = self.CFA_OFFSETS[self._cfa][channel]['x']
                y = self.CFA_OFFSETS[self._cfa][channel]['y']
                # This is the real debayering thing
                raw_pixels = img.raw_image[y::2, x::2].copy()
                raw_pixels = self._trim(raw_pixels)
                raw_pixels_list.append(raw_pixels)
        # Select the desired channels
        return self._select_by_channels(raw_pixels_list)

    def statistics(self):
        '''In-place statistics calculation for RPi Zero'''
        self._check_channels(
            err_msg="In-place statistics on G=(Gr+Gb)/2 channel not available")
        with rawpy.imread(self._path) as img:
            stats_list = list()
            for channel in CHANNELS:
                x = self.CFA_OFFSETS[self._cfa][channel]['x']
                y = self.CFA_OFFSETS[self._cfa][channel]['y']
                # This is the real debayering thing
                raw_pixels = img.raw_image[y::2, x::2]
                raw_pixels = self._trim(raw_pixels)
                stats = (raw_pixels.mean(), raw_pixels.var(
                    dtype=np.float64, ddof=1))
                stats_list.append(stats)
        return self._select_by_channels(stats_list)
