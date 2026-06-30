# ArcSmith: GIS toolbox utilities
# Copyright (c) 2026 @HFM3 (https://github.com/HFM3)
# SPDX-License-Identifier: MIT

from __future__ import annotations

import arcpy
from typing import Any, Optional, Union
from pathlib import Path


__all__ = ["state",
           "require",
           "require_one_of",
           "flag",
           "cascade_clear",
           "cascade_populate",
           "drop_populate",
           "checkbox_dependence",
           "dynamic_dropdown",
           "to_path"]


def _broadcast(value: Any, length: int, value_label: str = "value",
               length_label: str = "items") -> list:
    """
    Normalize ``value`` into a list of ``length`` entries.

    A scalar (anything that is not a ``list``, including ``None``) is broadcast
    to every position. A list is returned unchanged after its length is checked.
    This is the shared "scalar-or-list, aligned to N parameters" rule used by the
    parameter helpers below.

    Parameters
    ----------
    value : scalar or list
        The value to broadcast or validate.
    length : int
        Required length of the returned list.
    value_label : str, optional
        Name of ``value`` used in the error message (e.g. ``'placeholder'``).
    length_label : str, optional
        Name of the thing ``length`` came from, used in the error message
        (e.g. ``'dependents'``).

    Returns
    -------
    list
        A list of exactly ``length`` entries.

    Raises
    ------
    ValueError
        If ``value`` is a list whose length differs from ``length``.

    Examples
    --------
    >>> _broadcast("N/A", 3)
    ['N/A', 'N/A', 'N/A']
    >>> _broadcast(["a", "b"], 2)
    ['a', 'b']
    """
    if isinstance(value, list):
        if len(value) != length:
            raise ValueError(
                f"{value_label} list length ({len(value)}) must match "
                f"{length_label} length ({length})."
            )
        return value
    return [value] * length


def state(param: arcpy.Parameter) -> str:
    """
    Return a string describing the combined ``altered``/``hasBeenValidated`` state of an ``arcpy.Parameter``.

    fresh -> param is unaltered and unvalidated (initial state).

    pending -> param has been altered but not yet validated.

    settled -> param is unaltered but has been validated.

    confirmed -> param has been altered and validated.

    Parameters
    ----------
    param : arcpy.Parameter
        The parameter to inspect.

    Returns
    -------
    str
        One of ``'fresh'``, ``'pending'``, ``'settled'``, ``'confirmed'``.

    Examples
    --------
    >>> state(p)
    'fresh'
    >>> state(p)
    'pending'
    """
    altered = param.altered
    validated = param.hasBeenValidated

    if not altered and not validated:
        return 'fresh'
    elif altered and not validated:
        return 'pending'
    elif not altered and validated:
        return 'settled'
    else:
        return 'confirmed'


