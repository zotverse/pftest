# clerk.py
# PURF Utopia — Trillion-Request Hardened
# Logic: YOURS (Rich Domain, All examples) | Armor: Retries, Sanitization

import os
import json
import logging
import time
import google.generativeai as genai
from typing import Dict, Any

# --- 1. Startup Integrity & Logging ---
if not os.environ.get("GOOGLE_API_KEY"):
    raise RuntimeError("CRITICAL: GOOGLE_API_KEY environment variable is missing. Service cannot start.")

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Configure structured logging
logger = logging.getLogger("purf.clerk")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# USING YOUR AVAILABLE MODEL
MODEL = genai.GenerativeModel("gemini-2.5-flash-lite")

# --- 2. Helpers ---
def redact(text: str, length: int = 1000) -> str:
    """Redaction length increased to 1000 to see full JSON during debug."""
    if not text: return ""
    return text[:length] + ("..." if len(text) > length else "")

def clean_json_markdown(text: str) -> str:
    """Strip markdown fences and common prefixes; return plain JSON text."""
    if not text:
        return ""
    t = text.strip()

    # Remove triple-backtick fences if present
    if t.startswith("```"):
        lines = t.splitlines()
        if len(lines) >= 3:
            # Use actual newline character for join
            t = "\n".join(lines[1:-1]).strip()
        else:
            t = t.replace("```json", "").replace("```", "").strip()

    # Handle common "Here is the JSON:" prefixes from chat models
    lower = t.lower()
    prefixes = ("here is the json:", "here is the extracted json:", "json:", "output:")
    for p in prefixes:
        if lower.startswith(p):
            t = t[len(p):].strip()
            break
            
    return t

# --- 3. Domain Logic (ALL EXAMPLES) ---
SYSTEM_PROMPT = """
You are the PURF Clerk.

Your job is to extract ONLY explicitly stated facts into a strict JSON schema.

CRITICAL RULES:
- Do NOT infer.
- Do NOT convert time into money.
- Do NOT guess.
- Convert currency strings (e.g. "$5,000") to numbers (e.g. 5000).
- If not explicitly stated → null.
- Return JSON only.

SCHEMA (all keys required, use null when unknown):

{
  "actor": string | null,
  "payer": string | null,
  "beneficiary": string | null,
  "purchase_authority": true | false | null,
  "pain_description": string | null,
  "pain_magnitude": number | null,
  "solution_cost": number | null,
  "current_workaround_cost": number | null,
  "pain_frequency": "daily" | "weekly" | "monthly" | "yearly" | null,
  "engagement_frequency": "daily" | "weekly" | "monthly" | "yearly" | null,
  "mechanism_steps": [string] | null,
  "dependencies": [string] | null,
  "time_to_value": "instant" | "days" | "weeks" | "months" | null,
  "adoption_friction": "low" | "medium" | "high" | null
}

EXAMPLES:

Input: "Law firms pay us $5,000 per year."
Output: { "payer": "law firms", "solution_cost": 5000 }

Input: "This saves firms roughly $50,000 per year."
Output: { "pain_magnitude": 50000 }

Input: "Our system ingests case files and produces draft legal briefs."
Output: { "mechanism_steps": ["ingest case files", "produce draft legal briefs"] }

Input: "Partners approve the purchase."
Output: { "purchase_authority": true }

Input: "Associates use it daily."
Output: { "actor": "associates", "engagement_frequency": "daily" }

Input: "Manual reporting takes 10 hours every week."
Output: { "pain_description": "manual reporting takes 10 hours every week" }

Input: "Teams spend hours reconciling spreadsheets by hand."
Output: { "pain_description": "teams spend hours reconciling spreadsheets by hand" }

Input: "This improves productivity across the organization."
Output: { "pain_description": null }

Input: "We help teams work smarter and faster."
Output: { "pain_description": null }

Input: "It costs around $5k per year."
Output: { "solution_cost": null }

Input: "Pricing is between $3,000 and $6,000."
Output: { "solution_cost": null }

Input: "Six-figure savings."
Output: { "pain_magnitude": null }

Input: "Integrates directly with Salesforce and Slack."
Output: { "dependencies": ["salesforce", "slack"] }

Input: "Requires access to Stripe transaction data."
Output: { "dependencies": ["stripe transaction data"] }

Input: "Pulls data from the company’s Snowflake warehouse."
Output: { "dependencies": ["snowflake warehouse"] }

Input: "Legal teams use it daily, but the firm avoids regulatory penalties because of it."
Output: { "actor": "legal teams", "beneficiary": "firm" }

Input: "Engineers operate the system, but the company avoids costly outages."
Output: { "actor": "engineers", "beneficiary": "company" }

Input: "Compliance teams run this tool so the organization avoids audit fines."
Output: { "actor": "compliance teams", "beneficiary": "organization" }

Input: "Staff use it, but the business avoids revenue leakage."
Output: { "actor": "staff", "beneficiary": "business" }

Input: "Works better when more teams inside the company use it."
Output: { "mechanism_steps": null }

Input: "A collaborative workspace where everyone contributes knowledge."
Output: { "mechanism_steps": null }

Input: "Shared platform for teams to exchange information."
Output: { "mechanism_steps": null }
"""

ENUMS = {
    "pain_frequency": {"daily","weekly","monthly","yearly"},
    "engagement_frequency": {"daily","weekly","monthly","yearly"},
    "time_to_value": {"instant","days","weeks","months"},
    "adoption_friction": {"low","medium","high"},
}

REQUIRED_KEYS = [
    "actor","payer","beneficiary","purchase_authority",
    "pain_description","pain_magnitude","solution_cost",
    "current_workaround_cost","pain_frequency","engagement_frequency",
    "mechanism_steps","dependencies","time_to_value","adoption_friction"
]

def _canon_enum(val, allowed):
    if isinstance(val, str):
        v = val.lower().strip()
        return v if v in allowed else None
    return None

def extract_claims(text: str) -> Dict[str, Any]:
    # Corrected prompt construction (single backslash for newlines and quotes)
    prompt = SYSTEM_PROMPT + f"\n\nInput: \"{text}\""
    
    MAX_RETRIES = 3
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = MODEL.generate_content(
               prompt,
               generation_config={
                    "temperature": 0.0, # Strict determinism
                    "response_mime_type": "application/json"
                }
            )
            
            # Safe access to text
            raw = getattr(response, "text", "") or ""
            cleaned_raw = clean_json_markdown(raw).strip()
            
            # Debug log (redacted) - Using debug level for raw content
            logger.debug("Clerk raw output (redacted): %s", redact(cleaned_raw, 1000))

            if not cleaned_raw:
                raise ValueError("Empty cleaned model output")
            
            try:
                data = json.loads(cleaned_raw)
            except json.JSONDecodeError:
                logger.warning("JSON parse failed on cleaned output (redacted). Attempt %d", attempt)
                raise # Trigger retry
                
            # If successful, validate and return
            for k in REQUIRED_KEYS:
                data.setdefault(k, None)

            for k, allowed in ENUMS.items():
                data[k] = _canon_enum(data.get(k), allowed)
                
            return data

        except Exception as e:
            logger.warning(f"Clerk attempt {attempt} failed: {str(e)}")
            if attempt == MAX_RETRIES:
                logger.error("Clerk giving up after max retries.", exc_info=True)
                # Fail open (return nulls) so Guardrail catches it
                return {k: None for k in REQUIRED_KEYS}
            
            time.sleep(0.5 * (2 ** (attempt - 1)))
