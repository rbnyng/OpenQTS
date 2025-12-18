"""
UID generation utilities for Tang Poems scraper.

Provides functions for generating unique identifiers for poems.
"""


def generate_uid(volume_num: int, entry_index: int, part_index: int = 1) -> str:
    """
    Generate unique identifier for a poem.

    Format: QTS_VVV_EEE_PP
    - QTS: Quan Tang Shi (Complete Tang Poems)
    - VVV: Volume number (3 digits, zero-padded)
    - EEE: Entry index - the Nth title entry in the volume (3 digits, zero-padded)
    - PP: Part index - the Nth poem under that title (2 digits, zero-padded)

    Args:
        volume_num: Volume number (1-900)
        entry_index: Index of the title entry within the volume (1-based)
        part_index: Index of the poem within the entry (1-based, defaults to 1)

    Returns:
        UID string in format QTS_VVV_EEE_PP

    Examples:
        >>> generate_uid(5, 1)
        'QTS_005_001_01'
        >>> generate_uid(18, 4, 2)
        'QTS_018_004_02'
        >>> generate_uid(123, 456, 1)
        'QTS_123_456_01'
    """
    return f"QTS_{volume_num:03d}_{entry_index:03d}_{part_index:02d}"
