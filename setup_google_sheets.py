#!/usr/bin/env python3
"""
Simple Google Sheets Setup for Business Wisdom Database
Quick setup to connect your 1700 insights from Google Sheets
"""

import os
import sys

def main():
    print("🔗 Google Sheets Integration Setup")
    print("=" * 50)
    print("This will help you connect your 1700 insights from Google Sheets")
    print("to the Business Wisdom Search system.\n")
    
    # Check if required packages are installed
    try:
        import gspread
        import pandas as pd
        print("✅ Required packages are installed")
    except ImportError:
        print("❌ Missing required packages. Installing...")
        os.system("pip install gspread pandas google-auth")
        print("✅ Packages installed")
    
    # Get Google Sheet ID
    print("\n📋 Step 1: Get your Google Sheet ID")
    print("-" * 40)
    print("1. Open your Google Sheet with the 1700 insights")
    print("2. Copy the URL from your browser")
    print("3. The Sheet ID is the long string between /d/ and /edit")
    print("   Example: https://docs.google.com/spreadsheets/d/1ABC123.../edit")
    print("   Sheet ID: 1ABC123...")
    
    sheet_id = input("\nEnter your Google Sheet ID: ").strip()
    
    if not sheet_id:
        print("❌ No Sheet ID provided. Please run this script again.")
        return
    
    # Check for credentials
    print("\n🔐 Step 2: Authentication")
    print("-" * 40)
    
    if os.path.exists("credentials.json"):
        print("✅ Found credentials.json file")
        use_credentials = True
    else:
        print("⚠️  No credentials.json found")
        print("\nYou have two options:")
        print("1. Use OAuth2 (recommended for personal use)")
        print("2. Set up service account credentials")
        
        choice = input("\nChoose option (1 or 2): ").strip()
        
        if choice == "2":
            print("\nTo set up service account credentials:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a new project or select existing")
            print("3. Enable Google Sheets API")
            print("4. Create Service Account credentials")
            print("5. Download JSON file as 'credentials.json'")
            print("6. Place it in this directory")
            print("7. Share your Google Sheet with the service account email")
            
            input("\nPress Enter when you have credentials.json ready...")
            use_credentials = True
        else:
            use_credentials = False
    
    # Create the connector script
    print("\n🔧 Step 3: Creating connector script")
    print("-" * 40)
    
    connector_script = f"""#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_sheets_connector import GoogleSheetsConnector

# Your configuration
SHEET_ID = "{sheet_id}"
CREDENTIALS_FILE = "credentials.json" if {str(use_credentials).lower()} else None

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
    
    print(f"✅ Retrieved {{len(data)}} insights")
    
    # Simple column mapping (you can customize this)
    column_mapping = {{
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
    }}
    
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
"""
    
    with open("connect_my_sheets.py", "w") as f:
        f.write(connector_script)
    
    print("✅ Created connect_my_sheets.py")
    
    # Instructions
    print("\n📋 Next Steps:")
    print("-" * 40)
    print("1. Edit connect_my_sheets.py to map your column names")
    print("2. Run: python3 connect_my_sheets.py")
    print("3. Your 1700 insights will be added to the search system!")
    print("4. Test with: python3 wisdom_search.py --stats")
    
    print("\n🎯 Expected Result:")
    print(f"- Your 1700 insights will be available as 'GoogleSheets' source")
    print("- Total database will have ~2125 insights (425 + 1700)")
    print("- All search features will work with your data")

if __name__ == "__main__":
    main()
