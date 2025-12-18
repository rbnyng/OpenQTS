#!/usr/bin/env python3
"""
Post-processing script to apply hardcoded splits to raw scraped poems.

This script:
1. Reads raw JSON files from raw_output/
2. Applies multi-song splits (volumes 17-20)
3. Applies multi-part poem labeling (volumes 8, 13, 14)
4. Applies title rewrites
5. Generates new UIDs for split poems
6. Writes processed JSON to output/

Usage:
    python post_process_splits.py --start 1 --end 900
    python post_process_splits.py --volume 18
"""

import json
import logging
import argparse
import re
from pathlib import Path
from typing import List, Optional, Dict

from models import Poem, Author
import volume_special_cases
from utils import chinese_utils, uid_generator
from author_database import AuthorDatabase
from constants import LOG_FORMAT, DEFAULT_RAW_OUTPUT_DIR, DEFAULT_PROCESSED_OUTPUT_DIR

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


class PoemPostProcessor:
    """Post-processor for applying splits and corrections to scraped poems."""

    def __init__(self, raw_dir: str = None, output_dir: str = None, author_database: AuthorDatabase = None):
        """
        Initialize the post-processor.

        Args:
            raw_dir: Directory containing raw JSON files
            output_dir: Directory for processed JSON files
            author_database: AuthorDatabase instance for preserving biography content
        """
        self.raw_dir = Path(raw_dir or DEFAULT_RAW_OUTPUT_DIR)
        self.output_dir = Path(output_dir or DEFAULT_PROCESSED_OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)

        if author_database is None:
            authors_file = self.output_dir / 'authors.json'
            self.author_database = AuthorDatabase(filepath=str(authors_file))
        else:
            self.author_database = author_database

    def _cleanup_title_brackets(self, poems: List[Poem]) -> List[Poem]:
        """
        Clean up unclosed or stray brackets in poem titles.

        This handles cases where the scraper didn't properly extract bracketed content:
        1. Extract properly closed brackets (like 〈一本無此章〉) to notes if content is substantive
        2. Strip stray/unclosed opening or closing brackets (like 》〉 or （ alone)
        3. Strip empty brackets (like （） or 〈〉)

        Args:
            poems: List of Poem objects

        Returns:
            List of poems with cleaned titles
        """
        # All bracket types we handle
        open_brackets = '（(〈<《「『【'
        close_brackets = '）)〉>》」』】'
        bracket_pairs = dict(zip(open_brackets, close_brackets))
        reverse_pairs = dict(zip(close_brackets, open_brackets))

        # Pattern to match properly closed brackets and extract content
        # Matches any opening bracket, captures content, matches corresponding closing bracket
        closed_bracket_pattern = re.compile(r'[（(〈<《「『【]([^）)〉>》」』】]*)[）)〉>》」』】]')

        extract_count = 0
        strip_count = 0

        for poem in poems:
            original_title = poem.title
            title = poem.title
            notes_to_add = []

            # First, extract properly closed brackets with substantive content
            while True:
                match = closed_bracket_pattern.search(title)
                if not match:
                    break

                content = match.group(1).strip()

                # Skip empty brackets or very short content that's not meaningful
                if not content:
                    # Just remove empty brackets
                    title = title[:match.start()] + title[match.end():]
                    strip_count += 1
                    continue

                # Determine if this should be extracted to notes or kept as part of title
                # Extract if it looks like a note (starts with 一作, 一曰, 一本, etc.)
                # or if it's explaining something about the poem
                note_indicators = ['一作', '一曰', '一本', '本作', '疑作', '或作', '亦作',
                                   '見', '出', '此', '缺', '闕', '原', '注']

                should_extract = any(content.startswith(ind) for ind in note_indicators)

                # Also extract if it contains explanatory text (longer than 2 chars and has Chinese)
                if not should_extract and len(content) > 2:
                    # Check if it looks like a count (二首, 三首 etc.) - keep these in title
                    count_pattern = re.compile(r'^[一二三四五六七八九十百]+[首篇章詠]$')
                    if not count_pattern.match(content):
                        should_extract = True

                if should_extract:
                    # Get context (text before the bracket)
                    context_start = max(0, match.start() - 5)
                    context_text = title[context_start:match.start()].strip()

                    notes_to_add.append({
                        'content': content,
                        'context': context_text,
                        'original_title': original_title
                    })

                    # Remove the bracketed content from title
                    title = title[:match.start()] + title[match.end():]
                    extract_count += 1
                else:
                    # Keep in title but we've processed it, move past
                    # To avoid infinite loop, break if no extraction
                    break

            # Now strip any remaining unclosed/stray brackets
            # Remove stray closing brackets at any position
            for close_bracket in close_brackets:
                if close_bracket in title:
                    # Check if there's a matching open bracket before it
                    open_bracket = reverse_pairs[close_bracket]
                    # Count opens and closes
                    opens = title.count(open_bracket)
                    closes = title.count(close_bracket)
                    if closes > opens:
                        # More closes than opens - strip the extras
                        for _ in range(closes - opens):
                            title = title.replace(close_bracket, '', 1)
                            strip_count += 1

            # Remove stray opening brackets at any position
            for open_bracket in open_brackets:
                if open_bracket in title:
                    close_bracket = bracket_pairs[open_bracket]
                    opens = title.count(open_bracket)
                    closes = title.count(close_bracket)
                    if opens > closes:
                        # More opens than closes - strip from the end
                        for _ in range(opens - closes):
                            # Find last occurrence and remove it
                            idx = title.rfind(open_bracket)
                            if idx >= 0:
                                title = title[:idx] + title[idx+1:]
                                strip_count += 1

            # Clean up any resulting whitespace issues (normalize multiple spaces, strip ends)
            title = re.sub(r'\s+', ' ', title).strip()

            # Update poem if changed
            if title != original_title:
                poem.title = title
                logger.debug(f"Cleaned title brackets: '{original_title}' -> '{title}'")

            # Add extracted notes
            if notes_to_add:
                if poem.notes is None:
                    poem.notes = []
                poem.notes.extend(notes_to_add)

        if extract_count > 0 or strip_count > 0:
            logger.info(f"Bracket cleanup: extracted {extract_count} notes, stripped {strip_count} stray brackets")

        return poems

    def _normalize_title_character_variants(self, poems: List[Poem]) -> List[Poem]:
        """
        Normalize character variants in poem titles.

        Replaces variant characters with their standard forms:
        - 聖製 → 聖制 (imperial composition by a sage ruler)
        - 御製 → 御制 (imperial composition)
        - 應製 → 應制 (composed in response to imperial command)

        The character 製 (to manufacture) is a variant of 制 (to make/compose)
        in these imperial composition context terms.

        Args:
            poems: List of Poem objects

        Returns:
            List of poems with normalized titles
        """
        # Character variant replacements for title normalization
        replacements = {
            '聖製': '聖制',
            '御製': '御制',
            '應製': '應制',
        }

        count = 0
        for poem in poems:
            original_title = poem.title
            new_title = original_title

            for old, new in replacements.items():
                if old in new_title:
                    new_title = new_title.replace(old, new)

            if new_title != original_title:
                poem.title = new_title
                count += 1
                logger.debug(f"Normalized title: '{original_title}' -> '{new_title}'")

        if count > 0:
            logger.info(f"Normalized character variants in {count} titles")

        return poems

    def _strip_asterisk_from_titles(self, poems: List[Poem]) -> List[Poem]:
        """
        Strip leading asterisks from poem titles.

        Format: "*春寄尚顏" -> "春寄尚顏"

        Args:
            poems: List of Poem objects

        Returns:
            List of poems with asterisks removed from titles
        """
        count = 0
        for poem in poems:
            if poem.title.startswith('*'):
                poem.title = poem.title[1:]
                count += 1
                logger.debug(f"Stripped asterisk from title: {poem.title}")

        if count > 0:
            logger.info(f"Stripped asterisks from {count} titles")

        return poems

    def _strip_author_from_titles(self, poems: List[Poem]) -> List[Poem]:
        """
        Strip author name from the beginning of titles.

        Format: "王周 泊姑熟口" -> "泊姑熟口" (if author is 王周)

        Args:
            poems: List of Poem objects

        Returns:
            List of poems with author names removed from titles
        """
        count = 0
        for poem in poems:
            author_recorded = poem.author.recorded
            title = poem.title

            if title.startswith(f"{author_recorded} "):
                poem.title = title[len(author_recorded) + 1:]
                count += 1
                logger.debug(f"Stripped author '{author_recorded}' from title: {title} -> {poem.title}")

        if count > 0:
            logger.info(f"Stripped author names from {count} titles")

        return poems

    def _strip_redundant_part_suffix(self, poems: List[Poem]) -> List[Poem]:
        """
        Strip redundant part suffix (其一) from single-part poems.

        When a poem has part_index=1 and total_parts=1, the "其一" suffix is
        misleading since there's only one part. This method removes the suffix
        and resets the part fields to None.

        Format: "望月 其一" with part_index=1, total_parts=1 -> "望月" with None, None

        Args:
            poems: List of Poem objects

        Returns:
            List of poems with redundant part suffixes removed
        """
        count = 0
        for poem in poems:
            # Check if this is a single-part poem with part metadata
            if poem.part_index == 1 and poem.total_parts == 1:
                # pattern to match part suffix: 其一, 其（一）, （其一）, etc.
                # Also handle "一" at the end after space
                part_suffix_pattern = re.compile(r'\s*[（(]?其[一1][）)]?\s*$|\s+[一1]\s*$')

                new_title = part_suffix_pattern.sub('', poem.title)

                if new_title != poem.title:
                    old_title = poem.title
                    poem.title = new_title
                    poem.part_index = None
                    poem.total_parts = None
                    count += 1
                    logger.debug(f"Stripped redundant part suffix: '{old_title}' -> '{new_title}'")

        if count > 0:
            logger.info(f"Stripped redundant part suffixes from {count} single-part poems")

        return poems

    def _distribute_notes_for_split(self, notes: Optional[List], start_line: int, end_line: int) -> Optional[List]:
        """
        Distribute notes to a split part based on line indices.

        Args:
            notes: List of note dicts with optional 'line' field
            start_line: Start line index (0-indexed, inclusive)
            end_line: End line index (0-indexed, exclusive)

        Returns:
            List of notes for this split part with adjusted line indices, or None if empty
        """
        if not notes:
            return None

        part_notes = []
        for note in notes:
            note_line = note.get('line', 1) - 1  # Default to line 1 if not specified

            if start_line <= note_line < end_line:
                new_note = note.copy()
                new_note['line'] = note_line - start_line + 1  # 1-indexed relative to part
                part_notes.append(new_note)

        return part_notes if part_notes else None

    def _distribute_variants_for_split(self, variants: Optional[List], start_line: int, end_line: int) -> Optional[List]:
        """
        Distribute variants to a split part based on line indices.

        Args:
            variants: List of variant dicts with 'line' field
            start_line: Start line index (0-indexed, inclusive)
            end_line: End line index (0-indexed, exclusive)

        Returns:
            List of variants for this split part with adjusted line indices, or None if empty
        """
        if not variants:
            return None

        part_variants = []
        for variant in variants:
            variant_line = variant.get('line', 1) - 1

            # Check if this variant falls within the split range
            if start_line <= variant_line < end_line:
                new_variant = variant.copy()
                new_variant['line'] = variant_line - start_line + 1  # 1-indexed relative to part
                part_variants.append(new_variant)

        return part_variants if part_variants else None

    def _extract_source_markers_from_poem_lines(self, poems: List[Poem]) -> List[Poem]:
        """
        Extract single-character source markers (古, 主, etc.) from poem lines as notes.

        In some poems, source markers like "古" (ancient text) and "主" (main text)
        appear on separate lines to indicate textual variants. These should be
        extracted as notes attached to the preceding verse.

        Args:
            poems: List of Poem objects

        Returns:
            List of poems with source markers extracted as notes
        """
        # Known single-character source markers indicating textual variants/sources
        # These appear on separate lines and refer to different manuscript traditions
        source_markers = {
            '古',  # 古本 (ancient text)
            '主',  # 主本 (main/standard text)
            '知',  # 知不足齋 (Zhibuzuzhai collection)
            '齋',  # 齋本 (studio/study collection)
            '斋',  # 斋本 (simplified form)
            '一',  # 一本 (another version)
            '别',  # 別本 (alternative version, simplified)
            '別',  # 別本 (alternative version)
            '他',  # 他本 (other version)
            '或',  # 或本/或作 (variant reading)
            '今',  # 今本 (current/modern text)
            '宋',  # 宋本 (Song dynasty edition)
            '明',  # 明本 (Ming dynasty edition)
            '元',  # 元本 (Yuan dynasty edition)
            '唐',  # 唐本 (Tang dynasty edition)
        }

        # mapping of markers to their expanded forms
        marker_expansions = {
            '古': '古本',
            '主': '主本',
            '知': '知不足齋本',
            '齋': '齋本',
            '斋': '斋本',
            '一': '一本',
            '别': '別本',
            '別': '別本',
            '他': '他本',
            '或': '或本',
            '今': '今本',
            '宋': '宋本',
            '明': '明本',
            '元': '元本',
            '唐': '唐本',
        }

        updated_poems = []
        for poem in poems:
            # Check if any lines are source markers
            has_markers = any(line.strip() in source_markers for line in poem.poem)

            if not has_markers:
                updated_poems.append(poem)
                continue

            # Extract markers and clean poem lines
            clean_lines = []
            extracted_notes = list(poem.notes) if poem.notes else []
            prev_line = None

            for line in poem.poem:
                stripped = line.strip()
                if stripped in source_markers:
                    # This is a source marker - convert to note
                    if prev_line:
                        # expand marker to full form for clarity
                        marker_full = marker_expansions.get(stripped, stripped)
                        extracted_notes.append({
                            'line': len(clean_lines),  # 1-indexed line number
                            'content': marker_full,
                            'context': prev_line
                        })
                        logger.debug(f"Extracted source marker '{stripped}' -> '{marker_full}' from poem")
                else:
                    clean_lines.append(line)
                    prev_line = line

            # Create updated poem with cleaned lines and extracted notes
            updated_poem = Poem(
                uid=poem.uid,
                volume=poem.volume,
                author=poem.author,
                title=poem.title,
                poem=clean_lines,
                notes=extracted_notes if extracted_notes else None,
                preface=poem.preface,
                part_index=poem.part_index,
                total_parts=poem.total_parts,
                variants=poem.variants
            )
            updated_poems.append(updated_poem)

            if len(clean_lines) < len(poem.poem):
                logger.info(f"Extracted {len(poem.poem) - len(clean_lines)} source markers from '{poem.title}'")

        return updated_poems

    def _extract_author_attributions_from_poem_lines(self, poems: List[Poem]) -> List[Poem]:
        """
        Extract author attribution markers from collaborative poems (聯句).

        In linked verse (聯句), multiple poets take turns writing sections.
        Attributions can appear in two formats:
        1. Standalone lines: "——韓愈" or "——孟郊"
        2. Embedded at end of poem lines: "高歌閬風步瀛洲，——皎然"

        These attributions are extracted as notes with the verse section as context,
        allowing the poem to remain as a single collaborative work while preserving
        who wrote which parts.

        Args:
            poems: List of Poem objects

        Returns:
            List of poems with author attributions extracted as notes
        """
        # Pattern for standalone attribution lines: ——AuthorName (the entire line)
        standalone_pattern = re.compile(r'^[—–-]{1,2}\s*(.{2,5})\s*$')
        # pattern for embedded attributions at end of line: text——AuthorName
        embedded_pattern = re.compile(r'^(.+?)[—–-]{1,2}\s*(.{2,5})\s*$')

        updated_poems = []
        for poem in poems:
            # Check if any lines have attributions (standalone or embedded)
            has_attributions = any(
                standalone_pattern.match(line.strip()) or embedded_pattern.match(line.strip())
                for line in poem.poem
            )

            if not has_attributions:
                updated_poems.append(poem)
                continue

            # Extract  attributions and clean poem lines
            clean_lines = []
            extracted_notes = list(poem.notes) if poem.notes else []
            attribution_count = 0

            for line_idx, line in enumerate(poem.poem):
                stripped = line.strip()

                # First  check for standalone attribution line
                standalone_match = standalone_pattern.match(stripped)
                if standalone_match:
                    # this is a standalone attribution line - convert to note
                    author_name = standalone_match.group(1).strip()

                    # Context is the preceding line(s) since last attribution
                    context = clean_lines[-1] if clean_lines else None

                    extracted_notes.append({
                        'type': 'author_attribution',
                        'line': len(clean_lines),  # Line index (after the attributed line)
                        'content': author_name,
                        'context': context
                    })
                    attribution_count += 1
                    logger.debug(f"Extracted standalone attribution '{author_name}'")
                    continue

                # Check for embedded attribution at end of line
                embedded_match = embedded_pattern.match(stripped)
                if embedded_match:
                    # Extract the poem content and author separately
                    poem_content = embedded_match.group(1).strip()
                    author_name = embedded_match.group(2).strip()

                    # Add the cleaned poem line
                    clean_lines.append(poem_content)

                    # Add attribution note for this line
                    extracted_notes.append({
                        'type': 'author_attribution',
                        'line': len(clean_lines),  # Line index (1-based after adding)
                        'content': author_name,
                        'context': poem_content
                    })
                    attribution_count += 1
                    logger.debug(f"Extracted embedded attribution '{author_name}' from line")
                else:
                    # Regular poem line with no attribution
                    clean_lines.append(line)

            # Create updated poem with cleaned lines and extracted notes
            updated_poem = Poem(
                uid=poem.uid,
                volume=poem.volume,
                author=poem.author,
                title=poem.title,
                poem=clean_lines,
                notes=extracted_notes if extracted_notes else None,
                preface=poem.preface,
                part_index=poem.part_index,
                total_parts=poem.total_parts,
                variants=poem.variants
            )
            updated_poems.append(updated_poem)

            if attribution_count > 0:
                logger.info(f"Extracted {attribution_count} author attributions from '{poem.title}' (聯句)")

        return updated_poems

    def _remove_biography_entries(self, poems: List[Poem]) -> List[Poem]:
        """
        Remove entries where the title is just the author name (biography entries).

        These are typically biography paragraphs that were incorrectly extracted as poems.
        Format: title == author_recorded

        Args:
            poems: List of Poem objects

        Returns:
            Filtered list of poems with biography entries removed
        """
        before_count = len(poems)
        filtered_poems = []

        for poem in poems:
            author_recorded = poem.author.recorded
            title = poem.title

            # Check if title is exactly the author name (biography entry)
            if title == author_recorded:
                logger.debug(f"Removing biography entry: {poem.uid} - {title}")
                continue

            filtered_poems.append(poem)

        removed_count = before_count - len(filtered_poems)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} biography entries")

        return filtered_poems

    def _remove_volume_specific_biographies(self, poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Remove biography entries specified in volume_special_cases.py.

        Before removing, checks if the biography content is in the author database.
        If not, adds it to preserve the biographical information.

        Args:
            poems: List of Poem objects
            volume_num: Volume number

        Returns:
            Filtered list of poems with volume-specific biographies removed
        """
        before_count = len(poems)
        filtered_poems = []

        for poem in poems:
            # Check if this is a volume-specific biography to remove
            if volume_special_cases.should_remove_biography_entry(volume_num, poem.title):
                logger.info(f"Removing volume-specific biography: {poem.uid} - {poem.title}")

                # Extract biography text from poem content
                biography_text = '\n'.join(poem.poem)

                # Check if this biography is already in the author database
                author_data = self.author_database.get_author(poem.author.canonical)
                biography_exists = False

                if author_data and 'biographies' in author_data:
                    # Check if this exact biography already exists
                    biography_exists = any(
                        bio.get('text') == biography_text
                        for bio in author_data['biographies']
                    )

                if not biography_exists:
                    logger.info(
                        f"Preserving biography for {poem.author.canonical} "
                        f"from volume {volume_num} before removal"
                    )
                    self.author_database.add_or_update_author(
                        author=poem.author,
                        biography=biography_text,
                        source_volume=volume_num
                    )
                else:
                    logger.debug(
                        f"Biography for {poem.author.canonical} already exists in database"
                    )

                continue

            filtered_poems.append(poem)

        removed_count = before_count - len(filtered_poems)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} volume-specific biography entries")

        return filtered_poems

    def _remove_stub_entries(self, poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Remove stub/duplicate entries specified in volume_special_cases.py.

        Args:
            poems: List of Poem objects
            volume_num: Volume number

        Returns:
            Filtered list of poems with stub entries removed
        """
        before_count = len(poems)
        filtered_poems = []

        for poem in poems:
            first_line = poem.poem[0] if poem.poem else ""

            # Check if this is a stub entry to remove
            if volume_special_cases.should_remove_stub_entry(volume_num, poem.title, first_line):
                logger.info(f"Removing stub entry: {poem.uid} - {poem.title} ('{first_line}')")
                continue

            filtered_poems.append(poem)

        removed_count = before_count - len(filtered_poems)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} stub entries")

        return filtered_poems

    def _merge_preface_splits(self, poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Fix cases where a preface (并序/有序) was incorrectly split into separate entries.

        Patterns detected:
        1. Simple consecutive entries:
           - Two consecutive poems with same title and author
           - First has 〈并序〉 or 〈有序〉 note or prose content
           - Second has verse content

        2. Multi-part series with 〈并序〉 or 〈有序〉 note:
           - Part 1 contains prose (the preface), not poetry
           - Stray entry exists with same base title (no part markers)

        Solution:
        - For pattern 1: Merge first into preface field of second
        - For pattern 2: Move part 1's content to preface field for all parts,
          use stray entry as the new part 1

        Args:
            poems: List of Poem objects
            volume_num: Volume number for checking forced preface parts

        Returns:
            List of poems with preface splits merged
        """
        logger.debug(f"_merge_preface_splits: Processing {len(poems)} poems")
        result = []
        i = 0

        while i < len(poems):
            current = poems[i]

            # pattern 1: Check for simple consecutive entries with same title
            if i + 1 < len(poems):
                next_poem = poems[i + 1]

                current_title = current.title
                if current.author.recorded and current_title.startswith(f"{current.author.recorded} "):
                    current_title = current_title[len(current.author.recorded) + 1:]

                next_title = next_poem.title
                if next_poem.author.recorded and next_title.startswith(f"{next_poem.author.recorded} "):
                    next_title = next_title[len(next_poem.author.recorded) + 1:]

                # check if consecutive poems have identical titles and authors
                if (current_title == next_title and
                    current.author.canonical == next_poem.author.canonical and
                    not current.part_index and not next_poem.part_index):

                    # Check if first has 并序/並序/有序 note (preface indicators)
                    has_preface_note = current.notes and any(
                        '并序' in str(note) or '並序' in str(note) or '有序' in str(note)
                        for note in current.notes
                    )

                    # Check if first looks like prose (avg line length > 20)
                    current_avg_len = sum(len(line) for line in current.poem) / len(current.poem) if current.poem else 0
                    next_avg_len = sum(len(line) for line in next_poem.poem) / len(next_poem.poem) if next_poem.poem else 0

                    current_looks_like_prose = current_avg_len > 20
                    next_looks_like_verse = next_avg_len <= 15

                    # Check if first entry is empty (extracted preface with no content)
                    current_is_empty_preface = not current.poem and next_poem.poem

                    if has_preface_note or (current_looks_like_prose and next_looks_like_verse) or current_is_empty_preface:
                        logger.info(
                            f"Merging consecutive preface split: '{current.title}' "
                            f"(preface: {current_avg_len:.1f} chars/line, "
                            f"poem: {next_avg_len:.1f} chars/line, "
                            f"has note: {has_preface_note})"
                        )

                        # Merge: use current's content as preface for next
                        merged_preface = '\n'.join(current.poem)

                        # Keep next poem's existing preface if any, prepend new preface
                        if next_poem.preface:
                            merged_preface = merged_preface + '\n' + next_poem.preface

                        merged_poem = Poem(
                            uid=current.uid,  # Use first poem's UID
                            volume=next_poem.volume,
                            author=next_poem.author,
                            title=next_poem.title,
                            poem=next_poem.poem,
                            preface=merged_preface,
                            notes=current.notes if current.notes else next_poem.notes,
                            variants=next_poem.variants,
                            part_index=next_poem.part_index,
                            total_parts=next_poem.total_parts
                        )

                        result.append(merged_poem)
                        i += 2  # Skip both poems
                        continue

            # Pattern 2: Only check multi-part poems with 并序 note
            if not current.part_index or not current.notes:
                result.append(current)
                i += 1
                continue

            # Check if this series has a 并序/並序/有序 note (preface indicators)
            has_preface_note = any(
                '并序' in str(note) or '並序' in str(note) or '有序' in str(note)
                for note in current.notes
            )

            # also check if this is manually marked as a forced preface part (even without note)
            is_potential_forced_preface = (
                current.part_index == 1 and
                volume_special_cases.is_forced_preface_part(volume_num, current.title, current.author.canonical)
            )

            if not has_preface_note and not is_potential_forced_preface:
                result.append(current)
                i += 1
                continue

            logger.debug(f"Found poem with preface note (并序/有序): {current.title}")

            current_title_clean = current.title
            if current.author.recorded and current_title_clean.startswith(f"{current.author.recorded} "):
                current_title_clean = current_title_clean[len(current.author.recorded) + 1:]

            # Get base title (remove part markers)
            base_title = re.sub(r'\s+(其|第)([一二三四五六七八九十]+)$', '', current_title_clean)

            # Collect all poems in this series
            series_poems = []
            j = i
            while j < len(poems):
                poem = poems[j]

                poem_title_clean = poem.title
                if poem.author.recorded and poem_title_clean.startswith(f"{poem.author.recorded} "):
                    poem_title_clean = poem_title_clean[len(poem.author.recorded) + 1:]

                poem_base_title = re.sub(r'\s+(其|第)([一二三四五六七八九十]+)$', '', poem_title_clean)
                if poem_base_title == base_title and poem.author.canonical == current.author.canonical:
                    series_poems.append(poem)
                    j += 1
                else:
                    break

            logger.debug(f"  Collected {len(series_poems)} poems in series '{base_title}'")

            # Find part 1 and check if it looks like prose
            part1 = next((p for p in series_poems if p.part_index == 1), None)
            if not part1:
                logger.debug(f"  No part 1 found, skipping")
                result.extend(series_poems)
                i = j
                continue

            # Check if this is a forced preface part or if it looks like prose
            # Simple heuristic: prose lines are typically longer (>30 chars)
            # Poetry lines are typically 5-7 chars (plus punctuation)
            part1_avg_len = sum(len(line) for line in part1.poem) / len(part1.poem) if part1.poem else 0
            part1_looks_like_prose = part1_avg_len > 20

            # Also check if this is manually marked as a preface part
            is_forced_preface = volume_special_cases.is_forced_preface_part(
                volume_num, part1.title, part1.author.canonical
            )

            logger.debug(f"  Part 1 avg line length: {part1_avg_len:.1f} chars, looks like prose: {part1_looks_like_prose}, forced preface: {is_forced_preface}")

            if not part1_looks_like_prose and not is_forced_preface:
                result.extend(series_poems)
                i = j
                continue

            # Look for stray entry within the collected series (no part_index)
            stray = None
            stray_idx = None
            logger.debug(f"  Looking for stray entry with base title '{base_title}'...")
            for k, candidate in enumerate(series_poems):
                if not candidate.part_index:
                    stray = candidate
                    stray_idx = k
                    logger.debug(f"  Found stray entry in series at position {k}: {candidate.title}")
                    break

            if stray:
                # Found the pattern! Merge the preface split
                logger.info(
                    f"Detected preface split for '{base_title}': "
                    f"Part 1 is prose ({part1_avg_len:.1f} chars/line), "
                    f"found stray entry at position {stray_idx} in series. Merging..."
                )

                # Preface content from part 1
                preface_lines = part1.poem

                # create updated series:
                # - Parts 2-N shift down to become parts 1-(N-1)
                # - Stray entry becomes part N (last part)
                # - Only part 1 gets the preface

                # Renumber parts 2-N as 1-(N-1)
                for poem in series_poems:
                    if poem.part_index and poem.part_index > 1:
                        # Shift part number down by 1 (part 2 → part 1, etc.)
                        new_part_num = poem.part_index - 1

                        # Use original part 1's UID for new part 1, others keep their UIDs
                        if new_part_num == 1:
                            uid = part1.uid
                        else:
                            uid = poem.uid

                        updated_poem = Poem(
                            uid=uid,
                            volume=poem.volume,
                            author=poem.author,
                            title=f"{base_title} 其{chinese_utils.number_to_chinese(new_part_num)}",
                            poem=poem.poem,
                            notes=poem.notes if new_part_num > 1 else part1.notes,  # Part 1 gets original notes
                            preface=preface_lines if new_part_num == 1 else None,  # Only part 1 gets preface
                            part_index=new_part_num,
                            total_parts=current.total_parts,
                            variants=poem.variants
                        )
                        result.append(updated_poem)

                # Add stray as the final part (part N)
                final_part_num = current.total_parts
                final_part = Poem(
                    uid=stray.uid,
                    volume=stray.volume,
                    author=stray.author,
                    title=f"{base_title} 其{chinese_utils.number_to_chinese(final_part_num)}",
                    poem=stray.poem,
                    notes=stray.notes,
                    preface=None,  # Only part 1 gets preface
                    part_index=final_part_num,
                    total_parts=current.total_parts,
                    variants=stray.variants
                )
                result.append(final_part)

                logger.info(
                    f"Merged preface split for '{base_title}': "
                    f"Moved prose to preface field, renumbered parts, stray → part {final_part_num}"
                )

                # Skip past the entire series (including stray)
                i = j
            else:
                # No stray found - check if this is a forced preface that should still be merged
                if is_forced_preface and len(series_poems) >= 2:
                    logger.info(
                        f"Forced preface merge for '{base_title}': "
                        f"Attaching Part 1 as preface to remaining parts (no stray entry)"
                    )

                    # Attach Part 1's content as preface to Part 2 only
                    preface_content = '\n'.join(part1.poem)

                    for poem in series_poems:
                        if poem.part_index == 1:
                            # Skip Part 1 - it becomes the preface
                            continue
                        elif poem.part_index == 2:
                            # Attach preface to Part 2 and keep it as Part 2
                            merged_poem = Poem(
                                uid=poem.uid,
                                volume=poem.volume,
                                author=poem.author,
                                title=poem.title,
                                poem=poem.poem,
                                preface=preface_content,
                                notes=part1.notes if part1.notes else poem.notes,  # Use Part 1's notes
                                part_index=poem.part_index,
                                total_parts=current.total_parts,
                                variants=poem.variants
                            )
                            result.append(merged_poem)
                        else:
                            # Keep other parts as-is
                            result.append(poem)

                    i = j
                else:
                    # No stray found and not a forced preface, keep series as-is
                    result.extend(series_poems)
                    i = j

        return result

    def _validate_author_names(self, poems: List[Poem], volume_num: int) -> None:
        """
        Validate author names in the poem data and output warnings for issues.

        Checks for:
        - Empty canonical or recorded names
        - Names that are too long (> 100 characters)

        Args:
            poems: List of Poem objects to validate
            volume_num: Volume number for context in warnings
        """
        MAX_NAME_LENGTH = 100

        for poem in poems:
            author = poem.author

            # Check for empty canonical name
            if not author.canonical or not author.canonical.strip():
                logger.warning(
                    f"Volume {volume_num}, UID {poem.uid}: Author has empty canonical name. "
                    f"Recorded: '{author.recorded}', Title: '{poem.title}'"
                )

            # check for empty recorded name
            if not author.recorded or not author.recorded.strip():
                logger.warning(
                    f"Volume {volume_num}, UID {poem.uid}: Author has empty recorded name. "
                    f"Canonical: '{author.canonical}', Title: '{poem.title}'"
                )

            # Check for too long canonical name
            if author.canonical and len(author.canonical) > MAX_NAME_LENGTH:
                logger.warning(
                    f"Volume {volume_num}, UID {poem.uid}: Author canonical name is too long "
                    f"({len(author.canonical)} chars, max {MAX_NAME_LENGTH}). "
                    f"Name: '{author.canonical[:50]}...', Title: '{poem.title}'"
                )

            # Check for too long recorded name
            if author.recorded and len(author.recorded) > MAX_NAME_LENGTH:
                logger.warning(
                    f"Volume {volume_num}, UID {poem.uid}: Author recorded name is too long "
                    f"({len(author.recorded)} chars, max {MAX_NAME_LENGTH}). "
                    f"Name: '{author.recorded[:50]}...', Title: '{poem.title}'"
                )

    def _apply_cleanup_postprocessing(self, poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Apply all cleanup post-processing steps to poem data.

        Steps:
        1. Extract source markers (古, 主) from poem lines as notes
        2. Strip asterisks from titles
        3. Strip author names from titles
        4. Normalize character variants in titles (製 → 制 in imperial terms)
        5. Clean up unclosed/stray brackets in titles, extracting notes where appropriate
        6. Remove generic biography entries (title == author)
        7. Remove volume-specific biography entries
        8. Remove stub/duplicate entries
        9. Merge preface splits (并序/有序 cases)

        Args:
            poems: List of Poem objects
            volume_num: Volume number

        Returns:
            Post-processed list of poems
        """
        logger.info(f"Applying cleanup post-processing for {len(poems)} poems")

        # Apply all post-processing steps in order
        poems = self._extract_source_markers_from_poem_lines(poems)
        poems = self._extract_author_attributions_from_poem_lines(poems)
        poems = self._strip_asterisk_from_titles(poems)
        poems = self._strip_author_from_titles(poems)
        poems = self._normalize_title_character_variants(poems)
        poems = self._cleanup_title_brackets(poems)
        # Note: _strip_redundant_part_suffix is called AFTER _finalize_total_parts
        # to ensure total_parts is accurate before deciding whether to strip
        poems = self._remove_biography_entries(poems)
        poems = self._remove_volume_specific_biographies(poems, volume_num)
        poems = self._remove_stub_entries(poems, volume_num)
        poems = self._merge_preface_splits(poems, volume_num)

        # Reindex UIDs after all removals/merges (gaps in entry indices need to be closed)
        poems = self._reindex_uids(poems, volume_num)

        logger.info(f"Cleanup post-processing complete. Final count: {len(poems)} poems")

        return poems

    def _reindex_uids(self, poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Reindex UIDs to close gaps caused by removed poems.

        After removing biographies, stubs, and merging prefaces, there may be
        gaps in the entry indices. This function renumbers all UIDs to be sequential.

        Args:
            poems: List of poems with potentially gapped UIDs
            volume_num: Volume number

        Returns:
            List of poems with sequential UIDs
        """
        # Build a mapping of old entry_index -> new entry_index
        # Preserve multi-part poem grouping (all parts share same entry)
        old_to_new = {}
        current_entry = 0

        for poem in poems:
            # Extract old entry index from UID (format: QTS_VVV_EEE_PP)
            uid_parts = poem.uid.split('_')
            if len(uid_parts) >= 3:
                old_entry = int(uid_parts[2])

                # if this is a new entry we haven't seen, assign next sequential number
                if old_entry not in old_to_new:
                    current_entry += 1
                    old_to_new[old_entry] = current_entry

        # Update all UIDs with new entry indices
        updated_poems = []
        for poem in poems:
            uid_parts = poem.uid.split('_')
            if len(uid_parts) >= 4:
                old_entry = int(uid_parts[2])
                new_entry = old_to_new[old_entry]
                part_num = int(uid_parts[3])

                new_uid = uid_generator.generate_uid(volume_num, new_entry, part_num)

                updated_poem = Poem(
                    uid=new_uid,
                    volume=poem.volume,
                    author=poem.author,
                    title=poem.title,
                    poem=poem.poem,
                    notes=poem.notes,
                    preface=poem.preface,
                    part_index=poem.part_index,
                    total_parts=poem.total_parts,
                    variants=poem.variants
                )
                updated_poems.append(updated_poem)
            else:
                # Malformed UID, keep as-is
                updated_poems.append(poem)

        return updated_poems

    def _preprocess_merges(self, raw_poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Handle specific cases where notes/prefaces were scraped as separate poems.
        Merges them into the target poem's notes or preface field.
        """
        has_note_merges = volume_num in volume_special_cases.POEMS_TO_MERGE_AS_NOTES
        has_preface_merges = volume_num in volume_special_cases.POEMS_TO_MERGE_AS_PREFACE

        if not has_note_merges and not has_preface_merges:
            return raw_poems

        logger.info(f"Checking for manual merges in Volume {volume_num}...")
        merged_poems = []
        skip_indices = set()

        for i in range(len(raw_poems)):
            if i in skip_indices:
                continue

            current = raw_poems[i]

            # Safe check for first line existence
            first_line = current.poem[0] if current.poem else ""

            # Check if this poem matches a note merge rule
            note_rule = volume_special_cases.get_merge_rule(volume_num, current.title, first_line)

            if note_rule and note_rule['target'] == 'next' and i + 1 < len(raw_poems):
                target_poem = raw_poems[i + 1]

                # Double check the target has the same title (sanity check)
                if target_poem.title == current.title:
                    logger.info(f"Merging '{current.title}' (Note) into next entry")

                    note_content = "".join(current.poem)

                    if target_poem.notes is None:
                        target_poem.notes = []

                    target_poem.notes.insert(0, note_content)

                    # Add the modified target to our list
                    merged_poems.append(target_poem)

                    skip_indices.add(i + 1)
                    continue

            # Check if this poem matches a preface merge rule
            preface_rule = volume_special_cases.get_preface_merge_rule(
                volume_num, current.title, first_line, current.author.recorded
            )

            if preface_rule:
                logger.debug(f"Found preface merge rule for '{current.title}'")
                logger.debug(f"  First line: '{first_line[:60]}...'")
                logger.debug(f"  Rule target: {preface_rule['target']}")

            if preface_rule and preface_rule['target'] == 'next' and i + 1 < len(raw_poems):
                target_poem = raw_poems[i + 1]
                logger.debug(f"  Next poem title: '{target_poem.title}'")

                current_stripped = current.title
                if current.author.recorded and current_stripped.startswith(f"{current.author.recorded} "):
                    current_stripped = current_stripped[len(current.author.recorded) + 1:]

                target_stripped = target_poem.title
                if target_poem.author.recorded and target_stripped.startswith(f"{target_poem.author.recorded} "):
                    target_stripped = target_stripped[len(target_poem.author.recorded) + 1:]

                # Double check the target has the same title or starts with it (for multi-part series)
                title_match = (target_stripped == current_stripped or
                              target_stripped.startswith(current_stripped + ' '))

                logger.debug(f"  Title match: current_stripped='{current_stripped}', target_stripped='{target_stripped}'")
                logger.debug(f"    exact={target_stripped == current_stripped}, "
                           f"starts={target_stripped.startswith(current_stripped + ' ')}, result={title_match}")

                if title_match:
                    logger.info(f"Merging '{current.title}' (Preface) into next entry: '{target_poem.title}'")

                    # Strip newlines to create continuous prose text
                    preface_content = "".join(current.poem)

                    # set the target's preface
                    target_poem.preface = preface_content

                    # Add the modified target to our list
                    merged_poems.append(target_poem)

                    skip_indices.add(i + 1)
                    continue

            # If no rule matched, or logic failed, keep the poem as is
            merged_poems.append(current)

        return merged_poems

    def _fix_parent_title_duplicates(self, raw_poems: List[Poem]) -> List[Poem]:
        """
        Fix cases where scraper extracted both a parent title and child parts.

        Detects pattern like:
        - "望廬山瀑布水二首" (parent, duplicates 其一)
        - "其一" (child)
        - "其二" (child)

        Solution: Remove parent, rename children to include parent title.
        """
        multi_part_pattern = re.compile(r'([一二三四五六七八九十]+)首')
        result = []
        i = 0

        while i < len(raw_poems):
            current = raw_poems[i]

            # Check if this is a multi-part title (XXX N首)
            match = multi_part_pattern.search(current.title)
            if not match:
                result.append(current)
                i += 1
                continue

            # Check if the next poem is "其一"
            if i + 1 < len(raw_poems) and raw_poems[i + 1].title.strip() in ['其一', '其二', '其三', '其四', '其五',
                                                                                  '其六', '其七', '其八', '其九', '其十']:
                parent_title = current.title
                parent_author = current.author.recorded

                children = []
                j = i + 1
                while j < len(raw_poems):
                    next_poem = raw_poems[j]
                    # Check if it's a "其N" title with same author
                    if (re.match(r'^其[一二三四五六七八九十]+$', next_poem.title.strip()) and
                        next_poem.author.recorded == parent_author):
                        children.append(next_poem)
                        j += 1
                    else:
                        break

                # If we found children, skip parent and rename children
                if children:
                    logger.info(f"Fixing parent title duplicate: '{parent_title}' with {len(children)} children")

                    for child in children:
                        # Rename child to include parent title
                        new_title = f"{parent_title} {child.title}"
                        updated_poem = Poem(
                            uid=child.uid,
                            volume=child.volume,
                            author=child.author,
                            title=new_title,
                            poem=child.poem,
                            notes=child.notes,
                            preface=child.preface,
                            part_index=child.part_index,
                            total_parts=child.total_parts,
                            variants=child.variants
                        )
                        result.append(updated_poem)

                    i = j  # Skip past parent and all children
                    continue

            # No pattern matched, keep as-is
            result.append(current)
            i += 1

        return result

    def _merge_consecutive_multipart_poems(self, raw_poems: List[Poem]) -> List[Poem]:
        """
        Merge consecutive poems with same title that indicates multiple parts.

        Detects cases like:
        - "與國賢良夜歌二首" (poem 1)
        - "與國賢良夜歌二首" (poem 2)
        - "村夜二篇" (poem 1)
        - "村夜二篇" (poem 2)

        Where title indicates N parts but scraper extracted as separate poems.
        Adds part markers (其一, 其二) so later processing merges them correctly.

        Also supports FORCED_CONSECUTIVE_MERGE for titles where automatic detection
        gets the wrong count (e.g., "八詠應制二首" matches 八詠 instead of 二首).

        Args:
            raw_poems: List of raw poems

        Returns:
            List with part markers added to consecutive multi-part poems
        """
        # Pattern to detect "N首", "N篇", "N詠", or "N章" in title
        # Include "一" for numbers like "十一", "二十一", etc.
        multi_part_pattern = re.compile(r'([一二三四五六七八九十]+)(?:首|篇|詠|章)')
        chinese_numbers = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6,
            '七': 7, '八': 8, '九': 9, '十': 10,
            '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
            '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
            '三十': 30
        }

        # Get forced merge overrides for this volume
        volume_num = raw_poems[0].volume if raw_poems else None
        forced_merges = volume_special_cases.FORCED_CONSECUTIVE_MERGE.get(volume_num, [])

        result = []
        i = 0

        while i < len(raw_poems):
            current = raw_poems[i]

            # First, check for forced merge override
            expected_parts = None
            for override in forced_merges:
                if (current.title == override['title'] and
                    current.author.recorded == override['author']):
                    expected_parts = override['expected_parts']
                    logger.debug(f"Using forced merge override for '{current.title}': {expected_parts} parts")
                    break

            # If no override, use automatic pattern detection
            if expected_parts is None:
                # Check if title indicates multiple parts
                # Use findall and take the LAST match - e.g., "江有楓一篇十章" should match
                # "十章" (10 chapters), not "一篇" (1 section)
                matches = multi_part_pattern.findall(current.title)

                # If not in title, check notes for multi-part indicator
                if not matches and current.notes:
                    for note in current.notes:
                        # Check if note contains N首/N篇/N詠/N章
                        if isinstance(note, dict) and 'content' in note:
                            matches = multi_part_pattern.findall(note['content'])
                            if matches:
                                break

                if not matches:
                    result.append(current)
                    i += 1
                    continue

                chinese_num = matches[-1]  # Use last match
                expected_parts = chinese_numbers.get(chinese_num)

            if not expected_parts:
                result.append(current)
                i += 1
                continue

            # Skip single-part poems (expected_parts == 1) - no need to add "其一" markers
            # These are standalone poems like "上古一章" that happen to have "一章" in the title
            if expected_parts == 1:
                result.append(current)
                i += 1
                continue

            # Look ahead to find consecutive poems with same (title, author)
            group = [current]
            j = i + 1

            while j < len(raw_poems) and len(group) < expected_parts:
                next_poem = raw_poems[j]

                # Check if same title and author
                if (next_poem.title == current.title and
                    next_poem.author.recorded == current.author.recorded):
                    group.append(next_poem)
                    j += 1
                else:
                    break

            # If we found the expected number of parts, add part markers
            if len(group) == expected_parts:
                logger.info(
                    f"Merging {len(group)} consecutive poems: '{current.title}' "
                    f"by {current.author.recorded}"
                )

                for part_num, poem in enumerate(group, 1):
                    chinese_part = chinese_utils.number_to_chinese(part_num)
                    new_title = f"{poem.title} 其{chinese_part}"

                    # Create updated poem with part marker in title
                    updated_poem = Poem(
                        uid=poem.uid,
                        volume=poem.volume,
                        author=poem.author,
                        title=new_title,
                        poem=poem.poem,
                        notes=poem.notes,
                        preface=poem.preface,
                        part_index=poem.part_index,
                        total_parts=poem.total_parts,
                        variants=poem.variants
                    )
                    result.append(updated_poem)
                    logger.debug(f"  Added part marker: {new_title}")

                i = j  # Skip past all merged poems
            else:
                result.append(current)
                i += 1

        return result

    def _merge_seasonal_sets(self, raw_poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Merge seasonal sets for specific volumes.

        Detects cases like:
        - "相和歌辭·子夜四時歌四首·春歌"
        - "相和歌辭·子夜四時歌四首·夏歌"
        - "相和歌辭·子夜四時歌四首·秋歌"
        - "相和歌辭·子夜四時歌四首·冬歌"

        Where all four should share the same entry_index as a set.
        Adds part markers (其一, 其二, etc.) so later processing merges them correctly.

        Args:
            raw_poems: List of raw poems
            volume_num: Volume number

        Returns:
            List with part markers added to seasonal sets
        """
        # Get volume-specific seasonal/named part sets configuration using registry
        seasonal_configs = volume_special_cases.get_named_part_sets(volume_num)

        if not seasonal_configs:
            return raw_poems

        result = []
        i = 0

        while i < len(raw_poems):
            current = raw_poems[i]
            matched_config = None

            title = current.title
            if title.startswith(f"{current.author.recorded} "):
                title = title[len(current.author.recorded) + 1:]

            # Check if current poem matches any seasonal set configuration
            for config in seasonal_configs:
                if (current.author.recorded == config['author'] and
                    title.startswith(config['base_title'])):
                    matched_config = config
                    break

            if not matched_config:
                result.append(current)
                i += 1
                continue

            # Look ahead to find all poems in this seasonal/named part set
            base_title = matched_config['base_title']
            author = matched_config['author']
            expected_count = matched_config['expected_count']
            # Get part patterns (can be season_patterns or part_patterns)
            part_patterns = matched_config.get('season_patterns') or matched_config.get('part_patterns')

            # Check if first entry is a preface (has "並序" note)
            preface_entry = None
            is_preface = False
            if current.notes:
                for note in current.notes:
                    if '並序' in note.get('content', ''):
                        is_preface = True
                        preface_entry = current
                        break

            # If  first entry is preface, start collecting actual parts from next poem
            if is_preface:
                group = []
                j = i + 1
            else:
                group = [current]
                j = i + 1

            while j < len(raw_poems) and len(group) < expected_count:
                next_poem = raw_poems[j]

                next_title = next_poem.title
                if next_title.startswith(f"{next_poem.author.recorded} "):
                    next_title = next_title[len(next_poem.author.recorded) + 1:]

                # check if same author and base title
                if (next_poem.author.recorded == author and
                    next_title.startswith(base_title)):
                    group.append(next_poem)
                    j += 1
                else:
                    break

            # If we found the expected number of poems in the set, add part markers
            if len(group) == expected_count:
                logger.info(
                    f"Merging {len(group)} poems in set: '{base_title}' "
                    f"by {author}{' (with preface)' if preface_entry else ''}"
                )

                for part_num, poem in enumerate(group, 1):
                    chinese_part = chinese_utils.number_to_chinese(part_num)

                    if matched_config.get('use_custom_titles') and 'part_patterns' in matched_config:
                        # Custom titles: use part_patterns as actual titles (e.g., "高士詠 混元皇帝")
                        custom_title = part_patterns[part_num - 1] if part_num <= len(part_patterns) else f"其{chinese_part}"
                        new_title = f"{base_title} {custom_title}"
                    elif 'part_patterns' in matched_config:
                        # named part set - keep original title, but add hidden grouping marker
                        # Use special format: title + " __GROUP__" + base_title
                        new_title = f"{poem.title} __GROUP__{base_title}"
                    else:
                        # seasonal set - add 其X marker
                        new_title = f"{base_title} 其{chinese_part}"

                    # If this is the first part and we have a preface, merge preface content
                    merged_preface = poem.preface
                    merged_notes = poem.notes or []
                    if part_num == 1 and preface_entry:
                        # Merge preface poem content into preface field
                        if preface_entry.poem:
                            preface_text = '\n'.join(preface_entry.poem)
                            if merged_preface:
                                merged_preface = f"{preface_text}\n{merged_preface}"
                            else:
                                merged_preface = preface_text
                        # Merge preface notes
                        if preface_entry.notes:
                            merged_notes = preface_entry.notes + merged_notes

                    # Create updated poem with marker in title
                    updated_poem = Poem(
                        uid=poem.uid,
                        volume=poem.volume,
                        author=poem.author,
                        title=new_title,
                        poem=poem.poem,
                        notes=merged_notes,
                        preface=merged_preface,
                        part_index=part_num,  # Set part_index here
                        total_parts=expected_count,  # Set total_parts here
                        variants=poem.variants
                    )
                    result.append(updated_poem)
                    logger.debug(f"  Added part marker/grouping: {new_title}")

                i = j  # Skip past all merged poems
            else:
                result.append(current)
                i += 1

        return result

    def _get_line_char_count(self, line: str) -> int:
        """
        Get character count of a line, excluding punctuation.

        Args:
            line: Poem line

        Returns:
            Character count (excluding punctuation)
        """
        # Remove common Chinese punctuation
        clean_line = re.sub(r'[，。！？、；：]', '', line)
        return len(clean_line)

    def _find_format_boundaries(self, poem_lines: List[str]) -> Optional[List[tuple]]:
        """
        Find boundaries where line format (character count) changes.

        Args:
            poem_lines: Normalized poem lines

        Returns:
            List of (start, end) tuples for each segment, or None if no clear boundaries
        """
        if not poem_lines:
            return None

        # Get character count pattern for each line
        patterns = [self._get_line_char_count(line) for line in poem_lines]

        # Find boundaries where pattern changes
        boundaries = []
        start = 0
        current_pattern = patterns[0]

        for i in range(1, len(patterns)):
            if patterns[i] != current_pattern:
                boundaries.append((start, i))
                start = i
                current_pattern = patterns[i]

        # Add  final boundary
        boundaries.append((start, len(patterns)))

        # If only one boundary, no format changes detected
        if len(boundaries) == 1:
            return None

        return boundaries

    def _detect_format_change_split(self, poem: Poem, title: str) -> Optional[List[Poem]]:
        """
        Auto-detect and split poems where format changes (e.g., 7-char + 5-char stacked).

        Conservative safety rules:
        - Title must contain explicit part count (二首, 三首, etc.)
        - Format must change at clear boundaries
        - Number of segments must match title count
        - Each segment must pass safety checks (standard length, uniform)

        Args:
            poem: Poem to check
            title: Poem title (already stripped of author prefix)

        Returns:
            List of split poems if safe to split, None otherwise
        """
        import re

        # Check 1: Title must have explicit part count (二首, 三首, etc.)
        match = re.search(r'([二三四五六七八九十]+)首', title)
        if not match:
            return None

        expected_parts = chinese_utils.chinese_to_number(match.group(1))
        if expected_parts < 2:
            return None

        # Check 2: Normalize and find format boundaries
        # Use full normalization (not just single-paragraph splitting)
        poem_lines = chinese_utils.normalize_poem_lines(poem.poem)
        boundaries = self._find_format_boundaries(poem_lines)

        if not boundaries:
            # No format changes detected
            return None

        # Check 3: Number of segments must match expected parts
        if len(boundaries) != expected_parts:
            # Debug: show character patterns
            patterns = [self._get_line_char_count(line) for line in poem_lines]
            logger.debug(
                f"Format-change auto-split SKIPPED for '{title}': "
                f"Found {len(boundaries)} segments but title indicates {expected_parts} parts. "
                f"Patterns: {patterns}, Boundaries: {boundaries}"
            )
            return None

        # Check 4: Each segment must be safe to split (standard length, uniform)
        for start, end in boundaries:
            segment = poem_lines[start:end]
            # Use existing safety checker - validates standard length AND uniformity
            if not self._is_safe_to_autosplit(segment, 1, title):
                logger.debug(
                    f"Format-change auto-split SKIPPED for '{title}': "
                    f"Segment [{start}:{end}] failed safety checks"
                )
                return None

        # All checks passed - create split poems
        logger.info(
            f"Format-change auto-split detected: '{title}' "
            f"({len(poem_lines)} lines → {expected_parts} parts with format changes)"
        )

        base_title = title
        split_poems = []

        for part_num, (start, end) in enumerate(boundaries, 1):
            chinese_part = chinese_utils.number_to_chinese(part_num)
            part_title = f"{base_title} 其{chinese_part}"

            fragment_lines = poem_lines[start:end]

            # Distribute notes and variants based on line ranges
            part_notes = self._distribute_notes_for_split(poem.notes, start, end)
            part_variants = self._distribute_variants_for_split(poem.variants, start, end)

            split_poem = Poem(
                uid=poem.uid,  # Keep same UID for now, will be reindexed later
                volume=poem.volume,
                author=poem.author,
                title=part_title,
                poem=fragment_lines,
                preface=poem.preface if part_num == 1 else None,
                notes=part_notes,
                variants=part_variants,
            )
            split_poems.append(split_poem)

        return split_poems

    def _find_marker_boundaries(self, poem_lines: List[str], markers: List[str], title: str) -> Optional[List[tuple]]:
        """
        Find split boundaries based on marker lines (first line of each part after part 1).

        Args:
            poem_lines: Normalized poem lines
            markers: List of marker strings (first line of parts 2, 3, 4, ...)
            title: Poem title (for logging)

        Returns:
            List of (start, end) tuples for each part, or None if markers not found
        """
        # Find indices where each marker appears, searching SEQUENTIALLY
        # (each marker must come after the previous one to handle duplicate markers)
        marker_indices = []
        # Start searching from line 1, not 0 - markers indicate start of parts 2, 3, etc.
        # Part 1 always starts at line 0, so marker at line 0 would incorrectly empty Part 1
        search_start = 1

        for marker_idx, marker in enumerate(markers):
            found = False
            for i in range(search_start, len(poem_lines)):
                line = poem_lines[i]
                # Match if line starts with marker (handles punctuation variations)
                if line.startswith(marker) or marker in line:
                    marker_indices.append(i)
                    search_start = i + 1  # Next marker must come after this one
                    found = True
                    break

            if not found:
                logger.debug(
                    f"Marker-based split: Could not find marker '{marker}' (#{marker_idx + 2}) "
                    f"after line {search_start} in '{title}'"
                )
                return None

        # Build boundaries: [0, marker1), [marker1, marker2), [marker2, end)
        boundaries = []
        start = 0
        for marker_idx in marker_indices:
            boundaries.append((start, marker_idx))
            start = marker_idx

        # Add final boundary
        boundaries.append((start, len(poem_lines)))

        return boundaries

    def _should_skip_format_split(self, poem: Poem, title: str, raw_poems: List[Poem]) -> bool:
        """
        Check if format-change splitting should be skipped for this poem.

        Skip if the scraper already separated multiple poems with the same title,
        indicating they're distinct works (not stacked).

        Args:
            poem: Current poem
            title: Poem title (already stripped of author prefix)
            raw_poems: All raw poems in the volume

        Returns:
            True if format splitting should be skipped
        """
        import re

        # Extract expected count from title (e.g., "二首" → 2)
        match = re.search(r'([二三四五六七八九十]+)首', title)
        if not match:
            return False

        expected_count = chinese_utils.chinese_to_number(match.group(1))

        # Need to handle both with and without author prefix in title
        count = 0
        for p in raw_poems:
            p_title = p.title
            if p_title.startswith(f"{p.author.recorded} "):
                p_title = p_title[len(p.author.recorded) + 1:]

            if p_title == title and p.author.recorded == poem.author.recorded:
                count += 1

        # If scraper gave us exactly the expected number of poems, trust it
        if count == expected_count:
            logger.debug(
                f"Format-change split SKIPPED for '{title}': "
                f"Scraper already separated {count} poems matching expected count"
            )
            return True

        return False

    def _apply_custom_splits_preprocessing(self, raw_poems: List[Poem], volume_num: int) -> List[Poem]:
        """
        Apply custom splits to poems that need special handling before auto-detection.

        This handles nested multi-part structures that need to be split first before
        being grouped with other parts.

        Args:
            raw_poems: List of raw poems
            volume_num: Volume number

        Returns:
            List with custom splits applied
        """
        result = []

        for poem in raw_poems:
            title = poem.title
            if title.startswith(f"{poem.author.recorded} "):
                title = title[len(poem.author.recorded) + 1:]

            # Check if this poem needs custom splitting
            custom_split = volume_special_cases.get_custom_split_config(
                volume_num, title, poem.author.recorded
            )

            if custom_split:
                # Normalize poem lines (split concatenated lines on sentence boundaries)
                poem_lines = chinese_utils.normalize_poem_lines(poem.poem)

                base_title = custom_split.get('base_title', title)

                # Check if using function-based, marker-based, or index-based splitting
                if 'use_function' in custom_split:
                    # NEWEST: Function-based splitting (for complex special cases)
                    func_name = custom_split['use_function']

                    # Get the function from volume_special_cases module
                    if hasattr(volume_special_cases, func_name):
                        split_func = getattr(volume_special_cases, func_name)
                        splits = split_func(poem_lines)

                        if not splits:
                            logger.warning(f"Function-based split FAILED for '{title}': {func_name} returned None")
                            result.append(poem)
                            continue

                        logger.info(f"Applying function-based split: '{title}' ({len(poem_lines)} lines → {len(splits)} parts) using {func_name}")
                    else:
                        logger.error(f"Function-based split FAILED for '{title}': Function '{func_name}' not found in volume_special_cases")
                        result.append(poem)
                        continue
                elif 'markers' in custom_split:
                    # NEW: Marker-based splitting (index-agnostic)
                    markers = custom_split['markers']
                    splits = self._find_marker_boundaries(poem_lines, markers, title)

                    if not splits:
                        logger.warning(f"Marker-based split FAILED for '{title}': Could not find all markers")
                        result.append(poem)
                        continue

                    logger.info(f"Applying marker-based split: '{title}' ({len(poem_lines)} lines → {len(splits)} parts)")
                else:
                    # OLD: Index-based splitting (backward compatibility)
                    splits = custom_split['splits']
                    logger.info(f"Applying index-based split: '{title}' ({len(poem_lines)} lines → {len(splits)} parts)")

                # Check if custom part names are provided
                custom_part_names = custom_split.get('custom_part_names')

                for part_num, (start, end) in enumerate(splits, 1):
                    if custom_part_names and part_num <= len(custom_part_names):
                        # Use custom part name
                        part_title = f"{base_title} {custom_part_names[part_num - 1]}"
                    else:
                        # Use default 其X format
                        chinese_part = chinese_utils.number_to_chinese(part_num)
                        part_title = f"{base_title} 其{chinese_part}"

                    fragment_lines = poem_lines[start:end]

                    # distribute notes and variants based on line ranges
                    part_notes = self._distribute_notes_for_split(poem.notes, start, end)
                    part_variants = self._distribute_variants_for_split(poem.variants, start, end)

                    split_poem = Poem(
                        uid=poem.uid,  # Keep same UID for now, will be reindexed later
                        volume=poem.volume,
                        author=poem.author,
                        title=part_title,
                        poem=fragment_lines,
                        preface=poem.preface if part_num == 1 else None,
                        notes=part_notes,
                        variants=part_variants,
                        part_index=part_num,
                        total_parts=len(splits),
                    )
                    result.append(split_poem)
            else:
                # Skip if scraper already separated multiple poems with same title
                if self._should_skip_format_split(poem, title, raw_poems):
                    result.append(poem)
                else:
                    auto_split_poems = self._detect_format_change_split(poem, title)
                    if auto_split_poems:
                        result.extend(auto_split_poems)
                    else:
                        result.append(poem)

        return result

    def _auto_detect_named_part_sets(self, raw_poems: List[Poem]) -> List[Poem]:
        """
        Auto-detect and merge simple named-part sets using conservative pattern matching.

        Conservative safety rules:
        - Consecutive entries only (no gaps)
        - Same author for all parts
        - Titles must match pattern: "BaseTitle X首 PartName"
        - All parts must share same base title
        - Minimum 2 parts required
        - Skip if already processed (has part_index)

        Args:
            raw_poems: List of raw poems

        Returns:
            List with auto-detected sets merged
        """
        import re

        result = []
        i = 0

        while i < len(raw_poems):
            current = raw_poems[i]

            if current.part_index:
                result.append(current)
                i += 1
                continue

            title = current.title
            author_recorded = current.author.recorded
            if title.startswith(f"{author_recorded} "):
                title = title[len(author_recorded) + 1:]

            # Patern: "BaseTitle X首 PartName" where X is a number
            # Separator can be whitespce, Chinese colon (：), or regular colon (:)
            # extract base title by finding the "數首" pattern
            match = re.search(r'^(.+[一二三四五六七八九十百千]+首)[\s：:]+(.+)$', title)

            if not match:
                # No match - not a named-part set
                result.append(current)
                i += 1
                continue

            base_title = match.group(1)
            first_part_name = match.group(2)

            # Look ahead to find consecutive poems with same base title and author
            group = [current]
            j = i + 1

            while j < len(raw_poems):
                next_poem = raw_poems[j]

                if next_poem.part_index:
                    break

                next_title = next_poem.title
                if next_title.startswith(f"{next_poem.author.recorded} "):
                    next_title = next_title[len(next_poem.author.recorded) + 1:]

                # Check if mtaches pattern and has same base/author
                next_match = re.search(r'^(.+[一二三四五六七八九十百千]+首)[\s：:]+(.+)$', next_title)

                if (next_match and
                    next_match.group(1) == base_title and
                    next_poem.author.recorded == current.author.recorded):
                    group.append(next_poem)
                    j += 1
                else:
                    # No longer consecutive - stop looking
                    break

            # Apply conservative threshold: need at least 2 parts
            if len(group) >= 2:
                logger.info(
                    f"Auto-detected named-part set: '{base_title}' "
                    f"by {current.author.recorded} ({len(group)} parts)"
                )

                # Add part markers
                for part_num, poem in enumerate(group, 1):
                    # Keep original title with grouping marker
                    new_title = f"{poem.title} __GROUP__{base_title}"

                    updated_poem = Poem(
                        uid=poem.uid,
                        volume=poem.volume,
                        author=poem.author,
                        title=new_title,
                        poem=poem.poem,
                        notes=poem.notes,
                        preface=poem.preface,
                        part_index=part_num,
                        total_parts=len(group),
                        variants=poem.variants
                    )
                    result.append(updated_poem)
                    logger.debug(f"  Part {part_num}/{len(group)}: {poem.title}")

                i = j  # Skip past all merged poems
            else:
                # Single poem, not a set
                result.append(current)
                i += 1

        return result

    def process_volume(self, volume_num: int) -> List[Poem]:
        """
        Process a single volume's raw JSON and apply splits.

        Args:
            volume_num: Volume number to process

        Returns:
            List of processed Poem objects
        """
        raw_file = self.raw_dir / f"volume_{volume_num:03d}.json"

        if not raw_file.exists():
            logger.warning(f"Raw file not found: {raw_file}")
            return []

        logger.info(f"Processing volume {volume_num} from {raw_file}")

        with open(raw_file, 'r', encoding='utf-8') as f:
            raw_poems_data = json.load(f)

        # Convert to Poem objects
        raw_poems = [Poem.from_dict(data) for data in raw_poems_data]

        # Validate author names and output warnings
        self._validate_author_names(raw_poems, volume_num)

        raw_poems = self._preprocess_merges(raw_poems, volume_num)
        raw_poems = self._fix_parent_title_duplicates(raw_poems)
        raw_poems = self._apply_custom_splits_preprocessing(raw_poems, volume_num)  # Split nested structures first
        raw_poems = self._merge_consecutive_multipart_poems(raw_poems)
        raw_poems = self._merge_seasonal_sets(raw_poems, volume_num)
        raw_poems = self._auto_detect_named_part_sets(raw_poems)  # Auto-detect remaining sets

        processed_poems = []
        entry_index = 0

        # Track titles for multi-part labeling (volumes 8, 13, 14)
        # Maps title -> (entry_index, part_counter)
        title_entries = {}

        # Special tracking for volume 8 句 collection (all share same entry_index)
        ju_collection_entry_index = None
        ju_collection_part_counter = 0
        ju_collection_total_parts = None  # Will be set after we count them
        ju_collection_all_notes = None  # All notes from first fragment, to be redistributed

        # Pre-scan volume 8 to count 句 collection poems and collect all fragments
        ju_collection_fragments = []
        if volume_num == 8:
            ju_poems = [
                p for p in raw_poems
                if volume_special_cases.is_volume_8_ju_collection_poem(p.title, p.author.recorded)
            ]
            if ju_poems:
                ju_collection_total_parts = len(ju_poems)
                ju_collection_fragments = ju_poems
                # Collect all notes from first fragment
                ju_collection_all_notes = ju_poems[0].notes if ju_poems[0].notes else []
                logger.info(f"Detected 句 collection with {len(ju_poems)} parts, {len(ju_collection_all_notes)} total notes")

        for raw_poem in raw_poems:
            raw_poem.poem = chinese_utils.normalize_poem_lines(raw_poem.poem)
            title = raw_poem.title

            # titles like "白居易 續古詩十首 一" need to become "續古詩十首 一"
            # so  base title extraction works correctly
            author_recorded = raw_poem.author.recorded
            if title.startswith(f"{author_recorded} "):
                title = title[len(author_recorded) + 1:]
                raw_poem.title = title  # Update raw_poem to reflect stripped title

            # Apply title rewrites first
            rewritten_title = volume_special_cases.apply_title_rewrite(volume_num, title)
            if rewritten_title != title:
                logger.debug(f"Title rewrite: '{title}' -> '{rewritten_title}'")
                title = rewritten_title
                raw_poem.title = title

            # Apply Specific Couplet Fixes
            self._apply_text_fixes(raw_poem, volume_num)

            # Check if this is part of volume 8 句 collection
            if (volume_num == 8 and
                volume_special_cases.is_volume_8_ju_collection_poem(title, raw_poem.author.recorded)):

                # Assign  shared entry_index for all 句 poems
                if ju_collection_entry_index is None:
                    entry_index += 1
                    ju_collection_entry_index = entry_index
                    logger.info(f"Starting 句 collection at entry_index {ju_collection_entry_index}")

                ju_collection_part_counter += 1

                # redistribute notes from the collected pool based on context matching
                fragment_notes = self._match_notes_to_fragment(
                    ju_collection_all_notes, raw_poem.poem
                )

                # Create processed poem with shared entry_index
                processed_poem = Poem(
                    uid=uid_generator.generate_uid(
                        volume_num, ju_collection_entry_index, ju_collection_part_counter
                    ),
                    volume=volume_num,
                    author=raw_poem.author,
                    title=title,
                    poem=raw_poem.poem,
                    notes=fragment_notes,
                    preface=raw_poem.preface,
                    part_index=ju_collection_part_counter,
                    total_parts=ju_collection_total_parts,
                    variants=raw_poem.variants
                )
                processed_poems.append(processed_poem)
                logger.debug(
                    f"  句 collection part {ju_collection_part_counter}: {title} -> "
                    f"{processed_poem.uid} ({len(fragment_notes) if fragment_notes else 0} notes)"
                )
                continue

            # Check if this poem was already split in preprocessing
            # Pre-split poems have part_index set from preprocessing
            if raw_poem.part_index is not None:
                # This is a pre-split poem - assign UID based on part_index
                if raw_poem.part_index == 1:
                    # First part of a pre-split set - assign new entry_index
                    entry_index += 1
                    presplit_entry_index = entry_index
                # else: use the entry_index from the first part (already set)

                # Strip __GROUP__ marker from title if present (from named-part sets)
                clean_title = raw_poem.title
                group_match = re.search(r'^(.*?)\s+__GROUP__(.+)$', clean_title)
                if group_match:
                    clean_title = group_match.group(1).strip()

                processed_poem = Poem(
                    uid=uid_generator.generate_uid(volume_num, entry_index, part_index=raw_poem.part_index),
                    volume=volume_num,
                    author=raw_poem.author,
                    title=clean_title,
                    poem=raw_poem.poem,
                    notes=raw_poem.notes,
                    preface=raw_poem.preface,
                    part_index=raw_poem.part_index,
                    total_parts=raw_poem.total_parts,
                    variants=raw_poem.variants
                )
                processed_poems.append(processed_poem)
                continue

            # Check if this poem has a custom split configuration
            custom_split = volume_special_cases.get_custom_split_config(
                volume_num, title, raw_poem.author.recorded
            )
            if custom_split:
                # split according to custom configuration
                entry_index += 1
                split_poems = self._split_custom_poem(
                    raw_poem, custom_split, volume_num, entry_index
                )
                processed_poems.extend(split_poems)
                continue

            # Check Volume 16 custom splits
            if volume_num == 16:
                has_part_marker = bool(re.search(r'\s+(其|第)?([一二三四五六七八九十]+)$', title))
                if not has_part_marker:
                    # Check if this poem matches a custom split configuration
                    custom_split_applied = False
                    for config in volume_special_cases.VOLUME_16_MULTISONG_SPLITS:
                        if config['title_pattern'] not in title:
                            continue
                        if len(raw_poem.poem) != config['line_count']:
                            continue
                        if 'author' in config and raw_poem.author.recorded != config['author']:
                            continue

                        # Found a match - split this poem
                        entry_index += 1
                        split_poems = self._split_multisong_poem(
                            raw_poem, config['num_songs'], volume_num, entry_index
                        )
                        processed_poems.extend(split_poems)
                        logger.debug(f"Applied Volume 16 custom split for '{title}'")
                        custom_split_applied = True
                        break

                    # Skip to next poem if we applied a custom split
                    if custom_split_applied:
                        continue

            # check custom splits for hardcoded volumes (21-26, 85, 98, 218, 220-224)
            # These volumes use only custom split configurations to avoid edge cases
            if volume_num in [21, 22, 23, 24, 25, 26, 85, 98, 218, 220, 221, 222, 223, 224]:
                # Map volume numbers to their configuration lists
                volume_configs = {
                    21: volume_special_cases.VOLUME_21_MULTISONG_SPLITS,
                    22: volume_special_cases.VOLUME_22_MULTISONG_SPLITS,
                    23: volume_special_cases.VOLUME_23_MULTISONG_SPLITS,
                    24: volume_special_cases.VOLUME_24_MULTISONG_SPLITS,
                    25: volume_special_cases.VOLUME_25_MULTISONG_SPLITS,
                    26: volume_special_cases.VOLUME_26_MULTISONG_SPLITS,
                    85: volume_special_cases.VOLUME_85_MULTISONG_SPLITS,
                    98: volume_special_cases.VOLUME_98_MULTISONG_SPLITS,
                    218: volume_special_cases.VOLUME_218_MULTISONG_SPLITS,
                    220: volume_special_cases.VOLUME_220_MULTISONG_SPLITS,
                    221: volume_special_cases.VOLUME_221_MULTISONG_SPLITS,
                    222: volume_special_cases.VOLUME_222_MULTISONG_SPLITS,
                    223: volume_special_cases.VOLUME_223_MULTISONG_SPLITS,
                    224: volume_special_cases.VOLUME_224_MULTISONG_SPLITS,
                }

                custom_split_applied, split_poems, entry_index = self._check_and_apply_custom_split(
                    raw_poem, volume_num, entry_index, volume_configs[volume_num], title
                )

                if custom_split_applied:
                    processed_poems.extend(split_poems)
                    continue

            # Check if this is a multi-song poem (all volumes)
            # Volumes with custom configs (21-26, 85, 98, 218, 220-224) are handled above first
            # If no custom config matches, they fall through to here for safe auto-split
            # Matches patterns like: "續古詩十首 一", "帝京篇十首 其一", "望廬山瀑布水 第一"
            has_part_marker = bool(re.search(r'\s+(其|第)?([一二三四五六七八九十]+)$', title))
            # Also skip if raw data already has part_index set (scraper already split it)
            already_split = raw_poem.part_index is not None
            # Skip if poem has skip_autosplit hint (e.g., bio note indicates single poem corpus)
            has_skip_autosplit = raw_poem.notes and any(
                isinstance(note, dict) and note.get('type') == 'skip_autosplit'
                for note in raw_poem.notes
            )
            # Find all occurrences and use the LAST one (rightmost in title)
            # This handles titles like "子夜四時歌六首·春歌二首" where we want "二首" not "六首"
            multi_song_matches = re.findall(r'([二三四五六七八九十]+)首', title)
            num_songs = None

            if multi_song_matches and not has_part_marker and not already_split and not has_skip_autosplit:
                chinese_nums = {'二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                # Use the last (rightmost) match
                num_songs = chinese_nums.get(multi_song_matches[-1])
            elif volume_num == 19 and '輓歌' in title and len(raw_poem.poem) == 4:
                if raw_poem.poem[0].startswith('草草門巷喧'):
                    num_songs = 2

            if num_songs:
                # Before splitting, check if scraper already separated this many poems
                # Count poems with same title + author in raw_poems
                stripped_title = title
                if stripped_title.startswith(f"{raw_poem.author.recorded} "):
                    stripped_title = stripped_title[len(raw_poem.author.recorded) + 1:]

                count = sum(
                    1 for p in raw_poems
                    if ((p.title == raw_poem.title) or
                        (p.title.startswith(f"{p.author.recorded} ") and
                         p.title[len(p.author.recorded) + 1:] == stripped_title))
                    and p.author.recorded == raw_poem.author.recorded
                )

                if count == num_songs:
                    # Scraper already separated - skip splitting, just process normally
                    logger.debug(
                        f"Multisong split SKIPPED for '{title}': "
                        f"Scraper already separated {count} poems matching expected count"
                    )
                else:
                    # Split multi-song poem - all songs share the same entry_index
                    entry_index += 1
                    split_poems = self._split_multisong_poem(
                        raw_poem, num_songs, volume_num, entry_index
                    )

                    # If split was rejected (returned single poem), assign proper UID
                    # to avoid collision with next entry
                    if len(split_poems) == 1 and split_poems[0].uid == raw_poem.uid:
                        # Split was rejected, poem kept original UID from raw data
                        # Assign new UID with current entry_index to maintain sequential ordering
                        rejected_poem = Poem(
                            uid=uid_generator.generate_uid(volume_num, entry_index, 1),
                            volume=split_poems[0].volume,
                            author=split_poems[0].author,
                            title=split_poems[0].title,
                            poem=split_poems[0].poem,
                            notes=split_poems[0].notes,
                            preface=split_poems[0].preface,
                            part_index=None,
                            total_parts=None,
                            variants=split_poems[0].variants
                        )
                        processed_poems.append(rejected_poem)
                    else:
                        processed_poems.extend(split_poems)
                    continue

            # Check if this needs part numbering (volumes 8, 13, 14)
            num_parts = volume_special_cases.is_multipart_poem(volume_num, title)
            if num_parts > 0:
                # Multi-part poems with same title share the same entry_index
                if title not in title_entries:
                    entry_index += 1
                    title_entries[title] = [entry_index, 0]  # [entry_index, part_counter]

                title_entries[title][1] += 1
                part_num = title_entries[title][1]
                poem_entry_index = title_entries[title][0]

                chinese_num = chinese_utils.number_to_chinese(part_num)
                new_title = f"{title} 其{chinese_num}"

                processed_poem = Poem(
                    uid=uid_generator.generate_uid(volume_num, poem_entry_index, part_num),
                    volume=volume_num,
                    author=raw_poem.author,
                    title=new_title,
                    poem=raw_poem.poem,
                    notes=raw_poem.notes,
                    preface=raw_poem.preface,
                    part_index=part_num,
                    total_parts=num_parts,
                    variants=raw_poem.variants
                )
                processed_poems.append(processed_poem)
                continue

            # Check if this is part of a temple music set (Volume 13 special handling)
            temple_music_base_title = None
            temple_music_part_num = None
            if volume_num == 13:
                temple_configs = volume_special_cases.get_named_part_sets(13)
                for config in temple_configs:
                    if (raw_poem.author.recorded == config['author'] and
                        title.startswith(config['base_title'])):
                        # Extract the part number from patterns like "第三登歌", "第四迎神", etc.
                        for i, pattern in enumerate(config['part_patterns'], start=1):
                            if title.endswith(pattern):
                                temple_music_base_title = config['base_title']
                                temple_music_part_num = i
                                break
                        if temple_music_base_title:
                            break

            # Check if title has a grouping marker (for named part sets)
            # Format: "original title __GROUP__base_title"
            group_match = re.search(r'^(.*?)\s+__GROUP__(.+)$', title)
            if group_match:
                original_title = group_match.group(1).strip()
                group_base_title = group_match.group(2).strip()
                # Use the part_index and total_parts that were set during merge
                part_num = raw_poem.part_index
                total_parts = raw_poem.total_parts

                if group_base_title not in title_entries:
                    entry_index += 1
                    title_entries[group_base_title] = [entry_index, total_parts, total_parts]

                poem_entry_index = title_entries[group_base_title][0]

                processed_poem = Poem(
                    uid=uid_generator.generate_uid(volume_num, poem_entry_index, part_num),
                    volume=volume_num,
                    author=raw_poem.author,
                    title=original_title,  # Use original title without __GROUP__ marker
                    poem=raw_poem.poem,
                    notes=raw_poem.notes,
                    preface=raw_poem.preface,
                    part_index=part_num,
                    total_parts=total_parts,
                    variants=raw_poem.variants
                )
                processed_poems.append(processed_poem)
                logger.debug(f"Grouped poem: '{original_title}' -> entry={poem_entry_index}, part={part_num}")
                continue

            # Check if this is part of a seasonal set (special handling for base title extraction)
            seasonal_base_title = None
            if volume_num == 21:
                seasonal_configs = volume_special_cases.get_named_part_sets(21)
                for config in seasonal_configs:
                    if (raw_poem.author.recorded == config['author'] and
                        title.startswith(config['base_title'])):
                        # Use the configured base_title + author for unique grouping
                        # This ensures different authors' seasonal sets don't share entry_index
                        seasonal_base_title = f"{config['base_title']}_{config['author']}"
                        break

            # Check if title already has part markers (其一, 第一, or just 一, 二)
            # These  were added during scraping and need to be merged with same entry_index
            # Handle temple music sets first (Volume 13) as they have complex patterns
            if temple_music_base_title and temple_music_part_num:
                base_title = temple_music_base_title
                part_num = temple_music_part_num
                part_marker_match = True  # Flag to indicate we found a match
            else:
                part_marker_match = re.search(r'(.*?)\s+(其|第)?([一二三四五六七八九十]+)$', title)
                if part_marker_match:
                    base_title = part_marker_match.group(1).strip()
                    part_marker = part_marker_match.group(3)

                    # Override base_title with seasonal base if this is part of a seasonal set
                    if seasonal_base_title:
                        base_title = seasonal_base_title

                    # Convert Chinese number to integer
                    part_num = chinese_utils.chinese_to_number(part_marker)
                else:
                    part_num = 0  # No match found

            if part_marker_match and part_num > 0:
                # This is a multi-part poem - track by base title
                if base_title not in title_entries:
                    entry_index += 1
                    title_entries[base_title] = [entry_index, 0, 0]  # [entry_index, max_part_seen, total_parts]

                poem_entry_index = title_entries[base_title][0]

                # update max part number seen
                if part_num > title_entries[base_title][1]:
                    title_entries[base_title][1] = part_num

                # Total parts will be finalized later, use max for now
                total_parts = title_entries[base_title][1]

                # Normalize title format: always use "其" (qi) for part markers
                # "帝京篇十首 一" -> "帝京篇十首 其一"
                # "帝京篇十首 第一" -> "帝京篇十首 其一"
                chinese_part = chinese_utils.number_to_chinese(part_num)
                normalized_title = f"{base_title} 其{chinese_part}"

                processed_poem = Poem(
                    uid=uid_generator.generate_uid(volume_num, poem_entry_index, part_num),
                    volume=volume_num,
                    author=raw_poem.author,
                    title=normalized_title,  # Use normalized title with 其 marker
                    poem=raw_poem.poem,
                    notes=raw_poem.notes,
                    preface=raw_poem.preface,
                    part_index=part_num,
                    total_parts=total_parts,
                    variants=raw_poem.variants
                )
                processed_poems.append(processed_poem)

                logger.debug(f"Detected existing part marker: '{title}' -> normalized to '{normalized_title}', entry={poem_entry_index}")
                continue

            # Regular poem - just regenerate UID
            entry_index += 1
            processed_poem = Poem(
                uid=uid_generator.generate_uid(volume_num, entry_index, part_index=1),
                volume=volume_num,
                author=raw_poem.author,
                title=raw_poem.title,
                poem=raw_poem.poem,
                notes=raw_poem.notes,
                preface=raw_poem.preface,
                part_index=raw_poem.part_index,
                total_parts=raw_poem.total_parts,
                variants=raw_poem.variants
            )
            processed_poems.append(processed_poem)

        # Apply cleanup post-processing (remove asterisks, author prefixes, biography entries, stubs)
        # This includes UID reindexing, so we need to finalize total_parts AFTER this
        processed_poems = self._apply_cleanup_postprocessing(processed_poems, volume_num)

        # Finalize total_parts for multi-part poems AFTER cleanup/reindexing
        # This ensures total_parts is based on final UIDs, not pre-cleanup indices
        processed_poems = self._finalize_total_parts(processed_poems)

        # Strip redundant "其一" suffix from single-part poems AFTER total_parts is finalized
        # This ensures we only strip when we KNOW total_parts is actually 1
        processed_poems = self._strip_redundant_part_suffix(processed_poems)

        logger.info(
            f"Volume {volume_num}: {len(raw_poems)} raw poems -> "
            f"{len(processed_poems)} processed poems"
        )
        return processed_poems

    def _finalize_total_parts(self, poems: List[Poem]) -> List[Poem]:
        """
        Finalize total_parts for multi-part poems.

        After cleanup and reindexing, rebuild total_parts based on current UIDs.
        Groups poems by entry_index and sets total_parts to max part_index in each group.

        Args:
            poems: List of processed poems (after cleanup and reindexing)

        Returns:
            Updated list of poems with correct total_parts
        """
        # Group poems by entry_index and find max part_index for each
        # entry_index -> max_part_index
        entry_totals = {}

        for poem in poems:
            # Extract entry_index from UID (format: QTS_VVV_EEE_PP)
            uid_parts = poem.uid.split('_')
            if len(uid_parts) >= 4:
                try:
                    entry_idx = int(uid_parts[2])
                    part_idx = int(uid_parts[3])

                    # Track max part_index for this entry
                    if entry_idx not in entry_totals:
                        entry_totals[entry_idx] = part_idx
                    else:
                        entry_totals[entry_idx] = max(entry_totals[entry_idx], part_idx)
                except (ValueError, IndexError):
                    pass

        # Update all poems with matching entry_index
        updated_poems = []
        for poem in poems:
            # Extract entry_index from UID (format: QTS_VVV_EEE_PP)
            uid_parts = poem.uid.split('_')
            if len(uid_parts) >= 4:
                try:
                    entry_idx = int(uid_parts[2])
                    if entry_idx in entry_totals:
                        final_total = entry_totals[entry_idx]

                        # Only  set total_parts for multi-part poems (total > 1)
                        if final_total > 1 and poem.total_parts != final_total:
                            logger.debug(
                                f"Finalizing total_parts for {poem.uid}: "
                                f"{poem.total_parts} -> {final_total}"
                            )
                            # Create updated poem with correct total_parts
                            poem = Poem(
                                uid=poem.uid,
                                volume=poem.volume,
                                author=poem.author,
                                title=poem.title,
                                poem=poem.poem,
                                notes=poem.notes,
                                preface=poem.preface,
                                part_index=poem.part_index,
                                total_parts=final_total,
                                variants=poem.variants
                            )
                except (ValueError, IndexError):
                    pass

            updated_poems.append(poem)

        return updated_poems

    def _correct_note_line_numbers(self, notes: Optional[List], poem_lines: List[str]) -> Optional[List]:
        """
        Correct note line numbers to be relative to the current poem.

        Notes may have line numbers from the original source that don't match
        the current structure. This method uses the "context" field to find
        the actual line and corrects the line number.

        Args:
            notes: List of notes (can be strings or dicts)
            poem_lines: Lines of the current poem

        Returns:
            Notes with corrected line numbers
        """
        if not notes:
            return None

        corrected = []
        for note in notes:
            if isinstance(note, str):
                corrected.append(note)
                continue

            if isinstance(note, dict) and 'line' in note and 'context' in note:
                # Find the line that matches the context
                context = note['context']
                corrected_line = None

                for i, line in enumerate(poem_lines, 1):
                    if context in line or line in context:
                        corrected_line = i
                        break

                if corrected_line is not None:
                    # Create a copy with corrected line number
                    corrected_note = note.copy()
                    if corrected_note['line'] != corrected_line:
                        logger.debug(
                            f"Correcting note line number: {corrected_note['line']} -> "
                            f"{corrected_line} (context: {context[:30]}...)"
                        )
                        corrected_note['line'] = corrected_line
                    corrected.append(corrected_note)
                else:
                    # Context not found, keep original note but log warning
                    logger.warning(
                        f"Could not find context '{context[:30]}...' in poem lines, "
                        f"keeping original line number {note['line']}"
                    )
                    corrected.append(note)
            else:
                # Unknown format or missing fields, keep as-is
                corrected.append(note)

        return corrected if corrected else None

    def _match_notes_to_fragment(self, all_notes: Optional[List], fragment_lines: List[str]) -> Optional[List]:
        """
        Match notes to a specific fragment based on context field.

        This is used for collections like Volume 8 句 where all notes are collected
        from the first fragment and need to be redistributed to the correct fragments.

        Args:
            all_notes: All notes from the entire collection
            fragment_lines: Lines of the current fragment

        Returns:
            Notes that match this fragment with corrected line numbers, or None
        """
        if not all_notes:
            return None

        matched = []
        for note in all_notes:
            # Handle string notes - skip them as they don't have context
            if isinstance(note, str):
                continue

            # Handle dict notes with context field
            if isinstance(note, dict) and 'context' in note:
                context = note['context']
                matched_line = None

                for i, line in enumerate(fragment_lines, 1):  # 1-based
                    if context in line or line in context:
                        matched_line = i
                        break

                if matched_line is not None:
                    # This note belongs to this fragment
                    matched_note = note.copy()
                    matched_note['line'] = matched_line
                    matched.append(matched_note)
                    logger.debug(
                        f"Matched note to fragment: context='{context[:30]}...' -> line {matched_line}"
                    )

        return matched if matched else None

    def _redistribute_notes(self, notes: Optional[List], start_line: int, end_line: int) -> Optional[List]:
        """
        Redistribute notes for a poem split based on line ranges.

        Notes can be either strings or dicts with 'line', 'content', 'context' fields.
        When notes are dicts, the 'line' field (1-based) indicates which line they reference.

        Args:
            notes: Original notes list (can be strings or dicts)
            start_line: Starting line index (0-based, inclusive) for this part
            end_line: Ending line index (0-based, exclusive) for this part

        Returns:
            Filtered and adjusted notes for this part, or None if no notes
        """
        if not notes:
            return None

        redistributed = []

        for note in notes:
            # Handle string notes - they don't have line references, so include in all parts
            if isinstance(note, str):
                redistributed.append(note)
                continue

            # handle dict notes with line references
            if isinstance(note, dict) and 'line' in note:
                # Line numbers in notes are 1-based
                note_line_idx = note['line'] - 1  # Convert to 0-based

                # Check if this note's line falls within this part's range
                if start_line <= note_line_idx < end_line:
                    # Adjust line number to be relative to this part
                    adjusted_note = note.copy()
                    adjusted_note['line'] = note_line_idx - start_line + 1  # Back to 1-based
                    redistributed.append(adjusted_note)
            else:
                # Unknown format, include it to be safe
                redistributed.append(note)

        return redistributed if redistributed else None

    def _split_custom_poem(self, raw_poem: Poem, split_config: dict,
                          volume_num: int, entry_index: int) -> List[Poem]:
        """
        Split a poem according to custom split configuration.

        Args:
            raw_poem: Original Poem object
            split_config: Split configuration dict with 'splits'/'markers'/'use_function' and optional 'base_title'
            volume_num: Volume number
            entry_index: Entry index for UID generation (shared across all parts)

        Returns:
            List of split Poem objects
        """
        base_title = split_config.get('base_title', raw_poem.title)
        poem_lines = self._normalize_poem_lines(raw_poem.poem)

        if 'use_function' in split_config:
            # Function-based splitting
            func_name = split_config['use_function']
            if hasattr(volume_special_cases, func_name):
                split_func = getattr(volume_special_cases, func_name)
                splits = split_func(poem_lines)
                if not splits:
                    logger.warning(f"Function-based split FAILED for '{raw_poem.title}': {func_name} returned None")
                    return [raw_poem]
            else:
                logger.error(f"Function-based split FAILED for '{raw_poem.title}': Function '{func_name}' not found")
                return [raw_poem]
        elif 'markers' in split_config:
            # Marker-based splitting
            markers = split_config['markers']
            splits = self._find_marker_boundaries(poem_lines, markers, raw_poem.title)
            if not splits:
                logger.warning(f"Marker-based split FAILED for '{raw_poem.title}': Could not find all markers")
                return [raw_poem]
        else:
            # Index-based splitting (backward compatibility)
            splits = split_config['splits']

        logger.info(
            f"Applying custom split for '{raw_poem.title}' by {raw_poem.author.recorded}: "
            f"{len(splits)} parts"
        )

        # Check if custom part names are provided
        custom_part_names = split_config.get('custom_part_names')

        result = []
        for part_num, (start, end) in enumerate(splits, 1):
            if custom_part_names and part_num <= len(custom_part_names):
                # Use custom part name
                part_title = f"{base_title} {custom_part_names[part_num - 1]}"
            else:
                # Use default 其X format
                part_title = f"{base_title} 其{chinese_utils.number_to_chinese(part_num)}"

            part_lines = poem_lines[start:end]

            # Redistribute notes and variants based on line ranges
            part_notes = self._redistribute_notes(raw_poem.notes, start, end)
            part_variants = self._distribute_variants_for_split(raw_poem.variants, start, end)

            processed_poem = Poem(
                uid=uid_generator.generate_uid(volume_num, entry_index, part_index=part_num),
                volume=volume_num,
                author=raw_poem.author,
                title=part_title,
                poem=part_lines,
                notes=part_notes,
                preface=raw_poem.preface if part_num == 1 else None,  # Preface only on first part
                part_index=part_num,
                total_parts=len(splits),
                variants=part_variants
            )
            result.append(processed_poem)

            logger.debug(
                f"  Part {part_num}: lines {start}-{end}, "
                f"notes={len(part_notes) if part_notes else 0}"
            )

        return result

    def _apply_text_fixes(self, raw_poem: Poem, volume_num: int):
            """
            Applies manual text fixes defined in volume_special_cases.
            Modifies raw_poem.poem in place.
            """
            fixes = volume_special_cases.get_couplet_fix(volume_num, raw_poem.title)
            if not fixes:
                return

            current_lines = raw_poem.poem

            for fix in fixes:
                target = fix['target']
                replacement = fix['replacement']
                target_len = len(target)

                i = 0
                while i <= len(current_lines) - target_len:
                    # Check if current slice matches target
                    if current_lines[i : i + target_len] == target:
                        logger.info(f"Applying text fix for {raw_poem.title}: Merging lines {i}-{i+target_len}")

                        # Replace the slice with the single replacement string
                        current_lines[i : i + target_len] = [replacement]

                        # Since we modified the list length, we continue from current index
                        # (In case the same pattern repeats, though unlikely here)
                        continue
                    i += 1

            raw_poem.poem = current_lines

    def _normalize_poem_lines(self, poem_lines: List[str]) -> List[str]:
        """
        Normalize poem lines by splitting single-paragraph poems into multiple lines.
        Handles。！？punctuation marks as sentence endings.

        Args:
            poem_lines: Original poem lines

        Returns:
            Normalized list of poem lines
        """
        # If already multiple paragraphs, return as-is
        if len(poem_lines) != 1:
            return poem_lines

        single_para = poem_lines[0]
        lines = []

        # Split on。！？while preserving the punctuation
        sentences = re.split(r'([。！？])', single_para)
        i = 0
        while i < len(sentences):
            sentence = sentences[i].strip()
            # Attach punctuation mark to the sentence
            if i + 1 < len(sentences) and sentences[i+1] in '。！？':
                sentence += sentences[i+1]
                i += 2
            else:
                i += 1
            # Only add non-empty sentences (and skip standalone punctuation)
            if sentence and sentence not in '。！？':
                lines.append(sentence)

        return lines

    def _check_line_length_uniformity(self, poem_lines: List[str], tolerance: int = 1) -> bool:
        """
        Check if all lines are roughly the same character length.

        This detects mixed-form poems (e.g., 5-char vs 7-char lines) which are typically
        Yuefu (樂府), Ci (詞), or Gexing (歌行) forms that shouldn't be auto-split.

        Args:
            poem_lines: List of poem lines
            tolerance: Allow ±N character difference (for punctuation variance)

        Returns:
            bool: True if uniform (safe to split), False if mixed lengths
        """
        if not poem_lines:
            return False

        # Strip punctuation and measure actual content length
        lengths = []
        for line in poem_lines:
            # Remove common Chinese punctuation
            clean_line = re.sub(r'[，。！？、；：]', '', line)
            lengths.append(len(clean_line))

        if not lengths:
            return False

        min_len = min(lengths)
        max_len = max(lengths)

        # If difference > tolerance, it's mixed (5-char vs 7-char, etc.)
        is_uniform = (max_len - min_len) <= tolerance

        if not is_uniform:
            logger.debug(f"Line length variance detected: min={min_len}, max={max_len} (mixed form poem)")

        return is_uniform

    def _is_safe_to_autosplit(self, poem_lines: List[str], num_songs: int, title: str) -> bool:
        """
        Check if a poem is safe to auto-split using geometric division.

        Only auto-split poems that are structurally unambiguous:
        - Evenly divisible
        - Standard form lengths (2, 4, 8, 12, 16 lines per part)
        - Uniform line lengths (no mixed 5-char/7-char)

        This prevents corruption of irregular forms like Yuefu, Gexing, etc.

        Args:
            poem_lines: List of poem lines
            num_songs: Number of songs to split into
            title: Poem title (for logging)

        Returns:
            bool: True if safe to auto-split, False otherwise
        """
        total_lines = len(poem_lines)

        # Check 1: Divisibility
        if total_lines % num_songs != 0:
            logger.debug(
                f"Auto-split SKIPPED for '{title}': "
                f"{total_lines} lines not evenly divisible by {num_songs}"
            )
            return False

        lines_per_part = total_lines // num_songs

        # Check 2: Standard form length
        # Only auto-split standard Tang Dynasty forms:
        # - 2 lines: Couplets (對聯)
        # - 4 lines: Jueju (絕句)
        # - 8 lines: Lushi (律詩)
        # - 12 lines: Extended Lushi (排律/長律)
        # - 16 lines: Extended Lushi (排律)
        SAFE_LENGTHS = {2, 4, 8, 12, 16}

        if lines_per_part not in SAFE_LENGTHS:
            logger.debug(
                f"Auto-split SKIPPED for '{title}': "
                f"{lines_per_part} lines per part is not a standard form "
                f"(expected: {sorted(SAFE_LENGTHS)})"
            )
            return False

        # Check 3: Line length uniformity
        if not self._check_line_length_uniformity(poem_lines):
            logger.debug(
                f"Auto-split SKIPPED for '{title}': "
                f"Mixed line lengths detected (likely Yuefu/Gexing/Ci irregular form)"
            )
            return False

        # All checks passed - safe to auto-split
        logger.info(
            f"Auto-split SAFE for '{title}': "
            f"{total_lines} lines → {num_songs} parts × {lines_per_part} lines "
            f"(standard form, uniform lengths)"
        )
        return True

    def _check_and_apply_custom_split(self, raw_poem: Poem, volume_num: int, entry_index: int,
                                      custom_splits_config: list, title: str) -> tuple:
        """
        Check if a poem matches custom split configuration and apply if found.

        Args:
            raw_poem: The poem to check
            volume_num: Volume number
            entry_index: Current entry index (will be incremented if split is applied)
            custom_splits_config: List of custom split configurations for this volume
            title: Poem title

        Returns:
            Tuple of (custom_split_applied: bool, split_poems: List[Poem], new_entry_index: int)
        """
        # Check for part markers - skip if already has them (其一, 第一, or bare 一, 二, 三)
        has_part_marker = bool(re.search(r'\s+(其|第)?([一二三四五六七八九十]+)$', title))
        if has_part_marker:
            return False, [], entry_index

        # Normalize single-paragraph poems for line count check
        poem_lines = self._normalize_poem_lines(raw_poem.poem)

        # Check if this poem matches a custom split configuration
        for config in custom_splits_config:
            if config['title_pattern'] not in title:
                continue
            if len(poem_lines) != config['line_count']:
                continue
            if 'author' in config and raw_poem.author.recorded != config['author']:
                continue

            # Found a match - split this poem
            entry_index += 1
            split_poems = self._split_multisong_poem(
                raw_poem, config['num_songs'], volume_num, entry_index
            )
            logger.debug(f"Applied Volume {volume_num} custom split for '{title}'")
            return True, split_poems, entry_index

        return False, [], entry_index

    def _split_multisong_poem(self, raw_poem: Poem, num_songs: int,
                             volume_num: int, entry_index: int) -> List[Poem]:
        """
        Split a multi-song poem into separate poems.

        Args:
            raw_poem: Original Poem object
            num_songs: Number of songs to split into
            volume_num: Volume number
            entry_index: Entry index for UID generation (shared across all songs)

        Returns:
            List of split Poem objects
        """
        title = raw_poem.title
        author = raw_poem.author.canonical
        poem_lines = self._normalize_poem_lines(raw_poem.poem)

        # Get split configuration using registry
        splits = volume_special_cases.get_multisong_split(volume_num, title, author, poem_lines, num_songs)

        # Fallback to safe auto-split if no config found
        if not splits:
            logger.debug(f"No split config found for '{title}', attempting safe auto-split")

            # Check if safe to auto-split using our heuristic
            if self._is_safe_to_autosplit(poem_lines, num_songs, title):
                # Safe to split evenly
                lines_per_song = len(poem_lines) // num_songs
                splits = []
                for i in range(num_songs):
                    start = i * lines_per_song
                    end = start + lines_per_song if i < num_songs - 1 else len(poem_lines)
                    splits.append(poem_lines[start:end])
                logger.info(
                    f"Auto-split applied to '{title}': "
                    f"{len(poem_lines)} lines → {num_songs} parts × {lines_per_song} lines"
                )
            else:
                # Not safe to auto-split - skip splitting
                logger.warning(
                    f"Auto-split REJECTED for '{title}' ({author}): "
                    f"Failed safety checks (not a standard form or irregular structure). "
                    f"Manual configuration required. Keeping as single poem."
                )
                # Return the original poem unsplit
                return [raw_poem]

        # Create separate poem entries - all share the same entry_index
        result = []
        for song_num, song_lines in enumerate(splits, 1):
            song_title = f"{title} 其{chinese_utils.number_to_chinese(song_num)}"

            # Strip markers like （第一拍）, （第二拍）, etc. from 胡笳十八拍 poems
            if volume_num == 23 and '胡笳十八拍' in title and author == '劉商':
                if song_lines:
                    # Remove （第N拍） marker from the beginning of the first line
                    if song_lines[0]:
                        first_line = song_lines[0]
                        # Match （第[一二三四五六七八九十百]+拍）at the start
                        marker_match = re.match(r'^[（(]第[一二三四五六七八九十百]+拍[）)]', first_line)
                        if marker_match:
                            song_lines = [first_line[marker_match.end():]] + song_lines[1:]

                    # Remove （第N拍） marker from the end of the last line
                    if song_lines and song_lines[-1]:
                        last_line = song_lines[-1]
                        # Match （第[一二三四五六七八九十百]+拍）at the end
                        marker_match = re.search(r'[（(]第[一二三四五六七八九十百]+拍[）)]$', last_line)
                        if marker_match:
                            cleaned_last_line = last_line[:marker_match.start()]
                            # If the cleaned line is empty, remove it; otherwise replace it
                            if cleaned_last_line.strip():
                                song_lines = song_lines[:-1] + [cleaned_last_line]
                            else:
                                song_lines = song_lines[:-1]

            processed_poem = Poem(
                uid=uid_generator.generate_uid(volume_num, entry_index, part_index=song_num),
                volume=volume_num,
                author=raw_poem.author,
                title=song_title,
                poem=song_lines,
                notes=raw_poem.notes,
                preface=raw_poem.preface,
                part_index=song_num,
                total_parts=num_songs
            )
            result.append(processed_poem)

        return result

    def save_volume(self, volume_num: int, poems: List[Poem]):
        """
        Save processed poems to output file.

        Args:
            volume_num: Volume number
            poems: List of Poem objects to save
        """
        output_file = self.output_dir / f"volume_{volume_num:03d}.json"

        # Convert to dictionaries
        poems_data = [poem.to_dict() for poem in poems]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(poems_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Saved {len(poems)} poems to {output_file}. "
            f"File size: {output_file.stat().st_size / 1024:.1f} KB"
        )

    def _validate_and_copy_authors(self) -> None:
        """
        Validate author names from raw authors.json and copy to output.

        Validates for:
        - Empty canonical or recorded names
        - Names exceeding 100 characters

        Then copies the entire raw authors.json to output directory.
        """
        raw_authors_file = self.raw_dir / 'authors.json'
        output_authors_file = self.output_dir / 'authors.json'

        if not raw_authors_file.exists():
            logger.warning(f"Raw authors file not found: {raw_authors_file}")
            return

        with open(raw_authors_file, 'r', encoding='utf-8') as f:
            authors_data = json.load(f)

        MAX_NAME_LENGTH = 100

        for canonical, author_info in authors_data.items():
            # check canonical name (which is the key)
            if not canonical or not canonical.strip():
                logger.warning(f"Author has empty canonical name: {author_info}")

            if len(canonical) > MAX_NAME_LENGTH:
                logger.warning(
                    f"Author canonical name is too long ({len(canonical)} chars, max {MAX_NAME_LENGTH}). "
                    f"Name: '{canonical[:50]}...'"
                )

            # Check recorded variants
            recorded_variants = author_info.get('recorded_variants', [])
            for variant in recorded_variants:
                if not variant or not variant.strip():
                    logger.warning(
                        f"Author '{canonical}' has empty recorded variant"
                    )

                if len(variant) > MAX_NAME_LENGTH:
                    logger.warning(
                        f"Author '{canonical}' recorded variant is too long "
                        f"({len(variant)} chars, max {MAX_NAME_LENGTH}). "
                        f"Variant: '{variant[:50]}...'"
                    )

        # Copy raw authors.json to output
        import shutil
        shutil.copy2(raw_authors_file, output_authors_file)
        logger.info(f"Validated and copied {len(authors_data)} authors from {raw_authors_file} to {output_authors_file}")

    def process_volumes(self, start: int, end: int):
        """
        Process a range of volumes.

        Args:
            start: Starting volume number
            end: Ending volume number
        """
        for volume_num in range(start, end + 1):
            poems = self.process_volume(volume_num)
            if poems:
                self.save_volume(volume_num, poems)

        # after processing all volumes, validate and copy authors.json
        self._validate_and_copy_authors()


def main():
    parser = argparse.ArgumentParser(
        description='Post-process raw scraped poems to apply splits'
    )
    parser.add_argument('--start', type=int, default=1,
                       help='Starting volume (1-900)')
    parser.add_argument('--end', type=int, default=900,
                       help='Ending volume (1-900)')
    parser.add_argument('--volume', type=int,
                       help='Process single volume')
    parser.add_argument('--raw-dir', default=str(DEFAULT_RAW_OUTPUT_DIR),
                       help='Directory with raw JSON files')
    parser.add_argument('--output-dir', default=str(DEFAULT_PROCESSED_OUTPUT_DIR),
                       help='Directory for processed JSON files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose (DEBUG) logging')

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    processor = PoemPostProcessor(raw_dir=args.raw_dir, output_dir=args.output_dir)

    if args.volume:
        poems = processor.process_volume(args.volume)
        if poems:
            processor.save_volume(args.volume, poems)
        # Validate and copy authors.json
        processor._validate_and_copy_authors()
    else:
        processor.process_volumes(args.start, args.end)

    logger.info("Post-processing complete!")


if __name__ == '__main__':
    main()
