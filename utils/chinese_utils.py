"""
Chinese text processing utilities for Tang Poems scraper.

Contains functions for Chinese numeral conversion, text cleaning,
and other Chinese-specific text operations.
"""

import re


def chinese_to_number(chinese_num: str) -> int:
    """
    Convert Chinese numeral to Arabic number.

    Args:
        chinese_num: Chinese numeral string (e.g., '一', '十二', '二十五')

    Returns:
        Integer value (0 if conversion fails)

    Examples:
        >>> chinese_to_number('一')
        1
        >>> chinese_to_number('十二')
        12
        >>> chinese_to_number('二十五')
        25
    """
    chinese_num = chinese_num.strip()

    # Mapping of Chinese digits to numbers
    digit_map = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10
    }

    # Simple single digit
    if chinese_num in digit_map:
        return digit_map[chinese_num]

    # Handle '十X' pattern (10-19)
    if chinese_num.startswith('十') and len(chinese_num) == 2:
        ones = digit_map.get(chinese_num[1], 0)
        return 10 + ones

    # Handle 'X十' pattern (20, 30, etc.)
    if chinese_num.endswith('十') and len(chinese_num) == 2:
        tens = digit_map.get(chinese_num[0], 0)
        return tens * 10

    # Handle 'X十Y' pattern (21-99)
    if '十' in chinese_num and len(chinese_num) == 3:
        parts = chinese_num.split('十')
        if len(parts) == 2:
            tens = digit_map.get(parts[0], 0)
            ones = digit_map.get(parts[1], 0)
            return tens * 10 + ones

    # Fallback: return 0 if cannot parse
    return 0


def number_to_chinese(num: int) -> str:
    """
    Convert Arabic numeral to Chinese numeral.

    Args:
        num: Arabic number (1-999 supported)

    Returns:
        Chinese numeral string

    Examples:
        >>> number_to_chinese(1)
        '一'
        >>> number_to_chinese(12)
        '十二'
        >>> number_to_chinese(25)
        '二十五'
        >>> number_to_chinese(100)
        '一百'
        >>> number_to_chinese(101)
        '一百零一'
        >>> number_to_chinese(110)
        '一百一十'
        >>> number_to_chinese(303)
        '三百零三'
    """
    if num < 1 or num > 999:
        return str(num)

    chinese_digits = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']

    if num < 10:
        return chinese_digits[num]
    elif num < 20:
        return f'十{chinese_digits[num % 10]}'
    elif num < 100:
        tens = num // 10
        ones = num % 10
        return f'{chinese_digits[tens]}十{chinese_digits[ones]}'
    else:
        # Handle 100-999
        hundreds = num // 100
        remainder = num % 100
        result = f'{chinese_digits[hundreds]}百'

        if remainder == 0:
            # Exact hundred (100, 200, 300, etc.)
            pass
        elif remainder < 10:
            # 101-109, 201-209, etc. - need 零
            result += f'零{chinese_digits[remainder]}'
        elif remainder < 20:
            # 110-119, 210-219, etc.
            result += f'一十{chinese_digits[remainder % 10]}'
        else:
            # 120-199, 220-299, etc.
            tens = remainder // 10
            ones = remainder % 10
            result += f'{chinese_digits[tens]}十{chinese_digits[ones]}'

        return result


def clean_chinese_text(text: str) -> str:
    """
    Clean up Chinese text by removing common markup artifacts.

    Args:
        text: Raw text from HTML

    Returns:
        Cleaned text

    Removes:
        - [編輯] markers
        - Extra whitespace
    """
    text = re.sub(r'\[編輯\]', '', text)
    text = text.strip()
    return text


def is_part_indicator(line: str) -> bool:
    """
    Check if a line is a part indicator (其一, 其二, etc.).

    These indicators are used to mark multi-part poems and should
    typically be extracted as part of the title, not as poem content.

    Args:
        line: A single line of text

    Returns:
        True if the line is a part indicator

    Examples:
        >>> is_part_indicator('其一')
        True
        >>> is_part_indicator('其二十五')
        True
        >>> is_part_indicator('春江花月夜')
        False
    """
    return bool(re.match(r'^其[一二三四五六七八九十]+$', line.strip()))


def is_numbered_part(text: str) -> bool:
    """
    Check if text is a bare Chinese numeral part indicator (一, 二, 三, etc.).

    Used to detect multi-part works where each part is numbered with Chinese numerals.
    For example: "帝京篇十首 一", "帝京篇十首 二"

    Args:
        text: Text to check

    Returns:
        True if the text is a bare Chinese numeral (1-99)

    Examples:
        >>> is_numbered_part('一')
        True
        >>> is_numbered_part('十五')
        True
        >>> is_numbered_part('二十')
        True
        >>> is_numbered_part('春夜')
        False
    """
    return bool(re.match(r'^[一二三四五六七八九十]+$', text.strip()))


