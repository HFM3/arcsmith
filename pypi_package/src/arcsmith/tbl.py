# ArcSmith: GIS toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Optional, Union
import arcpy
from pathlib import Path, PureWindowsPath

from ._types import _FieldType, _PathLike

__all__ = ["from_rows", "add_rows", "join_lookup", "join_table",
           "add_to_map", "remove_from_map", "get"]

# Python type -> arcpy AddField type, used when a field type is inferred from
# the first non-null value in a column rather than supplied explicitly. Keyed on
# the exact type (not isinstance), so bool resolves to SHORT rather than LONG.
_PY_TO_ARCPY = {
    bool:  "SHORT",
    int:   "LONG",
    float: "DOUBLE",
    str:   "TEXT",
}

# Default length applied to inferred TEXT fields when the scanned values give no
# longer maximum (e.g. an all-null column with an explicit TEXT type).
_DEFAULT_TEXT_LEN = 255

# arcpy Field.type vocabulary -> AddField vocabulary. Used only to compare a
# requested field_type against an existing field's type when repopulating, so
# the comparison happens in one consistent vocabulary. Per the ArcGIS Pro Field
# docs, Field.type values are NOT identical to AddField keywords (e.g. 'Integer'
# vs 'LONG'); these are the documented equivalents. Newer Pro 3.x types
# (BigInteger, DateOnly, TimeOnly, TimestampOffset) are intentionally absent.
# An unmapped existing type falls through to the type-mismatch warning rather
# than silently comparing equal, which is the safe outcome.
_ADDFIELD_TYPE = {
    "SmallInteger": "SHORT",
    "Integer":      "LONG",
    "Single":       "FLOAT",
    "Double":       "DOUBLE",
    "String":       "TEXT",
    "Date":         "DATE",
}

# Field types JoinField cannot meaningfully copy. When a drop list is resolved
# into an explicit transfer list (fields=..., keep=False), these are removed
# first so the list mirrors what JoinField skips on its own when no fields are
# specified.
_NON_TRANSFERABLE_TYPES = {"OID", "Geometry", "GlobalID", "Blob", "Raster"}


