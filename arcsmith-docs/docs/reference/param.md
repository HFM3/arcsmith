<div class="as-hero" markdown>
<div class="as-hero__eyebrow">arcsmith.param</div>
<h2 class="as-hero__title">Parameter</h2>
<p class="as-hero__sub">Helpers for managing 'arcpy.Parameter' state and validation in a tool's 'updateParameters' and 'updateMessages' functions.</p>
<ul class="as-hero__highlights">
<li>Create dynamic ArcPy toolboxes that respond to user input</li>
<li>Automatically reset specified parameters following a change to an upstream value</li>
<li>Populate parameters and dropdowns with contextual content</li>
<li>Guide users with timely, self-clearing validation messages instead of premature errors</li>
</ul>
</div>

## Functions of the `param` module

## state

Translates a parameter's `altered` + `hasBeenValidated` flags into a single readable state.

```python
state(param: arcpy.Parameter) -> str
```

| State       | `.altered` | `.hasBeenValidated` | Description                  |
|-------------|:----------:|:-------------------:|------------------------------|
| `fresh`     | `False`    | `False`             | Initial, untouched state     |
| `pending`   | `True`     | `False`             | Changed, awaiting validation |
| `settled`   | `False`    | `True`              | Validated, not changed since |
| `confirmed` | `True`     | `True`              | Changed and validated        |

!!! tip
    `'pending'` is the most important state to detect. It marks the exact moment a value was _**just**_ changed and marks the right time to reset or re-populate dependent parameters.


**Example**

```python
# React only the moment a value changes
if arcsmith.param.state(parameters[0]) == 'pending':
    parameters[1].value = None
```

---

## require

Flags a parameter that must be filled in before the tool can run. Use it for an `Optional` parameter made mandatory by another choice. It is self-clearing: the prompt disappears the moment the user supplies a value or the condition turns off, so it is safe to call on every `updateMessages` pass.

```python
require(param, when=True, message=None, *, block=True) -> None
```

| Parameter | Type                              | Default  | Description                                                                                                          |
|-----------|-----------------------------------|----------|--------------------------------------------------------------------------------------------------------------------|
| `param`   | `arcpy.Parameter` or list         | required | Parameter(s) to check. A single parameter may be passed without a list.                                            |
| `when`    | `bool`                            | `True`   | The condition under which a value is required, computed by the caller (e.g. `area_type.valueAsText == "Polygon"`). |
| `message` | `str` or list of `str`            | `None`   | Message to show. `None` auto-generates a prompt per parameter from its `displayName`. A single string applies to all; a list maps one-to-one. |
| `block`   | `bool`                            | `True`   | Keyword-only. `True` sets a blocking error; `False` a non-blocking warning.                                        |

!!! success "Returns"
    `None`.

!!! note "Conditional parameters only"
    Do not use `require` for parameters declared `parameterType="Required"`. ArcGIS already flags those when empty, so a second message would duplicate it. This helper is for the conditional case ArcGIS cannot know about.

