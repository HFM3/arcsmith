"""Tests for the pure field-set helpers in arcsmith.flds.

``_is_system`` and ``_resolve_keep`` operate on plain string lists and never
call arcpy.
"""

import pytest

from arcsmith.flds import _is_system, _resolve_keep


# --- _is_system ----------------------------------------------------------- #

@pytest.mark.parametrize("name", ["OBJECTID", "objectid", "Shape", "Shape_Length",
                                  "GlobalID", "FID", "OID"])
def test_system_fields_recognized_case_insensitively(name: str) -> None:
    assert _is_system(name)


@pytest.mark.parametrize("name", ["NAME", "owner", "status", "shape_leng"])
def test_user_fields_not_system(name: str) -> None:
    assert not _is_system(name)


# --- _resolve_keep -------------------------------------------------------- #

ALL: list[str] = ["NAME", "OWNER", "STATUS", "AREA"]


def test_keep_returns_requested_with_original_casing() -> None:
    # Request lowercase; result should carry the source's original casing.
    assert _resolve_keep(ALL, ["name", "status"], keep=True) == {"NAME", "STATUS"}


def test_drop_returns_complement() -> None:
    assert _resolve_keep(ALL, ["OWNER"], keep=False) == {"NAME", "STATUS", "AREA"}


def test_unknown_field_raises() -> None:
    with pytest.raises(ValueError):
        _resolve_keep(ALL, ["NOPE"], keep=True)


def test_system_names_are_exempt_from_unknown_check() -> None:
    # OBJECTID is not in ALL, but being a system field it must not raise; it is
    # simply not added to the keep set (arcpy preserves it regardless).
    result = _resolve_keep(ALL, ["NAME", "OBJECTID"], keep=True)
    assert result == {"NAME"}


def test_keep_empty_list_keeps_nothing() -> None:
    assert _resolve_keep(ALL, [], keep=True) == set()
