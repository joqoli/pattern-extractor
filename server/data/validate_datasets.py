#!/usr/bin/env python3
"""Dataset validation and integrity checking."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class DatasetValidator:
    """Validates downloaded datasets for completeness and integrity."""

    def __init__(self, dataset_root: Path):
        self.dataset_root = Path(dataset_root)
        self.results = {"valid": 0, "warnings": 0, "errors": 0}

    def validate_all(self) -> None:
        """Validate all dataset subdirectories."""
        logger.info(f"Validating datasets in {self.dataset_root}")
        
        for category_dir in self.dataset_root.iterdir():
            if not category_dir.is_dir():
                continue
            
            for dataset_dir in category_dir.iterdir():
                if not dataset_dir.is_dir():
                    continue
                
                self.validate_dataset(dataset_dir)
        
        self._print_summary()

    def validate_dataset(self, dataset_dir: Path) -> bool:
        """Validate a single dataset directory."""
        dataset_name = dataset_dir.relative_to(self.dataset_root)
        logger.info(f"Validating: {dataset_name}")
        
        checks = [
            self._check_not_empty,
            self._check_readme,
            self._check_file_integrity,
        ]
        
        all_passed = True
        for check in checks:
            try:
                if not check(dataset_dir):
                    all_passed = False
            except Exception as e:
                logger.error(f"  ✗ Check failed: {e}")
                self.results["errors"] += 1
                all_passed = False
        
        if all_passed:
            self.results["valid"] += 1
            logger.info(f"  ✓ {dataset_name} is valid")
        
        return all_passed

    def _check_not_empty(self, dataset_dir: Path) -> bool:
        """Check that dataset directory is not empty."""
        files = list(dataset_dir.glob("*"))
        if not files:
            logger.warning(f"  ⚠ Dataset directory is empty")
            self.results["warnings"] += 1
            return False
        logger.debug(f"  ✓ Contains {len(files)} file(s)/dir(s)")
        return True

    def _check_readme(self, dataset_dir: Path) -> bool:
        """Check for documentation file."""
        readme_names = ["README.md", "DOWNLOAD_INSTRUCTIONS.md", "API_INSTRUCTIONS.md"]
        has_readme = any((dataset_dir / name).exists() for name in readme_names)
        
        if not has_readme:
            logger.warning(f"  ⚠ No documentation file found")
            self.results["warnings"] += 1
        else:
            logger.debug(f"  ✓ Documentation found")
        
        return True  # Not a hard error

    def _check_file_integrity(self, dataset_dir: Path) -> bool:
        """Check for common dataset file types."""
        valid_extensions = {
            ".jpg", ".jpeg", ".png", ".gif",  # Images
            ".dst", ".jef", ".pes", ".exp", ".vip",  # Embroidery
            ".zip", ".tar", ".gz",  # Archives
            ".json", ".csv",  # Data files
            ".pdf", ".txt",  # Documents
        }
        
        files = list(dataset_dir.rglob("*"))
        data_files = [f for f in files if f.is_file() and f.suffix.lower() in valid_extensions]
        
        if not data_files:
            logger.warning(f"  ⚠ No recognized dataset files found")
            self.results["warnings"] += 1
            return False
        
        logger.debug(f"  ✓ Found {len(data_files)} recognized file(s)")
        return True

    def _print_summary(self) -> None:
        """Print validation summary."""
        total = sum(self.results.values())
        logger.info("\n" + "="*60)
        logger.info("Validation Summary")
        logger.info("="*60)
        logger.info(f"Valid:    {self.results['valid']}")
        logger.info(f"Warnings: {self.results['warnings']}")
        logger.info(f"Errors:   {self.results['errors']}")
        logger.info(f"Total:    {total}")
        logger.info("="*60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate downloaded datasets")
    parser.add_argument(
        "dataset_root",
        nargs="?",
        default="./datasets",
        help="Root directory of datasets to validate (default: ./datasets)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    dataset_root = Path(args.dataset_root)
    if not dataset_root.exists():
        logger.error(f"Dataset root not found: {dataset_root}")
        return 1
    
    validator = DatasetValidator(dataset_root)
    validator.validate_all()
    
    return 0 if validator.results["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