def from_rows(out_table: _PathLike, rows: list, fields: list,
              overwrite: bool = False) -> str:
    """
    Create a standalone table from an in-memory list of rows.

    Use this to materialise Python data, such as a list of scalars, a list of
    tuples, or the output of :func:`arcsmith.flds.unique_values`, as an ArcGIS table. Point
    ``out_table`` at :func:`arcsmith.ws.temp_space` to produce a throwaway table
    for a subsequent join, or at a geodatabase path to keep it as a deliverable.

    For attaching a simple ``{key: value}`` lookup to a feature class, prefer
    :func:`join_lookup`, which needs no physical table at all. Reach for
    ``from_rows`` when you actually want a table: to persist one as a deliverable,
    or to build a multi-column source to feed :func:`join_table`.

    Parameters
    ----------
    out_table : str or Path
        Full path for the output table, including workspace and name
        (e.g. ``"C:/data/glacier.gdb/areas"`` or ``"memory/areas"``).
    rows : list
        The data to write. Either a list of tuples/lists (one per row, aligned
        to ``fields``) or, when there is a single field, a flat list of scalars
        (each is treated as a one-column row). An empty list is allowed only
        when every field carries an explicit type (an empty table with a fixed
        schema); an inferred field cannot be sized from no data and will raise.
    fields : list
        Column definitions, one per column, in order. Each entry may be:

        * ``(name, type)`` -- explicit arcpy field type
          (``"TEXT"``, ``"SHORT"``, ``"LONG"``, ``"FLOAT"``, ``"DOUBLE"``,
          ``"DATE"``).
        * ``(name, "TEXT", length)`` -- explicit text length.
        * ``name`` (a bare string) -- type inferred from the first non-null
          value in that column (``int`` -> ``LONG``, ``float`` -> ``DOUBLE``,
          ``str`` -> ``TEXT`` sized to the longest value, ``bool`` -> ``SHORT``).
    overwrite : bool, optional
        If ``False`` (default) and ``out_table`` already exists, a
        ``ValueError`` is raised rather than silently appending or replacing.
        If ``True``, an existing table at that path is deleted first.

    Returns
    -------
    str
        Path (or ``memory\\...`` path) to the created table.

    Raises
    ------
    ValueError
        If ``rows`` and ``fields`` disagree on column count, if a field type
        cannot be inferred (an all-null column with no explicit type), or if
        ``out_table`` exists and ``overwrite`` is ``False``.

    Notes
    -----
    Type inference keys on the exact Python type of the first non-null value, so
    values that are not plain ``int``/``float``/``str``/``bool`` (e.g. a
    ``numpy.int64`` from a dataframe) fall through to ``TEXT``. Supply an
    explicit ``(name, type)`` for those columns.

    The ``memory`` workspace does not support every field type an on-disk
    geodatabase does. The caveat documented on :func:`arcsmith.ws.temp_space`
    applies here too. If a write fails against ``memory``, target a scratch GDB
    path instead.

    Examples
    --------
    Single-column table from a flat list (scalars, not tuples):

    >>> area_codes = arcsmith.flds.unique_values(fc, "AREA_CODE")
    >>> arcsmith.tbl.from_rows("memory/area_codes", area_codes, [("AREA_CODE", "TEXT", 2)])

    Multi-column crosswalk with inferred types:

    >>> rows = [("NF", "North Fork"), ("LM", "Lake McDonald"), ("MG", "Many Glacier")]
    >>> arcsmith.tbl.from_rows(
    ...     "C:/data/glacier.gdb/areas", rows, ["AREA_CODE", "AREA_NAME"],
    ... )

    A temp table to feed a multi-column join:

    >>> tmp = arcsmith.tbl.from_rows(f"{arcsmith.ws.temp_space()}/area_xwalk", rows,
    ...                              ["AREA_CODE", "AREA_NAME"])
    >>> arcsmith.tbl.join_table(fc, "AREA_CODE", tmp, "AREA_CODE", ["AREA_NAME"])

    A red-bus ("Jammer") fleet roster as a standalone table:

    >>> rows = [(1, "Going-to-the-Sun", 17),
    ...         (2, "Many Glacier", 17),
    ...         (3, "Two Medicine", 17)]
    >>> arcsmith.tbl.from_rows("C:/data/glacier.gdb/red_buses", rows,
    ...                        ["BUS_ID", "ROUTE", "SEATS"])
    """
    out_table = Path(str(out_table))
    out_ws = str(out_table.parent)
    out_name = out_table.name

    # Normalise a flat list of scalars into a list of 1-tuples.
    single_col = len(fields) == 1
    if rows and not isinstance(rows[0], (tuple, list)):
        if not single_col:
            raise ValueError(
                "rows is a flat list of scalars but multiple fields were given; "
                "pass a list of tuples to populate more than one column."
            )
        rows = [(r,) for r in rows]

    # Validate row width against field count.
    for r in rows:
        if len(r) != len(fields):
            raise ValueError(
                f"Row {r!r} has {len(r)} value(s) but {len(fields)} field(s) "
                "were defined."
            )

    # Resolve each field spec to (name, type, length).
    resolved = []
    for col, spec in enumerate(fields):
        if isinstance(spec, str):
            name, ftype, length = spec, None, None
        elif len(spec) == 2:
            name, ftype, length = spec[0], spec[1], None
        else:
            name, ftype, length = spec[0], spec[1], spec[2]

        if ftype is None:
            # Infer from the first non-null value in this column.
            sample = next((r[col] for r in rows if r[col] is not None), None)
            if sample is None:
                raise ValueError(
                    f"Cannot infer a type for field '{name}': column is empty "
                    "or all-null. Supply an explicit (name, type)."
                )
            ftype = _PY_TO_ARCPY.get(type(sample), "TEXT")

        if ftype == "TEXT" and length is None:
            observed = [len(str(r[col])) for r in rows if r[col] is not None]
            length = max(observed) if observed else _DEFAULT_TEXT_LEN

        resolved.append((name, ftype, length))

    if arcpy.Exists(str(out_table)):
        if not overwrite:
            raise ValueError(
                f"Table already exists: {out_table}. "
                "Pass overwrite=True to replace it."
            )
        arcpy.management.Delete(str(out_table))

    arcpy.management.CreateTable(out_ws, out_name)

    for name, ftype, length in resolved:
        if ftype == "TEXT":
            arcpy.management.AddField(str(out_table), name, ftype, field_length=length)
        else:
            arcpy.management.AddField(str(out_table), name, ftype)

    field_names = [name for name, _, _ in resolved]
    with arcpy.da.InsertCursor(str(out_table), field_names) as cursor:
        for r in rows:
            cursor.insertRow(tuple(r))

    # arcpy.AddMessage(f"Created table {out_table} with {len(rows)} row(s).")
    return str(out_table)