def require(param: Union[arcpy.Parameter, list], when: bool = True,
            message: Optional[Union[str, list]] = None, *,
            block: bool = True) -> None:
    """
    Flag a parameter that must be filled in before the tool can run.

    Use this in ``updateMessages`` for a parameter that is required only under
    some condition (an ``Optional`` parameter made mandatory by another choice).
    When ``when`` is true and the parameter is empty a message is shown;
    otherwise the message is cleared. Because it clears itself, the prompt
    disappears the moment the user supplies a value or the condition turns off,
    and the call is safe to run on every ``updateMessages`` pass.

    Do not use this for parameters declared ``parameterType="Required"``: ArcGIS
    already flags those when empty, so a second message would duplicate it. This
    helper is for the conditional case ArcGIS cannot know about.

    Parameters
    ----------
    param : arcpy.Parameter or list of arcpy.Parameter
        The parameter(s) to check. A single parameter may be passed without a
        list.
    when : bool, optional
        The condition under which a value is required, computed by the caller
        (e.g. ``area_type.valueAsText == "Polygon"`` or ``checkbox.value``).
        Default ``True`` (always required).
    message : str or list of str, optional
        The message to show. Default ``None`` auto-generates a gentle prompt per
        parameter from its ``displayName``. A single string is applied to every
        parameter; a list is matched one-to-one and must match ``param`` in
        length.
    block : bool, optional
        Keyword-only. If ``True`` (default), the message is an error and blocks
        the tool from running (``setErrorMessage``). If ``False``, it is a
        non-blocking warning (``setWarningMessage``).

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If ``message`` is a list whose length differs from ``param``.

    Notes
    -----
    An ``arcpy.Parameter`` holds a single message, so each parameter's message
    should be owned by one helper call. Do not also set another message on the
    same parameter in the same pass, or this call's ``clearMessage`` will wipe it
    (or the reverse). For a parameter with more than one failure mode, compute a
    single message and use one ``flag`` call instead.

    ``require`` and placeholder values are two ends of one idea, chosen by a
    parameter's declared type. A *Required* parameter that is only sometimes
    relevant is kept satisfied with a non-``None`` ``hidden_value`` /
    ``shown_value`` placeholder (via ``checkbox_dependence`` /
    ``dynamic_dropdown``) so it behaves optional while inactive. An *Optional*
    parameter that is sometimes mandatory is flagged with ``require`` so it
    behaves required. Use only one per parameter: a placeholder is not ``None``,
    so ``require`` would read a pacified parameter as filled and never prompt.

    Examples
    --------
    Require a field only when a checkbox is on:

    >>> arcsmith.param.require(filter_field, when=use_filter.value)

    Require an input when a dropdown selects its mode, with a custom message:

    >>> arcsmith.param.require(area_polygon,
    ...                        when=area_type.valueAsText == "Polygon",
    ...                        message="Choose the polygon to use as the area.")

    Offer a non-blocking nudge instead of an error:

    >>> arcsmith.param.require(id_field, when=calc_pairs.value, block=False)
    """
    if not isinstance(param, list):
        param = [param]
    messages = _broadcast(message, len(param), "message", "param")

    for p, msg in zip(param, messages):
        if when and p.value is None:
            text = msg if msg is not None else (
                f"Provide a value for '{p.displayName}' before running the tool.")
            if block:
                p.setErrorMessage(text)
            else:
                p.setWarningMessage(text)
        else:
            p.clearMessage()


def require_one_of(params: list, when: bool = True,
                   message: Optional[str] = None, *,
                   block: bool = True) -> None:
    """
    Flag a group of parameters when at least one of them must be filled.

    Use this in ``updateMessages`` for an either/or input: when ``when`` is true
    and *every* parameter in ``params`` is empty, the message is shown on each
    one; as soon as any is filled (or the condition turns off) the messages
    clear. Like ``require`` it is self-clearing and safe to call every pass.

    Parameters
    ----------
    params : list of arcpy.Parameter
        The group of parameters, at least one of which must have a value.
    when : bool, optional
        The condition under which one is required, computed by the caller.
        Default ``True``.
    message : str, optional
        The message shown on each parameter while none is filled. Default
        ``None`` auto-generates a prompt listing the parameters' display names.
    block : bool, optional
        Keyword-only. If ``True`` (default), the messages are errors and block
        the run. If ``False``, they are non-blocking warnings.

    Returns
    -------
    None

    Notes
    -----
    The group counts as satisfied as soon as one parameter is not ``None``, so a
    non-``None`` ``hidden_value`` / ``shown_value`` placeholder set by
    ``checkbox_dependence`` / ``dynamic_dropdown`` would satisfy it on its own.
    Validate *Optional* parameters with this helper; pacify *Required* ones with a
    placeholder instead. See ``require`` for the full rationale.

    Examples
    --------
    Require either a polygon or a manual area value:

    >>> arcsmith.param.require_one_of([area_polygon, area_value])

    With a custom message, only while a checkbox is on:

    >>> arcsmith.param.require_one_of([field_a, field_b], when=use_fields.value,
    ...                               message="Pick at least one field.")
    """
    satisfied = any(p.value is not None for p in params)

    if when and not satisfied:
        if message is None:
            names = ", ".join(f"'{p.displayName}'" for p in params)
            message = f"Provide at least one of: {names}."
        for p in params:
            if block:
                p.setErrorMessage(message)
            else:
                p.setWarningMessage(message)
    else:
        for p in params:
            p.clearMessage()


