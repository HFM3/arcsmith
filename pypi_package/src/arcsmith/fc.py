# ArcSmith: GIS toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import Literal, Optional, Union
import arcpy
from pathlib import Path
from .flds import build_fld_map

from ._types import _PathLike

__all__ = ["build_where", "build_where_in", "get_area", "validate_geom_type", "export_fc"]

# Closed, case-sensitive set of linear units get_area can convert to (keys of
# _TO_METERS below). Literal gives editor autocomplete and static typo checks.
_LinearUnit = Literal["Meter", "Kilometer", "Foot_US", "Foot",
                      "Mile_US", "Nautical_Mile", "Yard"]

# Field types whose values must be quoted in a SQL expression.
_QUOTED_TYPES = {"String", "Guid", "Date"}


def _sql_quote(value):
    """
    Render ``value`` as a single-quoted SQL literal with embedded quotes escaped.

    Doubles any single quote per the SQL standard, so a value such as
    ``St. Mary's`` becomes the literal ``'St. Mary''s'`` rather than the
    malformed ``'St. Mary's'``. ``value`` is coerced to ``str`` first, matching how it is
    ultimately written into the clause.
    """
    return "'" + str(value).replace("'", "''") + "'"


# Conversion factors from each linear unit to meters (area factor = linear ** 2).
# Keys match arcpy spatialReference.linearUnitName values.
_TO_METERS = {
    "Meter":          1.0,
    "Kilometer":      1_000.0,
    "Foot_US":        0.304800609601,
    "Foot":           0.3048,
    "Mile_US":        1_609.347219,
    "Nautical_Mile":  1_852.0,
    "Yard":           0.9144,
}


def get_area(polygon_fc: _PathLike,
             output_units: Optional[_LinearUnit] = None) -> tuple[float, str]:
    """
    Return the area of a polygon feature class and the unit name.

    Sums ``SHAPE@AREA`` across every feature in the feature class, which arcpy
    always returns in the spatial reference's native linear units squared. A
    single-feature (e.g. dissolved) input therefore returns that feature's
    area; a multi-feature input returns the combined total. If ``output_units``
    is provided the area is converted to that unit system before being returned.

    Parameters
    ----------
    polygon_fc : str or Path
        Path to the polygon feature class.
    output_units : str, optional
        Linear unit name to convert the area into. Must be one of:
        ``'Meter'``, ``'Kilometer'``, ``'Foot_US'``, ``'Foot'``,
        ``'Mile_US'``, ``'Nautical_Mile'``, ``'Yard'``.
        Case-sensitive. Default ``None`` (return native units unchanged).

    Returns
    -------
    area : float
        Area of the polygon in the requested (or native) units squared.
    units : str
        Name of the units the returned area is expressed in.

    Raises
    ------
    ValueError
        If ``output_units`` is not a recognized unit name.
    ValueError
        If ``polygon_fc`` contains no features.
    ValueError
        If ``output_units`` is requested but the source's native units are not
        a recognized linear unit (e.g. the data is in a geographic coordinate
        system), so a conversion factor cannot be determined.

    Examples
    --------
    Native units:

    >>> area, units = arcsmith.fc.get_area("path/to/glaciers.shp")
    >>> arcpy.AddMessage(f"Area: {area} {units}^2")

    Convert to kilometers:

    >>> area, units = arcsmith.fc.get_area("path/to/glaciers.shp", output_units="Kilometer")

    Feed directly into AverageNearestNeighbor:

    >>> area, _ = arcsmith.fc.get_area(glaciers, output_units="Meter")
    >>> arcpy.stats.AverageNearestNeighbor(wildlife_sightings, "EUCLIDEAN_DISTANCE", Area=area)
    """
    if output_units is not None and output_units not in _TO_METERS:
        raise ValueError(
            f"Unknown output_units '{output_units}'. "
            f"Choose from: {sorted(_TO_METERS)}."
        )

    with arcpy.da.SearchCursor(str(polygon_fc), "SHAPE@AREA") as cursor:
        areas = [row[0] for row in cursor]

    if not areas:
        raise ValueError(f"No features found in {polygon_fc}; cannot compute area.")

    native_area = sum(areas)
    native_units = arcpy.Describe(str(polygon_fc)).spatialReference.linearUnitName

    if output_units is None or output_units == native_units:
        # arcpy.AddMessage(f"Polygon area: {native_area} {native_units}^2")
        return native_area, native_units

    if native_units not in _TO_METERS:
        raise ValueError(
            f"Cannot convert area: source units '{native_units}' are not a "
            f"recognized linear unit. The data may be in a geographic "
            f"coordinate system. Re-project to a projected CRS, or call "
            f"without output_units to get the native area unchanged."
        )

    # Convert: native -> meters -> output
    area_m2 = native_area * (_TO_METERS[native_units] ** 2)
    converted = area_m2 / (_TO_METERS[output_units] ** 2)

    # arcpy.AddMessage(f"Polygon area: {converted} {output_units}^2"
    #                  f" (converted from {native_area} {native_units}^2)")
    return converted, output_units


