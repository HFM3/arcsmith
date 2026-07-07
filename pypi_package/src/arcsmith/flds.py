# ArcSmith: GIS toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Optional, Union
import arcpy

from ._types import _FieldType, _PathLike

__all__ = ["build_fld_map", "clean_blanks", "unique_values", "list_cols",
           "add_fld", "rename_fld", "del_fld"]

# Fields that arcpy manages internally and cannot be removed from a FieldMappings
# object. Any name in ``fields`` that matches one of these (case-insensitive)
# is silently left alone. The field will always be present in the output
# regardless.
_SYSTEM_FIELDS = {
    "objectid", "oid", "fid",
    "shape", "shape_length", "shape_area",
    "globalid",
}

# Strings that are treated as blank regardless of case or surrounding whitespace.
_BLANK_STRINGS = {"n/a", "na", "none", "null", "nil", "-", "--", "---"}


def _is_system(field_name):
    return field_name.lower() in _SYSTEM_FIELDS


def _resolve_keep(all_fields, fields, keep):
    """
    Return the set of non-system field names to retain in the output.

    Parameters
    ----------
    all_fields : list of str
        All non-system field names present in the source feature class.
    fields : list of str
        The field names supplied by the caller.
    keep : bool
        If ``True``, ``fields`` are the fields to retain; all others are
        removed. If ``False``, ``fields`` are the fields to remove; all
        others are retained.

    Returns
    -------
    set of str
        Field names (original casing from ``all_fields``) to retain.

    Raises
    ------
    ValueError
        If any name in ``fields`` is not found in ``all_fields``
        (system fields are silently ignored rather than raising an error).
    """
    # Build a case-insensitive lookup: lower-name -> original-name
    lookup = {f.lower(): f for f in all_fields}

    unknown = [f for f in fields
               if f.lower() not in lookup and not _is_system(f)]
    if unknown:
        raise ValueError(
            f"Field(s) not found in source: {unknown}. "
            "Check spelling or remove them from 'fields'."
        )

    if keep:
        return {lookup[f.lower()] for f in fields if f.lower() in lookup}
    else:
        drop_lower = {f.lower() for f in fields}
        return {f for f in all_fields if f.lower() not in drop_lower}


def build_fld_map(input_fc: _PathLike, fields: Optional[list[str]] = None,
                    keep: bool = True) -> arcpy.FieldMappings:
    """
    Build an ``arcpy.FieldMappings`` object that retains only a chosen
    subset of fields.

    Pass the relevant field names in ``fields`` and set ``keep`` to
    control whether they are included or excluded. System-managed fields
    (``OID``, ``Shape``, ``Shape_Length``, ``Shape_Area``, ``GlobalID``) are
    always preserved by arcpy and are silently ignored if listed in ``fields``.

    Parameters
    ----------
    input_fc : str or Path
        Path to the source feature class.
    fields : list of str, optional
        Field names to act on. When ``keep=True`` (default) these are the
        fields to retain; all others are removed. When ``keep=False`` these
        are the fields to remove; all others are kept. Pass ``[]`` with
        ``keep=True`` to retain geometry only (no attribute fields). Default
        ``None`` (all fields are retained; ``keep`` is ignored).
    keep : bool, optional
        If ``True`` (default), ``fields`` specifies what to keep.
        If ``False``, ``fields`` specifies what to drop.
        Ignored when ``fields`` is ``None``.

    Returns
    -------
    arcpy.FieldMappings
        A ``FieldMappings`` object ready to pass to
        ``arcpy.conversion.ExportFeatures`` or any other
        arcpy tool that accepts field mappings.

    Raises
    ------
    ValueError
        If any field name in ``fields`` does not exist in ``input_fc``
        (system fields are exempt from this check).

    Examples
    --------
    All fields (no filtering):

    >>> fm = arcsmith.flds.build_fld_map(input_fc)

    Keep only the fields that are needed:

    >>> fm = arcsmith.flds.build_fld_map(input_fc, ["NAME", "VISITS_2024", "AREA"])

    Drop unwanted fields and keep everything else:

    >>> fm = arcsmith.flds.build_fld_map(input_fc, ["CLOSURE_NOTE", "TEMP_FLAG"], keep=False)

    Geometry only (no attribute fields):

    >>> fm = arcsmith.flds.build_fld_map(input_fc, [])

    Pass the result straight to an arcpy export tool:

    >>> fm = arcsmith.flds.build_fld_map(input_fc, ["NAME", "TRAIL_STATUS"])
    >>> arcpy.conversion.ExportFeatures(input_fc, "path/to/out.gdb/park_boundary", field_mapping=fm)

    Or use export_fc as a shorthand for the same operation:

    >>> arcsmith.fc.export_fc(input_fc, "path/to/out.gdb/park_boundary", ["NAME", "TRAIL_STATUS"])
    """
    input_fc = str(input_fc)

    fm = arcpy.FieldMappings()
    fm.addTable(input_fc)

    # None means all fields, so return the full mapping unchanged
    if fields is None:
        return fm

    # Collect all non-system fields present in the source
    all_fields = [
        f.name for f in arcpy.ListFields(input_fc)
        if not _is_system(f.name)
    ]

    retain = _resolve_keep(all_fields, fields, keep)

    # Iterate in reverse so removing by index doesn't shift subsequent indices
    for i in range(fm.fieldCount - 1, -1, -1):
        field_map = fm.getFieldMap(i)
        name = field_map.outputField.name
        if not _is_system(name) and name not in retain:
            fm.removeFieldMap(i)

    return fm