def flag(param: Union[arcpy.Parameter, list], when: bool,
         message: Union[str, list], *, block: bool = True) -> None:
    """
    Show a self-clearing message on a parameter while a condition holds.

    The general-purpose companion to ``require``/``require_one_of``, for
    value-semantic checks: wrong geometry, an out-of-range number, a bad format,
    too few features, a cross-field rule. When ``when`` is true the message is
    set; otherwise it is cleared. The caller computes ``when`` and supplies the
    message; there is no auto-generated text.

    Parameters
    ----------
    param : arcpy.Parameter or list of arcpy.Parameter
        The parameter(s) to flag. A single parameter may be passed without a
        list.
    when : bool
        The problem condition, computed by the caller (e.g.
        ``not arcsmith.fc.validate_geom_type(path, "Polygon")``). The message is
        shown when this is true and cleared when it is false.
    message : str or list of str
        The message to show. A single string applies to every parameter; a list
        is matched one-to-one and must match ``param`` in length.
    block : bool, optional
        Keyword-only. If ``True`` (default), the message is an error and blocks
        the run. If ``False``, a non-blocking warning.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If ``message`` is a list whose length differs from ``param``.

    Notes
    -----
    As with ``require``, each parameter's message should be owned by one call.
    Guard a value-semantic check so it only runs once the value exists, e.g.
    ``when=bool(param.value) and not <is_valid>``. A non-``None`` ``hidden_value``
    / ``shown_value`` placeholder from ``checkbox_dependence`` /
    ``dynamic_dropdown`` makes ``bool(param.value)`` true, so such a guard passes
    on a placeholder; see ``require``.

    Examples
    --------
    Check geometry type once a polygon is provided:

    >>> arcsmith.param.flag(
    ...     area_polygon,
    ...     when=bool(area_polygon.value)
    ...     and not arcsmith.fc.validate_geom_type(
    ...         arcsmith.param.to_path(area_polygon), "Polygon"),
    ...     message="Input must be a polygon.")

    Warn on a suspicious value without blocking the run:

    >>> arcsmith.param.flag(buffer_dist,
    ...                     when=bool(buffer_dist.value) and buffer_dist.value > 1000,
    ...                     message="That is a very large buffer.", block=False)
    """
    if not isinstance(param, list):
        param = [param]
    messages = _broadcast(message, len(param), "message", "param")

    for p, msg in zip(param, messages):
        if when:
            if block:
                p.setErrorMessage(msg)
            else:
                p.setWarningMessage(msg)
        else:
            p.clearMessage()


def _is_history_recall(params: list) -> bool:
    """
    Return ``True`` when ``params`` are being restored on a tool history re-run.

    When a tool is re-opened from its run history, ArcGIS reloads every saved
    value but has not validated any of them yet, so on that first
    ``updateParameters`` pass each parameter reads ``hasBeenValidated == False``.
    During ordinary interactive use a managed dependent was already validated on
    an earlier pass (validation runs after every pass), so at least one reads
    ``True``. That difference is enough to recognize the re-run pass using only
    the dependents a helper already manages. It needs no access to the full
    parameter list, and nothing for the tool author to wire up.

    The distinction matters for value seeding: on a re-run the dependents
    already hold their restored values, including any the user *deliberately
    cleared* before running. Seeding ``shown_value`` into those empties would
    wipe the user's intent, so the seeding helpers skip it when this returns
    ``True``.

    Parameters
    ----------
    params : list of arcpy.Parameter
        The dependent parameters a helper functions is about to manage. An empty list
        returns ``True`` (vacuously) which is harmless because there is nothing
        to seed.

    Returns
    -------
    bool
        ``True`` if none of ``params`` has been validated yet.
    """
    return not any(getattr(p, "hasBeenValidated", False) for p in params)


