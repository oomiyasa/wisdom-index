# Wisdom Index Data Organization

This document describes the data organization system for the Wisdom Index harvester.

## 📁 Data Directory Structure

All CSV files are automatically organized into the `data/` folder with the following structure:

```
data/
├── raw/           # Raw harvested data from platforms
├── filtered/      # Quality-filtered data
├── wisdom/        # Final wisdom insights (transformed by OpenAI)
└── archive/       # Test and debug files
```

## 🔄 Automatic File Organization

### Harvester (`harvesternew.py`)
- **Input**: YAML configuration file
- **Output**: Raw CSV files automatically saved to `data/raw/`
- **Example**: `python3 harvesternew.py --config wi_config_unified.yaml --out reddit_data.csv`

### Quality Filter (`filter_quality.py`)
- **Input**: Raw CSV files from `data/raw/`
- **Output**: Filtered CSV files automatically saved to `data/filtered/`
- **Example**: `python3 filter_quality.py --input reddit_data.csv --output reddit_filtered.csv`

### Transformer (`transform_wisdom_index_openai.py`)
- **Input**: Filtered CSV files from `data/filtered/`
- **Output**: Wisdom insights automatically saved to `data/wisdom/`
- **Example**: `python3 transform_wisdom_index_openai.py`

## 🧹 Data Management Tools

### Cleanup Script (`cleanup_data.py`)

#### Show Data Summary
```bash
python3 cleanup_data.py --summary
```

#### Organize Files into Subdirectories
```bash
python3 cleanup_data.py --organize
```

#### Clean Up Old Files
```bash
# Remove files older than 7 days
python3 cleanup_data.py --cleanup 7
```

## 📊 File Naming Conventions

### Raw Data Files
- `{platform}_data.csv` - Raw harvested data
- `{platform}_debug.csv` - Debug output
- `{platform}_test.csv` - Test runs

### Filtered Data Files
- `{platform}_quality_filtered.csv` - Quality-filtered data
- `{platform}_filtered.csv` - General filtered data

### Wisdom Files
- `{platform}_wisdom_index.csv` - Final wisdom insights

## 🔧 Configuration

### Platform Sources
Configure which platforms to harvest in `wi_config_unified.yaml`:

```yaml
sources:
  reddit: true
  github: false
  stackexchange: false
  medium: false
```

### Output Paths
All scripts automatically use the `data/` folder. You can specify custom paths:

```bash
# These are equivalent:
python3 harvesternew.py --out my_data.csv
python3 harvesternew.py --out data/my_data.csv
```

## 📈 Data Flow

```
1. Harvest (raw/) → 2. Filter (filtered/) → 3. Transform (wisdom/)
```

### Example Workflow
```bash
# 1. Harvest from Reddit
python3 harvesternew.py --config wi_config_unified.yaml --out reddit_raw.csv

# 2. Filter for quality
python3 filter_quality.py --input reddit_raw.csv --output reddit_filtered.csv

# 3. Transform to wisdom insights
python3 transform_wisdom_index_openai.py

# 4. Organize files
python3 cleanup_data.py --organize
```

## 📋 Best Practices

1. **Regular Cleanup**: Run `cleanup_data.py --organize` periodically
2. **Archive Old Files**: Use `cleanup_data.py --cleanup 30` to remove old test files
3. **Monitor Size**: Use `cleanup_data.py --summary` to track data growth
4. **Backup Wisdom**: The `data/wisdom/` folder contains your valuable insights

## 🚀 Quick Start

```bash
# Harvest from all enabled platforms
python3 harvesternew.py --config wi_config_unified.yaml

# Filter and transform
python3 filter_quality.py --input data/raw/github_data.csv --output data/filtered/github_filtered.csv
python3 transform_wisdom_index_openai.py

# Organize and view results
python3 cleanup_data.py --organize
ls data/wisdom/
```
