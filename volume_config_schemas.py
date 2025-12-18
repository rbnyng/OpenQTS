"""
Schema definitions for volume configuration.

This module defines the data structures used for configuring poem splits,
merges, and named part sets across different volumes of the Complete Tang Poems.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from enum import Enum


class SplitStrategy(Enum):
    """Strategy for splitting multi-part poems."""
    INDEX = "index"      # Split by line index ranges
    MARKER = "marker"    # Split by finding marker lines
    FUNCTION = "function"  # Use custom function


@dataclass
class MultisongSplitConfig:
    """Configuration for splitting multi-song poems.

    Attributes:
        title_pattern: Pattern to match in poem title
        line_count: Expected total line count (for validation)
        num_songs: Number of songs to split into
        splits: List of (start, end) tuples for line ranges
        author: Optional author filter (only split if author matches)
    """
    title_pattern: str
    line_count: int
    num_songs: int
    splits: List[Tuple[int, int]]
    author: Optional[str] = None

    def matches(self, title: str, author: str, poem_lines: List[str]) -> bool:
        if self.title_pattern not in title:
            return False
        if len(poem_lines) != self.line_count:
            return False
        if self.author is not None and author != self.author:
            return False
        return True

    def apply(self, poem_lines: List[str]) -> List[List[str]]:
        """Apply the split and return list of poem parts."""
        return [poem_lines[start:end] for start, end in self.splits]


@dataclass
class CustomSplitConfig:
    """Configuration for custom poem splits.

    Supports three split strategies:
    - INDEX: Use 'splits' list of (start, end) tuples
    - MARKER: Use 'markers' list of line prefixes to find split points
    - FUNCTION: Use 'use_function' name to call custom function

    Attributes:
        base_title: Base title for the split parts
        strategy: The split strategy to use
        splits: Line index ranges for INDEX strategy
        markers: Line prefix markers for MARKER strategy
        use_function: Function name for FUNCTION strategy
    """
    base_title: str
    strategy: SplitStrategy = SplitStrategy.INDEX
    splits: Optional[List[Tuple[int, int]]] = None
    markers: Optional[List[str]] = None
    use_function: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_title: str) -> 'CustomSplitConfig':
        """Create config from legacy dict format."""
        if 'markers' in data:
            return cls(
                base_title=data.get('base_title', base_title),
                strategy=SplitStrategy.MARKER,
                markers=data['markers']
            )
        elif 'use_function' in data:
            return cls(
                base_title=data.get('base_title', base_title),
                strategy=SplitStrategy.FUNCTION,
                use_function=data['use_function']
            )
        elif 'splits' in data:
            return cls(
                base_title=data.get('base_title', base_title),
                strategy=SplitStrategy.INDEX,
                splits=data['splits']
            )
        else:
            # Default to base_title only (marker-based with no explicit markers)
            return cls(
                base_title=data.get('base_title', base_title),
                strategy=SplitStrategy.MARKER,
                markers=data.get('markers', [])
            )


@dataclass
class NamedPartSetConfig:
    """Configuration for named part sets (poems that share entry_index).

    Attributes:
        base_title: The shared base title for all parts
        author: The author of the poem set
        expected_count: Number of parts expected in the set
        part_patterns: Patterns to identify each part (e.g., ['春歌', '夏歌', '秋歌', '冬歌'])
    """
    base_title: str
    author: str
    expected_count: int
    part_patterns: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NamedPartSetConfig':
        """Create config from legacy dict format."""
        # Handle both 'part_patterns' and 'season_patterns' field names
        patterns = data.get('part_patterns') or data.get('season_patterns', [])
        return cls(
            base_title=data['base_title'],
            author=data['author'],
            expected_count=data['expected_count'],
            part_patterns=patterns
        )


@dataclass
class MergeConfig:
    """Configuration for merging poems as notes or prefaces.

    Attributes:
        title: Title pattern to match
        marker: Content marker to identify the poem
        target: Where to merge ('next' or 'previous')
        merge_type: Type of merge ('note' or 'preface')
    """
    title: str
    marker: str
    target: str = 'next'
    merge_type: str = 'note'

    @classmethod
    def from_dict(cls, data: Dict[str, Any], merge_type: str = 'note') -> 'MergeConfig':
        """Create config from legacy dict format."""
        return cls(
            title=data['title'],
            marker=data['marker'],
            target=data.get('target', 'next'),
            merge_type=merge_type
        )


@dataclass
class VolumeConfig:
    """Complete configuration for a single volume.

    Consolidates all special case handling for a volume into one place.

    Attributes:
        volume_num: The volume number
        custom_splits: Dict mapping (title, author) to CustomSplitConfig
        multisong_splits: List of MultisongSplitConfig for this volume
        named_part_sets: List of NamedPartSetConfig for this volume
        merge_as_notes: List of MergeConfig for note merges
        merge_as_preface: List of MergeConfig for preface merges
        multipart_titles: Dict mapping title to expected part count
        biography_entries: List of author names to remove as biography entries
        stub_entries: List of (title, author) tuples to remove as stubs
        title_rewrites: Dict mapping old title to new title
        force_preface_parts: List of (title, author) tuples to force preface merge
    """
    volume_num: int
    custom_splits: Dict[Tuple[str, str], CustomSplitConfig] = field(default_factory=dict)
    multisong_splits: List[MultisongSplitConfig] = field(default_factory=list)
    named_part_sets: List[NamedPartSetConfig] = field(default_factory=list)
    merge_as_notes: List[MergeConfig] = field(default_factory=list)
    merge_as_preface: List[MergeConfig] = field(default_factory=list)
    multipart_titles: Dict[str, int] = field(default_factory=dict)
    biography_entries: List[str] = field(default_factory=list)
    stub_entries: List[Tuple[str, str]] = field(default_factory=list)
    title_rewrites: Dict[str, str] = field(default_factory=dict)
    force_preface_parts: List[Tuple[str, str]] = field(default_factory=list)

    # Optional custom split function for complex cases
    split_function: Optional[Callable] = None
    named_part_sets_function: Optional[Callable] = None


def validate_config(config: VolumeConfig) -> List[str]:
    """Validate a volume configuration and return list of errors."""
    errors = []

    # Validate custom splits
    for key, split_config in config.custom_splits.items():
        if split_config.strategy == SplitStrategy.INDEX and not split_config.splits:
            errors.append(f"Volume {config.volume_num}: Custom split {key} uses INDEX strategy but has no splits")
        if split_config.strategy == SplitStrategy.MARKER and not split_config.markers:
            errors.append(f"Volume {config.volume_num}: Custom split {key} uses MARKER strategy but has no markers")
        if split_config.strategy == SplitStrategy.FUNCTION and not split_config.use_function:
            errors.append(f"Volume {config.volume_num}: Custom split {key} uses FUNCTION strategy but has no function name")

    # Validate multisong splits
    for i, ms_config in enumerate(config.multisong_splits):
        if not ms_config.title_pattern:
            errors.append(f"Volume {config.volume_num}: Multisong split {i} has no title_pattern")
        if ms_config.num_songs != len(ms_config.splits):
            errors.append(f"Volume {config.volume_num}: Multisong split {i} num_songs ({ms_config.num_songs}) != len(splits) ({len(ms_config.splits)})")

    # Validate named part sets
    for i, nps_config in enumerate(config.named_part_sets):
        if nps_config.expected_count != len(nps_config.part_patterns):
            errors.append(f"Volume {config.volume_num}: Named part set {i} expected_count ({nps_config.expected_count}) != len(part_patterns) ({len(nps_config.part_patterns)})")

    return errors