def cascade_populate(trigger_param: arcpy.Parameter,
                     downstream_params: Union[arcpy.Parameter, list],
                     value: Any = None) -> None:
    """
    Assign a value to downstream parameters when an upstream parameter was just changed.

    On every ``updateParameters`` pass this is a no-op unless ``trigger_param``
    is in the ``'pending'`` state (it was *just* changed) or the ``'fresh'``
    state (the initial, untouched pass). In either case each parameter in
    ``downstream_params`` is set to ``value``.

    The default ``value=None`` clears the downstream parameters, which is the
    common case: invalidate stale dependent values when an upstream choice
    changes. Pass a scalar to set every downstream parameter to the same value,
    or a list to set them one-to-one.

    Parameters
    ----------
    trigger_param : arcpy.Parameter
        The parameter whose change triggers the cascade.
    downstream_params : arcpy.Parameter or list of arcpy.Parameter
        Parameter(s) to set when ``trigger_param`` is ``'pending'`` or ``'fresh'``.
        A single parameter may be passed without wrapping it in a list.
    value : scalar or list, optional
        Value assigned to each downstream parameter. A scalar is broadcast to
        all; a list maps one-to-one and must match ``downstream_params`` in
        length. Default ``None`` (clears every downstream parameter).

        ``None`` vs ``""``: ``None`` empties the parameter (it shows as unset);
        ``""`` assigns an explicit empty string, which is a *set* value. Use a
        concrete value (e.g. ``0`` or ``"N/A"``) when a required parameter must
        hold something.

    Raises
    ------
    ValueError
        If ``value`` is a list whose length differs from ``downstream_params``.

    See Also
    --------
    cascade_clear : Convenience wrapper for the common ``value=None`` case.

    Examples
    --------
    Clear dependent parameters when an upstream value changes (default):

    >>> cascade_populate(p1, [p2, p3])

    Reset dependents to a concrete value on change:

    >>> cascade_populate(p1, [p2, p3], value=0)

    Per-parameter values:

    >>> cascade_populate(p1, [p2, p3], value=["N/A", 0])
    """
    if not isinstance(downstream_params, list):
        downstream_params = [downstream_params]

    if state(trigger_param) in ('pending', 'fresh'):
        values = _broadcast(value, len(downstream_params), "value", "downstream_params")
        for param, val in zip(downstream_params, values):
            param.value = val


def cascade_clear(trigger_param: arcpy.Parameter,
                  downstream_params: Union[arcpy.Parameter, list]) -> None:
    """
    Clear downstream parameters when an upstream parameter was just changed.

    Thin convenience wrapper around :func:`cascade_populate` with ``value=None``.
    Kept for readability where the intent is simply to reset dependent values.

    Parameters
    ----------
    trigger_param : arcpy.Parameter
        The parameter whose change triggers the cascade.
    downstream_params : arcpy.Parameter or list of arcpy.Parameter
        Parameters to clear when ``trigger_param`` is ``'pending'`` or ``'fresh'``.

    Examples
    --------
    Clear dependent parameters when an upstream value changes:

    >>> cascade_clear(p1, [p2, p3])
    """
    cascade_populate(trigger_param, downstream_params, value=None)



