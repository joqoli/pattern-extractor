# server/data

Automated dataset acquisition toolkit for Pattern Extractor.

## Files

- `dataset_manifest.json`: Central registry of all available datasets
- `fetcher.py`: Main download orchestrator with multiple strategies
- `validate_datasets.py`: Integrity checking and validation
- `thingiverse_fetcher.py`: Optional Thingiverse API integration

## Quick Start

```bash
# Download all enabled datasets
make download-datasets

# Download specific category
python3 server/data/fetcher.py --category embroidery

# Download single dataset
python3 server/data/fetcher.py --name dtd

# Dry run (show what would download)
python3 server/data/fetcher.py --dry-run

# Validate downloaded datasets
python3 server/data/validate_datasets.py ./datasets
```

## Dependencies

Core:
- `aiohttp` (async downloads)
- `requests` (HTTP)

Optional:
- `beautifulsoup4` (catalog scraping)
- `feedparser` (RSS feeds)
- `kaggle` (Kaggle datasets)
- `git` (git cloning)

## Download Methods

- **direct-download**: HTTP download of archives
- **git-clone**: Clone git repositories
- **kaggle-api**: Use Kaggle CLI
- **catalog-scrape**: Scrape catalog pages for links
- **rss-feed**: Parse RSS feeds
- **api-paginate**: Paginate through APIs
- **manual-form**: Require manual download due to form/agreement

## Dataset Categories

- **embroidery**: DST, JEF, PES, SVG design files
- **texture**: Fabric and material textures
- **fashion**: Garment and clothing datasets
- **historical**: Public domain historical resources
- **community**: Community-contributed designs
