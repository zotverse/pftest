# explanation_templates.py

FIELD_EXPLANATIONS = {
    "solution_cost": {
        "base": "A single, unambiguous annual dollar price was not stated.",
        "with_text": "You mentioned pricing ({excerpt}), but did not state a single annual dollar amount."
    },
    "pain_magnitude": {
        "base": "A single, unambiguous annual dollar value of the problem was not stated.",
        "with_text": "You described impact ({excerpt}), but did not state a single annual dollar value."
    },
    "mechanism_steps": {
        "base": "The step-by-step mechanism of how the system works was not clearly described.",
        "with_text": "You described the product ({excerpt}), but not as a clear sequence of steps."
    },
    "payer": {
        "base": "Who pays for this was not clearly stated.",
        "with_text": "You referenced customers ({excerpt}), but did not clearly state who pays."
    },
    "actor": {
        "base": "Who uses this was not clearly stated.",
        "with_text": "You referenced users ({excerpt}), but did not clearly state who uses the system."
    },
}
