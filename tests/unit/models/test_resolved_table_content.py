import pytest
import sys
from pathlib import Path
root_path = Path(__file__).resolve().parents[3]
sys.path.append(str(root_path))
from core.models.resolved_content import ResolvedTableContent


def test_resolved_table_content_is_created_correctly():
    content = ResolvedTableContent(
        title="Document history",
        headers=["Version", "Date", "Author", "Description"],
        rows=[
            ["A", "2026-03-27", "Xavier", "Initial release"],
            ["B", "2026-03-28", "Laura", "Updated formatting"],
        ],
    )

    assert content.title == "Document history"
    assert len(content.headers) == 4
    assert len(content.rows) == 2
    assert content.rows[0][0] == "A"


def test_resolved_table_content_allows_empty_title():
    content = ResolvedTableContent(
        title=None,
        headers=["Version", "Date"],
        rows=[["A", "2026-03-27"]],
    )

    assert content.title is None


def test_resolved_table_content_accepts_empty_headers_and_rows():
    content = ResolvedTableContent()

    assert content.title is None
    assert content.headers == []
    assert content.rows == []


def test_resolved_table_content_fails_if_headers_is_not_a_list():
    with pytest.raises(TypeError):
        ResolvedTableContent(
            title="Document history",
            headers="not_a_list",
            rows=[],
        )


def test_resolved_table_content_fails_if_rows_is_not_a_list():
    with pytest.raises(TypeError):
        ResolvedTableContent(
            title="Document history",
            headers=["Version", "Date"],
            rows="not_a_list",
        )


def test_resolved_table_content_fails_if_one_row_is_not_a_list():
    with pytest.raises(TypeError):
        ResolvedTableContent(
            title="Document history",
            headers=["Version", "Date"],
            rows=[
                ["A", "2026-03-27"],
                "invalid_row",
            ],
        )


def test_resolved_table_content_fails_if_row_length_does_not_match_headers():
    with pytest.raises(ValueError):
        ResolvedTableContent(
            title="Document history",
            headers=["Version", "Date", "Author"],
            rows=[
                ["A", "2026-03-27"],
            ],
        )


def test_resolved_table_content_accepts_different_cell_value_types():
    content = ResolvedTableContent(
        title="Measurements",
        headers=["Name", "Value", "Valid"],
        rows=[
            ["Voltage", 12.5, True],
            ["Current", 1.8, False],
        ],
    )

    assert content.rows[0][1] == 12.5
    assert content.rows[1][2] is False
