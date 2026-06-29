<div class="as-hero" markdown>
<div class="as-hero__eyebrow">arcsmith.fc</div>
<h2 class="as-hero__title">Feature Class</h2>
<p class="as-hero__sub">Helpers for building SQL WHERE clauses and exporting filtered subsets of feature classes.</p>
<ul class="as-hero__highlights">
<li>Build SQL WHERE clauses with automatic field delimiting and value quoting, including multi-value IN filters</li>
<li>Export a feature class to a new location with optional field and row filtering, including a straight copy into a geodatabase</li>
<li>Validate geometry types and compute polygon area with optional unit conversion</li>
</ul>
</div>

## Functions of the `fc` module

## build_where

Builds a SQL WHERE clause for a single field comparison, handling field delimiting and value quoting automatically based on the field's type.

```python
build_where(input_fc, field, value, operator="=") -> str
```

| Parameter  | Type                              | Default  | Description                                                                                                                                                                                    |
|------------|-----------------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc` | `str` or `Path`                   | required | Path to the feature class. Used to resolve the correct field delimiter for the data source.                                                                                                    |
| `field`    | `str`                             | required | Name of the field to filter on.                                                                                                                                                                |
| `value`    | `str`, `int`, `float`, or `None`  | required | Value to compare against. Automatically quoted for string-like field types (`String`, `Guid`, `Date`). Pass `None` to produce an `IS NULL` or `IS NOT NULL` clause.                           |
| `operator` | `str`                             | `'='`    | SQL comparison operator. Any valid SQL operator is accepted (`'<>'`, `'>'`, `'<='`, etc.). When `value` is `None`, `'<>'` and `'!='` produce `IS NOT NULL`; all other operators produce `IS NULL`. Default `'='`. |

!!! success "Returns"
    `str`: a SQL WHERE clause ready to pass to `export_fc` or any arcpy function that accepts a where clause.

!!! failure "Raises"
    `ValueError` if `field` is not found in `input_fc`.

!!! note
    Field delimiters vary by data source (e.g. double-quotes for file geodatabases, square brackets for personal geodatabases). `build_where` calls `arcpy.AddFieldDelimiters` internally to process delimiters accordingly.

**Examples**

```python
# Filter wildlife sightings to a single species (string field, quoted automatically)
clause = arcsmith.fc.build_where(wildlife_sightings, "SPECIES", "Mountain Goat")
# "SPECIES" = 'Mountain Goat'

# String field: value is quoted automatically
clause = arcsmith.fc.build_where(input_fc, "TRAIL_STATUS", "Open")
# "TRAIL_STATUS" = 'Open'

# Exclude a value
clause = arcsmith.fc.build_where(input_fc, "TRAIL_STATUS", "Closed", operator="<>")
# "TRAIL_STATUS" <> 'Closed'

# Numeric field: no quoting applied
clause = arcsmith.fc.build_where(input_fc, "DISTRICT", 4, operator=">=")
# "DISTRICT" >= 4

# Null check produces IS NULL
clause = arcsmith.fc.build_where(input_fc, "CLOSURE_NOTE", None)
# "CLOSURE_NOTE" IS NULL

# Null exclusion produces IS NOT NULL
clause = arcsmith.fc.build_where(input_fc, "CLOSURE_NOTE", None, operator="<>")
# "CLOSURE_NOTE" IS NOT NULL
```

---

## build_where_in

Builds a SQL WHERE clause for a multi-value `IN` (or `NOT IN`) filter, handling field delimiting and value quoting automatically based on the field's type.

```python
build_where_in(input_fc, field, values, exclude=False) -> str
```

| Parameter  | Type                                    | Default  | Description                                                                                                                                          |
|------------|-----------------------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc` | `str` or `Path`                         | required | Path to the feature class. Used to resolve the correct field delimiter and field type for the data source.                                           |
| `field`    | `str`                                   | required | Name of the field to filter on.                                                                                                                      |
| `values`   | list of `str`, `int`, or `float`        | required | Values to match against. Must contain at least one entry. Automatically quoted for string-like field types (`String`, `Guid`, `Date`); left unquoted for numeric types. |
| `exclude`  | `bool`                                  | `False`  | If `False` (default), generates an `IN` clause (keep matching rows). If `True`, generates a `NOT IN` clause (drop matching rows).                   |

!!! success "Returns"
    `str`: a SQL WHERE clause ready to pass to `export_fc` or any arcpy function that accepts a where clause.

!!! failure "Raises"
    `ValueError` if `field` is not found in `input_fc`.

    `ValueError` if `values` is empty.


!!! note
    Use `build_where_in` when filtering on a list of values, such as the selections from a multi-value toolbox parameter. For a single value use `build_where` instead.

**Examples**

