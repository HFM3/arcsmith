# -*- coding: utf-8 -*-
"""
test_lyr.pyt
ArcGIS Pro test toolbox for arcsmith.lyr.

The pytest suite (tests/test_lyr.py) covers only the pure colour/preset helpers
(``_parse_color``, ``_random_simple_preset``, ``_seed_styles``). Every public
function manipulates a live map and its layers (addDataFromPath, symbology,
listLayers, addLayerToGroup, moveLayer, removeLayer) and can only run inside an
open ArcGIS Pro project. This toolbox drives them against the CURRENT project's
active map:

    - add           (add a source, with auto / preset / lyrx / explicit styling)
    - simple_sym    (restyle matched layers; presets + cross-geometry mapping)
    - get       (look up layers by name or source, with a geometry filter)
    - get_grp   (look up group layers)
    - add_to_grp  (move a layer into a group, with precise ordering)
    - make_grp    (create a group layer, optionally filling it on creation)
    - apply_lyrx    (push .lyrx symbology onto a layer object or matched layers)
    - remove        (remove layers by name or source)
    - move          (reorder a layer within its level: relative or top/bottom)

IMPORTANT: run these from a project that has an active map with some layers in
it. Each tool operates on ``ArcGISProject("CURRENT").activeMap``.
"""

import sys
from pathlib import Path

# Make the in-repo src/ layout importable so this toolbox tests the actual
# source under ../../src, with no install required (mirrors tests/conftest.py).
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import arcpy
import arcsmith
from importlib import reload

# Reload arcsmith from ../../src on every toolbox load, so edits to the package
# source are picked up without restarting ArcGIS Pro (Pro caches imports for the
# session). Submodules reload before the package; flds before fc, since fc
# imports from flds.
for _name in ("param", "flds", "fc", "tbl", "ws", "lyr"):
    reload(getattr(arcsmith, _name))
reload(arcsmith)


def _active_map():
    """Return the CURRENT project's active map, or raise a clear error."""
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.activeMap
    if m is None:
        raise arcpy.ExecuteError(
            "No active map. Open a map view in the current project and try again."
        )
    return m


def _preset_choices():
    """All registered preset names, for the style dropdowns."""
    return sorted(arcsmith.lyr.PRESETS)


# ===========================================================================
class Toolbox:
    def __init__(self):
        self.label = "Test arcsmith.lyr"
        self.alias = "test_arcsmith_lyr"
        self.tools = [
            AddLayer,
            SimpleSym,
            GetLayer,
            GetGroupLayer,
            AddToGroup,
            ApplyLyrx,
            RemoveLayer,
            MakeGroup,
            MoveLayer,
        ]


