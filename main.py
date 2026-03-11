# main.py
# PURF Utopia Orchestrator — Trillion-Request Grade (Merged & Fixed)

import logging
import os
import json
import hashlib
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Logic Imports ---
from clerk import extract_claims
from normalizer import normalize_claims
from canonicalizer import canonicalize
from semantic_mapper import map_claims
from constraints import run_tribunal
from explanation_templates import FIELD_EXPLANATIONS
from database import save_submission, save_snapshot

# --- Crypto/Signing Imports ---
from supabase import create_client, Client
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
from dotenv import load_dotenv

# --- 1. CONFIGURATION ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("purf.main")

if os.environ.get("PURF_ENV") == "dev":
    logger.setLevel(logging.DEBUG)

# Supabase Client for Signing (HTTP)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DEV_SIGNER_ID = os.environ.get("DEV_SIGNER_ID", "dev:ed25519:v1")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase credentials missing. Receipts will NOT be generated.")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

RULESET_VERSION = "utopia_v3"
EXPLANATION_VERSION = "opinion_writer_v1"
MAX_PAYLOAD_CHARS = 20000

# --- 2. CRYPTO HELPERS ---

def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_hex(b: bytes):
    return hashlib.sha256(b).hexdigest()

def get_signing_key():
    """Loads local dev key. In Prod, this would call KMS."""
    if not os.path.exists("dev_signing_key.hex"):
        return None
    with open("dev_signing_key.hex", "r") as f:
        return SigningKey(f.read().strip(), encoder=HexEncoder)

def async_sign_receipt(submission_id: str, founder_id: str, text: str, verdict_data: dict):
    """
    Background Task: 
    1. Syncs Submission to Cloud DB.
    2. Creates Event -> Links Hash -> Signs Receipt -> Saves.
    """
    if not supabase: return

    try:
        sk = get_signing_key()
        if not sk:
            logger.error("No signing key found. Cannot sign receipt.")
            return

        # A. SYNC SUBMISSION (The Fix for Foreign Key Error)
        # We try to insert. If it exists, we ignore (upsert behavior via ignore_duplicates if possible, 
        # but standard insert might fail if exists, so we catch).
        try:
            supabase.table("submissions").insert({
                "id": str(submission_id),
                "founder_id": founder_id,
                "raw_text": text
            }).execute()
        except Exception as e:
            # If it fails, it might already exist. We proceed.
            # logger.debug(f"Submission sync note: {e}")
            pass

        # B. Get Last Event Hash (Blockchain Link)
        r = supabase.table("events").select("event_hash").eq("submission_id", submission_id).order("created_at", desc=True).limit(1).execute()
        prev_hash = r.data[0]["event_hash"] if r.data else ""

        # C. Create Verdict Event
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        payload = {
            "verdict": verdict_data["verdict"],
            "rule": verdict_data.get("rule"),
            "commitment": verdict_data.get("commitment")
        }
        envelope = {"type": "VERDICT", "payload": payload, "timestamp": now}
        
        payload_hash = sha256_hex(canonical_bytes(envelope))
        combined = (prev_hash or "") + payload_hash + now
        event_hash = hashlib.sha256(combined.encode()).hexdigest()

        event_data = {
            "submission_id": submission_id,
            "event_type": "VERDICT",
            "payload": envelope,
            "created_at": now,
            "event_hash": event_hash
        }
        r = supabase.table("events").insert(event_data).execute()
        event_id = r.data[0]["id"]

        # D. Sign Receipt
        receipt = {
            "receipt_id": None, # assigned by DB
            "submission_id": str(submission_id),
            "event_id": str(event_id),
            "event_hash": event_hash,
            "rule_version": RULESET_VERSION,
            "verdict": verdict_data["verdict"],
            "timestamp": now
        }
        
        signature = sk.sign(canonical_bytes(receipt)).signature.hex()

        # E. Save Receipt
        supabase.table("receipts").insert({
            "submission_id": submission_id,
            "event_id": event_id,
            "receipt_json": receipt,
            "signer_key_id": DEV_SIGNER_ID,
            "signature": signature
        }).execute()
        
        logger.info(f"Receipt signed and stored for {submission_id}")

    except Exception as e:
        logger.error(f"Failed to sign receipt: {e}", exc_info=True)