def validate_geom_type(input_fc: _PathLike,
                       expected_shape: Union[str, list[str]]) -> bool:
    """
    Check whether a feature class has the expected geometry type.

    Parameters
    ----------
    input_fc : str or Path
        Path to the feature class to inspect.
    expected_shape : str or list of str
        Geometry type(s) to accept. Case-insensitive. Common values:
        ``'Point'``, ``'Polyline'``, ``'Polygon'``, ``'Multipoint'``.
        Pass a list to accept more than one type.

    Returns
    -------
    bool
        ``True`` if the feature class geometry matches any entry in
        ``expected_shape``, ``False`` otherwise.

    Examples
    --------
    Single type:

    >>> if not arcsmith.fc.validate_geom_type(input_fc, "Point"):
    ...     arcpy.AddError("Input must be a point layer.")

    Multiple accepted types:

    >>> if not arcsmith.fc.validate_geom_type(input_fc, ["Point", "Multipoint"]):
    ...     arcpy.AddError("Input must be a point or multipoint layer.")

    Use inside updateMessages:

    >>> if input_points.value:
    ...     fc_path = arcsmith.param.to_path(input_points)
    ...     if not arcsmith.fc.validate_geom_type(fc_path, "Point"):
    ...         input_points.setErrorMessage("Input must be a point layer.")
    """
    if isinstance(expected_shape, str):
        expected_shape = [expected_shape]

    accepted = {s.lower() for s in expected_shape}
    actual = arcpy.Describe(str(input_fc)).shapeType.lower()
    return actual in accepted


