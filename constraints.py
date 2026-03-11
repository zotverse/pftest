# constraints.py
# PURF Utopia — The Judge
# Logic: Hard economic rules. No AI. No guessing.

import hashlib
import json
from typing import Dict, Any, List

# ---------------------------------------------------------
# Utilities & Null Safety (THE FIX)
# ---------------------------------------------------------

def _safe_float(val):
    if isinstance(val, (int, float)):
        return float(val)
    return None  # Return None so logic can decide to SKIP

def _safe_str(val):
    if isinstance(val, str):
        return val.lower().strip()
    return ""

def _safe_list(val):
    if isinstance(val, list):
        return val
    return []

def merkle_root(obj: Any) -> str:
    # default=str handles objects that might not be natively serializable
    dump = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(dump).hexdigest()


def result(rule_id: str, status: str, fatal: bool,
           explanation: str, inputs: List[str]) -> Dict[str, Any]:
    return {
        "rule_id": rule_id,
        "status": status,        # PASS | FAIL | SKIP
        "fatal": fatal,          # only meaningful if FAIL
        "explanation": explanation,
        "inputs_used": inputs
    }


# ---------------------------------------------------------
# Tier 1 — Ontology
# ---------------------------------------------------------

def T1_1_actor_existence(c):
    actor = _safe_str(c.get("actor"))
    if not actor:
        return result("T1.1", "SKIP", False,
                      "Actor missing.", ["actor"])

    bad = ["everyone", "people", "users", "anyone", "companies"]
    if actor in bad:
        return result("T1.1", "FAIL", True,
                      "Actor is too vague.", ["actor"])

    return result("T1.1", "PASS", True,
                  "Actor is specific.", ["actor"])


def T1_2_actor_pain_plausible(c):
    actor = _safe_str(c.get("actor"))
    pain = _safe_str(c.get("pain_description"))

    if not actor or not pain:
        return result("T1.2", "SKIP", False,
                      "Cannot evaluate actor–pain plausibility.",
                      ["actor", "pain_description"])

    mismatches = [
        ("dentist", ["gpu", "kernel", "latency"]),
        ("student", ["enterprise procurement", "datacenter"]),
        ("teacher", ["server orchestration", "cloud billing"]),
    ]

    for role, terms in mismatches:
        if role in actor and any(t in pain for t in terms):
            return result("T1.2", "FAIL", True,
                          "Pain does not plausibly apply to actor.",
                          ["actor", "pain_description"])

    return result("T1.2", "PASS", True,
                  "Pain plausibly applies to actor.",
                  ["actor", "pain_description"])


def T1_3_payer_exists(c):
    if not c.get("payer"):
        return result("T1.3", "FAIL", True,
                      "No payer identified.", ["payer"])
    return result("T1.3", "PASS", True,
                  "Payer exists.", ["payer"])


def T1_4_purchase_authority(c):
    if not c.get("purchase_authority"):
        return result("T1.4", "FAIL", True,
                      "No purchase authority defined.",
                      ["purchase_authority"])
    return result("T1.4", "PASS", True,
                  "Purchase authority present.",
                  ["purchase_authority"])


# ---------------------------------------------------------
# Tier 2 — Economics
# ---------------------------------------------------------

def T2_1_economic_loop(c):
    payer = c.get("payer")
    beneficiary = c.get("beneficiary")
    pain = _safe_str(c.get("pain_description"))

    if not payer or not beneficiary or not pain:
        return result("T2.1", "SKIP", False,
                      "Cannot evaluate economic loop.",
                      ["payer", "beneficiary", "pain_description"])

    if payer == beneficiary:
        return result("T2.1", "PASS", True,
                      "Payer and beneficiary aligned.",
                      ["payer", "beneficiary"])

    if "because" not in pain:
        return result("T2.1", "FAIL", True,
                      "No causal reason payer would pay for beneficiary pain.",
                      ["payer", "beneficiary", "pain_description"])

    return result("T2.1", "PASS", True,
                  "Causal economic loop exists.",
                  ["payer", "beneficiary"])


