<div class="as-hero" markdown>
<div class="as-hero__eyebrow">arcsmith.lyr</div>
<h2 class="as-hero__title">Layer</h2>
<p class="as-hero__sub">Helpers for adding layers to a map and applying .lyrx symbology or simple inline fill/stroke programmatically.</p>
<ul class="as-hero__highlights">
<li>Add data sources to a map with optional symbology and display name</li>
<li>Style from named presets (e.g. <code>simple_blue</code>, <code>lake</code>, <code>highlight_pink</code>) for attractive output</li>
<li>Retrieve or remove layers from the map TOC with optional geometry type filtering</li>
<li>Create group layers, retrieve them by name, and move existing layers into a group with precise ordering</li>
<li>Reorder a layer within its current level, relative to a sibling or to the top/bottom</li>
</ul>
</div>

!!! tip "Style presets"
    For the full catalog of named symbology presets, including the `simple_*`
    families, refer to
    [Style presets](lyr_presets.md) page.

## Functions of the `lyr` module

## add

Adds a data source to a map as a new layer with optional symbology.

```python
add(target_map, lyr_src, lyr_name=None, *, lyrx_src=None, preset=None,
    fill_color=<omitted>, fill_opacity=<omitted>, stroke_color=<omitted>, stroke_width=<omitted>) -> arcpy.mp.Layer
```

Everything after `lyr_name` is keyword-only. Supply `lyrx_src`, `preset`, or any of the explicit style arguments to take control of symbology; `lyrx_src` and `preset` are mutually exclusive.

`<omitted>` marks a style argument you do not pass. It is distinct from `None`: omitting an argument falls back to the preset (or the random default), whereas passing `None` explicitly leaves that property as the layer already has it. Neither clears existing symbology.

| Parameter    | Type                               | Default  | Description                                                                      |
|--------------|------------------------------------|----------|----------------------------------------------------------------------------------|
| `target_map` | `arcpy.mp.Map`                     | required | Map object to add the layer to.                                                  |
| `lyr_src`    | `str`, `Path`, or `arcpy.Result`   | required | Path to the data source (feature class, raster, etc.) to add. arcpy `Result` objects (e.g. the return value of `arcpy.management.Dissolve`) are accepted and resolved to their output path automatically. |
| `lyr_name`   | `str`                              | `None`   | Display name for the layer in the TOC. Defaults to the source name.              |
| `lyrx_src`   | `str` or `Path`                    | `None`   | Keyword-only. Path to a `.lyrx` file. If provided, its symbology is applied and the stylish default is skipped. Mutually exclusive with `preset`. |
| `preset`     | `str` or `dict`                    | `None`   | Keyword-only. A registered preset name (a key of `PRESETS`) or a one-off style `dict`, applied via [`simple_sym`](lyr_presets.md). When omitted (and no explicit style args), a curated simple preset matched to the layer's geometry is applied at a random hue. Mutually exclusive with `lyrx_src`. |
| `fill_color` `fill_opacity` `stroke_color` `stroke_width` | see `simple_sym` | omitted | Keyword-only style overrides forwarded to `simple_sym`. Passing any suppresses the random default and applies the given style (on top of `preset` if also supplied). |

!!! success "Returns"
    `arcpy.mp.Layer`: the newly added layer.

!!! note "Styling only applies to simple feature layers"
    The automatic default fails soft: rasters, tables, and layers ArcGIS
    gives a non-`SimpleRenderer` default are returned untouched rather than
    raising. An explicitly requested `preset` or style on such a layer will
    surface the usual `simple_sym` error.

!!! note "Memory workspace"
    In-memory datasets (paths under `memory` or `in_memory`) are handled
    automatically. A map cannot consume an in-memory dataset directly, so the
    source is first staged into a layer, using `MakeRasterLayer` for raster data
    or `MakeFeatureLayer` otherwise, and that layer is added. A `memory\...`
    intermediate is therefore addable with no extra step. It still must be added
    here before `get`, `apply_lyrx`, or `remove` can see it in the TOC.

**Examples**

