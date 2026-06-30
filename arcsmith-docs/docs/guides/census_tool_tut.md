# Tutorial: Building the Census Regions Tool

<div class="as-download-strip">
  <div class="as-download-strip__text">
    <p class="as-download-strip__title">Tutorial data and toolbox</p>
    <p class="as-download-strip__sub">Includes the complete <code>source_files/</code> folder with sample data, ArcSmith, a lyrx file, and a finished copy of the tool.</p>
  </div>
  <a class="as-download-strip__btn" href="">Download (Coming soon)</a>
</div>

This tutorial covers building a real ArcGIS Pro geoprocessing tool from scratch using Python and the **ArcSmith** helper library. Each section explains the reasoning behind each decision, not just the code that results from it. The goal is to produce both a working tool and a clear mental model for building others.

---

## What Is a Python Toolbox?

A Python toolbox is a `.pyt` file that ArcGIS Pro reads as Python source code. Inside it, one `Toolbox` class registers the toolbox and lists which tools it contains, and one class is defined per tool. Each tool class contains a set of methods that ArcGIS calls at different moments during the tool's lifecycle: when the dialog opens, when a value changes, when Run is clicked, and so on.

What makes `.pyt` files particularly effective for tool development is that they are plain text. The file can be opened in any editor, saved, and ArcGIS picks up the changes immediately after a refresh. There is no compilation step, no separate dialog designer, and no XML to hand-edit. The interface, the validation logic, and the geoprocessing code all live in one readable file.

The tool built in this tutorial, **Census Regions**, takes a US Census county feature class, allows the selection of a set of states, trims the data to only the needed fields, and produces three output layers: county polygons for the selected states, state boundaries dissolved from those counties, and a single region boundary dissolving all selected states into one polygon.

---

## Loading a Toolbox in ArcGIS Pro

Before building anything, it helps to know how a toolbox is connected to a project. There are two ways to load a `.pyt` file:

**Browse to the folder (session only):** Navigate to the folder containing the `.pyt` file in the Catalog pane, expand it, and double-click the tool. This connection persists only for the current session. If the project is closed and reopened, the folder needs to be browsed to again.

**Add Toolbox (persists with the project):** Right-click **Toolboxes** in the Catalog pane and choose **Add Toolbox**. Browse to the `.pyt` file and select it. This registers the toolbox with the project and it will reopen automatically the next time the project is loaded.

To pick up changes after editing the `.pyt` file in an external editor, right-click the toolbox in the Catalog pane and choose **Refresh**. The tool dialog will reflect the updated code immediately.

---

## What Each Tool Method Does

Every tool class can define the following methods. Only `__init__` and `execute` are required. Most real tools use at least `getParameterInfo` and `updateParameters` as well.

| Method | When ArcGIS calls it |
|---|---|
| `__init__` | When the toolbox is loaded |
| `getParameterInfo` | When the tool dialog opens |
| `isLicensed` | When ArcGIS checks whether the tool should be enabled |
| `updateParameters` | Every time any parameter value changes |
| `updateMessages` | After ArcGIS runs its own internal validation |
| `execute` | When Run is clicked |
| `postExecute` | After execute finishes and outputs are added to the map |

These methods do not have to be written in strict isolation. A common and productive workflow is to define a parameter in `getParameterInfo`, immediately write the interactive behavior for it in `updateParameters`, test the result, and then return to `getParameterInfo` to define the next parameter. This tutorial follows that back-and-forth pattern.

---

## Try the Finished Tool First

The downloaded tutorial files include a completed copy of the tool. Opening and running it before building from scratch gives a clear picture of what is being built and lets the interactive parameter behavior be explored firsthand.

1. Extract the downloaded zip to a location on the machine.
2. In ArcGIS Pro, open the Catalog pane and navigate to the extracted `source_files/` folder.
3. Right-click **Toolboxes** in the Catalog pane, choose **Add Toolbox**, and select `census_tool_demo.pyt`.
4. To load the sample data, right-click `census_tutorial.gdb` in the Catalog pane and choose **Add To Current Map**. This makes the `CensusCounties` layer available in the map Contents pane.
5. Expand the toolbox and double-click **Census Regions** to open the tool dialog.

With the dialog open, spend a moment exploring how the parameters respond to each other before running the tool:

- Set **National County Feature Class** to the `CensusCounties` layer just added to the map. Notice that the **State Name Field** dropdown's list of text fields populates automatically, though no field is selected yet.
- Set **State Name Field** to a text field such as `NAMELSAD` and observe that the **States to Include** checklist populates with the unique values from that field. Then set it to `ST_STUSPS` to load the state abbreviations instead.
- Check **Add Results Prefix** and confirm that the **Output Prefix** text field activates. Uncheck it and confirm the field grays out again.

Once the parameters have been explored, set **States to Include** to a few states, pick `NAMELSAD` and `ST_STUSPS` in **Fields to Keep**, point the output at any geodatabase on the machine, and click **Run**. Three styled layers will be added to the map. The rest of this tutorial explains how every part of that behavior was built.

---

## Starter Template

Save the following as `census_tutorial.pyt` inside the `source_files/` folder. Every new toolbox starts from something like this.

```python
# -*- coding: utf-8 -*-

import arcpy


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Tool]


class Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tool"
        self.description = ""

    def getParameterInfo(self):
        """Define the tool parameters."""
        params = None
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed. This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
```

Rename the `Toolbox` label and alias and replace the `Tool` class with the `CensusRegions` class. The template already includes a `postExecute` stub, which ArcGIS Pro does not generate by default but is worth including from the start.

---

## Project Layout

The tutorial data and ArcSmith are pre-packaged in `source_files/`. Its layout looks like this:

