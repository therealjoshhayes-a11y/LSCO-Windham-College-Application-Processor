from __future__ import annotations

import re


def normalize_name(raw_text: str) -> str:
    text = raw_text or ""
    text = text.upper()
    text = re.sub(r"[^A-Z'\- ]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
