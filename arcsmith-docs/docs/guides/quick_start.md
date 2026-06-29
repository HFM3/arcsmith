<div class="as-hero" markdown>
<div class="as-hero__eyebrow">Getting started</div>
<h2 class="as-hero__title">With ArcSmith</h2>
<p class="as-hero__sub">Install <code>arcsmith</code>, understand where it fits in a Python toolbox, and build an interactive tool end to end in a few minutes.</p>
<ul class="as-hero__highlights">
<li>See how ArcSmith and its modules can help</li>
<li>Learn where each module plugs into the <code>.pyt</code> toolbox lifecycle</li>
<li>Build a complete, runnable filter tool with four parameters</li>
</ul>
</div>

## What is ArcSmith?

A tool builder's toolbox. ArcSmith is a library for building **ArcGIS Pro Python toolboxes** (`.pyt` files). It does not replace `arcpy`. It works on top of it and handles common toolboxes development tasks such as: reading parameter state, building quoted SQL `WHERE` clauses, applying symbology, populating value lists, and creating output geodatabases.

The next example shows the difference on one common task.

The result is that the *intent* of the validation and geoprocessing logic stays visible instead of being buried under arcpy plumbing.

!!! note "The problem in one example"
    Populating a dropdown with the unique values of a field, and clearing it whenever the user picks a different field, is a common routine of any dropdown menu. In vanilla arcpy it looks like this:

```python
    if state_field.altered and not state_field.hasBeenValidated:
        seen, values = set(), []
        with arcpy.da.SearchCursor(fc_path, [state_field.valueAsText]) as cur:
            for row in cur:
                if row[0] not in seen:
                    seen.add(row[0])
                    values.append(str(row[0]))
        values.sort()
        target.filter.type = "ValueList"
        target.filter.list = values
        target.value = None
```

With ArcSmith, the same behavior is two readable lines:

```python
    import arcsmith as arcs

    arcs.param.cascade_clear(state_field, [target])
    arcs.param.drop_populate(target, arcs.flds.unique_values(fc_path, state_field.valueAsText))
```

---

## Install

ArcSmith requires `arcpy`, which ships with ArcGIS Pro and is not available outside its Python environment. The recommended approach for portable tools is to drop the `arcsmith/` source folder next to the `.pyt` file so `import arcsmith as arcs` resolves locally with no installation step:

```
MyToolbox/
├── MyToolbox.pyt
└── arcsmith/
```

For installing into a cloned ArcGIS Pro environment instead, see the full [Installation](install.md) page.

---

## The six modules

Everything in ArcSmith is organized into six modules. The package is imported once, and each module is reached by name.

```python
import arcsmith as arcs
```

| Module        | Import path      | What it covers                                                                       |
|---------------|------------------|--------------------------------------------------------------------------------------|
| Parameter     | `arcs.param` | Parameter state, cascading resets, dropdown population, checkbox/dropdown dependence  |
| Fields        | `arcs.flds`  | Field maps, unique values, listing columns, standardizing blank values               |
| Feature class | `arcs.fc`    | SQL `WHERE` clauses, filtered export, polygon area, geometry-type validation          |
| Table         | `arcs.tbl`   | Standalone tables from in-memory rows, dict-based field lookups, permanent table joins |
| Workspace     | `arcs.ws`    | File geodatabase creation, temporary/scratch workspace selection                      |
| Layer         | `arcs.lyr`   | Adding layers to a map, applying `.lyrx` symbology, retrieving and removing layers    |

Few tools use all six modules at once. A typical tool leans heavily on `param` for its dialog behavior and on `fc`/`flds` for its geoprocessing.

---

## How a Python toolbox works

A `.pyt` file is plain Python that ArcGIS Pro reads as source. It defines one `Toolbox` class and one class per tool. Each tool class implements methods that ArcGIS calls at specific moments in the tool's process:

| Method             | When ArcGIS calls it                          | Where ArcSmith helps most        |
|--------------------|-----------------------------------------------|----------------------------------|
| `getParameterInfo` | When the tool dialog opens                    | Not applicable                   |
| `updateParameters` | Every time any parameter value changes        | `arcs.param`                 |
| `updateMessages`   | After ArcGIS runs its own validation          | `arcs.fc.validate_geom_type` |
| `execute`          | When **Run** is clicked                       | `arcs.fc`, `flds`, `tbl`, `ws`      |
| `postExecute`      | After outputs are added to the map            | `arcs.lyr`                   |