def checkbox_dependence(controlling_checkbox: arcpy.Parameter,
                        dependents: Union[arcpy.Parameter, list],
                        hidden_value: Any = None, shown_value: Any = None,
                        auto_hide_dependents: bool = True) -> None:
    """
    Drive the enabled state and value of dependent parameters from a checkbox.

    Each dependent parameter has two distinct fill values:

    * ``hidden_value`` -- assigned whenever the checkbox is unchecked, regardless
      of ``auto_hide_dependents``. Use it to keep a *required* parameter
      satisfied while it is inactive.
    * ``shown_value`` -- assigned the moment the checkbox is checked
      (``'pending'`` state), but only to a dependent that is currently empty.
      Use it to seed a starting value the user can then edit. A dependent that
      already holds a value is left untouched.

    History re-runs are handled automatically. When a tool is re-opened from its
    run history the checkbox reloads as ``'pending'`` even though the user did
    not toggle it, and every dependent reloads with its saved value, including
    any the user *deliberately cleared* before running. That pass is recognized
    (the dependents reload unvalidated) and seeding is skipped, so restored
    values *and* deliberate clears survive the reload. No wiring is required from
    the tool author.

    Behavior by checkbox state:

    * Unchecked: each dependent's value is set to ``hidden_value``.
      ``enabled`` becomes ``not auto_hide_dependents``.
    * Just checked (``'pending'``) on a genuine user toggle: each dependent is
      enabled, and any dependent that is currently empty has its value set to
      ``shown_value``. Dependents that already hold a value keep it.
    * ``'pending'`` on a history re-run: each dependent is enabled, but no value
      is seeded. Restored values and deliberate clears are preserved as saved.
    * Otherwise (stable): no-op; existing user input is preserved.

    Parameters
    ----------
    controlling_checkbox : arcpy.Parameter
        Boolean checkbox that drives the state of all dependents.
    dependents : arcpy.Parameter or list of arcpy.Parameter
        Parameter(s) to control. A single parameter may be passed without
        wrapping it in a list.
    hidden_value : scalar or list, optional
        Value(s) assigned to dependents while they are inactive (checkbox
        unchecked). A scalar is broadcast to all dependents; a list maps
        one-to-one and must match in length. Applied regardless of
        ``auto_hide_dependents`` -- the parameter is always set to this value
        while unchecked; ``auto_hide_dependents`` only controls whether it is
        also disabled. Default ``None``.
    shown_value : scalar or list, optional
        Value(s) assigned when dependents are first activated (checkbox just
        checked). Same scalar/list rules as ``hidden_value``. Default ``None``.
    auto_hide_dependents : bool, optional
        If ``True`` (default), dependents are disabled (grayed out) while the
        checkbox is unchecked -- normal production behavior. If ``False``,
        dependents remain enabled so a tester can see and interact with every
        parameter. ``hidden_value`` is still applied either way. Default ``True``.

    Raises
    ------
    ValueError
        If ``hidden_value`` or ``shown_value`` is a list whose length differs
        from ``dependents``.

    Notes
    -----
    ``None`` vs ``""`` for ``hidden_value``/``shown_value``: ``None`` leaves the
    parameter empty (shown as unset); ``""`` assigns an explicit empty string,
    which is a *set* value. For a required parameter that must hold something
    while inactive, use a concrete value such as ``"N/A"`` or ``0`` rather
    than ``None`` -- ``None`` leaves the required parameter empty and flags an
    error.

    A concrete placeholder reads as "filled" to ``require`` / ``require_one_of``
    / ``flag`` (which test ``value is None``), so do not also validate a
    placeholder-pacified parameter with those helpers. Placeholders are the tool
    for *Required* params that are sometimes inactive; ``require`` is the tool for
    *Optional* params that are sometimes mandatory.

    Examples
    --------
    Broadcast one hidden value to all dependents:

    >>> checkbox_dependence(cb, [p1, p2, p3], hidden_value="N/A")

    Single dependent (no list needed) with a starting value when shown:

    >>> checkbox_dependence(cb, p1, hidden_value=0, shown_value=10)

    Per-dependent values:

    >>> checkbox_dependence(
    ...     cb, [p1, p2],
    ...     hidden_value=["N/A", 0],
    ...     shown_value=["", 1],
    ... )

    Keep dependents enabled while testing (hidden_value still applied):

    >>> checkbox_dependence(cb, [p1, p2], hidden_value="N/A", auto_hide_dependents=False)
    """
    # Normalize dependents to a list
    if not isinstance(dependents, list):
        dependents = [dependents]

    # Normalize hidden_value/shown_value to lists aligned with dependents
    hidden_values = _broadcast(hidden_value, len(dependents), "hidden_value", "dependents")
    shown_values = _broadcast(shown_value, len(dependents), "shown_value", "dependents")

    if not controlling_checkbox.value:  # Checkbox unchecked
        for param, hv in zip(dependents, hidden_values):
            param.value = hv                      # always assign hidden_value
            param.enabled = not auto_hide_dependents
    elif state(controlling_checkbox) == 'pending':  # Checkbox just checked
        # A history re-run also reloads the checkbox as 'pending', but on that
        # pass the dependents are unvalidated and already hold their restored
        # values - including any the user deliberately cleared. Skip seeding then
        # so those values (and clears) survive; only seed on a genuine check.
        recall = _is_history_recall(dependents)
        for param, sv, hv in zip(dependents, shown_values, hidden_values):
            param.enabled = True
            if recall:
                continue
            # Genuine check: seed shown_value into a dependent that is currently
            # empty (or still holds its hidden_value).
            if not param.value or param.valueAsText == hv or str(Path(param.valueAsText).stem) == hv:
                param.value = sv
    else:
        pass  # Stable; preserve existing user input

