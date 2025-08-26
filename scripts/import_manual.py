#!/usr/bin/env python3
"""
Manual Google Sheets Import
Import your 1700 insights from a manually exported CSV file
"""

import csv
import os
import pandas as pd

def main():
    print("📥 Manual Google Sheets Import")
    print("=" * 40)
    print("This will help you import your 1700 insights from a CSV file.")
    print("\nSteps:")
    print("1. Export your Google Sheet as CSV")
    print("2. Save it as 'my_insights.csv' in this directory")
    print("3. Run this script to import it")
    
    # Check if the file exists
    csv_file = "my_insights.csv"
    if not os.path.exists(csv_file):
        print(f"\n❌ {csv_file} not found!")
        print("\nTo export from Google Sheets:")
        print("1. Open your Google Sheet")
        print("2. File → Download → CSV")
        print("3. Rename to 'my_insights.csv'")
        print("4. Place it in this directory")
        print("5. Run this script again")
        return
    
    print(f"\n✅ Found {csv_file}")
    
    # Read the CSV
    try:
        df = pd.read_csv(csv_file)
        print(f"📊 Loaded {len(df)} rows")
        
        # Show column names
        print(f"\n📋 Columns found:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. {col}")
        
        # Simple column mapping (you can customize this)
        print(f"\n🔄 Mapping columns...")
        
        # Create a mapping based on common column names
        column_mapping = {}
        
        # Try to auto-detect common column names
        for col in df.columns:
            col_lower = col.lower()
            if 'description' in col_lower or 'insight' in col_lower:
                column_mapping[col] = 'description'
            elif 'rationale' in col_lower or 'reason' in col_lower or 'why' in col_lower:
                column_mapping[col] = 'rationale'
            elif 'use' in col_lower and 'case' in col_lower:
                column_mapping[col] = 'use_case'
            elif 'impact' in col_lower:
                column_mapping[col] = 'impact_area'
            elif 'transfer' in col_lower:
                column_mapping[col] = 'transferability_score'
            elif 'action' in col_lower:
                column_mapping[col] = 'actionability_rating'
            elif 'type' in col_lower:
                column_mapping[col] = 'type_(form)'
            elif 'tag' in col_lower:
                column_mapping[col] = 'tag_(application)'
            elif 'source' in col_lower:
                column_mapping[col] = 'source_(interview_#/_name)'
            elif 'link' in col_lower or 'url' in col_lower:
                column_mapping[col] = 'link'
            elif 'note' in col_lower:
                column_mapping[col] = 'notes'
        
        print(f"✅ Auto-mapped {len(column_mapping)} columns:")
        for gsheet_col, our_col in column_mapping.items():
            print(f"   {gsheet_col} → {our_col}")
        
        # Create the mapped data
        mapped_data = []
        for _, row in df.iterrows():
            mapped_row = {}
            
            # Add mapped columns
            for gsheet_col, our_col in column_mapping.items():
                if gsheet_col in row:
                    mapped_row[our_col] = str(row[gsheet_col]) if pd.notna(row[gsheet_col]) else ''
                else:
                    mapped_row[our_col] = ''
            
            # Add missing columns with empty values
            standard_columns = [
                'description', 'rationale', 'use_case', 'impact_area',
                'transferability_score', 'actionability_rating', 'evidence_strength',
                'type_(form)', 'tag_(application)', 'unique?', 'role', 'function',
                'company', 'industry', 'country', 'date', 'source_(interview_#/_name)',
                'link', 'notes'
            ]
            
            for col in standard_columns:
                if col not in mapped_row:
                    mapped_row[col] = ''
            
            # Add source information
            mapped_row['source'] = 'GoogleSheets'
            mapped_row['filepath'] = f'Manual Import: {csv_file}'
            
            mapped_data.append(mapped_row)
        
        # Save to CSV
        output_file = "data/google_sheets_wisdom.csv"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if mapped_data:
                writer = csv.DictWriter(f, fieldnames=mapped_data[0].keys())
                writer.writeheader()
                writer.writerows(mapped_data)
        
        print(f"\n✅ Successfully imported {len(mapped_data)} insights!")
        print(f"📁 Saved to: {output_file}")
        
        # Test the integration
        print(f"\n🧪 Testing integration...")
        try:
            from wisdom_search import WisdomSearch
            searcher = WisdomSearch()
            stats = searcher.get_statistics()
            print(f"📊 Total insights in database: {stats['total_insights']}")
            print(f"📚 Sources: {list(stats['sources'].keys())}")
            
            if 'GoogleSheets' in stats['sources']:
                print(f"✅ Your Google Sheets data is now integrated!")
                print(f"🎯 You can search with: python3 wisdom_search.py 'your search term'")
            else:
                print(f"⚠️  GoogleSheets not found in sources. Check the data format.")
                
        except Exception as e:
            print(f"⚠️  Could not test integration: {e}")
        
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        print("Please check that the CSV file is properly formatted.")

if __name__ == "__main__":
    main()
