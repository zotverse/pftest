from clerk import extract_claims
import json

text = "I am building a dashboard for Enterprise CTOs. We charge $50k/year. It replaces 2 full-time analysts who cost $200k/year. We ingest AWS logs and output cost reports."

print("--- SENDING TO GEMINI ---")
data = extract_claims(text)
print(json.dumps(data, indent=2))