def clean_blanks(input_fc: _PathLike, fields: Union[str, list[str]],
                 output_fc: Optional[_PathLike] = None,
                 blank_value: str = "N/A") -> dict[str, int]:
    """
    Standardize blank-like values in string fields to a single canonical value.

    Scans every row in ``input_fc`` for cells that are blank or blank-like and
    replaces them with ``blank_value``. A cell is considered blank-like if it is:

    * ``None`` / SQL ``NULL``
    * An empty string ``""``
    * A whitespace-only string (e.g. ``"   "``)
    * A case-insensitive match (after stripping whitespace) for any of:
      ``"N/A"``, ``"NA"``, ``"None"``, ``"Null"``, ``"Nil"``, ``"-"``,
      ``"--"``, ``"---"``

    Only fields whose type is ``String`` are eligible; any non-string field
    in ``fields`` is skipped with a warning via ``arcpy.AddWarning``.

    Parameters
    ----------
    input_fc : str or Path
        Path to the feature class to process.
    fields : str or list of str
        Field name(s) to clean. A single name may be passed without a list.
    output_fc : str or Path, optional
        If provided, ``input_fc`` is first copied to ``output_fc`` and the
        cleaning is performed on the copy. ``input_fc`` is left unchanged.
        If ``None`` (default), rows are edited in-place.
    blank_value : str, optional
        The canonical replacement for blank-like cells. Default ``"N/A"``.

    Returns
    -------
    dict of {str: int}
        Maps each cleaned field name to the number of cells that were
        replaced. Fields that were skipped (non-string type) are not
        included.

    Raises
    ------
    ValueError
        If any name in ``fields`` does not exist in ``input_fc``.

    Examples
    --------
    Clean in-place:

    >>> counts = arcsmith.flds.clean_blanks(input_fc, "TRAIL_STATUS")

    Clean a copy, leaving the original unchanged:

    >>> counts = arcsmith.flds.clean_blanks(input_fc, "TRAIL_STATUS", output_fc="C:/data/glacier.gdb/trails_clean")

    Clean multiple fields with a custom replacement:

    >>> counts = arcsmith.flds.clean_blanks(
    ...     input_fc, ["TRAIL_STATUS", "CLOSURE_NOTE", "TRAIL_TYPE"],
    ...     blank_value="Unknown",
    ...     output_fc="C:/data/glacier.gdb/trails_clean",
    ... )

    Use the return value to report how many cells were standardized:

    >>> for field, n in counts.items():
    ...     arcpy.AddMessage(f"{field}: {n} blank(s) replaced")
    """
    if isinstance(fields, str):
        fields = [fields]

    if output_fc is not None:
        arcpy.management.CopyFeatures(str(input_fc), str(output_fc))
        target_fc = str(output_fc)
        # arcpy.AddMessage(f"Copied '{input_fc}' -> {output_fc}")
    else:
        target_fc = str(input_fc)

    # Validate all field names and separate string from non-string fields
    field_lookup = {f.name.lower(): f for f in arcpy.ListFields(target_fc)}
    unknown = [f for f in fields if f.lower() not in field_lookup]
    if unknown:
        raise ValueError(
            f"Field(s) not found in {target_fc}: {unknown}. "
            "Check spelling or remove them from 'fields'."
        )

    string_fields = []
    for name in fields:
        field_obj = field_lookup[name.lower()]
        if field_obj.type != "String":
            arcpy.AddWarning(
                f"clean_blanks: '{name}' is type '{field_obj.type}', not String. Skipped."
            )
        else:
            string_fields.append(field_obj.name)

    if not string_fields:
        return {}

    counts = {f: 0 for f in string_fields}

    with arcpy.da.UpdateCursor(target_fc, string_fields) as cursor:
        for row in cursor:
            new_row = list(row)
            changed = False
            for i, val in enumerate(row):
                if val is None:
                    is_blank = True
                elif isinstance(val, str):
                    stripped = val.strip()
                    is_blank = stripped == "" or stripped.lower() in _BLANK_STRINGS
                else:
                    is_blank = False

                if is_blank:
                    new_row[i] = blank_value
                    counts[string_fields[i]] += 1
                    changed = True

            if changed:
                cursor.updateRow(new_row)

    return counts


