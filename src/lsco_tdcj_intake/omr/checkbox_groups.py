"""Checkbox group definitions and interpretation for LSCO TDCJ forms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lsco_tdcj_intake.omr.checkbox import CheckboxOMRResult


GroupRule = Literal["exactly_one", "zero_or_more", "one_or_more"]


@dataclass(frozen=True)
class CheckboxOption:
    value: str
    field_id: str
    label: str


@dataclass(frozen=True)
class CheckboxGroup:
    page_number: int
    group_id: str
    label: str
    rule: GroupRule
    options: tuple[CheckboxOption, ...]


CHECKBOX_GROUPS: dict[tuple[int, str], CheckboxGroup] = {
    (1, "student_type"): CheckboxGroup(
        page_number=1,
        group_id="student_type",
        label="Student Type",
        rule="exactly_one",
        options=(
            CheckboxOption("first_time", "p1_student_type_first_time", "First Time"),
            CheckboxOption("returning", "p1_student_type_returning", "Returning"),
            CheckboxOption("transfer", "p1_student_type_transfer", "Transfer"),
        ),
    ),
    (1, "term"): CheckboxGroup(
        page_number=1,
        group_id="term",
        label="Term",
        rule="exactly_one",
        options=(
            CheckboxOption("fall", "p1_term_fall", "Fall"),
            CheckboxOption("spring", "p1_term_spring", "Spring"),
            CheckboxOption("summer", "p1_term_summer", "Summer"),
        ),
    ),
}


def get_checkbox_group(page_number: int, group_id: str) -> CheckboxGroup:
    key = (page_number, group_id)

    if key not in CHECKBOX_GROUPS:
        known = ", ".join(f"page {p} / {g}" for p, g in sorted(CHECKBOX_GROUPS))
        raise KeyError(f"Unknown checkbox group page={page_number} group={group_id!r}. Known: {known}")

    return CHECKBOX_GROUPS[key]


def interpret_checkbox_group(
    group: CheckboxGroup,
    results: dict[str, CheckboxOMRResult],
) -> dict:
    selected: list[str] = []
    uncertain: list[str] = []
    field_decisions: dict[str, dict] = {}

    field_to_option = {option.field_id: option for option in group.options}

    for option in group.options:
        result = results[option.field_id]

        field_decisions[option.field_id] = {
            "value": option.value,
            "label": option.label,
            "decision": result.decision,
            "checked": result.checked,
            "confidence": result.confidence,
            "dark_pixel_ratio": result.dark_pixel_ratio,
            "outer_box": result.outer_box,
            "interior_box": result.interior_box,
        }

        if result.checked is True:
            selected.append(option.value)
        elif result.checked is None:
            uncertain.append(option.value)

    if uncertain:
        status = "needs_review"
        message = f"Uncertain checkbox result(s): {', '.join(uncertain)}"
    elif group.rule == "exactly_one" and len(selected) == 1:
        status = "valid"
        message = f"Selected {selected[0]}"
    elif group.rule == "exactly_one" and len(selected) == 0:
        status = "invalid"
        message = "No option selected; exactly one required."
    elif group.rule == "exactly_one" and len(selected) > 1:
        status = "invalid"
        message = f"Multiple options selected: {', '.join(selected)}"
    elif group.rule == "one_or_more" and len(selected) >= 1:
        status = "valid"
        message = f"Selected {', '.join(selected)}"
    elif group.rule == "one_or_more":
        status = "invalid"
        message = "No option selected; one or more required."
    else:
        status = "valid"
        message = f"Selected {', '.join(selected)}" if selected else "No options selected."

    return {
        "page_number": group.page_number,
        "group_id": group.group_id,
        "label": group.label,
        "rule": group.rule,
        "status": status,
        "message": message,
        "selected": selected,
        "uncertain": uncertain,
        "fields": field_decisions,
    }