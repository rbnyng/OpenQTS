"""
Poem extraction strategies for different HTML formats.

Uses the Strategy pattern to handle different HTML structures across volumes.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict
from bs4 import BeautifulSoup, Tag
from urllib.parse import unquote

from models import Poem, Author
from author_service import AuthorMetadataService, parse_author_name
from utils import chinese_utils, text_utils, uid_generator
import volume_special_cases
from constants import (
    PART_INDICATOR_PATTERN,
    ANNOTATION_PATTERN,
    FRAGMENT_GROUP_PATTERN,
    PREFACE_TITLE_PATTERN,
    MIN_EMPTY_LINES_FOR_SPLIT,
    CHINESE_PUNCTUATION
)

logger = logging.getLogger(__name__)


class PoemExtractionStrategy(ABC):
    """Base  class for poem extraction strategies."""

    def __init__(self, author_service: AuthorMetadataService, author_database=None):
        """
        Initialize extraction strategy.

        Args:
            author_service: Service for fetching author metadata
            author_database: Optional AuthorDatabase for storing biographies
        """
        self.author_service = author_service
        self.author_database = author_database

    @abstractmethod
    def extract(self, soup: BeautifulSoup, volume_num: int) -> List[Poem]:
        """
        Extract poems from a volume page.

        Args:
            soup: BeautifulSoup object of the volume page
            volume_num: Volume number

        Returns:
            List of extracted poems
        """
        pass

    def extract_footnotes(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract footnote content from the page.

        Wikisource uses <ol class="references"> for footnotes.
        Each footnote is a <li id="cite_note-N"> with <span class="reference-text">.

        Some volumes wrap footnotes in invisible angle brackets like:
        <span style="color:transparent">〈</span>content<span style="color:transparent">〉</span>
        These are removed during extraction.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            Dictionary mapping footnote_id to footnote text
            e.g., {"cite_note-1": "一本無此二句。", "cite_note-2": "..."}
        """
        footnotes = {}

        refs_list = soup.find('ol', class_='references')
        if not refs_list:
            return footnotes

        for li in refs_list.find_all('li', id=lambda x: x and x.startswith('cite_note-')):
            footnote_id = li.get('id')
            ref_text_span = li.find('span', class_='reference-text')
            if ref_text_span:
                # Remove invisible wrapper spans (transparent angle brackets)
                # These appear as: <span style="color:transparent;font-size:0px">〈</span>
                for span in ref_text_span.find_all('span', style=lambda x: x and 'transparent' in x):
                    span.decompose()

                footnote_text = ref_text_span.get_text(strip=True)
                footnote_text = footnote_text.strip('〈〉')
                footnotes[footnote_id] = footnote_text

        return footnotes

    def generate_uid(self, volume_num: int, entry_index: int, part_index: int = 1) -> str:
        return uid_generator.generate_uid(volume_num, entry_index, part_index)

    def has_preface_marker(self, title: Optional[str]) -> bool:
        """Check if title contains preface marker like （并序）or （序）."""
        if not title:
            return False
        return bool(re.search(PREFACE_TITLE_PATTERN, title))

    def is_preface_only_title(self, title: Optional[str]) -> bool:
        """Check if title is ONLY a preface marker (e.g., just '並序' or '序')."""
        if not title:
            return False
        # strip whitespace and check if the title is exactly a preface marker
        # Pattern: 并序, 並序, 有序, or just 序 (with optional parentheses)
        return bool(re.fullmatch(r'[（(]?[并並有]?序[）)]?', title.strip()))

    def extract_poem_title_from_preface(self, preface_text: Optional[str]) -> Optional[str]:
        """
        Extract the actual poem title from preface text.

        Looks for patterns like:
        - 故述《帝京篇》以明雅志 -> "帝京篇"
        - 作《某某詩》 -> "某某詩"

        Args:
            preface_text: The preface text to extract from

        Returns:
            Extracted poem title, or None if not found
        """
        if not preface_text:
            return None

        # Pattern 1: 故述《X》 or similar patterns
        # Common patterns: 故述《X》, 作《X》, 賦《X》, 詠《X》
        match = re.search(r'(?:故述|作|賦|詠|撰)[《<]([^》>]+)[》>]', preface_text)
        if match:
            return match.group(1)

        # Patern 2: Just《X》near the end of the preface
        matches = re.findall(r'[《<]([^》>]+)[》>]', preface_text)
        if matches:
            # return the last one, as it's usually the poem title
            return matches[-1]

        return None

    def extract_title_notes(self, title: str) -> Tuple[str, List[Dict]]:
        """
        Extract parenthetical and angle bracket notes from title and return cleaned title with notes list.

        Handles patterns like:
        - "送從弟亞赴安西（一作河西）判官" -> title: "送從弟亞赴安西判官",
          notes: [{"content": "一作河西", "context": "安西", "original": "送從弟亞赴安西（一作河西）判官"}]
        - "病後遇（一作過）王倚飲贈歌" -> title: "病後遇王倚飲贈歌",
          notes: [{"content": "一作過", "context": "遇", "original": "病後遇（一作過）王倚飲贈歌"}]
        - "長門怨〈一作張循之詩。〉" -> title: "長門怨",
          notes: [{"content": "一作張循之詩。", "context": "長門怨", "original": "長門怨〈一作張循之詩。〉"}]

        Args:
            title: Title string potentially containing parenthetical or angle bracket notes

        Returns:
            Tuple of (cleaned_title, list_of_note_dicts)
        """
        if not title:
            return title, []

        notes = []
        cleaned_title = title

        # Pattern  to match parentheses （...）, (...), and angle brackets 〈...〉, <...>
        # Captures everything inside the brackets
        bracket_pattern = re.compile(r'[（(〈<]([^）)〉>]+)[）)〉>]')

        matches = list(bracket_pattern.finditer(title))

        # Process matches in reverse order to preserve string positions
        for match in reversed(matches):
            note_content = match.group(1).strip()

            context_start = max(0, match.start() - 5)
            context_text = title[context_start:match.start()].strip()

            note_dict = {
                'content': note_content,
                'context': context_text,
                'original_title': title
            }

            notes.insert(0, note_dict)  # Insert at beginning to maintain order

            cleaned_title = cleaned_title[:match.start()] + cleaned_title[match.end():]

        cleaned_title = re.sub(r'\s+', '', cleaned_title).strip()

        return cleaned_title, notes

    def extract_author_biography(self, heading_div: Tag) -> Optional[str]:
        """
        Extract author biography from paragraphs following an author heading.

        Biographies appear as <p> tags after h1/h2 author headings, before the
        first poem title (h2/h3).

        Args:
            heading_div: The heading div containing the author name

        Returns:
            Biography text if found, None otherwise
        """
        biography_parts = []
        sibling = heading_div.find_next_sibling()

        while sibling:
            if hasattr(sibling, 'name'):
                # Stop if we hit another heading (next author or first title)
                if sibling.name == 'div' and 'mw-heading' in sibling.get('class', []):
                    break

                # Stop if we hit a poem div
                if sibling.name == 'div' and 'poem' in sibling.get('class', []):
                    break

                # Stop if we hit dl (poem content)
                if sibling.name == 'dl':
                    break

                # Collect paragraph text (biography content)
                if sibling.name == 'p':
                    text = sibling.get_text(strip=True)
                    if text:
                        biography_parts.append(text)

            sibling = sibling.find_next_sibling()

        return '\n\n'.join(biography_parts) if biography_parts else None

    def extract_preface_from_heading(self, heading_div: Tag) -> Optional[str]:
        """
        Extract preface text from paragraphs following a heading.

        Prefaces appear as regular paragraph text between the title and the poem.
        They often contain classical patterns and end before the poem div starts.

        Args:
            heading_div: The heading div element containing the title

        Returns:
            Preface text if found, None otherwise
        """
        preface_parts = []
        sibling = heading_div.find_next_sibling()

        while sibling:
            if hasattr(sibling, 'name'):
                # Stop if we hit another heading or a poem div
                if sibling.name == 'div' and (
                    'mw-heading' in sibling.get('class', []) or
                    'poem' in sibling.get('class', [])
                ):
                    break

                # Stop if we hit a dl element (poem content)
                if sibling.name == 'dl':
                    break

                # Collect paragraph text (preface content)
                if sibling.name == 'p':
                    text = sibling.get_text(strip=True)
                    small_tag = sibling.find('small')
                    # Include text if:
                    # 1. No small tag (regular preface)
                    # 2. Small tag with angle brakets 〈...〉 (reference note/preface)
                    if text:
                        if not small_tag:
                            preface_parts.append(text)
                        elif '〈' in text or '〉' in text:
                            # This is a refernce note, include it as preface
                            preface_parts.append(text)

            sibling = sibling.find_next_sibling()

        return '\n\n'.join(preface_parts) if preface_parts else None

    def extract_variants_from_element(self, element: Tag, line_index: int) -> List[Dict]:
        """
        Extract textual variants from span elements with title attributes.

        Args:
            element: BeautifulSoup element to search for variants
            line_index: Line number for variant tracking

        Returns:
            List of variant dictionaries
        """
        variants = []

        # Find all spans with title attributes (textual variants)
        for span in element.find_all('span'):
            title = span.get('title', '').strip()
            if title and ('一作' in title or '作' in title):
                main_text = span.get_text(strip=True)

                # Format is typically like: "一作「山」" or just "作「山」"
                variant_match = re.search(r'[一]?作[「『](.+?)[」』]', title)
                if variant_match:
                    variant_text = variant_match.group(1)

                    # Calculate position in the line (this is approximate)
                    # We'd need the full line context to get exact position
                    variants.append({
                        'line': line_index,
                        'text': main_text,
                        'variant': variant_text,
                        'source': title
                    })

        return variants

    def extract_poem_lines(self, poem_div: Tag) -> Tuple[List[str], List[str], Optional[str], List[Dict], List[Dict]]:
        """
        Extract lines from a poem div, handling br tags and textual variants.

        Args:
            poem_div: BeautifulSoup div element with class="poem"

        Returns:
            Tuple of (poem_lines, notes, subtitle, variants, footnotes)
            - footnotes: List of dicts with 'id' and 'line' keys
        """
        lines = []
        notes = []
        subtitle = None
        variants = []
        footnotes = []  # Track footnote references with line indices

        # Find all <p> tags in the poem div
        p_tags_found = poem_div.find_all('p')
        logger.debug(f"extract_poem_lines: Found {len(p_tags_found)} <p> tags")
        for p_tag in p_tags_found:
            logger.debug(f"extract_poem_lines: Processing <p>: {p_tag.get_text(strip=True)[:50]}")
            # Process the p tag content line by line, tracking variants
            # Split by <br> to get individual lines
            line_content = []
            current_segment = []
            current_line_footnotes = []  # Track footnote IDs for current line being built

            for element in p_tag.children:
                if hasattr(element, 'name'):
                    if element.name == 'br':
                        # End of a line - save footnotes for this line
                        if current_line_footnotes:
                            for fid in current_line_footnotes:
                                footnotes.append({'id': fid, 'line_segment_idx': len(line_content)})
                            current_line_footnotes = []
                        line_content.append(current_segment)
                        current_segment = []
                    elif element.name == 'sup':
                        # Handle footnote references - multiple possible structures:
                        # 1. <sup id="cite_ref-1" class="reference"><a href="#cite_note-1">...</a></sup>
                        # 2. <sup><a href="#cite_note-1">[1]</a></sup>
                        # 3. <sup>[1]</sup>

                        if 'reference' in element.get('class', []):
                            sup_id = element.get('id', '')
                            if sup_id.startswith('cite_ref-'):
                                footnote_num = sup_id.replace('cite_ref-', '')
                                footnote_id = f"cite_note-{footnote_num}"
                                # track this footnote for the current line being built
                                if footnote_id not in current_line_footnotes:
                                    current_line_footnotes.append(footnote_id)

                        # Always skip the text content of sup tags (footnote markers like [1], [2])
                        # Don't add anything to current_segment
                    elif element.name == 'small':
                        # Small tags often wrap footnote markers
                        # Check for nested sup tags and extract footnote IDs
                        nested_sups = element.find_all('sup', class_='reference')
                        for sup in nested_sups:
                            sup_id = sup.get('id', '')
                            if sup_id.startswith('cite_ref-'):
                                footnote_num = sup_id.replace('cite_ref-', '')
                                footnote_id = f"cite_note-{footnote_num}"
                                if footnote_id not in current_line_footnotes:
                                    current_line_footnotes.append(footnote_id)
                        # Don't add text content of small tags containing footnotes
                        # (the markers should be removed)
                    elif element.name == 'span':
                        # Check if this is a variant span
                        title = element.get('title', '').strip()
                        if title and ('一作' in title or '作' in title):
                            main_text = element.get_text(strip=True)
                            variant_match = re.search(r'[一]?作[「『](.+?)[」』]', title)
                            if variant_match:
                                variant_text = variant_match.group(1)
                                # Mark this variant for the current line
                                current_segment.append({
                                    'type': 'variant',
                                    'text': main_text,
                                    'variant': variant_text,
                                    'source': title
                                })
                            # Don't append the text again - it's in the variant dict
                        else:
                            # Not a variant span, just get the text
                            current_segment.append(element.get_text())
                    else:
                        current_segment.append(element.get_text())
                else:
                    # Text node
                    current_segment.append(str(element))

            # Add last line
            if current_segment:
                logger.debug(f"extract_poem_lines: Adding last segment: {current_segment}")
                # Save any footnotes for this last line
                if current_line_footnotes:
                    for fid in current_line_footnotes:
                        footnotes.append({'id': fid, 'line_segment_idx': len(line_content)})
                    current_line_footnotes = []
                line_content.append(current_segment)
            else:
                logger.debug(f"extract_poem_lines: No current_segment to add")

            # Proccess each line
            for segment_idx, line_segments in enumerate(line_content):
                # Collect variants for this line
                line_variants = [seg for seg in line_segments if isinstance(seg, dict) and seg.get('type') == 'variant']
                # Get the text content
                line_text = ''.join(seg if isinstance(seg, str) else seg.get('text', '') for seg in line_segments)
                line_text = line_text.strip()

                # Remove footnote markers like [1], [2], etc. that may appear as text nodes
                # Patern: [digits] at the end of text or anywhere in the line
                line_text = re.sub(r'\[\d+\]', '', line_text)

                logger.debug(f"extract_poem_lines: line_text after strip/clean: '{line_text[:80] if line_text else 'EMPTY'}'")
                if line_text:
                    # Check if this line contains an annotation
                    poem_part, note_part = text_utils.separate_annotation(line_text)

                    if poem_part:
                        # Add the line
                        lines.append(text_utils.clean_line(poem_part))
                        current_line_idx = len(lines)  # 1-indexed line number (human-readable)

                        # add variants for this line
                        for v in line_variants:
                            variants.append({
                                'line': current_line_idx,
                                'text': v['text'],
                                'variant': v['variant'],
                                'source': v['source']
                            })

                        # Update footnotes for this line segment with actual line index
                        for fn in footnotes:
                            if fn.get('line_segment_idx') == segment_idx and 'line' not in fn:
                                fn['line'] = current_line_idx

                        # Add note with line index and context if present
                        if note_part:
                            notes.append({
                                'line': current_line_idx,
                                'content': text_utils.clean_line(note_part),
                                'context': text_utils.clean_line(poem_part)
                            })
                    elif note_part:
                        # Note  without poem content on this line (rare case)
                        # Use previous line as context if available
                        context = lines[-1] if lines else None
                        notes.append({
                            'line': current_line_idx,
                            'content': text_utils.clean_line(note_part),
                            'context': context
                        })
                else:
                    # Empty line - mark as separator
                    lines.append('')

        # Remove trailing empty lines
        while lines and lines[-1] == '':
            lines.pop()
        # Remove leading empty lines
        while lines and lines[0] == '':
            lines.pop(0)

        footnotes = [{'id': fn['id'], 'line': fn['line']} for fn in footnotes if 'line' in fn]

        logger.debug(f"extract_poem_lines: Before part indicator check, lines={len(lines)}")

        # Check if first line is a part indicator like 其一, 其二, etc.
        if lines and chinese_utils.is_part_indicator(lines[0]):
            subtitle = lines[0]
            lines = lines[1:]  # Remove it from poem content
            # Adjust variant line indices since we removed first line (1-based indexing)
            for v in variants:
                v['line'] = v['line'] - 1
            # Adjust  footnote line indices since we removed first line (1-based indexing)
            for fn in footnotes:
                fn['line'] = fn['line'] - 1

        logger.debug(f"extract_poem_lines: Returning {len(lines)} lines, {len(notes)} notes")
        return lines, notes, subtitle, variants, footnotes

    def extract_poem_lines_from_dl(self, dl_elem: Tag) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Extract lines from a dl (definition list) element.

        Args:
            dl_elem: BeautifulSoup dl element

        Returns:
            Tuple of (poem_lines, notes, subtitle)
        """
        lines = []
        notes = []
        subtitle = None

        # Each <dd> is a line of the poem
        for dd in dl_elem.find_all('dd'):
            line = dd.get_text(strip=True)
            if line:
                # Check if this line contains an annotation
                poem_part, note_part = text_utils.separate_annotation(line)

                if poem_part:
                    lines.append(text_utils.clean_line(poem_part))
                if note_part:
                    # Add note with line index and context from the poem line
                    notes.append({
                        'line': len(lines) if lines else 0,
                        'content': text_utils.clean_line(note_part),
                        'context': text_utils.clean_line(poem_part) if poem_part else None
                    })

        # Check if first line is a part indicator like 其一, 其二, etc.
        if lines and chinese_utils.is_part_indicator(lines[0]):
            subtitle = lines[0]
            lines = lines[1:]  # Remove it from poem content

        return lines, notes, subtitle

    def split_fragments(self, lines: List[str], notes: List[str]) -> List[Tuple[List[str], List[str], Optional[str]]]:
        """
        Split lines into separate fragments based on empty line separators.

        Used for "句" (Verses/Fragments) sections where multiple poems are in one div.

        Args:
            lines: List of poem lines with empty line separators
            notes: List of annotation notes

        Returns:
            List of (fragment_lines, fragment_notes, group_name) tuples
        """
        # First, split into individual fragments
        fragments = []
        current_lines = []
        empty_count = 0

        for line in lines:
            if line == '':
                empty_count += 1
            else:
                # Non-empty line found
                # check if we should start a new fragment (2+ empty lines before this)
                if empty_count >= MIN_EMPTY_LINES_FOR_SPLIT and current_lines:
                    # End current fragment
                    fragments.append(current_lines)
                    current_lines = []

                # add this line to current fragment
                current_lines.append(line)
                empty_count = 0

        # Add last fragment
        if current_lines:
            fragments.append(current_lines)

        # Now group fragments based on notes
        # Patern: "以下《X》" or "以下(X)" means following fragments from source X
        group_pattern = re.compile(FRAGMENT_GROUP_PATTERN)

        result = []
        current_group_name = None
        current_group_lines = []
        current_group_note = None
        note_idx = 0

        for i, frag_lines in enumerate(fragments):
            # Get note for this fragment
            note = notes[note_idx] if note_idx < len(notes) else None

            # Extract note content (handle both string and dict formats)
            note_content = note['content'] if isinstance(note, dict) else note

            # Check if this note starts a group
            group_match = group_pattern.search(note_content) if note_content else None

            if group_match:
                # This note starts a new group
                # First, save any previous group
                if current_group_lines:
                    result.append((current_group_lines, [current_group_note] if current_group_note else [], current_group_name))
                    current_group_lines = []

                # Start new group
                current_group_name = group_match.group(1)
                current_group_note = note
                current_group_lines = frag_lines
                note_idx += 1
            elif current_group_name and note:
                # We're  in a group but this fragment has an individual note
                # This means the group ends and this is a separate fragment
                # First, save the current group
                result.append((current_group_lines, [current_group_note] if current_group_note else [], current_group_name))
                current_group_lines = []
                current_group_name = None
                current_group_note = None

                # Add this fragment as individual
                result.append((frag_lines, [note], None))
                note_idx += 1
            elif current_group_name:
                current_group_lines.extend(frag_lines)
                # don't increment note_idx - this fragment doesn't have its own note
            else:
                # Individual fragment (not part of a group)
                result.append((frag_lines, [note] if note else [], None))
                if note:
                    note_idx += 1

        # Add final group if any
        if current_group_lines:
            result.append((current_group_lines, [current_group_note] if current_group_note else [], current_group_name))

        return result


class StandardFormatStrategy(PoemExtractionStrategy):
    """
    Strategy for standard format volumes.

    Structure: h1/h2 authors, h3 titles, div.poem or dl content
    """

    def extract(self, soup: BeautifulSoup, volume_num: int) -> List[Poem]:
        poems = []
        entry_index = 0

        # Find the main content div
        # Some volumes have multiple mw-parser-output divs; pick the one with actual content
        content_divs = soup.find_all('div', class_=lambda c: c and 'mw-parser-output' in c)
        content_div = None

        # score each div by content richness and pick the best one
        best_score = 0
        for div in content_divs:
            score = (
                len(div.find_all('div', class_='mw-heading')) * 10 +  # Headings are strong indicators
                len(div.find_all('div', class_='poem')) * 5 +
                len(div.find_all('dl')) * 5 +
                len(div.find_all('h2')) * 3 +
                len(div.find_all('h3')) * 2 +
                len(div.find_all('p'))
            )
            if score > best_score:
                best_score = score
                content_div = div

        if not content_div and content_divs:
            content_div = content_divs[0]

        if not content_div:
            logger.warning(f"No content found for volume {volume_num}. This may indicate a structural change in the source.")
            return poems

        # Extract footnotes from the page (once for all poems)
        footnotes = self.extract_footnotes(soup)
        if footnotes:
            logger.debug(f"Extracted {len(footnotes)} footnotes from volume {volume_num}")

        # Extract page-level author
        page_author, has_multiple_authors = self._extract_page_author(soup)
        current_author_canonical = page_author
        current_author_recorded = page_author
        current_title = None
        parent_title = None
        parent_h3_title = None
        current_h3_full_title = None  # Full combined h2+h3 title for h4 subtitles

        # Extract and save page-level author biography if available
        if page_author and not has_multiple_authors and self.author_database:
            # For single-author volumes, the first <p> tag is usually the biography
            first_p = content_div.find('p')
            if first_p:
                biography_text = first_p.get_text(strip=True)
                # check if this looks like a biography
                # Classical formats may have names split: "帝姓李氏，諱世民" instead of "李世民"
                # Check for exact match in first 50 chars, or check for name components
                is_biography = False

                if biography_text:
                    if page_author in biography_text[:50]:
                        is_biography = True
                    else:
                        # For multi-character names, check if individual characters appear
                        # This handles classical formats like "姓X氏，諱YZ"
                        if len(page_author) >= 2:
                            # Check if at least 2 characters from the name appear in first 50 chars
                            matching_chars = sum(1 for char in page_author if char in biography_text[:50])
                            if matching_chars >= 2:
                                is_biography = True

                if is_biography:
                    author = self.author_service.create_author(page_author, page_author, volume_num)
                    self.author_database.add_or_update_author(author, biography_text, volume_num)
                    logger.debug(f"Saved page-level biography for {page_author} ({len(biography_text)} chars)")

        # Track pending notes from anotation paragraphs
        pending_notes = []

        # Track preface for current title
        current_preface = None

        # Track author bio note for adding to notes
        current_author_bio_note = None

        # Track multi-part works with parent h2 title
        parent_preface = None  # Preface from h2 (applies to all parts)
        parent_entry_index = None  # Entry index for parent title (reused for numbered parts)
        parent_part_counter = 0  # Counter for parts under parent title

        for element in content_div.find_all(['h1', 'h2', 'h3', 'h4', 'div', 'dl']):
            # Handle  h1 (author headings OR titles in single-author volumes)
            if element.name == 'h1':
                # If we have a page_author and it's a single-author volume, treat h1 as title
                if page_author and not has_multiple_authors:
                    heading_div = element.find_parent('div', class_='mw-heading')
                    if heading_div:
                        h1_elem = heading_div.find('h1')
                        if h1_elem:
                            # Extract title text
                            title_text = h1_elem.get_text(strip=True)
                            title_text = re.sub(r'\[編輯\]', '', title_text).strip()

                            if title_text:
                                current_title = title_text
                                parent_title = title_text

                                # Reset multi-part tracking for new title
                                parent_entry_index = None
                                parent_part_counter = 0
                                parent_h3_title = None
                                current_preface = None

                                # Extract title notes if any
                                cleaned_title, title_notes = self.extract_title_notes(title_text)
                                if title_notes:
                                    pending_notes.extend(title_notes)
                                    current_title = cleaned_title
                                    parent_title = cleaned_title

                                logger.debug(f"Found h1 title in single-author volume: {current_title}")

                                # Add skip_autosplit hint if bio indicates single poem corpus
                                if current_author_bio_note and '詩一首' in current_author_bio_note:
                                    pending_notes.append({
                                        'type': 'skip_autosplit',
                                        'reason': 'single_poem_corpus'
                                    })
                                current_author_bio_note = None  # Clear after first use

                                # Extract bare p tag poems after h1 title
                                poem_data = self._extract_bare_p_poem(
                                    heading_div, current_title, current_author_canonical,
                                    current_author_recorded, volume_num, entry_index, pending_notes,
                                    current_preface, False, parent_entry_index, parent_part_counter
                                )
                                if poem_data:
                                    poems.append(poem_data['poem'])
                                    entry_index = poem_data['entry_index']
                                    pending_notes = poem_data['pending_notes']
                                    parent_entry_index = poem_data.get('parent_entry_index')
                                    parent_part_counter = poem_data.get('parent_part_counter', 0)
                                    current_preface = None  # Reset after use
                else:
                    # No page_author or multi-author volume - treat h1 as author heading
                    canonical, recorded = self._extract_h1_author(element)
                    if recorded:
                        current_author_canonical = canonical
                        current_author_recorded = recorded
                        parent_title = None
                        parent_preface = None
                        parent_entry_index = None
                        parent_part_counter = 0
                        parent_h3_title = None

                        # Extract and save author biography if database is available
                        if self.author_database:
                            heading_div = element.find_parent('div', class_='mw-heading')
                            if heading_div:
                                biography = self.extract_author_biography(heading_div)
                                if biography:
                                    # Create author object and add to database
                                    author = self.author_service.create_author(canonical, recorded, volume_num)
                                    self.author_database.add_or_update_author(author, biography, volume_num)
                                    logger.debug(f"Saved biography for {recorded} ({len(biography)} chars)")

            # Handle  h2 (author or title)
            elif element.name == 'h2':
                canonical, recorded, is_author, bio_note, embedded_author, h2_title_notes = self._extract_h2(element, page_author, has_multiple_authors, current_author_recorded)
                if is_author:
                    current_author_canonical = canonical
                    current_author_recorded = recorded
                    current_author_bio_note = bio_note  # Track for adding to first poem's notes
                    parent_title = None
                    parent_preface = None
                    parent_entry_index = None
                    parent_part_counter = 0
                    parent_h3_title = None

                    # Extract and save author biography if database is available
                    if self.author_database:
                        heading_div = element.find_parent('div', class_='mw-heading')
                        if heading_div:
                            biography = self.extract_author_biography(heading_div)
                            # Prepend bio_note to biography if present
                            if bio_note:
                                if biography:
                                    biography = f"{bio_note}\n\n{biography}"
                                else:
                                    biography = bio_note
                            if biography:
                                # Create author object and add to database
                                author = self.author_service.create_author(canonical, recorded, volume_num)
                                self.author_database.add_or_update_author(author, biography, volume_num)
                                logger.debug(f"Saved biography for {recorded} ({len(biography)} chars)")
                else:
                    # h2 is a title (likely parent of multi-part work)
                    # If embedded_author is present (e.g., Yuefu volumes 10-29), update current author
                    if embedded_author:
                        current_author_canonical = embedded_author
                        current_author_recorded = embedded_author
                        logger.debug(f"Set author from embedded h2: {embedded_author}")

                    # Add title notes from small tags (一作, 缺字, months, seasons)
                    if h2_title_notes:
                        pending_notes.extend(h2_title_notes)

                    # Extract parenthetical notes from title
                    cleaned_title, title_notes = self.extract_title_notes(recorded)

                    # add title notes to pending notes
                    if title_notes:
                        pending_notes.extend(title_notes)

                    heading_div = element.find_parent('div', class_='mw-heading')
                    if heading_div:
                        parent_preface = self.extract_preface_from_heading(heading_div)
                        current_preface = parent_preface
                        if parent_preface:
                            logger.debug(f"Extracted preface from h2 '{cleaned_title}'")
                    else:
                        parent_preface = None
                        current_preface = None

                    # Check if this title contains a preface marker
                    # Covers both preface-only titles (just "並序") and titles with markers ("帝京篇（並序）")
                    if self.is_preface_only_title(cleaned_title) or self.has_preface_marker(recorded):
                        # this has a preface marker - extract actual title or use cleaned version
                        if self.is_preface_only_title(cleaned_title):
                            # Pure  preface marker like "並序" - extract title from preface
                            logger.debug(f"Detected preface-only title: '{cleaned_title}'")
                            extracted_title = self.extract_poem_title_from_preface(parent_preface)
                            if extracted_title:
                                logger.info(f"Extracted actual poem title from preface: '{extracted_title}'")
                                parent_title = extracted_title
                                current_title = extracted_title
                            else:
                                # couldn't extract title from preface, use the cleaned title
                                logger.warning(f"Could not extract poem title from preface for '{cleaned_title}'")
                                parent_title = cleaned_title
                                current_title = cleaned_title
                        else:
                            # Title contains preface marker like "帝京篇（並序）"
                            # use the cleaned title (with parenthetical content removed)
                            logger.debug(f"Detected title with preface marker: '{recorded}' -> '{cleaned_title}'")
                            parent_title = cleaned_title
                            current_title = cleaned_title

                        # Don't create a poem entry for titles with preface markers
                        # The preface will be attached to the first numbered part
                        parent_entry_index = None
                        parent_part_counter = 0
                        parent_h3_title = None
                        continue
                    else:
                        # Regular title - set it normally
                        parent_title = cleaned_title
                        current_title = cleaned_title

                        # Reset multi-part tracking for new parent title
                        parent_entry_index = None
                        parent_part_counter = 0
                        parent_h3_title = None

                        # Check for bare p tag poems after h2 title
                        # Some volumes (e.g., 360) have H2 titles followed directly by bare p tags
                        if heading_div:
                            poem_data = self._extract_bare_p_poem(
                                heading_div, current_title, current_author_canonical,
                                current_author_recorded, volume_num, entry_index, pending_notes,
                                current_preface, False, parent_entry_index, parent_part_counter
                            )
                            if poem_data:
                                poems.append(poem_data['poem'])
                                entry_index = poem_data['entry_index']
                                pending_notes = poem_data['pending_notes']
                                parent_entry_index = poem_data.get('parent_entry_index')
                                parent_part_counter = poem_data.get('parent_part_counter', 0)
                                current_preface = None  # Reset after use
                            else:
                                # If no bare p poem found, check for <pre> tag (e.g., volume 336)
                                poem_data = self._extract_from_pre_tag(
                                    heading_div, current_title, current_author_canonical,
                                    current_author_recorded, volume_num, entry_index, pending_notes,
                                    current_preface, False, parent_entry_index, parent_part_counter
                                )
                                if poem_data:
                                    poems.append(poem_data['poem'])
                                    entry_index = poem_data['entry_index']
                                    pending_notes = poem_data['pending_notes']
                                    parent_entry_index = poem_data.get('parent_entry_index')
                                    parent_part_counter = poem_data.get('parent_part_counter', 0)
                                    current_preface = None  # Reset after use

            # Handle h3 (title)
            elif element.name == 'h3':
                current_title, parent_h3_title, heading_div, title_notes = self._extract_h3_title(element, parent_title)
                current_h3_full_title = current_title  # Store full combined title for h4 subtitles

                # add title notes to pending notes
                if title_notes:
                    pending_notes.extend(title_notes)

                # VOLUME-SPECIFIC: Handle H3 titles with preface markers as parent titles
                # In certain volumes (e.g., 428), H3 titles like "效陶潛體詩十六首（並序）"
                # should behave like H2 parent titles: set as parent, extract preface, skip poem creation
                # This allows subsequent "其一", "其二" H3 titles to inherit the parent title
                volumes_with_h3_parent_preface = [428]  # Add more volumes here if needed

                # Check  if this H3 had a preface marker (detected from title_notes)
                has_h3_preface_marker = any(
                    note.get('content') in ['並序', '并序', '序'] or '序' in note.get('content', '')
                    for note in title_notes
                )

                if (volume_num in volumes_with_h3_parent_preface and
                    parent_h3_title and
                    has_h3_preface_marker):
                    # This H3 has a preface marker - treat it as a parent title
                    # The title has already been cleaned by extract_title_notes
                    cleaned_title = parent_h3_title

                    # Extract preface from the heading
                    if heading_div:
                        parent_preface = self.extract_preface_from_heading(heading_div)
                        current_preface = parent_preface
                        if parent_preface:
                            logger.debug(f"Extracted preface from H3 '{cleaned_title}'")

                    # set this H3 as the parent title for subsequent H3s
                    parent_title = cleaned_title
                    current_title = cleaned_title

                    # Don't create a poem entry for this H3 with preface
                    # the preface will be attached to the first numbered part (其一)
                    parent_entry_index = None
                    parent_part_counter = 0
                    logger.info(f"H3 '{cleaned_title}' with preface marker set as parent title for volume {volume_num}")
                    continue

                # Check if this h3 is a numbered part (一, 二, 三, etc.) under a parent title
                is_numbered_part = parent_h3_title and chinese_utils.is_numbered_part(parent_h3_title)

                if is_numbered_part and parent_title:
                    # this is a numbered part of a multi-part work
                    # Use parent's preface instead of extracting new one
                    current_preface = parent_preface
                    logger.debug(f"h3 '{parent_h3_title}' is a numbered part under '{parent_title}'")
                else:
                    # Regular h3 title - check for its own preface first
                    if current_title and self.has_preface_marker(current_title) and heading_div:
                        current_preface = self.extract_preface_from_heading(heading_div)
                    elif parent_title and parent_preface:
                        # No own preface, but has parent - inherit parent preface (only once)
                        current_preface = parent_preface
                        logger.debug(f"h3 '{parent_h3_title}' inherits preface from parent '{parent_title}'")
                        # Clear  parent_preface after first use to prevent all h3s from getting it
                        parent_preface = None
                    else:
                        current_preface = None

                    # Reset multi-part tracking for non-numbered titles
                    parent_entry_index = None
                    parent_part_counter = 0
                    # parent_preface is cleared above after first use
                    # parent_title will be reset when we encounter a new h2

                # Add skip_autosplit hint if bio indicates single poem corpus
                if current_author_bio_note and '詩一首' in current_author_bio_note:
                    pending_notes.append({
                        'type': 'skip_autosplit',
                        'reason': 'single_poem_corpus'
                    })
                current_author_bio_note = None  # Clear after first use

                # Check for bare p tag poems after h3
                if heading_div:
                    poem_data = self._extract_bare_p_poem(
                        heading_div, current_title, current_author_canonical,
                        current_author_recorded, volume_num, entry_index, pending_notes,
                        current_preface, is_numbered_part, parent_entry_index, parent_part_counter
                    )
                    if poem_data:
                        poems.append(poem_data['poem'])
                        entry_index = poem_data['entry_index']
                        pending_notes = poem_data['pending_notes']
                        parent_entry_index = poem_data.get('parent_entry_index')
                        parent_part_counter = poem_data.get('parent_part_counter', 0)
                        if not is_numbered_part:
                            current_preface = None  # Reset after use for non-numbered parts
                    else:
                        # If no bare p poem found, check for <pre> tag
                        poem_data = self._extract_from_pre_tag(
                            heading_div, current_title, current_author_canonical,
                            current_author_recorded, volume_num, entry_index, pending_notes,
                            current_preface, is_numbered_part, parent_entry_index, parent_part_counter
                        )
                        if poem_data:
                            poems.append(poem_data['poem'])
                            entry_index = poem_data['entry_index']
                            pending_notes = poem_data['pending_notes']
                            parent_entry_index = poem_data.get('parent_entry_index')
                            parent_part_counter = poem_data.get('parent_part_counter', 0)
                            if not is_numbered_part:
                                current_preface = None  # Reset after use for non-numbered parts

            # Handle h4 (subtitle)
            elif element.name == 'h4':
                current_title, current_author_canonical, current_author_recorded = self._extract_h4_subtitle(
                    element, current_h3_full_title, current_author_canonical, current_author_recorded, volume_num
                )

                # check if h4 title has preface marker
                heading_div = element.find_parent('div', class_='mw-heading')
                if current_title and self.has_preface_marker(current_title) and heading_div:
                    current_preface = self.extract_preface_from_heading(heading_div)
                else:
                    current_preface = None

            # Handle div.poem
            elif element.name == 'div' and 'poem' in element.get('class', []):
                logger.debug(f"Found div.poem - current_title='{current_title}' current_author='{current_author_canonical}'")
                if current_title:
                    # Add skip_autosplit hint if bio indicates single poem corpus
                    if current_author_bio_note and '詩一首' in current_author_bio_note:
                        pending_notes.append({
                            'type': 'skip_autosplit',
                            'reason': 'single_poem_corpus'
                        })
                    current_author_bio_note = None  # Clear after first use

                    # Check if we're in a numbered part context
                    is_numbered_part = parent_h3_title and chinese_utils.is_numbered_part(parent_h3_title) and parent_title

                    extracted = self._extract_from_poem_div(
                        element, current_title, current_author_canonical,
                        current_author_recorded, volume_num, entry_index, pending_notes,
                        current_preface, is_numbered_part, parent_entry_index, parent_part_counter,
                        footnotes
                    )
                    logger.debug(f"_extract_from_poem_div returned: {len(extracted['poems']) if extracted else 0} poems for title='{current_title}'")
                    if extracted:
                        poems.extend(extracted['poems'])
                        entry_index = extracted['entry_index']
                        pending_notes = extracted['pending_notes']
                        parent_entry_index = extracted.get('parent_entry_index')
                        parent_part_counter = extracted.get('parent_part_counter', 0)
                        if not is_numbered_part:
                            current_preface = None  # Reset after use for non-numbered parts

            # Handle dl (definition list)
            elif element.name == 'dl':
                # Add skip_autosplit hint if bio indicates single poem corpus
                if current_author_bio_note and '詩一首' in current_author_bio_note:
                    pending_notes.append({
                        'type': 'skip_autosplit',
                        'reason': 'single_poem_corpus'
                    })
                current_author_bio_note = None  # Clear after first use

                is_numbered_part = parent_h3_title and chinese_utils.is_numbered_part(parent_h3_title) and parent_title

                extracted = self._extract_from_dl(
                    element, current_title, current_author_canonical,
                    current_author_recorded, volume_num, entry_index, pending_notes,
                    current_preface, is_numbered_part, parent_entry_index, parent_part_counter
                )
                if extracted:
                    poems.append(extracted['poem'])
                    entry_index = extracted['entry_index']
                    pending_notes = extracted['pending_notes']
                    parent_entry_index = extracted.get('parent_entry_index')
                    parent_part_counter = extracted.get('parent_part_counter', 0)
                    if not is_numbered_part:
                        current_preface = None  # Reset after use

        if self.author_database:
            seen_authors = set()
            for poem in poems:
                author_key = (poem.author.canonical, poem.author.recorded)
                if author_key not in seen_authors:
                    # Try to get Wikipedia bio for authors with wikidata_id but no QTS bio
                    wiki_bio = self.author_service.get_author_wikipedia_bio(poem.author)
                    if wiki_bio:
                        self.author_database.add_or_update_author(
                            poem.author, wiki_bio, bio_source="wikipedia"
                        )
                    else:
                        self.author_database.add_or_update_author(poem.author, None, volume_num)
                    seen_authors.add(author_key)
            logger.debug(f"Saved {len(seen_authors)} unique authors from volume {volume_num}")

        return poems

    def _extract_page_author(self, soup: BeautifulSoup) -> Tuple[Optional[str], bool]:
        """Extract the author mentioned in the page header table."""
        # Look for the pattern: 作者：<a>...</a> [<a>...</a>...]
        # Check if there are multiple author links (multi-author volume)
        author_pattern = soup.find('span', string=re.compile(r'作者[：:]'))
        if author_pattern:
            # Find all author links after the "作者：" label
            # They should be siblings of the span element
            parent = author_pattern.parent
            if parent:
                author_links = []
                # Get all <a> tags that are siblings after the span
                for sibling in author_pattern.find_next_siblings():
                    if sibling.name == 'a' and '/Author:' in str(sibling.get('href', '')):
                        author_links.append(sibling)
                    elif sibling.name != 'a':
                        # stop if we hit a non-link element (end of author section)
                        break

                if len(author_links) > 0:
                    has_multiple = len(author_links) > 1
                    first_author = author_links[0].get_text(strip=True)
                    if has_multiple:
                        logger.debug(f"Detected multi-author volume with {len(author_links)} authors in header")
                    return (first_author, has_multiple)

        # First priority: navigation table format (has proper author links)
        # Format: <td><b>全唐詩</b><br/>卷N<br/>AuthorName</td>
        nav_table = soup.find('table', style=re.compile(r'border:1px solid'))
        if nav_table:
            # Find the middle cell that contains "全唐詩" as a standalone line
            # (not as part of navigation links like "全唐詩/卷XXX")
            for td in nav_table.find_all('td'):
                lines = [text.strip() for text in td.stripped_strings]
                # Check if first line is exactly '全唐詩' (middle cell)
                # This avoids matching navigation cells like "←全唐詩/卷683"
                if lines and lines[0] == '全唐詩':
                    # Format is usually: ["全唐詩", "卷N", "AuthorName"]
                    # Author name should be the last line that's not "全唐詩" and doesn't start with "卷"
                    # Skip "附" markers which mean "appended/attached" in anthology volumes
                    # Skip "唐" which is a dynasty marker (appears in gray text in some volumes)
                    # Also skip "全唐詩/卷XXX" patterns (multi-author anthology volumes)

                    # Get all author-like lines
                    author_lines = [l for l in lines if l not in ['全唐詩', '附', '唐'] and not l.startswith('卷') and not l.startswith('全唐詩/')]

                    if author_lines:
                        # Check if this is multiple authors
                        # more than 1 author line means multi-author volume
                        has_multiple = len(author_lines) > 1

                        # Also check for multiple H2 headers with anthology pattern (〈詩X首〉)
                        # This handles volumes like 790 and 794 with few authors (below 5-token threshold)
                        if not has_multiple:
                            h2_headers = soup.find_all('h2')
                            anthology_headers = []
                            for h2 in h2_headers:
                                h2_text = h2.get_text(strip=True)
                                # Pattern: "AuthorName〈詩X首〉" or "AuthorName〈诗X首〉"
                                if re.search(r'〈[詩诗].+首〉', h2_text):
                                    anthology_headers.append(h2_text)

                            if len(anthology_headers) > 1:
                                has_multiple = True
                                logger.debug(f"Detected multi-author volume from {len(anthology_headers)} H2 anthology headers")

                        # Also check for H2 author sections with biography pattern
                        # This handles volumes like 811 where H2 is followed by biography mentioning "詩X首"
                        if not has_multiple:
                            if 'h2_headers' not in locals():
                                h2_headers = soup.find_all('h2')
                            biography_sections = []
                            for h2 in h2_headers:
                                h2_text = h2.get_text(strip=True)
                                if any(skip in h2_text for skip in ['目录', '註釋', '注释', '全唐詩']):
                                    continue

                                # H2 is wrapped in div.mw-heading, check next sibling of wrapper
                                h2_wrapper = h2.parent
                                if h2_wrapper and h2_wrapper.name == 'div':
                                    next_elem = h2_wrapper.find_next_sibling()
                                    if next_elem and next_elem.name == 'p':
                                        bio_text = next_elem.get_text(strip=True)
                                        # Biography mentions "詩X首" or "诗X首" (X poems)
                                        if re.search(r'[詩诗].{1,3}首', bio_text):
                                            biography_sections.append(h2_text)

                            if len(biography_sections) > 1:
                                has_multiple = True
                                logger.debug(f"Detected multi-author volume from {len(biography_sections)} H2 biography sections")

                        # Also check if a single line contains multiple author names
                        # This handles volumes like 795 (space-separated) and 688 (、-separated)
                        # Format examples:
                        #   "李日知 趙仁獎 郭延謂 韋青 ..." (spaces)
                        #   "孫偓、陸扆、薛昭緯、陸翱..." (、dunhao)
                        if not has_multiple and len(author_lines) == 1:
                            # Split on both spaces and 、(dunhao - Chinese enumeration comma)
                            author_text = author_lines[0]
                            # Replace 、with space for uniform splitting
                            author_text_normalized = author_text.replace('、', ' ')
                            author_tokens = author_text_normalized.split()
                            # Chinese names are typically 2-4 characters
                            # If we have many tokens, this is likely a multi-author list
                            # Use different thresholds based on separator:
                            # - 、(dunhao): 2+ tokens (specifically for listing people/items)
                            # -  spaces: 3+ tokens (3 or more names clearly indicates multi-author)
                            has_dunhao = '、' in author_text
                            threshold = 2 if has_dunhao else 3
                            if len(author_tokens) >= threshold:
                                has_multiple = True
                                separator = '、' if has_dunhao else 'spaces'
                                logger.debug(f"Detected multi-author volume from {separator}-separated list: {len(author_tokens)} names")

                        # Return the last author line (will be used as page_author)
                        # For multi-author volumes, h2 headings will override this
                        # If this is a space-separated list of many authors, return None as page_author
                        # to prevent trying to fetch author metadata for the entire list
                        if has_multiple and len(author_lines) == 1:
                            # Single line with multiple authors - return None
                            return (None, has_multiple)
                        else:
                            return (author_lines[-1], has_multiple)
                    break

        # Second priority: look for bold author name in the header
        header_table = soup.find('table', style=re.compile(r'background:#F2F9F2'))
        if header_table:
            bold_text = header_table.find('b')
            if bold_text:
                author_text = bold_text.get_text(strip=True)
                if author_text and '全唐詩' not in author_text:
                    authors = author_text.split()
                    has_multiple = len(authors) > 1
                    return (authors[0] if authors else author_text, has_multiple)

            # if no bold text, try to extract plain text after plainSister ul
            # This handles anthology volumes like 217-234 (Du Fu) where author is plain text
            # Format: <div><ul id="plainSister">...</ul> AuthorName</div>
            plain_sister_ul = header_table.find('ul', id='plainSister')
            if plain_sister_ul:
                # Get the parent div
                parent_div = plain_sister_ul.find_parent('div')
                if parent_div:
                    # Remove the edition div (版本信息 link) if present
                    # This is a noprint div with id="edition" that contains version info
                    parent_div_copy = parent_div.__copy__()
                    edition_div = parent_div_copy.find('div', id='edition')
                    if edition_div:
                        edition_div.decompose()

                    # Get  all text from the div
                    div_text = parent_div_copy.get_text(strip=True)
                    # Remove common unwanted strings
                    unwanted = ['姊妹計劃', '數據項', ':', '：', '姊妹计划', '数据项']
                    for unwanted_str in unwanted:
                        div_text = div_text.replace(unwanted_str, '')
                    div_text = div_text.strip()
                    # The remaining text should be the author name(s)
                    if div_text and '全唐詩' not in div_text:
                        # Check if this is a list of multiple authors (space or 、separated)
                        # (similar to volume 795/688 logic)
                        div_text_normalized = div_text.replace('、', ' ')
                        author_tokens = div_text_normalized.split()
                        # Use different thresholds: 、= 2+, spaces = 3+
                        has_dunhao = '、' in div_text
                        threshold = 2 if has_dunhao else 3
                        if len(author_tokens) >= threshold:
                            # multiple authors listed - this is a multi-author volume
                            has_multiple = True
                            separator = '、' if has_dunhao else 'spaces'
                            logger.debug(f"Detected multi-author volume from plainSister {separator}-separated text: {len(author_tokens)} names")
                            return (None, has_multiple)
                        elif len(div_text) <= 10:
                            # Single short author name
                            return (div_text, False)
                        # If text is long but < 5 tokens, it might be a single author with titles/notes
                        # Don't return it as it's likely not a clean author name

        # Final fallback: check for multiple H2 headers with biography pattern
        # This handles volumes with no header author info but multiple author sections
        h2_headers = soup.find_all('h2')
        biography_sections = []
        for h2 in h2_headers:
            h2_text = h2.get_text(strip=True)
            if any(skip in h2_text for skip in ['目次', '目录', '註釋', '注释', '全唐詩']):
                continue

            # h2 is wrapped in div.mw-heading, check next sibling of wrapper
            h2_wrapper = h2.parent
            if h2_wrapper and h2_wrapper.name == 'div':
                next_elem = h2_wrapper.find_next_sibling()
                if next_elem and next_elem.name == 'p':
                    bio_text = next_elem.get_text(strip=True)
                    # Biography mentions "詩X首" or "诗X首" (X poems)
                    if re.search(r'[詩诗].{1,3}首', bio_text):
                        biography_sections.append(h2_text)

        if len(biography_sections) > 1:
            logger.debug(f"Detected multi-author volume from {len(biography_sections)} H2 biography sections (fallback check)")
            return (None, True)

        return (None, False)

    def _extract_h1_author(self, element: Tag) -> Tuple[Optional[str], Optional[str]]:
        heading_div = element.find_parent('div', class_='mw-heading')
        if heading_div:
            h1_elem = heading_div.find('h1')
            if h1_elem:
                canonical, recorded = self.author_service.extract_author_from_element(h1_elem)

                # If no author link found, fall back to plain text content
                if not recorded:
                    recorded = h1_elem.get_text(strip=True)
                    recorded = re.sub(r'\[編輯\]', '', recorded).strip()
                    canonical = recorded
                else:
                    if recorded:
                        recorded = re.sub(r'\[編輯\]', '', recorded).strip()
                    if canonical:
                        canonical = re.sub(r'\[編輯\]', '', canonical).strip()

                if recorded and not any(skip in recorded for skip in ['編輯', '目次']):
                    logger.debug(f"Found author from h1: {canonical} (recorded as: {recorded})")
                    return canonical, recorded

        return None, None

    def _extract_h2(self, element: Tag, page_author: Optional[str], has_multiple_authors: bool, current_author: Optional[str] = None) -> Tuple[Optional[str], Optional[str], bool, Optional[str], Optional[str], List[Dict]]:
        """Extract author or title from h2 element.

        Returns:
            (canonical, recorded, is_author, bio_note, embedded_author, title_notes)

        embedded_author is set when h2 contains both title and author in format:
        <h2>Title<small>〈AuthorName〉</small></h2> (common in Yuefu volumes 10-29)

        title_notes is a list of notes extracted from <small> tags that contain
        title subtitles/variants (一作, 缺字, months, seasons) rather than authors.
        """
        heading_div = element.find_parent('div', class_='mw-heading')
        if not heading_div:
            return None, None, False, None, None, []

        h2_elem = heading_div.find('h2')
        if not h2_elem:
            return None, None, False, None, None, []

        # extract content from <small> tag before removing it
        # Three possible formats:
        # 1. <h2>AuthorName<small>〈biographical note〉</small></h2> - bio note (longer, contains 《》 or 詩X首)
        # 2. <h2>Title<small>〈AuthorName〉</small></h2> - embedded author (short, 2-5 chars)
        # 3. <h2>Title<small>〈subtitle/variant〉</small>More</h2> - title note (一作, 缺字, month, season)
        bio_note = None
        embedded_author = None
        small_title_notes = []  # Title notes extracted from small tags
        h2_copy = h2_elem.__copy__()
        small_tag = h2_copy.find('small')
        if small_tag:
            small_text = small_tag.get_text(strip=True)
            # Remove angle brackets
            small_text = re.sub(r'^[〈<]', '', small_text)
            small_text = re.sub(r'[〉>]$', '', small_text)

            # Extract context: text immediately before the small tag
            # For "和王卿〈一作太常〉立秋即事", context would be "王卿" (chars before small)
            small_context = None
            if small_tag.previous_sibling:
                prev_text = small_tag.previous_sibling
                if hasattr(prev_text, 'get_text'):
                    prev_text = prev_text.get_text(strip=True)
                elif isinstance(prev_text, str):
                    prev_text = prev_text.strip()
                else:
                    prev_text = ''
                # Take last 2-5 characters as context
                if prev_text:
                    small_context = prev_text[-5:] if len(prev_text) > 5 else prev_text

            if small_text:
                # author names: short (2-5 chars), no book titles 《》, no complex patterns
                # NOT author names:
                # - Bio notes: contain book titles, or contain patterns like 詩X首
                # - Variant notes: "一作" (alternatively written as), "一本" (one edition has)
                # - Missing text indicators: 缺X字 (one/two/etc characters missing)
                # - Temporal subtitles: months (X月), seasons (春/夏/秋/冬, 季春, 仲夏, etc.)
                # - Preface markers: 并序, 並序 (with preface)
                # - Location notes: 在X (at/in location)
                # - Date/composition notes: X年, X年作 (written in year X)
                # - Poem counts: X首 (X poems)
                # - Time/place words ending in 夜 (night)
                # - Boudoir poetry terms containing 閨
                is_title_subtitle = (
                    small_text.startswith('一作') or  # Variant reading notes ("alternatively written as")
                    small_text.startswith('一本') or  # Edition variant notes ("one edition has/lacks")
                    small_text.startswith('在') or  # Location notes ("at/in X")
                    small_text.endswith('首') or  # Poem counts (三首, 兩首, etc.)
                    small_text.endswith('夜') or  # Time markers ending in "night"
                    '閨' in small_text or  # Boudoir poetry terms (閨恨, 閨意, 夜閨)
                    re.search(r'缺.字', small_text) or  # Missing character indicators
                    re.search(r'^[一二三四五六七八九十]+月$', small_text) or  # Month names
                    re.search(r'^(孟|仲|季)?(春|夏|秋|冬)$', small_text) or  # Seasonal names
                    re.search(r'年', small_text) or  # Date notes containing "year"
                    small_text.endswith('作') or  # Composition notes ending with "written"
                    small_text in ('其一', '其二', '其三', '其四', '其五') or  # Part numbers
                    small_text in ('并序', '並序', '序', '有序') or  # Preface markers
                    small_text in ('雜言', '生查子', '鞦韆', '春盡', '再青春')  # Known non-name terms
                )
                # Author  names: typically 2-3 Chinese characters, no special patterns
                # Most Tang dynasty names are surname (1 char) + given name (1-2 chars)
                is_author_name = (
                    2 <= len(small_text) <= 3 and  # Restrict to 2-3 chars (typical name length)
                    '《' not in small_text and
                    '》' not in small_text and
                    not re.search(r'詩.+首', small_text) and
                    not re.search(r'存詩', small_text) and
                    not re.search(r'有《', small_text) and
                    not is_title_subtitle and  # Exclude known title subtitles
                    '、' not in small_text and  # Lists of items
                    '，' not in small_text  # Sentences with commas
                )
                if is_author_name:
                    embedded_author = small_text
                    logger.debug(f"Detected embedded author '{small_text}' in h2 title")
                elif is_title_subtitle:
                    # Create a title note with context
                    note_type = 'title_variant' if small_text.startswith('一作') else 'title_note'
                    small_title_notes.append({
                        'type': note_type,
                        'content': small_text,
                        'context': small_context
                    })
                    logger.debug(f"Extracted title note '{small_text}' with context '{small_context}'")
                else:
                    bio_note = small_text
            small_tag.decompose()

        # Extract footnote references before removing them (for later processing)
        footnote_refs = []
        for sup in h2_copy.find_all('sup', class_='reference'):
            # Get the href to find the footnote ID
            link = sup.find('a')
            if link and link.get('href'):
                href = link.get('href')
                # extract footnote ID from href like "#cite_note-1"
                if href.startswith('#'):
                    footnote_id = href[1:]  # Remove the # prefix
                    footnote_refs.append(footnote_id)
            sup.decompose()

        # Also remove standalone footnote links (not inside <sup>)
        # these are <a href="#cite_note-X">[X]</a> elements
        for link in h2_copy.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('#cite_note-'):
                # This is a footnote link, extract the ID and remove it
                footnote_id = href[1:]  # Remove the # prefix
                if footnote_id not in footnote_refs:
                    footnote_refs.append(footnote_id)
                link.decompose()

        canonical, recorded = self.author_service.extract_author_from_element(h2_copy)

        # If no link found, extract raw text for category name detection
        if not recorded:
            h2_text = h2_copy.get_text(strip=True)
            h2_text = re.sub(r'\[編輯\]', '', h2_text).strip()

            # Remove volume section markers like （一）, （二）, （三）, etc.
            # These appear in multi-volume author collections (e.g., "貫休（一）")
            # Pattern: parenthesized Chinese number at the end
            h2_text = re.sub(r'[（(][一二三四五六七八九十百千萬]+[）)]$', '', h2_text).strip()

            # Format: "AuthorName〈詩N首〉" means "N poems by AuthorName"
            # Pattern: 〈詩 + number + 首〉 at the end
            h2_text = re.sub(r'[〈<]詩[一二三四五六七八九十百千萬]+首[〉>]$', '', h2_text).strip()

            if h2_text and not any(skip in h2_text for skip in ['編輯', '目次']):
                recorded = h2_text
                canonical = h2_text

        if recorded:
            recorded = re.sub(r'\[編輯\]', '', recorded).strip()
            # Strip volume section markers like （一）, （二）from author names
            recorded = re.sub(r'[（(][一二三四五六七八九十百千萬]+[）)]$', '', recorded).strip()
            # Strip anthology markers like 〈詩五十七首〉 from author names
            recorded = re.sub(r'[〈<]詩[一二三四五六七八九十百千萬]+首[〉>]$', '', recorded).strip()
        if canonical:
            canonical = re.sub(r'\[編輯\]', '', canonical).strip()
            # Strip volume section markers like （一）, （二）from author names
            canonical = re.sub(r'[（(][一二三四五六七八九十百千萬]+[）)]$', '', canonical).strip()
            # Strip anthology markers like 〈詩五十七首〉 from author names
            canonical = re.sub(r'[〈<]詩[一二三四五六七八九十百千萬]+首[〉>]$', '', canonical).strip()

        if not recorded or any(skip in recorded for skip in ['編輯', '目次']):
            return None, None, False, None, None, []

        # Category names that should always be treated as titles, not authors
        # Even if they have Author: links in Wikisource
        CATEGORY_NAMES = {'郊廟歌辭', '樂府雜曲', '橫吹曲辭', '相和歌辭', '舞曲歌辭', '琴曲歌辭', '雜曲歌辭', '新樂府'}

        # Check if this is a known category name
        if recorded in CATEGORY_NAMES or canonical in CATEGORY_NAMES:
            is_author = False
            logger.debug(f"Found category title from h2: {recorded}")
            return canonical, recorded, is_author, None, embedded_author, small_title_notes

        link = h2_copy.find('a')
        has_author_link = link and 'Author:' in link.get('href', '')
        has_any_link = link is not None

        # Check if this H2 has an anthology marker (before stripping)
        # Format: "AuthorName〈詩N首〉" - if present, this is always an author heading
        raw_h2_text = h2_copy.get_text(strip=True)
        has_anthology_marker = bool(re.search(r'[〈<]詩[一二三四五六七八九十百千萬]+首[〉>]', raw_h2_text))

        # If h2 has embedded_author, this is definitely a title (not an author heading)
        if embedded_author:
            is_author = False
        # If h2 has a non-Author link, it's almost certainly a title
        elif has_any_link and not has_author_link:
            is_author = False
        else:
            # If we already have a current author (e.g., from h1), don't treat h2 as author
            # unless it has strong indicators (author link, anthology marker, or multi-author volume)
            if current_author and not has_author_link and not has_anthology_marker and not has_multiple_authors:
                is_author = False
            else:
                is_author = (has_author_link or
                            has_anthology_marker or  # Anthology format H2s are always authors
                            (has_multiple_authors and not has_any_link) or
                            (page_author is None and not has_any_link and 2 <= len(recorded) <= 5))

        if is_author:
            logger.debug(f"Found author from h2: {canonical} (recorded as: {recorded})")
            if bio_note:
                logger.debug(f"  Extracted bio note: {bio_note}")
        else:
            logger.debug(f"Found parent title from h2: {recorded}")
            if embedded_author:
                logger.debug(f"  With embedded author: {embedded_author}")

        return canonical, recorded, is_author, bio_note, embedded_author, small_title_notes

    def extract_footnote_content(self, soup: BeautifulSoup, footnote_id: str) -> Optional[str]:
        """
        Extract footnote content from the references section.

        Args:
            soup: BeautifulSoup object of the page
            footnote_id: The footnote ID (e.g., "cite_note-1")

        Returns:
            The footnote text content, or None if not found
        """
        # Find the footnote in the references list
        footnote_elem = soup.find('li', id=footnote_id)
        if not footnote_elem:
            return None

        # Extract text from the reference-text span
        ref_text_span = footnote_elem.find('span', class_='reference-text')
        if ref_text_span:
            # Get text and strip the backlink arrow
            text = ref_text_span.get_text(strip=True)
            return text

        return None

    def _extract_h3_title(self, element: Tag, parent_title: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[Tag], List[str]]:
        """Extract title from h3 element. Returns (current_title, parent_h3_title, heading_div, title_notes)."""
        heading_div = element.find_parent('div', class_='mw-heading')
        if not heading_div:
            return None, None, None, []

        h3_elem = heading_div.find('h3')
        if not h3_elem:
            return None, None, None, []

        # Extract footnote references before removing them
        # These are citation markers like [1], [2] that reference footnotes at the bottom
        footnote_refs = []
        h3_copy = h3_elem.__copy__()
        for sup in h3_copy.find_all('sup', class_='reference'):
            # Get the href to find the footnote ID
            link = sup.find('a')
            if link and link.get('href'):
                href = link.get('href')
                # Extract  footnote ID from href like "#cite_note-1"
                if href.startswith('#'):
                    footnote_id = href[1:]  # Remove the # prefix
                    footnote_refs.append(footnote_id)
            sup.decompose()

        # Also remove standalone footnote links (not inside <sup>)
        # These are <a href="#cite_note-X">[X]</a> elements
        for link in h3_copy.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('#cite_note-'):
                # This is a footnote link, extract the ID and remove it
                footnote_id = href[1:]  # Remove the # prefix
                if footnote_id not in footnote_refs:
                    footnote_refs.append(footnote_id)
                link.decompose()

        # Always  use the full h3 text, not just the first link's text
        # This handles cases where the h3 contains:
        # - The full title text with an author link in parentheses: "Title（Author）"
        # - Just a link wrapping the entire title: "<a>Title</a>"
        # Getting all text ensures we capture the complete title
        h3_text = h3_copy.get_text(strip=True)

        h3_text = re.sub(r'\[編輯\]', '', h3_text).strip()

        # Extract parenthetical notes from title (like 一作 variants)
        h3_text, title_notes = self.extract_title_notes(h3_text)

        # Extract footnote content and add to title notes
        if footnote_refs:
            # Get the soup from the heading_div's parent chain
            soup = heading_div.find_parent('html') or heading_div.find_parent()
            while soup and soup.parent:
                soup = soup.parent

            for footnote_id in footnote_refs:
                footnote_text = self.extract_footnote_content(soup, footnote_id)
                if footnote_text:
                    # Add footnote as a note
                    footnote_note = {
                        'content': footnote_text,
                        'context': h3_text,
                        'original_title': h3_text,
                        'type': 'footnote'
                    }
                    title_notes.append(footnote_note)
                    logger.debug(f"Extracted footnote for '{h3_text}': {footnote_text}")

        parent_h3_title = h3_text

        # Combine  with h2 parent title if it exists
        if parent_title:
            current_title = f"{parent_title} {h3_text}"
        else:
            current_title = h3_text

        logger.debug(f"Found h3 title: {current_title}" + (f" (with {len(title_notes)} notes)" if title_notes else ""))
        return current_title, parent_h3_title, heading_div, title_notes

    def _extract_h4_subtitle(self, element: Tag, parent_h3_title: Optional[str],
                            current_author_canonical: Optional[str],
                            current_author_recorded: Optional[str],
                            volume_num: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract subtitle from h4 element. Returns (current_title, author_canonical, author_recorded)."""
        heading_div = element.find_parent('div', class_='mw-heading')
        if not heading_div:
            return None, current_author_canonical, current_author_recorded

        h4_elem = heading_div.find('h4')
        if not h4_elem:
            return None, current_author_canonical, current_author_recorded

        # Make a copy and remove footnote markers before extracting text
        h4_copy = h4_elem.__copy__()
        for sup in h4_copy.find_all('sup', class_='reference'):
            sup.decompose()

        # Also remove standalone footnote links (not inside <sup>)
        # These are <a href="#cite_note-X">[X]</a> elements
        for link in h4_copy.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('#cite_note-'):
                # This is a footnote link, remove it
                link.decompose()

        h4_text = h4_copy.get_text(strip=True)
        h4_text = re.sub(r'\[編輯\]', '', h4_text).strip()

        # Check if h4 has author in parentheses: "慶和 (趙光逢)"
        author_match = re.match(r'^(.+?)\s*\((.+?)\)\s*$', h4_text)
        if author_match:
            h4_subtitle = author_match.group(1).strip()
            h4_author = author_match.group(2).strip()

            h4_canonical, h4_recorded = self.author_service.extract_author_from_element(h4_copy)
            if h4_canonical:
                current_author_canonical = h4_canonical
                current_author_recorded = h4_recorded or h4_author
            else:
                current_author_canonical = h4_author
                current_author_recorded = h4_author

            logger.debug(f"Found h4 subtitle with author: {h4_subtitle} ({h4_author})")
        else:
            h4_subtitle = h4_text
            # Check if h4 has an author link (without parentheses)
            h4_canonical, h4_recorded = self.author_service.extract_author_from_element(h4_copy)
            if h4_canonical and h4_canonical != h4_subtitle:
                # Has  an author link that's different from the title
                current_author_canonical = h4_canonical
                current_author_recorded = h4_recorded
                logger.debug(f"Found h4 subtitle with linked author: {h4_subtitle} (author: {h4_canonical})")
            else:
                # No author specified in h4
                # For ritual music volumes (10-16), pieces are often anonymous - default to Unknown
                # For other volumes (e.g., Buddhist clergy 806+), preserve H2 author
                is_ritual_music = 10 <= volume_num <= 16

                if is_ritual_music or not current_author_canonical or current_author_canonical == "Unknown":
                    # Ritual music pieces or no existing author - use Unknown
                    current_author_canonical = "Unknown"
                    current_author_recorded = "Unknown"
                    logger.debug(f"Found h4 subtitle without author: {h4_subtitle}")
                else:
                    # Keep existing author from h2 (e.g., Buddhist clergy volumes)
                    logger.debug(f"Found h4 subtitle, keeping h2 author: {h4_subtitle} (author: {current_author_canonical})")

        # Combine h3 + h4 as title
        if parent_h3_title:
            current_title = f"{parent_h3_title} {h4_subtitle}"
        else:
            current_title = h4_subtitle

        logger.debug(f"Combined h3+h4 title: {current_title}")
        return current_title, current_author_canonical, current_author_recorded

    def _extract_bare_p_poem(self, heading_div: Tag, current_title: Optional[str],
                            current_author_canonical: Optional[str],
                            current_author_recorded: Optional[str],
                            volume_num: int, entry_index: int,
                            pending_notes: List[str],
                            preface: Optional[str] = None,
                            is_numbered_part: bool = False,
                            parent_entry_index: Optional[int] = None,
                            parent_part_counter: int = 0) -> Optional[dict]:
        """Extract poem from bare p tag after h3."""
        logger.debug(f"_extract_bare_p_poem called for '{current_title}': is_numbered_part={is_numbered_part}, has_preface={bool(preface)}, preface_len={len(preface) if preface else 0}")
        next_elem = heading_div.next_sibling
        while next_elem and not (hasattr(next_elem, 'name') and next_elem.name):
            next_elem = next_elem.next_sibling

        if not (next_elem and next_elem.name == 'p' and current_title and
                next_elem.parent.get('class') != ['poem']):
            return None

        # Check if this is a PURE annotation paragraph (only contains annotation, no poem text)
        # vs an inline annotation (poem text with embedded <small> note)
        small_tag = next_elem.find('small')
        if small_tag:
            # Get the full paragraph text including the small tag
            full_text = next_elem.get_text(strip=True)
            # Get just the annotation text
            annotation_text = small_tag.get_text(strip=True)

            # If the paragraph is ONLY the annotation (no other substantive text), skip it
            # otherwise, the <small> is an inline note and we should process the whole paragraph as poem
            remaining_text = full_text.replace(annotation_text, '').strip()

            # Remove common annotation markers to check if there's actual content
            remaining_text = remaining_text.replace('〈', '').replace('〉', '').replace('《', '').replace('》', '').strip()

            if not remaining_text or len(remaining_text) < 5:
                # this is a pure annotation paragraph - skip it and look for the next <p> tag
                if annotation_text:
                    # don't add angle bracket editorial notes 〈...〉 to pending_notes
                    # These are already extracted as prefaces and shouldn't be duplicated as notes
                    if not (annotation_text.startswith('〈') and annotation_text.endswith('〉')):
                        pending_notes.append(annotation_text)
                        logger.debug(f"Found pure annotation paragraph: {annotation_text[:50]}...")
                    else:
                        logger.debug(f"Skipping angle bracket editorial note (already in preface): {annotation_text[:50]}...")

                next_elem = next_elem.next_sibling
                while next_elem and not (hasattr(next_elem, 'name') and next_elem.name):
                    next_elem = next_elem.next_sibling

                # If next element is not a <p> tag, there's no poem content
                if not (next_elem and next_elem.name == 'p'):
                    return None
            else:
                # This paragraph has both poem text AND inline annotation - process it as a poem
                # The inline annotation will be handled later when we parse the poem text
                logger.debug(f"Found inline annotation in poem text: {annotation_text[:30]}... (continuing to extract poem)")

        # Extract poem from ALL consecutive bare p tags
        # Some volumes (e.g., 851) have poems split across multiple p tags
        poem_lines = []
        current_elem = next_elem

        while current_elem:
            # Stop if we hit a heading
            if current_elem.name == 'div' and 'mw-heading' in current_elem.get('class', []):
                break

            # Process p tags
            if current_elem.name == 'p' and 'poem' not in current_elem.parent.get('class', []):
                poem_text = current_elem.get_text(strip=True)

                # Stop if this looks like navigation or metadata
                if not poem_text or poem_text.startswith('←') or poem_text.startswith('→'):
                    break
                if any(marker in poem_text for marker in ['全唐詩', '上一卷', '下一卷']):
                    break

                # Check if this paragraph consists ONLY of parenthetical content
                # Pattern: entire text is wrapped in parentheses like "（梁公玄孫旅於南國。）"
                only_parens_match = re.fullmatch(r'[（(〈<]([^）)〉>]+)[）)〉>]', poem_text)
                if only_parens_match:
                    # This is a standalone annotation paragraph - add to pending notes
                    note_content = only_parens_match.group(1).strip()
                    note_dict = {
                        'content': note_content,
                        'context': current_title,
                        'original_title': current_title
                    }
                    pending_notes.append(note_dict)
                    logger.debug(f"Found standalone annotation paragraph: '{note_content}' for title '{current_title}'")
                    # Move to next element and continue
                    current_elem = current_elem.next_sibling
                    while current_elem and not (hasattr(current_elem, 'name') and current_elem.name):
                        current_elem = current_elem.next_sibling
                    continue

                # FIRST:  Extract all parenthetical content (variants and notes) from the paragraph
                # before splitting by punctuation. This prevents splitting punctuation inside parens.
                # Use placeholders to track positions so we can map to line indices later.
                paren_pattern = re.compile(r'([（(])([^）)]+)([）)])')
                paren_matches = list(paren_pattern.finditer(poem_text))

                # track variants and notes for this paragraph with placeholders
                paragraph_items = []  # List of (placeholder, item_dict)
                cleaned_poem_text = poem_text

                for idx, match in enumerate(paren_matches):
                    paren_content = match.group(2)
                    full_match = match.group(0)
                    placeholder = f'__PAREN_{len(paragraph_items)}__'

                    # Check if this is a variant marker (一作... or 作...)
                    if paren_content.startswith('一作') or paren_content.startswith('作'):
                        # This is a variant - store it with placeholder
                        variant_match = re.match(r'([一]?作)(.+)', paren_content)
                        if variant_match:
                            variant_text = variant_match.group(2)
                            # Find the text before this variant
                            text_before_paren = poem_text[:match.start()]
                            variant_chars = len(variant_text)
                            if variant_chars > 0 and len(text_before_paren) >= variant_chars:
                                original_text = text_before_paren[-variant_chars:]
                            else:
                                original_text = text_before_paren
                            paragraph_items.append({
                                'type': 'variant',
                                'placeholder': placeholder,
                                'text': original_text,
                                'variant': variant_text,
                                'source': '一作'
                            })
                    else:
                        # This is a note/annotation - store it with placeholder
                        # Context will be set later from the cleaned line
                        paragraph_items.append({
                            'type': 'note',
                            'placeholder': placeholder,
                            'content': paren_content
                        })

                # Replace parenthetical content with placeholders
                for match in reversed(paren_matches):
                    match_idx = len(paren_matches) - paren_matches[::-1].index(match) - 1
                    if match_idx < len(paragraph_items):
                        placeholder = paragraph_items[match_idx]['placeholder']
                        cleaned_poem_text = cleaned_poem_text[:match.start()] + placeholder + cleaned_poem_text[match.end():]

                # NOW split by punctuation (parenthetical content replaced with placeholders)
                parts = re.split(r'([，。！？；：])', cleaned_poem_text)
                paragraph_start_line_idx = len(poem_lines)  # Track where this paragraph starts
                current_line = ''
                for part in parts:
                    if part in '，。！？；：':
                        current_line += part
                        if current_line.strip():
                            poem_lines.append(current_line.strip())
                        current_line = ''
                    else:
                        current_line += part
                if current_line.strip():
                    poem_lines.append(current_line.strip())

                # Map placeholders to line indices and clean them
                for i in range(paragraph_start_line_idx, len(poem_lines)):
                    for item in paragraph_items:
                        placeholder = item['placeholder']
                        if placeholder in poem_lines[i]:
                            # Remove placeholder from line first to get clean context
                            cleaned_line = poem_lines[i].replace(placeholder, '').strip()

                            # Found the placeholder in this line
                            if item['type'] == 'variant':
                                # Store variant with line index (1-based)
                                if not hasattr(self, '_temp_variants'):
                                    self._temp_variants = []
                                self._temp_variants.append({
                                    'line': i + 1,  # Convert to 1-based
                                    'text': item['text'],
                                    'variant': item['variant'],
                                    'source': item['source']
                                })
                            else:  # note
                                # Store note with line index (1-based) and context from cleaned line
                                if not hasattr(self, '_temp_notes'):
                                    self._temp_notes = []
                                self._temp_notes.append({
                                    'line': i + 1,  # Convert to 1-based
                                    'content': item['content'],
                                    'context': cleaned_line  # Use the cleaned line as context
                                })

                            # Update the line with cleaned version
                            poem_lines[i] = cleaned_line

            # Move to next sibling
            current_elem = current_elem.find_next_sibling()
            if not current_elem:
                break

            while current_elem and not (hasattr(current_elem, 'name') and current_elem.name):
                current_elem = current_elem.find_next_sibling()

        if not poem_lines:
            return None

        # Collect variants and notes from temp lists (already extracted during paragraph processing)
        variants = getattr(self, '_temp_variants', [])
        notes_with_context = getattr(self, '_temp_notes', [])

        if hasattr(self, '_temp_variants'):
            del self._temp_variants
        if hasattr(self, '_temp_notes'):
            del self._temp_notes

        # Add extracted notes to pending_notes (now with line and context info)
        if notes_with_context:
            pending_notes.extend(notes_with_context)

        # Check if preface is just the poem text itself (common in bare p poems)
        # If so, don't include it as a preface
        if preface:
            # Rmove ALL parenthetical content (variants and notes) from preface for fair comparison
            preface_for_compare = re.sub(r'[（(][^）)]+[）)]', '', preface)
            preface_for_compare = preface_for_compare.replace(' ', '').replace('\n', '')

            # Reconstruct poem text
            poem_as_text = ''.join(poem_lines)
            poem_for_compare = poem_as_text.replace(' ', '').replace('\n', '')

            # If they mtach, this isn't a real preface - it's just the poem itself
            if preface_for_compare == poem_for_compare or preface_for_compare in poem_for_compare:
                preface = None

        # Check if title has author in angle brackets (format: "Title〈Author〉")
        # Common in yuefu volumes 10-29, particularly volume 28
        if (current_title and
            (not current_author_canonical or current_author_canonical == "Unknown") and
            10 <= volume_num <= 29):

            # match pattern: "TitleName〈AuthorName〉" or "TitleName（AuthorName）"
            author_in_title_match = re.search(r'[〈（(]([^〉）)]+)[〉）)]$', current_title)
            if author_in_title_match:
                author_name = author_in_title_match.group(1).strip()
                # Make sure it looks like an author name (2-5 characters, no punctuation)
                has_no_punctuation = not any(p in author_name for p in '。，！？；：、""''《》')
                is_reasonable_length = 2 <= len(author_name) <= 5

                if has_no_punctuation and is_reasonable_length:
                    # extract author from title - normalize for canonical, keep original for recorded
                    current_author_canonical, current_author_recorded = parse_author_name(author_name)
                    # Rmove author part from title
                    current_title = re.sub(r'[〈（(][^〉）)]+[〉）)]$', '', current_title).strip()
                    logger.debug(f"Extracted author from title: {author_name} (canonical: {current_author_canonical}), cleaned title: {current_title}")

        # Check if first line is an author name (common in yuefu volumes 10-29)
        # In these volumes, poems with the same title by different authors are listed
        # sequentially with the author name as the first line
        if (poem_lines and
            (not current_author_canonical or current_author_canonical == "Unknown") and
            10 <= volume_num <= 29):

            first_line = poem_lines[0].strip()

            # Author name characteristics:
            # - No punctuation marks (。，！？；：、etc.)
            # - Relatively short (2-5 characters typical for Chinese names)
            # - Not empty or whitespace only
            has_no_punctuation = not any(p in first_line for p in '。，！？；：、""''《》〈〉（）()[]【】')
            is_short = 2 <= len(first_line) <= 5
            is_not_empty = len(first_line.strip()) > 0

            if has_no_punctuation and is_short and is_not_empty:
                # Exract first line as author - normalize for canonical, keep original for recorded
                current_author_canonical, current_author_recorded = parse_author_name(first_line)
                # Remove author name from poem lines
                poem_lines = poem_lines[1:]
                logger.debug(f"Extracted author from first line: {first_line} (canonical: {current_author_canonical})")

        # First, collapse multi-line angle bracket annotations 〈〉 into single lines
        # This handles cases where brackets span multiple lines:
        # - "擲瓦名婠妠〈上一丸切，"
        # - "下奴荅切。"
        # - "〉。"
        # Should become: "擲瓦名婠妠〈上一丸切，下奴荅切。〉。"
        collapsed_lines = []
        i = 0
        while i < len(poem_lines):
            line = poem_lines[i]
            # Check if line contains an opening bracket without a closing bracket
            if '〈' in line and '〉' not in line:
                # Start accumulating lines until we find the closing bracket
                accumulated = [line]
                i += 1
                while i < len(poem_lines):
                    next_line = poem_lines[i]
                    accumulated.append(next_line)
                    if '〉' in next_line:
                        # Found closing bracket - stop accumulating
                        i += 1
                        break
                    i += 1
                # Join accumulated lines into a single line
                collapsed_line = ''.join(accumulated)
                collapsed_lines.append(collapsed_line)
            else:
                # Line is complete (has both brackets or no brackets)
                collapsed_lines.append(line)
                i += 1

        # Now extract notes from collapsed lines using separate_annotation
        extracted_notes = []
        cleaned_lines = []
        for line in collapsed_lines:
            # Handle lines that start with just 〈 (standalone note lines)
            if line.startswith('〈'):
                # Extract the note content
                poem_part, note_part = text_utils.separate_annotation(line)
                if note_part:
                    # Use poem_part as context if available, otherwise use title
                    context = poem_part if poem_part else current_title
                    # For standalone notes, associate with previous line or 0 if no lines yet
                    line_idx = len(cleaned_lines) if cleaned_lines else 0
                    extracted_notes.append({
                        'line': line_idx,
                        'content': note_part,
                        'context': context
                    })
                    logger.debug(f"Extracted standalone angle bracket note: {note_part[:50]}...")
                # If there's poem content before or after, keep it
                if poem_part:
                    cleaned_lines.append(poem_part)
            else:
                # Regular line - may contain inline annotation
                poem_part, note_part = text_utils.separate_annotation(line)
                if poem_part:
                    cleaned_lines.append(poem_part)
                if note_part:
                    # Note is associated with the current line (just added)
                    extracted_notes.append({
                        'line': len(cleaned_lines),
                        'content': note_part,
                        'context': poem_part
                    })
                    logger.debug(f"Extracted inline angle bracket note: {note_part[:50]}...")

        # Use cleaned lines for the poem
        poem_lines = cleaned_lines

        # Combine all notes
        all_notes = pending_notes.copy() if pending_notes else []
        all_notes.extend(extracted_notes)

        # Handle multi-part logic
        if is_numbered_part:
            if parent_entry_index is None:
                entry_index += 1
                parent_entry_index = entry_index
            parent_part_counter += 1
            part_index = parent_part_counter
            final_entry_index = parent_entry_index
            # Only attach preface to part 1
            final_preface = preface if part_index == 1 else None
        else:
            entry_index += 1
            final_entry_index = entry_index
            part_index = 1  # For UID generation, always use 1 for non-numbered parts
            final_preface = preface

        author = self.author_service.create_author(current_author_canonical, current_author_recorded, volume_num)
        poem = Poem(
            uid=self.generate_uid(volume_num, final_entry_index, part_index),
            volume=volume_num,
            author=author,
            title=current_title,
            poem=poem_lines,
            notes=all_notes if all_notes else None,
            preface=final_preface,
            part_index=part_index if is_numbered_part else None,
            variants=variants if variants else None
        )

        logger.debug(f"Extracted bare p poem: {current_title} by {current_author_canonical} ({len(poem_lines)} lines)")
        return {
            'poem': poem,
            'entry_index': entry_index,
            'pending_notes': [],
            'parent_entry_index': parent_entry_index if is_numbered_part else None,
            'parent_part_counter': parent_part_counter if is_numbered_part else 0
        }

    def _extract_from_pre_tag(self, heading_div: Tag, current_title: Optional[str],
                              current_author_canonical: Optional[str],
                              current_author_recorded: Optional[str],
                              volume_num: int, entry_index: int,
                              pending_notes: List[str],
                              preface: Optional[str] = None,
                              is_numbered_part: bool = False,
                              parent_entry_index: Optional[int] = None,
                              parent_part_counter: int = 0) -> Optional[dict]:
        """Extract poem from <pre> tag after heading."""
        logger.debug(f"_extract_from_pre_tag called for '{current_title}'")

        # Find next <pre> element after the heading, skipping anotation <p> tags
        next_elem = heading_div.next_sibling
        while next_elem and not (hasattr(next_elem, 'name') and next_elem.name):
            next_elem = next_elem.next_sibling

        # to find the <pre> tag
        while next_elem:
            if next_elem.name == 'pre':
                # Found the pre tag!
                break
            elif next_elem.name == 'p':
                # Check if this is an annotation paragraph
                # Annotation paragraphs typically contain <small> tags with editorial notes
                small_tag = next_elem.find('small')
                if small_tag:
                    # This is an annotation, skip it and continue looking for <pre>
                    annotation_text = small_tag.get_text(strip=True)
                    # Extract and save annotation if it's not an editorial note
                    if not (annotation_text.startswith('〈') and annotation_text.endswith('〉')):
                        pending_notes.append(annotation_text)
                        logger.debug(f"Found annotation before <pre>: {annotation_text[:50]}...")
                    next_elem = next_elem.next_sibling
                    while next_elem and not (hasattr(next_elem, 'name') and next_elem.name):
                        next_elem = next_elem.next_sibling
                    continue
                else:
                    # Not an annotation, stop looking
                    break
            elif next_elem.name == 'div' and 'mw-heading' in next_elem.get('class', []):
                # Hit another heading, stop
                break
            else:
                # Some other element, stop
                break

        # Check if we found a <pre> tag with content
        if not (next_elem and next_elem.name == 'pre' and current_title):
            logger.debug(f"No <pre> tag found after heading for '{current_title}'")
            return None

        # Exract text from <pre> tag - it preserves whitespace and line breaks
        pre_text = next_elem.get_text()

        # split by newlines to get individual lines
        raw_lines = [line.strip() for line in pre_text.split('\n') if line.strip()]

        if not raw_lines:
            logger.debug(f"<pre> tag is empty for '{current_title}'")
            return None

        logger.debug(f"Extracted {len(raw_lines)} raw lines from <pre> tag for '{current_title}'")

        # Process each line to extract notes wrapped in 〈 〉 brackets
        lines = []
        extracted_notes = []
        for raw_line in raw_lines:
            # Check if this line contains an annotation
            poem_part, note_part = text_utils.separate_annotation(raw_line)

            if poem_part:
                lines.append(text_utils.clean_line(poem_part))
            if note_part:
                # Use poem_part as context if available, otherwise use title
                context = text_utils.clean_line(poem_part) if poem_part else current_title
                # Note is associated with the current line (1-indexed)
                extracted_notes.append({
                    'line': len(lines) if lines else 0,
                    'content': text_utils.clean_line(note_part),
                    'context': context
                })

        logger.debug(f"After note extraction: {len(lines)} poem lines, {len(extracted_notes)} notes for '{current_title}'")

        # handle multi-part logic for numbered parts
        if is_numbered_part:
            if parent_entry_index is None:
                entry_index += 1
                parent_entry_index = entry_index
            parent_part_counter += 1
            part_index = parent_part_counter
            final_entry_index = parent_entry_index
        else:
            entry_index += 1
            final_entry_index = entry_index
            part_index = None

        final_title = current_title
        author = self.author_service.create_author(current_author_canonical, current_author_recorded, volume_num)

        # Combine pending notes with extracted notes from poem lines
        all_notes = pending_notes.copy() if pending_notes else []
        all_notes.extend(extracted_notes)

        # Only attach preface to part 1 for numbered parts
        final_preface = preface if (not is_numbered_part or part_index == 1) else None

        poem = Poem(
            uid=self.generate_uid(volume_num, final_entry_index, part_index if is_numbered_part else 1),
            volume=volume_num,
            author=author,
            title=final_title,
            poem=lines,
            notes=all_notes if all_notes else None,
            preface=final_preface,
            part_index=part_index if is_numbered_part else None,
            variants=None
        )

        logger.debug(f"Extracted pre tag poem: {current_title} by {current_author_canonical} ({len(lines)} lines)")
        return {
            'poem': poem,
            'entry_index': entry_index,
            'pending_notes': [],
            'parent_entry_index': parent_entry_index if is_numbered_part else None,
            'parent_part_counter': parent_part_counter if is_numbered_part else 0
        }

    def _extract_from_poem_div(self, element: Tag, current_title: str,
                               current_author_canonical: Optional[str],
                               current_author_recorded: Optional[str],
                               volume_num: int, entry_index: int,
                               pending_notes: List[str],
                               preface: Optional[str] = None,
                               is_numbered_part: bool = False,
                               parent_entry_index: Optional[int] = None,
                               parent_part_counter: int = 0,
                               footnotes_dict: Dict[str, str] = None) -> Optional[dict]:
        """Extract poem(s) from div.poem element."""
        if footnotes_dict is None:
            footnotes_dict = {}

        poem_lines, notes, subtitle, variants, poem_footnotes = self.extract_poem_lines(element)

        # Add footnote content to notes with line context
        for fn in poem_footnotes:
            footnote_id = fn['id']
            line_idx = fn['line']
            if footnote_id in footnotes_dict:
                footnote_text = footnotes_dict[footnote_id]
                # Get the actual line text for context (clearer than line numbers)
                if 0 <= line_idx < len(poem_lines):
                    line_text = poem_lines[line_idx]
                    # Add as dict with line, content, and context (consistent with other notes)
                    notes.append({
                        'line': line_idx,
                        'content': footnote_text,
                        'context': line_text
                    })
                else:
                    # Fallback if line index is out of range - use title as context
                    notes.append({
                        'content': footnote_text,
                        'context': current_title
                    })
        if not poem_lines:
            return None

        poems = []
        entry_index += 1  # Increment once per title entry
        part_index = 1

        # Handle multi-part logic for numbered parts
        if is_numbered_part:
            if parent_entry_index is None:
                entry_index += 1
                parent_entry_index = entry_index
            parent_part_counter += 1
            part_index = parent_part_counter
            final_entry_index = parent_entry_index
        else:
            entry_index += 1  # Increment once per title entry
            final_entry_index = entry_index
            part_index = 1  # For UID generation, always use 1 for non-numbered parts

        # Check if this is a "句" (Verses/Fragments) section with multiple fragments
        if current_title == '句':
            # Volume 8 後主煜 句 section needs hardcoded splits
            if volume_num == 8 and current_author_recorded == '後主煜':
                # Filter empty lines and adjust variant indices to match
                clean_lines, adjusted_variants = text_utils.filter_empty_lines_with_variants(poem_lines, variants)

                for i, (title_suffix, start, end) in enumerate(volume_special_cases.VOLUME_8_HOUZHUYU_JU_FRAGMENT_SPLITS):
                    if end is None:
                        frag_lines = clean_lines[start:]
                        # For 1-indexed: lines from start+1 to len(clean_lines)
                        frag_variants = text_utils.extract_variants_for_range(
                            adjusted_variants, start + 1, len(clean_lines)
                        )
                    else:
                        frag_lines = clean_lines[start:end]
                        # For 1-indexed: lines from start+1 to end (end is exclusive in slice)
                        frag_variants = text_utils.extract_variants_for_range(
                            adjusted_variants, start + 1, end
                        )

                    if not frag_lines:
                        continue

                    # Attach ALL notes to first fragment only
                    # Post-processor will redistribute based on context mtaching
                    frag_notes = notes if i == 0 else None

                    title_to_use = f"{current_title} {title_suffix}"
                    author = self.author_service.create_author(current_author_canonical, current_author_recorded, volume_num)
                    frag_preface = preface if title_suffix == '其一' else None

                    poem = Poem(
                        uid=self.generate_uid(volume_num, final_entry_index, part_index),
                        volume=volume_num,
                        author=author,
                        title=title_to_use,
                        poem=frag_lines,
                        notes=frag_notes,
                        preface=frag_preface,
                        part_index=part_index,
                        variants=frag_variants
                    )
                    poems.append(poem)
                    logger.debug(f"Extracted fragment: {title_to_use}")
                    part_index += 1
            elif '' in poem_lines:
                # Generic fragment splitting (for other volumes)
                # First get variant indices adjusted for cleaned (no-empty) lines
                _, adjusted_variants = text_utils.filter_empty_lines_with_variants(poem_lines, variants)

                fragments = self.split_fragments(poem_lines, notes)

                # Track position in cleaned lines (1-indexed) to extract variants per fragment
                cleaned_line_idx = 1

                for i, (frag_lines, frag_notes, group_name) in enumerate(fragments, 1):
                    if frag_lines:
                        # Filter this fragment's empty lines
                        frag_lines_clean = [line for line in frag_lines if line]
                        frag_len = len(frag_lines_clean)

                        if frag_len > 0:
                            # Extract variants for this fragment's range in cleaned coordinates
                            frag_variants = text_utils.extract_variants_for_range(
                                adjusted_variants,
                                cleaned_line_idx,
                                cleaned_line_idx + frag_len - 1
                            )

                            if group_name:
                                title_to_use = f"{current_title} {group_name}"
                            else:
                                title_to_use = f"{current_title} 其{chinese_utils.number_to_chinese(i)}"

                            author = self.author_service.create_author(current_author_canonical, current_author_recorded, volume_num)
                            # Only attach preface to first fragment
                            frag_preface = preface if i == 1 else None
                            poem = Poem(
                                uid=self.generate_uid(volume_num, final_entry_index, part_index),
                                volume=volume_num,
                                author=author,
                                title=title_to_use,
                                poem=frag_lines_clean,
                                notes=frag_notes if frag_notes else None,
                                preface=frag_preface,
                                part_index=part_index,
                                variants=frag_variants
                            )
                            poems.append(poem)
                            logger.debug(f"Extracted fragment: {title_to_use}")
                            part_index += 1

                            # Advance position for next fragment
                            cleaned_line_idx += frag_len
            else:
                # Single-line 句 (fragment) with no empty lines - treat as single fragment
                logger.debug(f"Single-line 句 fragment with no empty lines")
                # Filter empty lines and adjust variant indices to match
                poem_lines_clean, variants_clean = text_utils.filter_empty_lines_with_variants(poem_lines, variants)
                if poem_lines_clean:
                    author = self.author_service.create_author(current_author_canonical, current_author_recorded, volume_num)
                    poem = Poem(
                        uid=self.generate_uid(volume_num, final_entry_index, part_index),
                        volume=volume_num,
                        author=author,
                        title=current_title,
                        poem=poem_lines_clean,
                        notes=notes if notes else None,
                        preface=preface,
                        part_index=part_index,
                        variants=variants_clean if variants_clean else None
                    )
                    poems.append(poem)
                    logger.debug(f"Extracted single-line 句 fragment: {current_title}")
        else:
            # Regular poem
            # Filter empty lines and adjust variant indices to match
            poem_lines, variants = text_utils.filter_empty_lines_with_variants(poem_lines, variants)

            # Check if title has author in angle brackets (format: "Title〈Author〉")
            # Common in yuefu volumes 10-29, particularly volume 28
            if (current_title and
                (not current_author_canonical or current_author_canonical == "Unknown") and
                10 <= volume_num <= 29):

                # Match  pattern: "TitleName〈AuthorName〉" or "TitleName（AuthorName）"
                author_in_title_match = re.search(r'[〈（(]([^〉）)]+)[〉）)]$', current_title)
                if author_in_title_match:
                    author_name = author_in_title_match.group(1).strip()
                    # Make sure it looks like an author name (2-5 characters, no punctuation)
                    has_no_punctuation = not any(p in author_name for p in '。，！？；：、""''《》')
                    is_reasonable_length = 2 <= len(author_name) <= 5

                    if has_no_punctuation and is_reasonable_length:
                        # Exract author from title - normalize for canonical, keep original for recorded
                        current_author_canonical, current_author_recorded = parse_author_name(author_name)
                        # Remove author part from title
                        current_title = re.sub(r'[〈（(][^〉）)]+[〉）)]$', '', current_title).strip()
                        logger.debug(f"Extracted author from title (poem div): {author_name} (canonical: {current_author_canonical}), cleaned title: {current_title}")

            # Check if first line is an author name (common in yuefu volumes 10-29)
            if (poem_lines and
                (not current_author_canonical or current_author_canonical == "Unknown") and
                10 <= volume_num <= 29):

                first_line = poem_lines[0].strip()
                has_no_punctuation = not any(p in first_line for p in '。，！？；：、""''《》〈〉（）()[]【】')
                is_short = 2 <= len(first_line) <= 5

                if has_no_punctuation and is_short and len(first_line.strip()) > 0:
                    # Extract  first line as author - normalize for canonical, keep original for recorded
                    current_author_canonical, current_author_recorded = parse_author_name(first_line)
                    # Remove author name from poem lines
                    poem_lines = poem_lines[1:]
                    logger.debug(f"Extracted author from first line (poem div): {first_line} (canonical: {current_author_canonical})")

            final_title = f"{current_title} {subtitle}" if subtitle else current_title

            author = self.author_service.create_author(current_author_canonical, current_author_recorded, volume_num)

            all_notes = pending_notes.copy() if pending_notes else []
            if notes:
                all_notes.extend(notes)

            # Only attach preface to part 1 for numbered parts
            final_preface = preface if (not is_numbered_part or part_index == 1) else None

            poem = Poem(
                uid=self.generate_uid(volume_num, final_entry_index, part_index),
                volume=volume_num,
                author=author,
                title=final_title,
                poem=poem_lines,
                notes=all_notes if all_notes else None,
                preface=final_preface,
                part_index=part_index if is_numbered_part else None,
                variants=variants if variants else None
            )
            poems.append(poem)
            logger.debug(f"Extracted poem: {final_title} by {current_author_canonical}")

        return {
            'poems': poems,
            'entry_index': entry_index,
            'pending_notes': [],
            'parent_entry_index': parent_entry_index if is_numbered_part else None,
            'parent_part_counter': parent_part_counter if is_numbered_part else 0
        }

    def _extract_from_dl(self, element: Tag, current_title: Optional[str],
                        current_author_canonical: Optional[str],
                        current_author_recorded: Optional[str],
                        volume_num: int, entry_index: int,
                        pending_notes: List[str],
                        preface: Optional[str] = None,
                        is_numbered_part: bool = False,
                        parent_entry_index: Optional[int] = None,
                        parent_part_counter: int = 0) -> Optional[dict]:
        """Extract poem from dl (definition list) element."""
        poem_lines, notes, subtitle = self.extract_poem_lines_from_dl(element)
        if not poem_lines:
            return None

        # Check previous div sibling for additional title info
        div_subtitle = None
        prev_div = element.find_previous_sibling('div')
        if prev_div and 'mw-heading' not in prev_div.get('class', []):
            div_text = prev_div.get_text(strip=True)
            div_text = re.sub(r'\[編輯\]', '', div_text).strip()
            if div_text and len(div_text) < 50:
                div_subtitle = div_text

        # Build final title
        final_title = current_title or ""
        if div_subtitle:
            final_title = f"{final_title} {div_subtitle}" if final_title else div_subtitle
        if subtitle:
            final_title = f"{final_title} {subtitle}" if final_title else subtitle

        if not final_title:
            return None

        final_title = final_title.strip()

        # Handle multi-part logic
        if is_numbered_part:
            if parent_entry_index is None:
                entry_index += 1
                parent_entry_index = entry_index
            parent_part_counter += 1
            part_index = parent_part_counter
            final_entry_index = parent_entry_index
            # Only attach preface to part 1
            final_preface = preface if part_index == 1 else None
        else:
            entry_index += 1
            final_entry_index = entry_index
            part_index = 1
            final_preface = preface

        author = self.author_service.create_author(current_author_canonical, current_author_recorded, volume_num)

        all_notes = pending_notes.copy() if pending_notes else []
        if notes:
            all_notes.extend(notes)

        poem = Poem(
            uid=self.generate_uid(volume_num, final_entry_index, part_index),
            volume=volume_num,
            author=author,
            title=final_title,
            poem=poem_lines,
            notes=all_notes if all_notes else None,
            preface=final_preface,
            part_index=part_index if is_numbered_part else None,
            variants=None  # DL elements don't have variant extraction yet
        )

        logger.debug(f"Extracted poem from dl: {final_title}")
        return {
            'poem': poem,
            'entry_index': entry_index,
            'pending_notes': [],
            'parent_entry_index': parent_entry_index if is_numbered_part else None,
            'parent_part_counter': parent_part_counter if is_numbered_part else 0
        }