def build_where(input_fc: _PathLike, field: str,
                value: Optional[Union[str, int, float]],
                operator: str = "=") -> str:
    """
    Build a SQL WHERE clause for a single field comparison.

    Handles field delimiting and value quoting based on the field's type,
    so the caller does not need to know whether the value needs quotes or
    which delimiter syntax the data source requires.

    Parameters
    ----------
    input_fc : str or Path
        Path to the feature class. Used to resolve the correct field
        delimiter for the data source.
    field : str
        Name of the field to filter on.
    value : str, int, float, or None
        Value to compare against. Automatically quoted for string-like
        field types (``String``, ``Guid``, ``Date``). Pass ``None`` to
        generate an ``IS NULL`` or ``IS NOT NULL`` clause.
    operator : str, optional
        SQL comparison operator. Default ``'='``. Use ``'<>'`` to exclude
        the value, or any other valid SQL operator (``'>'``, ``'<='``, etc.).
        When ``value`` is ``None``, ``'<>'`` and ``'!='`` produce
        ``IS NOT NULL``; all other operators produce ``IS NULL``.

    Returns
    -------
    str
        A SQL WHERE clause ready to pass to :func:`export_fc` or any
        arcpy function that accepts a where clause.

    Raises
    ------
    ValueError
        If ``field`` is not found in ``input_fc``.

    Examples
    --------
    Filter a point layer to a single species:

    >>> clause = arcsmith.fc.build_where(wildlife_sightings, "SPECIES", "Mountain Goat")
    >>> # "SPECIES" = 'Mountain Goat'

    >>> clause = arcsmith.fc.build_where("path/to/trails", "TRAIL_STATUS", "Open")
    >>> # "TRAIL_STATUS" = 'Open'

    >>> clause = arcsmith.fc.build_where("path/to/trails", "TRAIL_STATUS", "Closed", operator="<>")
    >>> # "TRAIL_STATUS" <> 'Closed'

    >>> clause = arcsmith.fc.build_where("path/to/trails", "DISTRICT", 4, operator=">=")
    >>> # "DISTRICT" >= 4

    >>> clause = arcsmith.fc.build_where("path/to/trails", "CLOSURE_NOTE", None)
    >>> # "CLOSURE_NOTE" IS NULL

    >>> clause = arcsmith.fc.build_where("path/to/trails", "CLOSURE_NOTE", None, operator="<>")
    >>> # "CLOSURE_NOTE" IS NOT NULL

    >>> clause = arcsmith.fc.build_where("path/to/trails", "NAME", "St. Mary's")
    >>> # "NAME" = 'St. Mary''s'  (embedded quote escaped)
    """
    field_info = [f for f in arcpy.ListFields(str(input_fc)) if f.name == field]
    if not field_info:
        raise ValueError(f"Field '{field}' not found in {input_fc}.")

    delimited = arcpy.AddFieldDelimiters(str(input_fc), field)

    if value is None:
        sql_op = "IS NOT NULL" if operator in ("<>", "!=") else "IS NULL"
        return f"{delimited} {sql_op}"

    if field_info[0].type in _QUOTED_TYPES:
        return f"{delimited} {operator} {_sql_quote(value)}"
    return f"{delimited} {operator} {value}"


def build_where_in(input_fc: _PathLike, field: str,
                   values: list[Union[str, int, float]],
                   exclude: bool = False) -> str:
    """
    Build a SQL WHERE clause for a multi-value ``IN`` (or ``NOT IN``) filter.

    Handles field delimiting and value quoting based on the field's type,
    so the caller does not need to know whether values need quotes or which
    delimiter syntax the data source requires.

    Use this when filtering on a list of values, such as the
    selections from a multi-value toolbox parameter. For a single value use
    :func:`build_where` instead.

    Parameters
    ----------
    input_fc : str or Path
        Path to the feature class. Used to resolve the correct field
        delimiter and field type for the data source.
    field : str
        Name of the field to filter on.
    values : list of str, int, or float
        Values to match against. Must contain at least one entry. Values are
        automatically quoted for string-like field types (``String``,
        ``Guid``, ``Date``) and left unquoted for numeric types.
    exclude : bool, optional
        If ``False`` (default), generates an ``IN`` clause (keep matching
        rows). If ``True``, generates a ``NOT IN`` clause (drop matching
        rows).

    Returns
    -------
    str
        A SQL WHERE clause ready to pass to :func:`export_fc` or any arcpy
        function that accepts a where clause.

    Raises
    ------
    ValueError
        If ``field`` is not found in ``input_fc``.
    ValueError
        If ``values`` is empty.

    Examples
    --------
    Keep only selected visitor facilities (string field, quoted automatically):

    >>> clause = arcsmith.fc.build_where_in(landmarks, "NAME",
    ...     ["Lake McDonald Lodge", "East Glacier Lodge", "St. Mary Lake Boats"])
    >>> # "NAME" IN ('Lake McDonald Lodge', 'East Glacier Lodge', 'St. Mary Lake Boats')

    Keep only selected area codes (string field):

    >>> clause = arcsmith.fc.build_where_in(fc, "AREA_CODE", ["NF", "LM", "MG"])
    >>> # "AREA_CODE" IN ('NF', 'LM', 'MG')

    Exclude a list of districts (numeric field):

    >>> clause = arcsmith.fc.build_where_in(fc, "DISTRICT", [3, 7, 12], exclude=True)
    >>> # "DISTRICT" NOT IN (3, 7, 12)

    Combine with export_fc to filter rows and fields in one call:

    >>> clause = arcsmith.fc.build_where_in(fc, "AREA", area_codes)
    >>> out = arcsmith.fc.export_fc(fc, output_fc, ["NAME", "AREA"], where_clause=clause)

    Unpack a multi-value toolbox parameter directly:

    >>> area_codes = ['TM', 'SM', 'GH']
    >>> clause = arcsmith.fc.build_where_in(fc_path, area_field, area_codes)
    """
    if not values:
        raise ValueError("'values' must contain at least one entry.")

    field_info = [f for f in arcpy.ListFields(str(input_fc)) if f.name == field]
    if not field_info:
        raise ValueError(f"Field '{field}' not found in {input_fc}.")

    delimited = arcpy.AddFieldDelimiters(str(input_fc), field)
    keyword = "NOT IN" if exclude else "IN"

    if field_info[0].type in _QUOTED_TYPES:
        joined = ", ".join(_sql_quote(v) for v in values)
    else:
        joined = ", ".join(str(v) for v in values)

    return f"{delimited} {keyword} ({joined})"