Only `__init__` and `execute` are strictly required, but most interactive tools also use `getParameterInfo` and `updateParameters`. Parameters are created as `arcpy.Parameter` objects in `getParameterInfo`, returned as a list, and that same list is handed back to every other method. Because of this, `parameters[0]` means the same parameter everywhere.

!!! tip "The most important state to detect is `'pending'`"
    ArcSmith collapses arcpy's two `altered` / `hasBeenValidated` booleans into four named states via `arcs.param.state`: `fresh`, `pending`, `settled`, and `confirmed`. `'pending'` marks the exact moment a value was *just* changed, which is the right time to reset or repopulate dependent parameters. This pattern is used in the tool below.

---

## Build an ArcSmith tool

This tool takes a feature class, lets the user pick a field from its attribute table, populates a dropdown with that field's unique values, and exports the rows matching the chosen value to a new feature class. It is deliberately minimal at four parameters, but it already exercises three of the six modules.

We will build it method by method, then show the complete file.

### getParameterInfo: define the dialog

```python
def getParameterInfo(self):
    p_00 = arcpy.Parameter(
        displayName="Input Feature Class",
        name="input_fc",
        datatype="GPFeatureLayer",
        parameterType="Required",
        direction="Input",
    )

    p_01 = arcpy.Parameter(
        displayName="Filter Field",
        name="filter_field",
        datatype="Field",            # Field picker dropdown
        parameterType="Required",
        direction="Input",
    )
    p_01.parameterDependencies = ["input_fc"]   # Reads its field list from p_00

    p_02 = arcpy.Parameter(
        displayName="Value to Keep",
        name="filter_value",
        datatype="GPString",         # Populated dynamically in updateParameters
        parameterType="Required",
        direction="Input",
    )

    p_03 = arcpy.Parameter(
        displayName="Output Feature Class",
        name="output_fc",
        datatype="DEFeatureClass",
        parameterType="Required",
        direction="Output",          # ArcGIS adds the result to the map automatically
    )

    return [p_00, p_01, p_02, p_03]
```

Two details matter here. Setting `p_01.parameterDependencies = ["input_fc"]` points the field picker at `p_00` by its `name`, so ArcGIS fills the field list automatically from whatever feature class the user chooses. And `direction="Output"` on `p_03` means ArcGIS adds the exported feature class to the map automatically once the tool finishes. No `arcpy.mp` code is required.

### updateParameters: make the dialog react

When the user picks a field, we read its unique values and load them into the **Value to Keep** dropdown. When they switch to a different field, the old selection is cleared first.

```python
def updateParameters(self, parameters):
    fc_in      = parameters[0]   # p_00
    field      = parameters[1]   # p_01
    value_pick = parameters[2]   # p_02

    if fc_in.value:
        # Resolve to a real path. This works whether the user browsed to a
        # file or selected a layer from the map's Contents pane.
        fc_in_path = arcs.param.to_path(fc_in)

        # Clear the value dropdown whenever the field changes.
        arcs.param.cascade_clear(field, [value_pick])

        # Repopulate only when the field was just picked ('pending') or holds
        # a validated default ('settled'). The `field.value` guard avoids
        # scanning before the field has resolved against a new feature class.
        if arcs.param.state(field) in ("pending", "settled") and field.value:
            values = arcs.flds.unique_values(fc_in_path, field.valueAsText)
            arcs.param.drop_populate(value_pick, values)

    return
```

!!! note "Why `to_path` instead of `valueAsText`?"
    When a user selects a layer from the map rather than browsing to a file, `valueAsText` returns the layer's display name (e.g. `"Trails 2024"`), not a path arcpy can open. `arcs.param.to_path` calls `arcpy.Describe` and returns the absolute `catalogPath`, handling the `None` check automatically.

!!! note "Why check both `'pending'` and `'settled'`?"
    `'pending'` catches the user actively changing the field. `'settled'` catches a default value that ArcGIS has validated on first open but the user hasn't touched. Without it, a dropdown driven by a default field would start empty. `cascade_clear` only fires on `'pending'`/`'fresh'`, so it never wipes a freshly populated `'settled'` list.

### execute: produce the output

By the time `execute` runs, every parameter has been validated allowing values to be read directly.

```python
def execute(self, parameters, messages):
    fc_in_path = arcs.param.to_path(parameters[0])
    field      = parameters[1].valueAsText
    value      = parameters[2].valueAsText
    out_fc     = parameters[3].valueAsText

    # build_where inspects the field type and quotes the value correctly:
    #   string field  →  "TRAIL_STATUS" = 'Open'
    #   numeric field →  "DISTRICT" = 4
    where = arcs.fc.build_where(fc_in_path, field, value)

    # export_fc filters rows (and optionally fields) into a new feature class
    # in a single call, with no intermediate layer.
    arcs.fc.export_fc(fc_in_path, out_fc, where_clause=where)

    return
```