def add_rows(target_table: _PathLike, rows: list,
             fields: Union[str, list]) -> int:
    """
    Append rows of Python data to an existing table or feature class.

    The row-shape complement of :func:`from_rows`: where ``from_rows`` creates a
    new table, ``add_rows`` writes into one that already exists, via an
    ``arcpy.da.InsertCursor``. The target must already have the fields named in
    ``fields``; create them first with ``arcsmith.flds.add_fld`` if needed.

    ``rows`` takes the same shapes ``from_rows`` accepts: a list of tuples/lists
    (one per row, aligned to ``fields``), or, for a single field, a flat list of
    scalars. Values are written positionally, so each row must line up with
    ``fields`` in order and type.

    Parameters
    ----------
    target_table : str or Path
        Existing table or feature class to append to. Edited in place.
    rows : list
        Rows to append. A list of tuples/lists aligned to ``fields``, or a flat
        list of scalars when ``fields`` names a single column.
    fields : str or list of str
        Field name(s) the row values map to, in order. Matched
        case-insensitively. A single name may be passed without a list. Cursor
        tokens such as ``'SHAPE@'`` are passed through unchanged, so geometry
        can be written alongside attributes.

    Returns
    -------
    int
        The number of rows appended.

    Raises
    ------
    ValueError
        If any name in ``fields`` is not found in ``target_table`` (cursor
        tokens are exempt), if ``rows`` is a flat scalar list but more than one
        field was given, or if a row's width does not match the field count.

    Examples
    --------
    Append rows to a multi-column table:

    >>> rows = [("TM", "Two Medicine"), ("CB", "Cut Bank")]
    >>> arcsmith.tbl.add_rows("C:/data/glacier.gdb/areas", rows, ["AREA_CODE", "AREA_NAME"])
    2

    Append to a single column from a flat list of scalars:

    >>> arcsmith.tbl.add_rows(areas, ["GL", "NF"], "AREA_CODE")
    2

    Append a point feature with geometry:

    >>> pt = arcpy.PointGeometry(arcpy.Point(-113.7, 48.7))
    >>> arcsmith.tbl.add_rows(sightings, [("Mountain Goat", pt)], ["SPECIES", "SHAPE@"])
    1
    """
    target_table = str(target_table)
    field_list = [fields] if isinstance(fields, str) else list(fields)

    # Validate ordinary field names; let cursor tokens (e.g. SHAPE@) through.
    existing = {f.name.lower(): f.name for f in arcpy.ListFields(target_table)}
    unknown = [f for f in field_list
               if "@" not in f and f.lower() not in existing]
    if unknown:
        raise ValueError(
            f"Field(s) not found in {target_table}: {unknown}. Check spelling, "
            "or add them first with arcsmith.flds.add_fld."
        )
    resolved = [f if "@" in f else existing[f.lower()] for f in field_list]

    # Accept a flat list of scalars for a single column, like from_rows.
    single_col = len(resolved) == 1
    if rows and not isinstance(rows[0], (tuple, list)):
        if not single_col:
            raise ValueError(
                "rows is a flat list of scalars but multiple fields were given; "
                "pass a list of tuples to populate more than one column."
            )
        rows = [(r,) for r in rows]

    # Validate row width against field count.
    for r in rows:
        if len(r) != len(resolved):
            raise ValueError(
                f"Row {r!r} has {len(r)} value(s) but {len(resolved)} field(s) "
                "were given."
            )

    count = 0
    with arcpy.da.InsertCursor(target_table, resolved) as cursor:
        for r in rows:
            cursor.insertRow(tuple(r))
            count += 1

    # arcpy.AddMessage(f"Appended {count} row(s) to {target_table}.")
    return count


