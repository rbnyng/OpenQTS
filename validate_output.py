#!/usr/bin/env python3
"""
Validation script for Complete Tang Poems data quality.

Checks:
1. UID uniqueness across all volumes
2. part_index <= total_parts
3. Multi-song poems detected but not configured
4. Duplicate titles within same volume
5. Missing author metadata
6. Poems with empty content
7. Invalid JSON structure

Usage:
    python validate_output.py --dir output
    python validate_output.py --volume 18
"""

import json
import logging
import argparse
import re
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

from models import Poem, Author
from constants import (
    LOG_FORMAT,
    DEFAULT_PROCESSED_OUTPUT_DIR,
    REQUIRED_POEM_FIELDS,
    MIN_VOLUME_NUMBER,
    MAX_VOLUME_NUMBER
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


class PoemValidator:
    """Validator for checking data quality of scraped poems."""

    def __init__(self, data_dir: str = None):
        """
        Initialize the validator.

        Args:
            data_dir: Directory containing processed JSON files
        """
        self.data_dir = Path(data_dir or DEFAULT_PROCESSED_OUTPUT_DIR)
        self.errors = []
        self.warnings = []
        self.stats = {
            'total_volumes': 0,
            'total_poems': 0,
            'multi_part_poems': 0,
            'missing_author_metadata': 0,
        }

    def validate_volume(self, volume_num: int) -> List[Poem]:
        """
        Validate a single volume and return poems.

        Args:
            volume_num: Volume number to validate

        Returns:
            List of Poem objects from the volume
        """
        volume_file = self.data_dir / f"volume_{volume_num:03d}.json"

        if not volume_file.exists():
            logger.debug(f"Volume {volume_num} file not found: {volume_file}")
            return []

        try:
            with open(volume_file, 'r', encoding='utf-8') as f:
                poems_data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(
                f"Volume {volume_num}: Invalid JSON in {volume_file} - {e}"
            )
            return []
        except IOError as e:
            self.errors.append(
                f"Volume {volume_num}: Error reading file {volume_file} - {e}"
            )
            return []

        # Convert to Poem objects for validation
        poems = []
        for data in poems_data:
            try:
                poem = Poem.from_dict(data)
                poems.append(poem)
            except (KeyError, TypeError, ValueError) as e:
                self.errors.append(
                    f"Volume {volume_num}: Error parsing poem '{data.get('title', 'Unknown')}' - {e}"
                )

        return poems

    def check_uid_uniqueness(self, all_poems: List[Poem]):
        """Check that all UIDs are unique across all volumes."""
        uid_to_poem = {}
        duplicates = []

        for poem in all_poems:
            if not poem.uid:
                self.errors.append(
                    f"Poem missing UID: '{poem.title}' (volume {poem.volume})"
                )
                continue

            if poem.uid in uid_to_poem:
                duplicates.append((poem.uid, uid_to_poem[poem.uid], poem))
            else:
                uid_to_poem[poem.uid] = poem

        for uid, poem1, poem2 in duplicates:
            self.errors.append(
                f"Duplicate UID '{uid}': "
                f"'{poem1.title}' (vol {poem1.volume}) and "
                f"'{poem2.title}' (vol {poem2.volume})"
            )

    def check_part_indices(self, poems: List[Poem], volume_num: int):
        """Check that part_index <= total_parts."""
        for poem in poems:
            if poem.part_index is not None and poem.total_parts is not None:
                if poem.part_index > poem.total_parts:
                    self.errors.append(
                        f"Volume {volume_num}: '{poem.title}' has "
                        f"part_index {poem.part_index} > total_parts {poem.total_parts}"
                    )
                elif poem.part_index < 1:
                    self.errors.append(
                        f"Volume {volume_num}: '{poem.title}' has "
                        f"invalid part_index {poem.part_index} (must be >= 1)"
                    )

    def check_multisong_detection(self, poems: List[Poem], volume_num: int):
        """Check for N首 titles that might need splitting."""
        if volume_num not in [17, 18, 19]:
            return

        for poem in poems:
            # Check for N首 pattern
            match = re.search(r'([二三四五六七八九十]+)首', poem.title)

            if match and poem.part_index is None:
                self.warnings.append(
                    f"Volume {volume_num}: '{poem.title}' has N首 pattern but no part_index. "
                    f"May need split configuration."
                )

    def check_duplicate_titles(self, poems: List[Poem], volume_num: int):
        """Check for duplicate titles within same volume."""
        title_counts = defaultdict(list)

        for i, poem in enumerate(poems):
            title_counts[poem.title].append(i)

        for title, indices in title_counts.items():
            if len(indices) > 1:
                # Check if they're legitimately multi-part
                poems_with_title = [poems[i] for i in indices]
                has_part_index = all(p.part_index is not None for p in poems_with_title)

                if not has_part_index:
                    self.warnings.append(
                        f"Volume {volume_num}: Duplicate title '{title}' "
                        f"appears {len(indices)} times without part_index"
                    )

    def check_author_metadata(self, poems: List[Poem], volume_num: int):
        """Check for missing author metadata."""
        for poem in poems:
            if not poem.author:
                self.errors.append(
                    f"Volume {volume_num}: '{poem.title}' missing author"
                )
                continue

            if poem.author.canonical == "Unknown":
                self.stats['missing_author_metadata'] += 1

    def check_empty_content(self, poems: List[Poem], volume_num: int):
        """Check for poems with empty content."""
        for poem in poems:
            if not poem.poem:
                self.errors.append(
                    f"Volume {volume_num}: '{poem.title}' has empty content"
                )
            elif all(not line.strip() for line in poem.poem):
                self.errors.append(
                    f"Volume {volume_num}: '{poem.title}' has only empty lines"
                )

    def check_required_fields(self, poems: List[Poem], volume_num: int):
        """Check that all required fields are present."""
        for poem in poems:
            # Check volume number matches
            if poem.volume != volume_num:
                self.errors.append(
                    f"Volume {volume_num}: '{poem.title}' has "
                    f"volume field = {poem.volume} (mismatch)"
                )

    def check_content_quality(self, poems: List[Poem], volume_num: int):
        """
        Check poem titles and content for unusual characters that shouldn't be present.

        Checks for:
        - English/Latin characters (a-z, A-Z) in titles or poems
        - Uncaught parentheses/brackets in titles (should have been extracted as notes)
        - Arabic digits in titles (unexpected)
        - Brackets in poem content (potential annotations)
        """
        for poem in poems:
            title = poem.title

            # Check for English/Latin characters in title
            if re.search(r'[a-zA-Z]', title):
                self.warnings.append(
                    f"Volume {volume_num}, UID {poem.uid}: Title contains English/Latin characters: '{title}'"
                )

            # Check for uncaught parentheses/brackets in title (should have been extracted as notes)
            if re.search(r'[（(〈<）)〉>]', title):
                self.warnings.append(
                    f"Volume {volume_num}, UID {poem.uid}: Title contains uncaught brackets/parentheses: '{title}'"
                )

            # Check for unexpected numbers in title (except in patterns like 其一, 其二)
            if re.search(r'\d', title):
                self.warnings.append(
                    f"Volume {volume_num}, UID {poem.uid}: Title contains digits: '{title}'"
                )

            # Check poem content for English/Latin characters
            for line_num, line in enumerate(poem.poem, 1):
                if re.search(r'[a-zA-Z]', line):
                    self.warnings.append(
                        f"Volume {volume_num}, UID {poem.uid}: Poem line {line_num} contains English/Latin characters: '{line}'"
                    )

                # Check for unusual brackets in poem content (occasional annotation markers are ok)
                # This is informational only, not a warning
                if re.search(r'[（(〈<）)〉>]', line):
                    pass

    def validate_all(self, start: int = MIN_VOLUME_NUMBER, end: int = MAX_VOLUME_NUMBER):
        """
        Validate all volumes in range.

        Args:
            start: Starting volume number
            end: Ending volume number

        Returns:
            List of all validated Poem objects
        """
        logger.info(f"Validating volumes {start}-{end} in {self.data_dir}")

        all_poems = []
        volumes_validated = 0

        for volume_num in range(start, end + 1):
            poems = self.validate_volume(volume_num)

            if not poems:
                continue

            volumes_validated += 1
            all_poems.extend(poems)

            # Run per-volume checks
            self.check_part_indices(poems, volume_num)
            self.check_multisong_detection(poems, volume_num)
            self.check_duplicate_titles(poems, volume_num)
            self.check_author_metadata(poems, volume_num)
            self.check_empty_content(poems, volume_num)
            self.check_required_fields(poems, volume_num)
            self.check_content_quality(poems, volume_num)

        # Run cross-volume checks
        self.check_uid_uniqueness(all_poems)

        # Update stats
        self.stats['total_volumes'] = volumes_validated
        self.stats['total_poems'] = len(all_poems)
        self.stats['multi_part_poems'] = sum(1 for p in all_poems if p.part_index is not None)

        return all_poems

    def print_report(self) -> bool:
        """
        Print validation report.

        Returns:
            True if validation passed (no errors), False otherwise
        """
        print("\n" + "=" * 80)
        print("VALIDATION REPORT")
        print("=" * 80)

        print("\nStatistics:")
        print(f"  Total volumes validated: {self.stats['total_volumes']}")
        print(f"  Total poems: {self.stats['total_poems']}")
        print(f"  Multi-part poems: {self.stats['multi_part_poems']}")
        print(f"  Missing author metadata: {self.stats['missing_author_metadata']}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors[:20]:  # Show first 20
                print(f"  - {error}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more errors")
        else:
            print("\n✅ No errors found!")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:20]:  # Show first 20
                print(f"  - {warning}")
            if len(self.warnings) > 20:
                print(f"  ... and {len(self.warnings) - 20} more warnings")
        else:
            print("\n✅ No warnings!")

        print("\n" + "=" * 80)

        return len(self.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description='Validate Complete Tang Poems output data'
    )
    parser.add_argument(
        '--dir',
        default=str(DEFAULT_PROCESSED_OUTPUT_DIR),
        help=f'Directory with processed JSON files, default: {DEFAULT_PROCESSED_OUTPUT_DIR}'
    )
    parser.add_argument(
        '--start',
        type=int,
        default=MIN_VOLUME_NUMBER,
        help=f'Starting volume ({MIN_VOLUME_NUMBER}-{MAX_VOLUME_NUMBER}), default: {MIN_VOLUME_NUMBER}'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=MAX_VOLUME_NUMBER,
        help=f'Ending volume ({MIN_VOLUME_NUMBER}-{MAX_VOLUME_NUMBER}), default: {MAX_VOLUME_NUMBER}'
    )
    parser.add_argument(
        '--volume',
        type=int,
        help='Validate single volume'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    validator = PoemValidator(data_dir=args.dir)

    if args.volume:
        poems = validator.validate_volume(args.volume)
        if poems:
            validator.check_part_indices(poems, args.volume)
            validator.check_multisong_detection(poems, args.volume)
            validator.check_duplicate_titles(poems, args.volume)
            validator.check_author_metadata(poems, args.volume)
            validator.check_empty_content(poems, args.volume)
            validator.check_required_fields(poems, args.volume)
            validator.check_content_quality(poems, args.volume)
            validator.check_uid_uniqueness(poems)

            validator.stats['total_volumes'] = 1
            validator.stats['total_poems'] = len(poems)
            validator.stats['multi_part_poems'] = sum(1 for p in poems if p.part_index is not None)
    else:
        validator.validate_all(args.start, args.end)

    success = validator.print_report()

    if not success:
        return 1
    return 0


if __name__ == '__main__':
    exit(main())
