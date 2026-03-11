# normalizer.py
# Pure structural firewall between Clerk and Mapper.

from typing import Dict, Any

REQUIRED_KEYS = [
    "actor",
    "payer",
    "beneficiary",
    "purchase_authority",
    "pain_description",
    "pain_magnitude",
    "solution_cost",
    "current_workaround_cost",
    "pain_frequency",
    "engagement_frequency",
    "mechanism_steps",
    "dependencies",
    "time_to_value",
    "adoption_friction" 
    # REMOVED "network_required" - Clerk does not produce this
]

def _is_list_or_none(x):
    return x is None or isinstance(x, list)

def normalize_claims(claims: Dict[str, Any]) -> Dict[str, Any]:
    """
    Utopia Normalizer.
    Guarantees structural integrity without semantic mutation.
    """

    normalized = {}
    metadata = {
        "missing_keys": [],
        "type_errors": [],
    }

    # --- 1. Ensure all keys exist ---
    for key in REQUIRED_KEYS:
        if key not in claims:
            normalized[key] = None
            metadata["missing_keys"].append(key)
        else:
            normalized[key] = claims[key]

    # --- 2. Type guards ---
    if not _is_list_or_none(normalized["mechanism_steps"]):
        metadata["type_errors"].append("mechanism_steps")
        normalized["mechanism_steps"] = None

    if not _is_list_or_none(normalized["dependencies"]):
        metadata["type_errors"].append("dependencies")
        normalized["dependencies"] = None

    # purchase_authority must be bool or None
    if not isinstance(normalized["purchase_authority"], (bool, type(None))):
        metadata["type_errors"].append("purchase_authority")
        normalized["purchase_authority"] = None

    # Scalars must not be list/dict
    scalar_fields = [
        "actor",
        "payer",
        "beneficiary",
        "pain_description",
        "pain_magnitude",
        "solution_cost",
        "current_workaround_cost",
        "pain_frequency",
        "engagement_frequency",
        "time_to_value",
        "adoption_friction"
    ]

    for f in scalar_fields:
        if isinstance(normalized[f], (list, dict)):
            metadata["type_errors"].append(f)
            normalized[f] = None

    normalized["_meta"] = metadata
    return normalized
