# 🔄 Wisdom Index Workflow

This document explains the improved Wisdom Index workflow with modular architecture and better error handling.

## 📋 Workflow Overview

The Wisdom Index follows a three-step process:

1. **Harvest** → Raw data collection from platforms
2. **Filter** → Quality filtering and validation
3. **Transform** → OpenAI-powered insight extraction

## 🏗️ Modular Architecture

### New Structure

```
Wisdex/
├── harvesters/                 # Modular harvester package
│   ├── __init__.py            # Package initialization
│   ├── base_harvester.py      # Base class with common functionality
│   ├── reddit_harvester.py    # Reddit-specific harvester
│   ├── github_harvester.py    # GitHub-specific harvester
│   ├── stackexchange_harvester.py
│   ├── medium_harvester.py
│   ├── youtube_harvester.py
│   └── podcast_harvester.py
├── harvester_main.py          # New main harvester (modular)
├── workflow.py               # Complete workflow runner
└── transform_wisdom_index_openai.py  # Improved with better error handling
```

### Key Improvements

- **Modular Design**: Each platform has its own harvester class
- **Better Error Handling**: Specific exception types and logging
- **Configuration Validation**: Proper config validation and error messages
- **Rate Limiting**: Built-in rate limiting and retry logic
- **Logging**: Comprehensive logging throughout the process

## 🚀 Usage

### Complete Workflow

Run the entire process:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run complete workflow
python3 workflow.py --config wi_config_unified.yaml
```

### Individual Steps

Run specific steps:

```bash
# Step 1: Harvest only
python3 workflow.py --step harvest --config wi_config_unified.yaml

# Step 2: Filter only
python3 workflow.py --step filter --config wi_config_unified.yaml

# Step 3: Transform only
python3 workflow.py --step transform --config wi_config_unified.yaml
```

### Manual Execution

Run steps manually:

```bash
# 1. Harvest raw data
python3 harvester_main.py --config wi_config_unified.yaml

# 2. Filter for quality (if filter_quality.py exists)
python3 filter_quality.py

# 3. Transform with OpenAI
python3 transform_wisdom_index_openai.py
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your API keys:

```bash
# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=WisdomIndexHarvester/1.0

# GitHub API (optional)
GITHUB_TOKEN=your_github_token

# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# StackExchange API (optional)
STACKEXCHANGE_KEY=your_stackexchange_key
```

### Configuration File

The `wi_config_unified.yaml` file controls which platforms to harvest:

```yaml
sources:
  reddit: true
  github: false
  stackexchange: false
  medium: false
  youtube: false
  podcasts: false

reddit:
  subreddits:
    - entrepreneur
    - smallbusiness
    - startup
  harvest:
    limit: 30
    time_filter: "month"
    sort: "top"
```

## 🛠️ Error Handling

### Improved Exception Types

- `HarvesterError`: Base exception for harvester errors
- `ConfigurationError`: Invalid configuration
- `RateLimitError`: API rate limit exceeded
- `RequestException`: Network/API errors

### Logging

All components now use proper logging:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Starting harvest...")
logger.warning("Rate limit approaching...")
logger.error("Harvest failed: {error}")
```

### Retry Logic

Built-in retry logic for network requests:

- Exponential backoff
- Rate limit handling
- Connection error recovery

## 📊 Data Flow

```
Platform APIs → Raw CSV → Filtered CSV → Wisdom Insights
     ↓              ↓           ↓            ↓
  Harvest      data/raw/   data/filtered/  data/wisdom/
```

### File Organization

- `data/raw/`: Raw harvested data
- `data/filtered/`: Quality-filtered data
- `data/wisdom/`: Final wisdom insights
- `data/wisdom_index/`: Combined wisdom database

## 🧪 Testing

Test the modular structure:

```bash
# Test imports
python3 -c "from harvesters import RedditHarvester; print('✅ Modular imports working')"

# Test configuration
python3 harvester_main.py --help
python3 workflow.py --help
```

## 🔒 Security Improvements

- ✅ Removed hardcoded API secrets
- ✅ All credentials now use environment variables
- ✅ Proper error handling without exposing sensitive data
- ✅ Input validation and sanitization

## 📈 Performance Improvements

- Modular design allows parallel development
- Better error handling reduces failed runs
- Rate limiting prevents API bans
- Logging helps with debugging and monitoring

## 🚨 Troubleshooting

### Common Issues

1. **Missing API Keys**: Check your `.env` file
2. **Rate Limits**: The system will automatically retry with backoff
3. **Network Errors**: Check your internet connection
4. **Configuration Errors**: Validate your YAML configuration

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Migration from Old System

The old `harvesternew.py` is still available but deprecated. To migrate:

1. Update your `.env` file with proper API keys
2. Use the new workflow: `python3 workflow.py`
3. The data format remains the same

## 🤝 Contributing

To add a new platform:

1. Create a new harvester in `harvesters/`
2. Inherit from `BaseHarvester`
3. Implement the `harvest()` method
4. Add to `harvesters/__init__.py`
5. Update configuration schema

Example:

```python
class NewPlatformHarvester(BaseHarvester):
    def __init__(self, config):
        super().__init__(config, "NewPlatform")
    
    def harvest(self):
        # Implement harvesting logic
        return results
```
