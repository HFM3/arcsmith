# Changelog

All notable changes to ArcSmith are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
from 1.0.0 onward.

> **Pre-1.0 notice.** While the version is `0.x`, the public API is still
> settling and breaking changes can land in any release. The renames and
> behavior changes below are the reason 1.0 has not been cut yet: 1.0 is the
> point at which this surface is frozen and changes start following SemVer.
>
> Release dates for `0.0.1`–`0.0.5` are not recorded; these predate version
> control on the project, so entries are reconstructed from the published
> distributions on PyPI rather than from a commit history.

## [0.0.8]

### Changed
- **Breaking:** `tbl.get_table` renamed to `tbl.get` for parity with `lyr.get`
  and the library's terse public-name convention. The signature is otherwise
  unchanged: `get(target_map, table_name=None, table_source=None)`. Update calls
  from `tbl.get_table(...)` to `tbl.get(...)`.
- Functions no longer emit informational `arcpy.AddMessage` output. Progress and
  result messages (table created, fields added, geodatabase reused, etc.) are
  left to the calling tool, so the library stays quiet in the geoprocessing pane
  by default. Return values are unchanged. Data-problem `arcpy.AddWarning`
  notices (e.g. unmatched join keys, skipped fields) are retained.

## [0.0.7]

### Added
- `lyr.move`: reorder a layer within its current level in the table of contents,
  either relative to a sibling (`relative_to` + `placement`) or to the top or
  bottom of its level (`position="TOP"`/`"BOTTOM"`). It changes order only, not
  grouping, and leaves a layer already at the requested edge in place.

### Changed
- **Breaking:** `lyr.apply_lyrx` reworked to the same dual-mode shape as
  `lyr.simple_sym`: it now accepts a single layer object as `lyr` (returned
  directly) in addition to map lookup. The signature is now
  `apply_lyrx(lyrx_src, lyr=None, *, target_map=None, lyr_name=None,
  lyr_source=None, geom_type=None)`, so `lyrx_src` is the first argument and
  `target_map` is keyword-only. Existing map-lookup calls such as
  `apply_lyrx(target_map, lyrx_src, lyr_name=...)` must move to
  `apply_lyrx(lyrx_src, target_map=target_map, lyr_name=...)`.
- **Breaking:** keyword-only arguments tightened across `lyr` for consistency
  with `add`/`simple_sym`/`apply_lyrx`. `get` and `remove` now take the
  match/options arguments keyword-only (everything after `target_map`):
  `get(target_map, *, lyr_name=None, lyr_source=None, geom_type=None)` and
  `remove(target_map, *, lyr_name=None, lyr_source=None, geom_type=None,
  silent=False, layer=None)`. `get_grp` makes `silent` keyword-only
  (`get_grp(target_map, grp_name=None, *, silent=False)`), and `add_to_grp`
  makes its ordering options keyword-only
  (`add_to_grp(target_map, grp_lyr, layer, *, position="BOTTOM",
  relative_to=None, placement="AFTER", remove_original=True)`). Calls that
  passed these positionally must switch to keywords, e.g.
  `get(m, "rivers")` becomes `get(m, lyr_name="rivers")`.

## [0.0.6]

### Added
- `tbl.add_to_map`, `tbl.remove_from_map`, `tbl.get_table`: add, find, and
  remove standalone tables in a map's table of contents (the table twins of the
  `lyr` add/get/remove helpers).
- `lyr.add` now applies an attractive default style to a new feature layer when
  no symbology is requested: a curated simple-fill preset matched to the layer's
  geometry (polygon fill, point marker, or line stroke) at a rotating random
  hue, so a plain add looks intentional instead of landing on ArcGIS's default.
- In-memory dataset support in `lyr.add` and `tbl.add_to_map`: a `memory\...`
  source is staged into a layer/table view automatically before being added to
  the map.
- `lyr.simple_sym` gains a `strict_geom` parameter (default `False`).
- Expanded the `lyr` style-preset catalog: added per-hue point (`simple_pt_*`)
  and line (`simple_ln_*`) companion presets to the existing simple-fill set,
  plus additional palette colors, so points, lines, and polygons of the same hue
  share a coordinated look.
- `flds.add_fld`, `flds.rename_fld`, `flds.del_fld`: create, rename, and delete
  fields in place (wrapping `AddField`, `AlterField`, and `DeleteField`),
  rounding out the in-place schema operations.
- `tbl.add_rows`: append rows of Python data to an existing table or feature
  class via an `InsertCursor`, the append complement to `from_rows`. Cursor
  tokens such as `SHAPE@` pass through, so geometry can be written alongside
  attributes.
- `lyr.make_grp`: create a group layer, optionally moving existing layers into
  it on creation.
- `flds.list_cols` gains a keyword-only `include_oid` flag to include the Object
  ID alongside the user-defined fields (for ID-field dropdowns) while still
  excluding the other system fields. The OID is matched by field type, so it is
  found whatever it is named (`OBJECTID`, `FID`, `OID`).
- Type annotations across the public API, including `Literal` types on closed
  string-enum arguments (`lyr` position/placement/geom_type, `fc.get_area`
  units, `flds`/`tbl` field types), so editors autocomplete the valid values and
  type checkers flag typos before runtime.
