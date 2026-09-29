import pytest
import sys
from pathlib import Path

root_path = Path(__file__).resolve().parents[3]
sys.path.append(str(root_path))

from core.models.resolved_content import (
        ResolvedSectionTitleRow,
        ResolvedLabelValueRow,
        ResolvedLabelValueTableContent
        )


def test_section_title_row_is_created_correctly():
    row = ResolvedSectionTitleRow(
            row_type="section_title",
            title="setup description"
            )

    assert row.row_type == "section_title"
    assert row.title == "setup description"


def test_section_title_row_fails_when_title_is_empty():
    with pytest.raises(ValueError):
        ResolvedSectionTitleRow(
                row_type="section_title",
                title="",
                )


def test_label_value_row_is_created_correctly():
    row = ResolvedLabelValueRow(
            row_type="label_value_row",
            label="description",
            value="test setup description"
            )

    assert row.row_type == "label_value_row"
    assert row.label == "description"
    assert row.value == "test setup description"


def test_label_value_row_fails_when_label_is_empty():
    with pytest.raises(ValueError):
        ResolvedLabelValueRow(
            row_type="label_value_row",
            label="",
            value="something"
        )


def test_label_value_table_content_accepts_valid_rows():
    title_row = ResolvedSectionTitleRow(
        row_type="section_title",
        title="Setup description",
    )
    value_row = ResolvedLabelValueRow(
        row_type="label_value_row",
        label="description",
        value="Text",
    )

    content = ResolvedLabelValueTableContent(rows=[title_row, value_row])

    assert len(content.rows) == 2


def test_label_value_table_content_fails_if_rows_is_not_a_list():
    with pytest.raises(TypeError):
        ResolvedLabelValueTableContent(rows="not_a_list")


def test_label_value_table_content_fails_with_invalid_row_type():
    with pytest.raises(TypeError):
        ResolvedLabelValueTableContent(rows=[123])


