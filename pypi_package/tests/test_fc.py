"""Tests for the pure SQL-literal helper in arcsmith.fc."""

import pytest

from arcsmith.fc import _sql_quote


def test_plain_string_is_wrapped_in_single_quotes() -> None:
    assert _sql_quote("Active") == "'Active'"


def test_embedded_single_quote_is_doubled() -> None:
    # The bug this guards against: a raw f-string would yield 'O'Brien',
    # which is malformed SQL.
    assert _sql_quote("O'Brien") == "'O''Brien'"


def test_multiple_quotes_each_doubled() -> None:
    assert _sql_quote("a'b'c") == "'a''b''c'"


def test_value_is_coerced_to_str() -> None:
    assert _sql_quote(4) == "'4'"


def test_empty_string() -> None:
    assert _sql_quote("") == "''"


@pytest.mark.parametrize("value, expected", [
    ("St. Mary's", "'St. Mary''s'"),
    ("D'Angelo", "'D''Angelo'"),
    ("plain", "'plain'"),
])
def test_realistic_values(value: str, expected: str) -> None:
    assert _sql_quote(value) == expected
