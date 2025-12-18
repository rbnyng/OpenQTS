"""
Volume-specific HTML format specifications for Tang Poems scraper.

This module centralizes knowledge about which volumes use which HTML formats,
making it easier to understand and maintain volume-specific extraction logic.
"""

from enum import Enum
from typing import Optional


class VolumeFormat(str, Enum):
    """HTML format types used across different volumes."""

    # Standard format: h2/h3 titles + div.poem content (most common)
    STANDARD = "standard"

    # DL format: Definition list (dl/dd) tags for content
    DL_FORMAT = "dl_format"

    # Yuefu format: h2/h4 titles + p tag content (volumes 17-25)
    YUEFU = "yuefu"

    # Hierarchical format: h3 + h4 nested titles (volumes 10-16)
    HIERARCHICAL = "hierarchical"

    # Bare p-tag format: Content directly in p tags after h3 (唐享昊天樂)
    BARE_P_TAG = "bare_p"

    # Legacy paragraph format: Plain p tags with "卷N_M 《title》author" markers
    LEGACY_PARAGRAPH = "legacy_paragraph"


# Map volume numbers to their primary format
# Volumes not in this dict default to STANDARD format
VOLUME_FORMAT_MAP = {
    # Hierarchical titles (h3 + h4)
    10: VolumeFormat.HIERARCHICAL,
    11: VolumeFormat.HIERARCHICAL,
    12: VolumeFormat.HIERARCHICAL,
    13: VolumeFormat.HIERARCHICAL,
    14: VolumeFormat.HIERARCHICAL,
    15: VolumeFormat.HIERARCHICAL,
    16: VolumeFormat.HIERARCHICAL,

    # Yuefu format (h2/h4 + p tags)
    17: VolumeFormat.YUEFU,
    18: VolumeFormat.YUEFU,
    19: VolumeFormat.YUEFU,
    20: VolumeFormat.YUEFU,
    21: VolumeFormat.YUEFU,
    22: VolumeFormat.YUEFU,
    23: VolumeFormat.YUEFU,
    24: VolumeFormat.YUEFU,
    25: VolumeFormat.YUEFU,

    # Legacy paragraph format (plain p tags with 卷N_M markers)
    # Note: Legacy format volumes are auto-detected via fallback mechanism
    # No need to register individually - the scraper will try legacy format
    # automatically if the primary strategy extracts 0 poems
}


# Volumes known to use DL format (in addition to or instead of div.poem)
DL_FORMAT_VOLUMES = {10, 11, 12, 13, 14, 15, 16}


# Volumes that may have bare p-tag poems (not exhaustive, detected at runtime)
BARE_P_TAG_VOLUMES = {5}  # Volume 5 has 唐享昊天樂十二首 with bare p tags


def get_volume_format(volume_num: int) -> VolumeFormat:
    """
    Get the primary HTML format for a volume.

    Args:
        volume_num: Volume number (1-900)

    Returns:
        VolumeFormat enum value

    Note:
        Some volumes may use multiple formats. This returns the primary format.
        The scraper should check for multiple formats at runtime.
    """
    return VOLUME_FORMAT_MAP.get(volume_num, VolumeFormat.STANDARD)


def uses_hierarchical_titles(volume_num: int) -> bool:
    """
    Check if volume uses hierarchical h3+h4 title structure.

    Args:
        volume_num: Volume number

    Returns:
        True if volume uses h3 + h4 hierarchical structure
    """
    return get_volume_format(volume_num) == VolumeFormat.HIERARCHICAL


def uses_yuefu_format(volume_num: int) -> bool:
    """
    Check if volume uses yuefu format (h2/h4 + p tags).

    Args:
        volume_num: Volume number

    Returns:
        True if volume uses yuefu format
    """
    return get_volume_format(volume_num) == VolumeFormat.YUEFU


def may_use_dl_format(volume_num: int) -> bool:
    """
    Check if volume may use DL (definition list) format.

    Args:
        volume_num: Volume number

    Returns:
        True if volume is known to use dl format
    """
    return volume_num in DL_FORMAT_VOLUMES


def may_have_bare_p_tags(volume_num: int) -> bool:
    """
    Check if volume may have bare p-tag poems.

    Args:
        volume_num: Volume number

    Returns:
        True if volume is known to have bare p-tag poems
    """
    return volume_num in BARE_P_TAG_VOLUMES


def get_volume_description(volume_num: int) -> str:
    """
    Get a human-readable description of the volume's format.

    Args:
        volume_num: Volume number

    Returns:
        Description string

    Examples:
        >>> get_volume_description(5)
        'Standard format (may have bare p-tag poems)'
        >>> get_volume_description(16)
        'Hierarchical format (h3 + h4 titles)'
        >>> get_volume_description(19)
        'Yuefu format (h2/h4 + p tags)'
    """
    format_type = get_volume_format(volume_num)

    descriptions = {
        VolumeFormat.STANDARD: "Standard format (div.poem)",
        VolumeFormat.DL_FORMAT: "DL format (definition lists)",
        VolumeFormat.YUEFU: "Yuefu format (h2/h4 + p tags)",
        VolumeFormat.HIERARCHICAL: "Hierarchical format (h3 + h4 titles)",
        VolumeFormat.BARE_P_TAG: "Bare p-tag format",
    }

    desc = descriptions.get(format_type, "Unknown format")

    # Add additional format notes
    notes = []
    if may_use_dl_format(volume_num) and format_type != VolumeFormat.DL_FORMAT:
        notes.append("may use dl format")
    if may_have_bare_p_tags(volume_num) and format_type != VolumeFormat.BARE_P_TAG:
        notes.append("may have bare p-tag poems")

    if notes:
        desc += f" ({', '.join(notes)})"

    return desc
