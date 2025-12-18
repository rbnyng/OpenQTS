"""
Constants for Complete Tang Poems scraper.

This module centralizes all magic numbers and configuration values
to improve maintainability.
"""

from pathlib import Path

# URL Templates
BASE_URL = "https://zh.wikisource.org/zh-hant/全唐詩"
VOLUME_URL_TEMPLATE = "https://zh.wikisource.org/zh-hant/全唐詩/卷{:03d}"
AUTHOR_URL_TEMPLATE = "https://zh.wikisource.org/wiki/Author:{}"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"

# HTTP Request Settings
DEFAULT_DELAY_SECONDS = 0.1
"""Delay between requests to be respectful to Wikisource servers"""

MAX_RETRIES = 0
"""Maximum number of retry attempts for failed requests"""

INITIAL_RETRY_WAIT_SECONDS = 2.5
"""Initial wait time before retrying a failed request"""

RETRY_BACKOFF_MULTIPLIER = 2
"""Multiplier for exponential backoff (5s, 10s, 20s)"""

HTTP_TIMEOUT_SECONDS = 30
"""Timeout for HTTP requests"""

# User-Agent for Wikimedia compliance
# See: https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = 'TangPoemsBot/1.0 (https://github.com/rbnyng/CompleteTangPoems; educational/research) python-requests'

# Rate Limiting Status Codes
RATE_LIMIT_STATUS_CODES = [429, 403]
"""HTTP status codes that indicate rate limiting"""

# Directory Settings
DEFAULT_RAW_OUTPUT_DIR = Path("raw_output")
DEFAULT_PROCESSED_OUTPUT_DIR = Path("output")
DEFAULT_CACHE_DIR = Path(".cache")

# Volume Settings
MIN_VOLUME_NUMBER = 1
MAX_VOLUME_NUMBER = 900
"""Complete Tang Poems contains 900 volumes"""

# Author Wikidata Properties
WIKIDATA_PROP_BIRTH = 'P569'  # Date of birth
WIKIDATA_PROP_DEATH = 'P570'  # Date of death
WIKIDATA_PROP_GENDER = 'P21'
WIKIDATA_PROP_CBDB_ID = 'P497'
WIKIDATA_PROP_COURTESY_NAME = 'P1782' # (Zi)
WIKIDATA_PROP_PSEUDONYM = 'P1787'    # (Hao/Other)
WIKIDATA_PROP_VIAF_ID = 'P214'  # Virtual International Authority File
WIKIDATA_PROP_LOC_ID = 'P244'   # Library of Congress authority ID
WIKIDATA_PROP_BIRTH_PLACE = 'P19'  # Place of birth
WIKIDATA_PROP_DEATH_PLACE = 'P20'  # Place of death
WIKIDATA_PROP_OCCUPATION = 'P106'  # Occupation
WIKIDATA_PROP_ACADEMIC_DEGREE = 'P512'  # Academic degree
WIKIDATA_PROP_NOTABLE_WORK = 'P800'  # Notable work
WIKIDATA_PROP_IMAGE = 'P18'  # Image

# Gender Mapping (Wikidata Q-IDs to text)
GENDER_MAP = {
    'Q6581097': 'male',
    'Q6581072': 'female',
    'Q1052281': 'transgender female', # I don't think this exists in historical records lol
}

# Tang Dynasty Periods (Approximate boundaries based on active years)
# Based on Stephen Owen, "The Great Age of Chinese Poetry: The High Tang"
PERIOD_RANGES = [
    ('Early Tang', 618, 712),
    ('High Tang', 713, 765),
    ('Middle Tang', 766, 835),
    ('Late Tang', 836, 907)
]

# Text Processing
MAX_SUBTITLE_LENGTH = 50
"""Maximum length for a subtitle to be considered valid"""

CHINESE_PUNCTUATION = '，。、！？；：""''（）【】《》…'
"""Common Chinese punctuation marks"""

# Poem Identification
PART_INDICATOR_PATTERN = r'^其[一二三四五六七八九十]+$'
"""Pattern to match part indicators like 其一, 其二"""

ANNOTATION_PATTERN = r'〈([^〉]+)〉'
"""Pattern to match annotations in 〈〉 brackets"""

FRAGMENT_GROUP_PATTERN = r'以下[《\(](.+?)[》\)]'
"""Pattern to match fragment group markers like 以下《X》"""

PREFACE_TITLE_PATTERN = r'[（(][并並]?序[）)]'
"""Pattern to match preface indicators in titles like （并序）, （並序）, or （序）"""

# Fragment Splitting
MIN_EMPTY_LINES_FOR_SPLIT = 2
"""Minimum number of empty lines to split fragments"""

# UID Generation
UID_PREFIX = "QTS"
"""Prefix for poem unique identifiers"""

UID_VOLUME_DIGITS = 3
"""Number of digits for volume number in UID"""

UID_ENTRY_DIGITS = 3
"""Number of digits for entry index in UID"""

UID_PART_DIGITS = 2
"""Number of digits for part index in UID"""

# Cache Settings
AUTHOR_CACHE_FILENAME = "author_metadata_cache.json"
"""Filename for persistent author metadata cache"""

CACHE_VERSION = 1
"""Cache format version for invalidation"""

# Validation
REQUIRED_POEM_FIELDS = ['uid', 'volume', 'author', 'title', 'poem']
"""Required fields for a valid poem entry"""

# Logging
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
"""Standard log message format"""

# Special Volume Ranges
YUEFU_VOLUMES = range(17, 30)
"""Volumes 17-29 use yuefu format (h2/h4 + p tags)"""

HIERARCHICAL_VOLUMES = range(10, 17)
"""Volumes 10-16 use hierarchical format (h3 + h4 titles)"""

DL_FORMAT_VOLUMES = {10, 11, 12, 13, 14, 15, 16}
"""Volumes that may use definition list (dl/dd) format"""

BARE_P_TAG_VOLUMES = {5}
"""Volumes that may have bare p-tag poems"""