def drop_populate(param: arcpy.Parameter, values: list,
                  default: Optional[str] = None, overwrite_empty: bool = False,
                  none_label: Optional[str] = None) -> None:
    """
    Set or replace a parameter's dropdown filter list.

    By default, skips the update if ``values`` is empty to avoid clearing
    an existing valid filter list when an upstream dependency has not yet
    been set. Set ``overwrite_empty=True`` to force the update regardless.

    ``None`` entries in ``values`` are handled according to ``none_label``:
    dropped silently by default, or replaced with a sentinel string if one
    is provided. All non-None values are coerced to ``str`` automatically,
    since arcpy's ``ValueList`` filter requires strings.

    Parameters
    ----------
    param : arcpy.Parameter
        The dropdown parameter to populate.
    values : list
        Options to display in the dropdown. Non-string values are coerced
        to ``str``. ``None`` entries are dropped unless ``none_label`` is
        provided.
    default : str, optional
        Value to assign to the parameter after the filter list is set.
        Must be one of the entries in ``values``. Only applied while the
        parameter is in the ``'fresh'`` or ``'settled'`` state (unaltered
        by the user), so existing user input is never overwritten. Ignored
        when the filter list is not updated (i.e. when ``values`` is empty
        and ``overwrite_empty`` is ``False``). Default ``None`` (leaves the
        current value unchanged).
    overwrite_empty : bool, optional
        If ``True``, updates the filter list even when ``values`` is empty.
        Default ``False``.
    none_label : str, optional
        If provided, ``None`` entries in ``values`` are replaced with this
        string in the dropdown rather than dropped. Note that selecting this
        label and passing it to :func:`arcsmith.fc.build_where` will not
        produce a valid ``IS NULL`` clause. Handle that case separately at
        the call site. Default ``None`` (drop ``None`` entries silently).

    Examples
    --------
    Populate a dropdown, skipping update if values are empty:

    >>> arcsmith.param.drop_populate(p, ["Lake McDonald Lodge", "East Glacier Lodge", "St. Mary Lake Boats"])

    Populate and pre-select a default option:

    >>> drop_populate(p, ["Hiking", "Stock"], default="Hiking")

    Force clear a dropdown by overwriting with an empty list:

    >>> drop_populate(p, [], overwrite_empty=True)

    Coerce non-string values and drop nulls automatically:

    >>> values = arcsmith.flds.unique_values(input_fc, "TRAIL_TYPE")
    >>> drop_populate(p, values)

    Preserve nulls as a selectable sentinel (handle separately in build_where):

    >>> drop_populate(p, values, none_label="(No value)")
    """
    cleaned = [
        none_label if v is None else str(v)
        for v in values
        if v is not None or none_label is not None
    ]

    if cleaned or overwrite_empty:
        param.filter.type = "ValueList"
        param.filter.list = cleaned
        if default is not None and state(param) in ('fresh', 'settled'):
            param.value = default


