# ArcSmith: GIS toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

from __future__ import annotations

import random
from typing import Any, Literal, Optional, Union
import arcpy
from pathlib import Path, PureWindowsPath

from ._types import _PathLike

__all__ = ["PRESETS", "add", "add_to_grp", "apply_lyrx", "get", "get_grp",
           "make_grp", "move", "remove", "simple_sym"]

# Closed string-enum types for arguments where arcpy (or this module) accepts
# only a fixed set of values. Annotating with Literal lets editors autocomplete
# the valid options and lets type checkers flag typos before runtime. Inputs are
# still normalized/validated at runtime, so the annotations document intent
# rather than enforce it.
_GeomType = Literal["Point", "Polyline", "Polygon", "Multipoint"]
_Position = Literal["TOP", "BOTTOM"]
_Placement = Literal["BEFORE", "AFTER"]


# Sentinel distinguishing "argument not passed" from an explicit ``None``.
# ``None`` means "leave this property as the renderer already has it";
# ``_UNSET`` means "no opinion", so fall back to the preset, if any. Defined
# before ``add``/``simple_sym`` because both use it as a default argument
# value, which is evaluated at function-definition (import) time.
_UNSET = object()


def _match_layers(target_map: arcpy.mp.Map, lyr_name: Optional[str] = None,
                  lyr_source: Optional[_PathLike] = None,
                  geom_type: Optional[str] = None,
                  feature_only: bool = True) -> list:
    """
    Find layers in the map TOC by display name or data source path.

    Validates the name/source arguments and returns matching layers without
    raising on an empty result, so callers can decide how to handle "not
    found" (raise, or return quietly). Matching by ``lyr_name`` returns all
    matches; matching by ``lyr_source`` returns at most the first match.

    By default only feature layers are considered, which is what symbology and
    geometry-filtering callers need. Pass ``feature_only=False`` to match any
    layer type (raster, group, etc.); attribute reads that some layer types do
    not support are guarded, and a ``geom_type`` filter still applies only to
    feature layers (non-feature layers have no geometry and never match it).
    """
    if (lyr_name is None) == (lyr_source is None):
        raise ValueError("Provide exactly one of 'lyr_name' or 'lyr_source'.")

    matched = []

    for lyr in target_map.listLayers():
        if feature_only and not lyr.isFeatureLayer:
            continue

        if lyr_source is not None:
            # dataSource is only valid on layers that have one; group, basemap,
            # and service layers do not, so guard before reading it.
            if lyr.supports("DATASOURCE") and lyr.dataSource == str(lyr_source):
                matched.append(lyr)
                break

        else:  # match by name
            if not (lyr.supports("NAME") and lyr.name == lyr_name):
                continue
            if geom_type is not None:
                # A geometry filter applies only to feature layers; non-feature
                # layers have no shapeType and cannot match a geom_type.
                if not lyr.isFeatureLayer:
                    continue
                if arcpy.Describe(lyr).shapeType.lower() != geom_type.lower():
                    continue
            matched.append(lyr)

    return matched


def _raise_not_found(lyr_name: Optional[str], lyr_source: Optional[_PathLike],
                     geom_type: Optional[str]) -> None:
    """Raise a ``ValueError`` describing which match criteria found nothing."""
    identifier = lyr_name if lyr_name is not None else lyr_source
    raise ValueError(f"No layers matching '{identifier}'"
                     + (f" with geom_type='{geom_type}'" if geom_type else "")
                     + " found in the map.")


def _is_memory_path(lyr_src: _PathLike) -> bool:
    """True when lyr_src targets the in-memory workspace ('memory' or 'in_memory').

    arcpy in-memory paths are Windows-style (``memory\\trails``), so parsing is
    done with ``PureWindowsPath`` to split on both ``\\`` and ``/`` regardless of
    the OS the pure tests happen to run on.
    """
    parts = PureWindowsPath(str(lyr_src)).parts
    return bool(parts) and parts[0].lower() in ("memory", "in_memory")


def add(target_map: arcpy.mp.Map, lyr_src: Union[str, Path, arcpy.Result],
        lyr_name: Optional[str] = None, *,
        lyrx_src: Optional[_PathLike] = None,
        preset: Optional[Union[str, dict]] = None,
        fill_color: Any = _UNSET, fill_opacity: Any = _UNSET,
        stroke_color: Any = _UNSET, stroke_width: Any = _UNSET) -> arcpy.mp.Layer:
    """
    Add a data source to a map as a new layer, with attractive default styling.

    Unless told otherwise, a new feature layer is styled from the curated
    simple set, matched to its geometry. A polygon lands as a pale fill with a
    same-hue outline, a point as a solid same-hue marker with a gray outline, and
    a line as a colored same-hue stroke. The hue is chosen at random per add,
    and ``_seed_styles`` makes the sequence reproducible. Because the three
    geometries get visually distinct defaults, they do not blend together when
    they share a map. Supply any of ``lyrx_src``, ``preset``, or the explicit
    style arguments to take control instead.

    Everything after ``lyr_name`` is keyword-only. ``lyrx_src`` and ``preset``
    are mutually exclusive (both set symbology). Explicit style arguments layer
    on top of ``preset`` exactly as in ``simple_sym``. Styling only applies to
    feature layers with a ``SimpleRenderer``; rasters, tables, and layers
    ArcGIS gives a non-simple default are returned untouched (the automatic
    default fails soft rather than raising).

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to add the layer to.
    lyr_src : str, Path, or arcpy.Result
        Path to the data source (feature class, raster, etc.) to add.
        arcpy ``Result`` objects (e.g. the return value of
        ``arcpy.management.Dissolve``) are accepted and resolved to their
        output path automatically via ``str()``.

        In-memory datasets (paths under the ``memory`` or ``in_memory``
        workspace) are handled automatically. A map cannot consume an in-memory
        dataset directly, so the source is first staged into a layer with
        ``MakeRasterLayer`` for raster data or ``MakeFeatureLayer`` for
        everything else, and that layer is added to the map. This makes a
        ``memory\\...`` intermediate addable with no extra step from the caller.
    lyr_name : str, optional
        Display name for the layer in the TOC. Defaults to the source name.
    lyrx_src : str or Path, optional
        Keyword-only. Path to a ``.lyrx`` file. If provided, its symbology is
        applied to the new layer and the stylish default is skipped. Mutually
        exclusive with ``preset``.
    preset : str or dict, optional
        Keyword-only. A registered preset name (a key of ``PRESETS``) or a
        one-off style ``dict``, applied via ``simple_sym``. Mutually exclusive
        with ``lyrx_src``. When omitted (and no explicit style args are
        given), a curated simple preset matched to the layer's geometry is
        applied at a random hue.
    fill_color, fill_opacity, stroke_color, stroke_width : optional
        Keyword-only style overrides forwarded to ``simple_sym``. Passing any
        of these suppresses the random default and applies the given style
        (on top of ``preset`` if one is also supplied).

    Returns
    -------
    arcpy.mp.Layer
        The newly added layer.

    Raises
    ------
    ValueError
        If both ``lyrx_src`` and ``preset`` are provided.

    Examples
    --------
    Add a layer with an attractive default style matched to its geometry:

    >>> lyr = arcsmith.lyr.add(target_map, "path/to/trails")

    Add a layer with a custom display name:

    >>> lyr = arcsmith.lyr.add(target_map, "path/to/landmarks", lyr_name="Lake McDonald Lodge")

    Add Glacier's red "Jammer" tour buses as a layer:

    >>> lyr = arcsmith.lyr.add(target_map, "path/to/red_buses", lyr_name="Red Bus Tours")

    Add a layer styled from a named preset:

    >>> lyr = arcsmith.lyr.add(target_map, "path/to/trails", preset="lake")

    Add a layer with explicit inline style:

    >>> lyr = arcsmith.lyr.add(target_map, "path/to/trails",
    ...                        fill_color="#C8E6C9", stroke_width=1)

    Add a layer with a name and ``.lyrx`` symbology:

    >>> lyr = arcsmith.lyr.add(target_map, "path/to/trails", lyr_name="Rivers", lyrx_src="path/to/trails.lyrx")

    Pass an arcpy Result directly (e.g. from Dissolve):

    >>> result = arcpy.management.Dissolve(in_fc, output_path, dissolve_field)
    >>> lyr = arcsmith.lyr.add(target_map, result, lyr_name="Park Boundary", lyrx_src="path/to/trails.lyrx")
    """
    if lyrx_src is not None and preset is not None:
        raise ValueError("Provide either 'lyrx_src' or 'preset', not both.")

    src = str(lyr_src)
    if _is_memory_path(src):
        # addDataFromPath can't consume an in-memory dataset; make a layer from
        # it first (feature or raster), then add that Layer object to the map.
        name = lyr_name or Path(src).stem
        if arcpy.Describe(src).dataType in ("RasterDataset", "RasterLayer", "RasterBand"):
            made = arcpy.management.MakeRasterLayer(src, name)
        else:
            made = arcpy.management.MakeFeatureLayer(src, name)
        lyr = target_map.addLayer(made.getOutput(0))[0]
    else:
        lyr = target_map.addDataFromPath(src)

    if lyr_name is not None:
        lyr.name = lyr_name

    if lyrx_src is not None:
        sym_layer = arcpy.mp.LayerFile(str(lyrx_src)).listLayers()[0]
        lyr.symbology = sym_layer.symbology
        return lyr

    explicit = any(v is not _UNSET for v in
                   (fill_color, fill_opacity, stroke_color, stroke_width))

    # No symbology asked for, so apply the curated random default. This path
    # must not break the add, so guard against non-feature and non-simple
    # layers and leave them with ArcGIS's own symbology. The default is
    # matched to the layer's geometry, so a polygon lands as a pale fill, a
    # point as a solid marker, and a line as a colored stroke, and the three
    # do not blend together on the same map.
    auto = preset is None and not explicit
    if auto:
        if not getattr(lyr, "isFeatureLayer", False):
            return lyr
        try:
            if lyr.symbology.renderer.type != "SimpleRenderer":
                return lyr
        except Exception:
            return lyr
        try:
            geom = arcpy.Describe(lyr).shapeType
        except Exception:
            geom = None
        preset = _random_simple_preset(geom)

    simple_sym(lyr, preset=preset, fill_color=fill_color,
               fill_opacity=fill_opacity, stroke_color=stroke_color,
               stroke_width=stroke_width)
    return lyr