```python
# Add a layer with an attractive default style matched to its geometry
lyr = arcsmith.lyr.add(target_map, "path/to/trails")

# Add a layer with a custom display name
lyr = arcsmith.lyr.add(target_map, "path/to/landmarks", lyr_name="Lake McDonald Lodge")

# Add Glacier's red "Jammer" tour buses as a layer
lyr = arcsmith.lyr.add(target_map, "path/to/red_buses", lyr_name="Red Bus Tours")

# Add a layer styled from a named preset
lyr = arcsmith.lyr.add(target_map, "path/to/trails", preset="lake")

# Add a layer with explicit inline style
lyr = arcsmith.lyr.add(target_map, "path/to/trails", fill_color="#C8E6C9", stroke_width=1)

# Add a layer with a name and .lyrx symbology
lyr = arcsmith.lyr.add(target_map, "path/to/trails", lyr_name="Rivers", lyrx_src="path/to/trails.lyrx")

# Pass an arcpy Result directly (e.g. from Dissolve) and add to map with symbology
result = arcpy.management.Dissolve(in_fc, output_path, dissolve_field)
lyr = arcsmith.lyr.add(target_map, result, lyr_name="Park Boundary", lyrx_src="path/to/trails.lyrx")

# Add an in-memory intermediate (staged into a layer automatically)
arcpy.analysis.Clip(trails, aoi, "memory/trails_clip")
lyr = arcsmith.lyr.add(target_map, "memory/trails_clip", lyr_name="Trails (clipped)")
```

---

## add_to_grp

Moves an existing layer into a group layer, with optional precise ordering against a sibling, and optionally removes the original top-level layer.

```python
add_to_grp(target_map, grp_lyr, layer, *, position="BOTTOM",
           relative_to=None, placement="AFTER", remove_original=True) -> arcpy.mp.Layer
```

The three layer arguments are positional; every option after them (`position`, `relative_to`, `placement`, `remove_original`) is keyword-only.

`addLayerToGroup` only *copies* the layer into the group and leaves the original top-level layer in place, so this function runs the full sequence: copy into the group, locate the in-group copy, optionally move it relative to a sibling, and optionally remove the original.

| Parameter         | Type                   | Default  | Description                                                                                                       |
|-------------------|------------------------|----------|-------------------------------------------------------------------------------------------------------------------|
| `target_map`      | `arcpy.mp.Map`         | required | Map object containing both the group layer and the layer to move.                                                |
| `grp_lyr`         | `arcpy.mp.Layer`       | required | The destination group layer (e.g. from `get_grp`).                                                            |
| `layer`           | `arcpy.mp.Layer`       | required | The layer to move into the group (e.g. from `get`).                                                           |
| `position`        | `'TOP'` or `'BOTTOM'`  | `'BOTTOM'`| **Keyword-only.** Initial placement within the group, passed to `addLayerToGroup`. Case-insensitive.            |
| `relative_to`     | `arcpy.mp.Layer`       | `None`   | **Keyword-only.** A layer already inside the group to position the moved layer against. When given, a `moveLayer` call runs after the add. Must already be a child of `grp_lyr`. |
| `placement`       | `'BEFORE'` or `'AFTER'`| `'AFTER'`| **Keyword-only.** Where to place the moved layer relative to `relative_to`. Case-insensitive. Ignored when `relative_to` is `None`. |
| `remove_original` | `bool`                 | `True`   | **Keyword-only.** If `True`, remove the original top-level layer after copying, leaving only the in-group copy.   |

!!! success "Returns"
    `arcpy.mp.Layer`: the in-group copy of the layer.

!!! failure "Raises"
    `ValueError` if `position` is not `'TOP'` or `'BOTTOM'`, if `placement` is not `'BEFORE'` or `'AFTER'`, or if the in-group copy cannot be located after the add.

!!! note "Two-stage positioning"
    `position` decides the initial drop point and accepts only `'TOP'` or `'BOTTOM'`, the two placements arcpy allows on `addLayerToGroup`. For index-level control, pass `relative_to` together with `placement`. The in-group copy is repositioned with `moveLayer` after the add, placing it before or after the named sibling.

!!! note "The original layer"
    The copy made by `addLayerToGroup` shares a display name with the original top-level layer. By default `remove_original` deletes that original by reference, leaving only the in-group copy. Pass `remove_original=False` to keep both.

**Examples**

```python
# Move a layer into a group at the bottom, cleaning up the original
grp = arcsmith.lyr.get_grp(target_map, grp_name="Backcountry")[0]
riv = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
arcsmith.lyr.add_to_grp(target_map, grp, riv)

# Drop it at the top instead
arcsmith.lyr.add_to_grp(target_map, grp, riv, position="TOP")

# Place it directly above an existing sibling
roads = arcsmith.lyr.get(target_map, lyr_name="roads")[0]
riv = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
arcsmith.lyr.add_to_grp(target_map, grp, riv, relative_to=roads, placement="BEFORE")

# Keep the original top-level layer in place as well as the in-group copy
arcsmith.lyr.add_to_grp(target_map, grp, riv, remove_original=False)
```

