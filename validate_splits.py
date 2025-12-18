#!/usr/bin/env python3
"""
Interactive validation script to detect poems that need manual attention.

This script scans processed output and detects:
1. Unsplit multi-part poems (title has 二首, 三首, etc. but not split)
2. Biography/misattributed entries (title is another author's name)
3. Collaborative poems (聯句) with attribution markers
4. Suspicious content (very short, metadata-like)
5. Abbreviated titles (containing ellipsis … or truncation markers)

Usage:
    python validate_splits.py --start 1 --end 900
    python validate_splits.py --volume 748
    python validate_splits.py --issue-type abbreviated
"""

import json
import logging
import argparse
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from models import Poem
from constants import DEFAULT_PROCESSED_OUTPUT_DIR, LOG_FORMAT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a validation issue found in the data."""
    issue_type: str  # 'unsplit', 'biography', 'suspicious', 'short'
    volume: int
    uid: str
    title: str
    author: str
    severity: str  # 'high', 'medium', 'low'
    description: str
    poem_data: Dict  # Full poem data for context
    suggested_action: Optional[str] = None


class PoemValidator:
    """Validates processed poems and detects issues requiring manual attention."""

    # Chinese number patterns for multi-part detection
    MULTI_PART_PATTERN = re.compile(r'([二三四五六七八九十百]+)首')
    CHINESE_NUMBERS = {
        '二': 2, '三': 3, '四': 4, '五': 5, '六': 6,
        '七': 7, '八': 8, '九': 9, '十': 10,
        '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
        '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20
    }

    # Known valid titles that look like person names but are actually poem titles
    # These should NOT be flagged as biography entries
    VALID_TITLE_EXCEPTIONS = {
        # place names and historical locations
        '石淙', '石橋', '高昌', '黃頰山',

        # Historical/mythological figures (valid poem subjects)
        '王昭君', '朱鷺', '王子喬', '牛女',

        # Yuefu (樂府) titles and song names
        '楊柳枝', '金縷衣', '蘇摩遮', '江南曲', '江南弄', '黃雀行',
        '高山引', '龍池篇', '公子行',

        # Nature/object titles
        '石竹詠', '江濱梅', '黃鶴', '林亭詠', '江樓', '江上',

        # Generic object/element names that are valid titles
        '石', '田', '江', '史', '金', '錢', '羅', '李',
        '龍', '馬', '牛', '熊', '劉生',
    }

    def __init__(self, output_dir: str = None):
        """
        Initialize the validator.

        Args:
            output_dir: Directory containing processed JSON files
        """
        self.output_dir = Path(output_dir or DEFAULT_PROCESSED_OUTPUT_DIR)
        self.issues: List[ValidationIssue] = []
        self.stats = {
            'volumes_scanned': 0,
            'poems_scanned': 0,
            'issues_found': 0,
            'by_type': {}
        }

    def validate_volume(self, volume_num: int) -> List[ValidationIssue]:
        """
        Validate a single volume and return list of issues.

        Args:
            volume_num: Volume number to validate

        Returns:
            List of ValidationIssue objects
        """
        volume_file = self.output_dir / f"volume_{volume_num:03d}.json"

        if not volume_file.exists():
            logger.warning(f"Volume file not found: {volume_file}")
            return []

        logger.info(f"Validating volume {volume_num}...")

        with open(volume_file, 'r', encoding='utf-8') as f:
            poems_data = json.load(f)

        poems = [Poem.from_dict(data) for data in poems_data]
        volume_issues = []

        self.stats['volumes_scanned'] += 1
        self.stats['poems_scanned'] += len(poems)

        for poem in poems:
            unsplit_issue = self._check_unsplit_multipart(poem)
            if unsplit_issue:
                volume_issues.append(unsplit_issue)

            bio_issue = self._check_biography_entry(poem)
            if bio_issue:
                volume_issues.append(bio_issue)

            lianqu_issue = self._check_collaborative_poem(poem)
            if lianqu_issue:
                volume_issues.append(lianqu_issue)

            suspicious_issue = self._check_suspicious_content(poem)
            if suspicious_issue:
                volume_issues.append(suspicious_issue)

            abbreviated_issue = self._check_abbreviated_title(poem)
            if abbreviated_issue:
                volume_issues.append(abbreviated_issue)

            quality_issue = self._check_content_quality(poem)
            if quality_issue:
                volume_issues.append(quality_issue)

        self.stats['issues_found'] += len(volume_issues)
        self.issues.extend(volume_issues)

        logger.info(f"Volume {volume_num}: Found {len(volume_issues)} issues")
        return volume_issues

    def _check_unsplit_multipart(self, poem: Poem) -> Optional[ValidationIssue]:
        """Check if poem title indicates multiple parts but isn't split."""
        match = self.MULTI_PART_PATTERN.search(poem.title)

        if match:
            chinese_num = match.group(1)
            expected_parts = self.CHINESE_NUMBERS.get(chinese_num)

            # Check if it's actually split
            is_split = poem.total_parts and poem.total_parts > 1
            actual_total_parts = poem.total_parts or 1

            if expected_parts:
                # Flag as UNSPLIT if:
                # 1. Not split at all (total_parts <= 1), OR
                # 2. Split but total_parts doesn't mtach expected number
                if not is_split:
                    return ValidationIssue(
                        issue_type='unsplit',
                        volume=poem.volume,
                        uid=poem.uid,
                        title=poem.title,
                        author=poem.author.recorded,
                        severity='high',
                        description=f"Title indicates {expected_parts} parts ('{chinese_num}首') but not split (total_parts={actual_total_parts})",
                        poem_data=poem.to_dict(),
                        suggested_action=f"Add split rule for volume {poem.volume} with {expected_parts} parts"
                    )
                elif actual_total_parts != expected_parts:
                    return ValidationIssue(
                        issue_type='unsplit',
                        volume=poem.volume,
                        uid=poem.uid,
                        title=poem.title,
                        author=poem.author.recorded,
                        severity='medium',
                        description=f"Title indicates {expected_parts} parts ('{chinese_num}首') but total_parts={actual_total_parts}",
                        poem_data=poem.to_dict(),
                        suggested_action=f"Verify split rule: expected {expected_parts} parts, found {actual_total_parts}"
                    )

        return None

    def _check_biography_entry(self, poem: Poem) -> Optional[ValidationIssue]:
        """Check if title looks like a biography or misattribution."""
        title = poem.title
        author = poem.author.recorded

        if title in self.VALID_TITLE_EXCEPTIONS:
            return None

        # Check  if title is suspiciously short (might be author name)
        if len(title) <= 3 and title != author:
            # Check if it looks like a person's name
            # Common indicators: 僧, 尚, 子, 公, etc.
            name_indicators = ['僧', '尚', '子', '公', '王', '李', '張', '劉', '陳', '楊', '趙', '黃', '周', '吳', '徐', '孫', '馬', '朱', '胡', '郭', '林', '何', '高', '梁', '鄭', '羅', '宋', '謝', '唐', '韓', '曹', '許', '鄧', '蕭', '馮', '曾', '程', '蔡', '彭', '潘', '袁', '于', '董', '余', '蘇', '葉', '呂', '魏', '蔣', '田', '杜', '丁', '沈', '姜', '范', '江', '傅', '鍾', '盧', '汪', '戴', '崔', '任', '陸', '廖', '姚', '方', '金', '邱', '夏', '譚', '韋', '賈', '鄒', '石', '熊', '孟', '秦', '閻', '薛', '侯', '雷', '白', '龍', '段', '郝', '孔', '邵', '史', '毛', '常', '萬', '顧', '賴', '武', '康', '賀', '嚴', '尹', '錢', '施', '牛', '洪', '龔']

            if any(title.startswith(indicator) for indicator in name_indicators):
                return ValidationIssue(
                    issue_type='biography',
                    volume=poem.volume,
                    uid=poem.uid,
                    title=title,
                    author=author,
                    severity='medium',
                    description=f"Title '{title}' looks like a person's name (possible misattribution or biography)",
                    poem_data=poem.to_dict(),
                    suggested_action="Review if this is a biography entry or misattributed poem"
                )

        return None

    def _check_collaborative_poem(self, poem: Poem) -> Optional[ValidationIssue]:
        """Check for collaborative poems (聯句) that need special handling."""
        attribution_pattern = re.compile(r'——(\w+)')
        has_attribution = any(attribution_pattern.search(line) for line in poem.poem)

        if has_attribution:
            attributions = set()
            for line in poem.poem:
                match = attribution_pattern.search(line)
                if match:
                    attributions.add(match.group(1))

            is_lianqu = '聯句' in poem.title

            # If it has attributions but title doesn't say 聯句, flag it
            if not is_lianqu:
                return ValidationIssue(
                    issue_type='collaborative',
                    volume=poem.volume,
                    uid=poem.uid,
                    title=poem.title,
                    author=poem.author.recorded,
                    severity='high',
                    description=f"Contains {len(attributions)} author attributions (——) but title doesn't indicate 聯句",
                    poem_data=poem.to_dict(),
                    suggested_action="Add 聯句 cleaning rule or verify if attributions should be preserved"
                )
            else:
                # Even if title says 聯句, flag it for cleaning
                return ValidationIssue(
                    issue_type='collaborative',
                    volume=poem.volume,
                    uid=poem.uid,
                    title=poem.title,
                    author=poem.author.recorded,
                    severity='medium',
                    description=f"Collaborative poem (聯句) with {len(attributions)} authors - may need attribution cleaning",
                    poem_data=poem.to_dict(),
                    suggested_action="Consider cleaning attribution markers (——) in post-processing"
                )

        return None

    def _check_suspicious_content(self, poem: Poem) -> Optional[ValidationIssue]:
        """Check for suspicious content that might not be a poem."""
        # very short poems (1 line)
        if len(poem.poem) == 1:
            first_line = poem.poem[0]

            # Check if it looks like metadata or navigation
            metadata_indicators = ['聯句', '○', '□', '缺', '無', '佚']

            if any(indicator in first_line for indicator in metadata_indicators):
                return ValidationIssue(
                    issue_type='suspicious',
                    volume=poem.volume,
                    uid=poem.uid,
                    title=poem.title,
                    author=poem.author.recorded,
                    severity='low',
                    description=f"Single-line poem with metadata-like content: '{first_line[:30]}...'",
                    poem_data=poem.to_dict(),
                    suggested_action="Review if this is actual poem content or metadata"
                )

        return None

    def _check_abbreviated_title(self, poem: Poem) -> Optional[ValidationIssue]:
        """Check if title contains ellipsis or truncation markers indicating abbreviated text."""
        title = poem.title

        # common ellipsis and truncation markers in Chinese and Western text
        truncation_markers = [
            '…',      # Horizontal ellipsis (U+2026)
            '...',    # Three dots
            '⋯',      # Midline horizontal ellipsis (U+22EF)
            '……',     # Two horizontal ellipses
            '［略］',  # [Omitted]
            '(略)',   # (Omitted)
            '（略）', # (Omitted) full-width
            '〔略〕', # [Omitted] variant brackets
        ]

        # Check if title contains any truncation markers
        has_truncation = any(marker in title for marker in truncation_markers)

        if has_truncation:
            return ValidationIssue(
                issue_type='abbreviated',
                volume=poem.volume,
                uid=poem.uid,
                title=title,
                author=poem.author.recorded,
                severity='high',
                description=f"Title contains truncation marker, indicating abbreviated/incomplete text: '{title}'",
                poem_data=poem.to_dict(),
                suggested_action="Check source data for complete title or mark as abbreviated in metadata"
            )

        return None

    def _check_content_quality(self, poem: Poem) -> Optional[ValidationIssue]:
        """
        Check for content quality issues in titles and poem text.

        Checks for:
        - English/Latin characters (a-z, A-Z) in titles or poems
        - Uncaught parentheses/brackets in titles (should have been extracted as notes)
        - Arabic digits in titles (unexpected)
        """
        issues_found = []

        title = poem.title

        if re.search(r'[a-zA-Z]', title):
            issues_found.append(f"Title contains English/Latin characters: '{title}'")

        if re.search(r'[（(〈<）)〉>]', title):
            issues_found.append(f"Title contains uncaught brackets/parentheses: '{title}'")

        if re.search(r'\d', title):
            issues_found.append(f"Title contains Arabic digits: '{title}'")

        # Check poem content for English/Latin characters
        for line_num, line in enumerate(poem.poem, 1):
            if re.search(r'[a-zA-Z]', line):
                issues_found.append(f"Poem line {line_num} contains English/Latin characters: '{line[:50]}...'")
                break  # Only report first occurrence to avoid spam

        if issues_found:
            return ValidationIssue(
                issue_type='content_quality',
                volume=poem.volume,
                uid=poem.uid,
                title=title,
                author=poem.author.recorded,
                severity='medium',
                description='; '.join(issues_found),
                poem_data=poem.to_dict(),
                suggested_action="Check source data for OCR errors, corrupted text, or encoding issues"
            )

        return None

    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate a report of all issues found.

        Args:
            output_file: Optional file to write report to

        Returns:
            Report as string
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("VALIDATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Volumes scanned: {self.stats['volumes_scanned']}")
        report_lines.append(f"Poems scanned: {self.stats['poems_scanned']}")
        report_lines.append(f"Issues found: {self.stats['issues_found']}")
        report_lines.append("")

        # Group by issue type
        by_type = {}
        for issue in self.issues:
            by_type.setdefault(issue.issue_type, []).append(issue)

        for issue_type, issues in sorted(by_type.items()):
            report_lines.append(f"\n{issue_type.upper()} ({len(issues)} issues)")
            report_lines.append("-" * 80)

            # Group by volume
            by_volume = {}
            for issue in issues:
                by_volume.setdefault(issue.volume, []).append(issue)

            for volume, vol_issues in sorted(by_volume.items()):
                report_lines.append(f"\n  Volume {volume}: {len(vol_issues)} issues")
                for issue in vol_issues:
                    report_lines.append(f"    - {issue.uid}: {issue.title} (by {issue.author})")
                    report_lines.append(f"      {issue.description}")
                    if issue.suggested_action:
                        report_lines.append(f"      → {issue.suggested_action}")

        report = "\n".join(report_lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report written to {output_file}")

        return report



def main():
    parser = argparse.ArgumentParser(
        description='Validate processed poems and detect issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # validate all volumes
  python validate_splits.py --start 1 --end 900

  # Validate specific volume
  python validate_splits.py --volume 748

  # Only check for unsplit poems
  python validate_splits.py --unsplit

  # Check for multiple categories
  python validate_splits.py --unsplit --biography
        """
    )

    parser.add_argument('--start', type=int, default=1,
                       help='Starting volume (1-900)')
    parser.add_argument('--end', type=int, default=900,
                       help='Ending volume (1-900)')
    parser.add_argument('--volume', type=int,
                       help='Validate single volume')
    parser.add_argument('--output-dir', default=str(DEFAULT_PROCESSED_OUTPUT_DIR),
                       help='Directory with processed JSON files')
    parser.add_argument('--report', type=Path,
                       help='Write report to file')
    parser.add_argument('--unsplit', action='store_true',
                       help='Check for unsplit multi-part poems')
    parser.add_argument('--biography', action='store_true',
                       help='Check for biography/misattributed entries')
    parser.add_argument('--collaborative', action='store_true',
                       help='Check for collaborative poems (聯句)')
    parser.add_argument('--suspicious', action='store_true',
                       help='Check for suspicious content')
    parser.add_argument('--abbreviated', action='store_true',
                       help='Check for abbreviated titles')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose (DEBUG) logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    validator = PoemValidator(output_dir=args.output_dir)

    # Validate volumes
    if args.volume:
        validator.validate_volume(args.volume)
    else:
        for volume_num in range(args.start, args.end + 1):
            validator.validate_volume(volume_num)

    # Filter by issue categories if specified
    enabled_categories = []
    if args.unsplit:
        enabled_categories.append('unsplit')
    if args.biography:
        enabled_categories.append('biography')
    if args.collaborative:
        enabled_categories.append('collaborative')
    if args.suspicious:
        enabled_categories.append('suspicious')
    if args.abbreviated:
        enabled_categories.append('abbreviated')

    if enabled_categories:
        validator.issues = [i for i in validator.issues if i.issue_type in enabled_categories]

    # generate report
    report = validator.generate_report(args.report)
    print(report)

    logger.info("Validation complete!")


if __name__ == '__main__':
    main()
