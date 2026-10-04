#!/usr/bin/env python3
"""Dataset fetcher for Pattern Extractor.

Automatically downloads and prepares embroidery, texture, and fashion datasets.
Supports multiple download strategies: direct HTTP, git clone, API pagination, RSS feeds, Kaggle API.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import aiohttp
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Error: required packages not found. Install with:")
    print("  pip install aiohttp requests")
    exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class DatasetFetcher:
    """Orchestrates dataset downloads with multiple strategies."""

    def __init__(self, manifest_path: Path, output_root: Path, config: dict[str, Any] | None = None):
        self.manifest_path = manifest_path
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        self.datasets = manifest["datasets"]
        self.download_config = manifest.get("download_config", {})
        if config:
            self.download_config.update(config)
        
        self.stats = {"downloaded": 0, "failed": 0, "skipped": 0}
        self._session = None

    @property
    def session(self) -> requests.Session:
        """Get or create a requests session with retry strategy."""
        if self._session is None:
            self._session = requests.Session()
            retry = Retry(
                total=self.download_config.get("retry_attempts", 3),
                backoff_factor=0.5,
                status_forcelist=(500, 502, 503, 504),
            )
            adapter = HTTPAdapter(max_retries=retry)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        return self._session

    def fetch_all(self, category_filter: str | None = None, name_filter: str | None = None) -> None:
        """Download all enabled datasets."""
        datasets_to_fetch = self.datasets
        
        if not category_filter and not name_filter:
            datasets_to_fetch = [d for d in datasets_to_fetch if d.get("enabled", True)]
        else:
            if category_filter:
                datasets_to_fetch = [d for d in datasets_to_fetch if d["category"] == category_filter]
            if name_filter:
                datasets_to_fetch = [d for d in datasets_to_fetch if d["id"] == name_filter]
        
        logger.info(f"Starting download of {len(datasets_to_fetch)} dataset(s)...")
        
        for dataset in datasets_to_fetch:
            try:
                self.fetch_one(dataset)
            except Exception as e:
                logger.error(f"Failed to download {dataset['id']}: {e}")
                self.stats["failed"] += 1
        
        self._print_summary()

    def fetch_one(self, dataset: dict[str, Any]) -> None:
        """Download a single dataset using the appropriate strategy."""
        dataset_id = dataset["id"]
        target_dir = self.output_root / dataset["target_dir"]
        
        if target_dir.exists() and self.download_config.get("skip_existing", True):
            logger.info(f"[{dataset_id}] Already exists, skipping.")
            self.stats["skipped"] += 1
            return
        
        target_dir.mkdir(parents=True, exist_ok=True)
        method = dataset.get("download_method", "manual")
        
        logger.info(f"[{dataset_id}] Using method: {method}")
        
        if method == "direct-download":
            self._download_direct(dataset, target_dir)
        elif method == "git-clone":
            self._download_git_clone(dataset, target_dir)
        elif method == "git-clone-and-form":
            self._download_git_clone_form(dataset, target_dir)
        elif method == "kaggle-api":
            self._download_kaggle(dataset, target_dir)
        elif method == "catalog-scrape":
            self._download_catalog_scrape(dataset, target_dir)
        elif method == "rss-feed":
            self._download_rss_feed(dataset, target_dir)
        elif method == "api-paginate":
            self._download_api_paginate(dataset, target_dir)
        elif method == "manual-form":
            self._write_manual_instructions(dataset, target_dir)
        else:
            self._write_manual_instructions(dataset, target_dir)
        
        self.stats["downloaded"] += 1

    def _download_direct(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download files directly from a URL."""
        url = dataset["url"]
        dataset_id = dataset["id"]
        
        logger.info(f"[{dataset_id}] Downloading from {url}")
        
        try:
            response = self.session.get(
                url,
                timeout=self.download_config.get("timeout_seconds", 300),
                stream=True,
            )
            response.raise_for_status()
            
            # Determine filename from URL or Content-Disposition header
            filename = url.split("/")[-1] or f"{dataset_id}.tar.gz"
            if "Content-Disposition" in response.headers:
                filename = response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
            
            file_path = target_dir / filename
            
            # Stream download with progress
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            pct = (downloaded / total_size) * 100
                            logger.debug(f"[{dataset_id}] Downloaded {pct:.1f}%")
            
            logger.info(f"[{dataset_id}] Downloaded {downloaded / 1024 / 1024:.1f} MB to {file_path}")
            
            # Extract if archive
            if self.download_config.get("extract_archives", True):
                self._extract_archive(file_path, target_dir)
        
        except Exception as e:
            logger.error(f"[{dataset_id}] Direct download failed: {e}")
            raise

    def _download_git_clone(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Clone a git repository."""
        url = dataset["url"]
        dataset_id = dataset["id"]
        
        logger.info(f"[{dataset_id}] Cloning git repo from {url}")
        
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", url, str(target_dir)],
                check=True,
                capture_output=True,
                timeout=self.download_config.get("timeout_seconds", 300),
            )
            logger.info(f"[{dataset_id}] Git clone complete.")
        except subprocess.CalledProcessError as e:
            logger.error(f"[{dataset_id}] Git clone failed: {e.stderr.decode()}")
            raise
        except FileNotFoundError:
            logger.warning(f"[{dataset_id}] Git not found. Falling back to manual instructions.")
            self._write_manual_instructions(dataset, target_dir)

    def _download_git_clone_form(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Clone repo but alert user to form requirement."""
        self._download_git_clone(dataset, target_dir)
        
        # Add note about the form
        note_file = target_dir / "FORM_REQUIRED.txt"
        note_file.write_text(
            f"Dataset: {dataset['name']}\n"
            f"URL: {dataset['url']}\n\n"
            f"This dataset requires you to sign and submit a usage agreement form.\n"
            f"Visit the GitHub repo and follow the instructions to obtain download links.\n"
            f"Place downloaded files in this directory.\n",
            encoding="utf-8",
        )
        logger.info(f"[{dataset['id']}] Form requirement noted in {note_file}")

    def _download_kaggle(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download from Kaggle using the Kaggle CLI."""
        dataset_id = dataset["id"]
        kaggle_ref = dataset["url"].split("/datasets/")[-1]
        
        logger.info(f"[{dataset_id}] Downloading Kaggle dataset: {kaggle_ref}")
        
        try:
            # Check if kaggle CLI is installed
            subprocess.run(["kaggle", "--version"], capture_output=True, check=True)
            
            # Download dataset
            subprocess.run(
                ["kaggle", "datasets", "download", "-d", kaggle_ref, "-p", str(target_dir)],
                check=True,
                capture_output=True,
            )
            
            # Extract
            if self.download_config.get("extract_archives", True):
                for zip_file in target_dir.glob("*.zip"):
                    self._extract_archive(zip_file, target_dir)
            
            logger.info(f"[{dataset_id}] Kaggle download complete.")
        
        except FileNotFoundError:
            logger.warning(f"[{dataset_id}] Kaggle CLI not found. Install with: pip install kaggle")
            self._write_manual_instructions(dataset, target_dir)
        except subprocess.CalledProcessError as e:
            logger.error(f"[{dataset_id}] Kaggle download failed: {e}")
            self._write_manual_instructions(dataset, target_dir)

    def _download_catalog_scrape(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Scrape a catalog page for download links."""
        dataset_id = dataset["id"]
        url = dataset["url"]
        
        logger.info(f"[{dataset_id}] Scraping catalog from {url}")
        logger.warning(f"[{dataset_id}] Catalog scraping requires BeautifulSoup4. Install with: pip install beautifulsoup4")
        
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error(f"[{dataset_id}] BeautifulSoup4 not installed.")
            self._write_manual_instructions(dataset, target_dir)
            return
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Look for download links
            links = soup.find_all("a", {"href": True})
            download_links = [link for link in links if any(ext in link["href"].lower() for ext in self.download_config.get("formats", ["zip", "tar", "gz"]))]
            
            if not download_links:
                logger.warning(f"[{dataset_id}] No download links found in catalog.")
                self._write_manual_instructions(dataset, target_dir)
                return
            
            logger.info(f"[{dataset_id}] Found {len(download_links)} download link(s).")
            
            # Download first few files (rate-limited)
            for i, link in enumerate(download_links[:10]):
                href = link["href"]
                if not href.startswith("http"):
                    href = urljoin(url, href)
                
                try:
                    logger.info(f"[{dataset_id}] Downloading link {i+1}: {href}")
                    self.session.get(href, timeout=60)  # Just test the link
                    logger.info(f"[{dataset_id}] Link {i+1} validated.")
                    await asyncio.sleep(self.download_config.get("rate_limit_delay_ms", 500) / 1000)
                except Exception as e:
                    logger.warning(f"[{dataset_id}] Could not access link {i+1}: {e}")
        
        except Exception as e:
            logger.error(f"[{dataset_id}] Catalog scrape failed: {e}")
            self._write_manual_instructions(dataset, target_dir)

    def _download_rss_feed(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download from an RSS feed."""
        dataset_id = dataset["id"]
        url = dataset["url"]
        
        logger.info(f"[{dataset_id}] Parsing RSS feed from {url}")
        logger.warning(f"[{dataset_id}] RSS feed parsing requires feedparser. Install with: pip install feedparser")
        
        try:
            import feedparser
        except ImportError:
            logger.error(f"[{dataset_id}] feedparser not installed.")
            self._write_manual_instructions(dataset, target_dir)
            return
        
        try:
            # Try to find RSS link on the page
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse RSS if available
            feed = feedparser.parse(response.content)
            
            if feed.entries:
                logger.info(f"[{dataset_id}] Found {len(feed.entries)} feed entries.")
                # Document feed structure for manual processing
                feed_info = target_dir / "FEED_INFO.json"
                feed_data = {
                    "feed_title": feed.feed.get("title", "Unknown"),
                    "feed_url": url,
                    "entry_count": len(feed.entries),
                    "entries": [{"title": e.get("title"), "link": e.get("link")} for e in feed.entries[:10]],
                }
                with open(feed_info, "w", encoding="utf-8") as f:
                    json.dump(feed_data, f, indent=2)
                logger.info(f"[{dataset_id}] Feed entries documented in FEED_INFO.json")
            else:
                logger.warning(f"[{dataset_id}] No feed entries found.")
                self._write_manual_instructions(dataset, target_dir)
        
        except Exception as e:
            logger.error(f"[{dataset_id}] RSS feed parsing failed: {e}")
            self._write_manual_instructions(dataset, target_dir)

    def _download_api_paginate(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download from an API with pagination."""
        dataset_id = dataset["id"]
        base_url = dataset["url"]
        
        logger.info(f"[{dataset_id}] Downloading from API: {base_url}")
        
        # For Thingiverse, we document the API structure
        if "thingiverse" in base_url:
            readme = target_dir / "API_INSTRUCTIONS.md"
            readme.write_text(
                f"# {dataset['name']}\n\n"
                f"This dataset is available via the Thingiverse API.\n\n"
                f"## Manual Download\n\n"
                f"To download embroidery designs from Thingiverse:\n\n"
                f"1. Get an API token from https://www.thingiverse.com/apps\n"
                f"2. Use the Thingiverse API to search: `q=embroidery&type=things`\n"
                f"3. Download individual thing files using the API.\n\n"
                f"## Example using curl:\n\n"
                f"```bash\n"
                f"curl -H 'Authorization: Bearer YOUR_TOKEN' https://api.thingiverse.com/search?q=embroidery\n"
                f"```\n\n"
                f"## Python helper script available in `server/data/thingiverse_fetcher.py`\n",
                encoding="utf-8",
            )
            logger.info(f"[{dataset_id}] API instructions written. See API_INSTRUCTIONS.md")
        else:
            self._write_manual_instructions(dataset, target_dir)

    def _extract_archive(self, archive_path: Path, extract_to: Path) -> None:
        """Extract tar.gz, tar, or zip archives."""
        logger.info(f"Extracting {archive_path.name} to {extract_to}")
        
        try:
            if archive_path.suffix == ".gz" or archive_path.name.endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(extract_to)
            elif archive_path.suffix == ".tar":
                with tarfile.open(archive_path, "r") as tar:
                    tar.extractall(extract_to)
            elif archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(extract_to)
            else:
                logger.warning(f"Unsupported archive format: {archive_path}")
                return
            
            # Remove archive after extraction
            archive_path.unlink()
            logger.info(f"Extraction complete. Archive removed.")
        
        except Exception as e:
            logger.error(f"Failed to extract {archive_path}: {e}")
            raise

    def _write_manual_instructions(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Write instructions for manual download."""
        dataset_id = dataset["id"]
        
        readme = target_dir / "DOWNLOAD_INSTRUCTIONS.md"
        readme.write_text(
            f"# {dataset['name']}\n\n"
            f"**Status:** Manual download required\n\n"
            f"## Information\n\n"
            f"- **URL:** {dataset['url']}\n"
            f"- **License:** {dataset['license']}\n"
            f"- **Commercial Use:** {'Yes' if dataset.get('commercial_use') else 'No'}\n"
            f"- **Estimated Size:** {dataset.get('estimated_size_mb', '?')} MB\n"
            f"- **Supported Formats:** {', '.join(dataset.get('formats', ['unknown']))}\n\n"
            f"## Instructions\n\n"
            f"1. Visit: {dataset['url']}\n"
            f"2. Review and accept the license terms.\n"
            f"3. Download the dataset files.\n"
            f"4. Extract the files into this directory: `{target_dir}`\n"
            f"5. Run the validator: `python3 server/data/validate_datasets.py {target_dir}`\n\n"
            f"## Notes\n\n"
            f"{dataset.get('notes', 'No additional notes.')}\n",
            encoding="utf-8",
        )
        
        logger.info(f"[{dataset_id}] Manual download instructions written to {readme}")

    def _print_summary(self) -> None:
        """Print download statistics."""
        total = sum(self.stats.values())
        logger.info("\n" + "="*60)
        logger.info("Download Summary")
        logger.info("="*60)
        logger.info(f"Downloaded:  {self.stats['downloaded']}")
        logger.info(f"Skipped:     {self.stats['skipped']}")
        logger.info(f"Failed:      {self.stats['failed']}")
        logger.info(f"Total:       {total}")
        logger.info("="*60)
        logger.info(f"\nDatasets stored in: {self.output_root}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated dataset fetcher for Pattern Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all enabled datasets
  python3 -m server.data.download_datasets --output-root ./datasets
  
  # Download only embroidery datasets
  python3 -m server.data.download_datasets --category embroidery
  
  # Download a specific dataset
  python3 -m server.data.download_datasets --name dtd
  
  # Dry run (show what would be downloaded)
  python3 -m server.data.download_datasets --dry-run
        """,
    )
    
    parser.add_argument(
        "--output-root",
        default="./datasets",
        help="Output directory for downloaded datasets (default: ./datasets)",
    )
    parser.add_argument(
        "--category",
        choices=["embroidery", "texture", "fashion", "historical", "community"],
        help="Download only datasets in a specific category",
    )
    parser.add_argument(
        "--name",
        help="Download only the specified dataset (by ID)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-download datasets that already exist",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Do not automatically extract downloaded archives",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel download workers (default: 4)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load manifest
    manifest_path = Path(__file__).parent / "dataset_manifest.json"
    
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return 1
    
    # Create fetcher
    config = {
        "skip_existing": not args.no_skip_existing,
        "extract_archives": not args.no_extract,
        "parallel_workers": args.workers,
    }
    
    fetcher = DatasetFetcher(
        manifest_path=manifest_path,
        output_root=Path(args.output_root),
        config=config,
    )
    
    # Show what would be downloaded
    datasets_to_fetch = fetcher.datasets
    if args.category:
        datasets_to_fetch = [d for d in datasets_to_fetch if d["category"] == args.category]
    if args.name:
        datasets_to_fetch = [d for d in datasets_to_fetch if d["id"] == args.name]
    
    if args.dry_run:
        logger.info("DRY RUN: Would download the following datasets:\n")
        for dataset in datasets_to_fetch:
            logger.info(f"  - {dataset['id']:<20} ({dataset['category']:<10}) {dataset['estimated_size_mb']:>5} MB")
        logger.info(f"\nTotal: ~{sum(d.get('estimated_size_mb', 0) for d in datasets_to_fetch)} MB")
        return 0
    
    # Download
    fetcher.fetch_all(category_filter=args.category, name_filter=args.name)
    
    return 0 if fetcher.stats["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