def apply_lyrx(lyrx_src: _PathLike, lyr: Optional[arcpy.mp.Layer] = None, *,
               target_map: Optional[arcpy.mp.Map] = None,
               lyr_name: Optional[str] = None,
               lyr_source: Optional[_PathLike] = None,
               geom_type: Optional[_GeomType] = None) -> Union[arcpy.mp.Layer, list]:
    """
    Apply symbology from a ``.lyrx`` file to one or more layers.

    Two targeting modes are available and exactly one must be used per call.
    Pass a single ``arcpy.mp.Layer`` as ``lyr`` to style it directly and
    receive it back as the return value. Alternatively, pass ``target_map``
    with ``lyr_name`` or ``lyr_source`` to match layers in the map TOC and
    receive the list of updated layers.

    When matching by ``lyr_name``, all layers with that name are updated.
    When matching by ``lyr_source``, only the first exact match is updated.

    Parameters
    ----------
    lyrx_src : str or Path
        Path to the ``.lyrx`` file containing the symbology to apply.
    lyr : arcpy.mp.Layer, optional
        A single layer to style directly. Mutually exclusive with
        ``target_map``, ``lyr_name``, and ``lyr_source``.
    target_map : arcpy.mp.Map, optional
        Map object containing the layer(s) to update. Required when matching
        by ``lyr_name`` or ``lyr_source``. Keyword-only.
    lyr_name : str, optional
        Display name to match against; all matching layers are updated.
        Requires ``target_map``. Keyword-only.
    lyr_source : str or Path, optional
        Data source path to match against; only the first match is updated.
        Requires ``target_map``. Keyword-only.
    geom_type : {'Point', 'Polyline', 'Polygon', 'Multipoint'}, optional
        Geometry type filter when matching by name. Only layers whose
        ``shapeType`` matches are updated. Case-insensitive. Ignored when
        matching by ``lyr_source`` or ``lyr``. Keyword-only.
        Default ``None`` (no filter).

    Returns
    -------
    arcpy.mp.Layer
        When called in ``lyr`` mode: the same layer object.
    list of arcpy.mp.Layer
        When called in map-lookup mode: all layers that were updated.

    Raises
    ------
    ValueError
        If both ``lyr`` and any map-lookup argument are provided, or if
        neither mode is specified.
    ValueError
        If no matching layers are found (map-lookup mode).

    Examples
    --------
    Style a layer object directly:

    >>> arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", lyr)

    Update all layers named "rivers":

    >>> lyrs = arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", target_map=current_map, lyr_name="rivers")

    Update only "rivers" layers with a polyline geometry:

    >>> lyrs = arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", target_map=current_map, lyr_name="rivers", geom_type="Polyline")

    Update a single layer by data source:

    >>> lyrs = arcsmith.lyr.apply_lyrx("path/to/trails.lyrx", target_map=current_map, lyr_source="path/to/trails")
    """
    map_lookup_args = (target_map, lyr_name, lyr_source)
    using_lyr = lyr is not None
    using_map = any(a is not None for a in map_lookup_args)

    if using_lyr and using_map:
        raise ValueError(
            "Provide either 'lyr' or map-lookup arguments "
            "('target_map' + 'lyr_name'/'lyr_source'), not both."
        )
    if not using_lyr and not using_map:
        raise ValueError(
            "Provide either 'lyr' or 'target_map' with 'lyr_name' or "
            "'lyr_source'."
        )

    if using_map:
        if target_map is None:
            raise ValueError(
                "'target_map' is required when using 'lyr_name' or 'lyr_source'."
            )
        matched = _match_layers(target_map, lyr_name=lyr_name,
                                lyr_source=lyr_source, geom_type=geom_type)
        if not matched:
            _raise_not_found(lyr_name, lyr_source, geom_type)
        targets = matched
    else:
        targets = [lyr]

    sym_layer = arcpy.mp.LayerFile(str(lyrx_src)).listLayers()[0]
    for layer in targets:
        layer.symbology = sym_layer.symbology

    return targets[0] if using_lyr else targets


def _parse_color(color: Union[str, tuple, list]) -> tuple:
    """
    Normalize a color value to an ``(R, G, B)`` integer tuple.

    Accepts:

    * An ``(R, G, B)`` tuple or list of ints (0 to 255). Returned as-is.
    * A hex string with or without a leading ``#``, e.g. ``"#ADBCE6"`` or
      ``"ADBCE6"``.  Three-digit shorthand (``"#F0A"``) is also accepted and
      expanded to six digits.

    Raises ``ValueError`` for any input that does not match these forms.
    """
    if isinstance(color, (tuple, list)) and len(color) == 3:
        return tuple(int(c) for c in color)

    if isinstance(color, str):
        h = color.lstrip("#").strip()
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    raise ValueError(
        f"Invalid color '{color}'. Provide an (R, G, B) tuple or a hex "
        "string such as '#ADBCE6' or 'ADBCE6'."
    )