class YuefuFormatStrategy(PoemExtractionStrategy):
    """
    Strategy for yuefu format volumes (17-25).

    Structure: h2/h4 titles with p tag content
    """

    def extract(self, soup: BeautifulSoup, volume_num: int) -> List[Poem]:
        poems = []
        entry_index = 0

        # Find the main content div
        # Some volumes have multiple mw-parser-output divs; pick the one with actual content
        content_divs = soup.find_all('div', class_=lambda c: c and 'mw-parser-output' in c)
        content_div = None

        # Score each div by content richness and pick the best one
        best_score = 0
        for div in content_divs:
            score = (
                len(div.find_all('div', class_='mw-heading')) * 10 +
                len(div.find_all('h2')) * 3 +
                len(div.find_all('h4')) * 3 +
                len(div.find_all('p'))
            )
            if score > best_score:
                best_score = score
                content_div = div

        if not content_div and content_divs:
            content_div = content_divs[0]

        if not content_div:
            logger.warning(
                f"No content found for volume {volume_num}. "
                f"This may indicate a structural change in the yuefu format source."
            )
            return poems

        # Extract footnotes from the page (once for all poems)
        footnotes = self.extract_footnotes(soup)
        if footnotes:
            logger.debug(f"Extracted {len(footnotes)} footnotes from yuefu volume {volume_num}")

        # Find all heading divs
        heading_divs = content_div.find_all('div', class_='mw-heading')

        for heading_div in heading_divs:
            # Check for h2 or h4
            h2 = heading_div.find('h2')
            h4 = heading_div.find('h4')

            if h2:
                heading_elem = h2
                is_h4_format = False
            elif h4:
                heading_elem = h4
                is_h4_format = True
            else:
                continue

            # Make a copy and remove footnote markers before extracting text
            heading_copy = heading_elem.__copy__()
            for sup in heading_copy.find_all('sup', class_='reference'):
                sup.decompose()

            title = heading_copy.get_text(strip=True)
            title = re.sub(r'\[編輯\]', '', title).strip()

            if not title:
                continue

            # Collect all p tags until next mw-heading div
            # Store soup objects to preserve footnote markers
            p_tag_soups = []
            sibling = heading_div.find_next_sibling()
            while sibling:
                if hasattr(sibling, 'name'):
                    if sibling.name == 'div' and 'mw-heading' in sibling.get('class', []):
                        break
                    elif sibling.name == 'p':
                        text = sibling.get_text(strip=True)
                        if text:
                            p_tag_soups.append(sibling)
                sibling = sibling.find_next_sibling()

            # Extract text from p tags, processing footnote markers
            p_tags = []
            p_tag_footnotes = []  # Track footnote IDs for each p tag
            for p_tag in p_tag_soups:
                # Extract footnote IDs before removing sup tags
                tag_footnote_ids = []
                for sup in p_tag.find_all('sup'):
                    # 1. <sup id="cite_ref-1" class="reference"><a href="#cite_note-1">...</a></sup>
                    if 'reference' in sup.get('class', []):
                        sup_id = sup.get('id', '')
                        if sup_id.startswith('cite_ref-'):
                            footnote_num = sup_id.replace('cite_ref-', '')
                            footnote_id = f"cite_note-{footnote_num}"
                            if footnote_id not in tag_footnote_ids:
                                tag_footnote_ids.append(footnote_id)
                    # 2. <sup><a href="#cite_note-N">[N]</a></sup>
                    else:
                        a_tag = sup.find('a', href=lambda h: h and h.startswith('#cite_note-'))
                        if a_tag:
                            href = a_tag.get('href', '')
                            footnote_id = href.replace('#', '')
                            if footnote_id not in tag_footnote_ids:
                                tag_footnote_ids.append(footnote_id)

                    # Remove sup tags and their contents
                    sup.decompose()

                # Now get the cleaned text
                text = p_tag.get_text(strip=True)
                if text:
                    p_tags.append(text)
                    p_tag_footnotes.append(tag_footnote_ids)

            if len(p_tags) == 0:
                continue

            # Extract author and poem lines based on format
            if is_h4_format:
                title, author_canonical, author_recorded, poem_lines = self._extract_h4_format(
                    heading_elem, title, p_tags
                )
            else:
                author_canonical, author_recorded, poem_lines = self._extract_h2_format(
                    heading_div, title, p_tags
                )

            # Separate annotations from poem lines
            clean_lines = []
            notes = []
            for line in poem_lines:
                poem_part, note_part = text_utils.separate_annotation(line)
                if poem_part:
                    clean_lines.append(text_utils.clean_line(poem_part))
                if note_part:
                    # Add note with line index and context from the poem line
                    notes.append({
                        'line': len(clean_lines) if clean_lines else 0,
                        'content': text_utils.clean_line(note_part),
                        'context': text_utils.clean_line(poem_part) if poem_part else title
                    })

            # Map footnotes to specific poem lines
            # Build a mapping of which p_tag each poem line came from
            line_to_ptag = self._map_lines_to_ptags(poem_lines, p_tags, is_h4_format)

            # Add footnote content to notes with line context (like StandardFormatStrategy)
            for line_idx, ptag_idx in line_to_ptag.items():
                if ptag_idx < len(p_tag_footnotes):
                    for footnote_id in p_tag_footnotes[ptag_idx]:
                        if footnote_id in footnotes:
                            footnote_text = footnotes[footnote_id]
                            # Add as dict with line number and context
                            if line_idx < len(clean_lines):
                                notes.append({
                                    'line': line_idx + 1,  # 1-indexed for user display
                                    'content': footnote_text,
                                    'context': clean_lines[line_idx]
                                })
                            else:
                                # Fallback if line index is out of range - use title as context
                                notes.append({
                                    'content': footnote_text,
                                    'context': title
                                })

            if clean_lines:
                entry_index += 1
                author = self.author_service.create_author(author_canonical, author_recorded, volume_num)
                poem = Poem(
                    uid=self.generate_uid(volume_num, entry_index, part_index=1),
                    volume=volume_num,
                    author=author,
                    title=title,
                    poem=clean_lines,
                    notes=notes if notes else None,
                    variants=None  # Yuefu format doesn't have variant extraction yet
                )
                poems.append(poem)
                logger.debug(f"Extracted yuefu poem: {title} by {author_canonical}")

        if self.author_database:
            seen_authors = set()
            for poem in poems:
                author_key = (poem.author.canonical, poem.author.recorded)
                if author_key not in seen_authors:
                    # Try to get Wikipedia bio for authors with wikidata_id but no QTS bio
                    wiki_bio = self.author_service.get_author_wikipedia_bio(poem.author)
                    if wiki_bio:
                        self.author_database.add_or_update_author(
                            poem.author, wiki_bio, bio_source="wikipedia"
                        )
                    else:
                        self.author_database.add_or_update_author(poem.author, None, volume_num)
                    seen_authors.add(author_key)
            logger.debug(f"Saved {len(seen_authors)} unique authors from volume {volume_num}")

        return poems

    def _map_lines_to_ptags(self, poem_lines: List[str], p_tags: List[str], is_h4_format: bool) -> Dict[int, int]:
        """
        Map poem lines back to their source p tags for footnote attribution.

        Args:
            poem_lines: Extracted poem lines (before cleaning)
            p_tags: Original p tag texts
            is_h4_format: Whether this is h4 format (all p_tags are content) or h2 format (first p_tag is author)

        Returns:
            Dict mapping line_index -> p_tag_index
        """
        line_to_ptag = {}

        # For h2 format, first p_tag is author info, skip it
        # For h4 format, all p_tags are poem content
        content_start_idx = 0 if is_h4_format else 1

        for line_idx, poem_line in enumerate(poem_lines):
            # Remove whitespace for matching
            poem_line_clean = poem_line.replace(' ', '').replace('\u3000', '')

            # Search through p_tags to find which one contains this line
            for ptag_idx in range(content_start_idx, len(p_tags)):
                ptag_clean = p_tags[ptag_idx].replace(' ', '').replace('\u3000', '')

                # Check if poem line appears in this p_tag
                if poem_line_clean in ptag_clean:
                    line_to_ptag[line_idx] = ptag_idx
                    break

            # If no match found, try partial matching (line might be split across p_tags)
            # Just assign to the nearest p_tag based on position
            if line_idx not in line_to_ptag and len(p_tags) > content_start_idx:
                # Heuristic: distribute lines evenly across p_tags
                ptag_idx = content_start_idx + (line_idx * (len(p_tags) - content_start_idx)) // max(len(poem_lines), 1)
                ptag_idx = min(ptag_idx, len(p_tags) - 1)
                line_to_ptag[line_idx] = ptag_idx

        return line_to_ptag

    def _extract_h4_format(self, heading_elem: Tag, title: str, p_tags: List[str]) -> Tuple[str, str, str, List[str]]:
        """
        Extract title, author, and poem from h4 format (title contains author).

        Returns:
            Tuple of (cleaned_title, author_canonical, author_recorded, poem_lines)
        """
        # h4 format: title has "poem_title  author著" format
        # note: "著" may be part of the author's name (e.g., 曹著) or just a marker meaning "authored by"
        # Extract with "著" included first
        author_match = re.search(r'(.+?)\s+(.+著)$', title)
        if author_match:
            title = author_match.group(1).strip()
            author_text_with_zhu = author_match.group(2).strip()
            author_text_without_zhu = author_text_with_zhu[:-1]  # Remove the 著 character
        else:
            # Fallback: try without "著" suffix
            author_match = re.search(r'(.+?)\s{2,}(.+?)$', title)
            if author_match:
                title = author_match.group(1).strip()
                author_text_with_zhu = author_match.group(2).strip()
                author_text_without_zhu = author_text_with_zhu
            else:
                author_text_with_zhu = "Unknown"
                author_text_without_zhu = "Unknown"

        # Check if there's an author link - this gives us the canonical name
        author_link = heading_elem.find('a')

        if author_link and 'Author:' in author_link.get('href', ''):
            # If there's an author link, use it (it will have the correct name with or without 著)
            href = author_link.get('href', '')
            author_part = href.split('Author:')[-1].split('#')[0].split('?')[0]
            author_canonical = unquote(author_part)
            author_recorded = author_link.get_text(strip=True)
        else:
            # No author link - need to decide whether to keep 著 or strip it
            # If the name without 著 is very short (1 char), 著 might be part of the name (e.g., 曹著)
            # But 2-char names are common (李白, 杜甫, 張籍), so strip 著 for those
            if len(author_text_without_zhu) <= 1:
                author_canonical = author_text_with_zhu
                author_recorded = author_text_with_zhu
            else:
                # For 2+ char names, 著 is just a marker meaning "authored by", so strip it
                author_canonical = author_text_without_zhu
                author_recorded = author_text_without_zhu

        # parse names to handle parenthetical format (e.g., "慶和 (趙光逢)")
        author_canonical, _ = parse_author_name(author_canonical)
        author_recorded, _ = parse_author_name(author_recorded)

        # All p tags are poem lines
        poem_lines = p_tags
        return title, author_canonical, author_recorded, poem_lines

    def _extract_h2_format(self, heading_div: Tag, title: str, p_tags: List[str]) -> Tuple[str, str, List[str]]:
        """Extract author and poem from h2 format (first p may be author)."""
        first_p_text = p_tags[0]
        has_punctuation = any(p in first_p_text for p in CHINESE_PUNCTUATION)
        is_short = len(first_p_text) <= 20

        # If  first p tag is short and has no punctuation, it's likely the author
        if is_short and not has_punctuation:
            author_text = first_p_text
            poem_lines = p_tags[1:]

            if not poem_lines:
                # No poem content, treat as all poem lines
                author_text = "Unknown"
                author_canonical = "Unknown"
                author_recorded = "Unknown"
                poem_lines = p_tags
                return author_canonical, author_recorded, poem_lines

            # Extract author from first p tag
            first_p = heading_div.find_next_sibling('p')
            author_canonical = author_text
            author_recorded = author_text

            if first_p:
                author_link = first_p.find('a')
                if author_link and 'Author:' in author_link.get('href', ''):
                    href = author_link.get('href', '')
                    author_part = href.split('Author:')[-1].split('#')[0].split('?')[0]
                    author_canonical = unquote(author_part)
                    author_recorded = author_link.get_text(strip=True)

            # Parse names to handle parenthetical format (e.g., "慶和 (趙光逢)")
            author_canonical, _ = parse_author_name(author_canonical)
            author_recorded, _ = parse_author_name(author_recorded)
        else:
            # All p tags are poem lines, no author specified
            author_canonical = "Unknown"
            author_recorded = "Unknown"
            poem_lines = p_tags

        return author_canonical, author_recorded, poem_lines


