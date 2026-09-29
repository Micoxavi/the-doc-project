from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class ResolvedTableContent:
    """
    Stores normalized table content after the resolution phase.

    This model represents a table in a stable internal format, using
    a title, a list of visible headers, and a list of body rows.
    It may also perform basic self-validation when instantiated to
    reject clearly inconsistent data.

    """

    title: str | None = None
    headers: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.headers, list):
            raise TypeError("headers must be a list.")

        if not isinstance(self.rows, list):
            raise TypeError("rows must be a list.")

        expected_len = len(self.headers)
        for idx, row in enumerate(self.rows):
            if not isinstance(row, list):
                raise TypeError(f"Row {idx} must be a list.")

            if expected_len and len(row) != expected_len:
                raise ValueError(
                    f"Row {idx} has {len(row)} cells but expected {expected_len}."
                )


@dataclass(slots=True)
class ResolvedSectionTitleRow:
    """
    """

    row_type: Literal["section_title"]
    title: str

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("title cannot be empty")


@dataclass(slots=True)
class ResolvedLabelValueRow:
    """
    """
    row_type: Literal["label_value_row"]
    label: str
    value: Any

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("label cannot be empty")


@dataclass(slots=True)
class ResolvedLabelValueTableContent:
    """
    Stores normalized table content after the resolution phase.

    This model represents a table in a stable internal format, using
    a title, a list of visible headers, and a list of body rows.
    It may also perform basic self-validation when instantiated to
    reject clearly inconsistent data.
    """
    rows: list[ResolvedSectionTitleRow |
               ResolvedLabelValueRow] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.rows, list):
            raise TypeError("rows must be a list")

        for idx, row in enumerate(self.rows):
            if not isinstance(row,
                             (ResolvedSectionTitleRow,
                             ResolvedLabelValueRow)):
                raise TypeError(
                    f"Row {idx} must be ResolvedSectionTitleRow or ResolvedLabelValueRow."
                )

