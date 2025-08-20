import csv
import json
import os
import openai
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

INPUT_FILE = "data/devto_quality_filtered.csv"
OUTPUT_FILE = "data/new_platforms_wisdom_index.csv"
MODEL = "gpt-4"
RATE_LIMIT_DELAY = 1.5  # seconds between requests

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set. Please create a .env file with your OpenAI API key.")

# Ensure data directory exists
from pathlib import Path
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

COLUMNS = [
    "description",
    "rationale",
    "use_case",
    "impact_area",
    "transferability_score",
    "actionability_rating",
    "evidence_strength",
    "type_(form)",
    "tag_(application)",
    "unique?",
    "role",
    "function",
    "company",
    "industry",
    "country",
    "date",
    "source_(interview_#/_name)",
    "link",
    "notes"
]

VALID_TYPES = {"pattern", "warning", "rule-of-thumb", "cue", "workaround", "checklist item"}
MAX_USE_CASE_LENGTH = 6  # words

def build_prompt(row):
    return f"""
You are a tacit knowledge extractor for a professional Wisdom Index. Extract ONLY non-obvious, experience-based insights that can only be learned through doing.

**REJECT if the insight is:**
- Common sense or obvious (e.g., "work hard", "be honest", "set boundaries")
- Generic motivational advice
- Personal life advice unrelated to business
- Too vague or non-actionable
- Related to one-time specific situations that don't apply broadly

**ACCEPT only insights that are:**
- Specific tactical knowledge learned through experience
- Non-obvious workarounds, patterns, or techniques
- Business-specific insights that can be applied by others
- Concrete, actionable advice with clear reasoning

Return a JSON object with these 19 fields (use "nan" where unknown). Rules:
- description: MUST start with a directive verb in present tense ("Avoid...", "Use...", "Track...", etc.)
- rationale: explain WHY the tactic works (the specific mechanism or reasoning)
- use_case: max 6 words describing the specific scenario
- impact_area: e.g. Efficiency, Risk, Revenue, Retention
- transferability_score and actionability_rating: integers from 1–5 only
- evidence_strength: one of Anecdotal, Observed, Data-backed, Peer-validated
- type_(form): one of {sorted(VALID_TYPES)}
- tag_(application): 1 short, normalized tag (e.g. Deal Control, Time Management)
- unique?: Y/N — is this highly context-specific?
- preserve these exactly: date, link, source_(interview_#/_name), notes

Example input:
"{row['description']}"

Metadata:
source: {row.get("source_(interview_#/_name)", "")}
link: {row.get("link", "")}
date: {row.get("date", "")}
notes: {row.get("notes", "")}
    """.strip()

def process_row(row):
    if not row.get("description") or len(row["description"]) < 90:
        return None
    
    # Pre-filter obvious or personal content
    description = row.get("description", "").lower()
    
    # Reject obvious/common sense content
    obvious_phrases = [
        "work hard", "be honest", "set boundaries", "communicate", 
        "be professional", "be respectful", "be organized", "be prepared",
        "work life balance", "time management", "stress management",
        "be patient", "be persistent", "be confident", "be positive"
    ]
    
    if any(phrase in description for phrase in obvious_phrases):
        return None
    
    # Reject personal life advice
    personal_phrases = [
        "personal", "family", "relationship", "marriage", "dating",
        "health", "exercise", "diet", "sleep", "hobby", "vacation"
    ]
    
    if any(phrase in description for phrase in personal_phrases):
        return None

    try:
        messages = [
            {"role": "system", "content": "You extract business-relevant tacit knowledge from real-world data."},
            {"role": "user", "content": build_prompt(row)}
        ]
        response = openai.chat.completions.create(
            model=MODEL,
            temperature=0.3,
            messages=messages
        )
        content = response.choices[0].message.content.strip()
        if "DISCARD" in content.upper():
            return None

        obj = json.loads(content)
        result = {col: obj.get(col, "nan") for col in COLUMNS}

        # Enforce numeric limits
        if not result["description"].lower().startswith(
            ("avoid", "use", "track", "document", "create", "establish", "schedule", "prioritize", "reduce", "require")
        ):
            return None
        if result["use_case"].count(" ") >= MAX_USE_CASE_LENGTH:
            return None
        if result["type_(form)"].strip().lower() not in VALID_TYPES:
            return None
        if result["transferability_score"] not in [1, 2, 3, 4, 5]:
            return None
        if result["actionability_rating"] not in [1, 2, 3, 4, 5]:
            return None
        
        # Quality check: ensure rationale is specific and non-obvious
        rationale = result.get("rationale", "").lower()
        if len(rationale) < 50:  # Too short
            return None
        
        # Reject generic rationales
        generic_rationales = [
            "it's important", "it's essential", "it's necessary", "it's good practice",
            "it helps", "it works", "it's effective", "it's beneficial",
            "because it's right", "because it's professional", "because it's ethical"
        ]
        
        if any(phrase in rationale for phrase in generic_rationales):
            return None

        return result

    except Exception as e:
        print(f"⚠️ Error processing row: {e}")
        return None

def main():
    with open(INPUT_FILE, newline='', encoding='utf-8') as infile, \
         open(OUTPUT_FILE, "w", newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=COLUMNS)
        writer.writeheader()

        for i, row in enumerate(reader, 1):
            print(f"🔍 Row {i:03d}...", end=" ")
            result = process_row(row)
            if result:
                writer.writerow(result)
                print("✅ kept")
            else:
                print("❌ discarded")
            time.sleep(RATE_LIMIT_DELAY)

    print(f"✅ Complete! Output written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
