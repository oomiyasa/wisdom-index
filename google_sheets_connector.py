#!/usr/bin/env python3
"""
Google Sheets Connector for Business Wisdom Database
Connects to Google Sheets and integrates with the search system
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import csv
import os
from typing import List, Dict, Any
import json

class GoogleSheetsConnector:
    def __init__(self, credentials_file: str = None, sheet_id: str = None):
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        self.client = None
        
    def authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            if self.credentials_file and os.path.exists(self.credentials_file):
                # Use service account credentials
                creds = Credentials.from_service_account_file(
                    self.credentials_file, scopes=self.scope
                )
                self.client = gspread.authorize(creds)
                print("✅ Authenticated with service account")
            else:
                # Use OAuth2 (requires manual setup)
                print("⚠️  No service account file found. Using OAuth2...")
                self.client = gspread.oauth()
                print("✅ Authenticated with OAuth2")
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
        return True
    
    def get_sheet_data(self, sheet_name: str = None) -> List[Dict[str, Any]]:
        """Get data from Google Sheet"""
        if not self.client:
            print("❌ Not authenticated. Call authenticate() first.")
            return []
        
        try:
            if self.sheet_id:
                # Open by sheet ID
                sheet = self.client.open_by_key(self.sheet_id)
            else:
                # Open by title (requires sharing with service account email)
                sheet = self.client.open("Business Wisdom Database")
            
            if sheet_name:
                worksheet = sheet.worksheet(sheet_name)
            else:
                worksheet = sheet.get_worksheet(0)  # First worksheet
            
            # Get all data
            data = worksheet.get_all_records()
            print(f"✅ Retrieved {len(data)} rows from Google Sheets")
            return data
            
        except Exception as e:
            print(f"❌ Error getting sheet data: {e}")
            return []
    
    def save_to_csv(self, data: List[Dict[str, Any]], filename: str = "data/google_sheets_wisdom.csv"):
        """Save Google Sheets data to CSV"""
        if not data:
            print("❌ No data to save")
            return False
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Convert to DataFrame and save
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            print(f"✅ Saved {len(data)} insights to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving to CSV: {e}")
            return False
    
    def map_columns(self, data: List[Dict[str, Any]], column_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Map Google Sheets columns to our standard format"""
        mapped_data = []
        
        for row in data:
            mapped_row = {}
            for gsheet_col, our_col in column_mapping.items():
                if gsheet_col in row:
                    mapped_row[our_col] = row[gsheet_col]
                else:
                    mapped_row[our_col] = ''
            
            # Add source information
            mapped_row['source'] = 'GoogleSheets'
            mapped_row['filepath'] = f'Google Sheets: {self.sheet_id}'
            
            mapped_data.append(mapped_row)
        
        return mapped_data

def setup_google_sheets():
    """Interactive setup for Google Sheets integration"""
    print("🔧 Google Sheets Integration Setup")
    print("=" * 50)
    
    # Get sheet ID
    sheet_id = input("Enter your Google Sheet ID (or press Enter to skip): ").strip()
    if not sheet_id:
        print("⚠️  No sheet ID provided. You'll need to share the sheet with the service account.")
    
    # Check for credentials
    credentials_file = "credentials.json"
    if os.path.exists(credentials_file):
        print(f"✅ Found credentials file: {credentials_file}")
    else:
        print("⚠️  No credentials.json found. You'll need to set up OAuth2.")
        print("   Instructions:")
        print("   1. Go to Google Cloud Console")
        print("   2. Create a project and enable Google Sheets API")
        print("   3. Create credentials (Service Account or OAuth2)")
        print("   4. Download credentials.json to this directory")
    
    return sheet_id, credentials_file

def create_column_mapping():
    """Create a mapping between Google Sheets columns and our format"""
    print("\n📋 Column Mapping Setup")
    print("=" * 30)
    print("Map your Google Sheets columns to our standard format:")
    
    # Standard columns we expect
    standard_columns = [
        'description', 'rationale', 'use_case', 'impact_area',
        'transferability_score', 'actionability_rating', 'evidence_strength',
        'type_(form)', 'tag_(application)', 'unique?', 'role', 'function',
        'company', 'industry', 'country', 'date', 'source_(interview_#/_name)',
        'link', 'notes'
    ]
    
    mapping = {}
    for col in standard_columns:
        gsheet_col = input(f"Enter Google Sheets column name for '{col}' (or press Enter to skip): ").strip()
        if gsheet_col:
            mapping[gsheet_col] = col
    
    return mapping

def main():
    """Main function to set up and test Google Sheets integration"""
    print("🔍 Google Sheets Wisdom Database Integration")
    print("=" * 60)
    
    # Setup
    sheet_id, credentials_file = setup_google_sheets()
    
    # Create connector
    connector = GoogleSheetsConnector(
        credentials_file=credentials_file if os.path.exists(credentials_file) else None,
        sheet_id=sheet_id if sheet_id else None
    )
    
    # Authenticate
    if not connector.authenticate():
        print("❌ Authentication failed. Please check your credentials.")
        return
    
    # Get column mapping
    column_mapping = create_column_mapping()
    
    # Test connection
    print("\n🔍 Testing connection...")
    data = connector.get_sheet_data()
    
    if not data:
        print("❌ Could not retrieve data. Please check:")
        print("   - Sheet ID is correct")
        print("   - Sheet is shared with your account")
        print("   - API is enabled")
        return
    
    print(f"✅ Successfully retrieved {len(data)} rows")
    
    # Show sample data
    if data:
        print("\n📋 Sample data (first row):")
        for key, value in data[0].items():
            print(f"   {key}: {str(value)[:50]}...")
    
    # Map columns
    print("\n🔄 Mapping columns...")
    mapped_data = connector.map_columns(data, column_mapping)
    
    # Save to CSV
    print("\n💾 Saving to CSV...")
    if connector.save_to_csv(mapped_data):
        print("✅ Integration complete! Your Google Sheets data is now available in the search system.")
        print("\n📊 Next steps:")
        print("   1. Run: python3 wisdom_search.py --stats")
        print("   2. Start web interface: python3 web_search.py")
        print("   3. Your 1700 insights will be included in searches!")
    else:
        print("❌ Failed to save data")

if __name__ == "__main__":
    main()