---

## apply_lyrx

Applies symbology from a `.lyrx` file to one or more layers, by layer reference, display name, or data source path.

```python
apply_lyrx(lyrx_src, lyr=None, *,
           target_map=None, lyr_name=None, lyr_source=None, geom_type=None) -> arcpy.mp.Layer | list
```

Every argument after `lyr` is keyword-only.

| Parameter    | Type                                          | Default  | Description                                                                                                 |
|--------------|-----------------------------------------------|----------|-------------------------------------------------------------------------------------------------------------|
| `lyrx_src`   | `str` or `Path`                               | required | Path to the `.lyrx` file whose symbology is applied.                                                       |
| `lyr`        | `arcpy.mp.Layer`                              | `None`   | A single layer to style directly. Mutually exclusive with `target_map`, `lyr_name`, and `lyr_source`.       |
| `target_map` | `arcpy.mp.Map`                                | `None`   | **Keyword-only.** Map object containing the layer(s) to update. Required with `lyr_name` or `lyr_source`.   |
| `lyr_name`   | `str`                                         | `None`   | **Keyword-only.** Display name to match. All layers with this name are updated. Mutually exclusive with `lyr_source`. |
| `lyr_source` | `str` or `Path`                               | `None`   | **Keyword-only.** Data source path to match. Only the first exact match is updated. Mutually exclusive with `lyr_name`. |
| `geom_type`  | `'Point'`, `'Polyline'`, `'Polygon'`, or `'Multipoint'` | `None`   | **Keyword-only.** Geometry type filter when matching by `lyr_name`. Case-insensitive. Ignored when matching by `lyr_source` or `lyr`. |

!!! success "Returns"
    `arcpy.mp.Layer` in `lyr` mode. `list of arcpy.mp.Layer` in map-lookup mode.

!!! failure "Raises"
    `ValueError` if both `lyr` and map-lookup arguments are provided, or if neither mode is specified.

    `ValueError` if no matching layers are found (map-lookup mode).

!!! note "Matching modes"
    Exactly one of `lyr`, or `target_map` with `lyr_name` or `lyr_source`, must be used per call. Matching by `lyr_name` updates **all** layers with that name; matching by `lyr_source` updates only the **first** exact match.

!!! note "Memory workspace"
    Memory layers should always be matched by `lyr_name` using their TOC
    display name. Their internal data source path is not predictable and
    cannot be used reliably with `lyr_source`.

**Examples**

```python
# Style a layer object directly
arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", lyr)

# Update all layers named "rivers"
lyrs = arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", target_map=current_map, lyr_name="rivers")

# Update only polyline "rivers" layers
lyrs = arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", target_map=current_map, lyr_name="rivers", geom_type="Polyline")

# Update a single layer by data source path
lyrs = arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", target_map=current_map, lyr_source="path/to/trails")
```

---

## get

Retrieves layer(s) from the map TOC by display name or data source path.

```python
get(target_map, *, lyr_name=None, lyr_source=None, geom_type=None) -> list
```

Every argument after `target_map` is keyword-only.

| Parameter    | Type                                          | Default  | Description                                                                                                     |
|--------------|-----------------------------------------------|----------|-----------------------------------------------------------------------------------------------------------------|
| `target_map` | `arcpy.mp.Map`                                | required | Map object to search.                                                                                           |
| `lyr_name`   | `str`                                         | `None`   | **Keyword-only.** Display name to match. All layers with this name are returned.                                |
| `lyr_source` | `str` or `Path`                               | `None`   | **Keyword-only.** Data source path to match. Only the first exact match is returned.                            |
| `geom_type`  | `'Point'`, `'Polyline'`, `'Polygon'`, or `'Multipoint'` | `None`   | **Keyword-only.** Geometry type filter when matching by `lyr_name`. Case-insensitive. Ignored when matching by `lyr_source`. |

!!! success "Returns"
    list of `arcpy.mp.Layer`: all matching layers. When matching by `lyr_source`, the list contains at most one entry.

!!! failure "Raises"
    `ValueError` if neither or both of `lyr_name` and `lyr_source` are provided.

    `ValueError` if no matching layers are found in the map.

