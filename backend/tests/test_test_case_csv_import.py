"""Unit tests for CSV test case import parsing and grouping."""

from __future__ import annotations

from features.functional.services import test_case_csv_import as M


def _parse(s: str):
    col_map, body, errs = M.parse_csv_to_rows(s)
    gerrs: list = list(errs)
    groups, gerrs = M.build_case_groups(col_map, body, gerrs)
    M.validate_groups_non_empty(groups, gerrs)
    return groups, gerrs


def test_parse_groups_steps_and_no_steps():
    csv = """case_key,title,step_number,action,target
A,Alpha,,,
A,,1,click,#btn
B,Beta only,,,
"""
    groups, errs = _parse(csv)
    assert not errs
    assert set(groups.keys()) == {"A", "B"}
    assert len(groups["A"].steps) == 1
    assert groups["A"].steps[0].action.value == "click"
    assert len(groups["B"].steps) == 0


def test_unknown_headers_ignored():
    csv = """case_key,title,junk_col
X,Hello,ignore-me
"""
    groups, errs = _parse(csv)
    assert not errs
    assert groups["X"].title == "Hello"


def test_requires_case_key_column():
    _cm, _body, errs = M.parse_csv_to_rows("title,foo\na,b\n")
    assert errs and "case_key" in errs[0].message.lower()


def test_leading_hash_comment_lines_skipped():
    csv = """# comment line
# another
case_key,title
K1,Hello
"""
    groups, errs = _parse(csv)
    assert not errs
    assert "K1" in groups


def test_duplicate_step_numbers_renumbered_with_error():
    csv = """case_key,step_number,action
Z,1,click
Z,1,click
"""
    groups, errs = _parse(csv)
    assert any("Duplicate step_number" in e.message for e in errs)
    assert groups["Z"].steps[0].step_number == 1
    assert groups["Z"].steps[1].step_number == 2


def test_decode_prefers_utf8_sig():
    raw = "\ufeffcase_key,title\nk1,T\n".encode("utf-8-sig")
    text, w = M.decode_csv_bytes(raw)
    assert "case_key" in text
    assert not w


def test_collect_constraints_detects_long_case_key():
    long_key = "x" * 51
    csv = f"case_key,title\n{long_key},T\n"
    groups, _ = _parse(csv)
    hits = M.collect_case_constraint_violations(groups)
    assert hits and hits[0][0] == long_key