!!! tip "One message per parameter"
    An `arcpy.Parameter` has a single message slot, so each parameter's message must be owned by one helper call. Do not stack a second message helper on the same parameter, or one call's clear will wipe the other. For a parameter with several failure modes, compute one message and use a single [`flag`](#flag).

!!! warning "Validators vs. placeholder values"
    `require` treats a parameter as filled when `value is not None`. [`checkbox_dependence`](#checkbox_dependence) and [`dynamic_dropdown`](#dynamic_dropdown) can assign a non-`None` `hidden_value` / `shown_value` placeholder (e.g. `"N/A"`, `0`) to keep a parameter satisfied while inactive. That value then reads as *filled* here, so `require` never prompts for it. These are opposite tools chosen by the parameter's declared type: pacify a **Required** param with a placeholder (it behaves optional while inactive); flag an **Optional** param with `require` (it behaves required when needed). Use only one per parameter.

!!! failure "Raises"
    `ValueError` if `message` is a list whose length differs from `param`.

**Examples**

```python
# Require a field only when a checkbox is on
arcsmith.param.require(filter_field, when=use_filter.value)

# Require an input for a selected mode, with a custom message
arcsmith.param.require(area_polygon, when=area_type.valueAsText == "Polygon",
                       message="Choose the polygon to use as the area.")

# Non-blocking nudge instead of an error
arcsmith.param.require(id_field, when=calc_pairs.value, block=False)
```

---

## require_one_of

Flags a group of parameters when at least one of them must be filled (an either/or input). When the condition holds and every parameter is empty, each is flagged; as soon as one is filled, all clear.

```python
require_one_of(params, when=True, message=None, *, block=True) -> None
```

| Parameter | Type                      | Default  | Description                                                                                  |
|-----------|---------------------------|----------|---------------------------------------------------------------------------------------------|
| `params`  | list of `arcpy.Parameter` | required | The group, at least one of which must have a value.                                         |
| `when`    | `bool`                    | `True`   | Condition under which one is required, computed by the caller.                              |
| `message` | `str`                     | `None`   | Message shown on each parameter while none is filled. `None` auto-generates a prompt listing the display names. |
| `block`   | `bool`                    | `True`   | Keyword-only. `True` sets blocking errors; `False` non-blocking warnings.                   |

!!! success "Returns"
    `None`.

!!! note "Placeholder values satisfy the group"
    The group counts as satisfied as soon as one parameter is not `None`, so a non-`None` `hidden_value` / `shown_value` placeholder set by [`checkbox_dependence`](#checkbox_dependence) / [`dynamic_dropdown`](#dynamic_dropdown) would satisfy it on its own. Validate **Optional** params with this helper; pacify **Required** ones with a placeholder instead. See [`require`](#require).

**Examples**

```python
# Require either a polygon or a manual area value
arcsmith.param.require_one_of([area_polygon, area_value])

# Custom message, only while a checkbox is on
arcsmith.param.require_one_of([field_a, field_b], when=use_fields.value,
                              message="Pick at least one field.")
```

---

## flag

Shows a self-clearing message on a parameter while a condition holds. It is the general companion to `require`/`require_one_of` for value-semantic checks (wrong geometry, out-of-range number, bad format, too few features). The caller computes `when` and supplies the message.

```python
flag(param, when, message, *, block=True) -> None
```

| Parameter | Type                      | Default  | Description                                                                                  |
|-----------|---------------------------|----------|---------------------------------------------------------------------------------------------|
| `param`   | `arcpy.Parameter` or list | required | Parameter(s) to flag. A single parameter may be passed without a list.                      |
| `when`    | `bool`                    | required | The problem condition. The message shows when this is `True` and clears when `False`.       |
| `message` | `str` or list of `str`    | required | Message to show. A single string applies to all; a list maps one-to-one.                    |
| `block`   | `bool`                    | `True`   | Keyword-only. `True` sets a blocking error; `False` a non-blocking warning.                 |

!!! success "Returns"
    `None`.

!!! tip "Guard value checks"
    Guard a value-semantic check so it only runs once the value exists: `when=bool(param.value) and not <is_valid>`. As with `require`, one helper owns each parameter's message. Note a non-`None` `hidden_value` / `shown_value` placeholder from [`checkbox_dependence`](#checkbox_dependence) / [`dynamic_dropdown`](#dynamic_dropdown) makes `bool(param.value)` true, so the guard passes on a placeholder.

!!! failure "Raises"
    `ValueError` if `message` is a list whose length differs from `param`.

**Examples**

```python
# Check geometry type once a polygon is provided (composes with validate_geom_type)
arcsmith.param.flag(
    area_polygon,
    when=bool(area_polygon.value)
    and not arcsmith.fc.validate_geom_type(arcsmith.param.to_path(area_polygon), "Polygon"),
    message="Input must be a polygon.")

# Non-blocking warning on a suspicious value
arcsmith.param.flag(buffer_dist,
                    when=bool(buffer_dist.value) and buffer_dist.value > 1000,
                    message="That is a very large buffer.", block=False)
```

---


## cascade_populate

Assigns a specific value to downstream parameters. Useful when a required downstream parameter needs to hold a concrete placeholder rather than be left empty.

```python
cascade_populate(trigger_param, downstream_params, value=None) -> None
```

| Parameter           | Type                                           | Default  | Description                                                                                                                    |
|---------------------|------------------------------------------------|----------|--------------------------------------------------------------------------------------------------------------------------------|
| `trigger_param`     | `arcpy.Parameter`                              | required | The parameter whose change triggers the cascade.                                                                               |
| `downstream_params` | `arcpy.Parameter` or list of `arcpy.Parameter` | required | Parameter(s) to set when `trigger_param` is `'pending'` or `'fresh'`. A single parameter may be passed without a list.         |
| `value`             | scalar or list                                 | `None`   | Value assigned to each downstream parameter. A scalar is broadcast to all; a list maps one-to-one. Default `None` clears them. |

!!! note
    Safe to call unconditionally on every `updateParameters` pass. If `trigger_param` is not `'pending'` or `'fresh'` the call is a no-op.

!!! failure "Raises"
    `ValueError` if `value` is a list whose length differs from `downstream_params`.

**Examples**

```python

# Reset all dependents to the same concrete value
arcsmith.param.cascade_populate(parameters[0], [parameters[1], parameters[2]], value=100)

# Reset each dependent to a different value
arcsmith.param.cascade_populate(parameters[0],
                                [parameters[1], parameters[2]],
                                value=["Visits", 3000])

# Reset all dependents to the default: None
# (cascade_clear performs the same operation)
arcsmith.param.cascade_populate(parameters[0], [parameters[1], parameters[2]])
```

---

## cascade_clear

Clears downstream parameters the moment an upstream value changes.

```python
cascade_clear(trigger_param, downstream_params) -> None
```

| Parameter           | Type                                           | Default  | Description                                                           |
|---------------------|------------------------------------------------|----------|-----------------------------------------------------------------------|
| `trigger_param`     | `arcpy.Parameter`                              | required | The parameter whose change triggers the cascade.                      |
| `downstream_params` | `arcpy.Parameter` or list of `arcpy.Parameter` | required | Parameters to clear when `trigger_param` is `'pending'` or `'fresh'`. |

!!! note "Fires on both _unvalidated_ states: `'fresh'` and `'pending'`"
    `cascade_clear` fires on both states so that clearing, resetting, *or* changing an upstream value reliably resets its dependents.

**Examples**

```python
# Clear a single downstream parameter
arcsmith.param.cascade_clear(parameters[0], parameters[1])

# Clear multiple downstream parameters at once
arcsmith.param.cascade_clear(parameters[0], [parameters[1], parameters[2]])
```

---

## drop_populate

Fills a parameter's dropdown list. Call this every `updateParameters` pass whenever the options depend on an upstream value. `drop_populate` is a no-op if the dropdown list hasn't changed and won't overwrite anything the user has already selected.

```python
drop_populate(param, values, default=None, overwrite_empty=False, none_label=None) -> None
```

| Parameter         | Type              | Default  | Description                                                                                                                                                                                              |
|-------------------|-------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `param`           | `arcpy.Parameter` | required | The parameter to populate with a dropdown.                                                                                                                                                               |
| `values`          | list              | required | Options to display in the dropdown. Non-string values are coerced to `str` automatically. `None` entries are dropped unless `none_label` is provided.                                                    |
| `default`         | `str`             | `None`   | Value to pre-select after the filter list is set. Only applied while the parameter is `'fresh'` or `'settled'` so existing user input is never overwritten. Ignored when the filter list is not updated. |
| `overwrite_empty` | `bool`            | `False`  | If `True`, updates the filter even when `values` is empty. Use this to clear a stale list when an upstream value is removed.                                                                             |
| `none_label`      | `str`             | `None`   | If provided, `None` entries in `values` are replaced with this string rather than dropped. Note that selecting this label and passing it to `arcsmith.fc.build_where` will not produce a valid `IS NULL` clause. Handle that case separately. |

!!! note
    Passing an empty `values` list is silently ignored by default. This prevents wiping a valid dropdown when the upstream feature class parameter hasn't been set yet on tool open.

!!! note "Null values"
    `None` entries are dropped silently by default since arcpy's `ValueList` filter requires strings and null is rarely a meaningful selectable option. Pass `none_label="(No value)"` if the user needs to be able to select null explicitly, and handle that sentinel separately before passing the value to `build_where`.

**Examples**

```python
# Populate dropdown options and pre-select a sensible default
arcsmith.param.drop_populate(
    parameters[1],
    ["Lake McDonald Lodge", "East Glacier Lodge", "St. Mary Lake Boats"],
    default="Lake McDonald Lodge",
)

# Explicitly clear a stale dropdown when the upstream value is removed
arcsmith.param.drop_populate(parameters[1], [], overwrite_empty=True)

# Fill a dropdown with unique field values. None entries and non-strings
# are handled automatically; no manual coercion needed at the call site
values = arcsmith.flds.unique_values(input_fc, "TRAIL_STATUS")
arcsmith.param.drop_populate(parameters[1], values)

# Common pattern: clear the dropdown when the feature class changes,
# then refill it if a feature class is currently set
arcsmith.param.cascade_clear(parameters[0], parameters[1])
arcsmith.param.drop_populate(
    parameters[1],
    arcsmith.flds.list_cols(parameters[0].valueAsText)
    if parameters[0].valueAsText else [],
    overwrite_empty=True,
)
```

---

## checkbox_dependence

Shows, hides, and seeds dependent parameters based on a controlling checkbox. Parameters are disabled while the checkbox is unchecked, enabled the moment it's checked, and left alone on every subsequent pass so that the user's input isn't overwritten.

```python
checkbox_dependence(
    controlling_checkbox,
    dependents,
    hidden_value=None,
    shown_value=None,
    auto_hide_dependents=True
) -> None
```

| Parameter              | Type                                           | Default  | Description                                                                                                                                                                 |
|------------------------|------------------------------------------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `controlling_checkbox` | `arcpy.Parameter`                              | required | Checkbox that drives the state of all dependents.                                                                                                                           |
| `dependents`           | `arcpy.Parameter` or list of `arcpy.Parameter` | required | Parameter(s) to control. A single parameter may be passed without a list.                                                                                                   |
| `hidden_value`         | scalar or list                                 | `None`   | Value(s) assigned while dependents are **inactive** (checkbox unchecked). A scalar broadcasts to all; a list maps one-to-one. Applied regardless of `auto_hide_dependents`. |
| `shown_value`          | scalar or list                                 | `None`   | Value(s) assigned the moment dependents are **first shown** (checkbox just checked). Same scalar/list rules.                                                                |
| `auto_hide_dependents` | `bool`                                         | `True`   | If `True`, dependents are not visible while the controlling checkbox is unchecked.                                                                                          |

!!! note "Autohide for tool development"
    Set to false `False` during tool development to interact with each dependent parameter regardless of controlling checkbox state.

| Checkbox state                          | Effect                                              |
|-----------------------------------------|-----------------------------------------------------|
| Unchecked, `auto_hide_dependents=True`  | `hidden_value` assigned; dependents disabled.       |
| Unchecked, `auto_hide_dependents=False` | `hidden_value` assigned; dependents remain enabled. |
| Just checked (`'pending'`), genuine toggle | `shown_value` assigned to empty dependents; dependents enabled. |
| `'pending'` on a history re-run         | No value seeded; dependents enabled. Saved values **and deliberate clears** are preserved. |
| Otherwise (stable)                      | No-op. Existing user input is preserved.            |

!!! tip "History re-runs are handled automatically"
    Re-opening a tool from its run history reloads the checkbox as `'pending'` even though the user never toggled it. `checkbox_dependence` recognizes that pass (the dependents reload unvalidated) and skips seeding, so a dependent the user **deliberately cleared** before running comes back clear instead of being re-seeded with `shown_value`. No extra work is required at the call site.

!!! note "Placeholder values and the validation helpers"
    A non-`None` `hidden_value` / `shown_value` placeholder keeps a parameter satisfied while inactive, but it also reads as *filled* to [`require`](#require) / [`require_one_of`](#require_one_of) / [`flag`](#flag) (which test `value is None`). Pacify **Required** params with a placeholder, and validate **Optional** ones with `require`. Do not use both on the same parameter.

!!! failure "Raises"
    `ValueError` if `hidden_value` or `shown_value` is a list whose length differs from `dependents`.

**Examples**

```python
# The simplest case: disable dependents when unchecked, enable when checked
arcsmith.param.checkbox_dependence(parameters[0], [parameters[1], parameters[2]])

# Keep dependent parameters satisfied with a placeholder
# value while inactive by using the hidden_value argument
arcsmith.param.checkbox_dependence(
    parameters[0],
    [parameters[1], parameters[2]],
    hidden_value=-999,
)

# Seed a starting value when the checkbox is first checked
arcsmith.param.checkbox_dependence(
    parameters[0],
    parameters[1],
    hidden_value=0,
    shown_value=100,
)

# Different hidden and shown values per dependent
arcsmith.param.checkbox_dependence(
    parameters[0],
    [parameters[1], parameters[2]],
    hidden_value=["Empty/Path", -999],
    shown_value=["", 1],
)

# Keep dependents visible while testing (hidden_value is still applied)
arcsmith.param.checkbox_dependence(
    parameters[0],
    [parameters[1], parameters[2]],
    hidden_value=-999,
    auto_hide_dependents=False,
)
```

---

## dynamic_dropdown

Dynamically enables/disables parameters based on what's selected in dropdown. Each option in the dropdown maps to a group of parameters; when that option is selected its group is enabled and all other groups are disabled.

```python
dynamic_dropdown(
    controlling_dropdown,
    option_map,
    hidden_value_map=None,
    shown_value_map=None,
    auto_hide_dependents=True
) -> None
```

| Parameter              | Type                                                            | Default  | Description                                                                                                                                                                                                                                                 |
|------------------------|-----------------------------------------------------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `controlling_dropdown` | `arcpy.Parameter`                                               | required | The parameter whose value controls which dependent parameter group is active.                                                                                                                                                                               |
| `option_map`           | dict of `str` to `arcpy.Parameter` or list of `arcpy.Parameter` | required | Maps each dropdown option to the dependent parameters that will be enabled when that option is selected. A single parameter may be passed without wrapping it in a list.                                                                                    |
| `hidden_value_map`     | dict of `str` to scalar or list                                 | `None`   | Values assigned to an option's dependent parameters while that group is **inactive**. Applied regardless of `auto_hide_dependents`. Per key: a scalar broadcasts to all parameters in that group; a list maps one-to-one. Missing keys fall back to `None`. |
| `shown_value_map`      | dict of `str` to scalar or list                                 | `None`   | Values assigned to an option's dependent parameters the moment the option is selected. Same per-key rules as `hidden_value_map`. Missing keys fall back to `None`.                                                                                          |
| `auto_hide_dependents` | `bool`                                                          | `True`   | If `True`, dependents are not visible while dropdown options is not selected.                                                                                                                                                                               |

!!! note "Autohide for tool development"
    Set to `False` during tool development to interact with each dependent parameter regardless of controlling dropdown's selected option.

| Dropdown state                               | Effect                                                 |
|----------------------------------------------|--------------------------------------------------------|
| Inactive group, `auto_hide_dependents=True`  | `hidden_value_map` applied; group disabled.            |
| Inactive group, `auto_hide_dependents=False` | `hidden_value_map` applied; group remains enabled.     |
| Active group, just selected (`'pending'`), genuine change | `shown_value_map` applied to empty params; group enabled. |
| Active group, `'pending'` on a history re-run | No value seeded; group enabled. Saved values **and deliberate clears** preserved. |
| Active group, stable                         | No-op; existing user input preserved. Group enabled.   |

!!! tip "History re-runs are handled automatically"
    Re-opening a tool from its run history reloads the dropdown as `'pending'` and its active group with the saved values. That pass is recognized (the group's params reload unvalidated) and seeding is skipped, so values the user cleared before running stay cleared instead of being re-seeded from `shown_value_map`. No extra work is required at the call site.

!!! note
    Length checks run for **every** option up front, so a misconfigured `hidden_value_map` or `shown_value_map` entry is caught immediately - even when that option isn't currently selected.

!!! note "Placeholder values and the validation helpers"
    A non-`None` `hidden_value_map` / `shown_value_map` placeholder keeps a parameter satisfied while its group is inactive, but it also reads as *filled* to [`require`](#require) / [`require_one_of`](#require_one_of) / [`flag`](#flag) (which test `value is None`). Pacify **Required** params with a placeholder, and validate **Optional** ones with `require`. Do not use both on the same parameter.

[//]: # (!!! note "Seeding values for populated dropdowns")

[//]: # (    When a dependent parameter's filter list is managed by `drop_populate`, don't use `drop_populate`'s `default` argument. Use `shown_value_map` here instead. `dynamic_dropdown` always has the final say over a managed parameter's value.)

    ```python
    # drop_populate owns the filter list; dynamic_dropdown owns the selected value
    arcsmith.param.drop_populate(parameters[4], ["Rectangle by Area", "Convex Hull", "Envelope"])

    arcsmith.param.dynamic_dropdown(
        parameters[1],
        option_map={"Minimum Bounding Geometry": [parameters[4]], ...},
        shown_value_map={"Minimum Bounding Geometry": ["Envelope"], ...},
    )
    ```

!!! failure "Raises"
    `ValueError` if any `hidden_value_map` or `shown_value_map` list length differs from its `option_map` counterpart.

**Examples**

```python
# Show a different parameter for each input type
arcsmith.param.dynamic_dropdown(
    parameters[0],
    option_map={
        # when "Shapefile" is selected in dropdown,
        # 'parameters[1]' is enabled. Dependents of other options are disabled.
        "Shapefile": parameters[1],
        # when "Feature Class" is selected in dropdown,
        # 'parameters[2]+[3]' are enabled. Dependents of other options are disabled.
        "Feature Class": [parameters[2], parameters[3]]
    }
)

# Seed a starting value when an option is selected,
# and fill inactive groups with a placeholder value
arcsmith.param.dynamic_dropdown(
    parameters[0],
    option_map={
        "Shapefile": [parameters[1]],
        "Feature Class": [parameters[2], parameters[3]],
    },
    shown_value_map={
        "Shapefile": [""],  # start p1 as an empty string
        "Feature Class": ["N/A", 0],  # one value per parameter in the group
    },
    hidden_value_map={
        "Feature Class": "N/A"  # scalar broadcasts to all dependents (p2 and p3)
    }
)

# Only seed one option; the other starts unset
arcsmith.param.dynamic_dropdown(
    parameters[0],
    option_map={
        "Shapefile":     parameters[1],
        "Feature Class": [parameters[2], parameters[3]],
    },
    shown_value_map={
        "Shapefile": ""  # "Feature Class" omitted, therefore its params start as None by default
    }
)

# Keep all groups visible while testing
arcsmith.param.dynamic_dropdown(parameters[0], option_map, auto_hide_dependents=False)
```

---

## to_path

Resolves a feature class or layer parameter to its real catalog path. Use this in `execute` instead of `param.valueAsText` whenever the user might select from the map TOC rather than browse to a file.
```python
to_path(param: arcpy.Parameter) -> str
```

!!! success "Returns"
    `str`: absolute catalog path to the data source.

!!! note "Why not `valueAsText`?"
    `valueAsText` returns whatever is shown in the tool dialog. When a user picks an existing map layer, that's the layer's TOC name (e.g. `"Trails 2024"`), not a path arcpy can open. `param_to_path` calls `arcpy.Describe` on the parameter value and returns `catalogPath` which is always an absolute, resolvable path.

    Use `Path(param.valueAsText)` only for parameters typed as plain file paths, such as an output folder or a `.lyrx` file.

**Examples**

```python
# Resolve a feature class parameter before passing it to other ArcSmith functions
fc_path = arcsmith.param.to_path(parameters[0])
clause = arcsmith.fc.build_where(fc_path, "TRAIL_STATUS", "Open")
out = arcsmith.fc.export_fc(fc_path, output_fc, ["TRAIL_ID", "MAINTAINER", "TRAIL_STATUS"],
                                    where_clause=clause)

# Resolve in updateParameters to drive a downstream field dropdown
fc_path = arcsmith.param.to_path(parameters[0])
arcsmith.param.drop_populate(parameters[1], arcsmith.flds.list_cols(fc_path))
```

<br><br><br><br><br>