# -*- coding: utf-8 -*-
"""
test_tbl.pyt
ArcGIS Pro test toolbox for arcsmith.tbl.

tbl.py has no pytest coverage: every function calls into arcpy. This toolbox
drives them live, ordered from the simplest map-TOC operations up to the more
involved data operations:

    - add_to_map      (add a standalone table to the active map)
    - remove_from_map (remove standalone table(s) from the map)
    - get_table       (look up standalone table(s) by name/source)
    - from_rows       (table creation + type inference branches)
    - add_rows        (append rows to an existing table via InsertCursor)
    - join_lookup     (table-free 1:1 join; matched/unmatched accounting)
    - join_table      (permanent JoinField with keep/drop field selection)

``from_rows`` takes in-memory Python rows, which a parameter form cannot easily
supply, so that tool offers a set of curated demo datasets. Each one targets a
specific branch (single-column inferred, multi-column inferred, explicit types,
explicit text length, empty-with-explicit-schema) that is otherwise hard to hit
from the UI.
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


# Curated demo datasets for from_rows, one per code path worth exercising.
# Each value is (rows, fields, note).
_DEMO_ROWS = {
    "Single column, inferred TEXT (flat scalars)": (
        ["NF", "LM", "MG"],
        ["AREA_CODE"],
        "Flat list of scalars -> 1-column table; TEXT length sized to longest.",
    ),
    "Multi column, inferred types": (
        [("NF", "North Fork", 3), ("LM", "Lake McDonald", 7), ("MG", "Many Glacier", 12)],
        ["AREA_CODE", "AREA_NAME", "DISTRICT"],
        "str -> TEXT, str -> TEXT, int -> LONG inferred from first non-null value.",
    ),
    "Explicit types + text length": (
        [(1, "Going-to-the-Sun", 17), (2, "Many Glacier", 17), (3, "Two Medicine", 17)],
        [("BUS_ID", "LONG"), ("ROUTE", "TEXT", 32), ("SEATS", "SHORT")],
        "Explicit (name, type) and (name, TEXT, length) specs.",
    ),
    "Empty rows + explicit schema": (
        [],
        [("CODE", "TEXT", 4), ("COUNT", "LONG")],
        "Empty data is allowed only when every field has an explicit type.",
    ),
}


# ===========================================================================
class Toolbox:
    def __init__(self):
        self.label = "Test arcsmith.tbl"
        self.alias = "test_arcsmith_tbl"
        # Ordered simplest-first: map-TOC table ops, then data ops.
        self.tools = [
            AddTableToMap,
            RemoveTableFromMap,
            GetTable,
            FromRows,
            JoinLookup,
            JoinTable,
            AddRows,
        ]


# ===========================================================================
# 1. add_to_map
# ===========================================================================
class AddTableToMap:
    def __init__(self):
        self.label = "01 Add Table To Map"
        self.description = (
            "Test arcsmith.tbl.add_to_map - add a standalone table to the active "
            "map. A standalone table lives under the map's Standalone Tables "
            "(not as a layer). Enable 'Stage input to memory first' to copy the "
            "table into the 'memory' workspace and add that, exercising the "
            "in-memory staging path (MakeTableView + addTable)."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Source Table (table dataset)",
            name="table_src",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Table Name (optional)",
            name="table_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Stage input to memory first (exercise the memory path)",
            name="stage_to_memory",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p2.value = False

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        table_src = arcsmith.param.to_path(parameters[0])
        table_name = parameters[1].valueAsText or None
        stage_to_memory = bool(parameters[2].value)

        # Copy the source into the 'memory' workspace and add that instead, so
        # add_to_map must route through MakeTableView + addTable rather than
        # addDataFromPath. Confirms in-memory tables are addable.
        if stage_to_memory:
            mem_src = f"memory\\{Path(table_src).stem}"
            if arcpy.Exists(mem_src):
                arcpy.management.Delete(mem_src)
            arcpy.management.CopyRows(table_src, mem_src)
            arcpy.AddMessage(f"Staged input to memory -> {mem_src}")
            table_src = mem_src

        tbl_obj = arcsmith.tbl.add_to_map(m, table_src, table_name=table_name)
        arcpy.AddMessage(f"Added standalone table -> {tbl_obj.name}")
        arcpy.AddMessage(
            f"Map now has {len(m.listTables())} standalone table(s): "
            f"{[t.name for t in m.listTables()]}"
        )

    def postExecute(self, parameters):
        return


# ===========================================================================
# 2. remove_from_map
# ===========================================================================
class RemoveTableFromMap:
    def __init__(self):
        self.label = "02 Remove Table From Map"
        self.description = (
            "Test arcsmith.tbl.remove_from_map - remove standalone table(s) from "
            "the active map by display name (all matches) or data source path "
            "(first match). With Silent on, a no-match returns quietly instead "
            "of raising.\n\n"
            "The Table Name dropdown lists only the map's standalone tables "
            "(populated from Map.listTables()). Alternatively, drag a table onto "
            "the Table by Source field to remove it by its data source path "
            "(resolved with arcsmith.param.to_path). Use one or the other."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Table Name (standalone tables in the map)",
            name="table_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p0.filter.type = "ValueList"

        p1 = arcpy.Parameter(
            displayName="Table by Source (pick or drag a table; matched by source)",
            name="table_source",
            datatype="GPTableView",
            parameterType="Optional",
            direction="Input",
        )
        # GPTableView would otherwise list feature layers too; a ValueList of the
        # map's standalone-table names (set in updateParameters) constrains the
        # dropdown to tables while still accepting a dragged table in the list.
        p1.filter.type = "ValueList"

        p2 = arcpy.Parameter(
            displayName="Silent (no raise on no match)",
            name="silent",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p2.value = False

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Filter both table inputs to the map's standalone tables only, so a
        # feature layer (which a GPTableView would otherwise list) can't appear.
        try:
            m = _active_map()
            names = [t.name for t in m.listTables()]
            parameters[0].filter.list = names
            parameters[1].filter.list = names
        except Exception:
            pass
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        table_name = parameters[0].valueAsText or None

        # The source param accepts a picked/dragged table; resolve it to its
        # catalog path so remove_from_map can match it by data source. Under the
        # ValueList filter the value may come through as the table name rather
        # than a table object, so fall back to resolving by name via listTables.
        table_source = None
        if parameters[1].value:
            try:
                table_source = arcsmith.param.to_path(parameters[1])
            except Exception:
                match = next(
                    (t for t in m.listTables() if t.name == parameters[1].valueAsText),
                    None,
                )
                table_source = getattr(match, "dataSource", None) if match else None

        silent = bool(parameters[2].value)

        removed = arcsmith.tbl.remove_from_map(
            m, table_name=table_name, table_source=table_source, silent=silent
        )
        # A removed table object is detached from the map, so its attributes
        # can no longer be read; report the count and the user's criterion.
        target = table_name or table_source or "(none)"
        arcpy.AddMessage(f"Removed {len(removed)} table(s) matching {target!r}.")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 3. get_table
# ===========================================================================
class GetTable:
    def __init__(self):
        self.label = "03 Get Table"
        self.description = (
            "Test arcsmith.tbl.get_table - look up standalone tables in the "
            "active map by display name (all matches) or by data source path "
            "(first match). Exactly one of Name / Source must be provided; a "
            "no-match raises."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Table Name (match all by name)",
            name="table_name",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Table Source Path (match first by source)",
            name="table_source",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        m = _active_map()
        table_name = parameters[0].valueAsText or None
        table_source = parameters[1].valueAsText or None

        matched = arcsmith.tbl.get_table(
            m, table_name=table_name, table_source=table_source
        )
        arcpy.AddMessage(f"Matched {len(matched)} table(s):")
        for tbl in matched:
            try:
                src = tbl.dataSource
            except Exception:
                src = "(no source)"
            arcpy.AddMessage(f"  - {tbl.name}  ({src})")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 4. from_rows
# ===========================================================================
class FromRows:
    def __init__(self):
        self.label = "04 From Rows"
        self.description = (
            "Test arcsmith.tbl.from_rows - materializes in-memory Python rows as "
            "an ArcGIS table. Pick a curated demo dataset to exercise a specific "
            "branch (single-column scalars, multi-column inference, explicit "
            "types, or empty-with-schema). Inspect the resulting table's schema "
            "and rows to confirm the inferred/declared field types. Target a "
            "geodatabase path (or memory/<name>) and use Overwrite to replace it."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Demo Dataset",
            name="demo",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        p0.filter.type = "ValueList"
        p0.filter.list = list(_DEMO_ROWS)
        p0.value = list(_DEMO_ROWS)[1]

        p1 = arcpy.Parameter(
            displayName="Output Table (gdb path or memory/<name>)",
            name="out_table",
            datatype="DETable",
            parameterType="Required",
            direction="Output",
        )

        p2 = arcpy.Parameter(
            displayName="Overwrite if it exists",
            name="overwrite",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p2.value = True

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        demo = parameters[0].valueAsText
        out_table = parameters[1].valueAsText
        overwrite = bool(parameters[2].value)

        rows, fields, note = _DEMO_ROWS[demo]
        arcpy.AddMessage(f"Demo: {demo}")
        arcpy.AddMessage(f"  {note}")
        arcpy.AddMessage(f"  rows={rows!r}")
        arcpy.AddMessage(f"  fields={fields!r}")

        out = arcsmith.tbl.from_rows(out_table, rows, fields, overwrite=overwrite)
        arcpy.AddMessage(f"Created -> {out}")

        # Report the resulting schema so inferred/declared types can be verified.
        arcpy.AddMessage("Output schema:")
        for f in arcpy.ListFields(out):
            length = f"({f.length})" if f.type == "String" else ""
            arcpy.AddMessage(f"  {f.name}: {f.type}{length}")
        count = int(arcpy.management.GetCount(out).getOutput(0))
        arcpy.AddMessage(f"Row count: {count}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 5. join_lookup
# ===========================================================================
class JoinLookup:
    def __init__(self):
        self.label = "05 Join Lookup"
        self.description = (
            "Test arcsmith.tbl.join_lookup - the table-free 1:1 join. This tool "
            "pulls the unique values of the chosen key field, builds a demo "
            "{key: label} mapping for them, adds a new field, and populates it. "
            "Toggle 'Leave some keys unmatched' to map only half the keys and "
            "watch the matched/unmatched counts and the default fall-back.\n\n"
            "WARNING: this edits the input feature class in place (adds a field)."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Input Feature Class (edited in place)",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Key Field",
            name="key_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Output Field Name",
            name="out_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        p2.value = "LOOKUP_LABEL"

        p3 = arcpy.Parameter(
            displayName="Default (value when key not in mapping)",
            name="default",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p3.value = "Unknown"

        p4 = arcpy.Parameter(
            displayName="Leave some keys unmatched (map only half)",
            name="partial",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p4.value = False

        p5 = arcpy.Parameter(
            displayName="Overwrite output field if it exists",
            name="overwrite",
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
        input_fc = arcsmith.param.to_path(parameters[0])
        key_field = parameters[1].valueAsText
        out_field = parameters[2].valueAsText
        default = parameters[3].valueAsText
        partial = bool(parameters[4].value)
        overwrite = bool(parameters[5].value)

        keys = arcsmith.flds.unique_values(input_fc, key_field)
        keys = [k for k in keys if k is not None]
        if partial:
            keys = keys[: max(1, len(keys) // 2)]  # map only the first half
        mapping = {k: f"label_for_{k}" for k in keys}
        arcpy.AddMessage(f"Built mapping for {len(mapping)} key(s): {mapping}")

        counts = arcsmith.tbl.join_lookup(
            input_fc, key_field, mapping, out_field, "TEXT",
            default=default, overwrite=overwrite,
        )
        arcpy.AddMessage(
            f"join_lookup -> matched={counts['matched']}, "
            f"unmatched={counts['unmatched']}"
        )

    def postExecute(self, parameters):
        return


# ===========================================================================
# 6. join_table
# ===========================================================================
class JoinTable:
    def __init__(self):
        self.label = "06 Join Table"
        self.description = (
            "Test arcsmith.tbl.join_table - permanently joins columns from a "
            "source table/feature class into the input via JoinField. Choose the "
            "join keys, then optionally name source fields to keep or drop. "
            "Leave Fields empty to transfer all transferable columns.\n\n"
            "WARNING: this edits the input feature class in place (adds columns)."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Input Feature Class (edited in place)",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Input Join Field",
            name="in_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Source Table / Feature Class",
            name="source_table",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input",
        )

        p3 = arcpy.Parameter(
            displayName="Source Join Field",
            name="join_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p3.parameterDependencies = ["source_table"]

        p4 = arcpy.Parameter(
            displayName="Source Fields to Keep / Drop (empty = all)",
            name="fields",
            datatype="Field",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
        )
        p4.parameterDependencies = ["source_table"]

        p5 = arcpy.Parameter(
            displayName="Field Mode",
            name="keep",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p5.filter.type = "ValueList"
        p5.filter.list = ["Keep listed fields", "Drop listed fields"]
        p5.value = "Keep listed fields"

        return [p0, p1, p2, p3, p4, p5]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        in_field = parameters[1].valueAsText
        source_table = arcsmith.param.to_path(parameters[2])
        join_field = parameters[3].valueAsText
        fields = [str(f) for f in parameters[4].values] if parameters[4].values else None
        keep = parameters[5].valueAsText != "Drop listed fields"

        before = set(arcsmith.flds.list_cols(input_fc))
        out = arcsmith.tbl.join_table(
            input_fc, in_field, source_table, join_field, fields=fields, keep=keep
        )
        after = arcsmith.flds.list_cols(out)
        added = [f for f in after if f not in before]
        arcpy.AddMessage(f"join_table -> {out}")
        arcpy.AddMessage(f"Columns added: {added}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 7. add_rows
# ===========================================================================
class AddRows:
    def __init__(self):
        self.label = "07 Add Rows"
        self.description = (
            "Test arcsmith.tbl.add_rows - append rows of Python data to an "
            "existing table or feature class via an InsertCursor (the append "
            "complement to from_rows). Pick the target and the fields to write, "
            "in order, then enter one or more rows. Each row is a set of values "
            "separated by '|', in the same order as the selected fields. A value "
            "is coerced to int or float when it looks numeric, and an empty value "
            "is written as NULL. Reports the row count add_rows returns."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Target Table or Feature Class (appended in place)",
            name="target",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Fields to Write (in order)",
            name="fields",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        p1.parameterDependencies = ["target"]

        p2 = arcpy.Parameter(
            displayName="Rows (each entry = one row; values separated by '|')",
            name="rows",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        target = arcsmith.param.to_path(parameters[0])
        fields = [str(f) for f in parameters[1].values]

        def _coerce(text):
            text = text.strip()
            if text == "":
                return None
            for cast in (int, float):
                try:
                    return cast(text)
                except ValueError:
                    pass
            return text

        rows = [[_coerce(v) for v in str(entry).split("|")]
                for entry in parameters[2].values]

        before = int(arcpy.management.GetCount(target).getOutput(0))
        n = arcsmith.tbl.add_rows(target, rows, fields)
        after = int(arcpy.management.GetCount(target).getOutput(0))

        arcpy.AddMessage(f"add_rows wrote {n} row(s) to {target}")
        arcpy.AddMessage(f"Row count: {before} -> {after}")

    def postExecute(self, parameters):
        return
