---
hide:
  - toc
---

<div class="as-hero" markdown>
<div class="as-hero__eyebrow">For tool builders</div>
<h2 class="as-hero__title">ArcSmith documentation</h2>
<p class="as-hero__sub">ArcSmith is a Python library for GIS researchers that want to shape rough scripts into polished .pyt tools. ArcSmith covers parameter state management, layer outputs, field mappings, feature-class filtering, table joins, and workspace setup through six focused modules.</p>
<p class="as-hero__sub" style="margin-bottom:0"><a class="as-hero__link" href="guides/quick_start">Getting started &rarr;</a></p>
</div>

---

<div class="grid cards" markdown>

-   arcsmith<span class="as-mod">.param</span>

    ---

    Named helpers for `updateParameters`. Parameter state detection, cascade resets, dropdown population, and controlling groups of dependent parameters.

    [:octicons-arrow-right-24: Reference sheet](reference/param.md)

-   arcsmith<span class="as-mod">.lyr</span>

    ---

    Add layers to a map with optional stroke/fill or `.lyrx` symbology, retrieve or remove layers by name or source, and organize layers into groups.

    [:octicons-arrow-right-24: Reference sheet](reference/lyr.md)

-   arcsmith<span class="as-mod">.ws</span>

    ---

    Create the output geodatabase and its parent folder in one call. Route intermediate outputs to `memory` or scratch GDB with a single flag.

    [:octicons-arrow-right-24: Reference sheet](reference/ws.md)

-   arcsmith<span class="as-mod">.fc</span>

    ---

    Build SQL WHERE clauses with automatic delimiting and quoting, including multi-value IN filters. Export a feature class to a new location with optional field and row filtering, validate geometry, and compute area.

    [:octicons-arrow-right-24: Reference sheet](reference/fc.md)

-   arcsmith<span class="as-mod">.flds</span>

    ---

    Build field mappings, keep or drop fields when copying, standardize blank values, and list column names or unique values for dropdown population.

    [:octicons-arrow-right-24: Reference sheet](reference/flds.md)

-   arcsmith<span class="as-mod">.tbl</span>

    ---

    Create standalone tables from in-memory rows, populate a field from a `{key: value}` lookup with no physical table, and permanently join an external table's columns into a feature class.

    [:octicons-arrow-right-24: Reference sheet](reference/tbl.md)

</div>

<div class="as-download-strip">

  <div class="as-download-strip__text">

    <p class="as-download-strip__title">Module demonstration toolboxes</p>

    <p class="as-download-strip__sub">Ready-to-open demo toolboxes. One <code>.atbx</code> file per ArcSmith module.</p>

  </div>

  <a class="as-download-strip__btn" href="">Download Coming Soon</a>

</div>


<br>
<div class="as-section-hero">
<div class="as-section-hero__eyebrow">Reference</div>
<h2 class="as-section-hero__title">Function references</h2>
<p class="as-section-hero__sub">All functions listed alphabetically within each module.</p>
</div>

## <a class="as-mod-link" href="reference/param">arcsmith<span class="as-mod">.param</span></a>

Named helpers for `updateParameters` and `updateMessages`. Covers parameter state detection, cascade resets, dropdown population, controlling groups of dependent parameters, and timely self-clearing validation messages.

