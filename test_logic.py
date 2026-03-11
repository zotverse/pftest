from constraints import run_tribunal
import json

# CASE 1: The Bad Founder (Broke Student Payer)
bad_case = {
    "raw_text": "I sell note taking apps to students for $500.",
    "entities": [
        {"name": "Students", "role": "Payer", "type": "Student"}
    ],
    "economics": {
        "price_annualized": 500.0,
        "pain_proxy_annualized": 0.0, # Undefined value
        "currency": "USD"
    },
    "mechanics": {
        "inputs": [],
        "outputs": ["Notes"],
        "magic_word_count": 0,
        "description_length": 10
    }
}

# CASE 2: The Good Founder (Enterprise)
good_case = {
    "raw_text": "I sell compliance software to banks.",
    "entities": [
        {"name": "Bank", "role": "Payer", "type": "Business"}
    ],
    "economics": {
        "price_annualized": 10000.0,
        "pain_proxy_annualized": 500000.0, # Regulatory fine risk
        "currency": "USD"
    },
    "mechanics": {
        "inputs": ["Transaction Logs"],
        "outputs": ["Audit Report"],
        "magic_word_count": 0,
        "description_length": 50
    }
}

print("--- JUDGING BAD CASE ---")
result_bad = run_tribunal(bad_case)
print(f"VERDICT: {result_bad['verdict']}")
if result_bad['verdict'] == 'FAIL':
    for r in result_bad['trace']:
        if not r['passed']:
            print(f"  [X] {r['reason']}")

print("\n--- JUDGING GOOD CASE ---")
result_good = run_tribunal(good_case)
print(f"VERDICT: {result_good['verdict']}")