# Named colors live in one place so presets reference them by name and the
# project palette can be retuned without hunting through every preset.
_PALETTE = {
    # Water
    "water":          "#A9D3E8",
    "water_edge":     "#7FB3CE",
    "ocean":          "#8FC1DD",
    "ocean_edge":     "#6BA8C9",
    "river_blue":     "#5B9BC4",
    "stream_blue":    "#8FBFD9",
    "coast_blue":     "#4A8FB5",
    # Vegetation
    "forest":         "#A7C293",
    "forest_edge":    "#87A86C",
    "park":           "#C8E2AF",
    "park_edge":      "#A8C98D",
    "wetland":        "#C2D6C4",
    "wetland_edge":   "#A0BCA2",
    # Terrain / bare ground
    "parchment":      "#EAE3D2",
    "parchment_edge": "#C9BFA8",
    "sand":           "#F0E2BE",
    "sand_edge":      "#DBC999",
    "glacier":        "#E9F3F6",
    "glacier_edge":   "#CADDE3",
    # Built environment
    "urban":          "#E6DAD2",
    "urban_edge":     "#CDBDB0",
    "building":       "#D8C7BA",
    "building_edge":  "#B6A393",
    # Lines
    "road_grey":      "#8C8C8C",
    "highway_orange": "#E8A33D",
    "railway_grey":   "#6B6B6B",
    "trail_brown":    "#B5651D",
    "boundary_mauve": "#9C8BA8",
    # Point markers
    "city_dark":      "#4D4D4D",
    "town_grey":      "#7A7A7A",
    "peak_brown":     "#8B5E3C",
    "poi_red":        "#C0392B",
    "marker_outline": "#666666",
    # Simple fills: pale tint + saturated same-hue outline
    "simple_blue":          "#BEE8FF", "simple_blue_edge":   "#004C73",
    "simple_sky":           "#BEF7FF", "simple_sky_edge":    "#005C73",
    "simple_green":         "#D3FFBE", "simple_green_edge":  "#267300",
    "simple_lime":          "#ECFFBE", "simple_lime_edge":   "#4C7300",
    "simple_orange":        "#FFEBAF", "simple_orange_edge": "#A83800",
    "simple_red":           "#FFBEBE", "simple_red_edge":    "#A80000",
    "simple_pink":          "#FFBEE8", "simple_pink_edge":   "#A80084",
    "simple_purple":        "#E8BEFF", "simple_purple_edge": "#4C0073",
    "simple_indigo":        "#C9BEFF", "simple_indigo_edge": "#1C3C73",
    "simple_yellow":        "#FFFFBE", "simple_yellow_edge": "#A87000",
    "simple_teal":          "#BEFFE8", "simple_teal_edge":   "#00734C",
    "simple_brown":         "#E8D3BE", "simple_brown_edge":  "#734C00",
    "simple_grey":          "#E1E1E1", "simple_grey_edge":   "#4E4E4E",
    "simple_slate":         "#D6DCE4", "simple_slate_edge":  "#4C5A66",
    # Administrative boundary strokes: neutral edges for admin or reference
    # boundaries drawn with no fill.
    "admin":            "#3C3C3C",
    "admin_bold":       "#1E1E1E",
    "admin_subtle":     "#9B9B9B",
    # Bright highlight strokes: saturated edges for call-outs and selections,
    # drawn over a hollow (unfilled) polygon.
    "highlight_red":    "#E31A1C",
    "highlight_orange": "#FF7A00",
    "highlight_yellow": "#FFD400",
    "highlight_green":  "#39D353",
    "highlight_teal":   "#10C7B0",
    "highlight_blue":   "#1F8FFF",
    "highlight_indigo": "#5B5BFF",
    "highlight_purple": "#A14BFF",
    "highlight_pink":   "#FF2D95",
    # Extra feature colors: farmland / arid / industrial fills, a few more
    # line strokes, and point markers (all paired with a grey outline).
    "farmland":       "#E9E4B0", "farmland_edge":   "#C7BE7A",
    "desert":         "#F3E2C0", "desert_edge":     "#D9C190",
    "industrial":     "#DCD4DE", "industrial_edge": "#B7AABA",
    "contour_brown":  "#B5905C",
    "cycleway_teal":  "#2E8B8B",
    "power_grey":     "#9A9A9A",
    "airport_blue":   "#3B6FB0",
    "camp_green":     "#5E7F3C",
    "harbor_navy":    "#2C5F7C",
}

# Geometry shorthands. A preset's ``geom`` may be a single shapeType or a
# collection of them; point markers accept both Point and Multipoint.
_POINTISH = ("Point", "Multipoint")
# Geometries that carry a fill + outline (the body-styling branch).
_FILLABLE = ("Polygon", "Point", "Multipoint")

