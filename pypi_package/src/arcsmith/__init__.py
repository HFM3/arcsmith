# ArcSmith: ArcPy toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

from importlib.metadata import PackageNotFoundError, version

from . import lyr
from . import param
from . import fc
from . import ws
from . import flds
from . import tbl

try:
    __version__ = version("arcsmith")
except PackageNotFoundError:  # running from a source checkout without an install
    __version__ = "0.0.0+unknown"