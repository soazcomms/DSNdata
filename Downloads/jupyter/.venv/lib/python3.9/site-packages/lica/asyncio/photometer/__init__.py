# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# ---------------------
# Third party libraries
# ---------------------
import sys
import enum
import decouple

if sys.version_info[1] < 11:
    from typing_extensions import Self
else:
    from typing import Self

# ---------
# Constants
# ---------


class Role(enum.IntEnum):
    REF = 1
    TEST = 0

    def tag(self):
        return f"{self.name:.<4s}"

    def __str__(self):
        return f"{self.name.lower()}"

    def __repr__(self):
        return f"{self.name.upper()}"

    def __iter__(self):
        return self

    def __next__(self):
        return Role.TEST if self is Role.REF else Role.REF

    def other(self) -> Self:
        return next(self)

    def endpoint(self) -> str:
        env_var = 'REF_ENDPOINT' if self is Role.REF else 'TEST_ENDPOINT'
        return decouple.config(env_var)


class Model(enum.Enum):
    # Photometer models
    TESSW = "TESS-W"
    TESSP = "TESS-P"
    TAS = "TAS"
    TESS4C = "TESS4C"


class Sensor(enum.Enum):
    TSL237 = "TSL237"
    S970501DT = "S9705-01DT"
