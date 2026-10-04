#!/usr/bin/env python3
"""Thingiverse API fetcher for embroidery designs.

Requires Thingiverse API token from https://www.thingiverse.com/apps
Set via environment variable: THINGIVERSE_API_TOKEN
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("Error: requests not installed. Install with: pip install requests")
    exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class ThingiverseFetcher:
    """Fetches embroidery designs from Thingiverse API."""

    API_BASE = "https://api.thingiverse.com"

    def __init__(self, api_token: str | None = None):
        self.api_token = api_token or os.getenv("THINGIVERSE_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "Thingiverse API token required. "
                "Set THINGIVERSE_API_TOKEN environment variable or pass --token"
            )
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.api_token}"

    def search(self, query: str = "embroidery", limit: int = 20) -> list[dict]:
        """Search for designs on Thingiverse."""
        logger.info(f"Searching for '{query}'...")
        
        url = urljoin(self.API_BASE, "/search")
        params = {"q": query, "type": "things", "sort": "relevant", "limit": limit}
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        
        results = response.json()
        logger.info(f"Found {len(results.get('hits', []))} results")
        
        return results.get("hits", [])

    def get_thing(self, thing_id: int) -> dict:
        """Get details for a specific thing."""
        url = urljoin(self.API_BASE, f"/things/{thing_id}")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def download_files(self, thing_id: int, output_dir: Path) -> None:
        """Download all files for a thing."""
        thing = self.get_thing(thing_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading files for: {thing['name']}")
        
        if "files" not in thing:
            logger.warning(f"No files found for thing {thing_id}")
            return
        
        for file_info in thing["files"]:
            url = file_info["url"]
            filename = file_info["name"]
            
            try:
                logger.info(f"  Downloading: {filename}")
                response = self.session.get(url, stream=True)
                response.raise_for_status()
                
                file_path = output_dir / filename
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"  Saved: {file_path}")
            
            except Exception as e:
                logger.error(f"  Failed to download {filename}: {e}")

    def fetch_collection(self, query: str = "embroidery", output_dir: Path | None = None, limit: int = 20) -> None:
        """Fetch a collection of designs."""
        if output_dir is None:
            output_dir = Path("./datasets/embroidery/thingiverse")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = self.search(query, limit)
        
        for i, thing in enumerate(results, 1):
            logger.info(f"\n[{i}/{len(results)}] Processing: {thing['name']}")
            try:
                thing_dir = output_dir / f"{thing['id']}_{thing['name'][:30]}"
                self.download_files(thing["id"], thing_dir)
            except Exception as e:
                logger.error(f"Failed to process thing {thing['id']}: {e}")
        
        logger.info(f"\nDownload complete. Files saved to {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch embroidery designs from Thingiverse",
    )
    parser.add_argument(
        "--query",
        default="embroidery",
        help="Search query (default: embroidery)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of designs to download (default: 20)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory (default: ./datasets/embroidery/thingiverse)",
    )
    parser.add_argument(
        "--token",
        help="Thingiverse API token (or set THINGIVERSE_API_TOKEN env var)",
    )
    
    args = parser.parse_args()
    
    try:
        fetcher = ThingiverseFetcher(args.token)
        output_dir = Path(args.output_dir) if args.output_dir else None
        fetcher.fetch_collection(args.query, output_dir, args.limit)
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
