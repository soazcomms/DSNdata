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
import math
import logging

# ---------------------
# Thrid-party libraries
# ---------------------

import numpy as np
from astropy.io import fits

# -----------
# Own package
# -----------

from .constants import CHANNELS
from .roi import Roi
from .abstract import AbstractImageLoader

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger(__name__)


class FitsImageLoader(AbstractImageLoader):

    def __init__(self, path, v_roi, channels):
        super().__init__(path, v_roi, channels)
        # self._fits()

    def get_header(self, header, tag, default=None):
        try:
            value = header[tag]
        except KeyError:
            value = default
        return value

    def _fits_metadata(self, hdul):
        self._name = os.path.basename(self._path)
        header = hdul[0].header
        self._dim = header['NAXIS']
        if self._dim == 2:
            height = header['NAXIS2']
            width = header['NAXIS1']
            # Here we need to debayer, so a CFA keyword is needed
            self._cfa = self.get_header(header, 'BAYER')
            self._roi = Roi.from_normalized_roi(
                width, height, self._n_roi, already_debayered=False)
            self._shape = (height // 2, width // 2)
        else:
            assert self._dim == 3
            Z = header['NAXIS3']  # noqa: F841
            height = header['NAXIS2']
            width = header['NAXIS1']
            self._roi = Roi.from_normalized_roi(
                width, height, self._n_roi, already_debayered=True)
            self._shape = (height, width)
            # Generic metadata
        self._metadata['name'] = self._name
        self._metadata['roi'] = str(self._roi)
        self._metadata['channels'] = ' '.join(self._channels)
        self._metadata['width'] = self._shape[1]
        self._metadata['height'] = self._shape[0]
        self._metadata['exposure'] = header['EXPTIME']
        self._metadata['camera'] = self.get_header(header, 'INSTRUME')
        self._metadata['maker'] = self.get_header(header, 'MAKER')       # ?
        self._metadata['iso'] = self.get_header(header, 'ISO')  # ?
        self._metadata['datetime'] = self.get_header(header, 'DATE-OBS')
        self._metadata['pedestal'] = self.get_header(header, 'PEDESTAL')
        self._metadata['log-gain'] = self.get_header(header, 'LOG-GAIN')
        self._metadata['xpixsize'] = self.get_header(header, 'XPIXSIZE')
        self._metadata['ypixsize'] = self.get_header(header, 'XPIXSIZE')
        self._metadata['bayerpat'] = self.get_header(header, 'BAYERPAT')
        self._metadata['imagetyp'] = self.get_header(header, 'IMAGETYP')
        diam = self.get_header(header, 'APTDIA')
        focal = self.get_header(header, 'FOCAL-LEN')
        self._metadata['f_number'] = (
            focal/diam) if diam is not None and focal is not None else None
        self._metadata['focal_length'] = focal

    def _fits(self):
        with fits.open(self._path) as hdul:
            self._fits_metadata(hdul)

    def _trim(self, pixels):
        '''Special case for 3D FITS'''
        if self._roi:
            y0 = self._roi.y0
            y1 = self._roi.y1
            x0 = self._roi.x0
            x1 = self._roi.x1
            pixels = pixels[:, y0:y1,
                            x0:x1] if self._dim == 3 else pixels[y0:y1, x0:x1]
        return pixels

    def _load_cube(self, hdul):
        pixels = hdul[0].data
        assert len(pixels.shape) == 3
        pixels = self._trim(pixels)
        if self._channels is None or len(self._channels) == 4:
            return pixels.copy()
        return self._select_by_channels(pixels)

    def _load_debayer(self, hdul):
        raise NotImplementedError("Debayering for FITS still not supported")

    def metadata(self):
        if self._name is None:
            self._fits()
        return self._metadata

    def shape(self):
        '''Overrdies base method'''
        if self._dim == 2:
            return super().shape()
        else:
            return self._shape

    def load(self):
        ''' For the time being we only support FITS 3D cubes'''
        with fits.open(self._path) as hdul:
            self._fits_metadata(hdul)
            if self._dim == 2:
                nparray = self._load_debayer(hdul)
            else:
                nparray = self._load_cube(hdul)
        return nparray

    def statistics(self):
        '''In-place statistics calculation for RPi Zero'''
        with fits.open(self._path) as hdul:
            self._fits_metadata(hdul)
            pixels = hdul[0].data
            assert len(pixels.shape) == 3
            pixels = self._trim(pixels)
            average = pixels.mean(axis=0)
            variance = pixels.var(axis=0, dtype=np.float64, ddof=1)
            output_list = list()
            if self._channels is None or len(self._channels) == 4:
                output_list = list(zip(average.tolist(), variance.tolist()))
            else:
                for ch in self._channels:
                    if ch == 'G':
                        # This assumes that initial list is a pixel array list
                        aver_green = (average[1] + average[2]) / 2
                        std_green = math.sqrt(variance[1] + variance[2])
                        output_list.append([aver_green, std_green])
                    else:
                        i = CHANNELS.index(ch)
                        output_list.append([average[i], math.sqrt(variance[i])])
                return np.stack(output_list)


# ------------------
# Auxiliary fnctions
# ------------------
