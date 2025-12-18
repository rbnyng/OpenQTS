"""
Education extraction utilities for Tang Poems authors.

Extracts academic degrees and educational achievements from Chinese biography text
and normalizes them to match Wikidata format (romanized/English).
"""

import re
from typing import Optional, Tuple

# Conversion table: Chinese term -> Normalized English/romanized form
# Matches the format used by Wikidata (e.g., "jinshi" not "進士")
EDUCATION_CONVERSION = {
    # Jinshi (進士) - Most prestigious degree
    '進士第一': 'jinshi',  # Top jinshi (still jinshi degree)
    '擢進士第一': 'jinshi',
    '進士及第': 'jinshi',
    '擢進士第': 'jinshi',
    '進士': 'jinshi',

    # Other civil service degrees
    '宏詞': 'hongci',  # Hongci examination (literary composition)
    '宏詞及第': 'hongci',
    '博學宏詞': 'hongci',
    '明經': 'mingjing',  # Ming jing (Classics examination)
    '秀才': 'xiucai',  # Xiucai
    '舉人': 'juren',  # Juren
    '生員': 'shengyuan',  # Shengyuan

    # General examination passing (treat as jinshi if no other info)
    '登第': 'examination',  # Generic "passed examination"
    '及第': 'examination',
}

# Regex patterns to match educational achievements in biography text
# Order matters: more specific patterns first
EDUCATION_PATTERNS = [
    (r'擢進士第一', 'jinshi'),
    (r'進士第一', 'jinshi'),
    (r'擢進士第', 'jinshi'),
    (r'進士及第', 'jinshi'),
    (r'博學宏詞(?:科)?及第', 'hongci'),
    (r'宏詞(?:科)?及第', 'hongci'),
    (r'宏詞', 'hongci'),
    (r'明經(?:科)?及第', 'mingjing'),
    (r'明經', 'mingjing'),
    (r'進士', 'jinshi'),  # General jinshi (after more specific patterns)
    (r'秀才', 'xiucai'),
    (r'舉人', 'juren'),
    (r'生員', 'shengyuan'),
    # Generic examination passing - lower priority
    (r'登第', 'examination'),
    (r'及第', 'examination'),
]


def extract_education_from_biography(biography_text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract academic degree from biography text.

    Searches for educational achievement markers in Chinese biography text
    and converts them to normalized English/romanized form that matches Wikidata.

    Args:
        biography_text: Biography text to analyze

    Returns:
        Tuple of (degree, source) where:
        - degree: Normalized degree name (e.g., "jinshi", "hongci")
        - source: Description showing the matched Chinese term

    Examples:
        "貞元間人，擢進士第一" -> ("jinshi", "inferred_education:擢進士第一")
        "貞元十二年宏詞及第" -> ("hongci", "inferred_education:宏詞及第")
        "梁州進士" -> ("jinshi", "inferred_education:進士")
    """
    if not biography_text:
        return None, None

    for pattern, degree in EDUCATION_PATTERNS:
        match = re.search(pattern, biography_text)
        if match:
            matched_text = match.group(0)
            return degree, f"inferred_education:{matched_text}"

    return None, None


def normalize_education_term(chinese_term: str) -> Optional[str]:
    """
    Normalize a Chinese education term to English/romanized form.

    Args:
        chinese_term: Chinese education term (e.g., "進士", "宏詞及第")

    Returns:
        Normalized English/romanized form (e.g., "jinshi", "hongci")
        or None if term not recognized
    """
    return EDUCATION_CONVERSION.get(chinese_term)
