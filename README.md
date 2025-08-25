# 🔍 Business Wisdom Database

A comprehensive database of actionable business insights extracted from multiple content sources including podcasts, GitHub discussions, Reddit, Stack Exchange, and more.

## 📊 Database Overview

- **Total Insights**: 425+ business insights
- **Data Sources**: 5 different platforms
- **Average Transferability Score**: 3.89/5
- **Average Actionability Rating**: 4.24/5

### Data Sources

1. **Combined Wisdom Index** (58 insights) - Podcasts + YouTube
2. **GitHub** (151 insights) - Technical discussions and best practices
3. **Reddit** (150 insights) - Community discussions and advice
4. **Stack Exchange** (62 insights) - Q&A platform insights
5. **Medium** (4 insights) - Article-based insights

## 🚀 Quick Start

### Data Processing Workflow

```bash
# Run the complete workflow
python3 workflow.py --config wi_config_unified.yaml

# Or run individual steps
python3 workflow.py --step harvest --config wi_config_unified.yaml
python3 workflow.py --step filter --config wi_config_unified.yaml
python3 workflow.py --step transform --config wi_config_unified.yaml
```

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Wisdex
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 📁 Project Structure

```
Wisdex/
├── data/                          # Data files
│   ├── combined_wisdom_index.csv  # Combined insights (podcasts + YouTube)
│   ├── wisdom/
│   │   └── github_wisdom_index.csv # GitHub insights
│   ├── reddit_full_harvest.csv    # Reddit insights
│   ├── stackexchange_final.csv    # Stack Exchange insights
│   └── medium_final.csv           # Medium insights
├── harvesters/                    # Modular harvester package
│   ├── base_harvester.py         # Base harvester class
│   ├── reddit_harvester.py       # Reddit harvester
│   └── ...                       # Other platform harvesters
├── harvester_main.py             # Main harvester (modular)
├── workflow.py                   # Complete workflow runner
├── transform_wisdom_index_openai.py # OpenAI processing script
└── README.md                     # This file
```

## 📈 Data Quality Metrics

### Transferability Score (1-5)
- **5**: Highly transferable across industries
- **4**: Transferable with minor modifications
- **3**: Moderately transferable
- **2**: Limited transferability
- **1**: Very specific to context

### Actionability Rating (1-5)
- **5**: Immediately actionable
- **4**: Actionable with minimal effort
- **3**: Requires some planning
- **2**: Requires significant effort
- **1**: Conceptual/strategic only

### Evidence Strength
- **Observed**: Direct observation or experience
- **Peer-validated**: Validated by multiple sources
- **Anecdotal**: Single source or story
- **Experimental**: Tested in controlled environment

## 🎯 Content Categories

### Impact Areas
- **Efficiency**: Process optimization, time-saving techniques
- **Risk**: Risk management, error prevention
- **Revenue**: Revenue generation, monetization strategies
- **Retention**: Customer/user retention strategies
- **Control**: Process control, quality management

### Insight Types
- **workaround**: Practical solutions to problems
- **rule-of-thumb**: General guidelines and principles
- **pattern**: Recurring solutions and approaches
- **best practice**: Industry-standard approaches
- **warning**: Common pitfalls to avoid
- **pro tip**: Advanced techniques and insights

### Application Tags
- **Data Management**: Database, analytics, data processing
- **Code Management**: Software development, coding practices
- **Resource Management**: Resource allocation, optimization
- **Project Management**: Planning, execution, delivery
- **Communication**: Team communication, stakeholder management

## 🔄 Data Processing Pipeline

### 1. Content Harvesting
- **Podcasts**: Manual curation of high-quality business content
- **YouTube**: Manual selection of business wisdom videos
- **GitHub**: Automated harvesting from issue discussions
- **Reddit**: Community-driven content collection
- **Stack Exchange**: Q&A platform insights extraction

### 2. OpenAI Processing
- **Quality Filtering**: Strict criteria for tacit knowledge
- **Categorization**: Automatic tagging and classification
- **Scoring**: Transferability and actionability assessment
- **Validation**: Evidence strength evaluation

### 3. Manual Curation
- **Review**: Human validation of AI-processed insights
- **Enhancement**: Additional context and metadata
- **Organization**: Structured categorization and tagging

## 🛠️ Development

### Adding New Data Sources

1. **Create harvester script**
   ```python
   # Example: harvest_new_source.py
   def harvest_content():
       # Extract insights from new source
       pass
   ```

2. **Process with OpenAI**
   ```bash
   python3 transform_wisdom_index_openai.py
   ```

### Customizing the Pipeline

- **Modify harvesting logic** in platform-specific harvesters
- **Adjust filtering criteria** in quality filters
- **Update transformation prompts** in OpenAI processing

## 🤝 Contributing

### Adding Insights
1. **Identify high-quality content** from business sources
2. **Extract actionable insights** with clear descriptions
3. **Categorize and tag** appropriately
4. **Validate quality** against existing standards

### Improving the Pipeline
1. **Enhance harvesting algorithms** for better data collection
2. **Add new filter options** for more precise quality control
3. **Optimize performance** for larger datasets
4. **Improve transformation prompts** for better insight extraction

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OpenAI** for providing the processing capabilities
- **Content creators** across all platforms for sharing their wisdom
- **Open source community** for the tools and frameworks used

## 📞 Support

For questions, suggestions, or contributions:
- **Issues**: Create an issue in the repository
- **Discussions**: Use the discussions tab for general questions
- **Email**: Contact the maintainers directly

---

**Last Updated**: January 2025
**Version**: 1.0.0
**Status**: Active Development

