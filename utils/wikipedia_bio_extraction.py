"""
Wikipedia biography extraction utilities.

Extracts structured information from Chinese Wikipedia biography text:
- Birth/death years
- Courtesy names (字)
- Art names (號)
- Birthplace/origin

These extractions supplement Wikidata metadata for authors who have
Wikipedia articles but limited Wikidata information.
"""

import re
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


def extract_birth_death_years(bio_text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract birth and death years from Wikipedia biography text.

    Handles various formats:
    - （598年—649年）or（598年－649年）
    - （？—962年）(unknown birth)
    - （约820年—约880年）(approximate years)
    - （598年1月28日—649年7月10日）(full dates)

    Args:
        bio_text: Wikipedia biography text

    Returns:
        Tuple of (birth_year, death_year), either may be None

    Examples:
        >>> extract_birth_death_years("李世民（598年—649年），唐朝皇帝")
        (598, 649)
        >>> extract_birth_death_years("李澣（？—962年），文學家")
        (None, 962)
    """
    birth_year = None
    death_year = None

    # Pattern for years in parentheses at start of bio
    # Matches: （598年—649年）, （？—962年）, （约820年—约880年）, etc.
    # Also handles full dates like 598年1月28日
    year_pattern = r'（([約约]?\d+年[^—－）]*)?[？\?]?[—－]([約约]?\d+年[^）]*)?）'

    match = re.search(year_pattern, bio_text[:200])  # Only search near beginning
    if match:
        birth_part = match.group(1)
        death_part = match.group(2)

        # Extract year from birth part
        if birth_part:
            year_match = re.search(r'[約约]?(\d+)年', birth_part)
            if year_match:
                birth_year = int(year_match.group(1))

        # Extract year from death part
        if death_part:
            year_match = re.search(r'[約约]?(\d+)年', death_part)
            if year_match:
                death_year = int(year_match.group(1))

    # Also try alternative format without parentheses
    # e.g., "生于820年" or "卒于880年"
    if birth_year is None:
        birth_match = re.search(r'生[於于]?[約约]?(\d+)年', bio_text[:300])
        if birth_match:
            birth_year = int(birth_match.group(1))

    if death_year is None:
        death_match = re.search(r'[卒殁歿](?:[於于])?[約约]?(\d+)年', bio_text[:300])
        if death_match:
            death_year = int(death_match.group(1))

    if birth_year or death_year:
        logger.debug(f"Extracted years from bio: birth={birth_year}, death={death_year}")

    return birth_year, death_year


def extract_courtesy_names(bio_text: str) -> List[str]:
    """
    Extract courtesy names (字) from Wikipedia biography text.

    Handles various formats:
    - 字日新
    - 字子美
    - 字太白，號青蓮居士 (multiple names)

    Args:
        bio_text: Wikipedia biography text

    Returns:
        List of courtesy names (may be empty)

    Examples:
        >>> extract_courtesy_names("李白，字太白，號青蓮居士")
        ['太白']
        >>> extract_courtesy_names("杜甫，字子美")
        ['子美']
    """
    courtesy_names = []

    # Pattern for 字XX (courtesy name)
    # Usually 2-3 characters after 字
    # Stop at punctuation, 號, or other markers
    zi_pattern = r'字([^，。、；：號\s]{1,4})'

    matches = re.findall(zi_pattern, bio_text[:500])
    for match in matches:
        name = match.strip()
        # Validate it looks like a name (not a sentence fragment)
        if len(name) >= 1 and len(name) <= 4:
            # Skip if it contains numbers or looks like a description
            if not re.search(r'\d', name):
                courtesy_names.append(name)

    if courtesy_names:
        logger.debug(f"Extracted courtesy names from bio: {courtesy_names}")

    return courtesy_names


def extract_art_names(bio_text: str) -> List[str]:
    """
    Extract art names/pseudonyms (號) from Wikipedia biography text.

    Handles various formats:
    - 號青蓮居士
    - 號東坡居士
    - 自號香山居士

    Args:
        bio_text: Wikipedia biography text

    Returns:
        List of art names (may be empty)

    Examples:
        >>> extract_art_names("李白，字太白，號青蓮居士")
        ['青蓮居士']
    """
    art_names = []

    # Pattern for 號XX or 自號XX (art name/pseudonym)
    # Can be longer than courtesy names (up to ~6 chars)
    hao_pattern = r'(?:自)?號([^，。、；：字\s]{1,8})'

    matches = re.findall(hao_pattern, bio_text[:500])
    for match in matches:
        name = match.strip()
        # Validate it looks like a name
        if len(name) >= 2 and len(name) <= 8:
            if not re.search(r'\d', name):
                art_names.append(name)

    if art_names:
        logger.debug(f"Extracted art names from bio: {art_names}")

    return art_names


def extract_birthplace(bio_text: str) -> Optional[str]:
    """
    Extract birthplace/origin from Wikipedia biography text.

    Handles various formats:
    - 京兆萬年人
    - 京兆萬年（今陝西西安）人
    - 河南洛陽人
    - XX縣人 / XX州人 / XX郡人

    Args:
        bio_text: Wikipedia biography text

    Returns:
        Birthplace string or None

    Examples:
        >>> extract_birthplace("李澣，京兆萬年（今陝西西安）人")
        '京兆萬年'
        >>> extract_birthplace("杜甫，河南鞏縣人")
        '河南鞏縣'
    """
    # Pattern for place + 人
    # Captures the place name before 人
    # Handles optional modern equivalent in parentheses
    # Must be preceded by punctuation or start to avoid matching 詩人, 文學家人 etc.
    place_pattern = r'[，。；：」）]([^，。；：（）\s]{2,8}?)(?:（[^）]+）)?人[，。]'

    match = re.search(place_pattern, bio_text[:300])
    if match:
        place = match.group(1).strip()
        # Validate it looks like a place name
        # Should end with typical place suffixes or be 2-5 chars
        place_suffixes = ['縣', '州', '郡', '府', '道', '路', '軍', '城', '鎮', '鄉', '里', '村']
        # Exclude common non-place patterns
        non_place_words = ['詩', '文學', '政治', '軍事', '唐朝', '宋朝', '明朝', '清朝']

        is_valid_place = (
            len(place) >= 2 and len(place) <= 8 and
            not any(word in place for word in non_place_words) and
            (any(place.endswith(suffix) for suffix in place_suffixes) or len(place) <= 5)
        )

        if is_valid_place:
            logger.debug(f"Extracted birthplace from bio: {place}")
            return place

    return None


def extract_alternate_names(bio_text: str) -> List[str]:
    """
    Extract alternate name forms from Wikipedia biography text.

    Handles:
    - 又作XX (also written as)
    - 一名XX (also called)
    - 本名XX (original name)

    Args:
        bio_text: Wikipedia biography text

    Returns:
        List of alternate names (may be empty)

    Examples:
        >>> extract_alternate_names("李澣（？—962年），又作李瀚")
        ['李瀚']
    """
    alt_names = []

    # Pattern for 又作XX, 一名XX, 本名XX
    alt_patterns = [
        r'又作([^，。、；：\s]{2,4})',
        r'一名([^，。、；：\s]{2,4})',
        r'本名([^，。、；：\s]{2,4})',
        r'原名([^，。、；：\s]{2,4})',
    ]

    for pattern in alt_patterns:
        matches = re.findall(pattern, bio_text[:300])
        for match in matches:
            name = match.strip()
            if len(name) >= 2 and len(name) <= 4:
                if not re.search(r'\d', name):
                    alt_names.append(name)

    if alt_names:
        logger.debug(f"Extracted alternate names from bio: {alt_names}")

    return alt_names


def extract_all_from_biography(bio_text: str) -> dict:
    """
    Extract all structured information from a Wikipedia biography.

    Args:
        bio_text: Wikipedia biography text

    Returns:
        Dictionary with extracted fields:
        - birth_year: int or None
        - death_year: int or None
        - courtesy_names: list of strings
        - art_names: list of strings
        - birthplace: string or None
        - alternate_names: list of strings
    """
    birth_year, death_year = extract_birth_death_years(bio_text)

    return {
        'birth_year': birth_year,
        'death_year': death_year,
        'courtesy_names': extract_courtesy_names(bio_text),
        'art_names': extract_art_names(bio_text),
        'birthplace': extract_birthplace(bio_text),
        'alternate_names': extract_alternate_names(bio_text),
    }
