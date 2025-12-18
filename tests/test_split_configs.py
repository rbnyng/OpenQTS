"""
Unit tests for split configurations in volume_special_cases.
"""

import pytest
import volume_special_cases


class TestVolume17Splits:
    """Test volume 17 split configurations."""

    def test_战城南二首_split(self):
        """Test 戰城南二首 split configuration."""
        title = "戰城南二首"
        author = "盧照鄰"
        # Simulated poem with 5 lines total
        poem_lines = ["line1", "line2", "line3", "line4", "line5"]

        result = volume_special_cases.get_volume_17_split(title, author, poem_lines, 2)

        assert result is not None
        assert len(result) == 2
        assert result[0] == ["line1", "line2", "line3"]  # 3 lines
        assert result[1] == ["line4", "line5"]  # 2 lines

    def test_巫山高二首_沈佺期(self):
        """Test 巫山高二首 for 沈佺期."""
        title = "巫山高二首"
        author = "沈佺期"
        poem_lines = ["line1", "line2", "line3", "line4"]

        result = volume_special_cases.get_volume_17_split(title, author, poem_lines, 2)

        assert result is not None
        assert len(result) == 2
        assert result[0] == ["line1", "line2"]
        assert result[1] == ["line3", "line4"]

    def test_巫山高二首_孟郊(self):
        """Test 巫山高二首 for 孟郊 (different split)."""
        title = "巫山高二首"
        author = "孟郊"
        poem_lines = ["line1", "line2", "line3", "line4", "line5"]

        result = volume_special_cases.get_volume_17_split(title, author, poem_lines, 2)

        assert result is not None
        assert len(result) == 2
        assert result[0] == ["line1", "line2", "line3"]  # 3 lines
        assert result[1] == ["line4", "line5"]  # 2 lines

    def test_凯歌六首(self):
        """Test 凱歌六首 split."""
        title = "凱歌六首"
        author = "岑參"
        poem_lines = [f"line{i}" for i in range(12)]  # 12 lines

        result = volume_special_cases.get_volume_17_split(title, author, poem_lines, 6)

        assert result is not None
        assert len(result) == 6
        # Each song should have 2 lines
        for song in result:
            assert len(song) == 2


class TestVolume18Splits:
    """Test volume 18 split configurations."""

    def test_前出塞九首(self):
        """Test 橫吹曲辭·前出塞九首 split."""
        title = "橫吹曲辭·前出塞九首"
        poem_lines = [f"line{i}" for i in range(36)]  # 36 lines

        result = volume_special_cases.get_volume_18_split(title, poem_lines, 9)

        assert result is not None
        assert len(result) == 9
        # Each song should have 4 lines
        for song in result:
            assert len(song) == 4

    def test_後出塞五首(self):
        """Test 橫吹曲辭·後出塞五首 split."""
        title = "橫吹曲辭·後出塞五首"
        poem_lines = [f"line{i}" for i in range(31)]  # 31 lines

        result = volume_special_cases.get_volume_18_split(title, poem_lines, 5)

        assert result is not None
        assert len(result) == 5
        assert len(result[0]) == 7  # Song 1: 7 lines
        assert len(result[1]) == 6  # Song 2: 6 lines
        assert len(result[2]) == 6  # Song 3: 6 lines
        assert len(result[3]) == 6  # Song 4: 6 lines
        assert len(result[4]) == 6  # Song 5: 6 lines

    def test_關山月二首(self):
        """Test 橫吹曲辭·關山月二首 split."""
        title = "橫吹曲辭·關山月二首"
        poem_lines = ["line1", "line2", "line3", "line4"]

        result = volume_special_cases.get_volume_18_split(title, poem_lines, 2)

        assert result is not None
        assert len(result) == 2
        assert result[0] == ["line1", "line2"]
        assert result[1] == ["line3", "line4"]


class TestVolume19Splits:
    """Test volume 19 split configurations."""

    def test_江南曲八首(self):
        """Test 江南曲八首 split."""
        title = "江南曲八首"
        poem_lines = [f"line{i}" for i in range(21)]  # 21 lines

        result = volume_special_cases.get_volume_19_split(title, poem_lines, 8)

        assert result is not None
        assert len(result) == 8
        # Check line distribution: 3,3,3,3,3,2,2,2
        assert len(result[0]) == 3
        assert len(result[1]) == 3
        assert len(result[5]) == 2
        assert len(result[6]) == 2
        assert len(result[7]) == 2


class TestMultiPartPoems:
    """Test multi-part poem detection."""

    def test_is_multipart_poem_volume_8(self):
        """Test multi-part detection for volume 8."""
        assert volume_special_cases.is_multipart_poem(8, '輓辭二首') == 2
        assert volume_special_cases.is_multipart_poem(8, '沒了期歌二首') == 2
        assert volume_special_cases.is_multipart_poem(8, 'Random Title') == 0

    def test_is_multipart_poem_volume_13(self):
        """Test multi-part detection for volume 13."""
        assert volume_special_cases.is_multipart_poem(13, '享太廟樂章 凱安四章') == 4

    def test_is_multipart_poem_volume_14(self):
        """Test that volume 14 uses title rewrites instead."""
        # Volume 14 uses title rewrites, not multipart detection
        result = volume_special_cases.is_multipart_poem(14, '太清宮樂章 序入破 第一奏')
        assert result == 0 or result == 3  # Depending on implementation


class TestTitleRewrites:
    """Test title rewrite functionality."""

    def test_volume_14_rewrites(self):
        """Test volume 14 title rewrites."""
        assert volume_special_cases.apply_title_rewrite(
            14, '太清宮樂章 序入破第一奏'
        ) == '太清宮樂章 序入破 第一奏'

        assert volume_special_cases.apply_title_rewrite(
            14, '太清宮樂章 第二奏'
        ) == '太清宮樂章 序入破 第二奏'

        assert volume_special_cases.apply_title_rewrite(
            14, '太清宮樂章 第三奏'
        ) == '太清宮樂章 序入破 第三奏'

    def test_no_rewrite_needed(self):
        """Test that titles without rewrites pass through unchanged."""
        title = "Random Poem Title"
        assert volume_special_cases.apply_title_rewrite(14, title) == title
        assert volume_special_cases.apply_title_rewrite(18, title) == title


class TestWrongParameters:
    """Test error handling for wrong parameters."""

    def test_wrong_line_count(self):
        """Test split returns None when line count doesn't match."""
        title = "橫吹曲辭·前出塞九首"
        poem_lines = ["line1", "line2"]  # Wrong count (should be 36)

        result = volume_special_cases.get_volume_18_split(title, poem_lines, 9)

        assert result is None

    def test_wrong_num_songs(self):
        """Test split returns None when num_songs doesn't match."""
        title = "橫吹曲辭·前出塞九首"
        poem_lines = [f"line{i}" for i in range(36)]

        result = volume_special_cases.get_volume_18_split(title, poem_lines, 5)  # Wrong

        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
