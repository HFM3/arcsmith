"""Tests for the pure helpers and parameter-state logic in arcsmith.param.

``state``, ``_broadcast``, ``cascade_populate``, ``cascade_clear``,
``_is_history_recall``, the validation helpers ``require`` / ``require_one_of`` /
``flag``, and the seeding branches of ``checkbox_dependence`` /
``dynamic_dropdown`` never call into arcpy — they only read/write attributes on
the parameter objects passed in. A tiny fake parameter is enough to exercise
their behavior.
"""

from typing import Any, Optional

import pytest

from arcsmith.param import (
    _broadcast,
    state,
    require,
    require_one_of,
    flag,
    cascade_populate,
    cascade_clear,
    _is_history_recall,
    checkbox_dependence,
    dynamic_dropdown,
)


class FakeParam:
    """Minimal stand-in for arcpy.Parameter for the attribute-only helpers."""

    def __init__(self, altered: bool = False, validated: bool = False,
                 value: Any = None, display_name: str = "Param") -> None:
        self.altered = altered
        self.hasBeenValidated = validated
        self.value = value
        self.enabled = True
        self.displayName = display_name
        # arcpy holds a single message per parameter; mirror that with one slot.
        self.message: Optional[str] = None
        self.message_type: Optional[str] = None

    @property
    def valueAsText(self) -> Optional[str]:
        # Mirrors arcpy: the display string of the value, or None when unset.
        return None if self.value is None else str(self.value)

    def setErrorMessage(self, text: str) -> None:
        self.message = text
        self.message_type = "error"

    def setWarningMessage(self, text: str) -> None:
        self.message = text
        self.message_type = "warning"

    def clearMessage(self) -> None:
        self.message = None
        self.message_type = None


# --- _broadcast ----------------------------------------------------------- #

def test_broadcast_scalar_is_repeated() -> None:
    assert _broadcast("N/A", 3) == ["N/A", "N/A", "N/A"]


def test_broadcast_none_is_treated_as_scalar() -> None:
    assert _broadcast(None, 2) == [None, None]


def test_broadcast_list_of_matching_length_returned_unchanged() -> None:
    assert _broadcast(["a", "b"], 2) == ["a", "b"]


def test_broadcast_list_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        _broadcast(["a", "b"], 3)


# --- state ---------------------------------------------------------------- #

@pytest.mark.parametrize("altered, validated, expected", [
    (False, False, "fresh"),
    (True, False, "pending"),
    (False, True, "settled"),
    (True, True, "confirmed"),
])
def test_state_matrix(altered: bool, validated: bool, expected: str) -> None:
    assert state(FakeParam(altered=altered, validated=validated)) == expected


# --- cascade_populate / cascade_clear ------------------------------------- #

def test_cascade_populate_sets_value_when_trigger_pending() -> None:
    trigger = FakeParam(altered=True, validated=False)  # 'pending'
    d1, d2 = FakeParam(value="old"), FakeParam(value="old")
    cascade_populate(trigger, [d1, d2], value=0)
    assert d1.value == 0 and d2.value == 0


def test_cascade_populate_noop_when_trigger_settled() -> None:
    trigger = FakeParam(altered=False, validated=True)  # 'settled'
    d1 = FakeParam(value="keep")
    cascade_populate(trigger, d1, value=0)
    assert d1.value == "keep"


def test_cascade_populate_accepts_single_param_without_list() -> None:
    trigger = FakeParam(altered=True, validated=False)
    d1 = FakeParam(value="old")
    cascade_populate(trigger, d1, value="new")
    assert d1.value == "new"


def test_cascade_populate_per_param_list_values() -> None:
    trigger = FakeParam(altered=False, validated=False)  # 'fresh' also triggers
    d1, d2 = FakeParam(), FakeParam()
    cascade_populate(trigger, [d1, d2], value=["N/A", 0])
    assert d1.value == "N/A" and d2.value == 0


def test_cascade_clear_sets_none() -> None:
    trigger = FakeParam(altered=True, validated=False)
    d1 = FakeParam(value="something")
    cascade_clear(trigger, d1)
    assert d1.value is None


# --- _is_history_recall --------------------------------------------------- #

def test_is_history_recall_true_when_nothing_validated() -> None:
    # First pass of a re-run: every restored param is unvalidated.
    params = [FakeParam(altered=True, validated=False),
              FakeParam(altered=True, validated=False)]
    assert _is_history_recall(params) is True


def test_is_history_recall_false_when_any_validated() -> None:
    # Mid-session: a dependent was validated on an earlier pass.
    params = [FakeParam(altered=True, validated=True),
              FakeParam(altered=True, validated=False)]
    assert _is_history_recall(params) is False


def test_is_history_recall_empty_list_is_vacuously_true() -> None:
    assert _is_history_recall([]) is True


# --- checkbox_dependence: history-recall seeding guard --------------------- #

def test_checkbox_dependence_skips_seeding_on_history_recall() -> None:
    # Checkbox reloads 'pending'; dependents reload unvalidated (a re-run).
    cb = FakeParam(altered=True, validated=False, value=True)
    cleared = FakeParam(altered=True, validated=False, value=None)   # user cleared it
    kept = FakeParam(altered=True, validated=False, value="entered")  # user value
    checkbox_dependence(cb, [cleared, kept], shown_value="SEED")
    assert cleared.value is None        # deliberate clear preserved, not re-seeded
    assert kept.value == "entered"      # entered value preserved
    assert cleared.enabled and kept.enabled  # still enabled