def export_fc(input_fc: _PathLike, output_fc: _PathLike,
              fields: Optional[list[str]] = None, keep: bool = True,
              where_clause: Optional[str] = None) -> str:
    """
    Export a feature class to a new location, optionally filtering fields and rows.

    Parameters
    ----------
    input_fc : str or Path
        Path to the source feature class.
    output_fc : str or Path
        Full path for the output feature class, including workspace and name
        (e.g. ``"C:/data/glacier.gdb/trails"``).
    fields : list of str, optional
        Field names to act on. When ``keep=True`` (default) these are the
        fields to retain; all others are removed. When ``keep=False`` these
        are the fields to remove; all others are kept. Pass ``[]`` with
        ``keep=True`` to export geometry only. Default ``None`` (all fields
        are exported).
    keep : bool, optional
        If ``True`` (default), ``fields`` specifies what to keep.
        If ``False``, ``fields`` specifies what to drop.
        Ignored when ``fields`` is ``None``.
    where_clause : str, optional
        SQL expression to filter rows. Evaluated against the source feature
        class, so a field used here does not need to appear in the output.
        A field can be filtered on while also being dropped from ``fields``.
        Default ``None`` (all rows are exported).

    Returns
    -------
    str
        Absolute path to the output feature class.

    Raises
    ------
    ValueError
        If any field name in ``fields`` does not exist in ``input_fc``.

    Examples
    --------
    Copy a feature class into a geodatabase (no filtering):

    >>> out = arcsmith.fc.export_fc(input_fc, "C:/data/glacier.gdb/trails")

    Row filter only:

    >>> clause = arcsmith.fc.build_where(input_fc, "TRAIL_STATUS", "Open")
    >>> out = arcsmith.fc.export_fc(input_fc, "C:/data/glacier.gdb/open_trails", where_clause=clause)

    Field filter only:

    >>> out = arcsmith.fc.export_fc(input_fc, "C:/data/glacier.gdb/trails_slim", fields=["NAME", "TRAIL_STATUS"])

    Filter rows on a field, then drop it from the output:

    >>> clause = arcsmith.fc.build_where(input_fc, "VISITS_2024", 10000, operator=">")
    >>> out = arcsmith.fc.export_fc(
    ...     input_fc, "C:/data/glacier.gdb/busy_trails",
    ...     fields=["NAME", "AREA"],
    ...     where_clause=clause,
    ... )

    Geometry only:

    >>> out = arcsmith.fc.export_fc(input_fc, "C:/data/glacier.gdb/trails_geom", fields=[])
    """
    input_fc = Path(str(input_fc))
    output_fc = Path(str(output_fc))

    fm = build_fld_map(input_fc, fields, keep=keep)

    arcpy.conversion.ExportFeatures(
        str(input_fc),
        str(output_fc),
        where_clause=where_clause or "",
        field_mapping=fm,
    )

    return str(output_fc)