# Semantic symbology presets, grouped by geometry. Each records the geometry
# it was designed for in its ``geom`` key. That geometry is advisory: by
# default ``simple_sym`` applies any preset to any geometry (mapping its style
# onto whatever the target supports). It is only enforced when
# ``simple_sym(..., strict_geom=True)`` is passed. The remaining keys are
# exactly the style parameters of ``simple_sym``.
PRESETS = {
    # --- Polygon (fill + outline) ----------------------------------- #
    "land":     {"geom": "Polygon", "fill_color": _PALETTE["parchment"],
                 "stroke_color": _PALETTE["parchment_edge"], "stroke_width": 0.7},
    "lake":     {"geom": "Polygon", "fill_color": _PALETTE["water"],
                 "stroke_color": _PALETTE["water_edge"], "stroke_width": 0.95},
    "ocean":    {"geom": "Polygon", "fill_color": _PALETTE["ocean"],
                 "stroke_color": _PALETTE["ocean_edge"], "stroke_width": 0.95},
    "forest":   {"geom": "Polygon", "fill_color": _PALETTE["forest"],
                 "stroke_color": _PALETTE["forest_edge"], "stroke_width": 0.7},
    "park":     {"geom": "Polygon", "fill_color": _PALETTE["park"],
                 "stroke_color": _PALETTE["park_edge"], "stroke_width": 0.7},
    "wetland":  {"geom": "Polygon", "fill_color": _PALETTE["wetland"],
                 "stroke_color": _PALETTE["wetland_edge"], "stroke_width": 0.7},
    "sand":     {"geom": "Polygon", "fill_color": _PALETTE["sand"],
                 "stroke_color": _PALETTE["sand_edge"], "stroke_width": 0.7},
    "glacier":  {"geom": "Polygon", "fill_color": _PALETTE["glacier"],
                 "stroke_color": _PALETTE["glacier_edge"], "stroke_width": 0.7},
    "urban":    {"geom": "Polygon", "fill_color": _PALETTE["urban"],
                 "stroke_color": _PALETTE["urban_edge"], "stroke_width": 0.7},
    "building": {"geom": "Polygon", "fill_color": _PALETTE["building"],
                 "stroke_color": _PALETTE["building_edge"], "stroke_width": 0.95},

    # Administrative boundaries: hollow polygons. The interior fill is made
    # fully transparent (fill_opacity=0) so the area underneath stays visible
    # and only the outline reads.
    "admin":        {"geom": "Polygon", "fill_opacity": 0,
                     "stroke_color": _PALETTE["admin"],        "stroke_width": 1.65},
    "admin_bold":   {"geom": "Polygon", "fill_opacity": 0,
                     "stroke_color": _PALETTE["admin_bold"],   "stroke_width": 3.5},
    "admin_subtle": {"geom": "Polygon", "fill_opacity": 0,
                     "stroke_color": _PALETTE["admin_subtle"], "stroke_width": 0.95},

    # --- Polyline (stroke only) ------------------------------------- #
    "river":    {"geom": "Polyline", "stroke_color": _PALETTE["river_blue"],
                 "stroke_width": 2.35},
    "stream":   {"geom": "Polyline", "stroke_color": _PALETTE["stream_blue"],
                 "stroke_width": 1.15},
    "coastline":{"geom": "Polyline", "stroke_color": _PALETTE["coast_blue"],
                 "stroke_width": 1.15},
    "road":     {"geom": "Polyline", "stroke_color": _PALETTE["road_grey"],
                 "stroke_width": 2.8},
    "highway":  {"geom": "Polyline", "stroke_color": _PALETTE["highway_orange"],
                 "stroke_width": 4.65},
    "railway":  {"geom": "Polyline", "stroke_color": _PALETTE["railway_grey"],
                 "stroke_width": 1.85},
    "trail":    {"geom": "Polyline", "stroke_color": _PALETTE["trail_brown"],
                 "stroke_width": 1.4},
    "boundary": {"geom": "Polyline", "stroke_color": _PALETTE["boundary_mauve"],
                 "stroke_width": 1.85},

    # --- Point (marker body + outline) ------------------------------ #
    "city":     {"geom": _POINTISH, "fill_color": _PALETTE["city_dark"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},
    "town":     {"geom": _POINTISH, "fill_color": _PALETTE["town_grey"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},
    "peak":     {"geom": _POINTISH, "fill_color": _PALETTE["peak_brown"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},
    "poi":      {"geom": _POINTISH, "fill_color": _PALETTE["poi_red"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},
    "spring":   {"geom": _POINTISH, "fill_color": _PALETTE["river_blue"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},

    # --- Additional features ---------------------------------------- #
    # Polygon (fill + outline)
    "farmland":   {"geom": "Polygon", "fill_color": _PALETTE["farmland"],
                   "stroke_color": _PALETTE["farmland_edge"], "stroke_width": 0.7},
    "desert":     {"geom": "Polygon", "fill_color": _PALETTE["desert"],
                   "stroke_color": _PALETTE["desert_edge"], "stroke_width": 0.7},
    "industrial": {"geom": "Polygon", "fill_color": _PALETTE["industrial"],
                   "stroke_color": _PALETTE["industrial_edge"], "stroke_width": 0.7},
    # Polyline (stroke only)
    "contour":  {"geom": "Polyline", "stroke_color": _PALETTE["contour_brown"],
                 "stroke_width": 0.5},
    "cycleway": {"geom": "Polyline", "stroke_color": _PALETTE["cycleway_teal"],
                 "stroke_width": 1.2},
    "power":    {"geom": "Polyline", "stroke_color": _PALETTE["power_grey"],
                 "stroke_width": 1.0},
    # Point (marker body + outline)
    "airport":  {"geom": _POINTISH, "fill_color": _PALETTE["airport_blue"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},
    "camp":     {"geom": _POINTISH, "fill_color": _PALETTE["camp_green"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},
    "harbor":   {"geom": _POINTISH, "fill_color": _PALETTE["harbor_navy"],
                 "stroke_color": _PALETTE["marker_outline"], "stroke_width": 0.70},
}

# Simple color fills for polygon/point output. Each is a pale tint fill with
# a deep, saturated outline of the same hue , with a 0.7 pt stroke. Built from
# the palette so every entry stays visually consistent.
_SIMPLE_HUES = ("red", "orange", "yellow", "lime", "green", "teal",
                "sky", "blue", "indigo", "purple", "pink",
                "brown", "grey", "slate")

# Subset of simple hues used for ``add``'s auto-random default: excludes grey
# and slate (less visually distinctive on first impression). All 14 simple_*
# presets still register and can be used explicitly.
_STYLISH_HUES = ("red", "orange", "yellow", "lime", "green", "teal",
                 "sky", "blue", "indigo", "purple", "pink", "brown")
PRESETS.update({
    f"simple_{hue}": {
        "geom": _FILLABLE,
        "fill_color": _PALETTE[f"simple_{hue}"],
        "stroke_color": _PALETTE[f"simple_{hue}_edge"],
        "stroke_width": 0.7,
    }
    for hue in _SIMPLE_HUES
})

# Simple point markers. Each is a solid same-hue marker with a grey outline,
# using the saturated edge color of the matching simple fill as the body. The
# body is the slightly dark version of the hue, so a default-styled point
# reads as a distinct marker against the pale simple_* polygon fills rather
# than blending into them. Point presets match both Point and Multipoint.
PRESETS.update({
    f"simple_pt_{hue}": {
        "geom": _POINTISH,
        "fill_color": _PALETTE[f"simple_{hue}_edge"],
        "stroke_color": _PALETTE["marker_outline"],
        "stroke_width": 0.7,
    }
    for hue in _SIMPLE_HUES
})

# Simple lines. Each is a solid same-hue stroke at a line weight, again using
# the saturated edge color of the matching simple fill. A line and a point of
# the same hue therefore share a color and read as siblings. The width is set
# above the polygon outline weight so a default-styled line reads as a line
# rather than as a stray polygon outline.
PRESETS.update({
    f"simple_ln_{hue}": {
        "geom": "Polyline",
        "stroke_color": _PALETTE[f"simple_{hue}_edge"],
        "stroke_width": 1.5,
    }
    for hue in _SIMPLE_HUES
})

# Bright hollow highlights for polygons: no fill over a saturated 2.0 pt
# outline, for call-outs and selections. Built from the palette so the set
# stays consistent. ``highlight`` (no hue) is kept as an alias for the red
# highlight so existing calls keep working.
_HIGHLIGHT_HUES = ("red", "orange", "yellow", "green", "teal",
                   "blue", "indigo", "purple", "pink")
PRESETS.update({
    f"highlight_{hue}": {
        "geom": "Polygon",
        "fill_opacity": 0,
        "stroke_color": _PALETTE[f"highlight_{hue}"],
        "stroke_width": 2.5,
    }
    for hue in _HIGHLIGHT_HUES
})
PRESETS["highlight"] = dict(PRESETS["highlight_red"])


# Stylish defaults. ``add`` styles every new feature layer from the curated
# simple-fill set so a plain add looks intentional rather than landing on
# ArcGIS's harsh random default. Hues are drawn from a reshuffled cycle so
# consecutive adds avoid repeats while staying varied; seed the RNG with
# ``_seed_styles`` for reproducible output across a run.
_style_rng = random.Random()


def _hue_cycle():
    """Yield stylish simple-fill hues forever, reshuffling each full pass so back-to-back
    adds rarely repeat a color. Uses the curated subset (excludes grey/slate)."""
    while True:
        hues = list(_STYLISH_HUES)
        _style_rng.shuffle(hues)
        for hue in hues:
            yield hue


_style_hues = _hue_cycle()


def _seed_styles(seed):
    """
    Seed the RNG behind ``add``'s stylish default fill for reproducible output.

    ``add`` assigns each new layer a fill from the curated simple-fill set at
    random. Calling this with a fixed ``seed`` makes that sequence
    deterministic across a run, so the same script produces the same colors in
    the same order. Reseeds the generator and restarts the hue cycle.

    Parameters
    ----------
    seed : int, str, bytes, or None
        Any value accepted by ``random.Random.seed``. Pass ``None`` to reseed
        from system entropy (non-reproducible).

    Examples
    --------
    >>> arcsmith.lyr._seed_styles(42)
    >>> a = arcsmith.lyr.add(target_map, fc_a)   # deterministic fill
    >>> b = arcsmith.lyr.add(target_map, fc_b)   # next fill in the sequence
    """
    global _style_hues
    _style_rng.seed(seed)
    _style_hues = _hue_cycle()


def _random_simple_preset(geom=None):
    """
    Return the next curated simple preset name, matched to a geometry.

    The hue comes from the shared stylish cycle, so consecutive adds rotate
    through colors the same way regardless of geometry. The family is then
    chosen from that hue. A point geometry returns a ``simple_pt_*`` marker
    preset, a polyline returns a ``simple_ln_*`` line preset, and anything
    else (including an unknown geometry) returns the ``simple_*`` polygon
    fill preset.
    """
    hue = next(_style_hues)
    if geom in _POINTISH:
        return f"simple_pt_{hue}"
    if geom == "Polyline":
        return f"simple_ln_{hue}"
    return f"simple_{hue}"


def simple_sym(lyr: Optional[arcpy.mp.Layer] = None, *,
               preset: Optional[Union[str, dict]] = None,
               fill_color: Any = _UNSET, fill_opacity: Any = _UNSET,
               stroke_color: Any = _UNSET, stroke_width: Any = _UNSET,
               strict_geom: bool = False,
               target_map: Optional[arcpy.mp.Map] = None,
               lyr_name: Optional[str] = None,
               lyr_source: Optional[_PathLike] = None,
               geom_type: Optional[_GeomType] = None) -> Union[arcpy.mp.Layer, list]:
    """
    Apply simple fill and stroke symbology to one or more feature layers.

    Works with Polygon, Polyline, and Point layers using a
    ``CIMSimpleRenderer``.  Parameters that do not apply to a geometry type
    are silently ignored (e.g. ``fill_color`` on a Polyline layer).

    Two targeting modes are available and exactly one must be used per call.
    Pass a single ``arcpy.mp.Layer`` as ``lyr`` to style it directly and
    receive it back as the return value.  Alternatively, pass ``target_map``
    with ``lyr_name`` or ``lyr_source`` to match layers by name or source,
    which behaves like ``apply_lyrx`` and returns a list of updated layers.

    Colors accept either an ``(R, G, B)`` tuple or a hex string
    (``"#ADBCE6"`` or ``"ADBCE6"``).

    A ``preset`` supplies a bundle of style values for a common feature type
    (e.g. ``"lake"``, ``"river"``, ``"land"``). Any style argument passed
    explicitly overrides the preset; anything omitted falls back to the
    preset, and failing that the layer's current symbology is preserved.

    By default a preset applies to a layer of **any** geometry: its style
    properties are mapped onto whatever the target geometry supports (see
    *Cross-geometry mapping* below) rather than refusing the operation. Each
    named preset still records the geometry it was designed for in its
    ``geom`` key, but that is advisory unless ``strict_geom=True`` is passed,
    in which case a mismatch raises in single-``lyr`` mode and skips the layer
    in map-lookup mode. See ``PRESETS`` for the
    registry; a one-off style ``dict`` may also be passed as ``preset``.

    Parameters
    ----------
    lyr : arcpy.mp.Layer, optional
        A single layer to style directly. Mutually exclusive with
        ``target_map``, ``lyr_name``, and ``lyr_source``.
    preset : str or dict, optional
        A registered preset name (a key of ``PRESETS``) or a one-off style
        ``dict`` using the same keys as the style parameters below. A dict
        may include a ``'geom'`` key to enable the geometry check; without
        one, no geometry check is performed. Explicit style arguments take
        precedence over the preset.
    fill_color : tuple of int or str, optional
        RGB fill color as ``(R, G, B)`` or a hex string. Applied to the
        body of Polygon and Point layers. Ignored for Polyline layers.
        Omitted by default (preset value, else existing color preserved).
    fill_opacity : int or float, optional
        Fill opacity as a percentage (0 to 100). Omitted by default; when
        omitted and no preset supplies it, opacity is left untouched (and
        treated as ``100`` if a new ``fill_color`` is applied). Ignored for
        Polyline layers.
    stroke_color : tuple of int or str, optional
        RGB stroke/outline color as ``(R, G, B)`` or a hex string. Sets
        the outline color on Polygon/Point layers; sets the line color on
        Polyline layers. Omitted by default (preset value, else preserved).
    stroke_width : int or float, optional
        Stroke/outline width in points. Sets the outline width on
        Polygon/Point layers; sets the line width on Polyline layers.
        Omitted by default (preset value, else preserved).
    strict_geom : bool, optional
        If ``True``, enforce a preset's intended geometry: a mismatch
        raises in single-``lyr`` mode and skips the layer in map-lookup
        mode. If ``False`` (the default), the geometry is not enforced and
        the preset is applied to any geometry via the cross-geometry mapping
        described in *Notes*. Only presets that carry a ``geom`` key (the
        registered named presets) can be enforced; ad-hoc dicts without one
        are never checked. Default ``False``.
    target_map : arcpy.mp.Map, optional
        Map to search when targeting by name or source. Required when
        using ``lyr_name`` or ``lyr_source``.
    lyr_name : str, optional
        Display name to match; all matching layers are updated. Requires
        ``target_map``. Mutually exclusive with ``lyr_source``.
    lyr_source : str or Path, optional
        Data source path to match; only the first exact match is updated.
        Requires ``target_map``. Mutually exclusive with ``lyr_name``.
    geom_type : {'Point', 'Polyline', 'Polygon', 'Multipoint'}, optional
        Geometry type filter when using ``lyr_name``. Case-insensitive.
        Ignored when using ``lyr_source`` or ``lyr``.

    Returns
    -------
    arcpy.mp.Layer
        When called in ``lyr`` mode: the same layer object.
    list of arcpy.mp.Layer
        When called in map-lookup mode: all layers that were updated.

    Raises
    ------
    ValueError
        If both ``lyr`` and any map-lookup argument are provided, or if
        neither mode is specified.
    ValueError
        If no matching layers are found (map-lookup mode).
    ValueError
        If a layer's renderer is not a ``CIMSimpleRenderer``.
    ValueError
        If a color value cannot be parsed.
    ValueError
        If ``preset`` is an unknown name, or is neither a str nor a dict.
    ValueError
        If a named preset's geometry does not match the layer **and**
        ``strict_geom=True``, in single-``lyr`` mode. (In map-lookup mode
        the layer is skipped instead.) With the default ``strict_geom=False``
        no geometry check is performed.

    Notes
    -----
    Color opacity in ArcPy's CIM model is stored as a 0 to 100 value in the
    fourth element of a color's value list.  ``fill_opacity`` maps directly
    to that slot.  Stroke opacity is always 100 (fully opaque).

    If ``fill_opacity`` is set without ``fill_color``, the existing RGB is
    preserved and only the opacity is updated. If neither is set (and no
    preset supplies them), the fill is left exactly as it is.

    Cross-geometry mapping. Style is applied through the arcpy.mp convenience
    properties ``symbol.color`` (the body fill), ``symbol.outlineColor`` and
    ``symbol.outlineWidth`` (the outline), which ArcPy resolves per geometry.
    The four style properties therefore land as follows:

    * Polygon: ``fill_color``/``fill_opacity`` set the fill;
      ``stroke_color``/``stroke_width`` set the outline. All four apply.
    * Point / Multipoint: same as Polygon: ``fill_color``/``fill_opacity``
      set the marker body, ``stroke_color``/``stroke_width`` its outline.
      All four apply.
    * Polyline: ``stroke_color``/``stroke_width`` define the line itself;
      ``fill_color``/``fill_opacity`` have no native target and are dropped
      (a line takes its stroke only). Applying a polygon-oriented preset to
      a line therefore styles the line from the preset's stroke.

    A fully transparent fill (``fill_opacity=0``) renders a Polygon or Point
    as hollow. When only ``fill_opacity`` is given and the symbol has no
    existing fill color to modify, a transparent fallback fill is supplied so
    the hollow result is still produced rather than erroring.

    Examples
    --------
    Style a layer object directly (tuple color):

    >>> arcsmith.lyr.simple_sym(lyr, fill_color=(173, 216, 230), fill_opacity=60,
    ...                         stroke_color=(30, 30, 30), stroke_width=1.5)

    Style a layer object directly (hex color):

    >>> arcsmith.lyr.simple_sym(lyr, fill_color="#ADD8E6", fill_opacity=60,
    ...                         stroke_color="#1E1E1E", stroke_width=1.5)

    Style by layer name (updates all matching layers):

    >>> arcsmith.lyr.simple_sym(target_map=current_map, lyr_name="Park Boundary",
    ...                         fill_color="#ADD8E6", fill_opacity=50,
    ...                         stroke_color="#1E1E1E", stroke_width=1)

    Style by data source path:

    >>> arcsmith.lyr.simple_sym(target_map=current_map, lyr_source="path/to/trails",
    ...                         stroke_color="#DC3232", stroke_width=2)

    Apply a named preset, then override one value:

    >>> arcsmith.lyr.simple_sym(lake_lyr, preset="lake", fill_opacity=60)

    Apply a preset by name across the map (non-matching geometries skipped):

    >>> arcsmith.lyr.simple_sym(target_map=current_map, lyr_name="Hydrography",
    ...                         preset="river")

    Use a one-off style dict as a preset:

    >>> arcsmith.lyr.simple_sym(lyr, preset={"fill_color": "#FFFFFF",
    ...                                      "stroke_width": 0.5})

    Apply a preset across any geometry (default), or enforce its geometry:

    >>> arcsmith.lyr.simple_sym(point_lyr, preset="land")  # ok: fill+outline
    >>> arcsmith.lyr.simple_sym(point_lyr, preset="land", strict_geom=True)
    Traceback (most recent call last):
        ...
    ValueError: Preset targets Polygon layers, but '...' is Point.

    Chain with add():

    >>> arcsmith.lyr.simple_sym(
    ...     arcsmith.lyr.add(current_map, result, lyr_name="Park Boundary"),
    ...     fill_color="#C8E6C9", fill_opacity=50,
    ...     stroke_color="#3C783C", stroke_width=1)
    """

    # ------------------------------------------------------------------ #
    # Argument validation                                                #
    # ------------------------------------------------------------------ #
    map_lookup_args = (target_map, lyr_name, lyr_source)
    using_lyr = lyr is not None
    using_map = any(a is not None for a in map_lookup_args)

    if using_lyr and using_map:
        raise ValueError(
            "Provide either 'lyr' or map-lookup arguments "
            "('target_map' + 'lyr_name'/'lyr_source'), not both."
        )
    if not using_lyr and not using_map:
        raise ValueError(
            "Provide either 'lyr' or 'target_map' with 'lyr_name' or "
            "'lyr_source'."
        )

    # ------------------------------------------------------------------ #
    # Resolve target layer(s)                                            #
    # ------------------------------------------------------------------ #
    if using_map:
        if target_map is None:
            raise ValueError(
                "'target_map' is required when using 'lyr_name' or 'lyr_source'."
            )
        matched = _match_layers(target_map, lyr_name=lyr_name,
                                lyr_source=lyr_source, geom_type=geom_type)
        if not matched:
            _raise_not_found(lyr_name, lyr_source, geom_type)
        targets = matched
    else:
        targets = [lyr]

    # ------------------------------------------------------------------ #
    # Resolve preset + explicit style args                               #
    # ------------------------------------------------------------------ #
    # A preset may be a registered name or a one-off style dict. It yields
    # a style mapping plus the geometry it intends (``None`` for an ad-hoc
    # dict without a 'geom' key, which disables the geometry check).
    if preset is None:
        preset_style, preset_geom = {}, None
    elif isinstance(preset, dict):
        preset_style = {k: v for k, v in preset.items() if k != "geom"}
        preset_geom = preset.get("geom")
    elif isinstance(preset, str):
        if preset not in PRESETS:
            raise ValueError(
                f"Unknown preset '{preset}'. "
                f"Available: {', '.join(sorted(PRESETS))}."
            )
        entry = PRESETS[preset]
        preset_style = {k: v for k, v in entry.items() if k != "geom"}
        preset_geom = entry.get("geom")
    else:
        raise ValueError(
            "'preset' must be a preset name (str) or a style dict, "
            f"not {type(preset).__name__}."
        )

    # Normalize the intended geometry to a tuple of shapeTypes (or None to
    # disable the check). ``geom`` may be given as a single string or any
    # collection of strings.
    if preset_geom is None:
        allowed_geom = None
    elif isinstance(preset_geom, str):
        allowed_geom = (preset_geom,)
    else:
        allowed_geom = tuple(preset_geom)

    # Explicit kwargs win over the preset; anything still ``_UNSET`` falls
    # back to the preset and, failing that, to ``None`` ("leave as-is").
    def _resolve(value, key):
        return value if value is not _UNSET else preset_style.get(key)

    fill_color = _resolve(fill_color, "fill_color")
    fill_opacity = _resolve(fill_opacity, "fill_opacity")
    stroke_color = _resolve(stroke_color, "stroke_color")
    stroke_width = _resolve(stroke_width, "stroke_width")

    # ------------------------------------------------------------------ #
    # Parse colors once up front                                           #
    # ------------------------------------------------------------------ #
    parsed_fill = _parse_color(fill_color) if fill_color is not None else None
    parsed_stroke = _parse_color(stroke_color) if stroke_color is not None else None

    # ------------------------------------------------------------------ #
    # Inner helpers                                                        #
    # ------------------------------------------------------------------ #
    def _rgb(rgb_tuple, opacity=100):
        r, g, b = rgb_tuple
        # arcpy.mp convenience color format (not the raw CIM JSON form).
        return {"RGB": [r, g, b, opacity]}

    def _apply_one(layer):
        sym = layer.symbology
        if sym.renderer.type != "SimpleRenderer":
            raise ValueError(
                f"simple_sym requires a SimpleRenderer; '{layer.name}' uses "
                f"'{sym.renderer.type}'."
            )

        symbol = sym.renderer.symbol

        # Opt-in geometry guard. Only consulted when ``strict_geom`` is set;
        # otherwise geometry is permissive and the style is mapped onto
        # whatever the target supports (see below). In single-layer mode a
        # mismatch is an error (the caller named one layer and one preset and
        # meant them together); in map-lookup mode it is a filter and the
        # layer is skipped.
        if strict_geom and allowed_geom is not None:
            geom = arcpy.Describe(layer).shapeType
            if geom not in allowed_geom:
                if using_lyr:
                    raise ValueError(
                        f"Preset targets {' / '.join(allowed_geom)} layers, "
                        f"but '{layer.name}' is {geom}."
                    )
                return None

        # Fill. ``symbol.color`` is the body fill on Polygon/Point/Multipoint.
        # On a Polyline the line carries no fill, so ArcPy ignores this and
        # only the stroke (below) defines the line: fill is effectively dropped.
        if parsed_fill is not None:
            symbol.color = _rgb(
                parsed_fill,
                fill_opacity if fill_opacity is not None else 100,
            )
        elif fill_opacity is not None:
            existing = symbol.color
            if isinstance(existing, dict) and "RGB" in existing:
                existing["RGB"][3] = fill_opacity
                symbol.color = existing
            else:
                # No existing fill to retune (e.g. a line symbol applied to a
                # polygon). Supply a transparent fallback so a zeroed opacity
                # still renders the body hollow instead of erroring.
                symbol.color = {"RGB": [0, 0, 0, fill_opacity]}

        # Stroke. ``outlineColor``/``outlineWidth`` are the outline on
        # Polygon/Point and the line itself on Polyline; ArcPy resolves the
        # right target per geometry.
        if parsed_stroke is not None:
            symbol.outlineColor = _rgb(parsed_stroke, 100)
        if stroke_width is not None:
            symbol.outlineWidth = stroke_width

        sym.renderer.symbol = symbol
        layer.symbology = sym
        return layer

    # ------------------------------------------------------------------ #
    # Apply and return                                                   #
    # ------------------------------------------------------------------ #
    updated = [r for r in (_apply_one(t) for t in targets) if r is not None]
    return updated[0] if using_lyr else updated


def get(target_map: arcpy.mp.Map, *, lyr_name: Optional[str] = None,
        lyr_source: Optional[_PathLike] = None,
        geom_type: Optional[_GeomType] = None) -> list:
    """
    Retrieve layer(s) from the map TOC by display name or data source path.

    When matching by ``lyr_name``, all layers with that name are returned.
    When matching by ``lyr_source``, only the first exact match is returned.
    Exactly one of ``lyr_name`` or ``lyr_source`` must be provided. Every
    argument after ``target_map`` is keyword-only.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to search.
    lyr_name : str, optional
        Keyword-only. Display name to match against; all matching layers are
        returned.
    lyr_source : str or Path, optional
        Data source path to match against; only the first exact match is
        returned. Memory layers should be matched by ``lyr_name`` instead.
        Their internal data source path is not predictable and cannot be
        used reliably with this parameter.
    geom_type : {'Point', 'Polyline', 'Polygon', 'Multipoint'}, optional
        Geometry type filter when matching by name. Only layers whose
        ``shapeType`` matches are included. Case-insensitive.
        Ignored when matching by ``lyr_source``. Default ``None`` (no filter).

    Returns
    -------
    list of arcpy.mp.Layer
        All matching layers. When matching by ``lyr_source``, the list
        contains at most one entry.

    Raises
    ------
    ValueError
        If neither or both of ``lyr_name`` and ``lyr_source`` are provided.
    ValueError
        If no matching layers are found in the map.

    Examples
    --------
    Get all layers named "rivers":

    >>> lyrs = arcsmith.lyr.get(target_map, lyr_name="rivers")

    Get only polyline "rivers" layers:

    >>> lyrs = arcsmith.lyr.get(target_map, lyr_name="rivers", geom_type="Polyline")

    Get a single layer by data source path:

    >>> lyrs = arcsmith.lyr.get(target_map, lyr_source="path/to/trails")

    Get a memory layer by its TOC display name:

    >>> lyrs = arcsmith.lyr.get(target_map, lyr_name="trails_memory")
    """
    matched = _match_layers(target_map, lyr_name=lyr_name, lyr_source=lyr_source,
                            geom_type=geom_type)
    if not matched:
        _raise_not_found(lyr_name, lyr_source, geom_type)

    return matched


def make_grp(target_map: arcpy.mp.Map, grp_name: str,
             layers: Optional[Union[arcpy.mp.Layer, list]] = None, *,
             parent_grp: Optional[arcpy.mp.Layer] = None) -> arcpy.mp.Layer:
    """
    Create a group layer in a map and return it, optionally filling it.

    Wraps ``arcpy.mp.Map.createGroupLayer``. The new group is added as the
    topmost entry of its container: the map's table of contents by default, or
    the parent group when ``parent_grp`` is given. Pass ``layers`` to move one
    or more existing map layers into the group as it is created, so the common
    "make a group and put these in it" workflow is a single call rather than a
    create-then-add sequence. Leave ``layers`` unset to create an empty group
    and populate it later. Pass ``parent_grp`` to nest the new group inside an
    existing group layer rather than adding it directly to the map.

    Each layer in ``layers`` is moved into the group: it is copied in and its
    original top-level entry is removed, so the layer ends up only inside the
    group rather than duplicated. Layers keep the order given, read top to
    bottom: each is added at the bottom of the group as the list is processed,
    so the first layer in the list ends up at the top of the group and the last
    at the bottom. For finer control over a single layer, such as positioning it
    against a sibling or keeping the original top-level entry, create the group
    here and call ``add_to_grp`` per layer instead.

    arcpy does not require group names to be unique, so calling this twice with
    the same ``grp_name`` produces two separate groups with that name. Hold on
    to the returned layer to act on a specific one rather than relying on a
    later name lookup.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to create the group layer in.
    grp_name : str
        Display name for the new group layer in the TOC.
    layers : arcpy.mp.Layer or list of arcpy.mp.Layer, optional
        Existing map layer(s) to move into the new group. List order is kept
        top to bottom in the group (first item at the top, last at the bottom).
        A single layer may be passed without a list. Each is removed from its
        original top-level position. Default ``None`` (the group is created
        empty).
    parent_grp : arcpy.mp.Layer, optional
        An existing group layer to nest the new group inside; the new group
        becomes the topmost entry of that parent group. Keyword-only. Default
        ``None`` (the new group is added directly to the map, as the topmost
        entry of the table of contents).

    Returns
    -------
    arcpy.mp.Layer
        The newly created group layer, holding any layers passed in ``layers``.

    Examples
    --------
    Create an empty group, then move a layer into it later:

    >>> grp = arcsmith.lyr.make_grp(target_map, "Backcountry")
    >>> riv = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
    >>> arcsmith.lyr.add_to_grp(target_map, grp, riv)

    Create a group and fill it in one call (roads ends up above trails, matching
    the list order top to bottom):

    >>> roads = arcsmith.lyr.get(target_map, lyr_name="roads")[0]
    >>> trails = arcsmith.lyr.get(target_map, lyr_name="trails")[0]
    >>> grp = arcsmith.lyr.make_grp(target_map, "Transport", [roads, trails])

    Create a group nested inside another group:

    >>> trails = arcsmith.lyr.make_grp(target_map, "Trails")
    >>> backcountry = arcsmith.lyr.make_grp(target_map, "Backcountry", parent_grp=trails)
    """
    if parent_grp is None:
        grp = target_map.createGroupLayer(grp_name)
    else:
        grp = target_map.createGroupLayer(grp_name, parent_grp)

    if layers is not None:
        for layer in (layers if isinstance(layers, list) else [layers]):
            add_to_grp(target_map, grp, layer)

    # arcpy.AddMessage(f"Group layer created: {grp_name}")
    return grp


def get_grp(target_map: arcpy.mp.Map, grp_name: Optional[str] = None, *,
            silent: bool = False) -> list:
    """
    Retrieve group layer(s) from the map TOC by display name.

    Scans the TOC for layers where ``isGroupLayer`` is True. All group
    layers with the matching name are returned.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to search.
    grp_name : str, optional
        Display name to match against; all matching group layers are
        returned. If omitted, every group layer in the map is returned.
    silent : bool, optional
        Keyword-only. If ``True``, return an empty list instead of raising
        when a named match finds nothing. Default ``False``.

    Returns
    -------
    list of arcpy.mp.Layer
        All matching group layers.

    Raises
    ------
    ValueError
        If ``grp_name`` is given and no matching group layer is found,
        unless ``silent=True``.

    Examples
    --------
    Get a group layer by name:

    >>> grp = arcsmith.lyr.get_grp(target_map, grp_name="Backcountry")[0]

    Get every group layer in the map:

    >>> grps = arcsmith.lyr.get_grp(target_map)

    Get a group layer if present, without raising when it is missing:

    >>> grps = arcsmith.lyr.get_grp(target_map, grp_name="Scratch", silent=True)
    """
    matched = [lyr for lyr in target_map.listLayers()
               if lyr.isGroupLayer and (grp_name is None or lyr.name == grp_name)]

    if not matched and grp_name is not None and not silent:
        raise ValueError(f"No group layer matching '{grp_name}' found in the map.")

    return matched


def add_to_grp(target_map: arcpy.mp.Map, grp_lyr: arcpy.mp.Layer,
               layer: arcpy.mp.Layer, *, position: _Position = "BOTTOM",
               relative_to: Optional[arcpy.mp.Layer] = None,
               placement: _Placement = "AFTER",
               remove_original: bool = True) -> arcpy.mp.Layer:
    """
    Move an existing layer into a group layer, with optional precise ordering.

    ``addLayerToGroup`` only *copies* the layer into the group and leaves the
    original top-level layer in place, so this function performs the full
    sequence: copy into the group, locate the in-group copy, optionally move
    it relative to a sibling, and optionally remove the original.

    Positioning happens in two stages. ``position`` (``"TOP"`` or
    ``"BOTTOM"``) is passed straight to ``addLayerToGroup`` and decides the
    initial drop point. These are the only placements arcpy accepts there.
    For index-level control, pass ``relative_to`` (a layer already inside the
    group) and ``placement`` (``"BEFORE"`` or ``"AFTER"``); the in-group copy
    is then repositioned with ``moveLayer``.

    The three layer arguments are positional; every option after them
    (``position``, ``relative_to``, ``placement``, ``remove_original``) is
    keyword-only.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object containing both the group layer and the layer to move.
    grp_lyr : arcpy.mp.Layer
        The destination group layer (e.g. from ``get_grp``).
    layer : arcpy.mp.Layer
        The layer to move into the group (e.g. from ``get``).
    position : {'TOP', 'BOTTOM'}, optional
        Keyword-only. Initial placement within the group, passed to
        ``addLayerToGroup``. Case-insensitive. Default ``'BOTTOM'``.
    relative_to : arcpy.mp.Layer, optional
        Keyword-only. A layer already inside the group to position the moved
        layer against. When given, a ``moveLayer`` call runs after the add.
        Must already be a child of ``grp_lyr``. Default ``None`` (no
        repositioning).
    placement : {'BEFORE', 'AFTER'}, optional
        Keyword-only. Where to place the moved layer relative to
        ``relative_to``. Case-insensitive. Ignored when ``relative_to`` is
        ``None``. Default ``'AFTER'``.
    remove_original : bool, optional
        Keyword-only. If ``True``, remove the original top-level layer after
        copying, by reference, leaving only the in-group copy. Default
        ``True``.

    Returns
    -------
    arcpy.mp.Layer
        The in-group copy of the layer.

    Raises
    ------
    ValueError
        If ``position`` is not ``'TOP'`` or ``'BOTTOM'``, if ``placement`` is
        not ``'BEFORE'`` or ``'AFTER'``, or if the in-group copy cannot be
        located after the add.

    Examples
    --------
    Move a layer into a group at the bottom, cleaning up the original:

    >>> grp = arcsmith.lyr.get_grp(target_map, grp_name="Backcountry")[0]
    >>> riv = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
    >>> arcsmith.lyr.add_to_grp(target_map, grp, riv)

    Drop it at the top instead:

    >>> arcsmith.lyr.add_to_grp(target_map, grp, riv, position="TOP")

    Place it directly above an existing sibling:

    >>> roads = arcsmith.lyr.get(target_map, lyr_name="roads")[0]
    >>> riv = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
    >>> arcsmith.lyr.add_to_grp(target_map, grp, riv,
    ...                           relative_to=roads, placement="BEFORE")

    Keep the original top-level layer in place as well as the in-group copy:

    >>> arcsmith.lyr.add_to_grp(target_map, grp, riv, remove_original=False)
    """
    position = position.upper()
    if position not in ("TOP", "BOTTOM"):
        raise ValueError("position must be 'TOP' or 'BOTTOM'.")

    placement = placement.upper()
    if placement not in ("BEFORE", "AFTER"):
        raise ValueError("placement must be 'BEFORE' or 'AFTER'.")

    # Snapshot the group's children before the add so the new copy can be
    # told apart from any pre-existing siblings sharing its display name.
    before = set(id(child) for child in grp_lyr.listLayers())

    target_map.addLayerToGroup(grp_lyr, layer, position)

    in_group = next((child for child in grp_lyr.listLayers()
                     if id(child) not in before), None)
    if in_group is None:
        raise ValueError("Could not locate the in-group copy after add.")

    if relative_to is not None:
        target_map.moveLayer(relative_to, in_group, placement)

    if remove_original:
        target_map.removeLayer(layer)

    return in_group


def _parent_path(layer: arcpy.mp.Layer) -> str:
    """Return a layer's TOC parent path: the ``longName`` minus its own name.

    ``longName`` encodes the full table-of-contents path with backslash
    separators (``"GroupA\\Rivers"`` for a layer inside ``GroupA``,
    ``"Rivers"`` for a top-level layer). Stripping the final segment leaves the
    path of the containing level (``""`` for a top-level layer). Two layers are
    direct siblings exactly when their parent paths are equal, which also
    excludes nested descendants (they carry a longer path).
    """
    return str(layer.longName).rpartition("\\")[0]


def move(target_map: arcpy.mp.Map, layer: arcpy.mp.Layer, *,
         relative_to: Optional[arcpy.mp.Layer] = None,
         placement: _Placement = "BEFORE",
         position: Optional[_Position] = None) -> arcpy.mp.Layer:
    """
    Reorder a layer within its current level in the map's table of contents.

    Changes only the draw/TOC order of ``layer`` among its siblings, the layers
    that share its level (the map's top level, or whichever group it currently
    lives in). It does not change grouping: the layer stays in the same
    container. To move a layer into a group, use ``add_to_grp``.

    Two targeting modes are available and exactly one must be used per call.
    Everything after ``layer`` is keyword-only.

    * Relative: pass ``relative_to`` (a sibling) and optionally ``placement``
      (``"BEFORE"`` or ``"AFTER"``) to drop ``layer`` just before or after it.
      The reference layer must sit at the same level as ``layer``.
    * Absolute: pass ``position`` (``"TOP"`` or ``"BOTTOM"``) to send ``layer``
      to the top or bottom of its current level. A layer already at that edge is
      left where it is.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object containing the layer to move.
    layer : arcpy.mp.Layer
        The layer to reorder.
    relative_to : arcpy.mp.Layer, optional
        Keyword-only. A sibling layer to position ``layer`` against. Must share
        ``layer``'s level. Mutually exclusive with ``position``.
    placement : {'BEFORE', 'AFTER'}, optional
        Keyword-only. Where to place ``layer`` relative to ``relative_to``.
        Case-insensitive. Ignored in absolute mode. Default ``'BEFORE'``.
    position : {'TOP', 'BOTTOM'}, optional
        Keyword-only. Send ``layer`` to the top or bottom of its current level.
        Case-insensitive. Mutually exclusive with ``relative_to``.

    Returns
    -------
    arcpy.mp.Layer
        The moved layer (the same object passed in).

    Raises
    ------
    ValueError
        If neither or both of ``relative_to`` and ``position`` are provided.
    ValueError
        If ``placement`` is not ``'BEFORE'`` or ``'AFTER'``, or ``position`` is
        not ``'TOP'`` or ``'BOTTOM'``.
    ValueError
        If ``relative_to`` is not at the same level as ``layer``.

    Notes
    -----
    Layer ordering uses ``arcpy.mp.Map.moveLayer``, which positions one layer
    relative to another at the same level. Absolute ``"TOP"``/``"BOTTOM"`` moves
    are resolved by referencing the current top or bottom sibling, found from
    the top-to-bottom order of ``listLayers()``.

    arcpy permits duplicate display names at one level. In the rare case where
    every sibling shares ``layer``'s name, an absolute move is left as a no-op
    rather than guessing which one to anchor against.

    Examples
    --------
    Move a layer to just above a sibling:

    >>> roads = arcsmith.lyr.get(target_map, lyr_name="roads")[0]
    >>> rivers = arcsmith.lyr.get(target_map, lyr_name="rivers")[0]
    >>> arcsmith.lyr.move(target_map, rivers, relative_to=roads, placement="BEFORE")

    Move a layer to just below a sibling:

    >>> arcsmith.lyr.move(target_map, rivers, relative_to=roads, placement="AFTER")

    Send a layer to the top of its current level:

    >>> arcsmith.lyr.move(target_map, rivers, position="TOP")

    Send a layer to the bottom of its current level:

    >>> arcsmith.lyr.move(target_map, rivers, position="BOTTOM")
    """
    using_relative = relative_to is not None
    using_position = position is not None

    if using_relative == using_position:
        raise ValueError(
            "Provide exactly one of 'relative_to' or 'position'."
        )

    if using_relative:
        placement = placement.upper()
        if placement not in ("BEFORE", "AFTER"):
            raise ValueError("placement must be 'BEFORE' or 'AFTER'.")
        if _parent_path(relative_to) != _parent_path(layer):
            raise ValueError(
                "'relative_to' must be at the same level as 'layer' "
                "(both top-level, or both in the same group)."
            )
        target_map.moveLayer(relative_to, layer, placement)
        return layer

    position = position.upper()
    if position not in ("TOP", "BOTTOM"):
        raise ValueError("position must be 'TOP' or 'BOTTOM'.")

    # Resolve the edge of the layer's current level from the top-to-bottom
    # listLayers() order. Anchor against the first/last sibling that is not the
    # layer itself: this avoids a self-referential move and makes an
    # already-at-edge layer a natural no-op.
    parent = _parent_path(layer)
    own_name = str(layer.longName)
    siblings = [lyr for lyr in target_map.listLayers()
                if _parent_path(lyr) == parent]
    others = [lyr for lyr in siblings if str(lyr.longName) != own_name]
    if not others:
        return layer

    if position == "TOP":
        target_map.moveLayer(others[0], layer, "BEFORE")
    else:
        target_map.moveLayer(others[-1], layer, "AFTER")

    return layer


def remove(target_map: arcpy.mp.Map, *, lyr_name: Optional[str] = None,
           lyr_source: Optional[_PathLike] = None,
           geom_type: Optional[_GeomType] = None, silent: bool = False,
           layer: Optional[Union[arcpy.mp.Layer, list]] = None) -> list:
    """
    Remove layer(s) from the map TOC by layer reference, display name, or
    data source path.

    Three matching modes, exactly one of which must be used per call:

    * ``layer``: removes the exact Layer object(s) given. No TOC scan or
      name/source matching is performed, so only the referenced instance is
      removed. This is the correct mode after ``addLayerToGroup``, which
      leaves the original top-level layer in place: pass the reference you
      already hold (e.g. from ``get``) to remove just that one, leaving
      the in-group copy untouched.
    * ``lyr_name``: removes *all* layers with that display name.
    * ``lyr_source``: removes only the *first* layer with that data source.

    Name and source matching consider layers of **any** type (feature, raster,
    group, etc.), so this can remove a layer that symbology helpers like
    ``get`` would skip. Removing a group layer removes its children with it.

    Every argument after ``target_map`` is keyword-only.

    Parameters
    ----------
    target_map : arcpy.mp.Map
        Map object to remove layer(s) from.
    lyr_name : str, optional
        Keyword-only. Display name to match against; all matching layers are
        removed.
    lyr_source : str or Path, optional
        Keyword-only. Data source path to match against; only the first match
        is removed. Layers without a data source (e.g. group or basemap layers)
        cannot be matched in this mode; match those by ``lyr_name`` instead.
    geom_type : {'Point', 'Polyline', 'Polygon', 'Multipoint'}, optional
        Keyword-only. Geometry type filter when matching by name.
        Case-insensitive. Applies to feature layers only; non-feature layers
        have no geometry and are never matched when a ``geom_type`` is given.
        Ignored when matching by ``lyr_source`` or ``layer``. Default ``None``.
    silent : bool, optional
        Keyword-only. If ``True``, return ``0`` instead of raising when a
        name/source match finds nothing. Invalid argument combinations still
        raise. Has no effect in ``layer`` mode. Default ``False``.
    layer : arcpy.mp.Layer or list of arcpy.mp.Layer, optional
        Keyword-only. The exact layer object(s) to remove. Mutually
        exclusive with ``lyr_name`` and ``lyr_source``.

    Returns
    -------
    list of arcpy.mp.Layer
        All layers that were removed.

    Raises
    ------
    ValueError
        If ``layer`` is combined with ``lyr_name`` or ``lyr_source``, or if
        neither nor both of ``lyr_name``/``lyr_source`` are provided when
        ``layer`` is omitted.
    ValueError
        If a name/source match finds no layers, unless ``silent=True``.

    Examples
    --------
    Remove the exact layer you grabbed, leaving an in-group copy intact:

    >>> eff_lyr = arcsmith.lyr.get(current_map, lyr_name="Trails")[0]
    >>> current_map.addLayerToGroup(eff_grp_lyr, eff_lyr)
    >>> arcsmith.lyr.remove(current_map, layer=eff_lyr)

    Remove every layer returned by a query in one call:

    >>> lyrs = arcsmith.lyr.get(current_map, lyr_name="rivers")
    >>> arcsmith.lyr.remove(current_map, layer=lyrs)

    Remove all layers named "rivers" by name:

    >>> arcsmith.lyr.remove(target_map, lyr_name="rivers")

    Remove a layer if present, without raising when it is missing:

    >>> arcsmith.lyr.remove(target_map, lyr_name="scratch", silent=True)
    """
    if layer is not None:
        if lyr_name is not None or lyr_source is not None:
            raise ValueError("Provide 'layer' alone, not with 'lyr_name' or 'lyr_source'.")
        layers = list(layer) if isinstance(layer, (list, tuple)) else [layer]
        for lyr in layers:
            target_map.removeLayer(lyr)
        return layers

    matched = _match_layers(target_map, lyr_name=lyr_name, lyr_source=lyr_source,
                            geom_type=geom_type, feature_only=False)
    if not matched and not silent:
        _raise_not_found(lyr_name, lyr_source, geom_type)

    for lyr in matched:
        target_map.removeLayer(lyr)

    return matched