# canonicalizer.py
# Safe type coercion layer between Normalizer and Mapper.
# Converts only unambiguous literals. Preserves uncertainty.

import re
from typing import Dict, Any

NUMERIC_FIELDS = [
    "pain_magnitude",
    "solution_cost",
    "current_workaround_cost",
]

ENUM_FIELDS = {
    "pain_frequency": {"yearly","monthly","weekly","daily"},
    "engagement_frequency": {"yearly","monthly","weekly","daily"},
    "time_to_value": {"instant","days","weeks","months"},
    "adoption_friction": {"low","medium","high"},
}

def _to_float(val):
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        v = val.strip().lower().replace("$", "").replace(",", "")
        # FIX: Correct regex for numbers (no double backslashes in raw string)
        if re.fullmatch(r"\d+(\.\d+)?", v):
            return float(v)
    return None

def _canon_enum(val, allowed):
    if isinstance(val, str):
        v = val.strip().lower()
        return v if v in allowed else None
    return None

def canonicalize(claims: Dict[str, Any]) -> Dict[str, Any]:
    c = claims.copy()

    # --- Numeric fields ---
    for f in NUMERIC_FIELDS:
        c[f] = _to_float(c.get(f))

    # --- Enum fields ---
    for f, allowed in ENUM_FIELDS.items():
        c[f] = _canon_enum(c.get(f), allowed)

    # --- Boolean field ---
    # Ensure it's a bool; otherwise None
    if not isinstance(c.get("purchase_authority"), bool):
        c["purchase_authority"] = None

    return c