def join_lookup(input_fc: _PathLike, key_field: str,
                mapping: Union[dict, Iterable], out_field: str,
                field_type: _FieldType,
                default: Any = None, length: Optional[int] = None,
                overwrite: bool = False) -> dict[str, int]:
    """
    Add a field and populate it from a 1:1 lookup keyed on an existing field.

    This is the fast, table-free form of a join: for each row, the value in
    ``key_field`` is looked up in ``mapping`` and written to ``out_field`` via an
    ``UpdateCursor``. It pairs directly with
    :func:`arcsmith.flds.unique_values`. Pull the distinct keys, build a
    ``{key: value}`` dict in caller code, and merge it back in one call.

    For one-to-many relationships, or to transfer several columns from an
    existing table, use :func:`join_table` instead. A dict cannot represent
    those.

    Parameters
    ----------
    input_fc : str or Path
        Feature class (or table) to add the field to. Edited in place.
    key_field : str
        Existing field whose values are looked up in ``mapping``. Matched
        case-insensitively by name; the cell *values* must match the dict keys
        by type (e.g. integer keys for a ``LONG`` field; see Notes).
    mapping : dict or iterable of (key, value)
        The lookup. A ``dict`` is used directly; any other iterable is treated
        as ``(key, value)`` pairs and converted (last pair wins on duplicates).
    out_field : str
        Name of the field to create and populate. If it already exists, see
        ``overwrite``.
    field_type : str
        arcpy field type for ``out_field`` (``"TEXT"``, ``"SHORT"``, ``"LONG"``,
        ``"FLOAT"``, ``"DOUBLE"``, ``"DATE"``). Used when the field is created;
        when an existing field is reused (``overwrite=True``) its on-disk type
        is kept and a warning is raised if it differs from ``field_type``.
    default : optional
        Value written to ``out_field`` when a row's key is absent from
        ``mapping``. Default ``None`` (leaves the cell ``NULL``). Pass e.g.
        ``"N/A"`` to mirror the canonical-blank convention of
        :func:`arcsmith.flds.clean_blanks`.
    length : int, optional
        Field length, used only when ``field_type`` is ``"TEXT"`` and the field
        is being created. Default ``None`` (arcpy's default length).
    overwrite : bool, optional
        Controls behavior when ``out_field`` already exists. If ``False``
        (default), a ``ValueError`` is raised. If ``True``, the existing field
        is reused and repopulated (its type is not changed).

    Returns
    -------
    dict of {str: int}
        ``{"matched": n, "unmatched": m}``. The values report how many rows found a key in
        ``mapping`` versus fell back to ``default``.

    Raises
    ------
    ValueError
        If ``key_field`` is not found in ``input_fc``, or if ``out_field``
        exists and ``overwrite`` is ``False``.

    Notes
    -----
    Key matching is by value and is *not* coerced: if ``key_field`` holds
    strings but the dict keys are integers, every row falls to ``default``. When
    no row matches anything, a warning is raised flagging a likely key-type
    mismatch, the most common cause of a silently empty join.

    Examples
    --------
    The full unique-values loop:

    >>> area_codes = arcsmith.flds.unique_values(fc, "AREA_CODE")
    >>> area_name = {s: area_name_for(s) for s in area_codes}      # caller's logic
    >>> counts = arcsmith.tbl.join_lookup(
    ...     fc, "AREA_CODE", area_name, "AREA_NAME", "TEXT", default="Unknown",
    ... )
    >>> arcpy.AddMessage(f"{counts['unmatched']} row(s) had no area name.")

    From a list of pairs rather than a dict:

    >>> pairs = [(1, "Low"), (2, "Medium"), (3, "High")]
    >>> arcsmith.tbl.join_lookup(fc, "BEAR_RISK", pairs, "BEAR_RISK_LABEL", "TEXT")

    Attach lodging/boat capacity to named facilities:

    >>> capacity = {"Lake McDonald Lodge": 82, "East Glacier Lodge": 161,
    ...             "St. Mary Lake Boats": 49}
    >>> arcsmith.tbl.join_lookup(landmarks, "NAME", capacity, "CAPACITY", "SHORT")
    """
    input_fc = str(input_fc)

    # Resolve key_field to its real casing (and validate existence).
    fields_by_lower = {f.name.lower(): f for f in arcpy.ListFields(input_fc)}
    if key_field.lower() not in fields_by_lower:
        raise ValueError(
            f"Field '{key_field}' not found in {input_fc}. "
            "Check spelling or pass the correct key field."
        )
    key_resolved = fields_by_lower[key_field.lower()].name

    if not isinstance(mapping, dict):
        mapping = dict(mapping)

    # Create out_field, or reuse it if overwrite is set.
    out_exists = out_field.lower() in fields_by_lower
    if out_exists:
        if not overwrite:
            raise ValueError(
                f"Field '{out_field}' already exists in {input_fc}. "
                "Pass overwrite=True to repopulate it."
            )
        existing = fields_by_lower[out_field.lower()]
        if _ADDFIELD_TYPE.get(existing.type, existing.type) != field_type:
            arcpy.AddWarning(
                f"join_lookup: existing field '{out_field}' is type "
                f"'{existing.type}', not the requested '{field_type}'. "
                "Reusing it as-is. Its type is not changed. Drop the field "
                "first if you need a different type."
            )
        out_resolved = existing.name
    else:
        if field_type == "TEXT" and length is not None:
            arcpy.management.AddField(input_fc, out_field, field_type, field_length=length)
        else:
            arcpy.management.AddField(input_fc, out_field, field_type)
        out_resolved = out_field

    matched = 0
    unmatched = 0
    with arcpy.da.UpdateCursor(input_fc, [key_resolved, out_resolved]) as cursor:
        for row in cursor:
            if row[0] in mapping:
                row[1] = mapping[row[0]]
                matched += 1
            else:
                row[1] = default
                unmatched += 1
            cursor.updateRow(row)

    if matched == 0 and unmatched > 0:
        arcpy.AddWarning(
            f"join_lookup: no rows matched any key in 'mapping'. Check that the "
            f"values in '{key_resolved}' match the dict key type "
            "(e.g. string keys for a text field, integer keys for a numeric one)."
        )

    # arcpy.AddMessage(
    #     f"join_lookup: populated '{out_field}': {matched} matched, "
    #     f"{unmatched} unmatched."
    # )
    return {"matched": matched, "unmatched": unmatched}


