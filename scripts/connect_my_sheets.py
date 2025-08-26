#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_sheets_connector import GoogleSheetsConnector

# Your configuration
SHEET_ID = "https://docs.google.com/spreadsheets/d/142CA2mTNiEBkXFNJ5Q-J55ldxi6XLhY75s6gHP-vHCw/edit?gid=2084641558#gid=2084641558"
CREDENTIALS_FILE = "credentials.json" if False else None

def main():
    print("🔍 Connecting to your Google Sheets...")
    
    # Create connector
    connector = GoogleSheetsConnector(
        credentials_file=CREDENTIALS_FILE,
        sheet_id=SHEET_ID
    )
    
    # Authenticate
    if not connector.authenticate():
        print("❌ Authentication failed")
        return
    
    # Get data
    print("📥 Retrieving your 1700 insights...")
    data = connector.get_sheet_data()
    
    if not data:
        print("❌ Could not retrieve data")
        return
    
    print(f"✅ Retrieved {len(data)} insights")
    
    # Simple column mapping (you can customize this)
    column_mapping = {
        # Map your Google Sheets columns to our format
        # Add your actual column names here
        "Description": "description",
        "Rationale": "rationale", 
        "Use Case": "use_case",
        "Impact Area": "impact_area",
        "Transferability": "transferability_score",
        "Actionability": "actionability_rating",
        "Type": "type_(form)",
        "Tag": "tag_(application)",
        "Source": "source_(interview_#/_name)",
        "Link": "link",
        "Notes": "notes"
    }
    
    # Map and save
    print("🔄 Processing data...")
    mapped_data = connector.map_columns(data, column_mapping)
    
    if connector.save_to_csv(mapped_data):
        print("✅ Success! Your Google Sheets data is now integrated.")
        print("📊 Run: python3 wisdom_search.py --stats")
        print("🌐 Run: python3 web_search.py")
    else:
        print("❌ Failed to save data")

if __name__ == "__main__":
    main()