def test_checkbox_dependence_seeds_on_genuine_check() -> None:
    # Genuine toggle: dependents were validated on an earlier pass.
    cb = FakeParam(altered=True, validated=False, value=True)  # 'pending'
    dep = FakeParam(altered=True, validated=True, value=None)  # empty, validated
    checkbox_dependence(cb, dep, shown_value="SEED")
    assert dep.value == "SEED"
    assert dep.enabled


def test_checkbox_dependence_unchecked_applies_hidden_value() -> None:
    cb = FakeParam(altered=True, validated=False, value=False)  # unchecked
    dep = FakeParam(validated=True, value="stale")
    checkbox_dependence(cb, dep, hidden_value="N/A")
    assert dep.value == "N/A"


# --- dynamic_dropdown: history-recall seeding guard ----------------------- #

def test_dynamic_dropdown_skips_seeding_on_history_recall() -> None:
    dd = FakeParam(altered=True, validated=False, value="A")  # 'pending'
    cleared = FakeParam(altered=True, validated=False, value=None)
    dynamic_dropdown(dd, {"A": cleared}, shown_value_map={"A": "SEED"})
    assert cleared.value is None        # clear preserved on re-run
    assert cleared.enabled


def test_dynamic_dropdown_seeds_on_genuine_change() -> None:
    dd = FakeParam(altered=True, validated=False, value="A")  # 'pending'
    dep = FakeParam(altered=True, validated=True, value=None)  # validated earlier
    dynamic_dropdown(dd, {"A": dep}, shown_value_map={"A": "SEED"})
    assert dep.value == "SEED"
    assert dep.enabled


# --- require -------------------------------------------------------------- #

def test_require_when_and_empty_sets_error_with_display_name() -> None:
    p = FakeParam(value=None, display_name="Filter Field")
    require(p, when=True)
    assert p.message_type == "error"
    assert "Filter Field" in p.message


def test_require_when_and_filled_clears() -> None:
    p = FakeParam(value="ROADS")
    p.setErrorMessage("stale")          # simulate a message from a prior pass
    require(p, when=True)
    assert p.message is None and p.message_type is None


def test_require_condition_off_clears() -> None:
    p = FakeParam(value=None)
    p.setErrorMessage("stale")
    require(p, when=False)
    assert p.message is None


def test_require_block_false_sets_warning() -> None:
    p = FakeParam(value=None)
    require(p, when=True, block=False)
    assert p.message_type == "warning"


def test_require_custom_message_overrides_auto() -> None:
    p = FakeParam(value=None, display_name="Polygon")
    require(p, when=True, message="Choose a polygon.")
    assert p.message == "Choose a polygon."


def test_require_single_param_accepted_without_list() -> None:
    p = FakeParam(value=None)
    require(p, when=True)               # not wrapped in a list
    assert p.message_type == "error"


def test_require_list_scalar_message_applies_to_all() -> None:
    a, b = FakeParam(value=None), FakeParam(value=None)
    require([a, b], when=True, message="Fill me.")
    assert a.message == "Fill me." and b.message == "Fill me."


def test_require_list_auto_message_is_per_param() -> None:
    a = FakeParam(value=None, display_name="Alpha")
    b = FakeParam(value=None, display_name="Beta")
    require([a, b], when=True)
    assert "Alpha" in a.message and "Beta" in b.message


def test_require_list_message_length_mismatch_raises() -> None:
    a, b = FakeParam(value=None), FakeParam(value=None)
    with pytest.raises(ValueError):
        require([a, b], when=True, message=["only one"])


# --- require_one_of ------------------------------------------------------- #

def test_require_one_of_all_empty_flags_each() -> None:
    a = FakeParam(value=None, display_name="Polygon")
    b = FakeParam(value=None, display_name="Area Value")
    require_one_of([a, b], when=True)
    assert a.message_type == "error" and b.message_type == "error"
    assert "Polygon" in a.message and "Area Value" in a.message


def test_require_one_of_one_filled_clears_all() -> None:
    a = FakeParam(value="poly")
    b = FakeParam(value=None)
    b.setErrorMessage("stale")
    require_one_of([a, b], when=True)
    assert a.message is None and b.message is None


def test_require_one_of_condition_off_clears_all() -> None:
    a, b = FakeParam(value=None), FakeParam(value=None)
    a.setErrorMessage("stale")
    require_one_of([a, b], when=False)
    assert a.message is None and b.message is None


# --- flag ----------------------------------------------------------------- #

def test_flag_sets_message_when_condition_true() -> None:
    p = FakeParam(value="pts")
    flag(p, when=True, message="Must be a point layer.")
    assert p.message == "Must be a point layer." and p.message_type == "error"


def test_flag_clears_when_condition_false() -> None:
    p = FakeParam(value="pts")
    p.setErrorMessage("stale")
    flag(p, when=False, message="unused")
    assert p.message is None


def test_flag_block_false_sets_warning() -> None:
    p = FakeParam(value=5)
    flag(p, when=True, message="Large value.", block=False)
    assert p.message_type == "warning"
