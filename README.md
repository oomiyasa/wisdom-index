# Wisdom Index - Tacit Knowledge Harvester

A comprehensive system for harvesting tacit knowledge from various online platforms and transforming it into structured insights.

## 🚀 Features

- **Multi-Platform Harvesting**: Reddit, GitHub, StackExchange, Medium, YouTube, and more
- **Intelligent Filtering**: Pre-filters content for high-quality tacit knowledge
- **OpenAI Integration**: Transforms raw content into structured insights
- **Scalable Architecture**: Configurable search parameters and rate limiting
- **Data Organization**: Automatic file organization and search history tracking

## 📋 Prerequisites

- Python 3.8+
- Required API keys (see Setup section)
- Internet connection for harvesting

## 🔧 Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Wisdex
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root with your API credentials:

```bash
# Required for OpenAI transformation
OPENAI_API_KEY=your_openai_api_key_here

# Required for Reddit harvesting
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=your_reddit_user_agent_here

# Required for GitHub harvesting
GITHUB_TOKEN=your_github_token_here

# Required for YouTube harvesting
YOUTUBE_API_KEY=your_youtube_api_key_here
```

### 4. Get API Keys

#### OpenAI API Key
- Visit: https://platform.openai.com/api-keys
- Create a new API key
- Add to `.env` file

#### Reddit API Credentials
- Visit: https://www.reddit.com/prefs/apps
- Create a new app (script type)
- Note the client ID and secret
- Add to `.env` file

#### GitHub Token
- Visit: https://github.com/settings/tokens
- Generate new token (classic)
- Select repo scope
- Add to `.env` file

#### YouTube Data API Key
- Visit: https://console.cloud.google.com/apis/credentials
- Create new project or select existing
- Enable YouTube Data API v3
- Create API credentials
- Add to `.env` file

## 🎯 Usage

### Basic Harvesting
```bash
# Harvest from all enabled platforms
python3 harvesternew.py --config wi_config_unified.yaml --out insights.csv

# Harvest from specific platform
python3 harvesternew.py --config wi_config_unified.yaml --out reddit_insights.csv
```

### Configuration
Edit `wi_config_unified.yaml` to:
- Enable/disable platforms
- Configure search terms
- Set rate limits
- Adjust filtering parameters

### Data Organization
```bash
# View search history
python3 view_search_history.py

# Organize data files
python3 cleanup_data.py

# Filter quality content
python3 filter_quality.py
```

## 📁 Project Structure

```
Wisdex/
├── harvesternew.py          # Main harvester script
├── transform_wisdom_index_openai.py  # OpenAI transformation
├── filter_quality.py        # Content filtering
├── view_search_history.py   # Search history management
├── cleanup_data.py          # Data organization
├── wi_config_unified.yaml   # Configuration file
├── .env                     # Environment variables (not in git)
├── .gitignore              # Git ignore rules
├── data/                   # Output directory
│   ├── raw/               # Raw harvested data
│   ├── filtered/          # Pre-filtered data
│   ├── wisdom/            # Final insights
│   └── archive/           # Archived data
└── README.md              # This file
```

## 🔒 Security

### Credential Protection
- **Never commit `.env` files** - they're in `.gitignore`
- **Use environment variables** for all API keys
- **Rotate keys regularly** for security
- **Limit API permissions** to minimum required

### Safe Practices
- Keep API keys private
- Monitor API usage and quotas
- Use rate limiting to avoid abuse
- Respect platform terms of service

## 📊 Data Flow

1. **Harvesting**: Raw content from platforms
2. **Filtering**: Quality filtering for tacit knowledge
3. **Transformation**: OpenAI processing into structured format
4. **Organization**: Automatic file organization
5. **Analysis**: Insights ready for analysis

## 🎛️ Configuration

### Platform Settings
Each platform has configurable parameters:
- Search terms/keywords
- Rate limits
- Result limits
- Filtering criteria

### Output Format
Insights are structured with fields:
- description, rationale, use_case
- impact_area, transferability_score
- actionability_rating, evidence_strength
- type, tag, role, function, company, industry
- date, source, link, notes

## 🚨 Troubleshooting

### Common Issues
- **API Quota Exceeded**: Wait for reset or reduce search scope
- **Rate Limiting**: Increase throttle delays in config
- **No Results**: Check search terms and filtering criteria
- **Import Errors**: Ensure all dependencies are installed

### Debug Mode
Add `--debug` flag for verbose output:
```bash
python3 harvesternew.py --config wi_config_unified.yaml --debug
```

## 📈 Scaling

### For Production Use
- Implement proper logging
- Add monitoring and alerts
- Use database storage
- Implement caching
- Add error recovery

### Performance Optimization
- Parallel processing
- Caching strategies
- Database indexing
- CDN for static assets

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- Platform APIs (Reddit, GitHub, YouTube, etc.)
- Open source community

---

**⚠️ Important**: Never commit API keys or credentials to version control. Always use environment variables and keep `.env` files secure.
