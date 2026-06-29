<div class="as-hero" markdown>
<div class="as-hero__eyebrow">arcsmith.flds</div>
<h2 class="as-hero__title">Fields</h2>
<p class="as-hero__sub">Utilities for field mapping, field-filtered copying, blank value standardization, and in-place schema edits.</p>
<ul class="as-hero__highlights">
<li>Build field mappings to retain or drop specific fields before exporting</li>
<li>Add, rename, and delete fields in place</li>
<li>Standardize blank-like values across string fields</li>
<li>List field names or extract unique values for use in dropdowns</li>
</ul>
</div>

## Functions of the `flds` module

## add_fld

Adds a new field to a feature class or table in place, then returns the path.

```python
add_fld(input_fc, field, field_type, *, length=None, alias=None) -> str
```

The field is created empty; populate it afterward with an `UpdateCursor`, [`join_lookup`](tbl.md#join_lookup), or [`clean_blanks`](#clean_blanks).

| Parameter    | Type                                                          | Default  | Description                                                              |
|--------------|---------------------------------------------------------------|----------|--------------------------------------------------------------------------|
| `input_fc`   | `str` or `Path`                                               | required | Feature class or table to add the field to. Edited in place.            |
| `field`      | `str`                                                         | required | Name of the new field.                                                  |
| `field_type` | `'TEXT'`, `'SHORT'`, `'LONG'`, `'FLOAT'`, `'DOUBLE'`, `'DATE'` | required | arcpy field type for the new field.                                     |
| `length`     | `int`                                                         | `None`   | Keyword-only. Field length, used only when `field_type` is `'TEXT'`. Default `None` (arcpy's default length). |
| `alias`      | `str`                                                         | `None`   | Keyword-only. Display alias for the field. Default `None` (alias matches the field name). |

!!! success "Returns"
    `str`: the `input_fc` path, now carrying the new field.

!!! failure "Raises"
    `ValueError` if a field named `field` already exists in `input_fc`. `add_fld` never silently overwrites an existing field; remove it first with [`del_fld`](#del_fld) if you mean to replace it.

**Examples**

```python
# Add a text field sized to 50 characters
arcsmith.flds.add_fld(trails, "TRAIL_NOTE", "TEXT", length=50)

# Add a numeric field with a friendly alias
arcsmith.flds.add_fld(trails, "VISITS_2024", "LONG", alias="2024 Visits")
```

---

## build_fld_map

Builds an `arcpy.FieldMappings` object that retains only a chosen subset of fields. Pass the result directly to any arcpy tool that accepts field mappings.

```python
build_fld_map(input_fc, fields=None, keep=True) -> arcpy.FieldMappings
```

| Parameter  | Type            | Default  | Description                                                                                                                                                                                              |
|------------|-----------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc` | `str` or `Path` | required | Path to the source feature class.                                                                                                                                                                        |
| `fields`   | list of `str`   | `None`   | Field names to act on. When `keep=True` these are the fields to retain; all others are removed. When `keep=False` these are the fields to remove; all others are kept. Pass `[]` with `keep=True` to retain geometry only. Default `None` (all fields retained; `keep` is ignored). |
| `keep`     | `bool`          | `True`   | If `True`, `fields` specifies what to keep. If `False`, `fields` specifies what to drop. Ignored when `fields` is `None`.                                                                               |

!!! success "Returns"
    `arcpy.FieldMappings`: ready to pass to `arcpy.conversion.ExportFeatures` or any other arcpy tool that accepts field mappings.

!!! failure "Raises"
    `ValueError` if any field name in `fields` does not exist in `input_fc` (system fields are exempt from this check).

!!! note "System fields"
    `OID`, `Shape`, `Shape_Length`, `Shape_Area`, and `GlobalID` are managed internally by arcpy and are always present in the output regardless. Listing them in `fields` is silently ignored rather than raising an error.

**Examples**

```python
# All fields - no filtering
fm = arcsmith.flds.build_fld_map(input_fc)

# Keep only the fields that are needed
fm = arcsmith.flds.build_fld_map(input_fc, ["NAME", "VISITS_2024", "AREA"])

# Drop unwanted fields and keep everything else
fm = arcsmith.flds.build_fld_map(input_fc, ["CLOSURE_NOTE", "TEMP_FLAG"], keep=False)

# Geometry only - no attribute fields
fm = arcsmith.flds.build_fld_map(input_fc, [])

# Pass directly to an arcpy export tool
fm = arcsmith.flds.build_fld_map(input_fc, ["NAME", "TRAIL_STATUS"])
arcpy.conversion.ExportFeatures(input_fc, "path/to/out.gdb/park_boundary", field_mapping=fm)

# Or use export_fc as a shorthand for the same operation
arcsmith.fc.export_fc(input_fc, "path/to/out.gdb/park_boundary", ["NAME", "TRAIL_STATUS"])

```

---

## clean_blanks

Standardizes blank-like values in a text field to a single canonical value. Edits in-place by default, or writes to a new feature class if `output_fc` is provided.

```python
clean_blanks(input_fc, fields, output_fc=None, blank_value="N/A") -> dict[str, int]
```

| Parameter     | Type                    | Default  | Description                                                                                                                                                  |
|---------------|-------------------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc`    | `str` or `Path`         | required | Path to the source feature class.                                                                                                                            |
| `fields`      | `str` or list of `str`  | required | Text field name(s) to clean. A single name may be passed without a list.                                                                                     |
| `output_fc`   | `str` or `Path`         | `None`   | If provided, `input_fc` is copied to this path and cleaning is performed on the copy. `input_fc` is left unchanged. Default `None` (edits `input_fc` in-place). |
| `blank_value` | `str`                   | `"N/A"`  | The canonical replacement for blank-like cells. Default `"N/A"`.                                                                                             |

!!! success "Returns"
    dict of `str` to `int`: maps each cleaned field name to the number of cells that were replaced. Fields that were skipped (non-string type) are not included.

!!! failure "Raises"
    `ValueError` if any name in `fields` does not exist in `input_fc`.

!!! note "What counts as blank"
    A cell is replaced if it is `None` / SQL `NULL`, an empty string `""`, a whitespace-only string, or a case-insensitive match (after stripping whitespace) for any of: `"N/A"`, `"NA"`, `"None"`, `"Null"`, `"Nil"`, `"-"`, `"--"`, `"---"`.

!!! note "Non-string fields"
    Any field in `fields` whose type is not `String` is skipped with an `arcpy.AddWarning` and is not included in the returned counts.

**Examples**

```python
# Clean a single field in-place
counts = arcsmith.flds.clean_blanks(input_fc, "TRAIL_STATUS")
# {"TRAIL_STATUS": 12}

# Clean a copy, leaving the original unchanged
counts = arcsmith.flds.clean_blanks(
    input_fc, "TRAIL_STATUS", output_fc="C:/data/glacier.gdb/trails_clean"
)

# Clean multiple fields with a custom replacement
counts = arcsmith.flds.clean_blanks(
    input_fc, ["TRAIL_STATUS", "CLOSURE_NOTE", "TRAIL_TYPE"],
    blank_value="Unknown",
    output_fc="C:/data/glacier.gdb/trails_clean",
)

# Report how many cells were standardized
for field, n in counts.items():
    arcpy.AddMessage(f"{field}: {n} blank(s) replaced")
```

---

## del_fld

Deletes one or more fields from a feature class or table in place, then returns the path.

```python
del_fld(input_fc, fields) -> str
```

| Parameter  | Type                   | Default  | Description                                                       |
|------------|------------------------|----------|-------------------------------------------------------------------|
| `input_fc` | `str` or `Path`        | required | Feature class or table to delete fields from. Edited in place.   |
| `fields`   | `str` or list of `str` | required | Field name(s) to delete. Matched case-insensitively. A single name may be passed without a list. |

!!! success "Returns"
    `str`: the `input_fc` path.

!!! failure "Raises"
    `ValueError` if any name in `fields` is not found in `input_fc`, or names a system-managed field.

!!! note "System fields are protected"
    System-managed fields (`OID`, `Shape`, `Shape_Length`, `Shape_Area`, `GlobalID`) cannot be deleted and are rejected with a clear error rather than handed to arcpy.

**Examples**

```python
# Delete a single field
arcsmith.flds.del_fld(trails, "TEMP_FLAG")

# Delete several at once
arcsmith.flds.del_fld(trails, ["TEMP_FLAG", "LEGACY_CODE", "SCRATCH"])
```

---

## list_cols

Returns the field names present in a feature class. System-managed fields are excluded by default.

```python
list_cols(input_fc, include_system=False, *, include_oid=False) -> list[str]
```

| Parameter        | Type            | Default  | Description                                                                                             |
|------------------|-----------------|----------|---------------------------------------------------------------------------------------------------------|
| `input_fc`       | `str` or `Path` | required | Path to the source feature class.                                                                       |
| `include_system` | `bool`          | `False`  | If `False` (default), system-managed fields (`OID`, `Shape`, `Shape_Length`, `Shape_Area`, `GlobalID`) are excluded. If `True`, all fields are returned. |
| `include_oid`    | `bool`          | `False`  | Keyword-only. If `True`, the Object ID field is included alongside the user-defined fields while the other system fields stay excluded. Matched by field type, so it is found whatever it is named (`OBJECTID`, `FID`, `OID`). No effect when `include_system=True`. |

!!! success "Returns"
    list of `str`: field names in the order arcpy reports them.

!!! tip "Object ID in an ID-field dropdown"
    Use `include_oid=True` when populating a dropdown where the user picks a unique-identifier field. The Object ID is the dependable fallback when a dataset has no user-defined ID. It is opt-in because it is rarely a useful choice for *grouping*, where it would produce one group per feature.

**Examples**

```python
# List user-defined fields
arcsmith.flds.list_cols(input_fc)
# ['TRAIL_ID', 'MAINTAINER', 'TRAIL_STATUS', 'LENGTH_MI']

# Include the Object ID for an ID-field dropdown
arcsmith.flds.list_cols(input_fc, include_oid=True)
# ['OBJECTID', 'TRAIL_ID', 'MAINTAINER', 'TRAIL_STATUS', 'LENGTH_MI']

# Include every system field
arcsmith.flds.list_cols(input_fc, include_system=True)
# ['OBJECTID', 'Shape', 'TRAIL_ID', 'MAINTAINER', 'TRAIL_STATUS', 'LENGTH_MI', 'Shape_Length', 'Shape_Area']

# Feed directly into a dropdown
arcsmith.param.drop_populate(parameters[1], arcsmith.flds.list_cols(parameters[0].valueAsText))
```

---

## rename_fld

Renames a field, and optionally its alias, in place using `arcpy.management.AlterField`, then returns the path.

```python
rename_fld(input_fc, field, new_name, *, new_alias=None) -> str
```

| Parameter   | Type            | Default  | Description                                                            |
|-------------|-----------------|----------|------------------------------------------------------------------------|
| `input_fc`  | `str` or `Path` | required | Feature class or table containing the field. Edited in place.         |
| `field`     | `str`           | required | Existing field to rename. Matched case-insensitively.                 |
| `new_name`  | `str`           | required | New name for the field.                                               |
| `new_alias` | `str`           | `None`   | Keyword-only. New display alias. Default `None` (alias left unchanged). |

!!! success "Returns"
    `str`: the `input_fc` path.

!!! failure "Raises"
    `ValueError` if `field` is not found in `input_fc`.

!!! warning "Not all formats support renaming"
    `AlterField` cannot rename a required or system-managed field, and some formats such as shapefiles do not allow renaming at all. arcpy raises in those cases.

**Examples**

```python
# Rename a field
arcsmith.flds.rename_fld(trails, "TRL_STAT", "TRAIL_STATUS")

# Rename a field and set a readable alias
arcsmith.flds.rename_fld(trails, "VIS24", "VISITS_2024", new_alias="2024 Visits")
```

---

## unique_values

Returns the unique values present in a single field, or the unique value combinations present across multiple fields.

```python
unique_values(input_fc, fields, sort=True, max_rows=None) -> list
```

| Parameter  | Type                   | Default  | Description                                                                                                                                                                                                 |
|------------|------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc` | `str` or `Path`        | required | Path to the source feature class.                                                                                                                                                                           |
| `fields`   | `str` or list of `str` | required | Field name(s) to inspect. A single string for one field; a list for multi-field combinations. Field names are matched case-insensitively.                                                                   |
| `sort`     | `bool`                 | `True`   | If `True`, the result is sorted: values directly for a single field, lexicographically for tuples. `None` sorts before all other values in every position. Set `False` to preserve first-encountered order. |
| `max_rows` | `int`                  | `None`   | If given, stop scanning after this many rows. Bounds the scan cost on large datasets, but the result may be incomplete. Only values found within the first `max_rows` rows are returned. Default `None` (full scan). |

!!! success "Returns"
    Single field: list of distinct values (any type). Multiple fields: list of `tuple`, one per unique combination, aligned to the order of `fields`.

!!! failure "Raises"
    `ValueError` if any name in `fields` does not exist in `input_fc`.

!!! note "`None` handling"
    SQL `NULL` is included as a distinct value when present in the data. With `sort=True`, `None` sorts before all other values in every position.

!!! warning "`max_rows` and completeness"
    Setting `max_rows` stops the scan early, so distinct values that appear only in rows beyond the limit will be missing. Leave it unset (the default) to capture every distinct value, such as when fully populating a dropdown.

**Examples**

```python
# Unique values from a single field
arcsmith.flds.unique_values(landmarks, "NAME")
# ['East Glacier Lodge', 'Lake McDonald Lodge', 'St. Mary Lake Boats']

# Unique combinations across two fields
arcsmith.flds.unique_values(input_fc, ["AREA_CODE", "SUBAREA"])
# [('MG', 'Swiftcurrent'), ('TM', 'Cut Bank'), ('TM', 'Two Medicine')]

# Preserve insertion order instead of sorting
arcsmith.flds.unique_values(input_fc, "TRAIL_STATUS", sort=False)

# Cap the scan on a large table (result may be incomplete)
arcsmith.flds.unique_values(input_fc, "TRAIL_STATUS", max_rows=10000)

# Feed directly into a parameter dropdown.
# None entries and non-strings are handled automatically by drop_populate.
values = arcsmith.flds.unique_values(input_fc, "TRAIL_TYPE")
arcsmith.param.drop_populate(parameters[1], values)
```

<br><br><br><br><br>