"""
Persistent caching utilities for Complete Tang Poems scraper.

Provides file-based caching to avoid redundant API requests across scraping sessions.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Any, Dict

from constants import AUTHOR_CACHE_FILENAME, DEFAULT_CACHE_DIR, CACHE_VERSION

logger = logging.getLogger(__name__)


class PersistentCache:
    """
    Persistent file-based cache for author metadata.

    Stores cache data in JSON format to avoid redundant API requests
    across multiple scraping sessions.
    """

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR, filename: str = AUTHOR_CACHE_FILENAME):
        """
        Initialize the persistent cache.

        Args:
            cache_dir: Directory to store cache files
            filename: Name of the cache file
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / filename
        self.cache: Dict[str, Any] = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """
        Load cache from file.

        Returns:
            Dictionary containing cached data, or empty dict if file doesn't exist
        """
        if not self.cache_file.exists():
            logger.debug(f"Cache file not found: {self.cache_file}. Starting with empty cache.")
            return {'version': CACHE_VERSION, 'data': {}}

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            if cache_data.get('version') != CACHE_VERSION:
                logger.warning(
                    f"Cache version mismatch (expected {CACHE_VERSION}, got {cache_data.get('version')}). "
                    f"Invalidating cache."
                )
                return {'version': CACHE_VERSION, 'data': {}}

            logger.info(f"Loaded cache from {self.cache_file} ({len(cache_data.get('data', {}))} entries)")
            return cache_data

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error loading cache from {self.cache_file}: {e}. Starting with empty cache.")
            return {'version': CACHE_VERSION, 'data': {}}

    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved cache to {self.cache_file} ({len(self.cache.get('data', {}))} entries)")

        except IOError as e:
            logger.error(f"Error saving cache to {self.cache_file}: {e}")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists, None otherwise
        """
        return self.cache.get('data', {}).get(key)

    def set(self, key: str, value: Any):
        """
        Set value in cache and persist to file.

        Args:
            key: Cache key
            value: Value to cache
        """
        if 'data' not in self.cache:
            self.cache['data'] = {}

        self.cache['data'][key] = value
        self._save_cache()

    def has(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists in cache
        """
        return key in self.cache.get('data', {})

    def clear(self):
        self.cache = {'version': CACHE_VERSION, 'data': {}}
        self._save_cache()
        logger.info(f"Cache cleared: {self.cache_file}")

    def size(self) -> int:
        """
        Get number of entries in cache.

        Returns:
            Number of cached entries
        """
        return len(self.cache.get('data', {}))

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator."""
        return self.has(key)

    def __len__(self) -> int:
        """Support len() function."""
        return self.size()
