"""
HTTP client for Complete Tang Poems scraper.

Handles all HTTP requests with retry logic, rate limiting, and proper error handling.
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Optional
from urllib.parse import quote

from constants import (
    DEFAULT_DELAY_SECONDS,
    MAX_RETRIES,
    INITIAL_RETRY_WAIT_SECONDS,
    RETRY_BACKOFF_MULTIPLIER,
    HTTP_TIMEOUT_SECONDS,
    USER_AGENT,
    RATE_LIMIT_STATUS_CODES
)

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP client with retry logic and rate limiting for Wikisource scraping."""

    def __init__(self, delay: float = DEFAULT_DELAY_SECONDS):
        """
        Initialize the HTTP client.

        Args:
            delay: Delay in seconds between requests (default: 2.0)
        """
        self.delay = delay
        self.session = requests.Session()

        # Follow Wikimedia User-Agent policy
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept-Encoding': 'gzip'
        })

    def fetch_page(self, url: str, retry_count: int = 0) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a page from Wikisource with retry logic.

        Args:
            url: URL to fetch
            retry_count: Current retry attempt (used for recursion)

        Returns:
            BeautifulSoup object if successful, None if all retries failed

        Raises:
            None - errors are logged and None is returned
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=HTTP_TIMEOUT_SECONDS)

            # Handle rate limiting (429 or 403)
            if response.status_code in RATE_LIMIT_STATUS_CODES:
                if retry_count >= MAX_RETRIES:
                    logger.error(
                        f"Max retries ({MAX_RETRIES}) exceeded for {url}. "
                        f"Status: {response.status_code}"
                    )
                    return None

                # Check for Retry-After header
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                else:
                    # Exponential backoff: 5s, 10s, 20s
                    wait_time = INITIAL_RETRY_WAIT_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** retry_count)

                logger.warning(
                    f"Rate limited (HTTP {response.status_code}) for {url}. "
                    f"Waiting {wait_time}s before retry {retry_count + 1}/{MAX_RETRIES}"
                )
                time.sleep(wait_time)
                return self.fetch_page(url, retry_count + 1)

            response.raise_for_status()
            time.sleep(self.delay)  # Be respectful to the server
            return BeautifulSoup(response.content, 'html.parser')

        except requests.HTTPError as e:
            logger.error(
                f"HTTP error fetching {url}: {e.response.status_code} - {e}"
            )
            if retry_count < MAX_RETRIES:
                wait_time = INITIAL_RETRY_WAIT_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** retry_count)
                logger.info(f"Retrying after {wait_time}s... (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return self.fetch_page(url, retry_count + 1)
            return None

        except requests.Timeout as e:
            logger.error(
                f"Timeout ({HTTP_TIMEOUT_SECONDS}s) fetching {url}: {e}"
            )
            if retry_count < MAX_RETRIES:
                wait_time = INITIAL_RETRY_WAIT_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** retry_count)
                logger.info(f"Retrying after {wait_time}s... (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return self.fetch_page(url, retry_count + 1)
            return None

        except requests.RequestException as e:
            logger.error(f"Request error fetching {url}: {type(e).__name__} - {e}")
            if retry_count < MAX_RETRIES:
                wait_time = INITIAL_RETRY_WAIT_SECONDS * (RETRY_BACKOFF_MULTIPLIER ** retry_count)
                logger.info(f"Retrying after {wait_time}s... (attempt {retry_count + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return self.fetch_page(url, retry_count + 1)
            return None

    def fetch_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """
        Fetch JSON data from an API endpoint.

        Args:
            url: API URL
            params: Query parameters

        Returns:
            Parsed JSON response as dictionary, or None if failed
        """
        try:
            logger.debug(f"Fetching JSON from: {url}")
            response = self.session.get(url, params=params, timeout=HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Error fetching JSON from {url}: {type(e).__name__} - {e}")
            return None

        except ValueError as e:
            logger.error(f"Error parsing JSON from {url}: {e}")
            return None

    def close(self):
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
