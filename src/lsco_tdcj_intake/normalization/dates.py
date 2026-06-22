from __future__ import annotations

import re


def normalize_mmddyyyy(raw_text: str) -> str:
    digits = re.sub(r"\D+", "", raw_text or "")

    if len(digits) == 8:
        return f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"

    return digits


def is_mmddyyyy(value: str) -> bool:
    return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", value or ""))