def unique_values(input_fc: _PathLike, fields: Union[str, list[str]],
                  sort: bool = True, max_rows: Optional[int] = None) -> list:
    """
    Return the unique values (or unique value combinations) present in one or
    more fields.

    A single field name returns a flat list of distinct values. Two or more
    field names return a list of tuples, one tuple per unique combination of
    values across those fields, in the order the fields are listed.

    ``None`` (SQL ``NULL``) is included as a distinct value when it appears in
    the data.

    Parameters
    ----------
    input_fc : str or Path
        Path to the source feature class.
    fields : str or list of str
        Field name(s) to inspect. Pass a single string for one field or a list
        for multi-field combinations. Field names are matched
        case-insensitively.
    sort : bool, optional
        If ``True`` (default), the result is sorted. For a single field the
        values are sorted directly; ``None`` sorts before all other values. For
        multiple fields the tuples are sorted lexicographically, with ``None``
        sorting first within each position. Set ``False`` to preserve insertion
        order (i.e. the order combinations are first encountered while scanning
        the table).
    max_rows : int, optional
        If given, stop scanning after this many rows have been read. This
        bounds the cost of the table scan on large datasets. The result may
        be incomplete: only values present within the first ``max_rows`` rows
        are returned, so distinct values that occur only in later rows are
        missed. Values are still de-duplicated and (optionally) sorted within
        the scanned portion. ``None`` (default) scans the entire table.

    Returns
    -------
    list
        * **Single field** -- ``list`` of distinct values (any type).
        * **Multiple fields** -- ``list`` of ``tuple``, one per unique
          combination, each tuple aligned to the order of ``fields``.

    Raises
    ------
    ValueError
        If any name in ``fields`` does not exist in ``input_fc``.

    Examples
    --------
    Unique values from a single field:

    >>> arcsmith.flds.unique_values(landmarks, "NAME")
    ['East Glacier Lodge', 'Lake McDonald Lodge', 'St. Mary Lake Boats']

    Unique combinations across two fields:

    >>> arcsmith.flds.unique_values(input_fc, ["AREA_CODE", "SUBAREA"])
    [('MG', 'Swiftcurrent'), ('TM', 'Cut Bank'), ('TM', 'Two Medicine')]

    Skip sorting to keep insertion order:

    >>> arcsmith.flds.unique_values(input_fc, "TRAIL_STATUS", sort=False)

    Cap the scan on a large table (result may be incomplete):

    >>> arcsmith.flds.unique_values(input_fc, "TRAIL_STATUS", max_rows=10000)

    Feed directly into a dropdown filter:

    >>> values = arcsmith.flds.unique_values(input_fc, "TRAIL_TYPE")
    >>> arcsmith.param.drop_populate(parameters[1], [str(v) for v in values])
    """
    if isinstance(fields, str):
        fields = [fields]

    input_fc = str(input_fc)

    # Validate field names case-insensitively
    field_lookup = {f.name.lower(): f.name for f in arcpy.ListFields(input_fc)}
    unknown = [f for f in fields if f.lower() not in field_lookup]
    if unknown:
        raise ValueError(
            f"Field(s) not found in {input_fc}: {unknown}. "
            "Check spelling or remove them from 'fields'."
        )

    # Resolve to original casing so arcpy is happy
    resolved = [field_lookup[f.lower()] for f in fields]
    single = len(resolved) == 1

    seen = set()
    result = []

    with arcpy.da.SearchCursor(input_fc, resolved) as cursor:
        for i, row in enumerate(cursor):
            if max_rows is not None and i >= max_rows:
                break
            value = row[0] if single else tuple(row)
            if value not in seen:
                seen.add(value)
                result.append(value)

    if sort:
        # None is not directly comparable to str/int in Python 3, so we sort
        # with a key that places None before all other values.
        if single:
            result.sort(key=lambda v: (v is not None, v))
        else:
            result.sort(key=lambda t: tuple((v is not None, v) for v in t))

    return result


