# ArcSmith: ArcPy toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

from __future__ import annotations

import arcpy
from pathlib import Path

from ._types import _PathLike

__all__ = ["init_gdb", "temp_space"]


def init_gdb(folder: _PathLike, gdb_name: str, overwrite: bool = False) -> str:
    """
    Create a file geodatabase at the specified location.

    The folder is created if it does not already exist. The behavior when the
    geodatabase itself already exists is controlled by ``overwrite``.

    Parameters
    ----------
    folder : str or Path
        Folder in which to create the geodatabase.
    gdb_name : str
        Name of the geodatabase. A trailing ``.gdb`` extension, if supplied, is
        stripped so that ``"glacier"`` and ``"glacier.gdb"`` behave identically.
    overwrite : bool, optional
        Controls what happens when the target ``.gdb`` already exists.
        If ``False`` (default), the existing geodatabase is left untouched and
        its path is returned (the call is idempotent). If ``True``, the
        existing geodatabase is deleted and recreated empty.

        Note that ``arcpy.env.overwriteOutput`` does not apply to geodatabase
        creation, so this flag is the only way to force a fresh workspace.

    Returns
    -------
    str
        Absolute path to the geodatabase as a string. This is the newly
        created ``.gdb`` unless an existing one was reused (``overwrite=False``).

    Examples
    --------
    >>> gdb = arcsmith.ws.init_gdb(r"C:/Projects/Glacier", "glacier")
    >>> # C:/Projects/Glacier/glacier.gdb

    >>> arcpy.env.workspace = arcsmith.ws.init_gdb(folder, gdb_name)

    Force a fresh, empty geodatabase even if one already exists:

    >>> gdb = arcsmith.ws.init_gdb(folder, "glacier", overwrite=True)
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)

    if gdb_name.lower().endswith(".gdb"):
        gdb_name = gdb_name[:-4]
    gdb_path = folder / f"{gdb_name}.gdb"

    if arcpy.Exists(str(gdb_path)):
        if overwrite:
            arcpy.management.Delete(str(gdb_path))
        else:
            arcpy.AddMessage(f"GeoDatabase already exists, reusing: {gdb_path}")
            return str(gdb_path)

    result = arcpy.management.CreateFileGDB(str(folder), f"{gdb_name}.gdb")
    out = result.getOutput(0)
    arcpy.AddMessage(f"GeoDatabase created: {out}")

    return out


def temp_space(use_memory: bool = True) -> str:
    """
    Return a workspace path for intermediate outputs.

    Use during development to route temporary feature classes to the scratch
    geodatabase for inspection, then switch to ``use_memory=True`` (the
    default) for production runs.

    Note that the ``'memory'`` workspace does not support everything an
    on-disk geodatabase does. Certain field types, attribute indexes, and a
    handful of tools cannot write to it. If a tool fails against ``'memory'``,
    fall back to ``use_memory=False`` for tool compatibility, not only for
    inspection.

    Parameters
    ----------
    use_memory : bool, optional
        If ``True`` (default), returns ``'memory'``. This is the in-memory workspace.
        If ``False``, returns ``arcpy.env.scratchGDB``. This is the session scratch
        geodatabase, which persists on disk and can be inspected in ArcGIS Pro.

    Returns
    -------
    str
        ``'memory'`` or the absolute path to the scratch geodatabase.

    Examples
    --------
    Build a temporary feature class path:

    >>> ws = arcsmith.ws.temp_space()
    >>> tmp = f"{ws}/trails_temp"

    Route intermediates to scratch GDB for inspection during development:

    >>> ws = arcsmith.ws.temp_space(use_memory=False)
    >>> tmp = f"{ws}/trails_temp"
    """
    if use_memory:
        return "memory"
    return arcpy.env.scratchGDB