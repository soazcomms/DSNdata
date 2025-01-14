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

import re

# ---------------------
# Thrid-party libraries
# ---------------------

import numpy as np

# -----
# ----------------------
# Module utility classes
# ----------------------


class Point:
    """Point class represents and manipulates x,y coords."""

    PATTERN = r"\((\d+),(\d+)\)"

    @classmethod
    def from_string(cls, point_str):
        pattern = re.compile(Point.PATTERN)
        matchobj = pattern.search(point_str)
        if matchobj:
            x = int(matchobj.group(1))
            y = int(matchobj.group(2))
            return cls(x, y)
        else:
            return None

    def __init__(self, x=0, y=0):
        """Create a new point at the origin"""
        self.x = x
        self.y = y

    def __add__(self, Roi):
        return NotImplementedError

    def __repr__(self):
        return f"({self.x},{self.y})"


class NormRoi:
    """Normalized Roiangle with 0..1 floating point coordinates and dimensions"""

    def __init__(self, n_x0=None, n_y0=None, n_width=1.0, n_height=1.0):
        self.x0 = n_x0
        self.y0 = n_y0
        self.width = n_width
        self.height = n_height

    @classmethod
    def from_roi(cls, roi, width, height):
        n_x0 = roi.x0 / width
        n_y0 = roi.y0 / height
        n_width = (roi.x1 - roi.x0) / width
        n_height = (roi.y1 - roi.y0) / height
        return cls(n_x0, n_y0, n_width, n_height)

    def __repr__(self):
        x0 = np.nan if self.x0 is None else self.x0
        y0 = np.nan if self.y0 is None else self.y0
        return f"[P0=({x0:.4f},{y0:.4f}) DIM=({self.width:.4f} x {self.height:.4f})]"


class Roi:
    """Region of interest"""

    # NumPy style [row0:row1,col0:col1]
    PATTERN = r"\[(\d+):(\d+),(\d+):(\d+)\]"

    @classmethod
    def from_string(cls, Roi_str):
        """numpy sections style"""
        pattern = re.compile(Roi.PATTERN)
        matchobj = pattern.search(Roi_str)
        if matchobj:
            y0 = int(matchobj.group(1))
            y1 = int(matchobj.group(2))
            x0 = int(matchobj.group(3))
            x1 = int(matchobj.group(4))
            return cls(x0, x1, y0, y1)
        else:
            return None

    @classmethod
    def from_normalized_roi(cls, width, height, n_roi, already_debayered=True):
        if n_roi.x0 is not None and n_roi.x0 + n_roi.width > 1.0:
            raise ValueError(
                f"normalized x0(={n_roi.x0}) + width(={n_roi.width}) = {n_roi.x0 + n_roi.width} exceeds 1.0"
            )
        if n_roi.y0 is not None and n_roi.y0 + n_roi.height > 1.0:
            raise ValueError(
                f"normalized x0(={n_roi.y0}) + width(={n_roi.height}) = {n_roi.y0 + n_roi.height} exceeds 1.0"
            )
        # If not already_debayered, we'll adjust to each image plane dimensions
        if not already_debayered:
            height = height // 2
            width = width // 2
        # From normalized ROI to actual image dimensions ROI
        w = int(round(width * n_roi.width, 0))
        h = int(round(height * n_roi.height, 0))
        x0 = (width - w) // 2 if n_roi.x0 is None else int(round(width * n_roi.x0, 0))
        y0 = (height - h) // 2 if n_roi.y0 is None else int(round(height * n_roi.y0, 0))
        return cls(x0, x0 + w, y0, y0 + h)

    @classmethod
    def from_dict(cls, Roi_dict):
        return cls(Roi_dict["x0"], Roi_dict["x1"], Roi_dict["y0"], Roi_dict["y1"])

    @classmethod
    def extend_X(cls, roi, width, already_debayered=True):
        """Produce a new ROI extendoing the existsing up to X Borders"""
        if not already_debayered:
            width = width // 2
        return cls(x0=0, x1=width, y0=roi.y0, y1=roi.y1)

    @classmethod
    def extend_Y(cls, roi, height, already_debayered=True):
        """Produce a new ROI extendoing the existsing up to Y Borders"""
        if not already_debayered:
            height = height // 2
        return cls(x0=roi.x0, x1=roi.x1, y0=0, y1=height)

    def __init__(self, x0, x1, y0, y1):
        self.x0 = min(x0, x1)
        self.y0 = min(y0, y1)
        self.x1 = max(x0, x1)
        self.y1 = max(y0, y1)

    def to_dict(self):
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1}

    def xy(self):
        """To use when displaying Rectangles in matplotlib"""
        return (self.x0, self.y0)

    def width(self):
        return abs(self.x1 - self.x0)

    def height(self):
        return abs(self.y1 - self.y0)

    def dimensions(self):
        """returns width and height"""
        return abs(self.x1 - self.x0), abs(self.y1 - self.y0)

    def centre(self):
        return (
            self.x0 + self.width() / 2,
            self.y0 + self.height() / 2,
        )

    def __add__(self, point):
        return Roi(
            self.x0 + point.x, self.x1 + point.x, self.y0 + point.y, self.y1 + point.y
        )

    def __radd__(self, point):
        return self.__add__(point)

    def __repr__(self):
        """string in NumPy section notation"""
        return f"[{self.y0}:{self.y1},{self.x0}:{self.x1}]"