def list_cols(input_fc: _PathLike, include_system: bool = False, *,
              include_oid: bool = False) -> list[str]:
    """
    Return the field names present in a feature class.

    By default, only user-defined fields are returned. Pass
    ``include_system=True`` to also include system-managed fields such as
    ``OID``, ``Shape``, ``Shape_Length``, ``Shape_Area``, and ``GlobalID``.

    Pass ``include_oid=True`` to add only the Object ID field to the
    user-defined fields, while still excluding the other system fields. This
    suits a dropdown where the user picks a unique-identifier field: the OID is
    the dependable fallback when a dataset has no user-defined ID, but it is
    rarely a useful choice for grouping, so it is opt-in rather than default.
    The OID is matched by field type, so it is found whatever it is named
    (``OBJECTID``, ``FID``, ``OID``).

    Parameters
    ----------
    input_fc : str or Path
        Path to the source feature class.
    include_system : bool, optional
        If ``False`` (default), system-managed fields are excluded.
        If ``True``, all fields are returned.
    include_oid : bool, optional
        If ``True``, the Object ID field is included alongside the user-defined
        fields even when ``include_system`` is ``False``. Keyword-only. Default
        ``False``. Has no effect when ``include_system`` is ``True`` (which
        already includes it).

    Returns
    -------
    list of str
        Field names in the order arcpy reports them.

    Examples
    --------
    List user-defined fields:

    >>> arcsmith.flds.list_cols(input_fc)
    ['TRAIL_ID', 'MAINTAINER', 'TRAIL_STATUS', 'LENGTH_MI']

    Include the Object ID for an ID-field dropdown:

    >>> arcsmith.flds.list_cols(input_fc, include_oid=True)
    ['OBJECTID', 'TRAIL_ID', 'MAINTAINER', 'TRAIL_STATUS', 'LENGTH_MI']

    Include every system field:

    >>> arcsmith.flds.list_cols(input_fc, include_system=True)
    ['OBJECTID', 'Shape', 'TRAIL_ID', 'MAINTAINER', 'TRAIL_STATUS', 'LENGTH_MI', 'Shape_Length', 'Shape_Area']

    Feed directly into a dropdown:

    >>> arcsmith.param.drop_populate(parameters[1], arcsmith.flds.list_cols(parameters[0].valueAsText))
    """
    return [
        f.name for f in arcpy.ListFields(str(input_fc))
        if include_system
        or not _is_system(f.name)
        or (include_oid and f.type == "OID")
    ]


def add_fld(input_fc: _PathLike, field: str, field_type: _FieldType, *,
              length: Optional[int] = None, alias: Optional[str] = None) -> str:
    """
    Add a new field to a feature class or table in place.

    Wraps ``arcpy.management.AddField``. The field is created empty; populate it
    afterward with an ``UpdateCursor``, ``arcsmith.tbl.join_lookup``, or
    ``arcsmith.flds.clean_blanks``. ``length`` sizes a ``TEXT`` field and is
    ignored for other types. ``alias`` sets the field's display alias; without
    it the alias defaults to the field name.

    Parameters
    ----------
    input_fc : str or Path
        Feature class or table to add the field to. Edited in place.
    field : str
        Name of the new field.
    field_type : {'TEXT', 'SHORT', 'LONG', 'FLOAT', 'DOUBLE', 'DATE'}
        arcpy field type for the new field.
    length : int, optional
        Field length, used only when ``field_type`` is ``'TEXT'``. Keyword-only.
        Default ``None`` (arcpy's default length).
    alias : str, optional
        Display alias for the field. Keyword-only. Default ``None`` (the alias
        matches the field name).

    Returns
    -------
    str
        The ``input_fc`` path (as ``str``), now carrying the new field.

    Raises
    ------
    ValueError
        If a field named ``field`` already exists in ``input_fc``.

    Examples
    --------
    Add a text field sized to 50 characters:

    >>> arcsmith.flds.add_fld(trails, "TRAIL_NOTE", "TEXT", length=50)

    Add a numeric field with a friendly alias:

    >>> arcsmith.flds.add_fld(trails, "VISITS_2024", "LONG", alias="2024 Visits")
    """
    input_fc = str(input_fc)

    existing = {f.name.lower() for f in arcpy.ListFields(input_fc)}
    if field.lower() in existing:
        raise ValueError(
            f"Field '{field}' already exists in {input_fc}. Pick a different "
            "name, or remove it first with del_fld."
        )

    arcpy.management.AddField(input_fc, field, field_type,
                              field_length=length, field_alias=alias)
    # arcpy.AddMessage(f"Added field '{field}' ({field_type}) to {input_fc}.")
    return input_fc


