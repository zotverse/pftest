# semantic_mapper.py
# Utopia V1: Passthrough Mapper
# The Clerk schema is already flat and canonical. We just pass it through.

from typing import Dict, Any

def map_claims(normalized: Dict[str, Any]) -> Dict[str, Any]:
    """
    Since Clerk v3 produces the exact flat schema we need,
    this mapper is a pure identity function for the relevant keys.
    """
    return {
        "actor": normalized.get("actor"),
        "payer": normalized.get("payer"),
        "beneficiary": normalized.get("beneficiary"),
        "purchase_authority": normalized.get("purchase_authority"),
        
        "pain_description": normalized.get("pain_description"),
        "pain_magnitude": normalized.get("pain_magnitude"),
        "solution_cost": normalized.get("solution_cost"),
        "current_workaround_cost": normalized.get("current_workaround_cost"),
        
        "pain_frequency": normalized.get("pain_frequency"),
        "engagement_frequency": normalized.get("engagement_frequency"),
        
        "mechanism_steps": normalized.get("mechanism_steps"),
        "dependencies": normalized.get("dependencies"),
        
        "time_to_value": normalized.get("time_to_value"),
        "adoption_friction": normalized.get("adoption_friction"),
    }