```
source_files/
├── census_tutorial.pyt   <-- The file to be created in this tutorial
├── census_tool_demo.pyt  <-- Demonstration version of the finished tool
├── census_tutorial.gdb/
│   └── CensusCounties
├── arcsmith/
│   └── ...
└── lyrx/
    └── state_boundary.lyrx
```

When ArcGIS Pro runs a `.pyt` file, Python automatically adds that file's directory to `sys.path`. Because `arcsmith/` sits in the same folder as the `.pyt`, `import arcsmith as arcs` resolves to the local copy without any installation step. This structure means the whole folder can be zipped and sent to a colleague and it will work immediately after unzipping on any machine.

### Creating the .pyt file

A `.pyt` file is a plain text file with a renamed extension. To create one, open any text editor. Notepad on Windows works fine, though a code editor like [Visual Studio Code](https://code.visualstudio.com/) provides syntax highlighting and makes working with Python considerably easier. Paste the starter template from the next section into the file, then save it with the name `census_tutorial.pyt` directly inside `source_files/`. When saving from Notepad, set **Save as type** to **All Files** to prevent Windows from appending `.txt` to the filename.

---

## Understanding Parameters Before Starting

Before writing any code, it helps to understand how parameters flow through a toolbox, because the same concept appears in every method.

Inside `getParameterInfo`, each parameter is created as an `arcpy.Parameter` object, collected into a Python list in the order they should appear in the dialog, and that list is returned. ArcGIS reads the list and builds the tool dialog from it.

Every other method receives that same list back as an argument called `parameters`. Individual parameters are accessed by their position: `parameters[0]` is the first one in the list, `parameters[1]` is the second, and so on. That index is the only thing connecting a parameter across `getParameterInfo`, `updateParameters`, `execute`, and `postExecute`.

This tutorial names each parameter variable with a zero-padded number prefix during definition (`p_00`, `p_01`, `p_02`, and so on) so that the index is visible in the variable name itself. When `parameters[3]` appears later inside `execute`, it is immediately clear that it refers to `p_03` without counting. Zero-padding matters for tools with ten or more parameters: without it, `p_1` would sort between `p_10` and `p_2` in most editors rather than in list order.

For the full list of valid `datatype` strings accepted by `arcpy.Parameter`, see the [ArcGIS Pro documentation on geoprocessing data types](https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing_and_python/defining-parameter-data-types-in-a-python-toolbox.htm).

Now update the template: rename the class to `CensusRegions`, set the label and description, and add `import arcsmith as arcs` at the top. The skeleton to work toward looks like this:

```python
# -*- coding: utf-8 -*-

import arcpy
import arcsmith as arcs
from pathlib import Path


class Toolbox:
    def __init__(self):
        self.label = "Census Tutorial Toolbox"
        self.alias = "censustutorial"
        self.tools = [CensusRegions]


class CensusRegions:
    def __init__(self):
        self.label = "Census Regions"
        self.description = (
            "Filter US Census county data to selected states, "
            "trim fields, and produce county, state, and region boundary layers."
        )

    def getParameterInfo(self): ...
    def isLicensed(self): return True
    def updateParameters(self, parameters): ...
    def updateMessages(self, parameters): return
    def execute(self, parameters, messages): ...
    def postExecute(self, parameters): ...
```

Each `...` is a placeholder to be filled in. After saving the file, open the tool dialog in ArcGIS Pro by right-clicking the `.pyt` in the Catalog pane, selecting **Refresh**, and double-clicking the tool. It will open with no parameters yet. Keep the dialog open throughout development. Each save-and-refresh will update it to reflect the latest code.

---

## p_00: The Input Feature Class

`getParameterInfo` starts with the input feature class. It is the foundation of this tool: every other parameter depends on knowing which feature class is being worked with.

Add this to the `getParameterInfo` method:

```python
def getParameterInfo(self):

    p_00 = arcpy.Parameter(
        displayName="National County Feature Class",  # Label shown in the tool dialog
        name="county_fc",                             # Internal ID used in parameterDependencies
        datatype="DEFeatureClass",                    # Accepts a path to a feature class on disk
        parameterType="Required",
        direction="Input",
    )
    # Development default. Pre-fills the dialog for faster testing during development.
    # Comment this out or remove it before distributing the tool.
    p_00.value = r"C:\source_files\census_tutorial.gdb\CensusCounties"

    params = [p_00]
    return params
```

`datatype="DEFeatureClass"` tells ArcGIS to display a file browser that accepts feature classes on disk. The `name` argument (`"county_fc"`) is the internal identifier referenced in `parameterDependencies` later.

**On setting a default value for development:** Calling `p_00.value = ...` pre-fills the dialog with a path so the dialog opens ready to test without typing the path every time. This is the general pattern for *development defaults*: any line that pre-fills an input with data is there only to speed up testing. That data might be a feature class path, a field name, or a list of values. Such a value points at something on the developer's machine, not the end user's, so these lines are commented out or removed before the tool is distributed. They are also a testing convenience only within a session: each refresh reloads the tool with whatever defaults the code sets, so a value the developer typed by hand is not remembered and has to be reselected.

This is distinct from a *functional default* such as a checkbox that should start checked or unchecked (`p_05` and `p_07` later in this tutorial). Those express sensible starting behavior for every user and are meant to ship with the tool. The rule of thumb: comment out defaults that pre-fill machine-specific data; keep defaults that set sensible behavior.

Save the file, refresh the toolbox, and open the tool dialog. One parameter should appear: a feature class browser pre-filled with the sample data path. Confirm it resolves to the CensusCounties layer before moving on.

---

## p_01: The State Field, Definition and Interactivity Together

The next parameter is a field picker for choosing which field contains state abbreviations. Rather than defining all parameters first and wiring them up later, the interactive behavior for this parameter is written immediately after defining it. This is the back-and-forth workflow that makes toolbox development feel natural.

### Define p_01 in getParameterInfo

Update `getParameterInfo` to add `p_01` and include both parameters in the returned list:

```python
    p_01 = arcpy.Parameter(
        displayName="State Name Field",
        name="state_field",
        datatype="Field",           # Creates a field picker dropdown
        parameterType="Required",
        direction="Input",
    )
    p_01.parameterDependencies = ["county_fc"]  # Reads field list from p_00
    p_01.filter.list = ["Text"]                 # Restrict to string fields only
    p_01.value = "ST_STUSPS"                    # Default: the state abbreviation field in Census data

    params = [p_00, p_01]
    return params
```

`datatype="Field"` creates a field picker, but a field picker on its own is empty because it does not know which feature class to read from. Setting `parameterDependencies = ["county_fc"]` points it at p_00 by its `name`. ArcGIS reads the field list from whatever the user has set for `county_fc` and populates the dropdown automatically. The value in that list must match the `name` property of the target parameter, not its `displayName` or its index.

`filter.list = ["Text"]` restricts the dropdown to string fields only. State abbreviations are strings, so numeric and date fields are not relevant here.

### Wire up the state dropdown in updateParameters

Now move to `updateParameters`. When a state field is picked, every unique value in that field should be read and loaded into the next parameter's checklist. This logic is written now, even though that checklist parameter does not exist yet:

```python
def updateParameters(self, parameters):

    fc_in       = parameters[0]   # p_00: the input feature class
    state_field = parameters[1]   # p_01: the state field picker

    if fc_in.value:
        # Resolve the feature class to a real file path (safe for map-layer inputs)
        fc_in_path = arcs.param.to_path(fc_in)

        if arcs.param.state(state_field) in ("pending", "settled") and state_field.value:
            states = arcs.flds.unique_values(fc_in_path, state_field.valueAsText)
            # parameters[2] is the States to Include checklist, defined in the next section.
            # arcs.param.drop_populate(parameters[2], states)

    return
```

Leave the `drop_populate` call commented out for now. It references `parameters[2]`, which does not exist yet. It will be uncommented after the next parameter is defined.

Two things in this code need explanation.

**Why `arcs.param.to_path` instead of `.valueAsText`?**

When a layer is selected from the map Contents pane rather than browsed to as a file, `.valueAsText` returns the display name shown in the map (for example, `"CensusCounties"`), not the underlying file path. `arcs.param.to_path` calls `arcpy.Describe` on the parameter value object and returns `catalogPath`, which is always the resolvable absolute file path regardless of how the input was provided.

!!! note "Without ArcSmith"
    Without `arcs.param.to_path`, the catalog path would need to be retrieved manually. That requires checking whether the parameter value is set before calling `arcpy.Describe` to avoid a `None` error:

    ```python
    if fc_in.value:
        fc_in_path = arcpy.Describe(fc_in.value).catalogPath
    ```

    ArcSmith wraps this into a single safe call that handles the `None` check internally.

**What does `arcs.param.state` return?**

ArcGIS tracks two booleans on every parameter: `altered` (whether the user has changed it) and `hasBeenValidated` (whether ArcGIS has run validation on it). ArcSmith combines these into four named states that are easier to reason about than the raw flags:

| State | What it means |
|---|---|
| `fresh` | Never touched and not yet validated |
| `pending` | Just changed by the user, not yet validated |
| `settled` | Not changed, but has been validated (initial load with a default) |
| `confirmed` | Changed and validated |

Checking for `"pending"` means the unique-value scan only runs when the user actively picks a new state field, not on every pass through `updateParameters` triggered by changes to unrelated parameters.

!!! note "Without ArcSmith"
    Without ArcSmith, the `altered` and `hasBeenValidated` booleans would need to be checked directly and combined every time this logic appears:

    ```python
    if state_field.altered and not state_field.hasBeenValidated:
        # field was just changed
    ```

    That pattern must be repeated for every parameter that needs it. The four named states make intent explicit and eliminate the repeated boolean logic across the entire toolbox.

Save and refresh. The dialog should now show two parameters. Changing the feature class path should update the field picker's list automatically.

---

## p_02: States to Include

Now add the multi-value checklist that will hold the available states. Update `getParameterInfo`:

```python
    p_02 = arcpy.Parameter(
        displayName="States to Include",
        name="states",
        datatype="GPString",
        parameterType="Required",
        direction="Input",
        multiValue=True,   # Changes control from a text box to a checklist
    )

    params = [p_00, p_01, p_02]
    return params
```

`multiValue=True` changes the UI control from a single text box to a checklist. The filter list for this parameter is intentionally not set here. Hardcoding a list of state abbreviations would make the tool brittle and specific to this dataset. Instead, the list is built dynamically in `updateParameters` from the actual values present in whichever field the user chose.

Now return to `updateParameters` to finish what was started. Uncomment the `drop_populate` line, add `selected_states` as an alias for `parameters[2]`, and add a `cascade_clear` call above `drop_populate`:

```python
def updateParameters(self, parameters):

    fc_in           = parameters[0]   # p_00
    state_field     = parameters[1]   # p_01
    selected_states = parameters[2]   # p_02: now defined

    if fc_in.value:
        fc_in_path = arcs.param.to_path(fc_in)

        # Clear any previous state selections when the field changes
        arcs.param.cascade_clear(state_field, [selected_states])

        if arcs.param.state(state_field) in ("pending", "settled") and state_field.value:
            # Read the unique values from the chosen field and populate the checklist
            states = arcs.flds.unique_values(fc_in_path, state_field.valueAsText)
            arcs.param.drop_populate(selected_states, states)

    return
```

`arcs.param.cascade_clear` clears `selected_states` whenever `state_field` is `pending` or `fresh`. Without this, if FL, GA, and AL were selected using one field and the user then switched to a different field, those three selections would silently persist in the checklist even though they may not be valid values in the new context.

The populate check uses `"pending"` or `"settled"` rather than `"pending"` alone. `"pending"` catches the case where the user actively changes the field. `"settled"` catches the case where the field already holds a value that ArcGIS has validated but the user has not yet interacted with. This most commonly happens with a development default like `p_01.value = "ST_STUSPS"`. With that default active, the field arrives pre-filled on the first pass, and without `"settled"` the states checklist would stay empty on open even though `ST_STUSPS` is already selected, because a pre-filled value goes through `"settled"` rather than `"pending"`. `cascade_clear` does not interfere with this because it only clears on `"pending"` or `"fresh"`, not `"settled"`, so the populate runs without being immediately wiped.

Once the development default is commented out for distribution, the field opens empty, so this first-pass populate simply does not fire until the user picks a field. That is the intended behavior for the shipped tool. Keeping `"settled"` in the check costs nothing in that case and keeps the tool convenient to test while the default is active.

The `and state_field.value` guard is also necessary. When a feature class is first set, ArcGIS may run `updateParameters` with `state_field` in `"settled"` state before it has resolved the field default against the new feature class. At that moment `state_field.valueAsText` returns `None`, which causes `unique_values` to error. The guard ensures the scan only runs when the field picker actually holds a value.

!!! note "Without ArcSmith"
    Populating a dropdown dynamically with vanilla arcpy requires a `SearchCursor` to read values, manual deduplication, sorting, and assignment to the filter list. The cascade clear requires an additional state check and a manual value reset:

    ```python
    if state_field.altered and not state_field.hasBeenValidated:
        # Read unique values manually
        seen = set()
        values = []
        with arcpy.da.SearchCursor(fc_in_path, [state_field.valueAsText]) as cur:
            for row in cur:
                if row[0] not in seen:
                    seen.add(row[0])
                    values.append(str(row[0]))
        values.sort()
        selected_states.filter.type = "ValueList"
        selected_states.filter.list = values

    # Clear stale selections when the field changes
    if state_field.altered and not state_field.hasBeenValidated:
        selected_states.value = None
    ```

    `arcs.flds.unique_values` and `arcs.param.drop_populate` replace all of that with two lines. `cascade_clear` replaces the manual state check and reset with one.

Save and refresh. Change the state field and confirm that the States to Include checklist repopulates with the actual unique values from that field.

---

## p_03: Fields to Keep

Add a multi-value field picker that lets the user select which columns to carry through to the outputs. This parameter is made `Optional` so that leaving it blank is a valid choice. When no fields are selected, only geometry is copied, which can be a useful output in its own right.

```python
    p_03 = arcpy.Parameter(
        displayName="Fields to Keep",
        name="fields_to_keep",
        datatype="Field",
        parameterType="Optional",   # Blank = geometry only, no attribute fields
        direction="Input",
        multiValue=True,
    )
    p_03.parameterDependencies = ["county_fc"]  # Field list populated from p_00

    params = [p_00, p_01, p_02, p_03]
    return params
```

Like p_01, this parameter depends on `county_fc` and ArcGIS will populate the field list automatically when the input changes. No type filter is applied because fields of any type may be worth keeping.

Because this parameter is `Optional`, `valueAsText` can return `None` when nothing is selected. This needs to be handled in `execute`. The approach is to check for `None` and pass `None` to `export_fc`, which interprets a `None` field list as a request to copy all fields. To produce geometry-only output instead, pass an empty list `[]`. This is handled in the execute section below.

!!! tip "Fields to use for this tutorial"
    For the Census data, select `NAMELSAD` (the county name) and `ST_STUSPS` (the state abbreviation). These are the two fields needed for the outputs this tool produces.

### Add an updateMessages warning

`updateMessages` runs after ArcGIS's own internal validation. It is the right place to add custom warnings that inform the user of valid but potentially surprising choices. Since an empty field selection is now allowed, it is worth flagging it:

```python
def updateMessages(self, parameters):
    fc_in          = parameters[0]
    fields_to_keep = parameters[3]

    # Only warn about empty fields once a feature class has been set.
    # Without this guard, the warning fires immediately when the dialog opens,
    # before the user has had a chance to select anything.
    if fc_in.value and not fields_to_keep.value:
        fields_to_keep.setWarningMessage(
            "No fields selected. The output will contain geometry only."
        )
    return
```

`setWarningMessage` shows a yellow warning indicator on the parameter without blocking the tool from running. The user is informed but not prevented from proceeding. This is the correct choice for a valid but unusual input. Use `setErrorMessage` only when the tool genuinely cannot run with the given value.

The `fc_in.value` guard is important. Without it the warning fires the moment the tool dialog opens, before the user has set anything at all. Gating it on the feature class being present means the warning only appears once the user is actively filling out the tool.

---

## p_04: Output Geodatabase

Since this tool produces multiple outputs, it is more convenient for the user to set a single output location rather than specify a path for each feature class individually. A single workspace parameter covers all three outputs. For contrast, if the tool produced only one output it would make more sense to expose that output as a proper output parameter. See the [Symbology on a Single-Output Tool](#symbology-on-a-single-output-tool-an-alternative-approach) section later in this tutorial for an example of that pattern.

```python
    p_04 = arcpy.Parameter(
        displayName="Output Geodatabase",
        name="output_gdb",
        datatype="DEWorkspace",    # Accepts a geodatabase or folder path
        parameterType="Required",
        direction="Input",
    )

    params = [p_00, p_01, p_02, p_03, p_04]
    return params
```

`datatype="DEWorkspace"` opens a browser that accepts geodatabases and folders. This parameter needs no `updateParameters` logic.

---

## p_05 and p_06: A Checkbox Controlling a Text Field

These two parameters work together. A checkbox (p_05) controls whether a text field (p_06) is active. When the checkbox is unchecked, the text field is grayed out and ignored. When it is checked, the text field becomes active and its value is prepended to the output feature class names.

Add both parameters to `getParameterInfo`:

```python
    p_05 = arcpy.Parameter(
        displayName="Add Results Prefix",
        name="add_prefix",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input",
    )
    p_05.value = False   # Unchecked by default

    p_06 = arcpy.Parameter(
        displayName="Output Prefix",
        name="output_prefix",
        datatype="GPString",
        parameterType="Optional",
        direction="Input",
    )
    # No default value. The user supplies whatever prefix fits their project.

    params = [p_00, p_01, p_02, p_03, p_04, p_05, p_06]
    return params
```

Now return to `updateParameters` and add one line to handle the relationship between them:

```python
    # Enable/disable the prefix text field based on the checkbox state
    arcs.param.checkbox_dependence(add_prefix, output_prefix, hidden_value=None)
```

The full `updateParameters` method now looks like this:

```python
def updateParameters(self, parameters):

    fc_in           = parameters[0]   # p_00
    state_field     = parameters[1]   # p_01
    selected_states = parameters[2]   # p_02
    add_prefix      = parameters[5]   # p_05
    output_prefix   = parameters[6]   # p_06

    if fc_in.value:
        fc_in_path = arcs.param.to_path(fc_in)
        arcs.param.cascade_clear(state_field, [selected_states])

        if arcs.param.state(state_field) in ("pending", "settled") and state_field.value:
            states = arcs.flds.unique_values(fc_in_path, state_field.valueAsText)
            arcs.param.drop_populate(selected_states, states)

    arcs.param.checkbox_dependence(add_prefix, output_prefix, hidden_value=None)

    return
```

`arcs.param.checkbox_dependence` handles the full enable/disable/clear cycle automatically. When `add_prefix` is unchecked it disables `output_prefix` and clears its value. When it is checked, `output_prefix` is enabled. When the state is stable (the checkbox has not just changed), the call is a no-op so any text already typed is preserved.

!!! note "Without ArcSmith"
    Without ArcSmith, managing a checkbox-controlled dependent parameter requires checking the checkbox value, manually toggling `enabled`, and conditionally clearing the dependent value, with extra care to avoid clearing user input on stable passes:

    ```python
    if not add_prefix.value:
        output_prefix.enabled = False
        output_prefix.value = None
    elif add_prefix.altered and not add_prefix.hasBeenValidated:
        output_prefix.enabled = True
    # else: stable, do nothing and preserve user input
    ```

    `checkbox_dependence` encapsulates all of that logic in one call and handles the stable-pass case correctly without any additional guards.

Save and refresh. Check and uncheck **Add Results Prefix** and confirm that the **Output Prefix** field grays in and out correctly.

---

## p_07: Apply Symbology

Add the last parameter, a checkbox that controls whether symbology is applied to the output layers:

```python
    p_07 = arcpy.Parameter(
        displayName="Apply Symbology",
        name="apply_symbology",
        datatype="GPBoolean",
        parameterType="Optional",
        direction="Input",
    )
    p_07.value = True   # Default to styled output

    params = [p_00, p_01, p_02, p_03, p_04, p_05, p_06, p_07]
    return params
```

The default is `True` because a styled result is more useful than an unstyled one in most cases. This parameter needs no `updateParameters` logic.

With all eight parameters defined, save and refresh one more time. The tool dialog should now display all parameters in order with the prefix field responding to the checkbox.

---

## execute: Building the Outputs

`execute` runs when **Run** is clicked. All parameters have been validated before this method is called, so values can be read directly.

### Reading parameter values

The first block of `execute` resolves and aliases every parameter value. Grouping this at the top keeps the geoprocessing logic below clean:

```python
def execute(self, parameters, messages):

    # --- Resolve all parameter values up front ---
    fc_in_path    = arcs.param.to_path(parameters[0])   # Absolute path, safe for map inputs
    state_field   = parameters[1].valueAsText                # Field name as a string
    states_list   = parameters[2].valueAsText.split(";")     # Multi-value → Python list
    out_gdb       = parameters[4].valueAsText                # Workspace path as a string
    add_prefix    = parameters[5].value                      # Boolean: use .value, not .valueAsText
    output_prefix = parameters[6].valueAsText                # String or None if blank
    apply_sym     = parameters[7].value                      # Boolean

    # p_03 (fields_to_keep) is Optional. Handle None separately below.
    fields_raw = parameters[3].valueAsText
    fields_list = fields_raw.split(";") if fields_raw else None   # None = copy all fields
```

**`.value` vs `.valueAsText`:** The right choice depends on what the value will be used for.

`.valueAsText` returns a string representation of the parameter value. It is the natural choice for strings, field names, and file paths because those are already strings. For multi-value parameters, it returns selections as a semicolon-delimited string (`"FL;GA;AL"`), which `.split(";")` converts to a Python list.

`.value` returns the raw Python value: a `bool` for checkboxes, an arcpy object for feature classes, or a string for text fields. For checkboxes, `.value` is the correct choice. `.valueAsText` on a boolean returns `"true"` or `"false"` as strings, and since non-empty strings are always truthy in Python, an `if apply_sym` check would always be `True` regardless of whether the box was checked.

Sometimes the raw parameter object is best left un-called entirely. When passing a parameter directly to another arcpy function or ArcSmith helper that knows how to inspect the parameter itself (such as `arcs.param.to_path`), calling `.value` or `.valueAsText` first is unnecessary.

**Handling the optional fields parameter:** Because p_03 is `Optional`, `valueAsText` returns `None` when nothing is selected. Passing `None` to `arcs.fc.export_fc` for the `fields` argument tells it to copy all fields, which is the correct interpretation. Passing an empty list `[]` with `keep=True` would instead produce geometry-only output.

---

### The geoprocessing workflow

The core of this tool is three steps: filter and slim the county data, dissolve to state boundaries, dissolve to a region boundary.

```python
    # --- Step 1: Build the output prefix ---
    # If prefixing is enabled, append an underscore separator to the prefix string.
    # If not, use an empty string so output names are unchanged.
    prefix = f"{output_prefix}_" if add_prefix else ""

    # --- Step 2: Filter counties to selected states and trim to chosen fields ---
    # build_where_in constructs a SQL IN clause from the list of selected states,
    # handling field delimiting and value quoting automatically.
    where_states = arcs.fc.build_where_in(fc_in_path, state_field, states_list)

    # export_fc combines ExportFeatures with a field filter and
    # a where clause in a single call. No intermediate layer needed.
    census_lite = arcs.fc.export_fc(
        fc_in_path,
        f"{out_gdb}/{prefix}census_lite",  # Output path built from workspace + name
        fields_list,                        # None = all fields, list = keep these fields
        keep=True,
        where_clause=where_states,
    )

    # --- Step 3: Dissolve counties to state boundaries ---
    # Dissolve groups all counties belonging to the same state into one polygon.
    # Dissolve returns a Result object. str() extracts the output path.
    state_boundaries = str(arcpy.management.Dissolve(
        census_lite,
        f"{out_gdb}/{prefix}state_boundaries",
        state_field,   # Dissolve field: one output polygon per unique state value
    ))

    # --- Step 4: Dissolve everything to a single region boundary ---
    # No dissolve field = all features merge into one polygon.
    region_boundary = str(arcpy.management.Dissolve(
        census_lite,
        f"{out_gdb}/{prefix}region_boundary",
    ))
```

`arcs.fc.build_where_in` inspects the field type on the feature class and handles SQL quoting automatically, producing a clause like:

```sql
"ST_STUSPS" IN ('FL', 'GA', 'AL')
```

!!! note "Without ArcSmith"
    Without ArcSmith, building the `IN` clause and exporting with a field filter requires substantially more code:

    ```python
    # Build the WHERE clause manually
    field_obj = [f for f in arcpy.ListFields(fc_in_path) if f.name == state_field][0]
    delimited = arcpy.AddFieldDelimiters(fc_in_path, state_field)
    quoted = [f"'{v}'" for v in states_list] if field_obj.type == "String" else states_list
    where_states = f"{delimited} IN ({', '.join(quoted)})"

    # Build a FieldMappings object to filter fields
    fm = arcpy.FieldMappings()
    fm.addTable(fc_in_path)
    keep_lower = {f.lower() for f in fields_list} if fields_list else None
    if keep_lower:
        for i in range(fm.fieldCount - 1, -1, -1):
            name = fm.getFieldMap(i).outputField.name
            if name.lower() not in keep_lower:
                fm.removeFieldMap(i)

    # Export
    arcpy.conversion.ExportFeatures(
        fc_in_path,
        f"{out_gdb}/{prefix}census_lite",
        where_clause=where_states,
        field_mapping=fm,
    )
    census_lite = f"{out_gdb}/{prefix}census_lite"
    ```

    `arcs.fc.build_where_in` and `arcs.fc.export_fc` replace all of that with two calls.

Both dissolves operate on `census_lite` rather than the original feature class. Because `census_lite` already contains only the selected states, neither dissolve needs its own where clause.

`arcpy.management.Dissolve` returns an arcpy `Result` object, not a string path. Wrapping it in `str()` extracts the output path string, which is what `arcs.lyr.add` expects.

---

### Adding layers to the map

```python
    # --- Step 5: Add outputs to the active map ---
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap

    if apply_sym:
        # Counties and Region take simple fill/stroke symbology, applied inline
        # through simple_sym. Neither needs a .lyrx file.
        arcs.lyr.add(
            active_map, census_lite,
            lyr_name="Counties",
            fill_color="#EBFAEB", stroke_color="#6E6E6E", stroke_width=0.7,
        )
        # Region is a hollow outline: fill_opacity=0 clears the interior,
        # leaving a 2.5 pt black boundary.
        arcs.lyr.add(
            active_map, region_boundary,
            lyr_name="Region",
            fill_opacity=0, stroke_color="#000000", stroke_width=2.5,
        )
        # States carries complex .lyrx symbology (a dashed line over a solid
        # white backing). It is added unstyled here and receives its .lyrx in
        # postExecute, once the output is fully committed to the map.
        arcs.lyr.add(active_map, state_boundaries, lyr_name="States")
    else:
        # Add without symbology overrides.
        arcs.lyr.add(active_map, census_lite, lyr_name="Counties")
        arcs.lyr.add(active_map, state_boundaries, lyr_name="States")
        arcs.lyr.add(active_map, region_boundary, lyr_name="Region")

    return
```

`execute` no longer references any `.lyrx` file. Counties and Region are styled inline through `simple_sym` by passing fill and stroke arguments straight to `arcs.lyr.add`, so no file path is needed here. The only `.lyrx` left in the tool belongs to the States layer, and it is applied in `postExecute`. That is where `tool_dir = Path(__file__).parent` now lives: it resolves to the folder containing the `.pyt` file at runtime and is used to build the path to `state_boundary.lyrx`. The `from pathlib import Path` line at the top of the file makes this available.

```python
    lyr = active_map.addDataFromPath(census_lite)
    lyr.name = "Counties"
    sym = lyr.symbology
    sym.renderer.symbol.color = {"RGB": [235, 250, 235, 100]}
    sym.renderer.symbol.outlineColor = {"RGB": [110, 110, 110, 100]}
    sym.renderer.symbol.outlineWidth = 0.7
    lyr.symbology = sym
```

`arcs.lyr.add` with style arguments collapses that into one call. For three layers, that is many lines of boilerplate replaced by three.

**Layer order in the Contents pane:** The order in which layers appear in the Contents pane is determined by ArcGIS Pro based on geometry type. Polygon layers typically appear below point layers regardless of the order they are added. When mixing geometry types or when a specific visual stacking order is needed, the layers can be rearranged programmatically using `arcs.lyr.get` to retrieve the layer objects and `active_map.moveLayer` to reposition them. For this tool, all three outputs are polygons, so the order is predictable.

Counties and Region are styled inline here with `simple_sym`, so neither needs a `.lyrx` file. States is added unstyled and receives its complex `.lyrx` symbology in `postExecute`. The next section explains why.

---

## postExecute: Applying Symbology After Outputs Are Ready

`postExecute` runs after `execute` completes and after ArcGIS has finished adding all outputs to the Contents pane.

The States layer carries the only complex symbology in this tool: a `.lyrx` symbol that draws a dashed line over a solid white backing. Applying that kind of layered symbology inside `execute` can produce unexpected results. Complex renderers often need to inspect the actual output already present in the map to resolve correctly; a unique value renderer, for example, reads the values in the output feature class to build its category list. If the `.lyrx` is applied through `arcpy.mp` before ArcGIS has fully committed the output to the map, that inspection may fail silently, producing a layer that appears on the map with no visible style, no error, and no indication of what went wrong. Applying the `.lyrx` in `postExecute` avoids this because all outputs are fully committed and accessible before the method is called.

It is important to understand that `postExecute` always fails silently. Any Python exception raised inside it is suppressed by ArcGIS and produces no message to the user. There is no way around this. What ArcSmith provides is not error surfacing but reliability through simplicity. Without ArcSmith, applying symbology through `arcpy.mp` requires getting the project, getting the active map, iterating layers to find the right one, loading the `.lyrx` file, extracting the symbology from it, and assigning it to the layer. Each of those steps can fail without raising an obvious error, and the more steps there are, the more places something can go silently wrong. `arcs.lyr.apply_lyrx` wraps the entire sequence into one call, reducing the number of things that can go wrong to a minimum.

```python
def postExecute(self, parameters):

    apply_sym = parameters[7].value

    tool_dir  = Path(__file__).parent

    if apply_sym:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap

        # Apply the complex .lyrx symbology to the States layer now that it
        # is committed to the map.
        arcs.lyr.apply_lyrx(
            tool_dir / "lyrx" / "state_boundary.lyrx",
            target_map=active_map,
            lyr_name="States",
        )

    return
```

`arcs.lyr.apply_lyrx` finds every layer in the Contents pane whose TOC name matches `"States"` and applies the symbology from the `.lyrx` file to each one.

---

## Symbology on a Single-Output Tool: An Alternative Approach

Since this tool produces multiple outputs, it is more convenient for the user to set a single output location rather than save each feature class individually. If the tool produced only one output, it would make more sense to expose that output as a proper `Derived` output parameter and attach symbology directly to it.

Here is what that looks like:

```python
p_out = arcpy.Parameter(
    displayName="Output Feature Class",
    name="output_fc",
    datatype="DEFeatureClass",
    parameterType="Derived",   # Produced by the tool, not entered by the user
    direction="Output",
)
p_out.symbology = r"C:\source_files\lyrx\my_style.lyrx"
```

Setting `parameterType="Derived"` tells ArcGIS that the output is produced by the tool. Setting `.symbology` to a `.lyrx` path tells ArcGIS to apply that style when the output is added to the map.

This approach works well for simple symbology: a single fill color, a single stroke style, or any renderer that does not need to read field values to build class breaks. For anything more complex, unexpected results can occur. A unique value renderer attached at the parameter level may regroup values differently than expected, produce duplicate symbols, or fall back to a default style when the output data does not match the categories baked into the `.lyrx` file. In those cases, `arcs.lyr.apply_lyrx` in `postExecute` is the more reliable path. It applies symbology after the data exists, at the right moment in the lifecycle, with clear feedback if something goes wrong.

---

## Complete Tool File

```python
# -*- coding: utf-8 -*-

import arcpy
import arcsmith as arcs
from pathlib import Path


class Toolbox:
    def __init__(self):
        self.label = "Census Tutorial Toolbox"
        self.alias = "censustutorial"
        self.tools = [CensusRegions]


class CensusRegions:
    def __init__(self):
        self.label = "Census Regions"
        self.description = (
            "Filter US Census county data to selected states, "
            "trim fields, and produce county, state, and region boundary layers."
        )

    def getParameterInfo(self):
        p_00 = arcpy.Parameter(
            displayName="National County Feature Class",
            name="county_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
        )
        # p_00.value = r"C:\source_files\census_tutorial.gdb\CensusCounties"

        p_01 = arcpy.Parameter(
            displayName="State Name Field",
            name="state_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
        )
        p_01.parameterDependencies = ["county_fc"]
        p_01.filter.list = ["Text"]
        # p_01.value = "ST_STUSPS"

        p_02 = arcpy.Parameter(
            displayName="States to Include",
            name="states",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )

        p_03 = arcpy.Parameter(
            displayName="Fields to Keep",
            name="fields_to_keep",
            datatype="Field",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
        )
        p_03.parameterDependencies = ["county_fc"]

        p_04 = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="output_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )

        p_05 = arcpy.Parameter(
            displayName="Add Results Prefix",
            name="add_prefix",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p_05.value = False

        p_06 = arcpy.Parameter(
            displayName="Output Prefix",
            name="output_prefix",
            datatype="GPString",
            parameterType="Optional",
            direction="Input",
        )

        p_07 = arcpy.Parameter(
            displayName="Apply Symbology",
            name="apply_symbology",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        p_07.value = True

        params = [p_00, p_01, p_02, p_03, p_04, p_05, p_06, p_07]
        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        fc_in           = parameters[0]
        state_field     = parameters[1]
        selected_states = parameters[2]
        add_prefix      = parameters[5]
        output_prefix   = parameters[6]

        if fc_in.value:
            fc_in_path = arcs.param.to_path(fc_in)
            arcs.param.cascade_clear(state_field, [selected_states])

            if arcs.param.state(state_field) in ("pending", "settled") and state_field.value:
                states = arcs.flds.unique_values(fc_in_path, state_field.valueAsText)
                arcs.param.drop_populate(selected_states, states)

        arcs.param.checkbox_dependence(add_prefix, output_prefix, hidden_value=None)

        return

    def updateMessages(self, parameters):
        fc_in          = parameters[0]
        fields_to_keep = parameters[3]

        if fc_in.value and not fields_to_keep.value:
            fields_to_keep.setWarningMessage(
                "No fields selected. The output will contain geometry only."
            )
        return

    def execute(self, parameters, messages):
        fc_in_path    = arcs.param.to_path(parameters[0])
        state_field   = parameters[1].valueAsText
        states_list   = parameters[2].valueAsText.split(";")
        out_gdb       = parameters[4].valueAsText
        add_prefix    = parameters[5].value
        output_prefix = parameters[6].valueAsText
        apply_sym     = parameters[7].value

        fields_raw  = parameters[3].valueAsText
        fields_list = fields_raw.split(";") if fields_raw else None

        prefix = f"{output_prefix}_" if add_prefix else ""

        where_states = arcs.fc.build_where_in(fc_in_path, state_field, states_list)

        census_lite = arcs.fc.export_fc(
            fc_in_path,
            f"{out_gdb}/{prefix}census_lite",
            fields_list,
            keep=True,
            where_clause=where_states,
        )

        state_boundaries = str(arcpy.management.Dissolve(
            census_lite,
            f"{out_gdb}/{prefix}state_boundaries",
            state_field,
        ))

        region_boundary = str(arcpy.management.Dissolve(
            census_lite,
            f"{out_gdb}/{prefix}region_boundary",
        ))

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap

        if apply_sym:
            arcs.lyr.add(
                active_map, census_lite,
                lyr_name="Counties",
                fill_color="#EBFAEB", stroke_color="#6E6E6E", stroke_width=0.7,
            )
            arcs.lyr.add(
                active_map, region_boundary,
                lyr_name="Region",
                fill_opacity=0, stroke_color="#000000", stroke_width=2.5,
            )
            arcs.lyr.add(active_map, state_boundaries, lyr_name="States")
        else:
            arcs.lyr.add(active_map, census_lite, lyr_name="Counties")
            arcs.lyr.add(active_map, state_boundaries, lyr_name="States")
            arcs.lyr.add(active_map, region_boundary, lyr_name="Region")

        return

    def postExecute(self, parameters):
        apply_sym = parameters[7].value

        tool_dir = Path(__file__).parent

        if apply_sym:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap

            arcs.lyr.apply_lyrx(
                tool_dir / "lyrx" / "state_boundary.lyrx",
                target_map=active_map,
                lyr_name="States",
            )

        return
```

---

## Running the Tool

1. Open ArcGIS Pro and connect to the `source_files/` folder in the Catalog pane.
2. Right-click `census_tutorial.gdb` and choose **Add To Current Map** to make `CensusCounties` available in the map.
3. Right-click `census_tutorial.pyt` and choose **Refresh**.
4. Expand the toolbox and double-click **Census Regions**.
5. Set **National County Feature Class** to the `CensusCounties` layer. The **State Name Field** dropdown's list of text fields will populate automatically, with nothing selected yet.
6. Set **State Name Field** to `ST_STUSPS`, then click into the **States to Include** field. The checklist should populate with state abbreviations from the data.
7. Pick the desired states.
8. In **Fields to Keep**, select `NAMELSAD` and `ST_STUSPS`. Leaving this blank will produce geometry-only output and display a warning once the feature class is set.
9. Set **Output Geodatabase** to an existing `.gdb`.
10. Optionally check **Add Results Prefix** and type a short prefix.
11. Leave **Apply Symbology** checked, then click **Run**.

---

## What Each Output Contains

| Layer | How it is produced | Contents |
|---|---|---|
| `census_lite` | Filtered copy of CensusCounties | County polygons for the selected states, trimmed to chosen fields |
| `state_boundaries` | Dissolve by state field | One polygon per state, county boundaries dissolved away |
| `region_boundary` | Full dissolve | Single polygon covering all selected states combined |

---

## ArcSmith Functions Used in This Tutorial

| Function | What it does |
|---|---|
| `arcs.param.to_path(param)` | Resolves a parameter to its absolute catalog path, safe for map-layer inputs |
| `arcs.param.state(param)` | Returns `'fresh'`, `'pending'`, `'settled'`, or `'confirmed'` for a parameter |
| `arcs.param.cascade_clear(trigger, dependents)` | Clears dependent parameters when the trigger changes |
| `arcs.param.drop_populate(param, values)` | Sets a dropdown filter list from a Python list |
| `arcs.param.checkbox_dependence(checkbox, dependents)` | Enables and disables dependent parameters based on a checkbox |
| `arcs.flds.unique_values(fc, field)` | Returns sorted unique values present in a field |
| `arcs.fc.build_where_in(fc, field, values)` | Builds a SQL `IN` clause for a list of values |
| `arcs.fc.export_fc(fc, output, fields, keep, where_clause)` | Exports a feature class with field and row filters in one call |
| `arcs.lyr.add(map, src, lyr_name, ...)` | Adds a data source to a map, optionally applying inline style arguments or a `.lyrx` file |
| `arcs.lyr.simple_sym(lyr, fill_color, stroke_color, stroke_width)` | Applies simple fill and stroke symbology to a layer inline, with no `.lyrx` file |
| `arcs.lyr.apply_lyrx(lyrx, target_map=map, lyr_name=...)` | Applies symbology from a `.lyrx` file to a layer object or to named layers in the map |
| `arcs.lyr.get(map, lyr_name=...)` | Retrieves layer objects from the map by name for repositioning or inspection |

<br><br><br><br><br>