def dynamic_dropdown(controlling_dropdown: arcpy.Parameter, option_map: dict,
                     hidden_value_map: Optional[dict] = None,
                     shown_value_map: Optional[dict] = None,
                     auto_hide_dependents: bool = True) -> None:
    """
    Show one group of dependent parameters based on the selected dropdown option.

    Each dropdown option maps to a group of parameters. When an option is
    selected its group becomes the *active* group; the groups for every other
    option are *inactive*.

    Each managed parameter has two fill values:

    * ``hidden_value_map`` -- values assigned to a group's parameters whenever
      that group is inactive (its option is not selected). Applied regardless
      of ``auto_hide_dependents``. Keeps required parameters satisfied.
    * ``shown_value_map`` -- values assigned to the active group the moment its
      option is selected (dropdown ``'pending'``), but only to params that are
      currently empty. Seeds starting values while preserving any value a param
      already holds.

    History re-runs are handled automatically: re-opening a tool from its run
    history reloads the dropdown as ``'pending'`` and its active group with the
    saved values (including deliberate clears). That pass is recognized (the
    group's params reload unvalidated) and seeding is skipped, so restored
    values and clears survive the reload with no wiring from the tool author.

    Behavior per group:

    * Inactive group: values set from ``hidden_value_map``; disabled if
      ``auto_hide_dependents=True``, enabled if ``False``.
    * Active group, just selected (``'pending'``) on a genuine user change:
      enabled; empty params seeded from ``shown_value_map``; params that already
      hold a value keep it.
    * Active group, ``'pending'`` on a history re-run: enabled; nothing seeded.
      Restored values and deliberate clears preserved.
    * Active group, stable: enabled; existing user input preserved.

    Parameters
    ----------
    controlling_dropdown : arcpy.Parameter
        Dropdown whose value selects which group is active.
    option_map : dict of {str : arcpy.Parameter or list of arcpy.Parameter}
        Maps each option label to the parameters enabled when that option is
        selected. Every parameter across every option is managed on each call.
        A single parameter may be passed without wrapping it in a list.

        Example::

            {
                "Shapefile":     [p1],
                "Feature Class": [p2, p3],
            }

    hidden_value_map : dict of {str : (scalar or list)}, optional
        Values assigned to a group's parameters while that group is inactive
        (its option is not selected). Applied regardless of
        ``auto_hide_dependents`` -- ``auto_hide_dependents`` only controls
        whether inactive parameters are also disabled. Keys should match
        ``option_map``; missing keys fall back to ``None``. For each key a
        scalar is broadcast to that option's parameters; a list maps
        one-to-one and must match in length. Default ``None``.

        Example::

            {
                "Feature Class": "N/A",   # broadcast to every param in that group
            }

    shown_value_map : dict of {str : (scalar or list)}, optional
        Values assigned to the active group when its option is first selected
        (dropdown ``'pending'``). Same keys and scalar/list rules as
        ``hidden_value_map``. Missing keys fall back to ``None``. Default ``None``.

        Example::

            {
                "Shapefile":     "",          # start p1 as an empty string
                "Feature Class": ["N/A", 0],  # one value per parameter
            }

    auto_hide_dependents : bool, optional
        If ``True`` (default), inactive groups are disabled (grayed out) in
        addition to receiving their ``hidden_value_map`` values. If ``False``,
        inactive groups remain enabled so a tester can see all parameters,
        but ``hidden_value_map`` is still applied. Default ``True``.

    Raises
    ------
    ValueError
        If a ``hidden_value_map`` or ``shown_value_map`` list length differs
        from its ``option_map`` counterpart.

    Notes
    -----
    ``None`` vs ``""`` per entry: ``None`` empties the parameter (shown as
    unset); ``""`` assigns an explicit empty string, which is a *set* value. For
    a required parameter that must hold something while inactive, use a concrete
    ``hidden_value_map`` entry such as ``"N/A"`` or ``0`` -- not ``None``.

    A concrete placeholder reads as "filled" to ``require`` / ``require_one_of``
    / ``flag`` (which test ``value is None``), so do not also validate a
    placeholder-pacified parameter with those helpers. Placeholders are the tool
    for *Required* params that are sometimes inactive; ``require`` is the tool for
    *Optional* params that are sometimes mandatory.

    Examples
    --------
    Basic -- enable the group for the selected option:

    >>> dynamic_dropdown(dropdown, {"Shapefile": [p1], "Feature Class": [p2, p3]})

    Seed starting values when an option is chosen, and fill inactive groups:

    >>> dynamic_dropdown(
    ...     dropdown,
    ...     option_map={"Shapefile": [p1], "Feature Class": [p2, p3]},
    ...     shown_value_map={"Shapefile": [""], "Feature Class": ["N/A", 0]},
    ...     hidden_value_map={"Feature Class": "N/A"},  # scalar broadcast to both
    ... )

    Keep inactive groups enabled while testing (hidden_value_map still applied):

    >>> dynamic_dropdown(dropdown, option_map, auto_hide_dependents=False)
    """
    hidden_value_map = hidden_value_map or {}
    shown_value_map = shown_value_map or {}

    # Validate and normalize every option's lists up front, so a misconfigured
    # entry is caught even when that option is not currently selected.
    norm_hidden = {}
    norm_shown = {}
    for option, params in option_map.items():
        if not isinstance(params, list):
            params = [params]
        norm_hidden[option] = _broadcast(
            hidden_value_map.get(option, None), len(params),
            f"hidden_value_map['{option}']", f"option_map['{option}']")
        norm_shown[option] = _broadcast(
            shown_value_map.get(option, None), len(params),
            f"shown_value_map['{option}']", f"option_map['{option}']")

    selected_option = controlling_dropdown.value
    is_pending = state(controlling_dropdown) == 'pending'

    for option, params in option_map.items():
        if not isinstance(params, list):
            params = [params]
        if option == selected_option:
            # Active group: always enabled; seed shown values only on a genuine
            # change, and only into params that are empty. A history re-run also
            # reloads the dropdown as 'pending', but on that pass the active
            # group's params are unvalidated and already hold their restored
            # values (including deliberate clears), so skip seeding to preserve
            # them. See _is_history_recall.
            for param in params:
                param.enabled = True
            if is_pending and not _is_history_recall(params):
                for param, sv in zip(params, norm_shown[option]):
                    if not param.value:
                        param.value = sv
        else:
            # Inactive group: always assign hidden_value; disable if auto_hide.
            for param, hv in zip(params, norm_hidden[option]):
                param.value = hv  # always assign hidden_value
                param.enabled = not auto_hide_dependents


