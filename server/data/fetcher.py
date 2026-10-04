#!/usr/bin/env python3
"""Advanced automated dataset fetcher for Pattern Extractor.

Supports multiple download strategies with intelligent fallbacks and progress tracking.

Usage:
    make download-datasets                              # Download all enabled datasets
    python3 server/data/fetcher.py --category embroidery  # Download embroidery only
    python3 server/data/fetcher.py --name dtd-texture     # Download specific dataset
    python3 server/data/fetcher.py --dry-run             # Preview without downloading
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlencode

try:
    import aiohttp
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Error: required packages not found. Install with: pip install aiohttp requests")
    exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DownloadProgress:
    """Track download progress with ETA."""

    def __init__(self, total_size: int):
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = datetime.now()

    def update(self, chunk_size: int) -> str:
        self.downloaded += chunk_size
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > 0:
            speed = self.downloaded / elapsed / 1024 / 1024  # MB/s
            if self.total_size > 0:
                pct = (self.downloaded / self.total_size) * 100
                remaining = (self.total_size - self.downloaded) / (speed * 1024 * 1024) if speed > 0 else 0
                return f"{pct:5.1f}% | {speed:6.2f} MB/s | {remaining:6.0f}s remaining"
        return f"{self.downloaded / 1024 / 1024:8.1f} MB"


class DatasetFetcher:
    """Orchestrates dataset downloads with multiple strategies and intelligent fallbacks."""

    STRATEGIES = {
        "direct-http-archive": "_download_direct_http",
        "direct-http-catalog": "_download_direct_http_catalog",
        "git-clone-shallow": "_download_git_clone",
        "web-scrape-links": "_download_web_scrape_links",
        "web-scrape-catalog": "_download_web_scrape_catalog",
        "web-scrape-freebies": "_download_web_scrape_freebies",
        "kaggle-cli": "_download_kaggle",
        "thingiverse-api": "_download_thingiverse_api",
        "github-api-repos": "_download_github_api_repos",
        "gutendex-api": "_download_gutendex_api",
        "manual-registration": "_write_manual_instructions",
    }

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

        self.stats = {"downloaded": 0, "failed": 0, "skipped": 0, "total_mb": 0}
        self._session = None
        self.executor = ThreadPoolExecutor(max_workers=self.download_config.get("parallel_workers", 4))

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

    def fetch_all(self, category_filter: str | None = None, name_filter: str | None = None, dry_run: bool = False) -> None:
        """Download all enabled datasets."""
        datasets_to_fetch = self.datasets

        if not category_filter and not name_filter:
            datasets_to_fetch = [d for d in datasets_to_fetch if d.get("enabled", True)]
        else:
            if category_filter:
                datasets_to_fetch = [d for d in datasets_to_fetch if d["category"] == category_filter]
            if name_filter:
                datasets_to_fetch = [d for d in datasets_to_fetch if d["id"] == name_filter]

        logger.info(f"Found {len(datasets_to_fetch)} dataset(s) to process")
        logger.info(f"Output root: {self.output_root}")
        logger.info(f"Parallel workers: {self.download_config.get('parallel_workers', 4)}")

        if dry_run:
            self._print_dry_run(datasets_to_fetch)
            return

        futures = []
        for dataset in datasets_to_fetch:
            future = self.executor.submit(self.fetch_one, dataset)
            futures.append((dataset["id"], future))

        for dataset_id, future in futures:
            try:
                future.result(timeout=self.download_config.get("timeout_seconds", 600))
            except Exception as e:
                logger.error(f"[{dataset_id}] Download failed: {e}")
                self.stats["failed"] += 1

        self._print_summary()

    def fetch_one(self, dataset: dict[str, Any]) -> None:
        """Download a single dataset using the appropriate strategy."""
        dataset_id = dataset["id"]
        target_dir = self.output_root / dataset["target_dir"]

        if target_dir.exists() and self.download_config.get("skip_existing", True):
            logger.info(f"[{dataset_id}] Already exists, skipping")
            self.stats["skipped"] += 1
            return

        target_dir.mkdir(parents=True, exist_ok=True)
        method = dataset.get("download_method", "manual-registration")
        strategy_method = self.STRATEGIES.get(method, "_write_manual_instructions")

        logger.info(f"[{dataset_id}] Starting download (method: {method})")

        try:
            getattr(self, strategy_method)(dataset, target_dir)
            self.stats["downloaded"] += 1
            size_mb = dataset.get("estimated_size_mb", 0)
            self.stats["total_mb"] += size_mb
            logger.info(f"[{dataset_id}] ✓ Download complete")
        except Exception as e:
            logger.error(f"[{dataset_id}] ✗ Failed: {e}")
            self.stats["failed"] += 1

    def _download_direct_http(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download files directly from a single URL."""
        url = dataset["url"]
        dataset_id = dataset["id"]

        logger.info(f"[{dataset_id}] Fetching {url}")

        response = self.session.head(url, timeout=30, allow_redirects=True)
        total_size = int(response.headers.get("content-length", 0))

        if total_size > self.download_config.get("max_file_size_mb", 10000) * 1024 * 1024:
            raise ValueError(f"File too large: {total_size / 1024 / 1024:.0f} MB")

        response = self.session.get(url, stream=True, timeout=self.download_config.get("timeout_seconds", 600))
        response.raise_for_status()

        filename = url.split("/")[-1] or f"{dataset_id}.tar.gz"
        file_path = target_dir / filename

        progress = DownloadProgress(total_size)

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    logger.debug(f"[{dataset_id}] {progress.update(len(chunk))}")

        logger.info(f"[{dataset_id}] Downloaded {total_size / 1024 / 1024:.1f} MB")

        if dataset.get("extract", False):
            self._extract_archive(file_path, target_dir)

    def _download_direct_http_catalog(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download from a paginated HTTP catalog."""
        dataset_id = dataset["id"]
        base_url = dataset["url"]
        pagination_param = dataset.get("pagination_param", "page")
        per_page = dataset.get("per_page", 100)
        max_pages = dataset.get("max_pages", 10)

        logger.info(f"[{dataset_id}] Fetching paginated catalog (max {max_pages} pages)")

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning(f"[{dataset_id}] BeautifulSoup4 not installed. Skipping catalog scrape.")
            self._write_manual_instructions(dataset, target_dir)
            return

        downloaded_count = 0
        for page in range(1, max_pages + 1):
            try:
                params = {pagination_param: page}
                url = f"{base_url}?{urlencode(params)}"
                logger.debug(f"[{dataset_id}] Fetching page {page}: {url}")

                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                links = soup.find_all("a", {"href": True})
                download_links = [link["href"] for link in links if any(ext in link["href"].lower() for ext in dataset.get("formats", []))]

                if not download_links:
                    logger.info(f"[{dataset_id}] No more files found at page {page}")
                    break

                for href in download_links:
                    if not href.startswith("http"):
                        href = urljoin(base_url, href)

                    try:
                        filename = href.split("/")[-1] or f"{dataset_id}_{downloaded_count}.zip"
                        file_path = target_dir / filename

                        if file_path.exists():
                            logger.debug(f"[{dataset_id}] File already exists: {filename}")
                            continue

                        resp = self.session.get(href, stream=True, timeout=60)
                        if resp.status_code == 200:
                            with open(file_path, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=65536):
                                    if chunk:
                                        f.write(chunk)
                            downloaded_count += 1
                            logger.debug(f"[{dataset_id}] Downloaded: {filename}")
                    except Exception as e:
                        logger.debug(f"[{dataset_id}] Failed to download file: {e}")

                if len(download_links) < per_page:
                    logger.info(f"[{dataset_id}] Fewer results than expected. Stopping pagination.")
                    break

            except Exception as e:
                logger.warning(f"[{dataset_id}] Error fetching page {page}: {e}")
                break

        logger.info(f"[{dataset_id}] Downloaded {downloaded_count} file(s) from catalog")

    def _download_git_clone(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Clone a git repository with shallow clone."""
        url = dataset["url"]
        dataset_id = dataset["id"]
        depth = dataset.get("depth", 1)

        logger.info(f"[{dataset_id}] Cloning git repo (depth={depth})")

        try:
            subprocess.run(
                ["git", "clone", "--depth", str(depth), url, str(target_dir)],
                check=True,
                capture_output=True,
                timeout=self.download_config.get("timeout_seconds", 600),
            )
            logger.info(f"[{dataset_id}] Git clone complete")
        except FileNotFoundError:
            logger.error(f"[{dataset_id}] Git not found. Install with: apt-get install git")
            raise
        except subprocess.CalledProcessError as e:
            logger.error(f"[{dataset_id}] Git clone failed: {e.stderr.decode()}")
            raise

    def _download_web_scrape_links(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Scrape download links from a webpage."""
        dataset_id = dataset["id"]
        url = dataset["url"]
        selector = dataset.get("selector", "a[href*=download]")

        logger.info(f"[{dataset_id}] Scraping download links from {url}")

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error(f"[{dataset_id}] BeautifulSoup4 required. Install with: pip install beautifulsoup4")
            raise

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        links = soup.select(selector)

        if not links:
            logger.warning(f"[{dataset_id}] No links found with selector: {selector}")
            return

        logger.info(f"[{dataset_id}] Found {len(links)} download link(s)")

        for i, link in enumerate(links[:20]):
            href = link.get("href")
            if not href:
                continue

            if not href.startswith("http"):
                href = urljoin(url, href)

            try:
                filename = href.split("/")[-1] or f"file_{i}.zip"
                file_path = target_dir / filename

                if file_path.exists():
                    logger.debug(f"[{dataset_id}] File exists: {filename}")
                    continue

                logger.debug(f"[{dataset_id}] Downloading: {filename}")
                resp = self.session.get(href, stream=True, timeout=60)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                    logger.debug(f"[{dataset_id}] Saved: {filename}")
            except Exception as e:
                logger.debug(f"[{dataset_id}] Failed: {e}")

    def _download_web_scrape_catalog(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Scrape a catalog page for links (similar to links scrape)."""
        self._download_web_scrape_links(dataset, target_dir)

    def _download_web_scrape_freebies(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Scrape free tier offerings from subscription-based sites."""
        dataset_id = dataset["id"]
        url = dataset["url"]

        logger.info(f"[{dataset_id}] Scraping free tier from {url}")

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error(f"[{dataset_id}] BeautifulSoup4 required")
            raise

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        # Look for free/freebie items
        free_items = soup.find_all("div", {"class": ["freebie", "free-item", "free"]})

        logger.info(f"[{dataset_id}] Found {len(free_items)} free item(s)")

        for item in free_items[:50]:
            links = item.find_all("a", {"href": True})
            for link in links:
                href = link["href"]
                if not href.startswith("http"):
                    href = urljoin(url, href)
                try:
                    filename = href.split("/")[-1] or f"freebie.zip"
                    file_path = target_dir / filename
                    if file_path.exists():
                        continue
                    resp = self.session.get(href, stream=True, timeout=60)
                    if resp.status_code == 200:
                        with open(file_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=65536):
                                if chunk:
                                    f.write(chunk)
                        logger.debug(f"[{dataset_id}] Downloaded: {filename}")
                except Exception:
                    pass

    def _download_kaggle(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download from Kaggle using Kaggle CLI."""
        dataset_id = dataset["id"]
        kaggle_dataset_name = dataset.get("kaggle_dataset_name")

        if not kaggle_dataset_name:
            raise ValueError(f"[{dataset_id}] kaggle_dataset_name required in manifest")

        logger.info(f"[{dataset_id}] Downloading Kaggle dataset: {kaggle_dataset_name}")

        try:
            subprocess.run(["kaggle", "--version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.error(f"[{dataset_id}] Kaggle CLI not found. Install with: pip install kaggle")
            logger.error(f"[{dataset_id}] Set up credentials at ~/.kaggle/kaggle.json")
            raise

        try:
            subprocess.run(
                ["kaggle", "datasets", "download", "-d", kaggle_dataset_name, "-p", str(target_dir)],
                check=True,
                capture_output=True,
                timeout=self.download_config.get("timeout_seconds", 600),
            )

            if dataset.get("extract", False):
                for zip_file in target_dir.glob("*.zip"):
                    self._extract_archive(zip_file, target_dir)

            logger.info(f"[{dataset_id}] Kaggle download complete")
        except subprocess.CalledProcessError as e:
            logger.error(f"[{dataset_id}] Kaggle download failed: {e.stderr.decode()}")
            raise

    def _download_thingiverse_api(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download from Thingiverse API."""
        dataset_id = dataset["id"]
        api_url = dataset.get("api_url", "https://api.thingiverse.com/search")
        api_token = os.getenv("THINGIVERSE_API_TOKEN")

        if not api_token:
            logger.warning(f"[{dataset_id}] THINGIVERSE_API_TOKEN not set. Set env var or skip.")
            self._write_manual_instructions(dataset, target_dir)
            return

        logger.info(f"[{dataset_id}] Fetching from Thingiverse API")

        headers = {"Authorization": f"Bearer {api_token}"}
        params = dataset.get("api_params", {})
        params["limit"] = 50
        max_results = dataset.get("max_results", 100)

        downloaded_count = 0
        page = 0

        while downloaded_count < max_results:
            params["offset"] = page * 50
            try:
                response = self.session.get(api_url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                results = data.get("hits", [])
                if not results:
                    break

                for thing in results:
                    thing_id = thing["id"]
                    thing_name = thing.get("name", f"thing_{thing_id}")
                    thing_dir = target_dir / f"{thing_id}_{thing_name[:40]}"
                    thing_dir.mkdir(parents=True, exist_ok=True)

                    # Write thing metadata
                    metadata_file = thing_dir / "metadata.json"
                    with open(metadata_file, "w", encoding="utf-8") as f:
                        json.dump(thing, f, indent=2)

                    downloaded_count += 1
                    logger.debug(f"[{dataset_id}] Processed: {thing_name}")

                    if downloaded_count >= max_results:
                        break

                page += 1
            except Exception as e:
                logger.warning(f"[{dataset_id}] API error: {e}")
                break

        logger.info(f"[{dataset_id}] Downloaded metadata for {downloaded_count} design(s)")

    def _download_github_api_repos(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download repositories from GitHub API."""
        dataset_id = dataset["id"]
        url = dataset["url"]

        logger.info(f"[{dataset_id}] Searching GitHub for repositories")

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.error(f"[{dataset_id}] BeautifulSoup4 required")
            raise

        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        repos = soup.find_all("a", {"data-filterable-for": "your-repos-filter"})

        logger.info(f"[{dataset_id}] Found {len(repos)} repository link(s)")

        for repo in repos[:20]:
            repo_url = repo.get("href")
            if repo_url and repo_url.startswith("/"):
                repo_url = f"https://github.com{repo_url}"

            if not repo_url:
                continue

            try:
                repo_name = repo_url.split("/")[-1]
                repo_dir = target_dir / repo_name

                if repo_dir.exists():
                    logger.debug(f"[{dataset_id}] Repo exists: {repo_name}")
                    continue

                logger.debug(f"[{dataset_id}] Cloning: {repo_url}")
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, str(repo_dir)],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
                logger.debug(f"[{dataset_id}] Cloned: {repo_name}")
            except Exception as e:
                logger.debug(f"[{dataset_id}] Failed to clone repo: {e}")

    def _download_gutendex_api(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Download from Gutendex API (Project Gutenberg mirror)."""
        dataset_id = dataset["id"]
        api_url = dataset.get("api_url", "https://gutendex.com/books")
        params = dataset.get("api_params", {})

        logger.info(f"[{dataset_id}] Fetching from Gutendex API")

        try:
            response = self.session.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            books = data.get("results", [])
            logger.info(f"[{dataset_id}] Found {len(books)} book(s)")

            for book in books[:50]:
                book_id = book["id"]
                book_name = book.get("title", f"book_{book_id}")
                book_dir = target_dir / f"{book_id}_{book_name[:40]}"
                book_dir.mkdir(parents=True, exist_ok=True)

                # Write metadata
                metadata_file = book_dir / "metadata.json"
                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(book, f, indent=2)

                # Download formats if available
                formats = book.get("formats", {})
                for fmt, url in list(formats.items())[:3]:  # Limit to 3 formats
                    try:
                        ext = fmt.split("/")[-1]
                        file_path = book_dir / f"{book_id}.{ext}"
                        if file_path.exists():
                            continue

                        resp = self.session.get(url, stream=True, timeout=60)
                        if resp.status_code == 200:
                            with open(file_path, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=65536):
                                    if chunk:
                                        f.write(chunk)
                            logger.debug(f"[{dataset_id}] Downloaded: {file_path.name}")
                    except Exception as e:
                        logger.debug(f"[{dataset_id}] Failed to download format: {e}")

        except Exception as e:
            logger.error(f"[{dataset_id}] Gutendex API error: {e}")
            raise

    def _extract_archive(self, archive_path: Path, extract_to: Path) -> None:
        """Extract tar.gz, tar, or zip archives."""
        logger.info(f"Extracting: {archive_path.name}")

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
                logger.warning(f"Unsupported archive: {archive_path}")
                return

            archive_path.unlink()
            logger.info(f"Extraction complete")
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise

    def _write_manual_instructions(self, dataset: dict[str, Any], target_dir: Path) -> None:
        """Write manual download instructions."""
        dataset_id = dataset["id"]
        readme = target_dir / "DOWNLOAD_INSTRUCTIONS.md"

        readme.write_text(
            f"# {dataset['name']}\n\n"
            f"**Status:** Manual download or authentication required\n\n"
            f"## Details\n\n"
            f"- **URL:** {dataset['url']}\n"
            f"- **License:** {dataset['license']}\n"
            f"- **Commercial Use:** {'✓ Yes' if dataset.get('commercial_use') else '✗ No'}\n"
            f"- **Estimated Size:** {dataset.get('estimated_size_mb', '?')} MB\n"
            f"- **Formats:** {', '.join(dataset.get('formats', ['unknown']))}\n\n"
            f"## Instructions\n\n"
            f"1. Visit: {dataset['url']}\n"
            f"2. Review and accept the license terms\n"
            f"3. Download the dataset files\n"
            f"4. Extract files into this directory: `{target_dir}`\n"
            f"5. Validate: `python3 server/data/validate_datasets.py {target_dir.parent}`\n\n"
            f"## Notes\n\n"
            f"{dataset.get('notes', 'No additional notes.')}\n",
            encoding="utf-8",
        )

        logger.info(f"[{dataset_id}] Manual instructions written to {readme}")

    def _print_dry_run(self, datasets: list[dict[str, Any]]) -> None:
        """Print what would be downloaded without actually downloading."""
        logger.info("\n" + "="*80)
        logger.info("DRY RUN: The following datasets would be downloaded")
        logger.info("="*80)

        total_size = 0
        for dataset in datasets:
            size_mb = dataset.get("estimated_size_mb", 0)
            total_size += size_mb
            status = "[auto]" if dataset.get("download_method") != "manual-registration" else "[manual]"
            logger.info(
                f"{status} {dataset['id']:<25} ({dataset['category']:<10}) {size_mb:>6} MB"
            )

        logger.info("="*80)
        logger.info(f"Total: ~{total_size} MB across {len(datasets)} dataset(s)")
        logger.info("="*80 + "\n")

    def _print_summary(self) -> None:
        """Print download statistics."""
        logger.info("\n" + "="*80)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("="*80)
        logger.info(f"Downloaded:   {self.stats['downloaded']} dataset(s)")
        logger.info(f"Skipped:      {self.stats['skipped']} dataset(s)")
        logger.info(f"Failed:       {self.stats['failed']} dataset(s)")
        logger.info(f"Total Data:   ~{self.stats['total_mb']} MB")
        logger.info("="*80)
        logger.info(f"\nDatasets stored in: {self.output_root}")
        logger.info(f"Next: python3 server/data/validate_datasets.py {self.output_root}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated dataset fetcher for Pattern Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all enabled datasets
  python3 server/data/fetcher.py --output-root ./datasets
  
  # Download specific category
  python3 server/data/fetcher.py --category embroidery
  
  # Download single dataset
  python3 server/data/fetcher.py --name dtd-texture
  
  # Dry run (show what would be downloaded)
  python3 server/data/fetcher.py --dry-run
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

    manifest_path = Path(__file__).parent / "dataset_manifest.json"

    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return 1

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

    fetcher.fetch_all(
        category_filter=args.category,
        name_filter=args.name,
        dry_run=args.dry_run,
    )

    return 0 if fetcher.stats["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