```python
# Keep only selected visitor facilities (string field, values quoted automatically)
clause = arcsmith.fc.build_where_in(
    landmarks, "NAME",
    ["Lake McDonald Lodge", "East Glacier Lodge", "St. Mary Lake Boats"],
)
# "NAME" IN ('Lake McDonald Lodge', 'East Glacier Lodge', 'St. Mary Lake Boats')

# Keep only selected area codes (string field, so values are quoted automatically)
clause = arcsmith.fc.build_where_in(trails, "AREA_CODE", ["NF", "LM", "MG"])
# "AREA_CODE" IN ('NF', 'LM', 'MG')

# Exclude a list of district IDs (numeric field, so no quoting is applied)
clause = arcsmith.fc.build_where_in(trails, "DISTRICT", [3, 7, 12], exclude=True)
# "DISTRICT" NOT IN (3, 7, 12)

# Combine with export_fc to filter rows and fields in one call
clause = arcsmith.fc.build_where_in(trails, "AREA", area_codes)
out = arcsmith.fc.export_fc(trails, output_fc, ["NAME", "AREA"], where_clause=clause)

# Unpack a multi-value toolbox parameter directly
area_codes = area_codes.valueAsText.split(";")
clause = arcsmith.fc.build_where_in(fc_path, area_field, area_codes)
```

---

## export_fc

Exports a feature class to a new location, optionally filtering fields and rows in a single call. Use it to copy a feature class into a geodatabase, export an attribute-filtered subset, keep or drop selected fields, or do all of these at once.

```python
export_fc(input_fc, output_fc, fields=None, keep=True, where_clause=None) -> str
```

| Parameter      | Type            | Default  | Description                                                                                                                                                                                                                                  |
|----------------|-----------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc`     | `str` or `Path` | required | Path to the source feature class.                                                                                                                                                                                                            |
| `output_fc`    | `str` or `Path` | required | Full path for the output feature class, including workspace and name (e.g. `"C:/data/glacier.gdb/trails"`).                                                                                                                                  |
| `fields`       | list of `str`   | `None`   | Field names to act on. When `keep=True` (default) these are the fields to retain; all others are removed. When `keep=False` these are the fields to remove; all others are kept. Pass `[]` with `keep=True` to export geometry only. Default `None` (all fields exported). |
| `keep`         | `bool`          | `True`   | If `True`, `fields` specifies what to keep. If `False`, `fields` specifies what to drop. Ignored when `fields` is `None`.                                                                                                                     |
| `where_clause` | `str`           | `None`   | SQL expression to filter rows. Evaluated against the source feature class, so a field used here need not appear in the output. A field can be filtered on while also being dropped from `fields`. Use `arcsmith.fc.build_where` or `build_where_in` to construct one. Default `None` (all rows exported). |

!!! success "Returns"
    `str`: absolute path to the output feature class.

!!! failure "Raises"
    `ValueError` if any field name in `fields` does not exist in `input_fc`.

!!! note
    Combines `arcsmith.flds.build_fld_map` with `arcpy.conversion.ExportFeatures`, so rows and fields are filtered together with no intermediate feature class. To pull an external feature class into the working geodatabase at the start of a script, call `export_fc` with just `input_fc` and an output path inside the gdb. The source is left unchanged.

!!! note "Multivalue field parameters"
    `arcpy.Parameter.values` on a multivalue `Field` parameter returns a list
    of `ValueObject`s, not strings. Extract string values before passing to
    ArcSmith functions:

    ```python
        fields = [str(f) for f in parameters[1].values] if parameters[1].values else None
    ```

**Examples**

```python
# Copy a feature class into a geodatabase (no filtering)
out = arcsmith.fc.export_fc(input_fc, "C:/data/glacier.gdb/trails")

# Ingest an external feature class into the working geodatabase, then add it to the map
src = arcsmith.param.to_path(parameters[0])
out = arcsmith.fc.export_fc(src, "C:/data/glacier.gdb/study_trails")
arcsmith.lyr.add(target_map, out)

# Geometry only, with no attribute fields
out = arcsmith.fc.export_fc(input_fc, "C:/data/glacier.gdb/trails_geom", fields=[])

# Keep only specific fields
out = arcsmith.fc.export_fc(
    input_fc, "C:/data/glacier.gdb/trails_slim",
    ["TRAIL_ID", "MAINTAINER", "LENGTH_MI"],
)

# Drop a few fields and keep everything else
out = arcsmith.fc.export_fc(
    input_fc, "C:/data/glacier.gdb/trails_clean",
    ["TEMP_FLAG", "LEGACY_CODE"], keep=False,
)

# Filter fields and rows together
clause = arcsmith.fc.build_where(input_fc, "TRAIL_STATUS", "Open")
out = arcsmith.fc.export_fc(
    input_fc, "C:/data/glacier.gdb/open_trails",
    ["TRAIL_ID", "MAINTAINER", "TRAIL_STATUS"],
    where_clause=clause,
)
arcsmith.lyr.add(target_map, out)

