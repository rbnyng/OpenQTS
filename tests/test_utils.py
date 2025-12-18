"""
Unit tests for utility functions.
"""

import pytest
from utils import chinese_utils, text_utils, uid_generator


class TestChineseUtils:
    """Test Chinese text processing utilities."""

    def test_number_to_chinese_single_digit(self):
        """Test conversion of single-digit numbers."""
        assert chinese_utils.number_to_chinese(1) == '一'
        assert chinese_utils.number_to_chinese(2) == '二'
        assert chinese_utils.number_to_chinese(5) == '五'
        assert chinese_utils.number_to_chinese(9) == '九'

    def test_number_to_chinese_ten(self):
        """Test conversion of 10."""
        assert chinese_utils.number_to_chinese(10) == '十'

    def test_number_to_chinese_teens(self):
        """Test conversion of 11-19."""
        assert chinese_utils.number_to_chinese(11) == '十一'
        assert chinese_utils.number_to_chinese(15) == '十五'
        assert chinese_utils.number_to_chinese(19) == '十九'

    def test_number_to_chinese_tens(self):
        """Test conversion of multiples of 10."""
        assert chinese_utils.number_to_chinese(20) == '二十'
        assert chinese_utils.number_to_chinese(30) == '三十'
        assert chinese_utils.number_to_chinese(90) == '九十'

    def test_number_to_chinese_compound(self):
        """Test conversion of compound numbers."""
        assert chinese_utils.number_to_chinese(21) == '二十一'
        assert chinese_utils.number_to_chinese(35) == '三十五'
        assert chinese_utils.number_to_chinese(99) == '九十九'

    def test_number_to_chinese_edge_cases(self):
        """Test edge cases."""
        # Out of range - should return string representation
        assert chinese_utils.number_to_chinese(0) == '0'
        assert chinese_utils.number_to_chinese(100) == '100'
        assert chinese_utils.number_to_chinese(-1) == '-1'


class TestTextUtils:
    """Test text processing utilities."""

    def test_separate_annotation_with_annotation(self):
        """Test separating annotation from poem line."""
        line = "戚戚去故里，悠悠赴交河。〈註釋〉"
        clean, annotation = text_utils.separate_annotation(line)
        assert clean == "戚戚去故里，悠悠赴交河。"
        assert annotation == "註釋"

    def test_separate_annotation_no_annotation(self):
        """Test line without annotation."""
        line = "戚戚去故里，悠悠赴交河。"
        clean, annotation = text_utils.separate_annotation(line)
        assert clean == "戚戚去故里，悠悠赴交河。"
        assert annotation == ""

    def test_separate_annotation_multiple_brackets(self):
        """Test line with multiple annotation brackets."""
        line = "詩句〈註一〉更多詩句〈註二〉"
        clean, annotation = text_utils.separate_annotation(line)
        # Should extract first annotation
        assert annotation == "註一"

    def test_clean_line_whitespace(self):
        """Test cleaning lines with extra whitespace."""
        assert text_utils.clean_line("  詩句  ") == "詩句"
        assert text_utils.clean_line("詩句\t\n") == "詩句"

    def test_clean_line_zero_width_chars(self):
        """Test removing zero-width characters."""
        # This would need the actual zero-width chars in the input
        line = "詩​句"  # Contains zero-width space
        cleaned = text_utils.clean_line(line)
        assert '​' not in cleaned


class TestUidGenerator:
    """Test UID generation."""

    def test_generate_uid_format(self):
        """Test UID format QTS_VVV_EEE_PP."""
        uid = uid_generator.generate_uid(1, 1)
        assert uid == "QTS_001_001_01"

    def test_generate_uid_with_part(self):
        """Test UID format with explicit part index."""
        uid = uid_generator.generate_uid(18, 4, 2)
        assert uid == "QTS_018_004_02"

    def test_generate_uid_large_numbers(self):
        """Test UID with large volume and entry numbers."""
        uid = uid_generator.generate_uid(900, 999)
        assert uid == "QTS_900_999_01"

    def test_generate_uid_padding(self):
        """Test that numbers are zero-padded."""
        uid = uid_generator.generate_uid(18, 5, 3)
        assert uid == "QTS_018_005_03"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