# ===========================================================================
# 1. add
# ===========================================================================
class AddLayer:
    def __init__(self):
        self.label = "01 Add Layer"
        self.description = (
            "Test arcsmith.lyr.add - adds a data source to the active map. "
            "Leave styling options empty to see the curated random default "
            "matched to geometry (polygon = pale fill, point = solid marker, "
            "line = coloured stroke). Or pick a preset, supply a .lyrx file, or "
            "set explicit colours. Preset and .lyrx are mutually exclusive."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Data Source to Add",
            name="lyr_src",
            datatype=["GPFeatureLayer", "DEFeatureClass"],
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Layer Name (optional)",
            name="lyr_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Preset (optional)",
            name="preset",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.filter.type = "ValueList"
        p2.filter.list = _preset_choices()

        p3 = arcpy.Parameter(
            displayName=".lyrx File (optional, mutually exclusive with preset)",
            name="lyrx_src",
            datatype="DEFile",
            parameterType="Optional",
            direction="Input",
        )
        p3.filter.list = ["lyrx"]

        p4 = arcpy.Parameter(
            displayName="Fill Color (hex, optional)",
            name="fill_color",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p5 = arcpy.Parameter(
            displayName="Stroke Color (hex, optional)",
            name="stroke_color",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p6 = arcpy.Parameter(
            displayName="Stage input to memory first (exercise the memory branch)",
            name="stage_to_memory",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p6.value = False

        return [p0, p1, p2, p3, p4, p5, p6]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Preset and lyrx are mutually exclusive; disable each when the other set.
        preset, lyrx = parameters[2], parameters[3]
        lyrx.enabled = not bool(preset.value)
        preset.enabled = not bool(lyrx.value)
        return

    def updateMessages(self, parameters):
        if parameters[2].value and parameters[3].value:
            parameters[3].setErrorMessage("Provide either a preset or a .lyrx file, not both.")
        return

    def execute(self, parameters, messages):
        m = _active_map()
        lyr_src = arcsmith.param.to_path(parameters[0])
        lyr_name = parameters[1].valueAsText or None
        preset = parameters[2].valueAsText or None
        lyrx_src = parameters[3].valueAsText or None
        stage_to_memory = bool(parameters[6].value)

        # Copy the source into the 'memory' workspace and add that instead, so
        # add() must route through MakeFeatureLayer + addLayer rather than
        # addDataFromPath. Confirms in-memory sources are addable.
        if stage_to_memory:
            mem_src = f"memory\\{Path(lyr_src).stem}"
            if arcpy.Exists(mem_src):
                arcpy.management.Delete(mem_src)
            arcpy.management.CopyFeatures(lyr_src, mem_src)
            arcpy.AddMessage(f"Staged input to memory -> {mem_src}")
            lyr_src = mem_src

        # Only pass explicit style kwargs when actually supplied, so the unset
        # sentinel default is preserved otherwise.
        kwargs = {}
        if parameters[4].valueAsText:
            kwargs["fill_color"] = parameters[4].valueAsText
        if parameters[5].valueAsText:
            kwargs["stroke_color"] = parameters[5].valueAsText

        lyr = arcsmith.lyr.add(
            m, lyr_src, lyr_name=lyr_name, lyrx_src=lyrx_src, preset=preset, **kwargs
        )
        arcpy.AddMessage(f"Added layer -> {lyr.name}")
        try:
            arcpy.AddMessage(f"  geometry: {arcpy.Describe(lyr).shapeType}")
        except Exception:
            pass

    def postExecute(self, parameters):
        return


# ===========================================================================
# 2. simple_sym
# ===========================================================================
class SimpleSym:
    def __init__(self):
        self.label = "02 Simple Symbology"
        self.description = (
            "Test arcsmith.lyr.simple_sym - restyle every layer matching a name "
            "in the active map. Apply a preset and/or explicit colours/widths. "
            "Try a polygon preset on a line layer to see the permissive "
            "cross-geometry mapping; turn on Strict Geometry to make a mismatch "
            "skip the layer instead."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Layer to Match (drag from Contents, or pick)",
            name="lyr_name",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Preset (optional)",
            name="preset",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p1.filter.type = "ValueList"
        p1.filter.list = _preset_choices()

        p2 = arcpy.Parameter(
            displayName="Fill Color (hex, optional)",
            name="fill_color",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p3 = arcpy.Parameter(
            displayName="Fill Opacity 0-100 (optional)",
            name="fill_opacity",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )

        p4 = arcpy.Parameter(
            displayName="Stroke Color (hex, optional)",
            name="stroke_color",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p5 = arcpy.Parameter(
            displayName="Stroke Width pt (optional)",
            name="stroke_width",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )

        p6 = arcpy.Parameter(
            displayName="Strict Geometry (skip on preset/geometry mismatch)",
            name="strict_geom",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p6.value = False

        return [p0, p1, p2, p3, p4, p5, p6]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        lyr_name = parameters[0].valueAsText
        preset = parameters[1].valueAsText or None
        strict_geom = bool(parameters[6].value)

        kwargs = {}
        if parameters[2].valueAsText:
            kwargs["fill_color"] = parameters[2].valueAsText
        if parameters[3].value is not None:
            kwargs["fill_opacity"] = parameters[3].value
        if parameters[4].valueAsText:
            kwargs["stroke_color"] = parameters[4].valueAsText
        if parameters[5].value is not None:
            kwargs["stroke_width"] = parameters[5].value

        updated = arcsmith.lyr.simple_sym(
            target_map=m, lyr_name=lyr_name, preset=preset,
            strict_geom=strict_geom, **kwargs
        )
        arcpy.AddMessage(f"Restyled {len(updated)} layer(s) named {lyr_name!r}:")
        for lyr in updated:
            arcpy.AddMessage(f"  - {lyr.name}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 3. get
# ===========================================================================
class GetLayer:
    def __init__(self):
        self.label = "03 Get Layer"
        self.description = (
            "Test arcsmith.lyr.get - look up feature layers in the active "
            "map by display name (all matches) or by data source path (first "
            "match). Optionally filter name matches by geometry type. Exactly "
            "one of Name / Source must be provided; a no-match raises."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Layer (drag/pick; matches all layers of this name)",
            name="lyr_name",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Layer Source Path (match first by source)",
            name="lyr_source",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Geometry Type Filter (name mode only)",
            name="geom_type",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.filter.type = "ValueList"
        p2.filter.list = ["Point", "Polyline", "Polygon", "Multipoint"]

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        lyr_name = parameters[0].valueAsText or None
        lyr_source = parameters[1].valueAsText or None
        geom_type = parameters[2].valueAsText or None

        matched = arcsmith.lyr.get(
            m, lyr_name=lyr_name, lyr_source=lyr_source, geom_type=geom_type
        )
        arcpy.AddMessage(f"Matched {len(matched)} layer(s):")
        for lyr in matched:
            src = getattr(lyr, "dataSource", "?")
            arcpy.AddMessage(f"  - {lyr.name}  ({src})")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 4. get_grp
# ===========================================================================
class GetGroupLayer:
    def __init__(self):
        self.label = "04 Get Group Layer"
        self.description = (
            "Test arcsmith.lyr.get_grp - find group layers in the active "
            "map. Leave Name empty to list every group layer. With a name, a "
            "no-match raises unless Silent is on."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Group Layer (drag/pick; empty = all group layers)",
            name="grp_name",
            datatype="GPGroupLayer",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Silent (return empty instead of raising on no match)",
            name="silent",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p1.value = False

        return [p0, p1]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        grp_name = parameters[0].valueAsText or None
        silent = bool(parameters[1].value)

        matched = arcsmith.lyr.get_grp(m, grp_name=grp_name, silent=silent)
        arcpy.AddMessage(f"Matched {len(matched)} group layer(s):")
        for grp in matched:
            children = [c.name for c in grp.listLayers()]
            arcpy.AddMessage(f"  - {grp.name}  children={children}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 5. add_to_grp
# ===========================================================================
class AddToGroup:
    def __init__(self):
        self.label = "05 Add To Group"
        self.description = (
            "Test arcsmith.lyr.add_to_grp - move a top-level layer into an "
            "existing group layer. Drag the destination group and the layer to "
            "move from the Contents pane (or pick them). Sets the initial drop "
            "point (TOP/BOTTOM); optionally repositions BEFORE/AFTER a sibling "
            "already in the group. By default the original top-level layer is "
            "removed, leaving only the in-group copy."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Group Layer (drag from Contents, or pick)",
            name="grp",
            datatype="GPGroupLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Layer to Move (drag from Contents, or pick)",
            name="lyr_name",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Initial Position",
            name="position",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.filter.type = "ValueList"
        p2.filter.list = ["TOP", "BOTTOM"]
        p2.value = "BOTTOM"

        p3 = arcpy.Parameter(
            displayName="Reposition Relative To (sibling in the group, optional)",
            name="relative_to",
            datatype="GPLayer",
            parameterType="Optional",
            direction="Input",
        )

        p4 = arcpy.Parameter(
            displayName="Placement (when repositioning)",
            name="placement",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p4.filter.type = "ValueList"
        p4.filter.list = ["BEFORE", "AFTER"]
        p4.value = "AFTER"

        p5 = arcpy.Parameter(
            displayName="Remove Original Top-Level Layer",
            name="remove_original",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p5.value = True

        return [p0, p1, p2, p3, p4, p5]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        # The layer parameters yield the picked layers' TOC names; resolve them
        # back to the active map's Layer objects that add_to_grp needs. (If
        # several groups share a name, the first is used.)
        grp_name = parameters[0].valueAsText
        lyr_name = parameters[1].valueAsText
        position = parameters[2].valueAsText or "BOTTOM"
        relative_to_name = parameters[3].valueAsText or None
        placement = parameters[4].valueAsText or "AFTER"
        remove_original = bool(parameters[5].value)

        grp = arcsmith.lyr.get_grp(m, grp_name=grp_name)[0]
        layer = arcsmith.lyr.get(m, lyr_name=lyr_name)[0]

        relative_to = None
        if relative_to_name:
            relative_to = next(
                (c for c in grp.listLayers() if c.name == relative_to_name), None
            )
            if relative_to is None:
                raise arcpy.ExecuteError(
                    f"No sibling named {relative_to_name!r} inside group {grp_name!r}."
                )

        in_group = arcsmith.lyr.add_to_grp(
            m, grp, layer, position=position,
            relative_to=relative_to, placement=placement,
            remove_original=remove_original,
        )
        arcpy.AddMessage(f"Moved {lyr_name!r} into group {grp_name!r}.")
        arcpy.AddMessage(f"In-group order is now: {[c.name for c in grp.listLayers()]}")
        arcpy.AddMessage(f"In-group copy: {in_group.name}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 6. apply_lyrx
# ===========================================================================
class ApplyLyrx:
    def __init__(self):
        self.label = "06 Apply Lyrx"
        self.description = (
            "Test arcsmith.lyr.apply_lyrx - push symbology from a .lyrx file "
            "onto layers in the active map. Two modes: map-lookup (match by "
            "name, all matches with optional geometry filter, or by source, "
            "first match), or direct layer-object mode (resolve the first "
            "name match to a Layer object and style it directly, returning "
            "that one layer). Direct mode takes precedence when set."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName=".lyrx File",
            name="lyrx_src",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )
        p0.filter.list = ["lyrx"]

        p1 = arcpy.Parameter(
            displayName="Layer (drag/pick; matches all layers of this name)",
            name="lyr_name",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Layer Source Path (match first by source)",
            name="lyr_source",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p3 = arcpy.Parameter(
            displayName="Geometry Type Filter (name mode only)",
            name="geom_type",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p3.filter.type = "ValueList"
        p3.filter.list = ["Point", "Polyline", "Polygon", "Multipoint"]

        p4 = arcpy.Parameter(
            displayName="Direct Layer Mode (style first name match as a Layer object)",
            name="lyr_obj",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2, p3, p4]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        lyrx_src = parameters[0].valueAsText
        lyr_name = parameters[1].valueAsText or None
        lyr_source = parameters[2].valueAsText or None
        geom_type = parameters[3].valueAsText or None
        lyr_obj_name = parameters[4].valueAsText or None

        if lyr_obj_name is not None:
            # Direct lyr mode: resolve a real Layer object from the active map
            # and hand it straight to apply_lyrx with no map-lookup args. This
            # exercises the single-layer path, which returns the styled layer
            # itself rather than a list.
            layer = arcsmith.lyr.get(m, lyr_name=lyr_obj_name)[0]
            result = arcsmith.lyr.apply_lyrx(lyrx_src, layer)
            arcpy.AddMessage(
                f"Applied {Path(lyrx_src).name} to layer object "
                f"{result.name!r} (direct lyr mode)."
            )
            return

        updated = arcsmith.lyr.apply_lyrx(
            lyrx_src, target_map=m, lyr_name=lyr_name, lyr_source=lyr_source,
            geom_type=geom_type
        )
        arcpy.AddMessage(f"Applied {Path(lyrx_src).name} to {len(updated)} layer(s):")
        for lyr in updated:
            arcpy.AddMessage(f"  - {lyr.name}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 7. remove
# ===========================================================================
class RemoveLayer:
    def __init__(self):
        self.label = "07 Remove Layer"
        self.description = (
            "Test arcsmith.lyr.remove - remove layers from the active map by "
            "display name (all matches) or data source path (first match). With "
            "Silent on, a no-match returns quietly instead of raising."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Layer (drag/pick any type; removes all of this name)",
            name="lyr_name",
            datatype="GPLayer",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Layer Source Path (remove first by source)",
            name="lyr_source",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Geometry Type Filter (name mode only)",
            name="geom_type",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.filter.type = "ValueList"
        p2.filter.list = ["Point", "Polyline", "Polygon", "Multipoint"]

        p3 = arcpy.Parameter(
            displayName="Silent (no raise on no match)",
            name="silent",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p3.value = False

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        lyr_name = parameters[0].valueAsText or None
        lyr_source = parameters[1].valueAsText or None
        geom_type = parameters[2].valueAsText or None
        silent = bool(parameters[3].value)

        removed = arcsmith.lyr.remove(
            m, lyr_name=lyr_name, lyr_source=lyr_source,
            geom_type=geom_type, silent=silent,
        )
        # A removed Layer object is detached from the map, so its attributes
        # (e.g. .name) can no longer be read. Report the count and the match
        # criterion the user supplied rather than inspecting the returned layers.
        target = lyr_name or lyr_source or "(all matches)"
        arcpy.AddMessage(f"Removed {len(removed)} layer(s) matching {target!r}.")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 8. make_grp
# ===========================================================================
class MakeGroup:
    def __init__(self):
        self.label = "08 Make Group"
        self.description = (
            "Test arcsmith.lyr.make_grp - create a group layer in the active "
            "map, optionally moving existing top-level layers into it as it is "
            "created. The group is created at the top of the Contents pane. Pick "
            "one or more layers to drop into it, or leave empty for an empty "
            "group. Use Parent Group to nest the new group inside an existing "
            "group. Moved layers are removed from their original top-level spot."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="New Group Name",
            name="grp_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Layers to Move Into the Group (optional)",
            name="layers",
            datatype="GPLayer",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
        )

        p2 = arcpy.Parameter(
            displayName="Parent Group (nest inside, optional)",
            name="parent_grp",
            datatype="GPGroupLayer",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        grp_name = parameters[0].valueAsText
        parent_name = parameters[2].valueAsText or None

        # Resolve picked layer names back to the map's Layer objects (any type).
        layers = None
        if parameters[1].values:
            names = [str(v) for v in parameters[1].values]
            layers = [lyr for n in names for lyr in m.listLayers(n)]

        parent = None
        if parent_name:
            parent = arcsmith.lyr.get_grp(m, grp_name=parent_name)[0]

        grp = arcsmith.lyr.make_grp(m, grp_name, layers=layers, parent_grp=parent)
        arcpy.AddMessage(f"Created group {grp.name!r}")
        arcpy.AddMessage(f"Children: {[c.name for c in grp.listLayers()]}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 9. move
# ===========================================================================
class MoveLayer:
    def __init__(self):
        self.label = "09 Move Layer"
        self.description = (
            "Test arcsmith.lyr.move - reorder a layer within its current level "
            "(the map's top level, or whichever group it lives in). Two modes, "
            "use exactly one: fill 'Relative To' (with BEFORE/AFTER) to drop the "
            "layer next to a sibling, or fill 'Position' (TOP/BOTTOM) to send it "
            "to the edge of its level. Leaving both empty or filling both is an "
            "error, by design."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Layer to Move (drag from Contents, or pick)",
            name="lyr_name",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Relative To (sibling layer; relative mode)",
            name="relative_to",
            datatype="GPLayer",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Placement (when using Relative To)",
            name="placement",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.filter.type = "ValueList"
        p2.filter.list = ["BEFORE", "AFTER"]
        p2.value = "BEFORE"

        p3 = arcpy.Parameter(
            displayName="Position (absolute mode)",
            name="position",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p3.filter.type = "ValueList"
        p3.filter.list = ["TOP", "BOTTOM"]

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        # Layer parameters yield the picked layers' TOC names; resolve the layer
        # to move back to its Layer object. Pass only the arguments the user
        # actually supplied, so move's own validation handles the
        # neither/both-modes cases.
        lyr_name = parameters[0].valueAsText
        relative_to_name = parameters[1].valueAsText or None
        placement = parameters[2].valueAsText or "BEFORE"
        position = parameters[3].valueAsText or None

        layer = arcsmith.lyr.get(m, lyr_name=lyr_name)[0]

        kwargs = {}
        if relative_to_name:
            relative_to = next(
                (lyr for lyr in m.listLayers() if lyr.name == relative_to_name), None
            )
            if relative_to is None:
                raise arcpy.ExecuteError(
                    f"No layer named {relative_to_name!r} in the map."
                )
            kwargs["relative_to"] = relative_to
            kwargs["placement"] = placement
        if position:
            kwargs["position"] = position

        moved = arcsmith.lyr.move(m, layer, **kwargs)

        # Report the new order of the moved layer's level for confirmation.
        parent = str(moved.longName).rpartition("\\")[0]
        order = [lyr.name for lyr in m.listLayers()
                 if str(lyr.longName).rpartition("\\")[0] == parent]
        arcpy.AddMessage(f"Moved {moved.name!r}.")
        arcpy.AddMessage(f"Level order is now: {order}")

    def postExecute(self, parameters):
        return