| Function | Description |
|---|---|
| [`cascade_clear`](reference/param.md#cascade_clear) | Clear downstream parameters the moment an upstream value changes |
| [`cascade_populate`](reference/param.md#cascade_populate) | Assign a value to downstream parameters when an upstream value changes |
| [`checkbox_dependence`](reference/param.md#checkbox_dependence) | Show, hide, and seed parameters controlled by a checkbox |
| [`drop_populate`](reference/param.md#drop_populate) | Fill a parameter's dropdown list |
| [`dynamic_dropdown`](reference/param.md#dynamic_dropdown) | Enable and disable parameter groups based on a dropdown selection |
| [`flag`](reference/param.md#flag) | Show a self-clearing message on a parameter while a condition holds |
| [`require`](reference/param.md#require) | Prompt for a parameter that must be filled before the tool runs, self-clearing |
| [`require_one_of`](reference/param.md#require_one_of) | Prompt when at least one of a group of parameters must be filled |
| [`state`](reference/param.md#state) | Translate `altered` + `hasBeenValidated` into a single readable state string |
| [`to_path`](reference/param.md#to_path) | Resolve a feature class or layer parameter to its catalog path |

---

## <a class="as-mod-link" href="reference/lyr">arcsmith<span class="as-mod">.lyr</span></a>
 
Add layers to a map with optional `.lyrx` symbology, apply symbology to existing layers, apply simple inline fill and stroke, retrieve or remove layers by display name or data source path, reorder layers within their level, and organize layers into group layers.
 
| Function | Description |
|---|---|
| [`add`](reference/lyr.md#add) | Add a data source to a map as a new layer, with optional symbology and display name |
| [`add_to_grp`](reference/lyr.md#add_to_grp) | Move an existing layer into a group layer, with optional precise ordering and removal of the original |
| [`apply_lyrx`](reference/lyr.md#apply_lyrx) | Apply `.lyrx` symbology to a layer object, or to layers in the map matched by name or source |
| [`get`](reference/lyr.md#get) | Retrieve layers from the map TOC by display name or data source path |
| [`get_grp`](reference/lyr.md#get_grp) | Retrieve group layer(s) from the map TOC by display name |
| [`make_grp`](reference/lyr.md#make_grp) | Create a group layer, optionally moving existing layers into it on creation |
| [`move`](reference/lyr.md#move) | Reorder a layer within its current TOC level, relative to a sibling or to the top/bottom |
| [`remove`](reference/lyr.md#remove) | Remove layers of any type from the map TOC by display name or data source path |
| [`simple_sym`](reference/lyr.md#simple_sym) | Apply simple fill color, fill opacity, stroke color, and stroke width to a layer, or apply a named style preset |

For ready-made fills and cartographic presets, plus the hollow boundary presets, used by `simple_sym`, see the [style presets](reference/lyr_presets.md) catalog.
 
---

## <a class="as-mod-link" href="reference/ws">arcsmith<span class="as-mod">.ws</span></a>

Create the output geodatabase and its parent folder in one call. Route intermediate outputs to `memory` or scratch GDB by flipping a single flag.

| Function | Description |
|---|---|
| [`init_gdb`](reference/ws.md#init_gdb) | Create a file geodatabase, creating the parent folder if needed |
| [`temp_space`](reference/ws.md#temp_space) | Return a workspace path for intermediate outputs, either memory or scratch GDB |

---

## <a class="as-mod-link" href="reference/fc">arcsmith<span class="as-mod">.fc</span></a>

Build SQL WHERE clauses with automatic field delimiting and value quoting, including multi-value IN filters. Export a feature class to a new location with optional field and row filtering, including a straight copy into a geodatabase. The module also validates geometry types and computes polygon area.

| Function | Description |
|---|---|
| [`build_where`](reference/fc.md#build_where) | Build a SQL WHERE clause for a single field, handling delimiters and quoting automatically |
| [`build_where_in`](reference/fc.md#build_where_in) | Build a SQL IN or NOT IN clause for a list of values, handling delimiters and quoting automatically |
| [`export_fc`](reference/fc.md#export_fc) | Export a feature class to a new location with optional field and row filtering, including copying one into a geodatabase |
| [`get_area`](reference/fc.md#get_area) | Return the area of a polygon feature class with optional unit conversion |
| [`validate_geom_type`](reference/fc.md#validate_geom_type) | Check whether a feature class has an expected geometry type |

---

## <a class="as-mod-link" href="reference/flds">arcsmith<span class="as-mod">.flds</span></a>

Build field mappings, add/rename/delete fields in place, keep or drop fields when copying a feature class, standardize blank values across string fields, and list column names or unique values for dropdown population.

| Function | Description |
|---|---|
| [`add_fld`](reference/flds.md#add_fld) | Add a new field to a feature class or table in place |
| [`build_fld_map`](reference/flds.md#build_fld_map) | Build a `FieldMappings` object retaining or dropping specified fields |
| [`clean_blanks`](reference/flds.md#clean_blanks) | Standardize blank-like values in string fields to a single canonical value |
| [`del_fld`](reference/flds.md#del_fld) | Delete one or more fields from a feature class or table in place |
| [`list_cols`](reference/flds.md#list_cols) | Return the field names present in a feature class |
| [`rename_fld`](reference/flds.md#rename_fld) | Rename a field, and optionally its alias, in place |
| [`unique_values`](reference/flds.md#unique_values) | Return the unique values or value combinations present in one or more fields |

---

## <a class="as-mod-link" href="reference/tbl">arcsmith<span class="as-mod">.tbl</span></a>

Create standalone tables from in-memory rows, append rows to an existing table, populate a field from a `{key: value}` lookup without building a physical table, permanently join an external table's columns into a feature class, and add, find, or remove standalone tables in a map.

| Function | Description |
|---|---|
| [`add_rows`](reference/tbl.md#add_rows) | Append rows of Python data to an existing table or feature class |
| [`add_to_map`](reference/tbl.md#add_to_map) | Add a standalone table to a map's table-of-contents |
| [`from_rows`](reference/tbl.md#from_rows) | Create a standalone table from an in-memory list of rows, with explicit or inferred field types |
| [`get_table`](reference/tbl.md#get_table) | Retrieve standalone table(s) from a map by display name or data source path |
| [`join_lookup`](reference/tbl.md#join_lookup) | Add a field and populate it from a 1:1 `{key: value}` lookup, with no physical table |
| [`join_table`](reference/tbl.md#join_table) | Join an external table to a feature class permanently, copying its columns in |
| [`remove_from_map`](reference/tbl.md#remove_from_map) | Remove standalone table(s) from a map by display name or data source path |

<br>
<br>
<br>
<br>
<br>