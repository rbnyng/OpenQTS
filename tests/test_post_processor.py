"""
Unit tests for post-processing logic.
"""

import pytest
import json
import tempfile
from pathlib import Path
from post_process_splits import PoemPostProcessor


class TestVolumeProcessing:
    """Test volume processing logic."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        raw_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        yield Path(raw_dir), Path(output_dir)

    @pytest.fixture
    def sample_raw_poem(self):
        """Sample raw poem data."""
        return {
            'uid': 'QTS_018_001',
            'volume': 18,
            'author': {
                'canonical': '杜甫',
                'recorded': '杜甫',
                'wikidata_id': 'Q33772',
                'english_name': 'Du Fu'
            },
            'title': '橫吹曲辭·前出塞九首',
            'poem': [
                "戚戚去故里，悠悠赴交河。公家有程期，亡命嬰禍羅。君已富土境，開邊一何多。"
                "棄絕父母恩，吞聲行負戈。出門日已遠，不受徒旅欺。骨肉恩豈斷，男兒死無時。"
                "走馬脫轡頭，手中挑青絲。捷下萬仞岡，俯身試搴旗。磨刀嗚咽水，水赤刃傷手。"
                "欲輕腸斷聲，心緒亂已久。丈夫誓許國，憤惋復何有。功名圖麒麟，戰骨當速朽。"
                "送徒既有長，遠戍亦有身。生死向前去，不勞吏怒嗔。路逢相識人，附書與六親。"
                "哀哉兩決絕，不復同苦辛。迢迢萬餘里，領我赴三軍。軍中異苦樂，主將寧盡聞。"
                "隔河見胡騎，倏忽數百群。我始為奴僕，幾時樹功勳。挽弓當挽強，用箭當用長。"
                "射人先射馬，擒賊先擒王。殺人亦有限，列國自有疆。苟能製侵陵，豈在多殺傷。"
                "驅馬天雨雪，軍行入高山。徑危抱寒石，指落曾冰間。已去漢月遠，何時築城還。"
                "浮雲暮南征，可望不可攀。單于寇我壘，百里風塵昏。雄劍四五動，彼軍為我奔。"
                "虜其名王歸，系頸授轅門。潛身備行列，一勝何足論。從軍十年餘，能無分寸功。"
                "眾人貴苟得，欲語羞雷同。中原有鬥爭，況在狄與戎。丈夫四方志，安可辭固窮。"
            ]
        }

    def test_volume_18_sentence_splitting(self, temp_dirs, sample_raw_poem):
        """Test that volume 18 single-paragraph poems are split by sentences."""
        raw_dir, output_dir = temp_dirs
        processor = PoemPostProcessor(raw_dir=str(raw_dir), output_dir=str(output_dir))

        # Create raw JSON file
        raw_file = raw_dir / "volume_018.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump([sample_raw_poem], f, ensure_ascii=False)

        # Process the volume
        poems = processor.process_volume(18)
        poems_data = [p.to_dict() for p in poems]

        # Should split into 9 songs
        assert len(poems_data) == 9

        # Check first song
        assert poems_data[0]['title'] == '橫吹曲辭·前出塞九首 其一'
        assert poems_data[0]['part_index'] == 1
        assert poems_data[0]['total_parts'] == 9

        # Check last song
        assert poems_data[8]['title'] == '橫吹曲辭·前出塞九首 其九'
        assert poems_data[8]['part_index'] == 9

    def test_multipart_poem_labeling(self, temp_dirs):
        """Test multi-part poem labeling (volumes 8, 13, 14)."""
        raw_dir, output_dir = temp_dirs
        processor = PoemPostProcessor(raw_dir=str(raw_dir), output_dir=str(output_dir))

        # Create sample volume 8 data with duplicate titles
        raw_poems = [
            {
                'uid': 'QTS_008_001',
                'volume': 8,
                'author': {'canonical': '李白', 'recorded': '李白'},
                'title': '輓辭二首',
                'poem': ['詩句一']
            },
            {
                'uid': 'QTS_008_002',
                'volume': 8,
                'author': {'canonical': '李白', 'recorded': '李白'},
                'title': '輓辭二首',
                'poem': ['詩句二']
            }
        ]

        raw_file = raw_dir / "volume_008.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw_poems, f, ensure_ascii=False)

        poems = processor.process_volume(8)
        poems_data = [p.to_dict() for p in poems]

        assert len(poems_data) == 2
        assert poems_data[0]['title'] == '輓辭二首 其一'
        assert poems_data[0]['part_index'] == 1
        assert poems_data[0]['total_parts'] == 2

        assert poems_data[1]['title'] == '輓辭二首 其二'
        assert poems_data[1]['part_index'] == 2
        assert poems_data[1]['total_parts'] == 2

    def test_regular_poem_passthrough(self, temp_dirs):
        """Test that regular poems pass through unchanged."""
        raw_dir, output_dir = temp_dirs
        processor = PoemPostProcessor(raw_dir=str(raw_dir), output_dir=str(output_dir))

        raw_poems = [
            {
                'uid': 'QTS_001_001',
                'volume': 1,
                'author': {'canonical': '李白', 'recorded': '李白'},
                'title': '靜夜思',
                'poem': ['床前明月光', '疑是地上霜']
            }
        ]

        raw_file = raw_dir / "volume_001.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw_poems, f, ensure_ascii=False)

        poems = processor.process_volume(1)
        poems_data = [p.to_dict() for p in poems]

        assert len(poems_data) == 1
        assert poems_data[0]['title'] == '靜夜思'
        assert 'part_index' not in poems_data[0]
        assert 'total_parts' not in poems_data[0]

    def test_uid_regeneration(self, temp_dirs):
        """Test that UIDs are regenerated for split poems."""
        raw_dir, output_dir = temp_dirs
        processor = PoemPostProcessor(raw_dir=str(raw_dir), output_dir=str(output_dir))

        # Create a simple multi-song poem
        raw_poems = [
            {
                'uid': 'QTS_019_001',
                'volume': 19,
                'author': {'canonical': '李白', 'recorded': '李白'},
                'title': '相和歌辭：短歌行二首',
                'poem': ['第一首', '第二首']
            }
        ]

        raw_file = raw_dir / "volume_019.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw_poems, f, ensure_ascii=False)

        poems = processor.process_volume(19)
        poems_data = [p.to_dict() for p in poems]

        # Should have 2 poems with same entry, different parts
        assert len(poems_data) == 2
        assert poems_data[0]['uid'] == 'QTS_019_001_01'
        assert poems_data[1]['uid'] == 'QTS_019_001_02'

    def test_preface_passthrough(self, temp_dirs):
        """Test that prefaces are preserved through post-processing."""
        raw_dir, output_dir = temp_dirs
        processor = PoemPostProcessor(raw_dir=str(raw_dir), output_dir=str(output_dir))

        # Create poems with and without prefaces
        raw_poems = [
            {
                'uid': 'QTS_008_001',
                'volume': 8,
                'author': {'canonical': '李煜', 'recorded': '李煜'},
                'title': '題金樓子後（并序）',
                'poem': ['牙籤萬軸裹紅綃', '王粲書同付火燒'],
                'preface': '梁元帝謂：王仲宣昔在荆州，著書數十篇。荆州壞，盡焚其書。'
            },
            {
                'uid': 'QTS_008_002',
                'volume': 8,
                'author': {'canonical': '李白', 'recorded': '李白'},
                'title': '靜夜思',
                'poem': ['床前明月光', '疑是地上霜']
            }
        ]

        raw_file = raw_dir / "volume_008.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw_poems, f, ensure_ascii=False)

        poems = processor.process_volume(8)
        poems_data = [p.to_dict() for p in poems]

        assert len(poems_data) == 2
        # First poem should have preface
        assert 'preface' in poems_data[0]
        assert poems_data[0]['preface'] == '梁元帝謂：王仲宣昔在荆州，著書數十篇。荆州壞，盡焚其書。'
        # Second poem should not have preface
        assert 'preface' not in poems_data[1]


class TestTitleRewrites:
    """Test title rewrite application during post-processing."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        raw_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        yield Path(raw_dir), Path(output_dir)

    def test_volume_14_title_rewrite(self, temp_dirs):
        """Test that volume 14 title rewrites are applied."""
        raw_dir, output_dir = temp_dirs
        processor = PoemPostProcessor(raw_dir=str(raw_dir), output_dir=str(output_dir))

        raw_poems = [
            {
                'uid': 'QTS_014_001',
                'volume': 14,
                'author': {'canonical': '作者', 'recorded': '作者'},
                'title': '太清宮樂章 序入破第一奏',
                'poem': ['詩句']
            }
        ]

        raw_file = raw_dir / "volume_014.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(raw_poems, f, ensure_ascii=False)

        poems = processor.process_volume(14)
        poems_data = [p.to_dict() for p in poems]

        # Title should be rewritten
        assert poems_data[0]['title'] == '太清宮樂章 序入破 第一奏'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