def join_table(input_fc: _PathLike, in_field: str, source_table: _PathLike,
               join_field: str, fields: Optional[list[str]] = None,
               keep: bool = True) -> str:
    """
    Join an external table to a feature class permanently, copying its columns in.

    Wraps ``arcpy.management.JoinField``: the selected columns from
    ``source_table`` are written into ``input_fc`` and persist on disk. Use this
    (rather than :func:`join_lookup`) when the lookup already exists as a table,
    or when you want to transfer several columns in one operation.

    The source may be any table arcpy can read, such as a geodatabase table, a feature
    class, or an on-disk table like a dBASE (``.dbf``) or CSV, so a crosswalk
    does not have to be imported first. To build a source from in-memory Python
    data, create it with :func:`from_rows` and pass it here.

    Each input row receives a single set of values from ``source_table``;
    ``JoinField`` does not multiply input rows. When an input row matches more
    than one join row, only one match is transferred rather than the row being
    duplicated. Preserving *every* match is the virtual ``AddJoin``-then-export
    route, which is deliberately out of scope here (it would break the package's
    "creation returns a path" contract); drop down to ``arcpy`` if you need it.

    Parameters
    ----------
    input_fc : str or Path
        Target feature class (the "left" side of the join). Edited in place.
    in_field : str
        Field in ``input_fc`` to join on. Matched case-insensitively.
    source_table : str or Path
        Table or feature class supplying the new columns.
    join_field : str
        Field in ``source_table`` to match against ``in_field``. Matched
        case-insensitively.
    fields : list of str, optional
        Field names from ``source_table`` to act on. When ``keep=True``
        (default) these are the columns to transfer; all others are skipped.
        When ``keep=False`` these are the columns to skip; all other
        transferable columns are brought across. Name the few to drop rather
        than the many to keep. Non-transferable system fields (OID, geometry,
        Global ID) are never transferred either way. To drop the redundant join
        key when the keys are named differently, include ``join_field`` here
        with ``keep=False``. Default ``None`` (all transferable columns).
    keep : bool, optional
        If ``True`` (default), ``fields`` specifies what to transfer. If
        ``False``, ``fields`` specifies what to skip. Ignored when ``fields``
        is ``None``.

    Returns
    -------
    str
        The ``input_fc`` path (as ``str``), now carrying the joined columns.

    Raises
    ------
    ValueError
        If ``in_field`` is not found in ``input_fc``; if ``join_field`` is not
        found in ``source_table``; if a name in ``fields`` is not found in
        ``source_table``; or if the resolved field list is empty (e.g.
        ``keep=False`` drops every transferable column, or ``keep=True`` is
        given an empty list).

    Notes
    -----
    ``JoinField`` builds an index on each call, so it is well suited to the
    deliverable-grade joins this is meant for but slow inside a hot loop over
    many small joins.

    Examples
    --------
    Copy an area name onto every trail:

    >>> arcsmith.tbl.join_table(
    ...     trails, "AREA_CODE", areas_tbl, "AREA_CODE", ["AREA_NAME"],
    ... )

    Build a crosswalk from Python data, then join it:

    >>> rows = [("NF", "North Fork"), ("LM", "Lake McDonald"), ("MG", "Many Glacier")]
    >>> xwalk = arcsmith.tbl.from_rows(
    ...     f"{arcsmith.ws.temp_space()}/area_xwalk", rows, ["AREA_CODE", "AREA_NAME"],
    ... )
    >>> arcsmith.tbl.join_table(trails, "AREA_CODE", xwalk, "AREA_CODE", ["AREA_NAME"])

    Keep everything from a wide table except a few columns (and the join key):

    >>> arcsmith.tbl.join_table(
    ...     trails, "AREA_CODE", area_info, "AREA_CODE",
    ...     fields=["AREA_CODE", "CENTROID_LAT", "CENTROID_LON", "STATUS_CODE"], keep=False,
    ... )
    """
    input_fc = str(input_fc)
    source_table = str(source_table)

    # Validate the join keys exist (case-insensitive), matching house style.
    in_fields = {f.name.lower() for f in arcpy.ListFields(input_fc)}
    if in_field.lower() not in in_fields:
        raise ValueError(
            f"Field '{in_field}' not found in {input_fc}. "
            "Check spelling or pass the correct join field."
        )

    src_field_objs = arcpy.ListFields(source_table)
    src_lower = {f.name.lower(): f.name for f in src_field_objs}
    if join_field.lower() not in src_lower:
        raise ValueError(
            f"Field '{join_field}' not found in {source_table}. "
            "Check spelling or pass the correct join field."
        )

    if fields is None:
        transfer = None  # JoinField-native: all transferable fields.
    else:
        unknown = [f for f in fields if f.lower() not in src_lower]
        if unknown:
            raise ValueError(
                f"Field(s) not found in {source_table}: {unknown}. "
                "Check spelling or remove them from 'fields'."
            )
        if keep:
            transfer = list(fields)
        else:
            drop = {f.lower() for f in fields}
            transfer = [
                f.name for f in src_field_objs
                if f.type not in _NON_TRANSFERABLE_TYPES
                and f.name.lower() not in drop
            ]
        if not transfer:
            raise ValueError(
                f"The resolved field list for {source_table} is empty; no "
                "columns would be joined. Check 'fields' and 'keep'."
            )

    arcpy.management.JoinField(input_fc, in_field, source_table, join_field, transfer)
    n_msg = "all" if transfer is None else str(len(transfer))
    # arcpy.AddMessage(
    #     f"join_table: joined {source_table} into {input_fc} on "
    #     f"{in_field} = {join_field} ({n_msg} field(s) transferred)."
    # )
    return input_fc


