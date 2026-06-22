from __future__ import annotations

import re


US_STATE_ABBREVIATIONS: set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def normalize_state_abbrev(raw_text: str) -> str:
    letters = re.sub(r"[^A-Za-z]+", "", raw_text or "").upper()
    return letters[:2]


def is_valid_state_abbrev(value: str) -> bool:
    return value in US_STATE_ABBREVIATIONS


def normalize_education_text(raw_text: str) -> str:
    text = raw_text or ""
    text = text.upper()
    text = re.sub(r"[^A-Z0-9'\- .,/&]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

