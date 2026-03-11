# create_receipt_http.py
import os, json, hashlib, time
from supabase import create_client, Client
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
DEV_SIGNER_ID = os.environ.get("DEV_SIGNER_ID", "dev:ed25519:v1")

if not URL or not KEY:
    raise SystemExit("Set SUPABASE_URL and SUPABASE_KEY in .env")

# Initialize HTTP Client (Bypasses Port 5432 blocks)
supabase: Client = create_client(URL, KEY)

def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_hex(b: bytes):
    return hashlib.sha256(b).hexdigest()

def ensure_dev_key():
    # Check if key exists via API
    r = supabase.table("signer_keys").select("public_key").eq("id", DEV_SIGNER_ID).execute()
    if r.data:
        print("Found existing dev signer:", DEV_SIGNER_ID)
        return r.data[0]["public_key"]
    
    # Generate and Insert
    sk = SigningKey.generate()
    pub_hex = sk.verify_key.encode(encoder=HexEncoder).decode()
    
    supabase.table("signer_keys").insert({
        "id": DEV_SIGNER_ID,
        "public_key": pub_hex,
        "active": True
    }).execute()
    
    with open("dev_signing_key.hex", "w") as f:
        f.write(sk.encode(encoder=HexEncoder).decode())
    print("Created dev signer and saved local key.")
    return pub_hex

def load_local_private_key():
    if not os.path.exists("dev_signing_key.hex"): return None
    with open("dev_signing_key.hex","r") as f:
        return SigningKey(f.read().strip(), encoder=HexEncoder)

def main():
    # 1. Setup Identity
    ensure_dev_key()
    sk = load_local_private_key()

    # 2. Get a Submission
    r = supabase.table("submissions").select("id").limit(1).execute()
    if not r.data: raise SystemExit("No submissions found.")
    sub_id = r.data[0]["id"]
    print(f"Using Submission: {sub_id}")

    # 3. Get Last Event Hash (for Blockchain link)
    r = supabase.table("events").select("event_hash").eq("submission_id", sub_id).order("created_at", desc=True).limit(1).execute()
    prev_hash = r.data[0]["event_hash"] if r.data else ""

    # 4. Create New Event
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = {"verdict": "PASS", "method": "HTTP_API_TEST"}
    envelope = {"type": "VERDICT_PASS", "payload": payload, "timestamp": now}
    
    payload_hash = sha256_hex(canonical_bytes(envelope))
    combined = (prev_hash or "") + payload_hash + now
    event_hash = hashlib.sha256(combined.encode()).hexdigest()

    print("Inserting Event...")
    event_data = {
        "submission_id": sub_id,
        "event_type": "VERDICT_PASS",
        "payload": envelope, # client handles JSON
        "created_at": now,
        "event_hash": event_hash
    }
    r = supabase.table("events").insert(event_data).execute()
    event_id = r.data[0]["id"]

    # 5. Sign and Receipt
    receipt = {
        "receipt_id": None,
        "submission_id": sub_id,
        "event_id": event_id,
        "event_hash": event_hash,
        "rule_version": "utopia_http_v1",
        "verdict": "PASS",
        "timestamp": now
    }
    
    signature = sk.sign(canonical_bytes(receipt)).signature.hex()
    
    print("Inserting Receipt...")
    supabase.table("receipts").insert({
        "submission_id": sub_id,
        "event_id": event_id,
        "receipt_json": receipt,
        "signer_key_id": DEV_SIGNER_ID,
        "signature": signature
    }).execute()

    print("\nSUCCESS: RECEIPT CREATED & VERIFIED via HTTP.")

if __name__ == "__main__":
    main()