def T2_2_solvency(c):
    pain = _safe_float(c.get("pain_magnitude"))
    cost = _safe_float(c.get("solution_cost"))

    if pain is None or cost is None:
        return result("T2.2", "SKIP", False,
                      "Missing economic values.",
                      ["pain_magnitude", "solution_cost"])

    # Protect against zero division or weird logic
    if cost > 0 and pain < 3 * cost:
        return result("T2.2", "FAIL", True,
                      "ROI less than 3x.",
                      ["pain_magnitude", "solution_cost"])

    return result("T2.2", "PASS", True,
                  "Solvency valid.",
                  ["pain_magnitude", "solution_cost"])


def T2_3_status_quo(c):
    sq = _safe_float(c.get("current_workaround_cost"))
    cost = _safe_float(c.get("solution_cost"))

    if sq is None or cost is None:
        return result("T2.3", "SKIP", False,
                      "Cannot compare status quo.",
                      ["current_workaround_cost", "solution_cost"])

    if cost >= sq:
        return result("T2.3", "FAIL", False,
                      "Solution not better than status quo.",
                      ["current_workaround_cost", "solution_cost"])

    return result("T2.3", "PASS", False,
                  "Improvement over status quo.",
                  ["current_workaround_cost", "solution_cost"])


def T2_4_frequency(c):
    pain_f = c.get("pain_frequency")
    eng_f = c.get("engagement_frequency")

    if not pain_f or not eng_f:
        return result("T2.4", "SKIP", False,
                      "Frequency unknown.",
                      ["pain_frequency", "engagement_frequency"])

    order = ["yearly", "monthly", "weekly", "daily"]
    
    if pain_f not in order or eng_f not in order:
         return result("T2.4", "SKIP", False, "Unknown frequency format", ["pain_frequency"])

    if order.index(eng_f) > order.index(pain_f):
        return result("T2.4", "FAIL", False,
                      "Engagement exceeds pain frequency.",
                      ["pain_frequency", "engagement_frequency"])

    return result("T2.4", "PASS", False,
                  "Frequency aligned.",
                  ["pain_frequency", "engagement_frequency"])


def T2_5_budget_locality(c):
    payer = _safe_str(c.get("payer"))
    cost = _safe_float(c.get("solution_cost"))

    if not payer or cost is None:
        return result("T2.5", "SKIP", False,
                      "Cannot evaluate budget locality.",
                      ["payer", "solution_cost"])

    if "student" in payer and cost > 2000:
        return result("T2.5", "FAIL", True,
                      "Budget mismatch for payer.",
                      ["payer", "solution_cost"])

    return result("T2.5", "PASS", True,
                  "Budget plausible.",
                  ["payer", "solution_cost"])


# ---------------------------------------------------------
# Tier 3 — Mechanism
# ---------------------------------------------------------

def T3_1_mechanism_complete(c):
    steps = _safe_list(c.get("mechanism_steps"))
    if not steps:
        return result("T3.1", "FAIL", True,
                      "No mechanism steps.",
                      ["mechanism_steps"])
    return result("T3.1", "PASS", True,
                  "Mechanism present.",
                  ["mechanism_steps"])


def T3_2_no_magic(c):
    # THE FIX: Use _safe_list to prevent .join(None) crash
    raw_steps = _safe_list(c.get("mechanism_steps"))
    steps = " ".join(str(x) for x in raw_steps).lower()
    
    if not steps:
        return result("T3.2", "SKIP", False,
                      "Cannot evaluate mechanism.",
                      ["mechanism_steps"])

    suspicious = ["predicts", "decides", "automatically"]
    if any(s in steps for s in suspicious) and "data" not in steps:
        return result("T3.2", "FAIL", True,
                      "Magic intelligence without data source.",
                      ["mechanism_steps"])

    return result("T3.2", "PASS", True,
                  "Mechanism grounded.",
                  ["mechanism_steps"])


def T3_3_dependency(c):
    deps = _safe_list(c.get("dependencies"))
    if not deps:
        return result("T3.3", "SKIP", False,
                      "No dependencies listed.",
                      ["dependencies"])
    return result("T3.3", "PASS", True,
                  "Dependencies plausible.",
                  ["dependencies"])