def to_path(param: arcpy.Parameter) -> str:
    """
    Resolve an ``arcpy.Parameter`` to its absolute catalog path as a string.

    Prefer this over ``param.valueAsText`` or ``Path(param.valueAsText)``
    when the parameter accepts a layer or feature class, because the display
    string can differ from the real path in several common situations:

    * **Map layer selected** -- the user picks a layer by its TOC name (e.g.
      ``"trails"``); ``valueAsText`` returns that name, not the underlying
      GDB path.
    * **SDE connection** -- the display string may be a connection alias;
      ``catalogPath`` returns the resolvable path.
    * **Relative path** -- ``catalogPath`` is always absolute.

    Use ``Path(param.valueAsText)`` only when the parameter is typed as a
    plain file path (e.g. an output folder or ``.lyrx`` file) and there is
    no chance the user will select from the map.

    Parameters
    ----------
    param : arcpy.Parameter
        A parameter whose value is a feature class, feature layer, table,
        raster, or any other describable data source.

    Returns
    -------
    str
        Absolute catalog path to the data source.

    Examples
    --------
    Resolve a feature-class parameter in ``execute``:

    >>> fc_path = arcsmith.param.to_path(parameters[0])
    >>> clause = arcsmith.fc.build_where(fc_path, "TRAIL_STATUS", "Open")

    Resolve in ``updateParameters`` to populate a downstream dropdown:

    >>> fc_path = arcsmith.param.to_path(parameters[0])
    >>> arcsmith.param.drop_populate(parameters[1], arcsmith.flds.list_cols(fc_path))
    """
    description = arcpy.Describe(param.value)
    catalog_path = description.catalogPath
    # arcpy.AddMessage(f"Resolved '{param.valueAsText}' -> {catalog_path}")
    return catalog_path