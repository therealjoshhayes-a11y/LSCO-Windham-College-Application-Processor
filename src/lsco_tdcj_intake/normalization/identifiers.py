from __future__ import annotations

import re


def digits_only(raw_text: str) -> str:
    return re.sub(r"\D+", "", raw_text or "")


def normalize_ssn(raw_text: str) -> str:
    return digits_only(raw_text)


def normalize_tdcj_number(raw_text: str) -> str:
    return digits_only(raw_text)


def normalize_year(raw_text: str) -> str:
    digits = digits_only(raw_text)
    return digits[:4]


def has_digits(value: str) -> bool:
    return bool(value) and value.isdigit()