#!/usr/bin/env python3
"""
Scraper for Complete Tang Poems (全唐詩) from Chinese Wikisource.

Extracts poems with title, author, and content into JSON format.
Refactored to use modular architecture with separation of concerns.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from models import Poem
from http_client import HttpClient
from cache import PersistentCache
from author_service import AuthorMetadataService
from author_database import AuthorDatabase
from extraction_strategies import (
    StandardFormatStrategy,
    YuefuFormatStrategy,
    LegacyParagraphExtractionStrategy
)
from constants import (
    VOLUME_URL_TEMPLATE,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_RAW_OUTPUT_DIR,
    MIN_VOLUME_NUMBER,
    MAX_VOLUME_NUMBER,
    LOG_FORMAT
)
import volume_specs
from volume_specs import VolumeFormat

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


class TangPoemsScraper:
    """
    Main scraper orchestrator for Complete Tang Poems.

    Coordinates HTTP client, author service, and extraction strategies
    to scrape and save poems from Wikisource.
    """

    def __init__(self, output_dir: str = None, delay: float = DEFAULT_DELAY_SECONDS):
        """
        Initialize the scraper.

        Args:
            output_dir: Directory to save raw JSON files
            delay: Delay in seconds between requests (be respectful!)
        """
        self.output_dir = Path(output_dir or DEFAULT_RAW_OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)

        self.http_client = HttpClient(delay=delay)
        self.cache = PersistentCache()
        self.author_service = AuthorMetadataService(self.http_client, self.cache)
        self.author_database = AuthorDatabase(filepath=str(self.output_dir / 'authors.json'))

        self.standard_strategy = StandardFormatStrategy(self.author_service, self.author_database)
        self.yuefu_strategy = YuefuFormatStrategy(self.author_service, self.author_database)
        self.legacy_paragraph_strategy = LegacyParagraphExtractionStrategy(self.author_service, self.author_database)

    def _get_strategy_for_volume(self, volume_num: int):
        """
        Get the appropriate extraction strategy for a volume.

        Args:
            volume_num: Volume number

        Returns:
            PoemExtractionStrategy instance
        """
        volume_format = volume_specs.get_volume_format(volume_num)

        if volume_format == VolumeFormat.YUEFU:
            logger.debug(f"Volume {volume_num} uses yuefu format")
            return self.yuefu_strategy
        elif volume_format == VolumeFormat.LEGACY_PARAGRAPH:
            logger.debug(f"Volume {volume_num} uses legacy paragraph format")
            return self.legacy_paragraph_strategy
        else:
            logger.debug(f"Volume {volume_num} uses standard format")
            return self.standard_strategy

    def scrape_volume(self, volume_num: int) -> List[Poem]:
        """
        Scrape a single volume.

        Args:
            volume_num: Volume number (1-900)

        Returns:
            List of Poem objects extracted from the volume
        """
        if not MIN_VOLUME_NUMBER <= volume_num <= MAX_VOLUME_NUMBER:
            logger.error(
                f"Invalid volume number {volume_num}. "
                f"Must be between {MIN_VOLUME_NUMBER} and {MAX_VOLUME_NUMBER}."
            )
            return []

        url = VOLUME_URL_TEMPLATE.format(volume_num)
        soup = self.http_client.fetch_page(url)

        if soup is None:
            logger.error(
                f"Failed to fetch volume {volume_num} from {url}. "
                f"The page may not exist or there was a network error."
            )
            return []

        strategy = self._get_strategy_for_volume(volume_num)
        poems = strategy.extract(soup, volume_num)

        # Fallback to legacy paragraph format if primary strategy extracted nothing
        if len(poems) == 0 and strategy != self.legacy_paragraph_strategy:
            logger.debug(f"Volume {volume_num}: Primary strategy extracted 0 poems, trying legacy paragraph format")
            poems = self.legacy_paragraph_strategy.extract(soup, volume_num)
            if len(poems) > 0:
                logger.info(f"Volume {volume_num}: Successfully extracted {len(poems)} poems using legacy format fallback")

        logger.info(
            f"Volume {volume_num}: Extracted {len(poems)} poems. "
            f"Format: {volume_specs.get_volume_description(volume_num)}"
        )

        return poems

    def scrape_volumes(self, start: int = 1, end: int = 10, save_per_volume: bool = True) -> List[Poem]:
        """
        Scrape multiple volumes.

        Args:
            start: Starting volume number (1-900)
            end: Ending volume number (1-900)
            save_per_volume: If True, save each volume separately; if False, save all at once

        Returns:
            List of all scraped Poem objects
        """
        all_poems = []

        for volume_num in range(start, end + 1):
            logger.info(f"Processing volume {volume_num}/{end}")

            volume_file = self.output_dir / f"volume_{volume_num:03d}.json"
            if volume_file.exists():
                logger.info(
                    f"Volume {volume_num} already exists at {volume_file}. "
                    f"Skipping to avoid duplicate work..."
                )
                continue

            poems = self.scrape_volume(volume_num)

            if save_per_volume and poems:
                self.save_poems(poems, volume_file)

            all_poems.extend(poems)

            self.author_database.save()

        if not save_per_volume:
            combined_file = self.output_dir / f"all_poems_{start}-{end}.json"
            self.save_poems(all_poems, combined_file)

        # also save a combined file regardless
        logger.info(f"Creating combined file for volumes {start}-{end}")
        combined_file = self.output_dir / f"combined_{start}-{end}.json"
        self.save_poems(all_poems, combined_file)

        logger.info(
            f"Scraping complete! Total poems scraped: {len(all_poems)}. "
            f"Cache stats: {self.author_service.cache_stats()}"
        )

        return all_poems

    def save_poems(self, poems: List[Poem], filepath: Path):
        """
        Save poems to a JSON file.

        Args:
            poems: List of Poem objects
            filepath: Path to save JSON file
        """
        try:
            poems_data = [poem.to_dict() for poem in poems]

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(poems_data, f, ensure_ascii=False, indent=2)

            logger.info(
                f"Successfully saved {len(poems)} poems to {filepath}. "
                f"File size: {filepath.stat().st_size / 1024:.1f} KB"
            )

        except IOError as e:
            logger.error(f"IO error saving to {filepath}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving to {filepath}: {type(e).__name__} - {e}")

    def close(self):
        """Clean up resources."""
        self.http_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Scrape Complete Tang Poems from Wikisource',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode (scrape volumes 1-3)
  python scraper.py --test

  # Scrape specific range
  python scraper.py --start 1 --end 50

  # Scrape  all 900 volumes (warning: takes a long time!)
  python scraper.py --start 1 --end 900

  # Custom delay and output directory
  python scraper.py --start 1 --end 10 --delay 3.0 --output-dir my_data
        """
    )

    parser.add_argument(
        '--start',
        type=int,
        default=1,
        help=f'Starting volume ({MIN_VOLUME_NUMBER}-{MAX_VOLUME_NUMBER}), default: 1'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=10,
        help=f'Ending volume ({MIN_VOLUME_NUMBER}-{MAX_VOLUME_NUMBER}), default: 10'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=str(DEFAULT_RAW_OUTPUT_DIR),
        help=f'Output directory for raw scraped data, default: {DEFAULT_RAW_OUTPUT_DIR}'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f'Delay between requests in seconds (minimum {DEFAULT_DELAY_SECONDS} recommended), default: {DEFAULT_DELAY_SECONDS}'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: only scrape volumes 1-3'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear author metadata cache before starting'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Test mode
    if args.test:
        logger.info("Running in TEST mode (volumes 1-3 only)")
        args.start = 1
        args.end = 3

    # Validate arguments
    if not MIN_VOLUME_NUMBER <= args.start <= MAX_VOLUME_NUMBER:
        logger.error(f"Invalid start volume: {args.start}. Must be between {MIN_VOLUME_NUMBER} and {MAX_VOLUME_NUMBER}.")
        return 1

    if not MIN_VOLUME_NUMBER <= args.end <= MAX_VOLUME_NUMBER:
        logger.error(f"Invalid end volume: {args.end}. Must be between {MIN_VOLUME_NUMBER} and {MAX_VOLUME_NUMBER}.")
        return 1

    if args.start > args.end:
        logger.error(f"Start volume ({args.start}) cannot be greater than end volume ({args.end}).")
        return 1

    if args.delay < 1.0:
        logger.warning(
            f"Delay of {args.delay}s is quite aggressive. "
            f"Please be respectful to Wikisource servers (recommended minimum: {DEFAULT_DELAY_SECONDS}s)."
        )

    with TangPoemsScraper(output_dir=args.output_dir, delay=args.delay) as scraper:
        if args.clear_cache:
            logger.info("Clearing author metadata cache...")
            scraper.author_service.clear_cache()

        scraper.scrape_volumes(start=args.start, end=args.end)

    return 0


if __name__ == '__main__':
    exit(main())