# --- 3. API APP ---

app = FastAPI(title="PURF Engine — Utopia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RawSubmission(BaseModel):
    founder_id: str
    text: str

def extract_excerpt(text: str, field: str) -> str | None:
    keywords = {
        "solution_cost": ["$", "price", "cost", "subscription"],
        "pain_magnitude": ["save", "loss", "waste", "hours"],
        "mechanism_steps": ["ingest", "process", "generate", "analyze", "platform"],
        "payer": ["pay", "customer", "buyer", "client"],
        "actor": ["use", "user", "team", "staff"],
    }
    t = text.lower()
    for kw in keywords.get(field, []):
        if kw in t: return kw
    return None

def explain_verdict(mapped: dict, verdict: dict, raw_text: str) -> dict:
    understood = {k: v for k, v in mapped.items() if v not in (None, [], {})}
    unclear = {}

    for field, value in mapped.items():
        if value in (None, [], {}) and field in FIELD_EXPLANATIONS:
            tmpl = FIELD_EXPLANATIONS[field]
            excerpt = extract_excerpt(raw_text, field)
            msg = tmpl["with_text"].format(excerpt=excerpt) if excerpt else tmpl["base"]
            unclear[field] = msg

    if verdict["verdict"] == "UNPROCESSABLE":
        summary = "We could not evaluate this because we found insufficient factual information to form a business model."
    elif verdict["verdict"] == "FAIL":
        summary = "The economics described do not close based on the facts provided."
    else:
        summary = "The economics described are compelling."

    return {
        "summary": summary,
        "what_we_understood": understood,
        "what_was_unclear": unclear,
    }

def render_founder_message(explanation: dict) -> str:
    lines = []
    if explanation.get("summary"):
        lines.append(explanation["summary"])
    if explanation.get("what_we_understood"):
        lines.append("\\nWe understood your business as follows:")
        for k, v in explanation["what_we_understood"].items():
            val_str = str(v)
            if isinstance(v, list): val_str = ", ".join(v)
            if k == "solution_cost" and isinstance(v, (int, float)): val_str = f"${v:,.0f}"
            if k == "pain_magnitude" and isinstance(v, (int, float)): val_str = f"${v:,.0f}"
            lines.append(f"- {k.replace('_',' ')}: {val_str}")
    if explanation.get("what_was_unclear"):
        lines.append("\\nWhat was unclear:")
        for msg in explanation["what_was_unclear"].values():
            lines.append(f"- {msg}")
    return "\\n".join(lines)

@app.post("/submit")
async def process_submission(payload: RawSubmission, background_tasks: BackgroundTasks):
    """
    Main Entry Point.
    """
    if len(payload.text) > MAX_PAYLOAD_CHARS:
        raise HTTPException(status_code=413, detail="Submission too large")

    submission_id = save_submission(payload.founder_id, payload.text)

    # 1. Extraction
    raw_claims = extract_claims(payload.text)
    normalized = normalize_claims(raw_claims)
    canonical = canonicalize(normalized)
    mapped = map_claims(canonical)

    # 2. Guardrail
    non_null_count = sum(1 for v in mapped.values() if v not in (None, [], {}))
    verdict = {"verdict": "UNPROCESSABLE"}

    if non_null_count >= 2:
        # 3. Judge (Only if passable)
        verdict = run_tribunal(mapped)

    # 4. Snapshot & Sign
    save_snapshot(
        submission_id=submission_id,
        normalized=normalized,
        canonical=canonical,
        mapped=mapped,
        verdict=verdict,
        ruleset_version=RULESET_VERSION,
        explanation_version=EXPLANATION_VERSION
    )
    
    # TRIGGER ASYNC SIGNING (UPDATED: Now passes payload info)
    background_tasks.add_task(async_sign_receipt, submission_id, payload.founder_id, payload.text, verdict)

    # 5. Response
    explanation_block = explain_verdict(mapped, verdict, payload.text)
    founder_message = render_founder_message(explanation_block)

    return {
        "submission_id": submission_id,
        "verdict": verdict["verdict"],
        "ruleset_version": RULESET_VERSION,
        "explanation_version": EXPLANATION_VERSION,
        "message": founder_message,
        "receipt_status": "pending_signature"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
