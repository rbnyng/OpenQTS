"""
Text processing utilities for Tang Poems scraper.

Contains functions for annotation extraction, line cleaning,
and other text manipulation operations.
"""

import re


def separate_annotation(line: str) -> tuple[str, str]:
    """
    Separate annotation from poem line.

    Annotations are wrapped in 〈 〉 brackets and contain editorial notes
    or source information that should be extracted separately.

    Args:
        line: A line that may contain annotation

    Returns:
        Tuple of (clean_line, annotation)
        - clean_line: The line with annotation removed
        - annotation: The annotation text (empty string if none)

    Examples:
        >>> separate_annotation('春眠不覺曉〈出自唐詩三百首〉')
        ('春眠不覺曉', '出自唐詩三百首')
        >>> separate_annotation('處處聞啼鳥')
        ('處處聞啼鳥', '')
    """
    # Match content within 〈 〉 brackets
    annotation_pattern = r'〈([^〉]+)〉'
    match = re.search(annotation_pattern, line)

    if match:
        annotation = match.group(1)
        # Remove the annotation from the line
        clean_line = re.sub(annotation_pattern, '', line).strip()
        return clean_line, annotation
    else:
        return line, ''


def clean_line(line: str) -> str:
    """
    Clean a poem line by removing extra whitespace and artifacts.

    Args:
        line: Raw line text

    Returns:
        Cleaned line

    Operations:
        - Strip leading/trailing whitespace
        - Normalize internal whitespace
        - Remove zero-width characters
    """
    # Remove zero-width spaces and other invisible characters
    line = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', line)

    # Strip and normalize whitespace
    line = ' '.join(line.split())

    return line.strip()


def extract_notes_from_text(text: str) -> list[str]:
    """
    Extract all annotation notes from text.

    Args:
        text: Text that may contain multiple annotations in 〈〉 brackets

    Returns:
        List of annotation strings

    Examples:
        >>> extract_notes_from_text('詩序〈注1〉內容〈注2〉')
        ['注1', '注2']
    """
    annotation_pattern = r'〈([^〉]+)〉'
    matches = re.findall(annotation_pattern, text)
    return matches


def remove_all_annotations(text: str) -> str:
    """
    Remove all annotations from text, leaving only the main content.

    Args:
        text: Text with possible annotations

    Returns:
        Text with all 〈〉 annotations removed

    Examples:
        >>> remove_all_annotations('春眠不覺曉〈出處〉處處聞啼鳥〈注〉')
        '春眠不覺曉處處聞啼鳥'
    """
    annotation_pattern = r'〈[^〉]+〉'
    return re.sub(annotation_pattern, '', text).strip()


def filter_empty_lines_with_variants(
    lines: list[str],
    variants: list[dict] | None
) -> tuple[list[str], list[dict] | None]:
    """
    Filter out empty lines and adjust variant line indices accordingly.

    When poem lines contain empty strings (from <br><br> in HTML), variant
    line indices become misaligned after empty lines are removed. This function
    removes empty lines and adjusts all variant 'line' values to match the
    new positions.

    Args:
        lines: List of poem lines, possibly containing empty strings
        variants: List of variant dicts with 'line' key (1-indexed), or None

    Returns:
        Tuple of (filtered_lines, adjusted_variants)
        - filtered_lines: List with empty strings removed
        - adjusted_variants: Variants with 'line' values adjusted, or None

    Example:
        >>> lines = ['line1', '', 'line2', '', 'line3']
        >>> variants = [{'line': 1, 'text': 'a'}, {'line': 3, 'text': 'b'}]
        >>> filter_empty_lines_with_variants(lines, variants)
        (['line1', 'line2', 'line3'], [{'line': 1, 'text': 'a'}, {'line': 2, 'text': 'b'}])
    """
    if not lines:
        return [], variants

    # Build mapping from old 1-indexed line to new 1-indexed line
    # Only non-empty lines get new indices
    old_to_new = {}
    new_idx = 0
    for old_idx, line in enumerate(lines):
        if line:  # Non-empty line
            new_idx += 1
            old_to_new[old_idx + 1] = new_idx  # Convert to 1-indexed

    # Filter out empty lines
    filtered_lines = [line for line in lines if line]

    # Adjust variant indices
    if variants:
        adjusted_variants = []
        for v in variants:
            old_line = v.get('line')
            if old_line is not None and old_line in old_to_new:
                adjusted_v = v.copy()
                adjusted_v['line'] = old_to_new[old_line]
                adjusted_variants.append(adjusted_v)
            # Skip variants referencing empty lines (shouldn't happen normally)
        variants = adjusted_variants if adjusted_variants else None

    return filtered_lines, variants


def extract_variants_for_range(
    variants: list[dict] | None,
    start_line: int,
    end_line: int
) -> list[dict] | None:
    """
    Extract variants within a line range and adjust indices relative to the range.

    Used when splitting a poem into fragments - each fragment should only get
    variants for lines within that fragment, with indices adjusted to start from 1.

    Args:
        variants: List of variant dicts with 'line' key (1-indexed), or None
        start_line: First line of range (1-indexed, inclusive)
        end_line: Last line of range (1-indexed, inclusive)

    Returns:
        Variants within range with 'line' adjusted relative to start_line, or None

    Example:
        >>> variants = [{'line': 2, 'text': 'a'}, {'line': 5, 'text': 'b'}, {'line': 8, 'text': 'c'}]
        >>> extract_variants_for_range(variants, 4, 6)
        [{'line': 2, 'text': 'b'}]  # line 5 becomes line 2 (5 - 4 + 1 = 2)
    """
    if not variants:
        return None

    extracted = []
    for v in variants:
        line = v.get('line')
        if line is not None and start_line <= line <= end_line:
            adjusted_v = v.copy()
            adjusted_v['line'] = line - start_line + 1  # Adjust relative to range start
            extracted.append(adjusted_v)

    return extracted if extracted else None