# Filter rows on a field, then drop it from the output
clause = arcsmith.fc.build_where(input_fc, "VISITS_2024", 10000, operator=">")
out = arcsmith.fc.export_fc(
    input_fc, "C:/data/glacier.gdb/busy_trails",
    fields=["NAME", "AREA"],
    where_clause=clause,
)
```

---

## get_area

Returns the area of a polygon feature class and the unit name, summed across every feature in the feature class. Optionally converts the area to a different unit system before returning.

```python
get_area(polygon_fc, output_units=None) -> tuple[float, str]
```

| Parameter      | Type            | Default  | Description                                                                                                                                                                                                                       |
|----------------|-----------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `polygon_fc`   | `str` or `Path` | required | Path to the polygon feature class.                                                                                                                                                                                                |
| `output_units` | `str`           | `None`   | Linear unit name to convert the area into. Must be one of: `'Meter'`, `'Kilometer'`, `'Foot_US'`, `'Foot'`, `'Mile_US'`, `'Nautical_Mile'`, `'Yard'`. Case-sensitive. Default `None` (returns area in the native spatial reference units). |

!!! success "Returns"
    `tuple` of (`float`, `str`): the area value and the name of the units it is expressed in.

!!! failure "Raises"
    `ValueError` if `output_units` is not a recognized unit name; if `polygon_fc` contains no features; or if `output_units` is requested but the source's native units are not a recognized linear unit (e.g. a geographic coordinate system), so no conversion factor exists.

!!! note "Area units"
    `SHAPE@AREA` is always in the spatial reference's native linear units squared. `get_area` sums the native value across all features and converts if `output_units` is provided. The returned unit string is the linear unit name; the area itself is in those units **squared**.

!!! warning "Geographic coordinate systems"
    A feature class in a geographic coordinate system (degrees) has no linear unit, so `SHAPE@AREA` is not a meaningful real-world area and conversion is impossible. Requesting `output_units` on such data raises `ValueError`; re-project to a projected CRS first.

**Linear unit conversion factors (area factor = linear² )**

| Unit            | Factor to Meters |
|-----------------|------------------|
| `Meter`         | 1.0              |
| `Kilometer`     | 1,000.0          |
| `Foot_US`       | 0.304800609601   |
| `Foot`          | 0.3048           |
| `Mile_US`       | 1,609.347219     |
| `Nautical_Mile` | 1,852.0          |
| `Yard`          | 0.9144           |

**Examples**

```python
# Native units, with no conversion
area, units = arcsmith.fc.get_area("path/to/glaciers.shp")
arcpy.AddMessage(f"Area: {area} {units}^2")

# Convert to kilometers before returning
area, units = arcsmith.fc.get_area("path/to/glaciers.shp", output_units="Kilometer")

# Feed directly into AverageNearestNeighbor (requires area in square meters)
area, _ = arcsmith.fc.get_area(glaciers, output_units="Meter")
arcpy.stats.AverageNearestNeighbor(wildlife_sightings, "EUCLIDEAN_DISTANCE", Area=area)
```

---

## validate_geom_type

Checks whether a feature class has the expected geometry type. Returns `True` if the geometry matches, `False` otherwise.

```python
validate_geom_type(input_fc, expected_shape) -> bool
```

| Parameter        | Type                   | Default  | Description                                                                                                                                                         |
|------------------|------------------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc`       | `str` or `Path`        | required | Path to the feature class to inspect.                                                                                                                               |
| `expected_shape` | `str` or list of `str` | required | Geometry type(s) to accept. Case-insensitive. Common values: `'Point'`, `'Polyline'`, `'Polygon'`, `'Multipoint'`. Pass a list to accept more than one type. |

!!! success "Returns"
    `bool`: `True` if the feature class geometry matches any entry in `expected_shape`, `False` otherwise.

!!! note "Where to call this"
    Call `validate_geom_type` inside `updateMessages` to surface a clear error while the user is still configuring the tool, rather than letting an unexpected geometry type cause a cryptic failure partway through `execute`.

**Examples**

```python
# Single accepted type
if not arcsmith.fc.validate_geom_type(input_fc, "Point"):
    arcpy.AddError("Input must be a point layer.")

# Multiple accepted types
if not arcsmith.fc.validate_geom_type(input_fc, ["Point", "Multipoint"]):
    arcpy.AddError("Input must be a point or multipoint layer.")


# Use inside updateMessages to set a parameter error message
def updateMessages(self, parameters):
    input_points = parameters[0]
    if input_points.value:
        fc_path = arcsmith.param.to_path(input_points)
        if not arcsmith.fc.validate_geom_type(fc_path, "Point"):
            input_points.setErrorMessage("Input must be a point layer.")
```
<br><br><br><br><br>