class LegacyParagraphExtractionStrategy(PoemExtractionStrategy):
    """
    Strategy for legacy plain-paragraph format volumes.

    Format: Plain <p> tags with markers like "卷323_1 《title》author"
    followed by poem lines in subsequent <p> tags.

    Example:
        <p>卷323_1 《送杜尹赴東都》權德輿</p>
        <p>商於留異績，河洛賀新遷。朝選吳公守，時推杜尹賢。</p>
        <p>如綸披鳳詔，出匣淬龍泉。風雨交中土，簪裾敞別筵。</p>
    """

    def extract(self, soup: BeautifulSoup, volume_num: int) -> List[Poem]:
        poems = []
        entry_index = 0

        # Find the content div - there may be multiple mw-parser-output divs
        # The actual content div has more children and p tags
        content_divs = soup.find_all('div', class_=lambda c: c and 'mw-parser-output' in c)
        content_div = None

        # Score each div and pick the one with most content
        best_score = 0
        for div in content_divs:
            score = len(div.find_all('p'))
            if score > best_score:
                best_score = score
                content_div = div

        if not content_div:
            logger.warning(f"No content found for volume {volume_num}")
            return poems

        all_p_tags = content_div.find_all('p')

        # Find p tags with poem markers (卷N_M format)
        poem_marker_pattern = re.compile(r'卷\d+_\d+')

        i = 0
        while i < len(all_p_tags):
            p = all_p_tags[i]
            text = p.get_text(strip=True)

            # check if this is a poem header
            if not poem_marker_pattern.search(text):
                i += 1
                continue

            # Parse header: 卷323_1 《title》author
            header_match = re.match(
                r'卷\d+_\d+\s*[《<](.+?)[》>]\s*(.+?)$',
                text
            )

            if not header_match:
                header_match = re.match(
                    r'卷\d+_\d+\s+(.+?)\s+(.+?)$',
                    text
                )

            if not header_match:
                logger.warning(f"Could not parse poem header: {text}")
                i += 1
                continue

            title = header_match.group(1).strip()
            author_text = header_match.group(2).strip()

            # Extract parenthetical notes from title
            title, title_notes = self.extract_title_notes(title)

            # Collect poem lines from subsequent p tags
            poem_lines = []
            i += 1

            while i < len(all_p_tags):
                next_p = all_p_tags[i]
                next_text = next_p.get_text(strip=True)

                # Stop if we hit another poem marker
                if poem_marker_pattern.search(next_text):
                    break

                # Stop if we hit navigation or other structural elements
                if not next_text or next_text.startswith('←') or next_text.startswith('→'):
                    i += 1
                    continue

                # Stop if this looks like metadata
                if any(marker in next_text for marker in ['全唐詩', '卷三百', '上一卷', '下一卷']):
                    break

                # Add the line
                if next_text:
                    # Separate annotations from poem text
                    poem_part, note_part = text_utils.separate_annotation(next_text)
                    if poem_part:
                        poem_lines.append(text_utils.clean_line(poem_part))

                i += 1

            # Create poem entry
            if poem_lines:
                entry_index += 1

                # create author
                author_canonical, author_recorded = parse_author_name(author_text)
                author = self.author_service.create_author(
                    author_canonical,
                    author_recorded,
                    volume_num
                )

                # Generate UID
                uid = uid_generator.generate_uid(volume_num, entry_index, part_index=1)

                # Create poem
                poem = Poem(
                    uid=uid,
                    volume=volume_num,
                    author=author,
                    title=title,
                    poem=poem_lines,
                    notes=title_notes if title_notes else None,
                    variants=None
                )

                poems.append(poem)
                logger.debug(f"Extracted legacy format poem: {title} by {author_canonical}")

        # Save authors to database
        if self.author_database:
            seen_authors = set()
            for poem in poems:
                author_key = (poem.author.canonical, poem.author.recorded)
                if author_key not in seen_authors:
                    # Try to get Wikipedia bio for authors with wikidata_id but no QTS bio
                    wiki_bio = self.author_service.get_author_wikipedia_bio(poem.author)
                    if wiki_bio:
                        self.author_database.add_or_update_author(
                            poem.author, wiki_bio, bio_source="wikipedia"
                        )
                    else:
                        self.author_database.add_or_update_author(poem.author, None, volume_num)
                    seen_authors.add(author_key)
            logger.debug(f"Saved {len(seen_authors)} unique authors from volume {volume_num}")

        return poems