# --------------------------------------------------------------------------- #
# Map-TOC operations for standalone tables.
#
# A standalone table is a distinct kind of map content from a layer: it lives
# in ``Map.listTables()`` (not ``listLayers()``) and is removed with
# ``Map.removeTable()`` (not ``removeLayer()``). These are the table twins of
# the layer operations in arcsmith.lyr (add / remove / get).
# --------------------------------------------------------------------------- #


def _is_memory_path(table_src):
    """True when table_src targets the in-memory workspace ('memory' or 'in_memory').

    arcpy in-memory paths are Windows-style (``memory\\areas``), so parsing is
    done with ``PureWindowsPath`` to split on both ``\\`` and ``/`` regardless of
    the OS this happens to run on.
    """
    parts = PureWindowsPath(str(table_src)).parts
    return bool(parts) and parts[0].lower() in ("memory", "in_memory")


def _match_tables(target_map, table_name=None, table_source=None):
    """
    Find standalone tables in the map by display name or data source path.

    Validates the name/source arguments and returns matching tables without
    raising on an empty result, so callers can decide how to handle "not found"
    (raise, or return quietly). Matching by ``table_name`` returns all matches;
    matching by ``table_source`` returns at most the first match. Attribute
    reads that some tables do not support are guarded.
    """
    if (table_name is None) == (table_source is None):
        raise ValueError("Provide exactly one of 'table_name' or 'table_source'.")

    matched = []
    for tbl in target_map.listTables():
        if table_source is not None:
            # Table has no ``supports()`` (that is a Layer method); read
            # dataSource directly and guard against tables that lack one.
            try:
                source = tbl.dataSource
            except Exception:
                continue
            if source == str(table_source):
                matched.append(tbl)
                break
        elif tbl.name == table_name:
            matched.append(tbl)

    return matched


