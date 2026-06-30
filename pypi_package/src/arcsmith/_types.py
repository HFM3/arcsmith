# ArcSmith: GIS toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

"""Internal shared type aliases.

Private module (underscore-prefixed): not part of the public API and not
imported by ``arcsmith/__init__.py``. It holds the type aliases that would
otherwise be duplicated across several modules, so each has a single definition.
Module-specific aliases (geometry types, SQL placements, linear units, and the
like) stay local to the module that uses them.
"""

from __future__ import annotations

from typing import Literal, Union
from pathlib import Path

# Accepted spelling for filesystem-path arguments: a string or a pathlib.Path.
_PathLike = Union[str, Path]

# Closed string-enum of the arcpy AddField field types arcsmith creates.
# Annotating with Literal lets editors autocomplete the valid options and lets
# type checkers flag typos before runtime.
_FieldType = Literal["TEXT", "SHORT", "LONG", "FLOAT", "DOUBLE", "DATE"]