`arcs.fc.build_where` handles the data-source-specific field delimiters and the quote-or-not decision based on field type, so the SQL never has to be assembled by hand. `arcs.fc.export_fc` wraps `ExportFeatures` with ArcSmith's field-mapping logic; here we pass only a `where_clause`, so all fields are kept and only matching rows are exported.

### Complete tool file

Save this as `quickstart_tool.pyt` next to the `arcsmith/` folder, then add it through the Catalog pane (**Toolboxes → Add Toolbox**) and double-click the tool.

```python
# -*- coding: utf-8 -*-

import arcpy
import arcsmith as arcs


class Toolbox:
    def __init__(self):
        self.label = "Quickstart Toolbox"
        self.alias = "quickstart"
        self.tools = [ValueFilter]


class ValueFilter:
    def __init__(self):
        self.label = "Value Filter"
        self.description = (
            "Filter a feature class to the rows matching a chosen field value "
            "and export them to a new feature class."
        )

    def getParameterInfo(self):
        p_00 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        p_01 = arcpy.Parameter(
            displayName="Filter Field",
            name="filter_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p_01.parameterDependencies = ["input_fc"]

        p_02 = arcpy.Parameter(
            displayName="Value to Keep",
            name="filter_value",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )

        p_03 = arcpy.Parameter(
            displayName="Output Feature Class",
            name="output_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        return [p_00, p_01, p_02, p_03]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        fc_in      = parameters[0]
        field      = parameters[1]
        value_pick = parameters[2]

        if fc_in.value:
            fc_in_path = arcs.param.to_path(fc_in)
            arcs.param.cascade_clear(field, [value_pick])

            if arcs.param.state(field) in ("pending", "settled") and field.value:
                values = arcs.flds.unique_values(fc_in_path, field.valueAsText)
                arcs.param.drop_populate(value_pick, values)

        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        fc_in_path = arcs.param.to_path(parameters[0])
        field      = parameters[1].valueAsText
        value      = parameters[2].valueAsText
        out_fc     = parameters[3].valueAsText

        where = arcs.fc.build_where(fc_in_path, field, value)
        arcs.fc.export_fc(fc_in_path, out_fc, where_clause=where)

        return

    def postExecute(self, parameters):
        return
```

### Try it

1. In ArcGIS Pro, add the toolbox and open **Value Filter**.
2. Set **Input Feature Class**. The **Filter Field** dropdown fills automatically.
3. Pick a field. The **Value to Keep** dropdown populates with that field's unique values. Switch fields and watch it reset and repopulate.
4. Choose a value, set an output path, and click **Run**. The filtered result is added to the map.

---

## What to learn next

That covers the core loop: define parameters, make them react in `updateParameters`, and do the work in `execute`. From here:

- **Add more interactivity.** `arcs.param.checkbox_dependence` and `dynamic_dropdown` enable and disable groups of parameters based on a checkbox or a dropdown selection. See the [Parameter reference](../reference/param.md).
- **Filter on many values, or trim fields.** `arcs.fc.build_where_in` builds an `IN` clause from a multi-value parameter, and `export_fc` accepts a `fields` list to keep or drop columns. See the [Feature class reference](../reference/fc.md).
- **Set up workspaces and symbolized output.** `arcs.ws.init_gdb` creates a file geodatabase. `arcs.lyr.add` adds layers with inline `simple_sym` fill/stroke styling or a `.lyrx` file, and `apply_lyrx` applies `.lyrx` styling to existing layers. See [Workspace](../reference/ws.md) and [Layer](../reference/lyr.md).
- **Create tables and join data.** `arcs.tbl.from_rows` materializes Python rows as a table, `arcs.tbl.join_lookup` adds a field from a `{key: value}` lookup with no physical table, and `arcs.tbl.join_table` joins an external table's columns in permanently. See the [Table reference](../reference/tbl.md).
- **Build a full tool from scratch.** The [Census Regions tutorial](census_tool_tut.md) walks through an eight-parameter tool. It covers cascading dropdowns, an optional field picker, a checkbox-controlled prefix, multiple dissolved outputs, and symbology applied in `postExecute`, explaining the reasoning behind every decision.

<br><br><br><br><br>