import csv
import json
import os
import openai
import time
import logging
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default values (can be overridden by command line arguments)
INPUT_FILE = "data/youtube_curated_insights.csv"
OUTPUT_FILE = "data/youtube_wisdom_index.csv"
MODEL = "gpt-4"
RATE_LIMIT_DELAY = 1.5  # seconds between requests

# Validate OpenAI API key
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

    except openai.RateLimitError as e:
        logger.warning(f"Rate limit exceeded: {e}")
        time.sleep(60)  # Wait 1 minute before retrying
        return None
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON response: {e}")
        return None
    except KeyError as e:
        logger.warning(f"Missing key in response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error processing row: {e}")
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Transform content using OpenAI to extract tacit knowledge")
    parser.add_argument("--input", default=INPUT_FILE, help="Input CSV file path")
    parser.add_argument("--output", default=OUTPUT_FILE, help="Output CSV file path")
    parser.add_argument("--skip-rows", type=int, default=0, help="Number of rows to skip")
    
    args = parser.parse_args()
    
    # Update file paths from arguments
    input_file = args.input
    output_file = args.output
    skip_rows = args.skip_rows
    
    try:
        # Check if input file exists
        if not os.path.exists(input_file):
            logger.error(f"Input file not found: {input_file}")
            return
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(input_file, newline='', encoding='utf-8') as infile, \
             open(output_file, "w", newline='', encoding='utf-8') as outfile:

            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=COLUMNS)
            writer.writeheader()  # Write header
            
            # Skip rows if specified
            for i in range(skip_rows):
                next(reader, None)

            for i, row in enumerate(reader, skip_rows + 1):
                logger.info(f"Processing row {i:03d}...")
                result = process_row(row)
                if result:
                    writer.writerow(result)
                    logger.info(f"Row {i}: ✅ kept")
                else:
                    logger.info(f"Row {i}: ❌ discarded")
                time.sleep(RATE_LIMIT_DELAY)

        logger.info(f"✅ Complete! Output written to {output_file}")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")

if __name__ == "__main__":
    main()
