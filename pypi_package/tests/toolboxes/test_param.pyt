# -*- coding: utf-8 -*-
"""
test_param.pyt
ArcGIS Pro test toolbox for arcsmith.param.

The pytest suite (tests/test_param.py) exercises the pure attribute-only logic
with a FakeParam: ``state``, ``_broadcast``, the cascade functions, and the
history-recall *seeding decision* inside ``checkbox_dependence`` /
``dynamic_dropdown``. What it cannot reproduce is the live ArcGIS Pro dialog:
real validation passes, the ``enabled``/grey-out behaviour, dropdown filter
population, history re-runs, and ``to_path`` resolving a map layer to its
catalog path. This toolbox drives all of that interactively:

    - state             (watch fresh / pending / settled / confirmed live)
    - cascade_populate  (upstream change seeds downstream)
    - cascade_clear     (upstream change clears downstream)
    - drop_populate     (dropdown filled from a field's unique values)
    - checkbox_dependence (enable + seed; history-recall preservation)
    - dynamic_dropdown  (show/hide groups; history-recall preservation)
    - to_path           (layer name vs resolved catalog path)
    - require           (conditional 'fill this' message that self-clears)
    - require_one_of    (at least one of a group must be filled)
    - flag              (self-clearing message while a condition holds)
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
        self.label = "Test arcsmith.param"
        self.alias = "test_arcsmith_param"
        self.tools = [
            StateInspector,
            CascadePopulate,
            CascadeClear,
            DropPopulate,
            CheckboxDependence,
            DynamicDropdown,
            ToPath,
            Require,
            RequireOneOf,
            Flag,
        ]


# ===========================================================================
# 1. state  - observe the four states as you interact with parameters
# ===========================================================================
class StateInspector:
    def __init__(self):
        self.label = "01 State Inspector"
        self.description = (
            "Test arcsmith.param.state - displays the current state of two "
            "parameters (fresh / pending / settled / confirmed) in the "
            "parameter messages as you interact with them."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Parameter A (change me to see state transitions)",
            name="param_a",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Parameter B (change me independently)",
            name="param_b",
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
        for p in parameters:
            s = arcsmith.param.state(p)
            p.setWarningMessage(f"state = '{s}'")

    def execute(self, parameters, messages):
        for p in parameters:
            arcpy.AddMessage(
                f"  '{p.displayName}' -> state='{arcsmith.param.state(p)}'"
            )

    def postExecute(self, parameters):
        return


# ===========================================================================
# 2. cascade_populate  - upstream change seeds downstream value
# ===========================================================================
class CascadePopulate:
    def __init__(self):
        self.label = "02 Cascade Populate"
        self.description = (
            "Test arcsmith.param.cascade_populate - changing the upstream "
            "parameter copies its value into both downstream parameters. "
            "Downstream values survive further edits (no double-clear)."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Upstream Trigger",
            name="upstream",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Downstream A (seeded from upstream)",
            name="downstream_a",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Downstream B (seeded from upstream)",
            name="downstream_b",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        upstream, downstream_a, downstream_b = parameters
        # Seed both downstream params with the upstream value when it changes
        arcsmith.param.cascade_populate(
            upstream, [downstream_a, downstream_b],
            value=upstream.valueAsText,
        )

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        arcpy.AddMessage(f"upstream      = {parameters[0].valueAsText!r}")
        arcpy.AddMessage(f"downstream_a  = {parameters[1].valueAsText!r}")
        arcpy.AddMessage(f"downstream_b  = {parameters[2].valueAsText!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 3. cascade_clear  - upstream change clears downstream params
# ===========================================================================
class CascadeClear:
    def __init__(self):
        self.label = "03 Cascade Clear"
        self.description = (
            "Test arcsmith.param.cascade_clear - changing the upstream "
            "parameter clears (sets to None) all downstream parameters."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Upstream Trigger (change me to clear downstream)",
            name="upstream",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Downstream A (will be cleared on upstream change)",
            name="downstream_a",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p1.value = "I will be cleared"

        p2 = arcpy.Parameter(
            displayName="Downstream B (will be cleared on upstream change)",
            name="downstream_b",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.value = "Me too"

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        upstream, downstream_a, downstream_b = parameters
        arcsmith.param.cascade_clear(upstream, [downstream_a, downstream_b])

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        arcpy.AddMessage(f"upstream      = {parameters[0].valueAsText!r}")
        arcpy.AddMessage(f"downstream_a  = {parameters[1].valueAsText!r}")
        arcpy.AddMessage(f"downstream_b  = {parameters[2].valueAsText!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 4. drop_populate  - dropdown populated from a feature class field
# ===========================================================================
class DropPopulate:
    def __init__(self):
        self.label = "04 Drop Populate"
        self.description = (
            "Test arcsmith.param.drop_populate - pick a feature class and a "
            "field; the third dropdown is automatically populated with the "
            "field's unique values via unique_values + drop_populate."
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
            displayName="Field to Inspect",
            name="field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p1.parameterDependencies = ["input_fc"]

        p2 = arcpy.Parameter(
            displayName="Unique Values (auto-populated)",
            name="chosen_value",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )
        p2.filter.type = "ValueList"

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        input_fc_param, field_param, value_param = parameters

        # Clear value_param when upstream changes
        arcsmith.param.cascade_clear(input_fc_param, [field_param, value_param])
        arcsmith.param.cascade_clear(field_param, [value_param])

        # Populate dropdown once both upstream params are set
        if input_fc_param.value and field_param.value:
            fc_path = arcsmith.param.to_path(input_fc_param)
            field = field_param.valueAsText
            try:
                vals = arcsmith.flds.unique_values(fc_path, field)
                arcsmith.param.drop_populate(value_param, [str(v) for v in vals])
            except Exception:
                pass

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        fc_path = arcsmith.param.to_path(parameters[0])
        field = parameters[1].valueAsText
        chosen = parameters[2].valueAsText

        arcpy.AddMessage(f"Feature class : {fc_path}")
        arcpy.AddMessage(f"Field         : {field}")
        arcpy.AddMessage(f"Chosen value  : {chosen!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 5. checkbox_dependence
# ===========================================================================
class CheckboxDependence:
    def __init__(self):
        self.label = "05 Checkbox Dependence"
        self.description = (
            "Test arcsmith.param.checkbox_dependence. A checkbox enables two "
            "dependent parameters and seeds each with a starting value the "
            "first time it is checked.\n\n"
            "History-recall test: check the box so Input A and Input B get "
            "seeded. Clear Input B, then Run the tool. Re-open this tool from "
            "its run history. Input B stays cleared instead of being re-seeded, "
            "and Input A keeps its value. The parameter messages show each "
            "parameter's live state so you can watch every parameter reload as "
            "'pending' on the history pass."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Enable Optional Inputs",
            name="checkbox",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p0.value = False

        p1 = arcpy.Parameter(
            displayName="Optional Input A (controlled by checkbox)",
            name="optional_a",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Optional Input B (controlled by checkbox)",
            name="optional_b",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        checkbox, optional_a, optional_b = parameters
        # shown_value seeds a starting value on a genuine check. On a history
        # re-run the seeding is skipped automatically, so a value the user
        # cleared before running comes back cleared.
        arcsmith.param.checkbox_dependence(
            checkbox,
            [optional_a, optional_b],
            shown_value=["Seeded A", "Seeded B"],
        )

    def updateMessages(self, parameters):
        # Surface each parameter's live state. On a history re-run every
        # parameter reloads as 'pending' on the first pass.
        for p in parameters:
            p.setWarningMessage(f"state = '{arcsmith.param.state(p)}'")

    def execute(self, parameters, messages):
        arcpy.AddMessage(f"checkbox   = {parameters[0].value}")
        arcpy.AddMessage(f"optional_a = {parameters[1].valueAsText!r}")
        arcpy.AddMessage(f"optional_b = {parameters[2].valueAsText!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 6. dynamic_dropdown
# ===========================================================================
class DynamicDropdown:
    def __init__(self):
        self.label = "06 Dynamic Dropdown"
        self.description = (
            "Test arcsmith.param.dynamic_dropdown - a controlling dropdown "
            "shows/hides two groups of parameters (Group A: p1; "
            "Group B: p2 + p3). The active group is seeded with starting "
            "values when its option is selected.\n\n"
            "History-recall test: with Option A selected, Group A's input is "
            "seeded. Clear it, then Run the tool. Re-open this tool from its "
            "run history. The cleared value stays cleared instead of being "
            "re-seeded."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Mode",
            name="mode",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        p0.filter.type = "ValueList"
        p0.filter.list = ["Option A", "Option B"]
        p0.value = "Option A"

        p1 = arcpy.Parameter(
            displayName="Group A - Input (only visible for Option A)",
            name="group_a_input",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Group B - Input 1 (only visible for Option B)",
            name="group_b_input1",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p3 = arcpy.Parameter(
            displayName="Group B - Input 2 (only visible for Option B)",
            name="group_b_input2",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2, p3]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        mode, group_a_input, group_b_input1, group_b_input2 = parameters

        # shown_value_map seeds the active group on a genuine option change.
        # On a history re-run the seeding is skipped automatically, so a
        # cleared value comes back cleared.
        arcsmith.param.dynamic_dropdown(
            mode,
            option_map={
                "Option A": [group_a_input],
                "Option B": [group_b_input1, group_b_input2],
            },
            hidden_value_map={
                "Option A": [None],
                "Option B": [None, None],
            },
            shown_value_map={
                "Option A": ["Seeded A"],
                "Option B": ["Seeded B1", "Seeded B2"],
            },
        )

    def updateMessages(self, parameters):
        # Surface each parameter's live state. On a history re-run every
        # parameter reloads as 'pending' on the first pass.
        for p in parameters:
            p.setWarningMessage(f"state = '{arcsmith.param.state(p)}'")

    def execute(self, parameters, messages):
        arcpy.AddMessage(f"mode            = {parameters[0].valueAsText!r}")
        arcpy.AddMessage(f"group_a_input   = {parameters[1].valueAsText!r}")
        arcpy.AddMessage(f"group_b_input1  = {parameters[2].valueAsText!r}")
        arcpy.AddMessage(f"group_b_input2  = {parameters[3].valueAsText!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 7. to_path
# ===========================================================================
class ToPath:
    def __init__(self):
        self.label = "07 To Path"
        self.description = (
            "Test arcsmith.param.to_path - resolves a feature class or layer "
            "parameter to its absolute catalog path and displays it alongside "
            "the raw valueAsText for comparison. Pick a map layer (by TOC name) "
            "to see the two differ; pick a direct path to see them match."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Feature Class or Layer",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        return [p0]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        raw_text = parameters[0].valueAsText
        catalog_path = arcsmith.param.to_path(parameters[0])

        arcpy.AddMessage(f"valueAsText  -> {raw_text!r}")
        arcpy.AddMessage(f"to_path()    -> {catalog_path!r}")

        if raw_text == catalog_path:
            arcpy.AddMessage("(values are identical - input was a direct path, not a map layer)")
        else:
            arcpy.AddMessage("(paths differ - to_path() resolved the map layer to its source)")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 8. require
# ===========================================================================
class Require:
    def __init__(self):
        self.label = "08 Require"
        self.description = (
            "Test arcsmith.param.require - a conditional 'fill this before "
            "running' prompt that self-clears. Check 'Require the input' and "
            "leave the input empty to see a blocking message; fill it or uncheck "
            "to watch the message clear. Toggle 'Non-blocking' to show it as a "
            "yellow warning (block=False) instead of a red error. The input is "
            "Optional, so ArcGIS does not flag it on its own."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Require the input below",
            name="needed",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p0.value = True

        p1 = arcpy.Parameter(
            displayName="Conditionally Required Input",
            name="value",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Non-blocking (warning instead of error)",
            name="non_blocking",
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
        needed, value, non_blocking = parameters
        arcsmith.param.require(
            value, when=bool(needed.value), block=not bool(non_blocking.value)
        )

    def execute(self, parameters, messages):
        arcpy.AddMessage(f"needed = {parameters[0].value}")
        arcpy.AddMessage(f"value  = {parameters[1].valueAsText!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 9. require_one_of
# ===========================================================================
class RequireOneOf:
    def __init__(self):
        self.label = "09 Require One Of"
        self.description = (
            "Test arcsmith.param.require_one_of - at least one of a group must be "
            "filled. With both inputs empty, both show the prompt; fill either "
            "one and both clear. Uncheck 'Require one of A/B' to drop the "
            "requirement entirely."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Require one of A / B",
            name="needed",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p0.value = True

        p1 = arcpy.Parameter(
            displayName="Input A",
            name="input_a",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p2 = arcpy.Parameter(
            displayName="Input B",
            name="input_b",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        return [p0, p1, p2]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        needed, input_a, input_b = parameters
        arcsmith.param.require_one_of([input_a, input_b], when=bool(needed.value))

    def execute(self, parameters, messages):
        arcpy.AddMessage(f"input_a = {parameters[1].valueAsText!r}")
        arcpy.AddMessage(f"input_b = {parameters[2].valueAsText!r}")

    def postExecute(self, parameters):
        return


# ===========================================================================
# 10. flag
# ===========================================================================
class Flag:
    def __init__(self):
        self.label = "10 Flag"
        self.description = (
            "Test arcsmith.param.flag - a general self-clearing message shown "
            "while a condition holds. Enter a number; values over 100 are "
            "flagged, and the message clears as soon as the value is 100 or less "
            "(or empty). flag is the building block for value-semantic checks and "
            "composes with helpers like fc.validate_geom_type. Toggle 'Blocking' "
            "to switch between a red error and a yellow warning."
        )

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Number (over 100 is flagged)",
            name="number",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )

        p1 = arcpy.Parameter(
            displayName="Blocking (error instead of warning)",
            name="blocking",
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
        number, blocking = parameters
        too_big = number.value is not None and number.value > 100
        arcsmith.param.flag(
            number,
            when=too_big,
            message="Over 100 - double-check this value.",
            block=bool(blocking.value),
        )

    def execute(self, parameters, messages):
        arcpy.AddMessage(f"number = {parameters[0].value}")

    def postExecute(self, parameters):
        return