def T3_4_single_player(c):
    raw_steps = _safe_list(c.get("mechanism_steps"))
    steps = " ".join(str(x) for x in raw_steps).lower()
    
    if "marketplace" in steps or "network" in steps:
        return result("T3.4", "FAIL", False,
                      "Requires network before value.",
                      ["mechanism_steps"])
    return result("T3.4", "PASS", False,
                  "Single player utility present.",
                  ["mechanism_steps"])


def T3_5_time_to_value(c):
    ttv = c.get("time_to_value")
    if not ttv:
        return result("T3.5", "SKIP", False,
                      "Time to value unknown.",
                      ["time_to_value"])
    return result("T3.5", "PASS", False,
                  "Time to value acceptable.",
                  ["time_to_value"])


def T3_6_adoption_friction(c):
    friction = c.get("adoption_friction")
    value = _safe_float(c.get("pain_magnitude"))

    if not friction or value is None:
        return result("T3.6", "SKIP", False,
                      "Cannot evaluate friction.",
                      ["adoption_friction", "pain_magnitude"])

    if friction == "high" and value < 50000:
        return result("T3.6", "FAIL", False,
                      "High friction not justified by value.",
                      ["adoption_friction", "pain_magnitude"])

    return result("T3.6", "PASS", False,
                  "Adoption friction acceptable.",
                  ["adoption_friction"])


def T3_7_risk_concentration(c):
    deps = _safe_list(c.get("dependencies"))
    if len(deps) == 1:
        return result("T3.7", "FAIL", False,
                      "Single point of failure.",
                      ["dependencies"])
    return result("T3.7", "PASS", False,
                  "Risk distributed.",
                  ["dependencies"])


# ---------------------------------------------------------
# Tier 4 — Coherence
# ---------------------------------------------------------

def T4_1_contradiction(c):
    actor = c.get("actor")
    payer = c.get("payer")
    cost = _safe_str(str(c.get("solution_cost", "")))

    if actor == payer and "free" in cost:
        return result("T4.1", "FAIL", True,
                      "Free usage and paid usage conflict.",
                      ["actor", "payer", "solution_cost"])

    return result("T4.1", "PASS", True,
                  "No obvious contradictions.",
                  ["actor", "payer"])


def T4_2_temporal(c):
    raw_steps = _safe_list(c.get("mechanism_steps"))
    steps = " ".join(str(x) for x in raw_steps).lower()

    if "before" in steps and "after" in steps:
        return result("T4.2", "FAIL", False,
                      "Temporal contradiction in steps.",
                      ["mechanism_steps"])
    return result("T4.2", "PASS", False,
                  "Temporal order valid.",
                  ["mechanism_steps"])


# ---------------------------------------------------------
# RULE REGISTRY
# ---------------------------------------------------------

RULES = [
    T1_1_actor_existence,
    T1_2_actor_pain_plausible,
    T1_3_payer_exists,
    T1_4_purchase_authority,
    T2_1_economic_loop,
    T2_2_solvency,
    T2_3_status_quo,
    T2_4_frequency,
    T2_5_budget_locality,
    T3_1_mechanism_complete,
    T3_2_no_magic,
    T3_3_dependency,
    T3_4_single_player,
    T3_5_time_to_value,
    T3_6_adoption_friction,
    T3_7_risk_concentration,
    T4_1_contradiction,
    T4_2_temporal,
]


# ---------------------------------------------------------
# Tribunal Entry
# ---------------------------------------------------------

def run_tribunal(claims: Dict[str, Any]) -> Dict[str, Any]:
    # We pass the full claims dict to every rule
    results = [rule(claims) for rule in RULES]

    verdict = "PASS"
    for r in results:
        # If any FATAL rule fails, the whole verdict is FAIL
        if r["status"] == "FAIL" and r["fatal"]:
            verdict = "FAIL"
            # We don't break immediately in this version because we want
            # to see all feedback, but you can break if you want fail-fast.
            # break 

    commitment = merkle_root({
        "claims": claims,
        "rule_results": results,
        "verdict": verdict
    })

    return {
        "verdict": verdict,
        "rule_results": results,
        "commitment": commitment
    }