def rename_fld(input_fc: _PathLike, field: str, new_name: str, *,
                 new_alias: Optional[str] = None) -> str:
    """
    Rename a field, and optionally its alias, in place.

    Wraps ``arcpy.management.AlterField``. The existing field is matched
    case-insensitively and renamed to ``new_name``, preserving its data; pass
    ``new_alias`` to also change the display alias.

    Not every data source supports renaming. ``AlterField`` cannot rename a
    required or system-managed field, and some formats such as shapefiles do
    not allow it at all; arcpy raises in those cases.

    Parameters
    ----------
    input_fc : str or Path
        Feature class or table containing the field. Edited in place.
    field : str
        Existing field to rename. Matched case-insensitively.
    new_name : str
        New name for the field.
    new_alias : str, optional
        New display alias. Keyword-only. Default ``None`` (the alias is left
        unchanged).

    Returns
    -------
    str
        The ``input_fc`` path (as ``str``).

    Raises
    ------
    ValueError
        If ``field`` is not found in ``input_fc``.

    Examples
    --------
    Rename a field:

    >>> arcsmith.flds.rename_fld(trails, "TRL_STAT", "TRAIL_STATUS")

    Rename a field and set a readable alias:

    >>> arcsmith.flds.rename_fld(trails, "VIS24", "VISITS_2024", new_alias="2024 Visits")
    """
    input_fc = str(input_fc)

    field_lookup = {f.name.lower(): f.name for f in arcpy.ListFields(input_fc)}
    if field.lower() not in field_lookup:
        raise ValueError(
            f"Field '{field}' not found in {input_fc}. Check spelling."
        )
    resolved = field_lookup[field.lower()]

    arcpy.management.AlterField(input_fc, resolved, new_field_name=new_name,
                                new_field_alias=new_alias)
    # arcpy.AddMessage(f"Renamed field '{resolved}' to '{new_name}' in {input_fc}.")
    return input_fc


def del_fld(input_fc: _PathLike, fields: Union[str, list]) -> str:
    """
    Delete one or more fields from a feature class or table in place.

    Wraps ``arcpy.management.DeleteField``. Field names are matched
    case-insensitively. System-managed fields (``OID``, ``Shape``,
    ``Shape_Length``, ``Shape_Area``, ``GlobalID``) cannot be deleted and are
    rejected with a clear error rather than handed to arcpy.

    Parameters
    ----------
    input_fc : str or Path
        Feature class or table to delete fields from. Edited in place.
    fields : str or list of str
        Field name(s) to delete. A single name may be passed without a list.

    Returns
    -------
    str
        The ``input_fc`` path (as ``str``).

    Raises
    ------
    ValueError
        If any name in ``fields`` is not found in ``input_fc``, or names a
        system-managed field.

    Examples
    --------
    Delete a single field:

    >>> arcsmith.flds.del_fld(trails, "TEMP_FLAG")

    Delete several at once:

    >>> arcsmith.flds.del_fld(trails, ["TEMP_FLAG", "LEGACY_CODE", "SCRATCH"])
    """
    input_fc = str(input_fc)
    field_list = [fields] if isinstance(fields, str) else list(fields)

    field_lookup = {f.name.lower(): f.name for f in arcpy.ListFields(input_fc)}
    unknown = [f for f in field_list if f.lower() not in field_lookup]
    if unknown:
        raise ValueError(
            f"Field(s) not found in {input_fc}: {unknown}. Check spelling."
        )

    system = [f for f in field_list if _is_system(f)]
    if system:
        raise ValueError(
            f"Cannot delete system-managed field(s): {system}. Fields like "
            "OID, Shape, and GlobalID are required by arcpy."
        )

    resolved = [field_lookup[f.lower()] for f in field_list]
    arcpy.management.DeleteField(input_fc, resolved)
    # arcpy.AddMessage(f"Deleted {len(resolved)} field(s) from {input_fc}: {resolved}.")
    return input_fc