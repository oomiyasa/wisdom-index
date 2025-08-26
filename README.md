# Wisdom Index - Tacit Knowledge Harvesting System

A comprehensive system for harvesting tacit knowledge from various online communities and transforming it into structured wisdom insights.

## 🚀 Features

- **Multi-Platform Harvesting**: Reddit, Web Forums, StackExchange, GitHub, Medium
- **177 Comprehensive Keywords**: Exhaustive tacit knowledge detection across 10 categories
- **Duplicate Search Prevention**: Intelligent detection to avoid re-harvesting
- **Quality Filtering**: Automated filtering of high-quality content
- **OpenAI Transformation**: Structured wisdom insights with metadata
- **Modular Architecture**: Extensible harvester system

## 📁 Project Structure

```
Wisdex/
├── harvesters/                 # Core harvesting modules
│   ├── __init__.py
│   ├── base_harvester.py      # Base harvester class
│   ├── reddit_harvester.py    # Reddit-specific harvester
│   └── web_harvester.py       # Web forum harvester
├── data/                      # Data storage
│   ├── raw/                   # Raw harvested data
│   ├── filtered/              # Quality-filtered data
│   ├── transformed/           # OpenAI-transformed insights
│   └── exports/               # Final wisdom exports
├── scripts/                   # Utility scripts
│   ├── debug/                 # Debug scripts
│   ├── test/                  # Test scripts
│   └── legacy/                # Legacy harvesters
├── harvester_main.py          # Main orchestration script
├── filter_quality.py          # Quality filtering
├── transform_wisdom_index_openai.py  # OpenAI transformation
├── wi_config_unified.yaml     # Configuration file
└── requirements.txt           # Dependencies
```

## 🔑 Comprehensive Keyword System

The system uses **177 tacit knowledge keywords** across 10 categories:

1. **How-To / Process-Oriented** (15 keywords)
   - `how_we_solved`, `my_process_for`, `troubleshooting_steps`

2. **Tips, Tricks, and Rules of Thumb** (19 keywords)
   - `pro_tip`, `rule_of_thumb`, `life_hack`, `quick_fix`

3. **Lessons & Experience-Based Insights** (17 keywords)
   - `lesson_learned`, `wish_i_knew`, `what_went_wrong`

4. **Playbooks, Practices, and Frameworks** (17 keywords)
   - `playbook`, `tribal_knowledge`, `best_practice`

5. **Failures, Escalations & Edge Cases** (16 keywords)
   - `postmortem`, `root_cause`, `edge_case`

6. **Workarounds & Hacks** (13 keywords)
   - `workaround`, `hack`, `dirty_fix`, `kludge`

7. **Coordination, Collaboration & Team Logic** (15 keywords)
   - `handoff`, `escalation`, `unspoken_rule`

8. **Warnings & Cautions** (11 keywords)
   - `watch_out_for`, `gotcha`, `red_flag`

9. **Tacit Resource Mentions** (11 keywords)
   - `buried_in_the_wiki`, `slack_thread`, `internal_doc`

10. **Documentation Gaps / Transfer Triggers** (11 keywords)
    - `not_in_the_docs`, `undocumented`, `trial_and_error`

## 🛠️ Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**:
   - Copy `.env.example` to `.env`
   - Add your API keys (OpenAI, Reddit, etc.)

3. **Run Harvest**:
   ```bash
   python3 harvester_main.py --config wi_config_unified.yaml
   ```

4. **Filter Quality**:
   ```bash
   python3 filter_quality.py --input data/raw/web_data.csv --output data/filtered/web_data_filtered.csv
   ```

5. **Transform to Wisdom**:
   ```bash
   python3 transform_wisdom_index_openai.py --input data/filtered/web_data_filtered.csv --output data/transformed/wisdom_insights.csv
   ```

## 📊 Supported Platforms

### Reddit
- Multi-mode harvesting (evergreen, top posts, new, controversial)
- Enhanced comment processing
- Subreddit-specific configurations

### Web Forums
- Selenium-based JavaScript support
- CSS selector configurations
- Kaggle, StackExchange, and custom forums

### StackExchange
- API and HTML harvesting modes
- Site-specific configurations
- Answer-focused harvesting

### GitHub
- Issues, discussions, and pull requests
- Label-based filtering
- Repository-specific harvesting

## 🔧 Configuration

The `wi_config_unified.yaml` file controls:
- **Source toggles**: Enable/disable platforms
- **Keywords**: 177 tacit knowledge signals
- **Industry modifiers**: Domain-specific terms
- **Harvest parameters**: Limits, filters, time windows
- **Platform-specific settings**: Subreddits, sites, selectors

## 📈 Recent Improvements

- **Comprehensive Keywords**: Expanded from ~20 to 177 keywords
- **Duplicate Detection**: Prevents re-harvesting same content
- **Multi-Mode Reddit**: Enhanced harvesting strategies
- **Selenium Support**: JavaScript-heavy site support
- **Modular Structure**: Clean, organized codebase

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Related Documentation

- `WORKFLOW_README.md` - Detailed workflow documentation
- `COMMUNITY_SWITCHING_GUIDE.md` - Community-specific configurations
- `GOOGLE_SHEETS_SETUP.md` - Google Sheets integration