- `param.require`, `param.require_one_of`, `param.flag`: self-clearing
  validation-message helpers for `updateMessages`. They show a gently-worded,
  well-timed prompt for a conditionally required parameter and clear it the
  moment the condition is met, replacing hand-rolled `setErrorMessage` blocks
  that scold mid-edit and leave stale errors behind. `block=False` makes the
  message a non-blocking warning.

### Changed
- **Breaking:** `lyr` functions renamed for brevity: `get_lyr` → `get`,
  `get_grp_lyr` → `get_grp`, `add_to_group` → `add_to_grp`. Update existing
  calls accordingly.
- **Breaking:** `flds.build_field_map` renamed to `flds.build_fld_map`, adopting
  the same `fld` abbreviation as the new `add_fld`/`rename_fld`/`del_fld`. Update
  existing calls accordingly.
- **Breaking (behavior):** `lyr.simple_sym` no longer hard-blocks a preset whose
  intended geometry differs from the target layer. Geometry is now permissive by
  default. A preset's style is mapped onto whatever the target supports. Pass
  `strict_geom=True` to restore the previous raise-on-mismatch behavior.
- **Breaking:** `lyr.add` made `lyrx_src` keyword-only and added keyword-only
  `preset` and explicit style overrides (`fill_color`, `fill_opacity`,
  `stroke_color`, `stroke_width`). Calls that passed `lyrx_src` positionally must
  now pass it by name.
- `lyr.remove` now matches layers of any type (feature, raster, group, and so
  on), not just feature layers, so it can remove layers that `get` and the
  symbology helpers skip. Removing a group layer removes its children with it.
- `fc.export_fc` now wraps `arcpy.conversion.ExportFeatures` instead of the
  deprecated `arcpy.conversion.FeatureClassToFeatureClass`. Output is unchanged;
  this also preserves a `.shp` extension on shapefile outputs, which the previous
  implementation could drop.
- `requires-python` lowered from `>=3.13` to `>=3.11` to support ArcGIS Pro 3.3+
  (Pro 3.3 was the first to ship Python 3.11; Pro 3.6+ ships 3.13). See the
  Compatibility page.
- Packaging: the source distribution is now built from an explicit allowlist
  (`src/arcsmith`, `tests`, and metadata files) via
  `[tool.hatch.build.targets.sdist]`, and the wheel target is pinned to
  `src/arcsmith`. Unrelated files in the build directory can no longer be
  bundled, which is the class of mistake that `0.0.3` was pulled for.
- Relicensed from GPL-3.0 to MIT. The `LICENSE` file, the `pyproject.toml`
  license field, and every module's source header (now a single
  `SPDX-License-Identifier: MIT` line) were updated together.
- Modules adopted `from __future__ import annotations`, so the new type
  annotations carry no import-time cost and the package keeps importing without
  arcpy present, which the test suite relies on.

### Fixed
- `fc.build_where` and `fc.build_where_in` now escape embedded single quotes in
  string values, via a shared `_sql_quote` helper, so a value like `St. Mary's`
  produces valid SQL (`'St. Mary''s'`) instead of a malformed clause. Previously
  the value was wrapped in quotes without escaping.
- `param.checkbox_dependence` and `param.dynamic_dropdown` no longer overwrite a
  dependent's value when a tool is re-opened from its run history. A new internal
  check distinguishes a genuine user toggle from a history recall/rerun (on a
  recall the dependents reload unvalidated), so restored values and deliberate
  clears survive the reload instead of being re-seeded from `shown_value`.

### Documentation
- Stopped documenting the private `lyr._seed_styles` helper in the public
  `lyr.add` examples.

## [0.0.5]

### Added
- Group-layer support in `lyr`: `add_to_group` (move a layer into a group layer)
  and `get_grp_lyr` (retrieve group layers by name).

## [0.0.4]

### Added
- New `tbl` module: in-memory table creation, key/value lookups, and table
  joins.
- `lyr.simple_sym` and the `PRESETS` style registry.

### Changed
- Packaging: the source distribution no longer bundles the built docs site,
  combo samples, and zip artifacts that `0.0.3` accidentally included. This was
  the fix that `0.0.3` was pulled for; `0.0.4` is the clean re-release with
  `tbl` and `simple_sym` added on top.

## [0.0.3] (deleted from PyPI)

Published and then deleted from PyPI because its source distribution bundled
files that were not meant for publishing (the built `arcsmith-docs/` site,
`combo_samples/`, and loose zip/html artifacts). The library code itself was
sound and was re-released, with a clean distribution, as `0.0.4`. The version is
permanently retired on PyPI; the wheel is kept locally in `dist/` for reference.

### Added
- The `fc` (WHERE-clause building, filtered export, area, geometry validation),
  `flds` (field maps, blank cleaning, unique values, column listing), and `ws`
  (geodatabase creation, temp workspace) modules. `lyr` carried `add`,
  `apply_lyrx`, `get_lyr`, and `remove` at this point; `simple_sym` and
  `PRESETS` did not arrive until `0.0.4`.

### Changed
- The `layer` module was renamed to `lyr`.

## [0.0.2]

### Added
- First functional release: the `param` module (parameter-state helpers,
  cascade resets, dropdown population, checkbox/dropdown dependence) and the
  `layer` module (add layers, apply symbology).
- Project summary set to "Utilities for building clean, maintainable ArcPy
  toolboxes."

## [0.0.1]

### Added
- Initial placeholder release to reserve the `arcsmith` name on PyPI. Package
  scaffolding only; no public functions.