!!! note
    Exactly one of `lyr_name` or `lyr_source` must be provided on each call. Matching by `lyr_name` returns **all** layers with that name. Matching by `lyr_source` returns only the **first** exact match.

!!! note "Memory workspace"
    Memory layers should always be matched by `lyr_name` using their TOC
    display name. Their internal data source path is not predictable and
    cannot be used reliably with `lyr_source`.

**Examples**

```python
# Get all layers named "rivers"
lyrs = arcsmith.lyr.get(target_map, lyr_name="rivers")

# Get only polyline "rivers" layers
lyrs = arcsmith.lyr.get(target_map, lyr_name="rivers", geom_type="Polyline")

# Get a single layer by data source path
lyrs = arcsmith.lyr.get(target_map, lyr_source="path/to/trails")

# Get a memory layer by its TOC display name
lyrs = arcsmith.lyr.get(target_map, lyr_name="trails_memory")
```

---

## get_grp

Retrieves group layer(s) from the map TOC by display name.

```python
get_grp(target_map, grp_name=None, *, silent=False) -> list
```

| Parameter    | Type             | Default  | Description                                                                                          |
|--------------|------------------|----------|------------------------------------------------------------------------------------------------------|
| `target_map` | `arcpy.mp.Map`   | required | Map object to search.                                                                                |
| `grp_name`   | `str`            | `None`   | Display name to match. All matching group layers are returned. If omitted, every group layer in the map is returned. |
| `silent`     | `bool`           | `False`  | **Keyword-only.** If `True`, return an empty list instead of raising when a named match finds nothing. |

!!! success "Returns"
    list of `arcpy.mp.Layer`: all matching group layers.

!!! failure "Raises"
    `ValueError` if `grp_name` is given and no matching group layer is found, unless `silent=True`.

!!! note "No geometry or source filter"
    Group layers have no geometry and no data source, so this function has no `geom_type` filter and no `lyr_source` mode. That is why it is kept separate from `get` rather than being a flag on it. Pass `grp_name` to match by name, or omit it to return every group layer.

**Examples**

```python
# Get a group layer by name
grp = arcsmith.lyr.get_grp(target_map, grp_name="Backcountry")[0]

# Get every group layer in the map
grps = arcsmith.lyr.get_grp(target_map)

# Get a group layer if present, without raising when it is missing
grps = arcsmith.lyr.get_grp(target_map, grp_name="Scratch", silent=True)
```

---

## make_grp

Creates a group layer in a map and returns it, optionally moving existing layers into it as it is created. The new group is added as the topmost entry of its container: the map's table of contents by default, or the parent group when `parent_grp` is given.

```python
make_grp(target_map, grp_name, layers=None, *, parent_grp=None) -> arcpy.mp.Layer
```