def normalize_poem_lines(lines: list[str]) -> list[str]:
    """
    Standardizes poem structure using a multi-step pipeline:
    Normalizes ASCII punctuation to Chinese (e.g., ',' -> '，').
    Converts internal spaces between characters into commas.
    Cleans remaining whitespace.
    Splits by sentence terminators (。！？) to ensure semantic units.
    """
    normalized = []
    
    for line in lines:
        # --- Normalize ASCII Punctuation ---
        # Handle ",", ", ", " , " -> "，"
        temp_text = re.sub(r'\s*,\s*', '，', line)
        # Handle "." -> "。"
        temp_text = re.sub(r'\s*\.\s*', '。', temp_text)
        # Handle "?" -> "？"
        temp_text = re.sub(r'\s*\?\s*', '？', temp_text)
        # Handle "!" -> "！"
        temp_text = re.sub(r'\s*!\s*', '！', temp_text)
        # Handle ":" -> "："
        temp_text = re.sub(r'\s*:\s*', '：', temp_text)

        # --- Handle Space-As-Comma ---
        # Look for: Chinese Char + Whitespace + Chinese Char
        # Replace with: Char + ， + Char
        # This fixes "尋真游勝境 巡禮到陽平" -> "尋真游勝境，巡禮到陽平"
        temp_text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1，\2', temp_text)
        
        # --- Final Cleanup ---
        # Remove any remaining whitespace (newlines, tabs, padding)
        clean_text = re.sub(r'\s+', '', temp_text)
        
        if not clean_text:
            continue
            
        # --- Split by Sentence Terminators ---
        # Split dense blocks like "Line A，Line B。Line C..."
        # Keep the delimiter in the result using capturing group
        # Special handling: Don't split on ？ or ！ if followed by text that forms a couplet

        # Helper to count characters excluding punctuation
        def count_chars(text: str) -> int:
            return len(re.sub(r'[，。！？：]', '', text))

        # Check if we should keep ？ or ！ from splitting
        # by looking for matching couplet pattern
        def should_keep_together(text_before: str, terminator: str, text_after: str) -> bool:
            """Check if text before terminator and after should stay together as couplet."""
            if terminator not in '？！':
                return False
            # Text after must end with 。
            if not text_after or not text_after.rstrip().endswith('。'):
                return False
            # Extract the part after terminator up to the first sentence terminator
            after_match = re.match(r'([^。！？]+[。！？])', text_after)
            if not after_match:
                return False
            after_line = after_match.group(1)
            # Check if both parts have same character count
            return count_chars(text_before + terminator) == count_chars(after_line)

        parts = re.split(r'([。！？])', clean_text)

        current_segment = ""
        i = 0

        while i < len(parts):
            part = parts[i]
            if not part:
                i += 1
                continue

            current_segment += part

            # If this part was just a terminator, check if we should finalize
            if part in '。！？':
                # Look ahead to see if we should keep the next segment together
                remaining_text = ''.join(parts[i+1:])
                text_before_terminator = current_segment[:-1]  # Remove the terminator

                if part in '？！' and should_keep_together(text_before_terminator, part, remaining_text):
                    # This is a couplet - continue accumulating until we hit the matching 。
                    # Find the next 。 and include everything up to it
                    j = i + 1
                    while j < len(parts):
                        next_part = parts[j]
                        current_segment += next_part
                        if next_part == '。':
                            # Found the end of the couplet
                            normalized.append(current_segment)
                            current_segment = ""
                            i = j + 1
                            break
                        j += 1
                    else:
                        # Didn't find closing 。, just add what we have
                        normalized.append(current_segment)
                        current_segment = ""
                        i += 1
                else:
                    # Normal split - finalize the segment
                    normalized.append(current_segment)
                    current_segment = ""
                    i += 1
            else:
                i += 1

        # Handle remaining text (e.g., lines that don't end in period)
        if current_segment:
            normalized.append(current_segment)

    # --- Merge Couplets ---
    # In classical Chinese poetry, consecutive lines where:
    # - One or more lines end with comma (，)
    # - Final line ends with period/terminator (。！？)
    # Should be merged into a single couplet
    # Example: "生離別，" + "生離別，" + "憂從中來無斷絕。" → one merged line
    #
    # Note: Rhetorical questions/exclamations are handled earlier in the splitting stage
    merged = []
    i = 0

    while i < len(normalized):
        current_line = normalized[i]

        # Check if this line ends with comma - start accumulating for merge
        if current_line.endswith('，'):
            # Accumulate all consecutive comma-ending lines
            accumulated = [current_line]
            j = i + 1

            while j < len(normalized):
                next_line = normalized[j]
                accumulated.append(next_line)
                j += 1

                # If we hit a line ending with terminator, merge everything
                if next_line[-1:] in '。！？':
                    merged_line = ''.join(accumulated)
                    merged.append(merged_line)
                    i = j  # Skip all merged lines
                    break

                # If next line doesn't end with comma or terminator, stop accumulating
                if not next_line.endswith('，'):
                    # Can't merge - add accumulated lines separately
                    merged.extend(accumulated)
                    i = j
                    break
            else:
                # Reached end of list without finding terminator
                merged.extend(accumulated)
                i = j
        else:
            # Line doesn't end with comma, add as-is
            merged.append(current_line)
            i += 1

    return merged