<div class="as-hero" markdown>
<div class="as-hero__eyebrow">arcsmith.tbl</div>
<h2 class="as-hero__title">Table</h2>
<p class="as-hero__sub">Helpers for creating standalone tables, joining tabular data into feature classes, and managing standalone tables in a map.</p>
<ul class="as-hero__highlights">
<li>Materialize an in-memory list of rows as a standalone ArcGIS table, or append rows to an existing table or feature class</li>
<li>Add and populate a field from a <code>{key: value}</code> lookup without building a physical table</li>
<li>Permanently join an external table's columns into a feature class</li>
<li>Add, find, and remove standalone tables in a map's table-of-contents</li>
</ul>
</div>

## Functions of the `tbl` module

## add_rows

Appends rows of Python data to an existing table or feature class via an `arcpy.da.InsertCursor`, and returns the number of rows written.

```python
add_rows(target_table, rows, fields) -> int
```

The row-shape complement of [`from_rows`](#from_rows): `from_rows` creates a new table, `add_rows` writes into one that already exists. The target must already have the fields named in `fields`; create them first with [`arcsmith.flds.add_fld`](flds.md#add_fld) if needed.

| Parameter      | Type                   | Default  | Description                                                                                                       |
|----------------|------------------------|----------|------------------------------------------------------------------------------------------------------------------|
| `target_table` | `str` or `Path`        | required | Existing table or feature class to append to. Edited in place.                                                   |
| `rows`         | `list`                 | required | Rows to append. A list of tuples/lists aligned to `fields`, or a flat list of scalars when `fields` names a single column. |
| `fields`       | `str` or list of `str` | required | Field name(s) the row values map to, in order. Matched case-insensitively. Cursor tokens such as `'SHAPE@'` pass through unchanged, so geometry can be written alongside attributes. |

!!! success "Returns"
    `int`: the number of rows appended.

!!! failure "Raises"
    `ValueError` if any name in `fields` is not found in `target_table` (cursor tokens are exempt), if `rows` is a flat scalar list but more than one field was given, or if a row's width does not match the field count.

**Examples**

```python
# Append rows to a multi-column table
rows = [("TM", "Two Medicine"), ("CB", "Cut Bank")]
arcsmith.tbl.add_rows("C:/data/glacier.gdb/areas", rows, ["AREA_CODE", "AREA_NAME"])

# Append to a single column from a flat list of scalars
arcsmith.tbl.add_rows(areas, ["GL", "NF"], "AREA_CODE")

# Append a point feature with geometry
pt = arcpy.PointGeometry(arcpy.Point(-113.7, 48.7))
arcsmith.tbl.add_rows(sightings, [("Mountain Goat", pt)], ["SPECIES", "SHAPE@"])
```

---

## add_to_map

Adds a standalone table to a map and returns the table object. A standalone table is a distinct kind of map content from a layer: it lives under the map's Standalone Tables, not in the layer list.

```python
add_to_map(target_map, table_src, table_name=None) -> arcpy.mp.Table
```

In-memory tables are handled automatically. A map cannot consume a dataset in the `memory` (or `in_memory`) workspace directly, so such a source is first staged into a table view with `arcpy.management.MakeTableView` and that view is added. An on-disk table is added directly.

| Parameter    | Type                             | Default  | Description                                                                                                      |
|--------------|----------------------------------|----------|-----------------------------------------------------------------------------------------------------------------|
| `target_map` | `arcpy.mp.Map`                   | required | Map object to add the table to.                                                                                 |
| `table_src`  | `str`, `Path`, or `arcpy.Result` | required | Path to the source table (geodatabase table, dBASE/CSV, in-memory table, etc.). `arcpy.Result` objects are accepted and resolved to their output path. |
| `table_name` | `str`                            | `None`   | Display name for the table in the map. Defaults to the source name.                                             |

!!! success "Returns"
    `arcpy.mp.Table`: the table object added to the map.

!!! note "Standalone tables are not layers"
    A standalone table is managed through `Map.listTables()` and `Map.removeTable()`, separate from layers. Use [`get_table`](#get_table) and [`remove_from_map`](#remove_from_map) to retrieve and remove them; the `arcsmith.lyr` helpers operate on layers only.

**Examples**

```python
# Add a geodatabase table to the active map
aprx = arcpy.mp.ArcGISProject("CURRENT")
arcsmith.tbl.add_to_map(aprx.activeMap, "C:/data/glacier.gdb/areas")

# Materialize rows and show the result in the map
rows = [("NF", "North Fork"), ("LM", "Lake McDonald")]
areas = arcsmith.tbl.from_rows("memory/areas", rows, ["AREA_CODE", "AREA_NAME"])
arcsmith.tbl.add_to_map(aprx.activeMap, areas, table_name="Area Names")
```

---

## from_rows

Creates a standalone table from an in-memory list of rows. Use it to materialize Python data as an ArcGIS table. That data can be a list of scalars, a list of tuples, or the output of `arcsmith.flds.unique_values`.

```python
from_rows(out_table, rows, fields, overwrite=False) -> str
```

| Parameter   | Type            | Default  | Description                                                                                                                                                                                                                                                                                  |
|-------------|-----------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `out_table` | `str` or `Path` | required | Full path for the output table, including workspace and name (e.g. `"C:/data/glacier.gdb/areas"` or `"memory/areas"`).                                                                                                                                                                    |
| `rows`      | `list`          | required | The data to write. Either a list of tuples/lists (one per row, aligned to `fields`) or, when there is a single field, a flat list of scalars (each treated as a one-column row). An empty list is allowed only when every field carries an explicit type; an inferred field cannot be sized from no data and will raise. |
| `fields`    | `list`          | required | Column definitions, one per column, in order. Each entry may be `(name, type)` (explicit arcpy field type), `(name, "TEXT", length)` (explicit text length), or a bare `name` string (type inferred from the first non-null value in that column).                                            |
| `overwrite` | `bool`          | `False`  | If `False` (default) and `out_table` already exists, a `ValueError` is raised rather than silently appending or replacing. If `True`, an existing table at that path is deleted first.                                                                                                         |

!!! success "Returns"
    `str`: path (or `memory\...` path) to the created table.

!!! failure "Raises"
    `ValueError` if `rows` and `fields` disagree on column count, if a field type cannot be inferred (an all-null column with no explicit type), or if `out_table` exists and `overwrite` is `False`.

**Inferred field types** (used when a column is given as a bare `name`)

| First non-null value | Inferred arcpy type            |
|----------------------|--------------------------------|
| `int`                | `LONG`                         |
| `float`              | `DOUBLE`                       |
| `str`                | `TEXT` (sized to the longest value) |
| `bool`               | `SHORT`                        |

An all-null `TEXT` column with an explicit type but no values is sized to a default length of `255`.

!!! note "When to reach for `from_rows`"
    For attaching a simple `{key: value}` lookup to a feature class, prefer [`join_lookup`](#join_lookup). It needs no physical table at all. Reach for `from_rows` when you actually want a table: to persist one as a deliverable, or to build a multi-column source to feed [`join_table`](#join_table).

!!! note "Type inference is exact-type"
    Inference keys on the exact Python type of the first non-null value, so values that are not plain `int` / `float` / `str` / `bool` (e.g. a `numpy.int64` from a dataframe) fall through to `TEXT`. Supply an explicit `(name, type)` for those columns.

!!! warning "`memory` limitations"
    The `memory` workspace does not support every field type an on-disk geodatabase does. The caveat documented on [`arcsmith.ws.temp_space`](ws.md#temp_space) applies here too. If a write fails against `memory`, target a scratch GDB path instead.

**Examples**

```python
# Single-column table from a flat list (scalars, not tuples)
area_codes = arcsmith.flds.unique_values(fc, "AREA_CODE")
arcsmith.tbl.from_rows("memory/area_codes", area_codes, [("AREA_CODE", "TEXT", 2)])

# Multi-column crosswalk with inferred types
rows = [("NF", "North Fork"), ("LM", "Lake McDonald"), ("MG", "Many Glacier")]
arcsmith.tbl.from_rows(
    "C:/data/glacier.gdb/areas", rows, ["AREA_CODE", "AREA_NAME"],
)

# A temp table to feed a multi-column join
tmp = arcsmith.tbl.from_rows(
    f"{arcsmith.ws.temp_space()}/area_xwalk", rows, ["AREA_CODE", "AREA_NAME"],
)
arcsmith.tbl.join_table(fc, "AREA_CODE", tmp, "AREA_CODE", ["AREA_NAME"])

# A red-bus ("Jammer") fleet roster as a standalone table
rows = [
    (1, "Going-to-the-Sun", 17),
    (2, "Many Glacier", 17),
    (3, "Two Medicine", 17),
]
arcsmith.tbl.from_rows("C:/data/glacier.gdb/red_buses", rows, ["BUS_ID", "ROUTE", "SEATS"])
```

---

## get_table

Retrieves standalone table(s) from a map by display name or data source path. Matching by `table_name` returns all matches; matching by `table_source` returns at most the first match. Exactly one must be provided.

```python
get_table(target_map, table_name=None, table_source=None) -> list
```

| Parameter      | Type            | Default  | Description                                                          |
|----------------|-----------------|----------|---------------------------------------------------------------------|
| `target_map`   | `arcpy.mp.Map`  | required | Map object to search.                                               |
| `table_name`   | `str`           | `None`   | Display name to match. All matching tables are returned.            |
| `table_source` | `str` or `Path` | `None`   | Data source path to match. Only the first exact match is returned.  |

!!! success "Returns"
    list of `arcpy.mp.Table`: all matching tables. When matching by `table_source`, the list has at most one entry.

!!! failure "Raises"
    `ValueError` if neither or both of `table_name` and `table_source` are provided, or if no matching table is found in the map.

**Examples**

```python
# Get every standalone table named "areas"
tables = arcsmith.tbl.get_table(target_map, table_name="areas")

# Get a single table by data source path
tables = arcsmith.tbl.get_table(target_map, table_source="C:/data/glacier.gdb/areas")
```

---

## join_lookup

Adds a field and populates it from a 1:1 lookup keyed on an existing field. This is the fast, table-free form of a join: for each row, the value in `key_field` is looked up in `mapping` and written to `out_field` via an `UpdateCursor`.

```python
join_lookup(input_fc, key_field, mapping, out_field, field_type,
            default=None, length=None, overwrite=False) -> dict[str, int]
```

| Parameter    | Type                          | Default  | Description                                                                                                                                                                                                                       |
|--------------|-------------------------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc`   | `str` or `Path`               | required | Feature class (or table) to add the field to. Edited in place.                                                                                                                                                                    |
| `key_field`  | `str`                         | required | Existing field whose values are looked up in `mapping`. Matched case-insensitively by name; the cell *values* must match the dict keys by type, for example integer keys for a `LONG` field. See the note on key matching.             |
| `mapping`    | `dict` or iterable of `(key, value)` | required | The lookup. A `dict` is used directly; any other iterable is treated as `(key, value)` pairs and converted (last pair wins on duplicates).                                                                                |
| `out_field`  | `str`                         | required | Name of the field to create and populate. If it already exists, see `overwrite`.                                                                                                                                                  |
| `field_type` | `str`                         | required | arcpy field type for `out_field` (`"TEXT"`, `"SHORT"`, `"LONG"`, `"FLOAT"`, `"DOUBLE"`, `"DATE"`). Used when the field is created; when an existing field is reused (`overwrite=True`) its on-disk type is kept and a warning is raised if it differs. |
| `default`    | scalar                        | `None`   | Value written to `out_field` when a row's key is absent from `mapping`. Default `None` (leaves the cell `NULL`). Pass e.g. `"N/A"` to mirror the canonical-blank convention of `arcsmith.flds.clean_blanks`.                       |
| `length`     | `int`                         | `None`   | Field length, used only when `field_type` is `"TEXT"` and the field is being created. Default `None` (arcpy's default length).                                                                                                    |
| `overwrite`  | `bool`                        | `False`  | Controls behavior when `out_field` already exists. If `False` (default), a `ValueError` is raised. If `True`, the existing field is reused and repopulated (its type is not changed).                                             |

!!! success "Returns"
    dict of `str` to `int`: `{"matched": n, "unmatched": m}`. This is how many rows found a key in `mapping` versus fell back to `default`.

!!! failure "Raises"
    `ValueError` if `key_field` is not found in `input_fc`, or if `out_field` exists and `overwrite` is `False`.

!!! note "Pairs with `unique_values`"
    `join_lookup` pairs directly with [`arcsmith.flds.unique_values`](flds.md#unique_values). Pull the distinct keys, build a `{key: value}` dict in caller code, and merge it back in one call. For one-to-many relationships, or to transfer several columns from an existing table, use [`join_table`](#join_table) instead, since a dict cannot represent those.

!!! note "Only one column is touched"
    The lookup keys live in the `mapping` dict in memory and are never written to the table, so there is no second key column to clean up afterward. The function reads `key_field` and writes `out_field`, and nothing else changes. The redundant-key concern that applies to a table join does not arise here.

!!! warning "Key matching is by value and not coerced"
    If `key_field` holds strings but the dict keys are integers, every row falls to `default`. When no row matches anything, a warning is raised flagging a likely key-type mismatch. This is the most common cause of a silently empty join. Check that the values in `key_field` match the dict key type.

**Examples**

```python
# From a list of pairs
pairs = [(1, "Low"), (2, "Medium"), (3, "High")]
arcsmith.tbl.join_lookup(fc, "BEAR_RISK", pairs, "BEAR_RISK_LABEL", "TEXT")

# The full unique-values loop
area_codes = arcsmith.flds.unique_values(fc, "AREA_CODE")
area_name = {a: area_name_for(a) for a in area_codes}      # caller's logic
counts = arcsmith.tbl.join_lookup(
    fc, "AREA_CODE", area_name, "AREA_NAME", "TEXT", default="Unknown",
)
arcpy.AddMessage(f"{counts['unmatched']} row(s) had no area.")

# Attach lodging/boat capacity to named facilities
capacity = {
    "Lake McDonald Lodge": 82,
    "East Glacier Lodge": 161,
    "St. Mary Lake Boats": 49,
}
arcsmith.tbl.join_lookup(landmarks, "NAME", capacity, "CAPACITY", "SHORT")

```

---

## join_table

Joins an external table to a feature class permanently, copying its columns in. Wraps `arcpy.management.JoinField`: the selected columns from `source_table` are written into `input_fc` and persist on disk.

```python
join_table(input_fc, in_field, source_table, join_field, fields=None, keep=True) -> str
```

| Parameter      | Type            | Default  | Description                                                                                                                                                                  |
|----------------|-----------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `input_fc`     | `str` or `Path` | required | Target feature class (the "left" side of the join). Edited in place.                                                                                                         |
| `in_field`     | `str`           | required | Field in `input_fc` to join on. Matched case-insensitively.                                                                                                                  |
| `source_table` | `str` or `Path` | required | Table or feature class supplying the new columns. May be any table arcpy can read, such as a geodatabase table, a feature class, or an on-disk table like a dBASE (`.dbf`) or CSV. |
| `join_field`   | `str`           | required | Field in `source_table` to match against `in_field`. Matched case-insensitively.                                                                                            |
| `fields`       | list of `str`   | `None`   | Field names from `source_table` to act on. When `keep` is `True` (the default) these are the columns to transfer and all others are skipped. When `keep` is `False` these are the columns to skip and all other transferable columns are brought across, so you can name the few columns to drop instead of the many to keep. Non-transferable system fields such as the Object ID, geometry, and Global ID are never transferred in either mode. To drop the redundant join key when the two keys have different names, include `join_field` in this list with `keep` set to `False`. Default `None` (all transferable columns). |
| `keep`         | `bool`          | `True`   | If `True` (the default), `fields` lists the columns to transfer. If `False`, `fields` lists the columns to skip. Ignored when `fields` is `None`.                            |

!!! success "Returns"
    `str`: the `input_fc` path, now carrying the joined columns.

!!! failure "Raises"
    `ValueError` if `in_field` is not found in `input_fc`, if `join_field` is not found in `source_table`, if any name in `fields` is not found in `source_table`, or if the resolved field list is empty. The list is empty when `keep` is `False` and every transferable column is dropped, or when `keep` is `True` and `fields` is an empty list.

!!! note "When to use `join_table`"
    Use this (rather than [`join_lookup`](#join_lookup)) when the lookup already exists as a table, or when you want to transfer several columns in one operation. To build a source from in-memory Python data, create it with [`from_rows`](#from_rows) and pass it here.

!!! warning "Index cost in a loop"
    `JoinField` builds an index on each call, so it is well suited for deliverable-grade joins, but slow inside a loop over many small joins.

**Examples**

```python
# Copy an area label onto every trail
arcsmith.tbl.join_table(
    trails, "AREA_CODE", areas_tbl, "AREA_CODE", ["AREA_NAME"],
)

# Build a crosswalk from Python data, then join it
rows = [("NF", "North Fork"), ("LM", "Lake McDonald"), ("MG", "Many Glacier")]
area_xwalk = arcsmith.tbl.from_rows(
    f"{arcsmith.ws.temp_space()}/area_xwalk", rows, ["AREA_CODE", "AREA_NAME"],
)
arcsmith.tbl.join_table(trails, "AREA_CODE", area_xwalk, "AREA_CODE", ["AREA_NAME"])

# Keep everything from a wide area_info table except a few columns and the join key
arcsmith.tbl.join_table(
    trails, "AREA_CODE", area_info, "AREA_CODE",
    fields=["AREA_CODE", "CENTROID_LAT", "CENTROID_LON", "STATUS_CODE"], keep=False,
)
```

---

## remove_from_map

Removes standalone table(s) from a map by table reference, display name, or data source path.

```python
remove_from_map(target_map, table_name=None, table_source=None, silent=False, *, table=None) -> list
```

| Parameter      | Type                                          | Default  | Description                                                                                                  |
|----------------|-----------------------------------------------|----------|--------------------------------------------------------------------------------------------------------------|
| `target_map`   | `arcpy.mp.Map`                                | required | Map object to remove table(s) from.                                                                          |
| `table_name`   | `str`                                         | `None`   | Display name to match. All standalone tables with this name are removed.                                     |
| `table_source` | `str` or `Path`                               | `None`   | Data source path to match. The first match is removed. Tables without a data source cannot be matched this way; match those by `table_name`. |
| `silent`       | `bool`                                        | `False`  | If `True`, return an empty list instead of raising when a name/source match finds nothing. Invalid argument combinations still raise. No effect in `table` mode. |
| `table`        | `arcpy.mp.Table` or list of `arcpy.mp.Table`  | `None`   | The exact table object(s) to remove. **Keyword-only.** No scan or name/source matching is performed. Mutually exclusive with `table_name` and `table_source`. |

!!! success "Returns"
    list of `arcpy.mp.Table`: all tables that were removed.

!!! failure "Raises"
    `ValueError` if `table` is combined with `table_name` or `table_source`, or if neither nor both of `table_name`/`table_source` are provided when `table` is omitted; or if a name/source match finds nothing and `silent=False`.

!!! note "Matching modes"
    Exactly one of `table`, `table_name`, or `table_source` must be used per call.

    - **`table`** removes the exact object(s) given.
    - **`table_name`** removes **all** standalone tables with that name.
    - **`table_source`** removes the first match.

**Examples**

```python
# Remove the exact table you grabbed
areas = arcsmith.tbl.get_table(current_map, table_name="areas")[0]
arcsmith.tbl.remove_from_map(current_map, table=areas)

# Remove all tables named "scratch", quietly if none are present
arcsmith.tbl.remove_from_map(current_map, table_name="scratch", silent=True)
```

<br><br><br><br><br>