Pass `layers` to fill the group in the same call instead of creating it empty and adding to it afterward. Each layer is moved in: it is copied into the group and its original top-level entry is removed, so it ends up only inside the group rather than duplicated. List order is kept top to bottom: each layer is added at the bottom of the group as the list is processed, so the first item in the list ends up at the top of the group and the last at the bottom. For finer control over a single layer, such as positioning it against a sibling or keeping the original top-level entry, create the group here and call [`add_to_grp`](#add_to_grp) per layer instead.

| Parameter    | Type                                          | Default  | Description                                                                                                                          |
|--------------|-----------------------------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------|
| `target_map` | `arcpy.mp.Map`                                | required | Map object to create the group layer in.                                                                                            |
| `grp_name`   | `str`                                         | required | Display name for the new group layer in the TOC.                                                                                    |
| `layers`     | `arcpy.mp.Layer` or list of `arcpy.mp.Layer`  | `None`   | Existing map layer(s) to move into the new group. List order is kept top to bottom in the group (first item at the top, last at the bottom). A single layer may be passed without a list. Each is removed from its original top-level position. Default `None` (the group is created empty). |
| `parent_grp` | `arcpy.mp.Layer`                              | `None`   | Keyword-only. An existing group layer to nest the new group inside; the new group becomes the topmost entry of that parent group. Default `None` (the new group is added directly to the map, as the topmost entry of the TOC). |

!!! success "Returns"
    `arcpy.mp.Layer`: the newly created group layer, holding any layers passed in `layers`.

!!! note "Group names are not unique"
    arcpy allows duplicate display names, so calling `make_grp` twice with the same `grp_name` produces two separate groups. Hold on to the returned layer to act on a specific group rather than relying on a later `get_grp` name lookup.

**Examples**

```python
# Create an empty group, then move a layer into it later
grp = arcsmith.lyr.make_grp(target_map, "Backcountry")
riv = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
arcsmith.lyr.add_to_grp(target_map, grp, riv)

# Create a group and fill it in one call
# (roads ends up above trails, matching the list order top to bottom)
roads = arcsmith.lyr.get(target_map, lyr_name="roads")[0]
trails = arcsmith.lyr.get(target_map, lyr_name="trails")[0]
grp = arcsmith.lyr.make_grp(target_map, "Transport", [roads, trails])

# Create a group nested inside another group
trails = arcsmith.lyr.make_grp(target_map, "Trails")
backcountry = arcsmith.lyr.make_grp(target_map, "Backcountry", parent_grp=trails)
```

---

## move

Reorders a layer within its current level in the table of contents, relative to a sibling or to the top/bottom of that level.

```python
move(target_map, layer, *, relative_to=None, placement="BEFORE", position=None) -> arcpy.mp.Layer
```

Everything after `layer` is keyword-only. The `move` function changes only the order of `layer` among its siblings, the layers that share its level or whichever group it lives in. It does not change grouping; the layer stays in the same container. To move a layer *into* a group, use [`add_to_grp`](#add_to_grp).

Two targeting modes are available and exactly one must be used per call:

| Mode | Arguments | Effect |
|---|---|---|
| **Relative** | `relative_to` (+ `placement`) | Drop `layer` just before/after a sibling |
| **Absolute** | `position` | Send `layer` to the top/bottom of its level |

| Parameter     | Type                   | Default    | Description                                                                                                      |
|---------------|------------------------|------------|------------------------------------------------------------------------------------------------------------------|
| `target_map`  | `arcpy.mp.Map`         | required   | Map object containing the layer to move.                                                                         |
| `layer`       | `arcpy.mp.Layer`       | required   | The layer to reorder.                                                                                            |
| `relative_to` | `arcpy.mp.Layer`       | `None`     | **Keyword-only.** A sibling layer to position `layer` against. Must share `layer`'s level. Mutually exclusive with `position`. |
| `placement`   | `'BEFORE'` or `'AFTER'`| `'BEFORE'` | **Keyword-only.** Where to place `layer` relative to `relative_to`. Case-insensitive. Ignored in absolute mode. |
| `position`    | `'TOP'` or `'BOTTOM'`  | `None`     | **Keyword-only.** Send `layer` to the top or bottom of its current level. Case-insensitive. Mutually exclusive with `relative_to`. |

!!! success "Returns"
    `arcpy.mp.Layer`: the moved layer (the same object passed in).

!!! failure "Raises"
    `ValueError` if neither or both of `relative_to` and `position` are provided.

    `ValueError` if `placement` is not `'BEFORE'`/`'AFTER'`, or `position` is not `'TOP'`/`'BOTTOM'`.

    `ValueError` if `relative_to` is not at the same level as `layer`.

!!! note "Order only, not grouping"
    `move` reorders a layer within its existing level. A layer at the map's top level stays at the top level; a layer inside a group is reordered within that group. An absolute move on a layer already at the requested edge is a no-op. arcpy allows duplicate display names at one level; in the rare case where every sibling shares `layer`'s name, an absolute move is left unchanged rather than guessing.

**Examples**

```python
roads = arcsmith.lyr.get(target_map, lyr_name="roads")[0]
rivers = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]

# Move a layer to just above a sibling
arcsmith.lyr.move(target_map, rivers, relative_to=roads, placement="BEFORE")

# Move a layer to just below a sibling
arcsmith.lyr.move(target_map, rivers, relative_to=roads, placement="AFTER")

# Send a layer to the top of its current level
arcsmith.lyr.move(target_map, rivers, position="TOP")

# Send a layer to the bottom of its current level
arcsmith.lyr.move(target_map, rivers, position="BOTTOM")
```

---

## remove

Removes layer(s) of any type (feature, raster, group, …) from the map TOC by layer reference, display name, or data source path.

```python
remove(target_map, *, lyr_name=None, lyr_source=None, geom_type=None, silent=False, layer=None) -> list
```

Every argument after `target_map` is keyword-only.

| Parameter    | Type                                          | Default  | Description                                                                                                     |
|--------------|-----------------------------------------------|----------|-----------------------------------------------------------------------------------------------------------------|
| `target_map` | `arcpy.mp.Map`                                | required | Map object to remove layer(s) from.                                                                             |
| `lyr_name`   | `str`                                         | `None`   | **Keyword-only.** Display name to match. All layers with this name are removed.                                 |
| `lyr_source` | `str` or `Path`                               | `None`   | **Keyword-only.** Data source path to match. The exact match is removed. Layers without a data source (e.g. group or basemap layers) cannot be matched this way; match those by `lyr_name`. |
| `geom_type`  | `'Point'`, `'Polyline'`, `'Polygon'`, or `'Multipoint'` | `None`   | **Keyword-only.** Geometry type filter when matching by `lyr_name`. Case-insensitive. Applies to feature layers only. Non-feature layers have no geometry and never match a `geom_type`. Ignored when matching by `lyr_source` or `layer`. |
| `silent`     | `bool`                                        | `False`  | **Keyword-only.** If `True`, return `0` instead of raising when a name/source match finds nothing. Invalid argument combinations still raise. No effect in `layer` mode. |
| `layer`      | `arcpy.mp.Layer` or list of `arcpy.mp.Layer`  | `None`   | **Keyword-only.** The exact layer object(s) to remove. No TOC scan or name/source matching is performed. Mutually exclusive with `lyr_name` and `lyr_source`. |

!!! success "Returns"
    list of `arcpy.mp.Layer`: all layers that were removed.

!!! failure "Raises"
    `ValueError` if `layer` is combined with `lyr_name` or `lyr_source`, or if neither nor both of `lyr_name`/`lyr_source` are provided when `layer` is omitted.

    `ValueError` if a name/source match finds no layers, unless `silent=True`.

!!! note "Matching modes"
    Exactly one of `layer`, `lyr_name`, or `lyr_source` must be used per call.

    - **`layer`** removes the exact object(s) given. This is the correct mode
      after `addLayerToGroup`, which copies the layer into the group and leaves
      the original top-level layer in place: pass the reference you already
      hold (e.g. from `get`) to remove just that one, leaving the in-group
      copy untouched. Matching by name would remove **both**, since they share
      a display name.
    - **`lyr_name`** removes **all** layers with that name.
    - **`lyr_source`** removes the exact match.

!!! note "Any layer type"
    Name and source matching consider layers of **any** type (feature, raster,
    group, etc.), so `remove` can clear a layer that symbology helpers such as
    `get` skip. Removing a group layer removes its children with it. A layer
    without a data source (e.g. a group or basemap layer) cannot be matched by
    `lyr_source`; match those by `lyr_name`.

!!! note "Memory workspace"
    Memory layers should always be matched by `lyr_name` using their TOC
    display name. Their internal data source path is not predictable and
    cannot be used reliably with `lyr_source`.

**Examples**

```python
# Remove the exact layer you hold, leaving an in-group copy intact
lyr = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
target_map.addLayerToGroup(grp_lyr, lyr)
arcsmith.lyr.remove(target_map, layer=lyr)

# Remove every layer returned by a query in one call
lyrs = arcsmith.lyr.get(target_map, lyr_name="rivers")
arcsmith.lyr.remove(target_map, layer=lyrs)

# Remove all layers named "rivers"
arcsmith.lyr.remove(target_map, lyr_name="rivers")

# Remove only polyline "rivers" layers
arcsmith.lyr.remove(target_map, lyr_name="rivers", geom_type="Polyline")

# Remove a single layer by data source path
arcsmith.lyr.remove(target_map, lyr_source="path/to/trails")

# Remove a raster or group layer by name (any layer type matches)
arcsmith.lyr.remove(target_map, lyr_name="Hillshade")
arcsmith.lyr.remove(target_map, lyr_name="Backcountry")  # group + its children

# Remove a memory layer by its TOC display name
arcsmith.lyr.remove(target_map, lyr_name="trails_memory")

# Remove a layer if present, without raising when it is missing
arcsmith.lyr.remove(target_map, lyr_name="scratch", silent=True)
```

---

## simple_sym

Applies simple fill and stroke symbology to one or more feature layers. No `.lyrx` file needed. Style values can be given individually, drawn from a named `preset`, or both.

```python
simple_sym(lyr=None, *, preset=None,
           fill_color=<omitted>, fill_opacity=<omitted>, stroke_color=<omitted>, stroke_width=<omitted>,
           strict_geom=False,
           target_map=None, lyr_name=None, lyr_source=None, geom_type=None) -> arcpy.mp.Layer | list
```

Every parameter after `lyr` is **keyword-only** (note the `*`), so style and targeting arguments cannot be passed positionally.

Two targeting modes are available and exactly one must be used per call:

| Mode             | Arguments | Returns |
|------------------|---|---|
| **Layer object** | `lyr` | `arcpy.mp.Layer` |
| **Layer lookup** | `target_map` + `lyr_name` or `lyr_source` | `list of arcpy.mp.Layer` |

| Parameter      | Type                           | Default  | Description                                                                                                                        |
|----------------|--------------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------|
| `lyr`          | `arcpy.mp.Layer`               | `None`   | A single layer to style directly. Mutually exclusive with `target_map`, `lyr_name`, and `lyr_source`.                             |
| `preset`       | `str` or `dict`                | `None`   | A registered preset name (a key of `PRESETS`) or a one-off style `dict` using the same keys as the style parameters below. Supplies a bundle of style values; any style parameter passed explicitly overrides the preset. See [Style presets](lyr_presets.md). |
| `fill_color`   | `tuple[int, int, int]` or `str`| omitted  | RGB fill color as `(R, G, B)` or a hex string (`"#ADBCE6"` or `"ADBCE6"`). Applied to Polygon and Point layers. Ignored for Polyline layers. |
| `fill_opacity` | `int` or `float`               | omitted  | Fill opacity as a percentage (0 to 100). Ignored for Polyline layers.                                                              |
| `stroke_color` | `tuple[int, int, int]` or `str`| omitted  | RGB stroke color as `(R, G, B)` or a hex string. Sets the outline on Polygon/Point layers. Sets the line color on Polyline layers. |
| `stroke_width` | `int` or `float`               | omitted  | Stroke/outline width in points.                                                                                                    |
| `strict_geom`  | `bool`                         | `False`  | If `True`, enforce a preset's intended geometry (mismatch raises in `lyr` mode, skips in map-lookup mode). If `False` (default), geometry is not enforced and the preset is applied to any geometry via the cross-geometry mapping below. Only presets carrying a `'geom'` key can be enforced. |
| `target_map`   | `arcpy.mp.Map`                 | `None`   | Map to search when targeting by name or source. Required with `lyr_name` or `lyr_source`.                                         |
| `lyr_name`     | `str`                          | `None`   | Display name to match. All matching layers are updated. Mutually exclusive with `lyr_source`.                                      |
| `lyr_source`   | `str` or `Path`                | `None`   | Data source path to match. Only the first exact match is updated. Mutually exclusive with `lyr_name`.                             |
| `geom_type`    | `'Point'`, `'Polyline'`, `'Polygon'`, or `'Multipoint'` | `None` | Geometry type filter when using `lyr_name`. Case-insensitive. Ignored with `lyr_source` or `lyr`. |

!!! success "Returns"
    `arcpy.mp.Layer` in `lyr` mode. `list of arcpy.mp.Layer` in map-lookup mode.

!!! failure "Raises"
    `ValueError` if both `lyr` and map-lookup arguments are provided, or if neither mode is specified.

    `ValueError` if no matching layers are found (map-lookup mode).

    `ValueError` if a layer's renderer is not a `CIMSimpleRenderer`.

    `ValueError` if `preset` is an unknown name, or is neither a `str` nor a `dict`.

    `ValueError` if a named preset's geometry does not match the layer **and** `strict_geom=True`, in `lyr` mode. In map-lookup mode the non-matching layer is skipped instead. With the default `strict_geom=False` no geometry check is performed. See [Style presets](lyr_presets.md).

!!! note "Geometry type behavior"
    By default (`strict_geom=False`) any preset style applies to any geometry; each property is mapped onto whatever the target supports. Style is applied through the arcpy.mp convenience properties `symbol.color` (body fill), `symbol.outlineColor`, and `symbol.outlineWidth` (outline), which ArcPy resolves per geometry:

    | Geometry | `fill_color` | `fill_opacity` | `stroke_color` | `stroke_width` |
    |---|---|---|---|---|
    | **Polygon** | fill | fill opacity | outline color | outline width |
    | **Point / Multipoint** | marker fill | marker opacity | marker outline color | marker outline width |
    | **Polyline** | dropped¹ | dropped¹ | line color | line width |

    A line carries no fill, so `fill_color`/`fill_opacity` have no native target and are dropped. The line takes its stroke only. Applying a polygon-oriented preset to a line therefore colors the line from the preset's stroke.

    A fully transparent fill (`fill_opacity=0`) renders a Polygon or Point as **hollow**. When only `fill_opacity` is supplied and the symbol has no existing fill color to retune, a transparent fallback fill is created so the hollow result is still produced.

!!! note "Omitted vs. None"
    The four style parameters default to *omitted* (you do not pass them). When omitted, the value falls back to the `preset` (if any) and, failing that, the layer's current symbology is left unchanged. Passing `None` explicitly forces "leave unchanged" even when a preset would otherwise set that property. Passing a value applies it, overriding the preset. Neither omitting an argument nor passing `None` clears an existing value.

!!! note "Opacity"
    `fill_opacity` accepts 0 (transparent) to 100 (fully opaque). If set without `fill_color`, the existing RGB is preserved and only the opacity is updated. If omitted (and no preset supplies it), the fill is left exactly as it is. Stroke opacity is always 100.

**Examples**

```python
# Layer object, hex colors
arcsmith.lyr.simple_sym(lyr, fill_color="#ADD8E6", fill_opacity=60,
                        stroke_color="#1E1E1E", stroke_width=1.5)

# Layer object, tuple colors
arcsmith.lyr.simple_sym(lyr, fill_color=(173, 216, 230), fill_opacity=60,
                        stroke_color=(30, 30, 30), stroke_width=1.5)

# Map lookup by name (updates all matching layers)
arcsmith.lyr.simple_sym(target_map=the_map, lyr_name="Park Boundary",
                        fill_color="#C8E6C9", fill_opacity=50,
                        stroke_color="#3C783C", stroke_width=1)

# Map lookup by source
arcsmith.lyr.simple_sym(target_map=the_map, lyr_source="path/to/trails",
                        stroke_color="#DC3232", stroke_width=2)

# Named preset
arcsmith.lyr.simple_sym(lyr, preset="simple_blue")

# Named preset, with one value overridden
arcsmith.lyr.simple_sym(lyr, preset="lake", fill_opacity=60)

# Hollow admin-boundary preset (transparent fill over a visible outline)
arcsmith.lyr.simple_sym(lyr, preset="admin")

# Hollow highlight preset with the outline recolored
arcsmith.lyr.simple_sym(lyr, preset="highlight", stroke_color="#00429D")

# Preset by name across the map (non-matching geometries are skipped)
arcsmith.lyr.simple_sym(target_map=the_map, lyr_name="Hydrography", preset="river")

# One-off style dict as a preset
arcsmith.lyr.simple_sym(lyr, preset={"fill_color": "#FFFFFF", "stroke_width": 0.5})

# Apply a polygon preset to a point layer (permissive by default)
arcsmith.lyr.simple_sym(point_lyr, preset="land")

# Enforce the preset's declared geometry instead
arcsmith.lyr.simple_sym(poly_lyr, preset="river", strict_geom=True)  # raises if poly_lyr isn't a Polyline

# Chain with add()
arcsmith.lyr.simple_sym(
    arcsmith.lyr.add(the_map, result, lyr_name="Park Boundary"),
    fill_color="#C8E6C9", fill_opacity=50,
    stroke_color="#3C783C", stroke_width=1)
```

### Presets

A `preset` supplies a bundle of style values under a single name, so a common look can be applied in one argument. Pass a registered name (a key of `PRESETS`) or a one-off style `dict`.

Resolution order is explicit argument, then preset, then leave unchanged. Any style parameter you pass explicitly overrides the preset, anything omitted falls back to the preset, and failing that the layer's current symbology is left unchanged.

Most named presets declare the geometry they were designed for in a `'geom'` key. By default, that key is **advisory**: the preset applies to any geometry, with its properties mapped onto whatever the target supports (a Polygon fills and outlines; a Polyline takes the stroke as its line and drops the fill; a Point styles its marker body and outline). Pass `strict_geom=True` to enforce the declared geometry instead.

!!! warning "Geometry matching"
    With the default `strict_geom=False`, geometry is never checked and a preset is applied to whatever layer it is given. With `strict_geom=True`, a preset that carries a `'geom'` key is enforced: in `lyr` mode a mismatch raises `ValueError`, and in map-lookup mode a non-matching layer is simply skipped, so a single name like `"Hydrography"` can be passed `preset="river", strict_geom=True` and only the polyline layers are styled. A preset without a `'geom'` key (any one-off `dict`) is never geometry-checked, regardless of `strict_geom`.

The full catalog of registered presets lives on the [Style presets](lyr_presets.md) page. The registry is also exposed as `arcsmith.lyr.PRESETS`, so you can inspect or extend it in code.

<br><br><br><br><br>