def _raise_table_not_found(table_name, table_source):
    """Raise a ``ValueError`` naming the criterion that matched no table."""
    identifier = table_name if table_name is not None else table_source
    raise ValueError(f"No standalone table matching '{identifier}' found in the map.")


def add_to_map(target_map: arcpy.mp.Map,
               table_src: Union[str, Path, arcpy.Result],
               table_name: Optional[str] = None) -> arcpy.mp.Table:
    """
    Add a standalone table to a map.

    Adds the table at ``table_src`` to ``target_map`` and returns the resulting
    table object. In-memory tables are handled automatically: a map cannot
    consume a dataset in the ``memory`` (or ``in_memory``) workspace directly,
    so such a source is first staged into a table view with
    ``arcpy.management.MakeTableView`` and that view is added to the map. An
    on-disk table is added directly.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to add the table to.
    table_src : str, Path, or arcpy.Result
        Path to the source table (geodatabase table, dBASE/CSV, in-memory
        table, etc.). ``arcpy.Result`` objects are accepted and resolved to
        their output path via ``str()``.
    table_name : str, optional
        Display name for the table in the map. Defaults to the source name.

    Returns
    -------
    arcpy.mp.Table
        The table object added to the map.

    Examples
    --------
    Add a geodatabase table to the active map:

    >>> aprx = arcpy.mp.ArcGISProject("CURRENT")
    >>> arcsmith.tbl.add_to_map(aprx.activeMap, "C:/data/glacier.gdb/areas")

    Materialize rows and show the result in the map:

    >>> rows = [("NF", "North Fork"), ("LM", "Lake McDonald")]
    >>> areas = arcsmith.tbl.from_rows("memory/areas", rows, ["AREA_CODE", "AREA_NAME"])
    >>> arcsmith.tbl.add_to_map(aprx.activeMap, areas, table_name="Area Names")
    """
    src = str(table_src)
    if _is_memory_path(src):
        # addDataFromPath can't consume an in-memory dataset; make a table view
        # from it first, then add that table object to the map.
        name = table_name or Path(src).stem
        made = arcpy.management.MakeTableView(src, name)
        tbl_obj = target_map.addTable(made.getOutput(0))
    else:
        tbl_obj = target_map.addDataFromPath(src)

    if table_name is not None:
        tbl_obj.name = table_name

    # arcpy.AddMessage(f"Added standalone table -> {tbl_obj.name}")
    return tbl_obj


