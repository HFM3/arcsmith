"""Tests for the pure color/preset helpers in arcsmith.lyr."""

import pytest

from arcsmith import lyr
from arcsmith.lyr import (
    _parse_color,
    _random_simple_preset,
    _STYLISH_HUES,
    _is_memory_path,
)


# --- _parse_color --------------------------------------------------------- #

def test_rgb_tuple_passthrough() -> None:
    assert _parse_color((173, 216, 230)) == (173, 216, 230)


def test_rgb_list_coerced_to_int_tuple() -> None:
    assert _parse_color([1.0, 2.0, 3.0]) == (1, 2, 3)


def test_hex_with_hash() -> None:
    assert _parse_color("#ADBCE6") == (0xAD, 0xBC, 0xE6)


def test_hex_without_hash() -> None:
    assert _parse_color("ADBCE6") == (0xAD, 0xBC, 0xE6)


def test_hex_shorthand_expanded() -> None:
    assert _parse_color("#F0A") == (0xFF, 0x00, 0xAA)


@pytest.mark.parametrize("bad", ["#12", "#GGGGGG", "nothex", (1, 2), (1, 2, 3, 4)])
def test_invalid_color_raises(bad: object) -> None:
    with pytest.raises(ValueError):
        _parse_color(bad)


# --- _random_simple_preset geometry mapping ------------------------------- #

def test_preset_family_matches_geometry() -> None:
    assert _random_simple_preset("Point").startswith("simple_pt_")
    assert _random_simple_preset("Multipoint").startswith("simple_pt_")
    assert _random_simple_preset("Polyline").startswith("simple_ln_")
    assert _random_simple_preset("Polygon").startswith("simple_")


def test_unknown_geometry_falls_back_to_polygon_fill() -> None:
    name = _random_simple_preset(None)
    assert name.startswith("simple_") and not name.startswith(
        ("simple_pt_", "simple_ln_")
    )


def test_every_returned_preset_is_registered() -> None:
    for geom in ("Point", "Polyline", "Polygon", None):
        assert _random_simple_preset(geom) in lyr.PRESETS


# --- _seed_styles reproducibility ----------------------------------------- #

def test_seed_makes_hue_sequence_reproducible() -> None:
    lyr._seed_styles(42)
    first = [_random_simple_preset("Polygon") for _ in range(20)]
    lyr._seed_styles(42)
    second = [_random_simple_preset("Polygon") for _ in range(20)]
    assert first == second


def test_hue_cycle_covers_full_set_without_repeat_within_a_pass() -> None:
    lyr._seed_styles(0)
    n = len(_STYLISH_HUES)
    one_pass = [_random_simple_preset("Polygon") for _ in range(n)]
    assert len(set(one_pass)) == n  # no repeat before the set is exhausted


# --- _is_memory_path ------------------------------------------------------ #

@pytest.mark.parametrize("src", [
    r"memory\trails",
    "memory/trails",
    r"in_memory\trails",
    "in_memory/trails",
    "memory",          # bare workspace
    r"MEMORY\Trails",  # case-insensitive
])
def test_memory_paths_detected(src: str) -> None:
    assert _is_memory_path(src) is True


@pytest.mark.parametrize("src", [
    r"C:\data\glacier.gdb\trails",
    "trails.shp",
    "memorydata/trails",   # 'memory' must be a whole path part, not a prefix
    "",                    # empty -> no parts
])
def test_non_memory_paths_rejected(src: str) -> None:
    assert _is_memory_path(src) is False


def test_memory_path_detected_on_stringified_result() -> None:
    # An arcpy.Result stringifies to its output path; detection runs on str(src).
    class FakeResult:
        def __str__(self) -> str:
            return r"memory\dissolve_out"

    assert _is_memory_path(FakeResult()) is True
