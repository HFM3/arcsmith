# -*- coding: utf-8 -*-
"""
test_flds.pyt
ArcGIS Pro test toolbox for the arcpy-driven functions in arcsmith.flds.

The pytest suite (tests/test_flds.py) covers only the pure field-set helpers
``_is_system`` and ``_resolve_keep``. The public functions all call into arcpy
(ListFields, FieldMappings, SearchCursor, UpdateCursor, CopyFeatures) and need a
live machine. This toolbox drives them against real data:

    - list_cols        (ListFields, system-field filtering, include_oid)
    - unique_values    (SearchCursor scan, single vs multi-field, sort, max_rows)
    - build_fld_map    (FieldMappings keep/drop, system-field exemption)
    - clean_blanks     (UpdateCursor blank standardization, string-only guard)
    - add_fld          (AddField with type, length, alias)
    - rename_fld       (AlterField name and optional alias)
    - del_fld          (DeleteField, system-field guard)
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
        self.label = "Test arcsmith.flds"
        self.alias = "test_arcsmith_flds"
        self.tools = [
            ListCols,
            UniqueValues,
            BuildFieldMap,
            CleanBlanks,
            AddField,
            RenameField,
            DeleteField,
        ]


# ===========================================================================
# 1. list_cols
# ===========================================================================
class ListCols:
    def __init__(self):
        self.label = "01 List Columns"
        self.description = (
            "Test arcsmith.flds.list_cols - lists field names. Toggle 'Include "
            "system fields' to see OBJECTID / Shape / Shape_Length / Shape_Area "
            "/ GlobalID appear or disappear. Toggle 'Include OID only' to add the "
            "Object ID alongside the user fields while the other system fields "
            "stay hidden (matched by field type, so OBJECTID / FID / OID all work)."
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
            displayName="Include System Fields",
            name="include_system",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p1.value = False

        p2 = arcpy.Parameter(
            displayName="Include OID only (keep Object ID, hide other system fields)",
            name="include_oid",
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
        input_fc = arcsmith.param.to_path(parameters[0])
        include_system = bool(parameters[1].value)
        include_oid = bool(parameters[2].value)

        cols = arcsmith.flds.list_cols(
            input_fc, include_system=include_system, include_oid=include_oid
        )
        arcpy.AddMessage(
            f"{len(cols)} field(s) "
            f"(include_system={include_system}, include_oid={include_oid}):"
        )
        for c in cols:
            arcpy.AddMessage(f"  - {c}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 2. unique_values
# ===========================================================================
class UniqueValues:
    def __init__(self):
        self.label = "02 Unique Values"
        self.description = (
            "Test arcsmith.flds.unique_values - returns distinct values for one "
            "field, or distinct tuples across several. Toggle Sort to compare "
            "sorted vs insertion order (None sorts first). Set Max Rows to cap "
            "the scan (result may then be incomplete)."
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
            displayName="Field(s) (one = flat list, two+ = tuples)",
            name="fields",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Sort",
            name="sort",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p2.value = True

        p3 = arcpy.Parameter(
            displayName="Max Rows (optional scan cap)",
            name="max_rows",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        fields = [str(f) for f in parameters[1].values]
        sort = bool(parameters[2].value)
        max_rows = parameters[3].value  # None when unset

        # A single-element list of fields still returns a flat list; pass the
        # bare string in that case to match typical call-site usage.
        arg = fields[0] if len(fields) == 1 else fields
        result = arcsmith.flds.unique_values(input_fc, arg, sort=sort, max_rows=max_rows)

        arcpy.AddMessage(f"{len(result)} unique value(s) for {fields} "
                         f"(sort={sort}, max_rows={max_rows}):")
        for v in result:
            arcpy.AddMessage(f"  {v!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 3. build_fld_map
# ===========================================================================
class BuildFieldMap:
    def __init__(self):
        self.label = "03 Build Field Map"
        self.description = (
            "Test arcsmith.flds.build_fld_map - builds a FieldMappings object "
            "retaining a chosen subset of fields. This tool reports which "
            "output fields the mapping carries so you can confirm keep/drop "
            "behavior and that system fields are always preserved. Leave Fields "
            "empty to map all fields; choose 'Keep listed fields' with an empty "
            "list to retain geometry only."
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
            displayName="Geometry-only (force empty keep list)",
            name="geom_only",
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
        input_fc = arcsmith.param.to_path(parameters[0])
        keep = parameters[2].valueAsText != "Drop listed fields"
        geom_only = bool(parameters[3].value)

        if geom_only:
            fields = []  # keep nothing -> geometry only
        elif parameters[1].values:
            fields = [str(f) for f in parameters[1].values]
        else:
            fields = None  # all fields

        fm = arcsmith.flds.build_fld_map(input_fc, fields, keep=keep)

        mapped = [fm.getFieldMap(i).outputField.name for i in range(fm.fieldCount)]
        arcpy.AddMessage(f"fields={fields}, keep={keep}")
        arcpy.AddMessage(f"FieldMappings carries {len(mapped)} output field(s):")
        for name in mapped:
            arcpy.AddMessage(f"  - {name}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 4. clean_blanks
# ===========================================================================
class CleanBlanks:
    def __init__(self):
        self.label = "04 Clean Blanks"
        self.description = (
            "Test arcsmith.flds.clean_blanks - standardizes blank-like cells "
            "(NULL, empty, whitespace, 'N/A', 'NA', 'None', 'Null', 'Nil', "
            "'-', '--', '---') to a canonical value in string fields. "
            "Non-string fields are skipped with a warning. Provide an Output "
            "Feature Class to clean a copy and leave the source untouched; "
            "leave it empty to edit in place.\n\n"
            "The returned dict reports how many cells were replaced per field."
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
            displayName="Field(s) to Clean",
            name="fields",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Blank Replacement Value",
            name="blank_value",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.value = "N/A"

        p3 = arcpy.Parameter(
            displayName="Output Feature Class (empty = edit in place)",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Output",
        )

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        fields = [str(f) for f in parameters[1].values]
        blank_value = parameters[2].valueAsText or "N/A"
        output_fc = parameters[3].valueAsText or None

        counts = arcsmith.flds.clean_blanks(
            input_fc, fields, output_fc=output_fc, blank_value=blank_value
        )

        target = output_fc or input_fc
        arcpy.AddMessage(f"Cleaned -> {target}")
        if counts:
            for field, n in counts.items():
                arcpy.AddMessage(f"  {field}: {n} blank(s) replaced with {blank_value!r}")
        else:
            arcpy.AddMessage("  No string fields cleaned (all selected fields skipped).")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 5. add_fld
# ===========================================================================
class AddField:
    def __init__(self):
        self.label = "05 Add Field"
        self.description = (
            "Test arcsmith.flds.add_fld - add a new field to a feature class or "
            "table in place. Pick the arcpy field type; Length applies to TEXT "
            "only and Alias is optional. Re-running with a name that already "
            "exists raises, since add_fld never silently overwrites."
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
            displayName="New Field Name",
            name="field",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Field Type",
            name="field_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        p2.filter.type = "ValueList"
        p2.filter.list = ["TEXT", "SHORT", "LONG", "FLOAT", "DOUBLE", "DATE"]
        p2.value = "TEXT"

        p3 = arcpy.Parameter(
            displayName="Length (TEXT only)",
            name="length",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )

        p4 = arcpy.Parameter(
            displayName="Alias (optional)",
            name="alias",
            datatype="GPString",
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
        input_fc = arcsmith.param.to_path(parameters[0])
        field = parameters[1].valueAsText
        field_type = parameters[2].valueAsText
        length = parameters[3].value  # None when unset
        alias = parameters[4].valueAsText or None

        arcsmith.flds.add_fld(input_fc, field, field_type, length=length, alias=alias)
        arcpy.AddMessage(f"Added field {field!r} ({field_type}) to {input_fc}")
        arcpy.AddMessage("Fields now:")
        for c in arcsmith.flds.list_cols(input_fc, include_oid=True):
            arcpy.AddMessage(f"  - {c}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 6. rename_fld
# ===========================================================================
class RenameField:
    def __init__(self):
        self.label = "06 Rename Field"
        self.description = (
            "Test arcsmith.flds.rename_fld - rename a field (and optionally its "
            "alias) in place via AlterField. The existing field is matched "
            "case-insensitively. Some formats such as shapefiles, and required "
            "or system fields, cannot be renamed; arcpy raises in those cases."
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
            displayName="Existing Field",
            name="field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="New Name",
            name="new_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        p3 = arcpy.Parameter(
            displayName="New Alias (optional)",
            name="new_alias",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        field = parameters[1].valueAsText
        new_name = parameters[2].valueAsText
        new_alias = parameters[3].valueAsText or None

        arcsmith.flds.rename_fld(input_fc, field, new_name, new_alias=new_alias)
        arcpy.AddMessage(f"Renamed {field!r} -> {new_name!r}")
        arcpy.AddMessage("Fields now:")
        for c in arcsmith.flds.list_cols(input_fc, include_oid=True):
            arcpy.AddMessage(f"  - {c}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 7. del_fld
# ===========================================================================
class DeleteField:
    def __init__(self):
        self.label = "07 Delete Field"
        self.description = (
            "Test arcsmith.flds.del_fld - delete one or more fields in place via "
            "DeleteField. Names are matched case-insensitively. System fields "
            "(OID, Shape, Shape_Length, Shape_Area, GlobalID) are refused with a "
            "clear error rather than handed to arcpy."
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
            displayName="Field(s) to Delete",
            name="fields",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        p1.parameterDependencies = ["input_fc"]

        return [p0, p1]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        input_fc = arcsmith.param.to_path(parameters[0])
        fields = [str(f) for f in parameters[1].values]

        arcsmith.flds.del_fld(input_fc, fields)
        arcpy.AddMessage(f"Deleted {fields} from {input_fc}")
        arcpy.AddMessage("Fields now:")
        for c in arcsmith.flds.list_cols(input_fc, include_oid=True):
            arcpy.AddMessage(f"  - {c}")

    def postExecute(self, parameters):
        return