def get(target_map: arcpy.mp.Map, table_name: Optional[str] = None,
        table_source: Optional[_PathLike] = None) -> list:
    """
    Retrieve standalone table(s) from a map by display name or data source path.

    When matching by ``table_name``, all tables with that name are returned.
    When matching by ``table_source``, only the first exact match is returned.
    Exactly one of ``table_name`` or ``table_source`` must be provided.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to search.
    table_name : str, optional
        Display name to match against; all matching tables are returned.
    table_source : str or Path, optional
        Data source path to match against; only the first exact match is
        returned.

    Returns
    -------
    list of arcpy.mp.Table
        All matching tables. When matching by ``table_source``, the list
        contains at most one entry.

    Raises
    ------
    ValueError
        If neither or both of ``table_name`` and ``table_source`` are provided,
        or if no matching table is found in the map.

    Examples
    --------
    Get every standalone table named "areas":

    >>> tables = arcsmith.tbl.get(target_map, table_name="areas")

    Get a single table by data source path:

    >>> tables = arcsmith.tbl.get(target_map, table_source="C:/data/glacier.gdb/areas")
    """
    matched = _match_tables(target_map, table_name=table_name,
                            table_source=table_source)
    if not matched:
        _raise_table_not_found(table_name, table_source)
    return matched


def remove_from_map(target_map: arcpy.mp.Map, table_name: Optional[str] = None,
                    table_source: Optional[_PathLike] = None,
                    silent: bool = False, *,
                    table: Optional[Union[arcpy.mp.Table, list]] = None) -> list:
    """
    Remove standalone table(s) from a map by reference, display name, or source.

    Three matching modes, exactly one of which must be used per call:

    * ``table``: removes the exact table object(s) given. No scan or name/source
      matching is performed.
    * ``table_name``: removes *all* standalone tables with that display name.
    * ``table_source``: removes only the *first* table with that data source.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to remove table(s) from.
    table_name : str, optional
        Display name to match against; all matching tables are removed.
    table_source : str or Path, optional
        Data source path to match against; only the first match is removed.
        Tables without a data source cannot be matched in this mode; match
        those by ``table_name`` instead.
    silent : bool, optional
        If ``True``, return an empty list instead of raising when a name/source
        match finds nothing. Invalid argument combinations still raise. Has no
        effect in ``table`` mode. Default ``False``.
    table : arcpy.mp.Table or list of arcpy.mp.Table, optional
        The exact table object(s) to remove. Keyword-only. Mutually exclusive
        with ``table_name`` and ``table_source``.

    Returns
    -------
    list of arcpy.mp.Table
        All tables that were removed.

    Raises
    ------
    ValueError
        If ``table`` is combined with ``table_name`` or ``table_source``, or if
        neither nor both of ``table_name``/``table_source`` are provided when
        ``table`` is omitted; or if a name/source match finds nothing and
        ``silent`` is ``False``.

    Examples
    --------
    Remove the exact table you grabbed:

    >>> areas = arcsmith.tbl.get(current_map, table_name="areas")[0]
    >>> arcsmith.tbl.remove_from_map(current_map, table=areas)

    Remove all tables named "scratch", quietly if none are present:

    >>> arcsmith.tbl.remove_from_map(current_map, table_name="scratch", silent=True)
    """
    if table is not None:
        if table_name is not None or table_source is not None:
            raise ValueError(
                "Provide 'table' alone, not with 'table_name' or 'table_source'."
            )
        tables = list(table) if isinstance(table, (list, tuple)) else [table]
        for tbl in tables:
            target_map.removeTable(tbl)
        return tables

    matched = _match_tables(target_map, table_name=table_name,
                            table_source=table_source)
    if not matched and not silent:
        _raise_table_not_found(table_name, table_source)

    for tbl in matched:
        target_map.removeTable(tbl)

    return matched