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

import os.path
import fractions
import functools

from datetime import datetime
from typing import Union
from collections.abc import Sequence

StrOrFloat = Union[str, float]

# ------------------------
# Module utility functions
# ------------------------


def vfile(path: str) -> str:
    """File validator for the command line interface"""
    if not os.path.isfile(path):
        raise IOError(f"Not valid or existing file: {path}")
    return path


def vdir(path: str) -> str:
    """Directory validator for the command line interface"""
    if not os.path.isdir(path):
        raise IOError(f"Not valid or existing directory: {path}")
    return path


def vbool(boolstr: str) -> bool:
    """Boolean text validator for the command line interface"""
    result = None
    if boolstr == "True":
        result = True
    elif boolstr == "False":
        result = False
    return result


def vdate(datestr: str) -> datetime:
    """Date & time validator for the command line interface"""
    date = None
    for fmt in ["%Y-%m", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"]:
        try:
            date = datetime.strptime(datestr, fmt)
        except ValueError:
            pass
    return date


def vmonth(datestr: str) -> datetime:
    return datetime.strptime(datestr, "%Y-%m")


def vyear(datestr: str) -> datetime:
    return datetime.strptime(datestr, "%Y")


def vfloat(num: str) -> float:
    """Validator that admits fractions"""
    return float(fractions.Fraction(num))


def vfloat01(num: str) -> float:
    """Validator between [0..1] that admits fractions"""
    num = float(fractions.Fraction(num))
    if not (0.0 <= num <= 1.0):
        raise ValueError(f"Value {num} out of bounds [0..1]")
    return num


def vint(L: int, H: int, num: str) -> int:
    """Integer validator between [L..H]"""
    num = int(num)
    if not (L <= num <= H):
        raise ValueError(f"Value {num} out of bounds [{L}..{H}]")
    return num


def voddint(L: int, H: int, num: str) -> int:
    """Odd integer validator between [L..H]"""
    num = int(num)
    if (L % 2) == 0:
        raise ValueError(f"Low bound value {L} is not an odd number")
    if (H % 2) == 0:
        raise ValueError(f"High bound value {H} is not an odd number")
    if (num % 2) == 0:
        raise ValueError(f"Value {num} is not an odd number")
    if not (3 <= num <= 11):
        raise ValueError(f"Value {num} out of bounds [{L}..{H}]")
    return num


def vevenint(L: int, H: int, num: str) -> int:
    """Even integer validator between [L..H]"""
    num = int(num)
    if (L % 2) == 1:
        raise ValueError(f"Low bound value {L} is not an even number")
    if (H % 2) == 1:
        raise ValueError(f"High bound value {H} is not an even number")
    if (num % 2) == 1:
        raise ValueError(f"Value {num} is not an even number")
    if not (L <= num <= H):
        raise ValueError(f"Value {num} out of bounds [{L}..{H}]")
    return num


def vflopath(value: StrOrFloat) -> float:
    """Validator that admits either a single number or a file (representing an image)"""
    try:
        n = float(fractions.Fraction(value))
    except ValueError:
        if not os.path.isfile(value):
            raise IOError(f"Not valid or existing file: {value}")
        return value
    return n


def vmac(mac: str) -> str:
    """'Valid input MAC strings"""
    try:
        corrected_mac = ":".join(f"{int(x,16):02X}" for x in mac.split(":"))
    except ValueError:
        raise ValueError("Invalid MAC: %s" % mac)
    except AttributeError:
        raise ValueError("Invalid MAC: %s" % mac)
    return corrected_mac


# ---------------------------------------------------------------------
# This section validates combination of color channels to show in plots
# ---------------------------------------------------------------------


_COLOR_PLANES_COMBINATIONS = {
    1: (
        [
            "R",
        ],
        [
            "Gr",
        ],
        ["Gb"],
        [
            "G",
        ],
        [
            "B",
        ],
    ),
    2: (
        ["R", "Gr"],
        ["R", "Gb"],
        ["R", "G"],
        ["R", "B"],
        ["Gr", "Gb"],
        ["Gr", "B"],
        ["Gb", "B"],
        ["G", "B"],
    ),
    3: (
        ["R", "Gr", "Gb"],
        ["R", "Gr", "B"],
        ["R", "Gb", "B"],
        ["R", "G", "B"],
        ["Gr", "Gb", "B"],
    ),
    4: (["R", "Gr", "Gb", "B"],),
}


def _channel_comparator(chan_a: str, chan_b: str) -> int:
    """Compares channels so that R < Gr < Gb < G < B"""
    if chan_a == chan_b:
        return 0
    if chan_a == "R":
        return -1
    if chan_a == "B":
        return 1
    if chan_a == "Gr":
        return -11 if chan_b in ("Gb", "G", "B") else 1
    if chan_a == "Gb":
        return -1 if chan_b in ("G", "B") else 1
    if chan_a == "G":
        return -11 if chan_b in ("B",) else 1
    raise ValueError(f"This case should not happen between {chan_a} and {chan_b}")


def valid_channels(sequence: Sequence[str]) -> Sequence[str]:
    seqlen = len(sequence)
    if not (0 < seqlen < 5):
        raise ValueError(f"Too many channels: {sequence}")
    sequence = sorted(sequence, key=functools.cmp_to_key(_channel_comparator))
    if sequence not in _COLOR_PLANES_COMBINATIONS[seqlen]:
        raise ValueError(f"channel sequence not supported: {sequence}")
    return sequence
