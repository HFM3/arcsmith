# -*- coding: utf-8 -*-
"""
test_fc.pyt
ArcGIS Pro test toolbox for the arcpy-driven functions in arcsmith.fc.

The pytest suite (tests/test_fc.py) can only exercise the pure SQL helper
``_sql_quote`` -- everything else in fc.py calls into arcpy (cursors, Describe,
ListFields, AddFieldDelimiters, geoprocessing) and cannot run off an ArcGIS Pro
machine. This toolbox drives those functions interactively so they can be
verified against real data:

    - get_area            (SHAPE@AREA cursor + unit conversion)
    - validate_geom_type  (Describe.shapeType)
    - build_where         (field delimiting + type-aware value quoting)
    - build_where_in      (IN / NOT IN clause building)
    - export_fc           (ExportFeatures + field map)

Open it in ArcGIS Pro, point each tool at a real feature class, and confirm the
messages match what you expect.
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


# ===========================================================================
class Toolbox:
    def __init__(self):
        self.label = "Test arcsmith.fc"
        self.alias = "test_arcsmith_fc"
        self.tools = [
            GetArea,
            ValidateGeomType,
            BuildWhere,
            BuildWhereIn,
            ExportFc,
        ]


# ===========================================================================
# 1. get_area
# ===========================================================================
class GetArea:
    def __init__(self):
        self.label = "01 Get Area"
        self.description = (
            "Test arcsmith.fc.get_area - sums SHAPE@AREA across a polygon "
            "feature class and optionally converts to a chosen unit. Try a "
            "projected layer (native units) and a geographic layer with a unit "
            "selected to confirm the GCS conversion error is raised."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Input Polygon Feature Class",
            name="polygon_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )
        p0.filter.list = ["Polygon"]

        p1 = arcpy.Parameter(
            displayName="Output Units (optional)",
            name="output_units",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p1.filter.type = "ValueList"
        p1.filter.list = [
            "Meter", "Kilometer", "Foot_US", "Foot",
            "Mile_US", "Nautical_Mile", "Yard",
        ]

        return [p0, p1]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        polygon_fc = arcsmith.param.to_path(parameters[0])
        output_units = parameters[1].valueAsText or None

        area, units = arcsmith.fc.get_area(polygon_fc, output_units=output_units)
        arcpy.AddMessage(f"Result  -> area={area:.4f}, units={units}^2")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 2. validate_geom_type
# ===========================================================================
class ValidateGeomType:
    def __init__(self):
        self.label = "02 Validate Geometry Type"
        self.description = (
            "Test arcsmith.fc.validate_geom_type - checks whether a feature "
            "class matches one of the expected geometry type(s). Matching is "
            "case-insensitive; pass several types to accept any of them."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Expected Geometry Type(s)",
            name="expected_shape",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        p1.filter.type = "ValueList"
        p1.filter.list = ["Point", "Polyline", "Polygon", "Multipoint"]

        return [p0, p1]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        expected_shape = parameters[1].values  # list when multiValue=True

        result = arcsmith.fc.validate_geom_type(input_fc, expected_shape)
        actual = arcpy.Describe(input_fc).shapeType

        if result:
            arcpy.AddMessage(
                f"PASS - actual geometry '{actual}' matches expected {expected_shape}."
            )
        else:
            arcpy.AddWarning(
                f"FAIL - actual geometry '{actual}' does NOT match expected {expected_shape}."
            )

    def postExecute(self, parameters):
        return


# ===========================================================================
# 3. build_where
# ===========================================================================
class BuildWhere:
    def __init__(self):
        self.label = "03 Build Where Clause"
        self.description = (
            "Test arcsmith.fc.build_where - builds a single-field SQL WHERE "
            "clause with correct field delimiting and type-aware value quoting. "
            "The Value dropdown is auto-populated from the field's unique "
            "values. Leave Value empty to generate an IS NULL / IS NOT NULL "
            "clause (use the '<>' operator for IS NOT NULL)."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Field Name",
            name="field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Value (leave empty for IS NULL / IS NOT NULL)",
            name="value",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p3 = arcpy.Parameter(
            displayName="Operator",
            name="operator",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p3.filter.type = "ValueList"
        p3.filter.list = ["=", "<>", ">", ">=", "<", "<="]
        p3.value = "="

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        input_fc_param, field, value, _operator = parameters

        # Clear and repopulate the value dropdown when the field changes.
        if arcsmith.param.state(field) == "pending":
            arcsmith.param.cascade_clear(field, value)
            if input_fc_param.value and field.valueAsText:
                fc_path = arcsmith.param.to_path(input_fc_param)
                try:
                    unique = arcsmith.flds.unique_values(fc_path, field.valueAsText)
                    arcsmith.param.drop_populate(value, unique, overwrite_empty=True)
                except Exception:
                    pass
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        field = parameters[1].valueAsText
        value = parameters[2].valueAsText  # None when left empty -> IS NULL path
        operator = parameters[3].valueAsText or "="

        clause = arcsmith.fc.build_where(input_fc, field, value, operator=operator)
        arcpy.AddMessage(f"WHERE clause -> {clause}")

        # Confirm the clause is actually valid against the data by counting it.
        try:
            with arcpy.da.SearchCursor(input_fc, "OID@", where_clause=clause) as cur:
                n = sum(1 for _ in cur)
            arcpy.AddMessage(f"Matched {n} row(s).")
        except Exception as exc:
            arcpy.AddWarning(f"Clause did not execute against the data: {exc}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 4. build_where_in
# ===========================================================================
class BuildWhereIn:
    def __init__(self):
        self.label = "04 Build Where IN Clause"
        self.description = (
            "Test arcsmith.fc.build_where_in - builds a multi-value IN (or "
            "NOT IN) clause from a list of selected values, quoting them "
            "according to the field type. The Values list is auto-populated "
            "from the field's unique values."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Field Name",
            name="field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Values",
            name="values",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        p2.filter.type = "ValueList"

        p3 = arcpy.Parameter(
            displayName="Exclude (NOT IN instead of IN)",
            name="exclude",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p3.value = False

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        input_fc_param, field, values, _exclude = parameters

        if arcsmith.param.state(field) == "pending":
            arcsmith.param.cascade_clear(field, values)
            if input_fc_param.value and field.valueAsText:
                fc_path = arcsmith.param.to_path(input_fc_param)
                try:
                    unique = arcsmith.flds.unique_values(fc_path, field.valueAsText)
                    arcsmith.param.drop_populate(values, unique, overwrite_empty=True)
                except Exception:
                    pass
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        field = parameters[1].valueAsText
        values = [str(v) for v in parameters[2].values] if parameters[2].values else []
        exclude = bool(parameters[3].value)

        clause = arcsmith.fc.build_where_in(input_fc, field, values, exclude=exclude)
        arcpy.AddMessage(f"WHERE clause -> {clause}")

        try:
            with arcpy.da.SearchCursor(input_fc, "OID@", where_clause=clause) as cur:
                n = sum(1 for _ in cur)
            arcpy.AddMessage(f"Matched {n} row(s).")
        except Exception as exc:
            arcpy.AddWarning(f"Clause did not execute against the data: {exc}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 5. export_fc
# ===========================================================================
class ExportFc:
    def __init__(self):
        self.label = "05 Export Feature Class"
        self.description = (
            "Test arcsmith.fc.export_fc - exports a feature class while "
            "filtering fields (keep or drop) and optionally filtering rows "
            "with a WHERE clause. Confirms the output count and the fields "
            "retained. Leave Fields empty to export all fields; choose 'Keep "
            "listed fields' with an empty list to export geometry only."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Fields to Keep / Drop (empty = all fields)",
            name="fields",
            datatype="Field",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Field Mode",
            name="keep",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.filter.type = "ValueList"
        p2.filter.list = ["Keep listed fields", "Drop listed fields"]
        p2.value = "Keep listed fields"

        p3 = arcpy.Parameter(
            displayName="WHERE Clause (optional row filter)",
            name="where_clause",
            datatype="GPSQLExpression",
            parameterType="Optional",
            direction="Input",
        )
        p3.parameterDependencies = ["input_fc"]

        p4 = arcpy.Parameter(
            displayName="Output Feature Class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        return [p0, p1, p2, p3, p4]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        # None (all fields) vs an explicit (possibly empty) list. An empty
        # multiValue reads as None, so only treat it as a list when the user
        # actually picked fields.
        fields = [str(f) for f in parameters[1].values] if parameters[1].values else None
        keep = parameters[2].valueAsText != "Drop listed fields"
        where_clause = parameters[3].valueAsText or None
        output_fc = parameters[4].valueAsText

        out = arcsmith.fc.export_fc(
            input_fc, output_fc,
            fields=fields,
            keep=keep,
            where_clause=where_clause,
        )

        count = int(arcpy.management.GetCount(out).getOutput(0))
        out_fields = arcsmith.flds.list_cols(out)
        arcpy.AddMessage(f"Output -> {out}  ({count} feature(s))")
        arcpy.AddMessage(f"Fields retained: {out_fields}")

    def postExecute(self, parameters):
        return