# 🔗 Google Sheets Integration Guide

## 🎯 Quick Start: Connect Your 1700 Insights

### Step 1: Get Your Google Sheet ID

1. **Open your Google Sheet** with the 1700 insights
2. **Copy the URL** from your browser
3. **Extract the Sheet ID** - it's the long string between `/d/` and `/edit`

Example:
```
https://docs.google.com/spreadsheets/d/1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX234YZA567BCD/edit
                                    ↑
                              Sheet ID: 1ABC123DEF456GHI789JKL012MNO345PQR678STU901VWX234YZA567BCD
```

### Step 2: Run the Setup Script

```bash
cd /Users/davidwarren/Desktop/Wisdex
source venv/bin/activate
python3 setup_google_sheets.py
```

This will:
- ✅ Install required packages (gspread, pandas, google-auth)
- 🔧 Create a custom connector script for your sheet
- 📋 Guide you through authentication setup

### Step 3: Choose Authentication Method

#### Option A: OAuth2 (Recommended for Personal Use)
- ✅ No setup required
- ✅ Uses your Google account
- ✅ Works immediately

#### Option B: Service Account (For Production)
- 🔧 Requires Google Cloud Console setup
- 🔧 More secure for automated systems
- 📋 Follow the setup instructions in the script

### Step 4: Map Your Columns

The script will ask you to map your Google Sheets columns to our standard format:

| Your Column Name | Our Format |
|------------------|------------|
| Description | description |
| Rationale | rationale |
| Use Case | use_case |
| Impact Area | impact_area |
| Transferability | transferability_score |
| Actionability | actionability_rating |
| Type | type_(form) |
| Tag | tag_(application) |
| Source | source_(interview_#/_name) |
| Link | link |
| Notes | notes |

### Step 5: Connect and Test

```bash
# Run the generated connector
python3 connect_my_sheets.py

# Test the integration
python3 wisdom_search.py --stats

# Start the web interface
python3 web_search.py
```

## 🎉 Expected Results

After successful integration:

- **Total Insights**: ~2125 (425 existing + 1700 from Google Sheets)
- **New Source**: "GoogleSheets" will appear in search filters
- **Full Search**: All 1700 insights searchable via web and command line
- **Statistics**: Updated dashboard showing your data

## 🔍 Example Searches with Your Data

```bash
# Search your Google Sheets insights specifically
python3 wisdom_search.py "your search term" --source GoogleSheets

# Search across all sources
python3 wisdom_search.py "data management"

# Web interface will include your data automatically
# Visit: http://localhost:5000
```

## 🛠️ Troubleshooting

### "Authentication failed"
- Check that you're using the correct Google account
- Ensure Google Sheets API is enabled
- Try OAuth2 method if service account fails

### "Could not retrieve data"
- Verify the Sheet ID is correct
- Check that the sheet is shared with your account
- Ensure the sheet has data in the expected format

### "Column mapping issues"
- Edit `connect_my_sheets.py` to fix column names
- Check that your Google Sheets has headers in the first row
- Ensure required columns exist (description, rationale, etc.)

## 📊 Data Quality Tips

For best results with your 1700 insights:

1. **Ensure Required Fields**: At minimum, have `description` and `rationale` columns
2. **Use Consistent Formatting**: Keep data types consistent across rows
3. **Add Metadata**: Include `type`, `tag`, `impact_area` for better filtering
4. **Quality Scores**: Add `transferability_score` and `actionability_rating` if possible

## 🚀 Advanced Features

Once connected, you can:

- **Real-time Updates**: Re-run the connector to sync new data
- **Custom Filtering**: Filter by your specific tags and categories
- **Export Results**: Save search results to CSV
- **API Access**: Use the web API for programmatic access

## 📞 Need Help?

If you encounter issues:

1. Check the error messages in the terminal
2. Verify your Google Sheet structure matches the expected format
3. Ensure all required packages are installed
4. Try the OAuth2 authentication method

---

**🎯 Goal**: Transform your 1700 Google Sheets insights into a searchable, filterable business wisdom database!
