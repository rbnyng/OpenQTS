"""
Special case handling for volumes with non-standard structure.

This module contains hardcoded split rules and special parsing logic
for volumes that cannot be handled by the generic scraper.
"""

# Volume 8: 後主煜 句 section
# All poems with titles starting with "句" by 後主煜 should be grouped together
# They represent a collection of fragments that should share the same entry_index
# Title patterns to recognize:
#   - "句 其一", "句 其二", etc. (numbered fragments)
#   - "句 律髓注", "句 翰府名談", etc. (source-labeled fragments)
VOLUME_8_JU_COLLECTION_AUTHOR = '後主煜'
VOLUME_8_JU_COLLECTION_PATTERN = r'^句\s+'  # Matches titles starting with "句 "

# Volume 8: Hardcoded splits for 後主煜 句 section
# These fragments don't have clear empty-line boundaries for generic splitting
# Format: List of (title_suffix, start_line, end_line) tuples
VOLUME_8_HOUZHUYU_JU_FRAGMENT_SPLITS = [
    ('其一', 0, 4),           # 迢迢牽牛星... (4 lines)
    ('其二', 4, 6),           # 鶯狂應有恨... (2 lines)
    ('其三', 6, 8),           # 揖讓月在手... (2 lines)
    ('其四', 8, 10),          # 病態如衰弱... (2 lines)
    ('律髓注', 10, 16),       # 衰顔一病難牽復... (6 lines)
    ('翰府名談', 16, 18),     # 萬古到頭歸一死... (2 lines)
    ('野客叢談', 18, 20),     # 人生不滿百... (2 lines)
    ('海錄碎事', 20, 22),     # 日映仙雲薄... (2 lines)
    ('其九', 22, 24),         # 烏照始潛輝... (2 lines)
    ('孔帖', 24, None),       # 凝珠滿露枝... (remaining lines)
]

# Volume 8: Custom splits for poems that need special handling
# Format: {
#   (title, author): {
#     'splits': [(start_line, end_line), ...],  # Line ranges for each part (0-based, end exclusive)
#     'base_title': str,  # Base title without part markers (optional, defaults to original title)
#   }
# }
VOLUME_8_CUSTOM_SPLITS = {
    ('句 其一', '嗣主璟'): {
        'splits': [
            (0, 2),  # Part 1: 靈槎思浩蕩, 老鶴倚崆峒
            (2, 4),  # Part 2: 蒼苔迷古道, 紅葉亂朝霞
            (4, 6),  # Part 3: 棲鳳枝梢猶軟弱, 化龍形狀已依稀
        ],
        'base_title': '句',  # Will become 句 其一, 句 其二, 句 其三
    },
}

# Format: Volume -> List of merge rules for entries that are actually notes
# marker: A unique string in the first line to confirm this is the note, not the poem
POEMS_TO_MERGE_AS_NOTES = {
    8: [
        {
            'title': '詠燈',
            'marker': '《詩史》云',
            'target': 'next'  # We are merging this entry into the NEXT one
        }
    ]
}

# Format: Volume -> List of merge rules for entries that are actually prefaces
# marker: A unique string in the first line to confirm this is the preface, not the poem
POEMS_TO_MERGE_AS_PREFACE = {
    8: [
        {
            'title': '題金樓子後',
            'marker': '梁元帝謂：',
            'target': 'next'  # We are merging this entry into the NEXT one
        }
    ],
    182: [
        {
            'title': '對酒憶賀監二首',
            'marker': '太子賓客賀公於長安紫極宮一見余，',
            'target': 'next'  # Merge preface into first poem
        }
    ],
    585: [
        {
            'title': '唐樂府十首',
            'marker': '《唐樂府》，自送征夫至獻賀觴商，歌河湟之事也。',
            'target': 'next'  # Merge preface into first part of multi-part series
        }
    ],
    592: [
        {
            'title': '四怨三愁五情詩十二首',
            'marker': '鬱於內者，怨也；阻於外者，愁也；犯於性者，情也。',
            'target': 'next'  # Merge preface into first part of multi-part series
        }
    ],
    820: [
        {
            'title': '南池雜詠五首',
            'marker': '余草堂在池上洲。',
            'target': 'next'  # Merge preface into first poem part (水月)
        }
    ],
    853: [
        {
            'title': '高士詠',
            'marker': '《易》稱：',  # First line of preface
            'target': 'next'  # Merge preface into first actual poem (混元皇帝)
        }
    ]
}

# Multi-part series where part 1 is a preface that should be merged
# even if it doesn't meet automatic prose detection threshold
FORCE_PREFACE_PARTS = {
    561: [
        {
            'title': '符亭二首 其一',
            'author': '薛能'
        }
    ],
}

# Override for consecutive merge when automatic pattern detection gets wrong count
# Used when title has multiple number patterns (e.g., "八詠應制二首" has both 八詠 and 二首)
FORCED_CONSECUTIVE_MERGE = {
    40: [
        {
            'title': '八詠應制二首',
            'author': '上官儀',
            'expected_parts': 2,  # Title has "二首" but regex matches "八詠" first
        }
    ],
}

# Volume 17: Custom splits for poems that need special handling
VOLUME_17_CUSTOM_SPLITS = {
    ('巫山高二首', '孟郊'): {
        'splits': [
            (0, 4),    # Part 1: 巴山上峽重複重... (4 lines)
            (4, 8),    # Part 2: 見盡數萬里... (4 lines)
        ],
        'base_title': '巫山高二首',
    },
}

# Volume 17: Multi-song poems that need splitting (Yuefu format)
# NOTE: Line counts are AFTER normalization (splitting on 。！？punctuation)
VOLUME_17_MULTISONG_SPLITS = [
    {
        'title_pattern': '戰城南二首',
        'line_count': 9,  # Normalized from 5 raw lines
        'num_songs': 2,
        'splits': [
            (0, 5),    # Song 1: 5 lines
            (5, 9),    # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '巫山高二首',
        'author': '沈佺期',
        'line_count': 8,  # Normalized from 4 raw lines
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 8),    # Song 2: 4 lines
        ]
    },
    # Note: 孟郊's 巫山高二首 now handled by VOLUME_17_CUSTOM_SPLITS
    {
        'title_pattern': '凱歌六首',
        'line_count': 12,  # Already normalized (no change)
        'num_songs': 6,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
            (4, 6),    # Song 3: 2 lines
            (6, 8),    # Song 4: 2 lines
            (8, 10),   # Song 5: 2 lines
            (10, 12),  # Song 6: 2 lines
        ]
    },
]

# Volume 18: Multi-song poems that need splitting (Yuefu format)
VOLUME_18_MULTISONG_SPLITS = [
    {
        'title_pattern': '橫吹曲辭·前出塞九首',
        'line_count': 36,
        'num_songs': 9,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
            (12, 16),   # Song 4: 4 lines
            (16, 20),   # Song 5: 4 lines
            (20, 24),   # Song 6: 4 lines
            (24, 28),   # Song 7: 4 lines
            (28, 32),   # Song 8: 4 lines
            (32, 36),   # Song 9: 4 lines
        ]
    },
    {
        'title_pattern': '橫吹曲辭·後出塞五首',
        'line_count': 31,
        'num_songs': 5,
        'splits': [
            (0, 7),     # Song 1: 7 lines
            (7, 13),    # Song 2: 6 lines
            (13, 19),   # Song 3: 6 lines
            (19, 25),   # Song 4: 6 lines
            (25, 31),   # Song 5: 6 lines
        ]
    },
    {
        'title_pattern': '橫吹曲辭·關山月二首',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
]

VOLUME_19_MULTISONG_SPLITS = [
    # All configs commented out - line counts don't match normalized data
    # User needs to provide correct splits based on actual normalized line counts
]

# Volume 20: Multi-song poems that need splitting
VOLUME_20_MULTISONG_SPLITS = [
    {
        'title_pattern': '相和歌辭·前苦寒行二首',
        'author': '杜甫',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 couplets
            (4, 8),    # Song 2: 4 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·後苦寒行二首',
        'author': '杜甫',
        'line_count': 7, 
        'num_songs': 2,
        'splits': [
            (0, 3),    # Song 1: 3 couplets (irregular structure in source)
            (3, 7),    # Song 2: 4 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·相逢行二首',
        'author': '李白',
        'line_count': 12,
        'num_songs': 2,
        'splits': [
            (0, 10),   # Song 1: 10 couplets
            (10, 12),  # Song 2: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·白頭吟二首',
        'author': '李白',
        'line_count': 33,
        'num_songs': 2,
        'splits': [
            (0, 15),   # Song 1: 15 couplets
            (15, 33),  # Song 2: 18 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·決絕詞三首',
        'author': '元稹',
        'line_count': 29,
        'num_songs': 3,
        'splits': [
            (0, 9),    # Song 1: 9 couplets
            (9, 19),   # Song 2: 10 couplets
            (19, 29),  # Song 3: 10 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·怨詩二首',
        'author': '薛奇童',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 couplets
            (4, 8),    # Song 2: 4 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·怨詩三首',
        'author': '李暇',
        'line_count': 6,
        'num_songs': 3,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 4),    # Song 2: 2 couplets
            (4, 6),    # Song 3: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·怨詩二首',
        'author': '崔國輔',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 4),    # Song 2: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·怨詩二首',
        'author': '姚氏月華',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 4),    # Song 2: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·長門怨二首',
        'author': '李白',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 4),    # Song 2: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·長門怨二首',
        'author': '高蟾',
        'line_count': 6,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 6),    # Song 2: 4 couplets (combines stanzas 2 and 3)
        ]
    },
    {
        'title_pattern': '相和歌辭·長門怨二首',
        'author': '鄭谷',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 4),    # Song 2: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·長門怨二首',
        'author': '劉氏媛',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 4),    # Song 2: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·班婕妤三首',
        'author': '王維',
        'line_count': 6,
        'num_songs': 3,
        'splits': [
            (0, 2),    # Song 1: 2 couplets
            (2, 4),    # Song 2: 2 couplets
            (4, 6),    # Song 3: 2 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·雜怨三首',
        'author': '聶夷中',
        'line_count': 9,
        'num_songs': 3,
        'splits': [
            (0, 4),    # Song 1: 4 couplets
            (4, 6),    # Song 2: 2 couplets
            (6, 9),    # Song 3: 3 couplets
        ]
    },
    {
        'title_pattern': '相和歌辭·雜怨三首',
        'author': '孟郊',
        'line_count': 13,
        'num_songs': 3,
        'splits': [
            (0, 4),    # Song 1: 4 couplets
            (4, 9),    # Song 2: 5 couplets
            (9, 13),   # Song 3: 4 couplets
        ]
    },
]

# Volume 21: Seasonal sets that need to be merged (share entry_index)
# Format: {
#   'base_title': str,  # Base title pattern to match
#   'author': str,      # Author name
#   'expected_count': int,  # Expected number of seasonal poems
#   'season_patterns': list[str],  # Ordered list of seasonal suffixes
# }
VOLUME_21_SEASONAL_SETS = [
    {
        'base_title': '相和歌辭·子夜四時歌四首',
        'author': '李白',
        'expected_count': 4,
        'part_patterns': ['春歌', '夏歌', '秋歌', '冬歌'],
    },
    {
        'base_title': '相和歌辭·子夜四時歌四首',
        'author': '陸龜蒙',
        'expected_count': 4,
        'part_patterns': ['春歌', '夏歌', '秋歌', '冬歌'],
    },
    {
        'base_title': '相和歌辭·子夜四時歌六首',
        'author': '郭元振',
        'expected_count': 6,
        'part_patterns': ['春歌二首 其一', '春歌二首 其二',
                         '秋歌二首 其一', '秋歌二首 其二',
                         '冬歌二首 其一', '冬歌二首 其二'],
    },
]

# Volume 13: Temple music sets that need to be merged (share entry_index)
# Format: {
#   'base_title': str,  # Base title pattern to match
#   'author': str,      # Author name
#   'expected_count': int,  # Expected number of parts
#   'part_patterns': list[str],  # Ordered list of part suffixes
# }
VOLUME_13_TEMPLE_MUSIC_SETS = [
    {
        'base_title': '郊廟歌辭 武後享清廟樂章十首',
        'author': 'Unknown',
        'expected_count': 10,
        'part_patterns': ['第一', '第二', '第三登歌', '第四迎神', '第五飲福',
                         '第六送文舞', '第七迎武舞', '第八武舞作', '第九徹俎', '第十送神'],
    },
]

# Volume 41: Named part sets that need to be merged (share entry_index)
# 中和樂九章 - Nine Chapters of Zhonghe Music by 盧照鄰
VOLUME_41_NAMED_PART_SETS = [
    {
        'base_title': '中和樂九章',
        'author': '盧照鄰',
        'expected_count': 9,
        'part_patterns': ['歌登封第一', '歌明堂第二', '歌東軍第三', '歌南郊第四',
                         '歌中宮第五', '歌儲宮第六', '歌諸王第七', '歌公卿第八', '總歌第九'],
    },
]

# Volume 66: Named part sets that need to be merged (share entry_index)
# Format: {
#   'base_title': str,  # Base title pattern to match
#   'author': str,      # Author name
#   'expected_count': int,  # Expected number of parts
#   'part_patterns': list[str],  # Ordered list of part suffixes
# }
VOLUME_66_NAMED_PART_SETS = [
    {
        'base_title': '子夜四時歌六首',
        'author': '郭震',
        'expected_count': 6,
        'part_patterns': ['春歌一', '春歌二', '秋歌一', '秋歌二', '冬歌一', '冬歌二'],
    },
]

# Volume 83: Named part sets that need to be merged (share entry_index)
VOLUME_83_NAMED_PART_SETS = [
    {
        'base_title': '薊丘覽古贈盧居士藏用七首',
        'author': '陳子昂',
        'expected_count': 7,
        'part_patterns': ['軒轅臺', '燕昭王', '樂生', '燕太子', '田光先生', '鄒衍', '郭隗'],
    },
]

# Volume 86: Named part sets that need to be merged (share entry_index)
VOLUME_86_NAMED_PART_SETS = [
    {
        'base_title': '五君詠五首',
        'author': '張說',
        'expected_count': 5,
        'part_patterns': ['魏齊公元忠', '蘇許公瓌', '李趙公嶠', '郭代公元振', '趙耿公彥昭'],
    },
]

# Volume 128: Named part sets that need to be merged (share entry_index)
VOLUME_128_NAMED_PART_SETS = [
    {
        'base_title': '皇甫嶽雲溪雜題五首',
        'author': '王維',
        'expected_count': 5,
        'part_patterns': ['鳥鳴澗', '蓮花塢', '鸕鶿堰', '上平田', '萍池'],
    },
]

# Volume 129: Named part sets that need to be merged (share entry_index)
VOLUME_129_NAMED_PART_SETS = [
    {
        'base_title': '輞川集二十首',
        'author': '裴迪',
        'expected_count': 20,
        'part_patterns': ['孟城坳', '華子岡', '文杏館', '斤竹嶺', '鹿柴', '木蘭柴', '茱萸沜', '宮槐陌',
                         '臨湖亭', '南垞', '欹湖', '柳浪', '欒家瀨', '金屑泉', '白石灘', '北垞',
                         '竹里館', '辛夷塢', '漆園', '椒園'],
    },
]

# Volume 136: Named part sets that need to be merged (share entry_index)
VOLUME_136_NAMED_PART_SETS = [
    {
        'base_title': '雜詠五首',
        'author': '儲光羲',
        'expected_count': 5,
        'part_patterns': ['石子松', '架簷藤', '池邊鶴', '釣魚灣', '幽人居'],
    },
]

# Volume 148: Named part sets that need to be merged (share entry_index)
VOLUME_148_NAMED_PART_SETS = [
    {
        'base_title': '湘中紀行十首',
        'author': '劉長卿',
        'expected_count': 10,
        'part_patterns': ['湘妃廟', '斑竹巖', '洞山陽', '雲母溪', '赤沙湖', '秋雲嶺', '花石潭', '石圍峰',
                         '浮石瀨', '橫龍渡'],
    },
    {
        'base_title': '雜詠八首上禮部李侍郎',
        'author': '劉長卿',
        'expected_count': 8,
        'part_patterns': ['幽琴', '晚桃', '疲馬', '春鏡', '古劒', '舊井', '白鷺', '寒釭'],
    },
]

# Volume 234: Named part sets that need to be merged (share entry_index)
# Note: These are parts 7-9 of a 9-part poem (parts 1-6 are in Volume 13)
VOLUME_234_NAMED_PART_SETS = [
    {
        'base_title': '絕句九首',
        'author': '杜甫',
        'expected_count': 3,  # Parts 7, 8, 9 (first 6 parts are in Volume 13)
        'part_patterns': [
            '絕句九首',  # Part 7: 聞道巴山裏... (with preface)
            '絕句九首',  # Part 8: 水檻溫江口...
            '絕句九首',  # Part 9: 設道春來好...
        ],
    },
]

# Volume 240: Named part sets that need to be merged (share entry_index)
VOLUME_240_NAMED_PART_SETS = [
    {
        'base_title': '系樂府十二首',
        'author': '元結',
        'expected_count': 12,
        'part_patterns': ['思太古', '隴上歎', '頌東夷', '賤士吟', '欸乃曲', '貧婦詞', '去鄉悲', '壽翁興',
                         '農臣怨', '謝大龜', '古遺歎', '下客謠'],
    },
    {
        'base_title': '引極三首',
        'author': '元結',
        'expected_count': 3,
        'part_patterns': ['思元極', '望仙府', '懷潛君'],
    },
    {
        'base_title': '演興四首',
        'author': '元結',
        'expected_count': 4,
        'part_patterns': ['招太靈', '初祀', '訟木魅', '閔嶺中'],
    },
]

# Volume 264: Custom splits for poems that need special handling
# 上古之什補亡訓傳十三章 - some entries have 二章 (2 stanzas) that need splitting
VOLUME_264_CUSTOM_SPLITS = {
    ('上古之什補亡訓傳十三章 左車二章', '顧況'): {
        'splits': [
            (0, 3),  # Part 1: 左車有慶，萬人猶病。曷可去之，於黨孔盛。敏爾之生，胡為波迸。
            (3, 6),  # Part 2: 左車有赫，萬人毒螫。曷可去之，於黨孔碩。敏爾之生，胡為草戚。
        ],
        'base_title': '上古之什補亡訓傳十三章 左車二章',
    },
    ('上古之什補亡訓傳十三章 築城二章', '顧況'): {
        'splits': [
            (0, 3),  # Part 1: 築城登登，於以作固。咨爾寺兮，發郊外塚墓。死而無知，猶或不可；若其有知，惟上帝是愬。
            (3, 7),  # Part 2: 築城奕奕，於以固敵。咨爾寺兮，發郊外塚甓。死而無知，猶或不可。若其有知，惟上帝是謫。
        ],
        'base_title': '上古之什補亡訓傳十三章 築城二章',
    },
}

# Volume 264: Named part sets that need to be merged (share entry_index)
# 上古之什補亡訓傳十三章 - 13 chapters by 顧況
# Note: 左車二章 and 築城二章 are split first via VOLUME_264_CUSTOM_SPLITS
VOLUME_264_NAMED_PART_SETS = [
    {
        'base_title': '上古之什補亡訓傳十三章',
        'author': '顧況',
        'expected_count': 13,
        'part_patterns': ['上古一章',
                         '左車二章 其一', '左車二章 其二',
                         '築城二章 其一', '築城二章 其二',
                         '持斧一章', '十月之郊一章', '燕於巢一章', '蘇方一章',
                         '陵霜之華一章', '囝一章', '我行自東一章', '採蠟一章'],
    },
]

# Volume 271: Named part sets that need to be merged (share entry_index)
# Note: Title says 三首 (3 poems) but only 2 are extant
VOLUME_271_NAMED_PART_SETS = [
    {
        'base_title': '貞懿皇后輓歌三首',
        'author': '竇叔向',
        'expected_count': 2,  # Only 2 of 3 parts are extant
        'part_patterns': [
            '貞懿皇后輓歌三首',  # Part 1: 二陵恭婦道...
            '貞懿皇后輓歌三首',  # Part 2: 後庭攀畫柳...
        ],
    },
]

# Volume 387: Named part sets that need to be merged (share entry_index)
VOLUME_387_NAMED_PART_SETS = [
    {
        'base_title': '蕭宅二三子贈答詩二十首',
        'author': '盧仝',
        'expected_count': 20,
        'part_patterns': ['客贈石', '石讓竹', '竹答客', '石請客', '客答石', '石答竹', '竹請客', '客謝竹',
                         '石請客', '客謝石', '石再請客', '客許石', '井請客', '客謝井', '馬蘭請客', '客請馬蘭',
                         '蛺蝶請客', '客答蛺蝶', '蝦䗫請客', '客請蝦䗫'],
    },
]

# Volume 388: Custom splits for multi-part poems (marker-based)
VOLUME_388_CUSTOM_SPLITS = {
    ('冬行三首', '盧仝'): {
        'markers': [
            '長年愛伊洛，',     # Part 2
            '不敢唾汴水，',     # Part 3
        ],
        'base_title': '冬行三首',
    },
    ('憶金鵝山沈山人二首', '盧仝'): {
        'markers': [
            '君愛鍊藥藥欲成，',  # Part 2
        ],
        'base_title': '憶金鵝山沈山人二首',
    },
    ('感古四首', '盧仝'): {
        'markers': [
            '古來不患寡，',     # Part 2
            '君莫以富貴，',  # Part 3
            '其奈一朝太守振羽儀，',  # Part 4
        ],
        'base_title': '感古四首',
    },
}

# Volume 390: Custom splits for multi-part poems (marker-based)
VOLUME_390_CUSTOM_SPLITS = {
    ('南園十三首', '李賀'): {
        'markers': [
            '宮北田塍曉氣酣，',    # Part 2
            '竹裏繰絲挑網車，',    # Part 3
            '三十未有二十餘，',    # Part 4
            '男兒何不帶吳鉤，',    # Part 5
            '尋章摘句老雕蟲，',    # Part 6
            '長卿牢落悲空舍，',    # Part 7
            '春水初生乳燕飛，',    # Part 8
            '泉沙耎臥鴛鴦暖，',    # Part 9
            '邊讓今朝憶蔡邕，',    # Part 10
            '長巒谷口倚嵇家，',    # Part 11
            '松溪黑水新龍卵，',    # Part 12
            '小樹開朝逕，',          # Part 13
        ],
        'base_title': '南園十三首',
    },
}

# Volume 394: Custom splits for multi-part poems (marker-based)
VOLUME_394_CUSTOM_SPLITS = {
    ('感諷六首', '李賀'): {
        'markers': [
            '苦風吹朔寒，',     # Part 2
            '雜雜胡馬塵，',     # Part 3
            '青門放彈去，',     # Part 4
            '曉菊泫寒露，',     # Part 5
            '蝶飛紅粉臺，',     # Part 6
        ],
        'base_title': '感諷六首',
    },
}

# Volume 397: Custom splits for multi-part poems (marker-based)
VOLUME_397_CUSTOM_SPLITS = {
    ('諭寶二首', '元稹'): {
        'markers': [
            '冰置白玉壺，',  # Part 2
        ],
        'base_title': '諭寶二首',
    },
}

# Volume 400: Custom splits for multi-part poems (marker-based)
VOLUME_400_CUSTOM_SPLITS = {
    ('楊子華畫三首', '元稹'): {
        'markers': [
            '皓腕卷紅袖，',  # Part 2
            '顛倒世人心，',  # Part 3
        ],
        'base_title': '楊子華畫三首',
    },
}

# Volume 403: Custom splits for multi-part poems (marker-based)
VOLUME_403_CUSTOM_SPLITS = {
    ('酬樂天赴江州路上見寄三首', '元稹'): {
        'markers': [
            '襄陽大堤繞，',  # Part 2
            '人亦有相愛，',  # Part 3
        ],
        'base_title': '酬樂天赴江州路上見寄三首',
    },
    ('代杭人作使君一朝去二首', '元稹'): {
        'markers': [
            '使君一朝去，',  # Part 2
        ],
        'base_title': '代杭人作使君一朝去二首',
    },
}

# Volume 410: Custom splits for multi-part poems (marker-based)
VOLUME_410_CUSTOM_SPLITS = {
    ('生春二十首', '元稹'): {
        'markers': [
            '春生漫雪中。',   # Part 2
            '春生霽色中。',   # Part 3
            '春生曙火中。',   # Part 4
            '春生曉禁中。',   # Part 5
            '春生江路中。',   # Part 6
            '春生野墅中。',   # Part 7
            '春生冰岸中。',   # Part 8
            '春生柳眼中。',   # Part 9
            '春生梅援中。',   # Part 10
            '春生鳥思中。',   # Part 11
            '春生池榭中。',   # Part 12
            '春生稚戲中。',   # Part 13
            '春生人意中。',   # Part 14
            '春生半睡中。',   # Part 15
            '春生曉鏡中。',   # Part 16
            '春生綺戶中。',   # Part 17
            '春生老病中。',   # Part 18
            '春生客思中。',   # Part 19
            '春生蒙雨中。',   # Part 20
        ],
        'base_title': '生春二十首',
    },
}

# Volume 413: Custom splits for multi-part poems (marker-based)
VOLUME_413_CUSTOM_SPLITS = {
    ('放言五首', '元稹'): {
        'markers': [
            '莫將心事厭長沙，',  # Part 2
            '霆轟電烻數聲頻，',  # Part 3
            '安得心源處處安，',  # Part 4
            '三十年來世上行，',  # Part 5
        ],
        'base_title': '放言五首',
    },
}

# Volume 414: Custom splits for multi-part poems (marker-based)
VOLUME_414_CUSTOM_SPLITS = {
    ('西歸絕句十二首', '元稹'): {
        'markers': [
            '五年江上損容顏，',  # Part 2
            '同歸諫院韋丞相，',  # Part 3
            '只去長安六日期，',  # Part 4
            '白頭歸舍意如何，',  # Part 5
            '還鄉何用淚沾襟，',  # Part 6
            '閒遊寺觀從容到，',  # Part 7
            '一世營營死是休，',  # Part 8
            '今朝西渡丹河水，',  # Part 9
            '寒窗風雪擁深爐，',  # Part 10
            '雲覆藍橋雪滿溪，',  # Part 11
            '寒花帶雪滿山腰，',  # Part 12
        ],
        'base_title': '西歸絕句十二首',
    },
}

# Volume 421: Custom splits for multi-part poems (marker-based)
VOLUME_421_CUSTOM_SPLITS = {
    ('通州丁溪館夜別李景信三首', '元稹'): {
        'markers': [
            '水環環兮山簇簇，',  # Part 2
            '雨瀟瀟兮鵑咽咽，',  # Part 3
        ],
        'base_title': '通州丁溪館夜別李景信三首',
    },
}

# Volume 425: Custom splits for multi-part poems (marker-based)
VOLUME_425_CUSTOM_SPLITS = {
    ('歎魯二首', '白居易'): {
        'markers': [
            '展禽胡為者？',  # Part 2
        ],
        'base_title': '歎魯二首',
    },
}

# Volume 424: Custom splits for multi-part poems (marker-based)
VOLUME_424_CUSTOM_SPLITS = {
    ('雜興三首', '白居易'): {
        'markers': [
            '越國政初荒，',  # Part 2
            '吳王心日侈，',  # Part 3
        ],
        'base_title': '雜興三首',
    },
    ('傷唐衢二首', '白居易'): {
        'markers': [
            '憶昨元和初，',  # Part 2
        ],
        'base_title': '傷唐衢二首',
    },
}

# Volume 429: Custom splits for multi-part poems (marker-based)
VOLUME_429_CUSTOM_SPLITS = {
    ('適意二首', '白居易'): {
        'markers': [
            '早歲從旅遊，',  # Part 2
        ],
        'base_title': '適意二首',
    },
    ('歸田三首', '白居易'): {
        'markers': [
            '種田意已決，',  # Part 2
            '三十為近臣，',  # Part 3
        ],
        'base_title': '歸田三首',
    },
}

# Volume 430: Custom splits for multi-part poems (marker-based)
VOLUME_430_CUSTOM_SPLITS = {
    ('小池二首', '白居易'): {
        'markers': [
            '有意不在大，',  # Part 2
        ],
        'base_title': '小池二首',
    },
}

# Volume 431: Custom splits for multi-part poems (marker-based)
VOLUME_431_CUSTOM_SPLITS = {
    ('三年為刺史二首', '白居易'): {
        'markers': [
            '三年為刺史，',  # Part 2
        ],
        'base_title': '三年為刺史二首',
    },
}

# Volume 433: Custom splits for multi-part poems (marker-based)
VOLUME_433_CUSTOM_SPLITS = {
    ('歎老三首', '白居易'): {
        'markers': [
            '我有一握髮，',  # Part 2
            '前年種桃核，',  # Part 3
        ],
        'base_title': '歎老三首',
    },
    ('念金鑾子二首', '白居易'): {
        'markers': [
            '與爾為父子，',  # Part 2
        ],
        'base_title': '念金鑾子二首',
    },
    ('村居臥病三首', '白居易'): {
        'markers': [
            '新秋久病容，',  # Part 2
            '種黍三十畝，',  # Part 3
        ],
        'base_title': '村居臥病三首',
    },
    ('自覺二首', '白居易'): {
        'markers': [
            '朝哭心所愛，',  # Part 2
        ],
        'base_title': '自覺二首',
    },
    ('寄微之三首', '白居易'): {
        'markers': [
            '君遊襄陽日，',  # Part 2
            '去國日已遠，',  # Part 3
        ],
        'base_title': '寄微之三首',
    },
    ('因沐感髮，寄朗上人二首', '白居易'): {
        'markers': [
            '漸少不滿把，',  # Part 2
        ],
        'base_title': '因沐感髮，寄朗上人二首',
    },
}

# Volume 434: Custom splits for multi-part poems (marker-based)
VOLUME_434_CUSTOM_SPLITS = {
    ('東坡種花二首', '白居易'): {
        'markers': [
            '東坡春向暮，',  # Part 2
        ],
        'base_title': '東坡種花二首',
    },
    ('曲江感秋二首', '白居易'): {
        'markers': [
            '疏蕪南岸草，',  # Part 2
        ],
        'base_title': '曲江感秋二首',
    },
    ('玩松竹二首', '白居易'): {
        'markers': [
            '坐愛前簷前，',  # Part 2
        ],
        'base_title': '玩松竹二首',
    },
}

# Volume 439: Custom splits for multi-part poems (marker-based)
VOLUME_439_CUSTOM_SPLITS = {
    ('春末夏初閒遊江郭二首', '白居易'): {
        'markers': [
            '柳影繁初合，',  # Part 2
        ],
        'base_title': '春末夏初閒遊江郭二首',
    },
}

# Volume 440: Custom splits for multi-part poems (marker-based)
VOLUME_440_CUSTOM_SPLITS = {
    ('送蕭煉師步虛詞十首，卷後以二絕繼之', '白居易'): {
        'markers': [
            '花紙瑤緘松墨字，',  # Part 2
        ],
        'base_title': '送蕭煉師步虛詞十首，卷後以二絕繼之',
    },
}

# Volume 441: Custom splits for multi-part poems (marker-based)
VOLUME_441_CUSTOM_SPLITS = {
    ('獨眠吟二首', '白居易'): {
        'markers': [
            '獨眠客，',  # Part 2
        ],
        'base_title': '獨眠吟二首',
    },
}

# Volume 444: Custom splits for multi-part poems (marker-based)
VOLUME_444_CUSTOM_SPLITS = {
    ('吳中好風景二首', '白居易'): {
        'markers': [
            '吳中好風景，',  # Part 2
        ],
        'base_title': '吳中好風景二首',
    },
    ('有感三首', '白居易'): {
        'markers': [
            '莫養瘦馬駒，',  # Part 2
            '往事勿追思，',  # Part 3
        ],
        'base_title': '有感三首',
    },
}

# Volume 445: Custom splits for multi-part poems (marker-based)
VOLUME_445_CUSTOM_SPLITS = {
    ('偶作二首', '白居易'): {
        'markers': [
            '日出起盥櫛，',  # Part 2
        ],
        'base_title': '偶作二首',
    },
}

# Volume 446: Custom splits for multi-part poems (marker-based)
VOLUME_446_CUSTOM_SPLITS = {
    ('泛小䑳二首', '白居易'): {
        'markers': [
            '船緩進，',  # Part 2
        ],
        'base_title': '泛小䑳二首',
    },
}

# Volume 449: Custom splits for multi-part poems (marker-based)
VOLUME_449_CUSTOM_SPLITS = {
    ('和春深二十首', '白居易'): {
        'markers': [
            '何處春深好，',  # Part 2
            '何處春深好，',  # Part 3
            '何處春深好，',  # Part 4
            '何處春深好，',  # Part 5
            '何處春深好，',  # Part 6
            '何處春深好，',  # Part 7
            '何處春深好，',  # Part 8
            '何處春深好，',  # Part 9
            '何處春深好，',  # Part 10
            '何處春深好，',  # Part 11
            '何處春深好，',  # Part 12
            '何處春深好，',  # Part 13
            '何處春深好，',  # Part 14
            '何處春深好，',  # Part 15
            '何處春深好，',  # Part 16
            '何處春深好，',  # Part 17
            '何處春深好，',  # Part 18
            '何處春深好，',  # Part 19
            '何處春深好，',  # Part 20
        ],
        'base_title': '和春深二十首',
    },
}

# Volume 451: Custom splits for multi-part poems (marker-based)
VOLUME_451_CUSTOM_SPLITS = {
    ('不准擬二首', '白居易'): {
        'markers': [
            '憶昔謫居炎瘴地，',  # Part 2
        ],
        'base_title': '不准擬二首',
    },
}

# Volume 453: Custom splits for multi-part poems (marker-based)
VOLUME_453_CUSTOM_SPLITS = {
    ('旱熱二首', '白居易'): {
        'markers': [
            '勃勃旱塵氣，',  # Part 2
        ],
        'base_title': '旱熱二首',
    },
    ('偶作二首', '白居易'): {
        'markers': [
            '名無高與卑，',  # Part 2
        ],
        'base_title': '偶作二首',
    },
}

# Volume 458: Custom splits for multi-part poems (marker-based)
# Volume 458: VOLUME_458_CUSTOM_SPLITS moved to line ~1089 (merged with other 458 configs)

# Volume 459: Custom splits for multi-part poems (marker-based)
VOLUME_459_CUSTOM_SPLITS = {
    ('春日閒居三首', '白居易'): {
        'markers': [
            '廣池春水平，',  # Part 2
            '勞者不覺歌，',  # Part 3
        ],
        'base_title': '春日閒居三首',
    },
}

# Volume 475: Named part sets that need to be merged (share entry_index)
VOLUME_475_NAMED_PART_SETS = [
    {
        'base_title': '春暮思平泉雜詠二十首',
        'author': '李德裕',
        'expected_count': 20,
        'part_patterns': ['望伊川', '潭上紫藤', '書樓晴望', '西嶺望鳴皋山', '瀑泉亭', '紅桂樹', '金松',
                         '月桂', '山桂', '柏', '芳蓀', '流杯亭', '東溪', '鸂鶒', '西園', '海石楠',
                         '雙碧潭', '竹徑', '花藥欄', '自敘'],
    },
    {
        'base_title': '思山居一十首',
        'author': '李德裕',
        'expected_count': 11,  # Note: Title says "一十首" (10) but actually has 11 parts
        'part_patterns': ['清明後憶山中', '題寄商山石', '憶種苽時', '春日獨坐思歸', '思登家山林嶺',
                         '思鄉園老人', '寄龍門僧', '憶藥苗', '憶村中老人春酒', '憶葛勝木禪床', '初夏有懷山居'],
    },
    {
        'base_title': '思平泉樹石雜詠一十首',
        'author': '李德裕',
        'expected_count': 10,
        'part_patterns': ['釣臺', '似鹿石', '海上石筍', '疊石', '重臺芙蓉', '白鷺鶿', '海魚骨', '泛池舟',
                         '舴艋舟', '二猿'],
    },
    {
        'base_title': '重憶山居六首',
        'author': '李德裕',
        'expected_count': 6,
        'part_patterns': ['平泉源', '泰山石', '巫山石', '羅浮山', '漏潭石', '釣石'],
    },
    {
        'base_title': '東郡懷古二首',
        'author': '李德裕',
        'expected_count': 2,
        'part_patterns': ['王京兆', '陽給事'],
    },
]

# Volume 685: Custom splits for poems that need special handling
VOLUME_685_CUSTOM_SPLITS = {
    ('和韓致光侍郎無題三首十四韻', '吳融'): {
        'markers': [
            '舞轉輕輕雪，',  # Part 2
            '綺閣臨初日，',  # Part 3
        ],
        'base_title': '和韓致光侍郎無題三首十四韻',
    },
}

# Volume 686: Custom splits for poems that need special handling
VOLUME_686_CUSTOM_SPLITS = {
    ('南遷途中作七首 登七盤嶺二首', '吳融'): {
        'splits': [
            (0, 2),  # Part 1: 才非賈傅亦遷官，五月驅羸上七盤。從此自知身計定，不能迴首望長安。
            (2, 4),  # Part 2: 七盤嶺上一長號，將謂青天鑒鬱陶。近日青天都不鑒，七盤應是未高高。
        ],
        'base_title': '南遷途中作七首 登七盤嶺二首',  # Will become 南遷途中作七首 登七盤嶺二首 其一, 其二
    },
}

# Volume 686: Named part sets that need to be merged (share entry_index)
VOLUME_686_NAMED_PART_SETS = [
    {
        'base_title': '閿鄉寓居十首',
        'author': '吳融',
        'expected_count': 10,
        'part_patterns': ['阿對泉', '蛙聲', '茆堂', '清溪', '釣竿', '山僧', '小徑', '聞提壺鳥', '木塔偶題', '山禽'],
    },
    {
        'base_title': '南遷途中作七首',
        'author': '吳融',
        'expected_count': 7,
        # Note: Parts 1-2 are from the nested "登七盤嶺二首" which gets custom-split first
        'part_patterns': ['登七盤嶺二首 其一', '登七盤嶺二首 其二', '渡漢江初嘗鯿魚有作', '溪翁',
                         '寄友人', '途中偶懷', '訪貫休上人'],
    },
]

# Volume 853: Named part sets for 吳筠's 高士詠 (50 poems about high scholars)
# use_custom_titles=True means part_patterns are used as actual titles (not suffixes)
VOLUME_853_NAMED_PART_SETS = [
    {
        'base_title': '高士詠',
        'author': '吳筠',
        'expected_count': 50,
        'use_custom_titles': True,  # Part patterns become the actual titles
        'part_patterns': [
            '混元皇帝', '廣成子', '許先生', '樊先生', '柏成子高',
            '臧丈人', '伯夷叔齊', '南華真人', '沖虛真人', '洞靈真人',
            '通玄真人', '文始真人', '榮啟期', '長沮桀溺', '顏闔',
            '老萊夫妻', '楚狂接輿夫妻', '鄭商人弦高', '柳下惠', '荷蓧晨門',
            '漢陰丈人', '於陵夫妻', '項橐', '太伯延陵', '壺丘子',
            '段幹木', '魯仲連', '顏歜', '周豐', '師金',
            '南郭子綦', '黔婁先生', '原憲', '商山四皓', '河上公',
            '東方曼倩', '嚴君平', '司馬季主', '鄭子真張仲蔚', '嚴子陵',
            '向子平', '韓康', '臺佟管甯', '高鳳', '龐德公',
            '玄晏先生', '孫公和', '董威輦', '郭文舉', '陶征君',
        ],
    },
]

# Volume 690: Custom splits for multi-part poems (marker-based)
VOLUME_690_CUSTOM_SPLITS = {
    ('惆悵詩十二首', '王渙'): {
        'markers': [
            '李夫人病已經秋，',  # Part 2
            '謝家池館花籠月，',  # Part 3
            '隋師戰艦欲亡陳，',  # Part 4
            '七夕瓊筵隨事陳，',  # Part 5
            '夜寒春病不勝懷，',  # Part 6
            '嗚咽離聲管吹秋，',  # Part 7
            '青絲一綹墮雲鬟，',  # Part 8
            '陳宮興廢事難期，',  # Part 9
            '晨肇重來路已迷，',  # Part 10
            '少卿降北子卿還，',  # Part 11
            '夢裏分明入漢宮，',  # Part 12
        ],
        'base_title': '惆悵詩十二首',
    },
}

# Volume 727: Custom splits for multi-part poems (marker-based)
VOLUME_727_CUSTOM_SPLITS = {
    ('宿顧城二首', '張直'): {
        'markers': [
            '醉臥夜將半，',  # Part 2
        ],
        'base_title': '宿顧城二首',
    },
}

# Volume 745: Custom splits for multi-part poems (marker-based)
VOLUME_745_CUSTOM_SPLITS = {
    ('懷仙吟二首', '陳陶'): {
        'markers': [
            '雲溪古流水，',  # Part 2
        ],
        'base_title': '懷仙吟二首',
    },
}

# Volume 752: Custom splits for multi-part poems (marker-based)
VOLUME_752_CUSTOM_SPLITS = {
    ('柳枝辭十二首', '徐鉉'): {
        'markers': [
            '南園日暮起春風，',  # Part 2
            '陌上朱門柳映花，',  # Part 3
            '夾岸朱欄柳映樓，',  # Part 4
            '老大逢春總恨春，',  # Part 5
            '濛濛堤畔柳含煙，',  # Part 6
            '水閣春來乍減寒，',  # Part 7
            '柳岸煙昏醉裏歸，',  # Part 8
            '此去仙源不是遙，',  # Part 9
            '暫別揚州十度春，',  # Part 10
            '仙樂春來按舞腰，',  # Part 11
            '鳳笙臨檻不能吹，',  # Part 12
        ],
        'base_title': '柳枝辭十二首',
    },
}

# Volume 754: Custom splits for multi-part poems (marker-based)
VOLUME_754_CUSTOM_SPLITS = {
    ('拋毬樂辭二首', '徐鉉'): {
        'markers': [
            '灼灼傳花枝，',  # Part 2
        ],
        'base_title': '拋毬樂辭二首',
    },
}

# Volume 769: Custom splits for multi-part poems (marker-based)
VOLUME_769_CUSTOM_SPLITS = {
    ('侍宴賦得起坐彈鳴琴二首', '楊希道'): {
        'markers': [
            '絲傳園客意，',  # Part 2
        ],
        'base_title': '侍宴賦得起坐彈鳴琴二首',
    },
}

# Volume 770: Custom splits for multi-part poems (marker-based)
VOLUME_770_CUSTOM_SPLITS = {
    ('還渭南感舊二首', '唐暄'): {
        'markers': [
            '常時華室靜，',  # Part 2
        ],
        'base_title': '還渭南感舊二首',
    },
}

# Volume 777: Custom splits for multi-part poems (marker-based)
VOLUME_777_CUSTOM_SPLITS = {
    ('古興二首', '沈徽'): {
        'markers': [
            '長安富豪右，',  # Part 2
        ],
        'base_title': '古興二首',
    },
}

# Volume 785: Custom splits for multi-part poems (marker-based)
VOLUME_785_CUSTOM_SPLITS = {
    ('春二首', '無名氏'): {
        'markers': [
            '烏足遲遲日宮裏，',  # Part 2
        ],
        'base_title': '春二首',
    },
}

# Volume 798: Custom splits for 花蕊夫人 宮詞 (157 quatrains)
# 314 lines = 157 quatrains (2 lines each)
_HUARUI_GONGCI_SPLITS = [(i*2, (i+1)*2) for i in range(157)]
VOLUME_798_CUSTOM_SPLITS = {
    ('花蕊夫人徐氏 宮詞', '花蕊夫人'): {
        'splits': _HUARUI_GONGCI_SPLITS,
        'base_title': '宮詞',
    },
}

# Volume 800: Custom splits for multi-part poems (marker-based)
VOLUME_800_CUSTOM_SPLITS = {
    ('子夜歌十八首', '晁采'): {
        'markers': [
            '夜夜不成寐，',  # Part 2
            '何時得成匹，',  # Part 3
            '相逢逐涼候，',  # Part 4
            '明窗弄玉指，',  # Part 5
            '寄語閨中娘，',  # Part 6
            '良會終有時，',  # Part 7
            '醉夢幸逢郎，',  # Part 8
            '信使無虛日，',  # Part 9
            '繡房擬會郎，',  # Part 10
            '相思百餘日，',  # Part 11
            '金盆盥素手，',  # Part 12
            '花池多芳水，',  # Part 13
            '感郎金鍼贈，',  # Part 14
            '寒風響枯木，',  # Part 15
            '得郎日嗣音，',  # Part 16
            '輕巾手自製，',  # Part 17
            '儂贈綠絲衣，',  # Part 18
        ],
        'base_title': '子夜歌十八首',
    },
}

# Volume 801: Custom splits for multi-part poems (marker-based)
VOLUME_801_CUSTOM_SPLITS = {
    ('宛轉歌二首', '郎大家宋氏'): {
        'markers': [
            '日已暮，',  # Part 2
        ],
        'base_title': '宛轉歌二首',
    },
    ('春詞二首', '張琰'): {
        'markers': [
            '昨日桃花飛，',  # Part 2
        ],
        'base_title': '春詞二首',
    },
}

# Volume 804: Custom splits for multi-part poems (marker-based)
VOLUME_804_CUSTOM_SPLITS = {
    ('和新及第悼亡詩二首', '魚玄機'): {
        'markers': [
            '一枝月桂和煙秀，',  # Part 2
        ],
        'base_title': '和新及第悼亡詩二首',
    },
}

# Volume 806: Custom splits for multi-part poems (marker-based)
VOLUME_806_CUSTOM_SPLITS = {
    ('拾遺二首新添', '寒山'): {
        'markers': [
            '家有寒山詩，',  # Part 2
        ],
        'base_title': '拾遺二首新添',
    },
    ('三字詩六首', '寒山'): {
        'markers': [
            '寒山寒，',  # Part 2
            '我居山，',  # Part 3
            '寒山深，',  # Part 4
            '重巖中，',  # Part 5
            '寒山子，',  # Part 6
        ],
        'base_title': '三字詩六首',
    },
    ('詩三百三首', '寒山'): {
        'markers': [
            '重巖我卜居，',  # Part 2
            '可笑寒山道，',  # Part 3
            '吾家好隱淪，',  # Part 4
            '琴書須自隨，',  # Part 5
            '弟兄同五郡，',  # Part 6
            '一為書劍客，',  # Part 7
            '莊子說送終，',  # Part 8
            '人問寒山道，',  # Part 9
            '天生百尺樹，',  # Part 10
            '驅馬度荒城，',  # Part 11
            '鸚鵡宅西國，',  # Part 12
            '玉堂掛珠簾，',  # Part 13
            '城中娥眉女，',  # Part 14
            '父母續經多，',  # Part 15
            '家住綠岩下，',  # Part 16
            '四時無止息，',  # Part 17
            '歲去換愁年，',  # Part 18
            '手筆太縱橫，',  # Part 19
            '欲得安身處，',  # Part 20
            '俊傑馬上郎，',  # Part 21
            '有一餐霞子，',  # Part 22
            '妾在邯鄲住，',  # Part 23
            '快搒三翼舟，',  # Part 24
            '智者君拋我，',  # Part 25
            '有鳥五色彣，',  # Part 26
            '茅棟野人居，',  # Part 27
            '登陟寒山道，',  # Part 28
            '六極常嬰困，',  # Part 29
            '白雲高嵯峨，',  # Part 30
            '杳杳寒山道，',  # Part 31
            '少年何所愁，',  # Part 32
            '聞道愁難遣，',  # Part 33
            '兩龜乘犢車，',  # Part 34
            '三月蠶猶小，',  # Part 35
            '東家一老婆，',  # Part 36
            '富兒多鞅掌，',  # Part 37
            '余曾昔睹聰明士，',  # Part 38
            '白鶴銜苦桃，',  # Part 39
            '慣居幽隱處，',  # Part 40
            '生前大愚癡，',  # Part 41
            '璨璨盧家女，',  # Part 42
            '低眼鄒公妻，',  # Part 43
            '獨臥重岩下，',  # Part 44
            '夫物有所用，',  # Part 45
            '誰家長不死，',  # Part 46
            '騮馬珊瑚鞭，',  # Part 47
            '竟日常如醉，',  # Part 48
            '一向寒山坐，',  # Part 49
            '相喚采芙蓉，',  # Part 50
            '吾心似秋月，',  # Part 51
            '垂柳暗如煙，',  # Part 52
            '有酒相招飲，',  # Part 53
            '可憐好丈夫，',  # Part 54
            '桃花欲經夏，',  # Part 55
            '我見東家女，',  # Part 56
            '田舍多桑園，',  # Part 57
            '我見百十狗，',  # Part 58
            '極目兮長望，',  # Part 59
            '洛陽多女兒，',  # Part 60
            '春女衒容儀，',  # Part 61
            '群女戲夕陽，',  # Part 62
            '若人逢鬼魅，',  # Part 63
            '浩浩黃河水，',  # Part 64
            '乘茲朽木船，',  # Part 65
            '默默永無言，',  # Part 66
            '山中何太冷，',  # Part 67
            '山客心悄悄，',  # Part 68
            '有人兮山楹，',  # Part 69
            '豬喫死人肉，',  # Part 70
            '快哉混沌身，',  # Part 71
            '啼哭緣何事，',  # Part 72
            '婦女慵經織，',  # Part 73
            '不行真正道，',  # Part 74
            '世有一等愚，',  # Part 75
            '有漢姓傲慢，',  # Part 76
            '縱你居犀角，',  # Part 77
            '卜擇幽居地，',  # Part 78
            '益者益其精，',  # Part 79
            '徒勞說三史，',  # Part 80
            '碧澗泉水清，',  # Part 81
            '我今有一襦，',  # Part 82
            '白拂栴檀柄，',  # Part 83
            '貪愛有人求快活，',  # Part 84
            '多少般數人，',  # Part 85
            '貪人好聚財，',  # Part 86
            '去家一萬里，',  # Part 87
            '瞋是心中火，',  # Part 88
            '汝為埋頭癡兀兀，',  # Part 89
            '惡趣甚茫茫，',  # Part 90
            '世有多解人，',  # Part 91
            '天高高不窮，',  # Part 92
            '天下幾種人，',  # Part 93
            '賢士不貪婪，',  # Part 94
            '嗊嗊買魚肉，',  # Part 95
            '有人把椿樹，',  # Part 96
            '蒸砂擬作飯，',  # Part 97
            '推尋世間事，',  # Part 98
            '蹭蹬諸貧士，',  # Part 99
            '欲識生死譬，',  # Part 100
            '尋思少年日，',  # Part 101
            '偃息深林下，',  # Part 102
            '不須攻人惡，',  # Part 103
            '富兒會高堂，',  # Part 104
            '世有聰明士，',  # Part 105
            '層層山水秀，',  # Part 106
            '滿卷才子詩，',  # Part 107
            '施家有兩兒，',  # Part 108
            '止宿鴛鴦鳥，',  # Part 109
            '或有衒行人，',  # Part 110
            '少小帶經鋤，',  # Part 111
            '變化計無窮，',  # Part 112
            '書判全非弱，',  # Part 113
            '貧驢欠一尺，',  # Part 114
            '柳郎八十二，',  # Part 115
            '大有饑寒客，',  # Part 116
            '赫赫誰𤮧肆，',  # Part 117
            '吁嗟濁濫處，',  # Part 118
            '田家避暑月，',  # Part 119
            '箇是何措大，',  # Part 120
            '為人常喫用，',  # Part 121
            '浪造淩霄閣，',  # Part 122
            '雲山疊疊連天碧，',  # Part 123
            '富貴疏親聚，',  # Part 124
            '我見一癡漢，',  # Part 125
            '新穀尚未熟，',  # Part 126
            '大有好笑事，',  # Part 127
            '老翁娶少婦，',  # Part 128
            '雍容美少年，',  # Part 129
            '鳥語情不堪，',  # Part 130
            '昨日何悠悠，',  # Part 131
            '丈夫莫守困，',  # Part 132
            '之子何惶惶，',  # Part 133
            '昨夜夢還家，',  # Part 134
            '人生不滿百，',  # Part 135
            '世有一等流，',  # Part 136
            '董郎年少時，',  # Part 137
            '個是誰家子，',  # Part 138
            '人以身為本，',  # Part 139
            '城北仲家翁，',  # Part 140
            '下愚讀我詩，',  # Part 141
            '自有慳惜人，',  # Part 142
            '我行經古墳，',  # Part 143
            '夕陽赫西山，',  # Part 144
            '出身既擾擾，',  # Part 145
            '有樂且須樂，',  # Part 146
            '獨坐常忽忽，',  # Part 147
            '一人好頭肚，',  # Part 148
            '他賢君即受，',  # Part 149
            '俗薄真成薄，',  # Part 150
            '是我有錢日，',  # Part 151
            '人生一百年，',  # Part 152
            '教汝數般事，',  # Part 153
            '寒山多幽奇，',  # Part 154
            '有樹先林生，',  # Part 155
            '寒山有躶蟲，',  # Part 156
            '有人畏白首，',  # Part 157
            '昔時可哥貧，',  # Part 158
            '我見世間人，',  # Part 159
            '可貴天然物，',  # Part 160
            '餘家有一窟，',  # Part 161
            '男兒大丈夫，',  # Part 162
            '粵自居寒山，',  # Part 163
            '可重是寒山，',  # Part 164
            '閒自訪高僧，',  # Part 165
            '閒遊華頂上，',  # Part 166
            '世有多事人，',  # Part 167
            '寒山有一宅，',  # Part 168
            '儂家暫下山，',  # Part 169
            '一自遯寒山，',  # Part 170
            '我見世間人，',  # Part 171
            '自聞梁朝日，',  # Part 172
            '吁嗟貧複病，',  # Part 173
            '養女畏太多，',  # Part 174
            '秉志不可卷，',  # Part 175
            '以我棲遲處，',  # Part 176
            '憶昔遇逢處，',  # Part 177
            '報汝修道者，',  # Part 178
            '去年春鳥鳴，',  # Part 179
            '多少天臺人，',  # Part 180
            '一住寒山萬事休，',  # Part 181
            '可惜百年屋，',  # Part 182
            '精神殊爽爽，',  # Part 183
            '笑我田舍兒，',  # Part 184
            '買肉血𣽅𣽅，',  # Part 185
            '客難寒山子，',  # Part 186
            '從生不往來，',  # Part 187
            '一瓶鑄金成，',  # Part 188
            '摧殘荒草廬，',  # Part 189
            '有身與無身，',  # Part 190
            '昨見河邊樹，',  # Part 191
            '余見僧繇性希奇，',  # Part 192
            '久住寒山凡幾秋，',  # Part 193
            '丹丘迥聳與雲齊，',  # Part 194
            '千生萬死凡幾生，',  # Part 195
            '老病殘年百有餘，',  # Part 196
            '世間何事最堪嗟，',  # Part 197
            '昔年曾到大海遊，',  # Part 198
            '眾星羅列夜明深，',  # Part 199
            '千年石上古人蹤，',  # Part 200
            '寒山頂上月輪孤，',  # Part 201
            '我向前溪照碧流，',  # Part 202
            '我家本住在寒山，',  # Part 203
            '世人何事可籲嗟，',  # Part 204
            '余家本住在天臺，',  # Part 205
            '憐底眾生病，',  # Part 206
            '讀書豈免死，',  # Part 207
            '我見瞞人漢，',  # Part 208
            '不見朝垂露，',  # Part 209
            '水清澄澄瑩，',  # Part 210
            '自從到此天臺境，',  # Part 211
            '說食終不飽，',  # Part 212
            '可畏輪回苦，',  # Part 213
            '可畏三界輪，',  # Part 214
            '昨日遊峰頂，',  # Part 215
            '自古多少聖，',  # Part 216
            '我聞天台山，',  # Part 217
            '養子不經師，',  # Part 218
            '徒閉蓬門坐，',  # Part 219
            '時人見寒山，',  # Part 220
            '自在白雲閑，',  # Part 221
            '我在村中住，',  # Part 222
            '死生元有命，',  # Part 223
            '國以人為本，',  # Part 224
            '眾生不可說，',  # Part 225
            '自樂平生道，',  # Part 226
            '大海水無邊，',  # Part 227
            '自見天台頂，',  # Part 228
            '三五癡後生，',  # Part 229
            '心高如山嶽，',  # Part 230
            '如許多寶貝，',  # Part 231
            '我見凡愚人，',  # Part 232
            '勸你三界子，',  # Part 233
            '三界人蠢蠢，',  # Part 234
            '人生在塵蒙，',  # Part 235
            '寒山出此語，',  # Part 236
            '我見多知漢，',  # Part 237
            '寄語諸仁者，',  # Part 238
            '世有一般人，',  # Part 239
            '常聞釋迦佛，',  # Part 240
            '常聞國大臣，',  # Part 241
            '上人心猛利，',  # Part 242
            '我有六兄弟，',  # Part 243
            '昔日極貧苦，',  # Part 244
            '一生慵懶作，',  # Part 245
            '我見出家人，',  # Part 246
            '昨到雲霞觀，',  # Part 247
            '余家有一宅，',  # Part 248
            '傳語諸公子，',  # Part 249
            '何以長惆悵，',  # Part 250
            '繿縷關前業，',  # Part 251
            '我見黃河水，',  # Part 252
            '二儀既開闢，',  # Part 253
            '余勸諸稚子，',  # Part 254
            '可歎浮生人，',  # Part 255
            '時人尋雲路，',  # Part 256
            '寒山棲隱處，',  # Part 257
            '五嶽俱成粉，',  # Part 258
            '無衣自訪覓，',  # Part 259
            '自羨山間樂，',  # Part 260
            '我見轉輪王，',  # Part 261
            '平野水寬闊，',  # Part 262
            '可貴一名山，',  # Part 263
            '我見世間人，',  # Part 264
            '迥聳霄漢外，',  # Part 265
            '盤陁石上坐，',  # Part 266
            '隱士遁人間，',  # Part 267
            '寄語食肉漢，',  # Part 268
            '自從出家後，',  # Part 269
            '五言五百篇，',  # Part 270
            '世事繞悠悠，',  # Part 271
            '可笑五陰窟，',  # Part 272
            '常聞漢武帝，',  # Part 273
            '憶得二十年，',  # Part 274
            '語你出家輩，',  # Part 275
            '寒巖深更好，',  # Part 276
            '岩前獨靜坐，',  # Part 277
            '本志慕道倫，',  # Part 278
            '元非隱逸士，',  # Part 279
            '自古諸哲人，',  # Part 280
            '今日巖前坐，',  # Part 281 (not '岩前獨靜坐' which is Part 277)
            '千雲萬水間，',  # Part 282
            '勸你休去來，',  # Part 283
            '世間一等流，',  # Part 284
            '高高峰頂上，',  # Part 285
            '有箇王秀才，',  # Part 286
            '我住在村鄉，',  # Part 287
            '寒山出此語，',  # Part 288
            '我見人轉經，',  # Part 289
            '寒山唯白雲，',  # Part 290
            '鹿生深林中，',  # Part 291
            '花上黃鶯子，',  # Part 292
            '棲遲寒岩下，',  # Part 293
            '昔日經行處，',  # Part 294
            '欲向東岩去，',  # Part 295
            '我見利智人，',  # Part 296
            '身著空花衣，',  # Part 297
            '君看葉裏花，',  # Part 298
            '畫棟非吾宅，',  # Part 299
            '出生三十年，',  # Part 300
            '寒山無漏岩，',  # Part 301
            '沙門不持戒，',  # Part 302
            '有人笑我詩，',  # Part 303
        ],
        'base_title': '詩三百三首',
    },
}

# Volume 820: Custom splits for 皎然's multi-part poems (marker-based)
VOLUME_820_CUSTOM_SPLITS = {
    ('雜興六首', '皎然'): {
        'markers': [
            '短齡役長世，擾擾悟不早。',  # Part 2
            '誰高齊公子，泣聽雍門琴。',  # Part 3
            '獨高庭中鶴，意遠貴氛埃。',  # Part 4
            '白雲琅玕色，一片生虛無。',  # Part 5
            '疏散遂吾性，棲山更無機。',  # Part 6
        ],
        'base_title': '雜興六首',
    },
    ('偶然五首', '皎然'): {
        'markers': [
            '偶然寂無喧，吾了心性源。',  # Part 2
            '隱心不隱跡，卻欲住人寰。',  # Part 3
            '虜語嫌不學，胡音從不翻。',  # Part 4
            '真隱須無矯，忘名要似愚。',  # Part 5
        ],
        'base_title': '偶然五首',
    },
}

# Volume 826: Custom splits for 貫休's multi-part poems (marker-based)
VOLUME_826_CUSTOM_SPLITS = {
    ('偶作二首', '貫休'): {
        'markers': [
            '門前數枝路，路路車馬鳴。',  # Part 2
        ],
        'base_title': '偶作二首',
    },
    ('春晚書山家屋壁二首', '貫休'): {
        'markers': [
            '水香塘黑蒲森森，鴛鴦鸂鶒如家禽。',  # Part 2
        ],
        'base_title': '春晚書山家屋壁二首',
    },
    ('戰城南二首', '貫休'): {
        'markers': [
            '磧中有陰兵，戰馬時驚蹶。',  # Part 2
        ],
        'base_title': '戰城南二首',
    },
    ('夢遊仙四首', '貫休'): {
        'markers': [
            '三四仙女兒，身著瑟瑟衣。',  # Part 2
            '車渠地無塵，行至瑤池濱。',  # Part 3
            '宮殿崢嶸籠紫氣，金渠玉砂五色水。',  # Part 4
        ],
        'base_title': '夢遊仙四首',
    },
    ('輕薄篇二首', '貫休'): {
        'markers': [
            '木落蕭蕭，蟲鳴唧唧。',  # Part 2
        ],
        'base_title': '輕薄篇二首',
    },
    ('富貴曲二首', '貫休'): {
        'markers': [
            '如神若仙，似蘭同雪。',  # Part 2
        ],
        'base_title': '富貴曲二首',
    },
    ('古意九首', '貫休'): {
        'markers': [
            '陽烏爍萬物，草木懷春恩。',  # Part 2
            '美人如游龍，被服金鴛鴦。',  # Part 3
            '乾坤有清氣，散入詩人脾。',  # Part 4
            '莫輕白雲白，不與風雨會。',  # Part 5
            '古交如真金，百煉色不回。',  # Part 6
            '常思謝康樂，文章有神力。',  # Part 7
            '常思李太白，仙筆驅造化。',  # Part 8
            '憶在山中時，丹桂花葳蕤。',  # Part 9
        ],
        'base_title': '古意九首',
    },
    ('擬齊梁酬所知見贈二首', '貫休'): {
        'markers': [
            '美如仙鼎金，清如纖手琴。',  # Part 2
        ],
        'base_title': '擬齊梁酬所知見贈二首',
    },
}

# Volume 827: Custom splits for 貫休's multi-part poems (marker-based)
VOLUME_827_CUSTOM_SPLITS = {
    ('閒居擬齊梁四首', '貫休'): {
        'markers': [
            '果熟無低枝，芳香入屏帷。',  # Part 2
            '紅藕映嘉魴，澄池照孤坐。',  # Part 3
            '清氣生滄洲，殘雲落林藪。',  # Part 4
        ],
        'base_title': '閒居擬齊梁四首',
    },
    ('塞上曲二首', '貫休'): {
        'markers': [
            '去年轉鬬陰山腳，生得單于卻放卻。',  # Part 2
        ],
        'base_title': '塞上曲二首',
    },
    ('擬齊梁體寄馮使君三首', '貫休'): {
        'markers': [
            '露益蟬聲長，蕙蘭垂紫帶。',  # Part 2
            '大道貴無心，聖賢為始慕。',  # Part 3
        ],
        'base_title': '擬齊梁體寄馮使君三首',
    },
    ('冬末病中作二首', '貫休'): {
        'markers': [
            '胸中有一物，旅拒復攻擊。',  # Part 2
        ],
        'base_title': '冬末病中作二首',
    },
    ('書陳處士屋壁二首', '貫休'): {
        'markers': [
            '高步前山前，高歌北山北。',  # Part 2
        ],
        'base_title': '書陳處士屋壁二首',
    },
    ('擬君子有所思二首', '貫休'): {
        'markers': [
            '君不見沈約道，佳人不在茲，春光為誰惜。',  # Part 2
        ],
        'base_title': '擬君子有所思二首',
    },
    ('古塞下曲四首', '貫休'): {
        'markers': [
            '戰骨踐成塵，飛入征人目。',  # Part 2
            '日向平沙出，還向平沙沒。',  # Part 3
            '狼煙在陣雲，匈奴愛輕敵。',  # Part 4
        ],
        'base_title': '古塞下曲四首',
    },
    ('邊上作三首', '貫休'): {
        'markers': [
            '陣雲忽向沙中起，探得胡兵過遼水。',  # Part 2
            '見說青塚穴，中有白野狐。',  # Part 3
        ],
        'base_title': '邊上作三首',
    },
}

# Volume 830: Custom splits for 貫休's multi-part poems (marker-based)
VOLUME_830_CUSTOM_SPLITS = {
    ('桐江閒居作十二首', '貫休'): {
        'markers': [
            '香剎通真觀，',  # Part 2
            '靜室焚檀印，',  # Part 3
            '不問賡桑子，',  # Part 4
            '詩琢冰成句，',  # Part 5
            '紅黍飯溪苔，',  # Part 6
            '蟬急野蕭蕭，',  # Part 7
            '露滴滴蘅茅，',  # Part 8
            '塹鳥毛衣別，',  # Part 9
            '芙蓉峰裏居，',  # Part 10
            '憶在山中日，',  # Part 11
            '囊非撲滿器，',  # Part 12
        ],
        'base_title': '桐江閒居作十二首',
    },
}

# Volume 835: Custom splits for 貫休's multi-part poems (marker-based)
VOLUME_835_CUSTOM_SPLITS = {
    ('大蜀皇帝潛龍日述聖德詩五首', '貫休'): {
        'markers': [
            '扶持社稷似齊桓，',  # Part 2
            '珠履三千侍玉除，',  # Part 3
            '紫髯青眼代天才，',  # Part 4
            '丈夫勳業正乾坤，',  # Part 5
        ],
        'base_title': '大蜀皇帝潛龍日述聖德詩五首',
    },
}

# Volume 842: Custom splits for 齊己's multi-part poems (marker-based)
VOLUME_842_CUSTOM_SPLITS = {
    ('渚宮莫問詩一十五首', '齊己'): {
        'markers': [
            '莫問伊嵇懶，',  # Part 2
            '莫問休行腳，',  # Part 3
            '莫問孱愚格，',  # Part 4
            '莫問無求意，',  # Part 5
            '莫問閑行趣，',  # Part 6
            '莫問真消息，',  # Part 7
            '莫問休持缽，',  # Part 8
            '莫問依劉跡，',  # Part 9
            '莫問無機性，',  # Part 10
            '莫問關門意，',  # Part 11
            '莫問□□□，',  # Part 12
            '莫問多山興，',  # Part 13
            '莫問衰殘質，',  # Part 14
            '莫問野騰騰，',  # Part 15
        ],
        'base_title': '渚宮莫問詩一十五首',
    },
}

# Volume 861: Custom splits for multi-part poems (marker-based)
VOLUME_861_CUSTOM_SPLITS = {
    ('又詩二首', '馬湘'): {
        'markers': [
            '何用燒丹學駐顏，',  # Part 2
        ],
        'base_title': '又詩二首',
    },
}

# Volume 862: Custom splits for multi-part poems (marker-based)
VOLUME_862_CUSTOM_SPLITS = {
    ('授炙轂子歌二首', '希道'): {
        'markers': [
            '魄微入魂牝牡結，',  # Part 2
        ],
        'base_title': '授炙轂子歌二首',
    },
}

# Volume 865: Custom splits for multi-part poems (marker-based)
VOLUME_865_CUSTOM_SPLITS = {
    ('詩二首', '虎丘山石壁鬼'): {
        'markers': [
            '神仙不可學，',  # Part 2
        ],
        'base_title': '詩二首',
    },
}

# Volume 807: Custom splits for multi-part poems (marker-based)
VOLUME_807_CUSTOM_SPLITS = {
    ('詩 其一', '拾得'): {
        'markers': [
            '嗟見世間人，個個愛吃肉。',  # Part 2
            '出家要清閒，清閒即為貴。',  # Part 3
            '養兒與娶妻，養女求媒娉。',  # Part 4
            '得此分段身，可笑好形質。',  # Part 5
            '佛哀三界子，總是親男女。',  # Part 6
            '佛舍尊榮樂，為湣諸癡子。',  # Part 7
            '嗟見世間人，永劫在迷津。',  # Part 8
            '我詩也是詩，有人喚作偈。',  # Part 9
            '有偈有千萬，卒急述應難。',  # Part 10
            '世間億萬人，面孔不相似。',  # Part 11
            '男女為婚嫁，俗務是常儀。',  # Part 12
            '世上一種人，出性常多事。',  # Part 13
            '我勸出家輩，須知教法深。',  # Part 14
            '寒山住寒山，拾得自拾得。',  # Part 15
            '從來是拾得，不是偶然稱。',  # Part 16
            '若解捉老鼠，不在五白貓。',  # Part 17
            '運心常寬廣，此則名為布。',  # Part 18
            '獼猴尚教得，人何不憤發。',  # Part 19
            '自從到此天臺寺，經今早已幾冬春。',  # Part 20
            '君不見，三界之中紛擾擾，只為無明不了絕。',  # Part 21
            '故林又斬新，剡源溪上人。',  # Part 22
            '自笑老夫筋力敗，偏戀松巖愛獨遊。',  # Part 23
            '一入雙溪不計春，煉暴黃精幾許斤。',  # Part 24
            '躑躅一群羊，沿山又入穀。',  # Part 25
            '銀星釘稱衡，綠絲作稱紐。',  # Part 26
            '閉門私造罪，准擬免災殃。',  # Part 27
            '悠悠塵裏人，常道塵中樂。',  # Part 28
            '無去無來本湛然，不居內外及中間。',  # Part 29
            '少年學書劍，叱馭到荊州。',  # Part 30
            '三界如轉輪，浮生若流水。',  # Part 31
            '閒入天台洞，訪人人不知。',  # Part 32
            '古佛路淒淒，愚人到卻迷。',  # Part 33
            '各有天真佛，號之為寶王。',  # Part 34
            '出家求出離，哀念苦眾生。',  # Part 35
            '常飲三毒酒，昏昏都不知。',  # Part 36
            '雲山疊疊幾千重，幽谷路深絕人蹤。',  # Part 37
            '後來出家子，論情入骨癡。',  # Part 38
            '若論常快活，唯有隱居人。',  # Part 39
            '我見出家人，總愛吃酒肉。',  # Part 40
            '我見頑鈍人，燈心柱須彌。',  # Part 41
            '若見月光明，照燭四天下。',  # Part 42
            '余住無方所，盤泊無為理。',  # Part 43
            '左手握驪珠，右手執慧劍。',  # Part 44
            '般若酒泠泠，飲多人易醒。',  # Part 45
            '平生何所憂，此世隨緣過。',  # Part 46
            '嗟見多知漢，終日枉用心。',  # Part 47
            '迢迢山徑峻，萬仞險隘危。',  # Part 48
            '松月冷颼颼，片片雲霞起。',  # Part 49
            '世有多解人，愚癡學閑文。',  # Part 50
            '人生浮世中，個個願富貴。',  # Part 51
            '水浸泥彈丸，思量無道理。',  # Part 52
            '雲林最幽棲，傍澗枕月溪。',  # Part 53
            '可笑是林泉，數裏少人煙。',  # Part 54
        ],
        'base_title': '詩',
    },
    ('壁上詩二首', '豐干'): {
        'markers': [
            '本來無一物，亦無塵可拂。',  # Part 2
        ],
        'base_title': '壁上詩二首',
    },
}

# Volume 740: Custom splits for 句 (fragments) entries - each line is a separate verse
VOLUME_740_CUSTOM_SPLITS = {
    # 孟賓于's 句 entries - each line is a separate couplet
    ('句 其一', '孟賓於'): {
        'splits': [
            (0, 1),  # 遠樹連沙靜，閑舟入浦遲。
            (1, 2),  # 簾垂群吏散，苔長訟庭閑。
            (2, 3),  # 去年曾折處，今日又垂條。
        ],
        'base_title': '句',
    },
    ('句 其二', '孟賓於'): {
        'splits': [
            (0, 1),   # 早知落處隨疎雨，悔得開時順暖風。
            (1, 2),   # 千家簾幕春空在，幾處樓臺月自明。
            (2, 3),   # 臘雪化為流水去，春風吹出好山來。
            (3, 4),   # 昔日聲塵喧洛下，近年詩句滿江南。
            (4, 5),   # 匝地人家憑檻見，遠山秋色捲簾看。
            (5, 6),   # 蟾宮空手下，澤國更誰來。
            (6, 7),   # 水國二親應探榜，龍門三月又傷春。
            (7, 8),   # 仙鳥卻回空說夢，清朝未達自嫌身。
            (8, 9),   # 失意從他桃李春，嵩陽經過歇行塵。
            (9, 10),  # 雲僧不見城中事，問是今年第幾人。
            (10, 11), # 因逢日者教重應，忍被雲僧勸卻歸。
        ],
        'base_title': '句',
    },
    # 左偃's 句 entry - each line has a source note
    ('句', '左偃'): {
        'splits': [
            (0, 1),  # 胡笳聞欲死，漢月望還生。 (《昭君怨》)
            (1, 2),  # 日華離碧海，雲影散青霄。 (《早日》)
        ],
        'base_title': '句',
    },
}

# Volume 741: Custom splits for 句 (fragments) entries - each line is a separate verse
VOLUME_741_CUSTOM_SPLITS = {
    # 劉洞's 句 entry - each line is a separate couplet
    ('句 其一', '劉洞'): {
        'splits': [
            (0, 1),  # 千里長江皆渡馬，十年養士得何人。
            (1, 2),  # 翻憶潘郎章奏內，愔愔日暮好沾巾。
            (2, 3),  # 百骸同草木，萬象入心靈。
        ],
        'base_title': '句',
    },
    # 江為's 句 entry - each line is a separate couplet
    ('句 其一', '江為'): {
        'splits': [
            (0, 1),  # 吟登蕭寺旃檀閣，醉倚王家玳瑁筵。
            (1, 2),  # 遠遠朝宗出白雲，方圓隨處性長存。
        ],
        'base_title': '句',
    },
}

# Volume 458: Custom splits for poems that need special handling
VOLUME_458_CUSTOM_SPLITS = {
    ('開成大行皇帝輓歌詞四首，奉敕撰進', '白居易'): {
        'markers': [
            '晏駕辭雙闕，',  # Part 2
            '嚴恭七月禮，',  # Part 3
            '化成同軌表清平，',  # Part 4
        ],
        'base_title': '開成大行皇帝輓歌詞四首，奉敕撰進',
    },
    ('病中詩十五首：病中五絕句', '白居易'): {
        'splits': [
            (0, 2),  # Part 1: 世間生老病相隨，此事心中久自知。今日行年將七十，猶須慚愧病來遲。
            (2, 4),  # Part 2: 方寸成灰鬢作絲，假如強健亦何為。家無憂累身無事，正是安閒好病時。
            (4, 6),  # Part 3: 李君墓上松應拱，元相池頭竹盡枯。多幸樂天今始病，不知合要苦治無。
            (6, 8),  # Part 4: 目昏思寢即安眠，足軟妨行便坐禪。身作醫王心是藥，不勞和扁到門前。
            (8, 10), # Part 5: 交親不要苦相憂，亦擬時時強出遊。但有心情何用腳，陸乘肩輿水乘舟。
        ],
        'base_title': '病中詩十五首：病中五絕句',  # Will become 病中詩十五首：病中五絕句 其一, 其二, etc.
    },
}

# Volume 458: Named part sets that need to be merged (share entry_index)
VOLUME_458_NAMED_PART_SETS = [
    {
        'base_title': '病中詩十五首',
        'author': '白居易',
        'expected_count': 15,
        # Note: Parts 4-8 are from the nested "病中五絕句" which gets custom-split first
        'part_patterns': ['初病風', '枕上作', '答閑上人來問因何風疾',
                         '病中五絕句 其一', '病中五絕句 其二', '病中五絕句 其三', '病中五絕句 其四', '病中五絕句 其五',
                         '送嵩客', '罷灸', '賣駱馬', '別柳枝', '就暖偶酌戲諸詩酒舊侶',
                         '歲暮呈思黯相公、皇甫朗之及夢得尚書', '自解'],
    },
]

# Volume 437: Custom splits for poems that need special handling
VOLUME_437_CUSTOM_SPLITS = {
    ('酬和元九東川路詩十二首：山枇杷花二首', '白居易'): {
        'splits': [
            (0, 2),  # Part 1: 萬重青嶂蜀門口，一樹紅花山頂頭。春盡憶家歸未得，低紅如解替君愁。
            (2, 4),  # Part 2: 葉如裙色碧綃淺，花似芙蓉紅粉輕。若使此花兼解語，推囚御史定違程。
        ],
        'base_title': '酬和元九東川路詩十二首：山枇杷花二首',
    },
    ('酬和元九東川路詩十二首：嘉陵夜有懷二首', '白居易'): {
        'splits': [
            (0, 2),  # Part 1: 露濕牆花春意深，西廊月上半床陰。憐君獨臥無言語，唯我知君此夜心。
            (2, 4),  # Part 2: 不明不暗朧朧月，不暖不寒慢慢風。獨臥空床好天氣，平明閒事到心中。
        ],
        'base_title': '酬和元九東川路詩十二首：嘉陵夜有懷二首',
    },
}

# Volume 437: Named part sets that need to be merged (share entry_index)
VOLUME_437_NAMED_PART_SETS = [
    {
        'base_title': '酬和元九東川路詩十二首',
        'author': '白居易',
        'expected_count': 12,
        # Note: Parts 3-4 are from "山枇杷花二首", parts 7-8 are from "嘉陵夜有懷二首"
        'part_patterns': ['駱口驛舊題詩', '南秦雪',
                         '山枇杷花二首 其一', '山枇杷花二首 其二',
                         '江樓月', '亞枝花', '江上笛',
                         '嘉陵夜有懷二首 其一', '嘉陵夜有懷二首 其二',
                         '夜深行', '望驛台', '江岸梨花'],
    },
]

# Volume 19: Custom splits for Yuefu poems (h2/h4 format)
# These poems use blank <p><br /></p> as separators in the HTML
VOLUME_19_CUSTOM_SPLITS = {
    ('相和歌辭·江南曲八首', '劉希夷'): {
        'splits': [
            (0, 5),    # Part 1: 暮宿南洲草...
            (5, 10),   # Part 2: 艷唱潮初落...
            (10, 15),  # Part 3: 君為隴西客...
            (15, 20),  # Part 4: 皓如楚江月...
            (20, 25),  # Part 5: 艤舟乘潮去...
            (25, 30),  # Part 6: 暮春三月晴...
            (30, 34),  # Part 7: 北堂紅草盛豐茸...
            (34, 38),  # Part 8: 憶昔江南年盛時...
        ],
        'base_title': '相和歌辭·江南曲八首',
    },
    ('相和歌辭·輓歌二首', '於鵠'): {
        'splits': [
            (0, 2),    # Part 1: 陰風吹黃蒿...
            (2, 4),    # Part 2: 見人切肺肝...
        ],
        'base_title': '相和歌辭·輓歌二首',
    },
    ('相和歌辭·對酒二首', '李白'): {
        'splits': [
            (0, 3),    # Part 1: 松子棲金華...
            (3, 7),    # Part 2: 勸君莫拒杯...
        ],
        'base_title': '相和歌辭·對酒二首',
    },
    ('相和歌辭·短歌行六首', '顧況'): {
        'splits': [
            (0, 4),    # Part 1: 城邊路...
            (4, 8),    # Part 2: 我欲升天天隔霄...
            (8, 10),   # Part 3: 新繫青絲百尺繩...
            (10, 12),  # Part 4: 何處春風吹曉幕...
            (12, 15),  # Part 5: 臨春風，聽春鳥...
            (15, 18),  # Part 6: 軒轅皇帝初得仙...
        ],
        'base_title': '相和歌辭·短歌行六首',
    },
    ('相和歌辭·短歌行二首', '白居易'): {
        'splits': [
            (0, 8),    # Part 1: 曈曈太陽如火色...
            (8, 15),   # Part 2: 世人求富貴...
        ],
        'base_title': '相和歌辭·短歌行二首',
    },
    ('相和歌辭·從軍行六首', '劉長卿'): {
        'splits': [
            (0, 2),    # Part 1: 回看虜騎合...
            (2, 4),    # Part 2: 落日更蕭條...
            (4, 6),    # Part 3: 草枯秋塞上...
            (6, 8),    # Part 4: 目極雁門道...
            (8, 10),   # Part 5: 倚劍白日暮...
            (10, 12),  # Part 6: 黃沙一萬里...
        ],
        'base_title': '相和歌辭·從軍行六首',
    },
    ('相和歌辭·從軍行五首', '令狐楚'): {
        'splits': [
            (0, 1),    # Part 1: 荒雞隔水啼...
            (1, 2),    # Part 2: 孤心眠夜雪...
            (2, 3),    # Part 3: 卻望冰河闊...
            (3, 4),    # Part 4: 胡風千里驚...
            (4, 5),    # Part 5: 暮雪連青海...
        ],
        'base_title': '相和歌辭·從軍行五首',
    },
    ('相和歌辭·苦哉行五首', '戎昱'): {
        'splits': [
            (0, 3),    # Part 1: 彼鼠侵我廚...
            (3, 6),    # Part 2: 官軍收洛陽...
            (6, 9),    # Part 3: 登樓望天衢...
            (9, 14),   # Part 4: 妾家青河邊...
            (14, 17),  # Part 5: 可汗奉親詔...
        ],
        'base_title': '相和歌辭·苦哉行五首',
    },
    ('相和歌辭·從軍行二首', '虞世南'): {
        'splits': [
            (0, 5),    # Part 1: 5 raw lines → 9 normalized
            (5, 9),    # Part 2: 4 raw lines → 8 normalized
        ],
        'base_title': '相和歌辭·從軍行二首',
    },
    ('相和歌辭·王昭君二首', '李白'): {
        'splits': [
            (0, 5),    # Part 1: 5 raw lines → 5 normalized
            (5, 6),    # Part 2: 1 raw line → 2 normalized
        ],
        'base_title': '相和歌辭·王昭君二首',
    },
    ('相和歌辭·從軍行二首', '李白'): {
        'splits': [
            (0, 2),    # Part 1: 2 raw lines → 4 normalized
            (2, 4),    # Part 2: 2 raw lines → 2 normalized
        ],
        'base_title': '相和歌辭·從軍行二首',
    },
    ('相和歌辭·從軍行三首', '王涯'): {
        'splits': [
            (0, 1),
            (1, 2),
            (2, 4),
        ],
        'base_title': '相和歌辭·從軍行三首',
    },
}

# Volume 20: Custom splits for Yuefu poems
VOLUME_20_CUSTOM_SPLITS = {
    ('相和歌辭·後苦寒行二首', '杜甫'): {
        'splits': [
            (0, 3),    # Part 1: 南紀巫廬瘴不絕... (3 lines)
            (3, 6),    # Part 2: 晚來江門失大木... (3 lines)
        ],
        'base_title': '相和歌辭·後苦寒行二首',
    },
    ('相和歌辭·相逢行二首', '李白'): {
        'splits': [
            (0, 17),   # Part 1: 朝騎五花馬... (17 lines)
            (17, 19),  # Part 2: 相逢紅塵內... (2 lines)
        ],
        'base_title': '相和歌辭·相逢行二首',
    },
    ('相和歌辭·決絕詞三首', '元稹'): {
        'splits': [
            (0, 9),    # Part 1: 乍可為天上牽牛織女星... (9 lines)
            (9, 18),   # Part 2: 噫春冰之將泮... (9 lines)
            (18, 27),  # Part 3: 夜夜相抱眠... (9 lines)
        ],
        'base_title': '相和歌辭·決絕詞三首',
    },
}

# Volume 21: Custom splits for nested multi-part poem
# These run in preprocessing phase, before _merge_seasonal_sets
VOLUME_21_CUSTOM_SPLITS = {
    ('相和歌辭·子夜四時歌六首·春歌二首', '郭元振'): {
        'splits': [
            (0, 2),    # Part 1: 青樓含日光，綠池起風色...
            (2, 4),    # Part 2: 陌頭楊柳枝，已被春風吹...
        ],
        'base_title': '相和歌辭·子夜四時歌六首·春歌二首',
    },
    ('相和歌辭·子夜四時歌六首·秋歌二首', '郭元振'): {
        'splits': [
            (0, 2),    # Part 1: 邀歡空佇立，望美頻回顧...
            (2, 4),    # Part 2: 辟惡茱萸囊，延年菊花酒...
        ],
        'base_title': '相和歌辭·子夜四時歌六首·秋歌二首',
    },
    ('相和歌辭·子夜四時歌六首·冬歌二首', '郭元振'): {
        'splits': [
            (0, 2),    # Part 1: 北極嚴氣升，南至溫風謝...
            (2, 4),    # Part 2: 帷橫雙翡翠，被卷兩鴛鴦...
        ],
        'base_title': '相和歌辭·子夜四時歌六首·冬歌二首',
    },
}

# Volume 26: Custom splits for multi-part poems
VOLUME_26_CUSTOM_SPLITS = {
    ('雜曲歌辭·古別離二首', '於濆'): {
        'markers': [
            '郎本東家兒',    # Part 2
        ],
        'base_title': '雜曲歌辭·古別離二首',
    },
    ('雜曲歌辭·古別離二首', '李端'): {
        'markers': [
            '與君桂陽別',    # Part 2
        ],
        'base_title': '雜曲歌辭·古別離二首',
    },
    ('雜曲歌辭·古別離二首', '施肩吾'): {
        'markers': [
            '老母別愛子',    # Part 2
        ],
        'base_title': '雜曲歌辭·古別離二首',
    },
    ('雜曲歌辭·古離別二首', '孟郊'): {
        'markers': [
            '山川古今路',    # Part 2
        ],
        'base_title': '雜曲歌辭·古離別二首',
    },
    ('雜曲歌辭·長干行二首', '李白'): {
        'markers': [
            '憶妾深閨里',    # Part 2
        ],
        'base_title': '雜曲歌辭·長干行二首',
    },
    ('雜曲歌辭·秋夜曲二首', '王建'): {
        'markers': [
            '秋燈向壁掩洞房',    # Part 2
        ],
        'base_title': '雜曲歌辭·秋夜曲二首',
    },
}

# Volume 443: Custom splits for nested multi-part poem
VOLUME_443_CUSTOM_SPLITS = {
    ('奉和李大夫題新詩二首各六韻：因嚴亭', '白居易'): {
        'splits': [
            (0, 3),    # Part 1: 箕潁人窮獨... (3 lines)
            (3, 6),    # Part 2: 清景徒堪賞... (3 lines)
        ],
        'base_title': '奉和李大夫題新詩二首各六韻：因嚴亭',
    },
    ('奉和李大夫題新詩二首各六韻：忘筌亭', '白居易'): {
        'splits': [
            (0, 3),    # Part 1: 翠巘公門對... (3 lines)
            (3, 6),    # Part 2: 自笑滄江畔... (3 lines)
        ],
        'base_title': '奉和李大夫題新詩二首各六韻：忘筌亭',
    },
}

# Volume 443: Named part sets that need to be merged
VOLUME_443_NAMED_PART_SETS = [
    {
        'base_title': '奉和李大夫題新詩二首各六韻',
        'author': '白居易',
        'expected_count': 4,
        'part_patterns': ['因嚴亭 其一', '因嚴亭 其二',
                         '忘筌亭 其一', '忘筌亭 其二'],
    },
]

# Volume 450: Custom splits for nested multi-part poem
VOLUME_450_CUSTOM_SPLITS = {
    ('勸酒十四首：何處難忘酒七首', '白居易'): {
        'splits': [
            (0, 4),     # Part 1: 何處難忘酒，長安喜氣新... (4 lines)
            (4, 8),     # Part 2: 何處難忘酒，天涯話舊情... (4 lines)
            (8, 12),    # Part 3: 何處難忘酒，朱門羨少年... (4 lines)
            (12, 16),   # Part 4: 何處難忘酒，霜庭老病翁... (4 lines)
            (16, 20),   # Part 5: 何處難忘酒，軍功第一高... (4 lines)
            (20, 24),   # Part 6: 何處難忘酒，青門送別多... (4 lines)
            (24, 28),   # Part 7: 何處難忘酒，逐臣歸故園... (4 lines)
        ],
        'base_title': '勸酒十四首：何處難忘酒七首',
    },
    ('勸酒十四首：不如來飲酒七首', '白居易'): {
        'splits': [
            (0, 4),     # Part 1: 莫隱深山去，君應到自嫌... (4 lines)
            (4, 8),     # Part 2: 莫作農夫去，君應見自愁... (4 lines)
            (8, 12),    # Part 3: 莫作商人去，恓惶君未諳... (4 lines)
            (12, 16),   # Part 4: 莫事長征去，辛勤難具論... (4 lines)
            (16, 20),   # Part 5: 莫學長生去，仙方誤殺君... (4 lines)
            (20, 24),   # Part 6: 莫上青雲去，青雲足愛憎... (4 lines)
            (24, 28),   # Part 7: 莫入紅塵去，令人心力勞... (4 lines)
        ],
        'base_title': '勸酒十四首：不如來飲酒七首',
    },
}

# Volume 450: Named part sets that need to be merged
VOLUME_450_NAMED_PART_SETS = [
    {
        'base_title': '勸酒十四首',
        'author': '白居易',
        'expected_count': 14,
        'part_patterns': [
            '何處難忘酒七首 其一', '何處難忘酒七首 其二', '何處難忘酒七首 其三',
            '何處難忘酒七首 其四', '何處難忘酒七首 其五', '何處難忘酒七首 其六', '何處難忘酒七首 其七',
            '不如來飲酒七首 其一', '不如來飲酒七首 其二', '不如來飲酒七首 其三',
            '不如來飲酒七首 其四', '不如來飲酒七首 其五', '不如來飲酒七首 其六', '不如來飲酒七首 其七',
        ],
    },
]

# Volume 479: Named part sets that need to be merged
# 盛山十二詩 - Twelve Poems of Sheng Mountain by 韋處厚
VOLUME_479_NAMED_PART_SETS = [
    {
        'base_title': '盛山十二詩',
        'author': '韋處厚',
        'expected_count': 12,
        'part_patterns': [
            '隠月岫', '流桮渠', '竹巖', '繡衣石榻', '宿雲亭', '梅谿',
            '桃塢', '胡盧沼', '茶嶺', '盤石磴', '琵琶臺', '上士缾泉',
        ],
    },
]

# Volume 480: Named part sets that need to be merged
# Note: Scraper gives us 8 poems (not 10 - title says 十首 but only 8 exist)
#       The "（二首）" poems are pre-separated by scraper without 其一/其二 markers
VOLUME_480_NAMED_PART_SETS = [
    {
        'base_title': '壽陽罷郡日有詩十首，與追懷不殊，今編於後，兼紀瑞物',
        'author': '李紳',
        'expected_count': 8,  # Title says 十首 but only 8 poems exist
        'part_patterns': [
            '肥河維舟阻凍袛待勅命（二首）',  # First occurrence (no marker from scraper)
            '肥河維舟阻凍袛待勅命（二首）',  # Second occurrence (no marker from scraper)
            '別連理樹',
            '虎不食人',
            '發壽陽分司，勅到，又遇新正，感懷書事',
            '初出淝口入淮',
            '入淮至盱眙',
            '憶東湖',
        ],
    },
]

# Volume 343: Custom splits for nested multi-part poem
VOLUME_343_CUSTOM_SPLITS = {
    ('游城南十六首：楸樹二首', '韓愈'): {
        'splits': [
            (0, 2),    # Part 1: 楸樹二首 其一 (2 lines)
            (2, 4),    # Part 2: 楸樹二首 其二 (2 lines)
        ],
        'base_title': '游城南十六首：楸樹二首',
    },
}

# Volume 343: Named part sets that need to be merged
VOLUME_343_NAMED_PART_SETS = [
    {
        'base_title': '游城南十六首',
        'author': '韓愈',
        'expected_count': 16,
        'part_patterns': [
            '賽神',
            '題於賓客莊',
            '晚春',
            '落花',
            '楸樹二首 其一',
            '楸樹二首 其二',
            '風折花枝',
            '贈同遊',
            '贈張十八助教',
            '題韋氏莊',
            '晚雨',
            '出城',
            '把酒',
            '嘲少年',
            '楸樹',
            '遣興',
        ],
    },
]

# Volume 541: Named part sets that need to be merged (燕臺四首)
# The Four Poems on the Swallow Terrace by Li Shangyin - one set of 4 seasonal poems
# Summer and Winter were incorrectly auto-split into sub-parts, need to merge them first
VOLUME_541_NAMED_PART_SETS = [
    {
        'base_title': '燕臺四首·夏',
        'author': '李商隱',
        'expected_count': 4,
        'part_patterns': [
            '燕臺四首·夏 其一',
            '燕臺四首·夏 其二',
            '燕臺四首·夏 其三',
            '燕臺四首·夏 其四',
        ],
    },
    {
        'base_title': '燕臺四首·冬',
        'author': '李商隱',
        'expected_count': 4,
        'part_patterns': [
            '燕臺四首·冬 其一',
            '燕臺四首·冬 其二',
            '燕臺四首·冬 其三',
            '燕臺四首·冬 其四',
        ],
    },
    {
        'base_title': '燕臺四首',
        'author': '李商隱',
        'expected_count': 4,
        'part_patterns': [
            '燕臺四首·春',
            '燕臺四首·夏',
            '燕臺四首·秋',
            '燕臺四首·冬',
        ],
    },
]

# Volume 228: Custom splits for multi-part poems (marker-based)
VOLUME_228_CUSTOM_SPLITS = {
    ('傷春五首', '杜甫'): {
        'markers': [
            '鶯入新年語',     # Part 2
            '日月還相鬥',     # Part 3
            '再有朝廷亂',     # Part 4
            '聞說初東幸',     # Part 5
        ],
        'base_title': '傷春五首',
    },
}

# Volume 229: Custom splits for multi-part poems (marker-based)
VOLUME_229_CUSTOM_SPLITS = {
    ('西閣二首', '杜甫'): {
        'markers': ['懶心似江水'],  # Part 2
        'base_title': '西閣二首',
    },
    ('上白帝城二首', '杜甫'): {
        'markers': ['白帝空祠廟'],  # Part 2
        'base_title': '上白帝城二首',
    },
}

# Volume 230: Custom splits for multi-part poems (marker-based)
VOLUME_230_CUSTOM_SPLITS = {
    ('承聞河北諸道節度入朝歡喜口號絕句十二首', '杜甫'): {
        'markers': [
            '洶洶人寰',    # Part 2
            '社稷蒼生',    # Part 3
            '喧喧道路',    # Part 4
            '不道諸公',    # Part 5
            '鳴玉鏘金',    # Part 6
            '英雄見事',    # Part 7
            '抱病江天',    # Part 8
            '澶漫山東',    # Part 9
            '東逾遼水',    # Part 10
            '漁陽突騎',    # Part 11
            '李相將軍',    # Part 12
        ],
        'base_title': '承聞河北諸道節度入朝歡喜口號絕句十二首',
    },
    ('複愁十二首', '杜甫'): {
        'markers': [
            '野鶻翻窺',    # Part 2
            '釣艇收緡',    # Part 3
            '萬國尚防',    # Part 4
            '身覺省郎',    # Part 5
            '金絲鏤箭',    # Part 6
            '胡虜何曾',    # Part 7
            '貞觀銅牙',    # Part 8
            '今日翔麟',    # Part 9
            '任轉江淮',    # Part 10
            '江上亦秋',    # Part 11
            '每恨陶彭澤',  # Part 12
        ],
        'base_title': '複愁十二首',
    },
    ('解悶十二首', '杜甫'): {
        'markers': [
            '商胡離別',    # Part 2
            '一辭故國',    # Part 3
            '沈范早知',    # Part 4
            '李陵蘇武',    # Part 5
            '複憶襄陽',    # Part 6
            '陶冶性靈',    # Part 7
            '不見高人',    # Part 8
            '先帝貴妃',    # Part 9
            '憶過瀘戎',    # Part 10
            '翠瓜碧李',    # Part 11
            '側生野岸',    # Part 12
        ],
        'base_title': '解悶十二首',
    },
}

# Volume 312: Custom splits for 游爛柯山四首 (4-part sets by two authors)
# Note: Splits are applied to RAW scraped lines (8 lines) before normalization
# Each raw line may contain 1-2 sentences; normalization will split them
VOLUME_312_CUSTOM_SPLITS = {
    ('游爛柯山四首', '李幼卿'): {
        'splits': [
            (0, 2),    # Part 1: Raw lines 0-1 (拂霧理孤策...物象不可及)
            (2, 4),    # Part 2: Raw lines 2-3 (巨石何崔嵬...聖者開津梁)
            (4, 6),    # Part 3: Raw lines 4-5 (二仙自圍棋...笙鶴何時還)
            (6, 8),    # Part 4: Raw lines 6-7 (石室過雲外...作禮未及終)
        ],
        'base_title': '游爛柯山四首',
    },
    ('游爛柯山四首', '李深'): {
        'splits': [
            (0, 2),    # Part 1: Raw lines 0-1 (尋源路不迷...雙林春色上)
            (2, 4),    # Part 2: Raw lines 2-3 (嵌空橫洞天...真興得津梁)
            (4, 6),    # Part 3: Raw lines 4-5 (羽客無姓名...懷古正怡然)
            (6, 8),    # Part 4: Raw lines 6-7 (稽首期發蒙...鳴磬雨花香)
        ],
        'base_title': '游爛柯山四首',
    },
}

# Volume 226: No manual splits needed - format-change auto-splitter handles 二首 poems

# Volume 231: Custom splits for Du Fu multi-part poems (marker-based)
# Note: Title says 五首 but only 4 parts exist
VOLUME_231_CUSTOM_SPLITS = {
    ('九日五首', '杜甫'): {
        'markers': [
            '舊日重陽日',     # Part 2
            '舊與蘇司業',     # Part 3
            '故里樊川菊',     # Part 4
        ],
        'base_title': '九日五首',
    },
}

# Volume 233: Custom splits for Du Fu multi-part poems (marker-based)
VOLUME_233_CUSTOM_SPLITS = {
    ('千秋節有感二首', '杜甫'): {
        'markers': ['禦氣雲樓敞'],  # Part 2
        'base_title': '千秋節有感二首',
    },
    ('清明二首', '杜甫'): {
        'markers': ['此身飄泊苦西東'],  # Part 2
        'base_title': '清明二首',
    },
}

# Volume 297: Custom splits for multi-part poems
VOLUME_297_CUSTOM_SPLITS = {
    ('江南雜體二首', '王建'): {
        'markers': [
            '處處江草綠',    # Part 2
        ],
        'base_title': '江南雜體二首',
    },
}

# Volume 298: Custom splits for multi-part poems
VOLUME_298_CUSTOM_SPLITS = {
    ('白紵歌二首', '王建'): {
        'markers': [
            '館娃宮中春日暮',    # Part 2
        ],
        'base_title': '白紵歌二首',
    },
    ('秋夜曲二首', '王建'): {
        'markers': [
            '秋燈向壁掩洞房',    # Part 2
        ],
        'base_title': '秋夜曲二首',
    },
}

# Volume 299: Custom splits for multi-part poems
VOLUME_299_CUSTOM_SPLITS = {
    ('原上新居十三首', '王建'): {
        'markers': [
            '一家榆柳新',     # Part 2
            '長安無舊識',     # Part 3
            '雞鳴村舍遙',     # Part 4
            '春來梨棗盡',     # Part 5
            '自掃一間房',     # Part 6
            '擬作讀經人',     # Part 7
            '移家近住村',     # Part 8
            '和暖繞林行',     # Part 9
            '住處鐘鼓外',     # Part 10
            '近來年紀到',     # Part 11
            '懶更學諸餘',     # Part 12
            '住處去山近',     # Part 13
        ],
        'base_title': '原上新居十三首',
    },
}

# Volume 314: Custom splits for multi-part poems
VOLUME_314_CUSTOM_SPLITS = {
    ('步虛詞十九首', '韋渠牟'): {
        'markers': [
            '羽駕正翩翩',     # Part 2
            '上帝求仙使',     # Part 3
            '鸞鶴共裴回',     # Part 4
            '羽節忽排煙',     # Part 5
            '靜發降靈香',     # Part 6
            '幾度遊三洞',     # Part 7
            '上法杳無營',     # Part 8
            '羽衛一何鮮',     # Part 9
            '大道何年學',     # Part 10
            '獨自授金書',     # Part 11
            '道學已通神',     # Part 12
            '上界有黃房',     # Part 13
            '珠佩紫霞纓',     # Part 14
            '西海辭金母',     # Part 15
            '玉樹雜金花',     # Part 16
            '舞鳳淩天出',     # Part 17
            '紫府與玄洲',     # Part 18
            '轡鶴複驂鸞',     # Part 19
        ],
        'base_title': '步虛詞十九首',
    },
}

# Volume 326: Custom splits for multi-part poems
VOLUME_326_CUSTOM_SPLITS = {
    ('與沈十九拾遺同遊棲霞寺上方於亮上人院會宿二首', '權德輿'): {
        'markers': [
            '偶來人境外',    # Part 2
        ],
        'base_title': '與沈十九拾遺同遊棲霞寺上方於亮上人院會宿二首',
    },
}

# Volume 328: Custom splits for multi-part poems
VOLUME_328_CUSTOM_SPLITS = {
    ('雜言和常州李員外副使春日戲題十首', '權德輿'): {
        'markers': [
            '蘭橈畫舸轉花塘',    # Part 2
            '簷前曉色驚雙燕',    # Part 3
            '枕上覺',           # Part 4
            '閒庭無事',         # Part 5
            '江春好遊衍',       # Part 6
            '曙月漸到窗前',     # Part 7
            '露洗百花新',       # Part 8
            '雨歇風輕一院香',   # Part 9
            '春風半',           # Part 10
        ],
        'base_title': '雜言和常州李員外副使春日戲題十首',
    },
    ('渡江秋怨二首', '權德輿'): {
        'markers': [
            '渡秋江兮渺然',    # Part 2
        ],
        'base_title': '渡江秋怨二首',
    },
    ('玉台體十二首', '權德輿'): {
        'markers': [
            '嬋娟二八正嬌羞',    # Part 2
            '隱映羅衫薄',        # Part 3
            '知向遼東去',        # Part 4
            '樓上吹簫罷',        # Part 5
            '淚盡珊瑚枕',        # Part 6
            '君去期花時',        # Part 7
            '空閨滅燭後',        # Part 8
            '秋風一夜至',        # Part 9
            '獨自披衣坐',        # Part 10
            '昨夜裙帶解',        # Part 11
            '萬里行人至',        # Part 12
        ],
        'base_title': '玉台體十二首',
    },
}

# Volume 333: Custom splits for multi-part poems
VOLUME_333_CUSTOM_SPLITS = {
    ('春日奉獻聖壽無疆詞十首', '楊巨源'): {
        'markers': [
            '鴛鷺彤庭際',    # Part 2
            '雲陛臨黃道',    # Part 3
            '玉漏飄青瑣',    # Part 4
            '垂拱乾坤正',    # Part 5
            '代是文明晝',    # Part 6
            '睿德符玄化',    # Part 7
            '物象朝高殿',    # Part 8
            '日上蒼龍闕',    # Part 9
            '化洽生成遂',    # Part 10
        ],
        'base_title': '春日奉獻聖壽無疆詞十首',
    },
}

# Volume 337: Custom splits for multi-part poems
VOLUME_337_CUSTOM_SPLITS = {
    ('汴州亂二首', '韓愈'): {
        'markers': [
            '母從子走者為誰',    # Part 2
        ],
        'base_title': '汴州亂二首',
    },
}

# Volume 302: Custom splits for 宮詞一百首 (actually 102 poems) and 句
# 宮詞一百首 has 204 lines = 102 quatrains (2 lines each, title says 100 but actually 102)
_GONGCI_102_SPLITS = [(i*2, (i+1)*2) for i in range(102)]
VOLUME_302_CUSTOM_SPLITS = {
    ('宮詞一百首', '王建'): {
        'splits': _GONGCI_102_SPLITS,
        'base_title': '宮詞一百首',
    },
    ('句', '王建'): {
        # After normalization: 9 lines (6 poems + 3 annotation lines split out)
        # Lines 0,2,4,6,7,8 are poems; lines 1,3,5 are annotations
        'splits': [(0, 1), (2, 3), (4, 5), (6, 7), (7, 8), (8, 9)],
        'base_title': '句',
    },
}

# Volume 338: Custom splits for multi-part poems
VOLUME_338_CUSTOM_SPLITS = {
    ('河之水二首寄子侄老成', '韓愈'): {
        'markers': [
            '河之水，',    # Part 2 (second occurrence with comma)
        ],
        'base_title': '河之水二首寄子侄老成',
    },
    ('感春四首', '韓愈'): {
        'markers': [
            '皇天平分成四時',    # Part 2
            '朝騎一馬出',        # Part 3
            '我恨不如江頭人',    # Part 4
        ],
        'base_title': '感春四首',
    },
}

# Volume 340: Custom splits for multi-part poems
VOLUME_340_CUSTOM_SPLITS = {
    ('李花二首', '韓愈'): {
        'markers': [
            '當春天地爭奢華',    # Part 2
        ],
        'base_title': '李花二首',
    },
}

# Volume 341: Custom splits for multi-part poems
VOLUME_341_CUSTOM_SPLITS = {
    ('讀皇甫湜公安園池詩書其後二首', '韓愈'): {
        'markers': [
            '我有一池水',    # Part 2
        ],
        'base_title': '讀皇甫湜公安園池詩書其後二首',
    },
    ('贈別元十八協律六首', '韓愈'): {
        'markers': [
            '英英桂林伯',    # Part 2
            '吾友柳子厚',    # Part 3
            '勢要情所重',    # Part 4
            '讀書患不多',    # Part 5
            '寄書龍城守',    # Part 6
        ],
        'base_title': '贈別元十八協律六首',
    },
    ('宿曾江口示侄孫湘二首', '韓愈'): {
        'markers': [
            '舟行忘故道',    # Part 2
        ],
        'base_title': '宿曾江口示侄孫湘二首',
    },
}

# Volume 342: Custom splits for multi-part poems
VOLUME_342_CUSTOM_SPLITS = {
    ('感春三首', '韓愈'): {
        'markers': [
            '黃黃蕪菁花',    # Part 2
            '晨游百花林',    # Part 3
        ],
        'base_title': '感春三首',
    },
    ('雜詩四首', '韓愈'): {
        'markers': [
            '鵲鳴聲楂楂',    # Part 2
            '截橑為欂櫨',    # Part 3
            '雀鳴朝營食',    # Part 4
        ],
        'base_title': '雜詩四首',
    },
    ('南溪始泛三首', '韓愈'): {
        'markers': [
            '南溪亦清駛',    # Part 2
            '足弱不能步',    # Part 3
        ],
        'base_title': '南溪始泛三首',
    },
}

# Volume 346: Custom splits for multi-part poems
VOLUME_346_CUSTOM_SPLITS = {
    ('從軍詞三首', '王涯'): {
        'markers': [
            '燕頷多奇相',    # Part 2
            '旄頭夜落捷書飛',    # Part 3
        ],
        'base_title': '從軍詞三首',
    },
}

# Volume 352: Custom splits for multi-part poems (marker-based)
VOLUME_352_CUSTOM_SPLITS = {
    ('酬賈鵬山人郡內新栽松寓興見贈二首', '柳宗元'): {
        'markers': [
            '無能常閉閣，',  # Part 2
        ],
        'base_title': '酬賈鵬山人郡內新栽松寓興見贈二首',
    },
}

# Volume 354: Custom splits for multi-part poems
VOLUME_354_CUSTOM_SPLITS = {
    ('送春曲三首', '劉禹錫'): {
        'markers': [
            '春已暮',    # Part 2
            '春景去',    # Part 3
        ],
        'base_title': '送春曲三首',
    },
    ('初夏曲三首', '劉禹錫'): {
        'markers': [
            '時節過繁華',    # Part 2
            '綠水風初暖',    # Part 3
        ],
        'base_title': '初夏曲三首',
    },
    ('觀柘枝舞二首', '劉禹錫'): {
        'markers': [
            '山雞臨清鏡',    # Part 2
        ],
        'base_title': '觀柘枝舞二首',
    },
}

# Volume 355: Custom splits for multi-part poems
VOLUME_355_CUSTOM_SPLITS = {
    ('春日寄楊八唐州二首', '劉禹錫'): {
        'markers': [
            '漠漠淮上春',    # Part 2
        ],
        'base_title': '春日寄楊八唐州二首',
    },
}

# Volume 356: Custom splits for multi-part poems
VOLUME_356_CUSTOM_SPLITS = {
    ('平齊行二首', '劉禹錫'): {
        'markers': [
            '泰山沈寇六十年',    # Part 2
        ],
        'base_title': '平齊行二首',
    },
    ('兩如何詩謝裴令公贈別二首', '劉禹錫'): {
        'markers': [
            '一東一西別',    # Part 2
        ],
        'base_title': '兩如何詩謝裴令公贈別二首',
    },
    ('平蔡州三首', '劉禹錫'): {
        'markers': [
            '汝南晨雞喔喔鳴',    # Part 2
            '九衢車馬渾渾流',    # Part 3
        ],
        'base_title': '平蔡州三首',
    },
}

# Volume 357: Custom splits for multi-part poems
VOLUME_357_CUSTOM_SPLITS = {
    ('同樂天和微之深春二十首', '劉禹錫'): {
        'markers': [
            '何處深春好，春深阿母家',    # Part 2
            '何處深春好，春深執政家',    # Part 3
            '何處深春好，春深大鎮家',    # Part 4
            '何處深春好，春深貴戚家',    # Part 5
            '何處深春好，春深恩澤家',    # Part 6
            '何處深春好，春深京兆家',    # Part 7
            '何處深春好，春深刺史家',    # Part 8
            '何處深春好，春深羽客家',    # Part 9
            '何處深春好，春深小隱家',    # Part 10
            '何處深春好，春深富室家',    # Part 11
            '何處深春好，春深豪士家',    # Part 12
            '何處深春好，春深貴胄家',    # Part 13
            '何處深春好，春深唱第家',    # Part 14
            '何處深春好，春深少婦家',    # Part 15
            '何處深春好，春深幼女家',    # Part 16
            '何處深春好，春深蘭若家',    # Part 17
            '何處深春好，春深老宿家',    # Part 18
            '何處深春好，春深種蒔家',    # Part 19
            '何處深春好，春深稚子家',    # Part 20
        ],
        'base_title': '同樂天和微之深春二十首',
    },
}

# Volume 468: Custom splits for multi-part poems (marker-based)
VOLUME_468_CUSTOM_SPLITS = {
    ('北原情三首', '劉言史'): {
        'markers': [
            '洛陽城北山，',  # Part 2
            '蔔地起孤墳，',  # Part 3
        ],
        'base_title': '北原情三首',
    },
}

# Volume 485: Custom splits for multi-part poems (marker-based)
VOLUME_485_CUSTOM_SPLITS = {
    ('懷仙二首', '鮑溶'): {
        'markers': [
            '閬峰綺閣幾千丈，',  # Part 2
        ],
        'base_title': '懷仙二首',
    },
    ('秋懷五首', '鮑溶'): {
        'markers': [
            '秋曉客迢迢，',  # Part 2
            '九月夜如年，',  # Part 3
            '金氣白日來，',  # Part 4
            '龍荒變露色，',  # Part 5
        ],
        'base_title': '秋懷五首',
    },
    ('范真傳侍御累有寄，因奉酬十首', '鮑溶'): {
        'markers': [
            '白雪翦花朱蠟蒂，',  # Part 2
            '雲髻鳳文細，',  # Part 3
            '玉管傾杯樂，',  # Part 4
            '聞道中山酒，',  # Part 5
            '紅袂歌聲起，',  # Part 6
            '相勸醉年華，',  # Part 7
            '碧綠草縈堤，',  # Part 8
            '萋萋巫峽雲，',  # Part 9
            '歲酒勸屠蘇，',  # Part 10
        ],
        'base_title': '范真傳侍御累有寄，因奉酬十首',
    },
}

# Volume 486: Custom splits for multi-part poems (marker-based)
VOLUME_486_CUSTOM_SPLITS = {
    ('弄玉詞二首', '鮑溶'): {
        'markers': [
            '三清弄玉秦公女，',  # Part 2
        ],
        'base_title': '弄玉詞二首',
    },
    ('途中旅思二首', '鮑溶'): {
        'markers': [
            '星出方問宿，',  # Part 2
        ],
        'base_title': '途中旅思二首',
    },
    ('秋思三首', '鮑溶'): {
        'markers': [
            '顧兔蝕殘月，',  # Part 2
            '季秋天地閒，',  # Part 3
        ],
        'base_title': '秋思三首',
    },
    ('山中冬思二首', '鮑溶'): {
        'markers': [
            '雪壯冰亦堅，',  # Part 2
        ],
        'base_title': '山中冬思二首',
    },
    ('採蓮曲二首', '鮑溶'): {
        'markers': [
            '採蓮朅來水無風，',  # Part 2
        ],
        'base_title': '採蓮曲二首',
    },
}

# Volume 494: Custom splits for multi-part poems (marker-based)
VOLUME_494_CUSTOM_SPLITS = {
    ('古別離二首', '施肩吾'): {
        'markers': [
            '老母別愛子，',  # Part 2
        ],
        'base_title': '古別離二首',
    },
}

# Volume 522: Custom splits for multi-part poems (marker-based)
VOLUME_522_CUSTOM_SPLITS = {
    ('揚州三首', '杜牧'): {
        'markers': [
            '秋風放螢苑，',  # Part 2
            '街垂千步柳，',  # Part 3
        ],
        'base_title': '揚州三首',
    },
}

# Volume 527: Custom splits for multi-part poems (marker-based)
VOLUME_527_CUSTOM_SPLITS = {
    ('為人題贈二首', '杜牧'): {
        'markers': [
            '綠樹鶯鶯語，',  # Part 2
        ],
        'base_title': '為人題贈二首',
    },
}

# Volume 539: Custom splits for multi-part poems (marker-based)
# Note: Volume 539 has TWO different "無題二首" poems by 李商隱 (UIDs 539_103 and 539_110).
# They have different content and require different splits. Use get_volume_539_wuti_ershou_split()
# function which identifies the poem by first line and returns appropriate splits.
VOLUME_539_CUSTOM_SPLITS = {
    ('漫成三首', '李商隱'): {
        'markers': [
            '沈約憐何遜',  # Part 2 (use first half - normalization adds comma)
            '霧夕詠芙蕖',  # Part 3
        ],
        'base_title': '漫成三首',
    },
    ('無題二首', '李商隱'): {
        'use_function': 'get_volume_539_wuti_ershou_split',  # Special handling
        'base_title': '無題二首',
    },
    ('無題四首', '李商隱'): {
        'markers': [
            '颯颯東風細雨來',  # Part 2 (use first half - normalization adds comma)
            '含情春晼晚',       # Part 3
            '何處哀箏隨急管',  # Part 4
        ],
        'base_title': '無題四首',
    },
    ('蝶三首', '李商隱'): {
        'markers': [
            '長眉畫了繡簾開',  # Part 2 (use first half - normalization adds comma)
            '壽陽公主嫁時妝',  # Part 3
        ],
        'base_title': '蝶三首',
    },
    ('馬嵬二首', '李商隱'): {
        'markers': [
            '海外徒聞更九州',  # Part 2 (use first half - normalization adds comma)
        ],
        'base_title': '馬嵬二首',
    },
}

# Volume 540: Custom splits for multi-part poems (marker-based)
VOLUME_540_CUSTOM_SPLITS = {
    ('楚宮二首', '李商隱'): {
        'markers': [
            '月姊曾逢下彩蟾，',  # Part 2
        ],
        'base_title': '楚宮二首',
    },
    ('李夫人三首', '李商隱'): {
        'markers': [
            '剩結茱萸枝，',  # Part 2
            '壽宮不惜鑄南人，',  # Part 3
        ],
        'base_title': '李夫人三首',
    },
}

# Volume 541: Custom splits for multi-part poems (marker-based)
VOLUME_541_CUSTOM_SPLITS = {
    ('河內詩二首', '李商隱'): {
        'markers': [
            '閶門日下吳歌遠，',  # Part 2
        ],
        'base_title': '河內詩二首',
    },
}

# Volume 608: Named part sets that need to be merged (share entry_index)
VOLUME_608_NAMED_PART_SETS = [
    {
        'base_title': '補周禮九夏系文：九夏歌九篇',
        'author': '皮日休',
        'expected_count': 9,
        'part_patterns': ['王出入', '屍出入', '牲出入', '四方賓客來', '臣有功',
                         '夫人祭', '族人酌', '賓既出', '公出入'],
    },
    {
        'base_title': '七愛詩',
        'author': '皮日休',
        'expected_count': 6,
        'part_patterns': ['房杜二相國', '李太尉', '盧征君', '元魯山', '李翰林', '白太傅'],
    },
    {
        'base_title': '正樂府十篇',
        'author': '皮日休',
        'expected_count': 10,
        'part_patterns': ['卒妻怨', '橡媼歎', '貪官怨', '農父謠', '路臣恨',
                         '賤貢士', '頌夷臣', '惜義鳥', '誚虛器', '哀隴民'],
    },
]

# Volume 608: Custom splits for multi-part poems
VOLUME_608_CUSTOM_SPLITS = {
    ('補周禮九夏系文：九夏歌九篇', '皮日休'): {
        'markers': [
            '愔愔清廟，',  # Part 2: 屍出入 (line 16)
            '有鬱其鬯，',  # Part 3: 牲出入 (line 24)
            '麟之儀儀，',  # Part 4: 四方賓客來 (line 32)
            '王有虎臣，',  # Part 5: 臣有功 (line 48)
            '何以樂之，',  # Part 6: 夫人祭 (line 60)
            '洪源誰孕，',  # Part 7: 族人酌 (line 68)
            '禮酒既酌，',  # Part 8: 賓既出 (line 76)
            '桓桓其珪，',  # Part 9: 公出入 (line 85)
        ],
        'custom_part_names': ['王出入', '屍出入', '牲出入', '四方賓客來', '臣有功',
                             '夫人祭', '族人酌', '賓既出', '公出入'],
        'base_title': '補周禮九夏系文：九夏歌九篇',
    },
    ('三羞詩三首', '皮日休'): {
        'markers': [
            '南荒不擇吏，',  # Part 2 (line 40)
            '天子丙戌年，',  # Part 3 (line 74)
        ],
        'base_title': '三羞詩三首',
    },
}

# Volume 616: Custom splits for multi-part poems
VOLUME_616_CUSTOM_SPLITS = {
    ('夜會問答十', '皮日休'): {
        'markers': [
            '癭木杯，',  # Part 2 (line 2)
            '落霞琴，',  # Part 3 (line 4)
            '蓮花燭，',  # Part 4 (line 6)
            '金火障，',  # Part 5 (line 8)
            '憶山月，',  # Part 6 (line 10)
            '錦鯨薦，',  # Part 7 (line 12)
            '懷溪雲，',  # Part 8 (line 14)
            '霜中笛，',  # Part 9 (line 16)
            '月下橋，',  # Part 10 (line 18)
        ],
        'base_title': '夜會問答十',
    },
}

# Volume 609: Named part sets that need to be merged (share entry_index)
VOLUME_609_NAMED_PART_SETS = [
    {
        'base_title': '二遊詩',
        'author': '皮日休',
        'expected_count': 2,
        'part_patterns': ['徐詩', '任詩'],
    },
    {
        'base_title': '公齋四詠',
        'author': '皮日休',
        'expected_count': 4,
        'part_patterns': ['小松', '小桂', '新竹', '鶴屏'],
    },
]

# Volume 610: Named part sets that need to be merged (share entry_index)
VOLUME_610_NAMED_PART_SETS = [
    {
        'base_title': '太湖詩',
        'author': '皮日休',
        'expected_count': 20,
        'part_patterns': ['初入太湖', '曉次神景宮', '入林屋洞', '雨中游包山精舍', '游毛公壇',
                         '三宿神景宮', '以毛公泉一瓶獻上諫議因寄', '縹緲峰', '桃花塢', '明月灣',
                         '練瀆', '投龍潭', '孤園寺', '上真觀', '銷夏灣',
                         '包山祠', '聖姑廟', '太湖石', '崦裏', '石板'],
    },
]

# Volume 611: Named part sets that need to be merged (share entry_index)
VOLUME_611_NAMED_PART_SETS = [
    {
        'base_title': '奉和魯望漁具十五詠',
        'author': '皮日休',
        'expected_count': 15,
        'part_patterns': ['網', '罩', '罱', '釣筒', '釣車', '漁梁', '叉魚', '射魚',
                         '鳴桹', '滬', '𥶠', '種魚', '藥魚', '舴艋', '笭箵'],
    },
    {
        'base_title': '添魚具詩',
        'author': '皮日休',
        'expected_count': 5,
        'part_patterns': ['魚庵', '釣磯', '蓑衣', '箬笠', '背篷'],
    },
    {
        'base_title': '奉和魯望樵人十詠',
        'author': '皮日休',
        'expected_count': 10,
        'part_patterns': ['樵溪', '樵家', '樵叟', '樵子', '樵徑', '樵斧', '樵擔', '樵風', '樵火', '樵歌'],
    },
    {
        'base_title': '酒中十詠',
        'author': '皮日休',
        'expected_count': 10,
        'part_patterns': ['酒星', '酒泉', '酒篘', '酒床', '酒壚', '酒樓', '酒旗', '酒樽', '酒城', '酒鄉'],
    },
    {
        'base_title': '奉和添酒中六詠',
        'author': '皮日休',
        'expected_count': 6,
        'part_patterns': ['酒池', '酒龍', '酒甕', '酒船', '酒槍', '酒杯'],
    },
    {
        'base_title': '茶中雜詠',
        'author': '皮日休',
        'expected_count': 10,
        'part_patterns': ['茶塢', '茶人', '茶筍', '茶籝', '茶舍', '茶灶', '茶焙', '茶鼎', '茶甌', '煮茶'],
    },
]

# Volume 612: Named part sets that need to be merged (share entry_index)
VOLUME_612_NAMED_PART_SETS = [
    {
        'base_title': '奉和魯望四明山九題',
        'author': '皮日休',
        'expected_count': 9,
        'part_patterns': ['石窗', '過雲', '雲南', '雲北', '鹿亭', '樊榭', '潺湲洞', '青欞子', '鞠侯'],
    },
    {
        'base_title': '五貺詩',
        'author': '皮日休',
        'expected_count': 5,
        'part_patterns': ['五瀉舟', '華頂杖', '太湖硯', '烏龍養和', '訶陵樽'],
    },
]

# Volume 615: Named part sets that need to be merged (share entry_index)
VOLUME_615_NAMED_PART_SETS = [
    {
        'base_title': '木蘭後池三詠',
        'author': '皮日休',
        'expected_count': 3,
        'part_patterns': ['重台蓮花', '浮萍', '白蓮'],
    },
]

# Volume 616: Named part sets that need to be merged (share entry_index)
VOLUME_616_NAMED_PART_SETS = [
    {
        'base_title': '苦雨中又作四聲詩寄魯望',
        'author': '皮日休',
        'expected_count': 4,
        'part_patterns': ['平聲', '平上聲', '平去聲', '平入聲'],
    },
]

# Volume 617: Named part sets that need to be merged (share entry_index)
VOLUME_617_NAMED_PART_SETS = [
    {
        'base_title': '奉和襲美二遊詩',
        'author': '陸龜蒙',
        'expected_count': 2,
        'part_patterns': ['徐詩', '任詩'],
    },
]

# Volume 618: Named part sets that need to be merged (share entry_index)
VOLUME_618_NAMED_PART_SETS = [
    {
        'base_title': '奉和襲美公齋四詠次韻',
        'author': '陸龜蒙',
        'expected_count': 4,
        'part_patterns': ['小松', '小桂', '新竹', '鶴屏'],
    },
]

# Volume 620: Named part sets that need to be merged (share entry_index)
VOLUME_620_NAMED_PART_SETS = [
    {
        'base_title': '漁具詩',
        'author': '陸龜蒙',
        'expected_count': 15,
        'part_patterns': ['網', '罩', '𠉁', '釣筒', '釣車', '魚梁', '叉魚', '射魚', '鳴桹', '滬', '𥶠', '種魚', '藥魚', '舴艋', '笭箵'],
    },
    {
        'base_title': '奉和襲美添漁具五篇',
        'author': '陸龜蒙',
        'expected_count': 5,
        'part_patterns': ['漁庵', '釣磯', '蓑衣', '箬笠', '背蓬'],
    },
    {
        'base_title': '樵人十詠',
        'author': '陸龜蒙',
        'expected_count': 10,
        'part_patterns': ['樵谿', '樵家', '樵叟', '樵子', '樵徑', '樵斧', '樵擔', '樵風', '樵火', '樵歌'],
    },
    {
        'base_title': '奉和襲美酒中十詠',
        'author': '陸龜蒙',
        'expected_count': 10,
        'part_patterns': ['酒星', '酒泉', '酒篘', '酒牀', '酒壚', '酒樓', '酒旗', '酒尊', '酒城', '酒鄉'],
    },
    {
        'base_title': '添酒中六詠',
        'author': '陸龜蒙',
        'expected_count': 6,
        'part_patterns': ['酒池', '酒龍', '酒甕', '酒船', '酒槍', '酒杯'],
    },
    {
        'base_title': '奉和襲美茶具十詠',
        'author': '陸龜蒙',
        'expected_count': 10,
        'part_patterns': ['茶塢', '茶人', '茶筍', '茶籝', '茶舍', '茶竈', '茶焙', '茶鼎', '茶甌', '煮茶'],
    },
]

# Volume 621: Named part sets that need to be merged (share entry_index)
VOLUME_621_NAMED_PART_SETS = [
    {
        'base_title': '句曲山朝真詞二首',
        'author': '陸龜蒙',
        'expected_count': 2,
        'part_patterns': ['迎真', '送真'],
    },
    {
        'base_title': '迎潮送潮辭',
        'author': '陸龜蒙',
        'expected_count': 2,
        'part_patterns': ['迎潮', '送潮'],
    },
    {
        'base_title': '吳俞兒舞歌',
        'author': '陸龜蒙',
        'expected_count': 3,
        'part_patterns': ['劍俞', '矛俞', '弩俞'],
    },
    {
        'base_title': '五歌',
        'author': '陸龜蒙',
        'expected_count': 5,
        'part_patterns': ['放牛', '水鳥', '刈獲', '雨夜', '食魚'],
    },
]

# Volume 622: Named part sets that need to be merged (share entry_index)
VOLUME_622_NAMED_PART_SETS = [
    {
        'base_title': '四明山詩',
        'author': '陸龜蒙',
        'expected_count': 9,
        'part_patterns': ['石窗', '過雲', '雲南', '雲北', '鹿亭', '樊榭', '潺湲洞', '青欞子', '鞠侯'],
    },
    {
        'base_title': '奉和襲美贈魏處士五貺詩',
        'author': '陸龜蒙',
        'expected_count': 5,
        'part_patterns': ['五瀉舟', '華頂杖', '太湖硯', '烏龍養和', '訶陵尊'],
    },
]

# Volume 627: Named part sets that need to be merged (share entry_index)
VOLUME_627_NAMED_PART_SETS = [
    {
        'base_title': '子夜四時歌',
        'author': '陸龜蒙',
        'expected_count': 4,
        'part_patterns': ['春', '夏', '秋', '冬'],
    },
]

# Volume 628: Named part sets that need to be merged (share entry_index)
VOLUME_628_NAMED_PART_SETS = [
    {
        'base_title': '和襲美木蘭後池三詠',
        'author': '陸龜蒙',
        'expected_count': 3,
        'part_patterns': ['重臺蓮花', '浮萍', '白蓮'],
    },
]

# Volume 630: Named part sets that need to be merged (share entry_index)
VOLUME_630_NAMED_PART_SETS = [
    {
        'base_title': '夏日閒居作四聲詩寄襲美',
        'author': '陸龜蒙',
        'expected_count': 4,
        'part_patterns': ['平聲', '平上聲', '平去聲', '平入聲'],
    },
    {
        'base_title': '奉酬襲美苦雨四聲重寄三十二句',
        'author': '陸龜蒙',
        'expected_count': 4,
        'part_patterns': ['平聲', '平上聲', '平去聲', '平入聲'],
    },
]

# Volume 634: Named part sets that need to be merged (share entry_index)
VOLUME_634_NAMED_PART_SETS = [
    {
        'base_title': '詩品二十四則',
        'author': '司空圖',
        'expected_count': 24,
        'part_patterns': ['雄渾', '沖淡', '纖穠', '沉著', '高古', '典雅', '洗煉', '勁健', '綺麗', '自然',
                         '含蓄', '豪放', '精神', '縝密', '疏野', '清奇', '委曲', '實境', '悲慨', '形容',
                         '超詣', '飄逸', '曠達', '流動'],
    },
]

# Volume 16: Multi-song poems that need splitting
VOLUME_16_MULTISONG_SPLITS = [
    {
        'title_pattern': '郊廟歌辭 晉昭德成功舞歌 昭德舞歌二首',
        'author': 'Unknown',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 8),    # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '郊廟歌辭 晉昭德成功舞歌 武功舞歌二首',
        'author': 'Unknown',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 8),    # Song 2: 4 lines
        ]
    },
]

# Volume 22: Multi-song poems that need splitting
VOLUME_22_MULTISONG_SPLITS = [
    {
        'title_pattern': '舞曲歌辭·白紵辭二首',
        'author': '崔國輔',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '舞曲歌辭·白紵辭二首',
        'author': '楊衡',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 8),    # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '舞曲歌辭·白紵歌二首',
        'author': '王建',
        'line_count': 9,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 9),    # Song 2: 5 lines
        ]
    },
    {
        'title_pattern': '舞曲歌辭·霓裳辭十首',
        'author': '王建',
        'line_count': 20,
        'num_songs': 10,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
            (4, 6),     # Song 3: 2 lines
            (6, 8),     # Song 4: 2 lines
            (8, 10),    # Song 5: 2 lines
            (10, 12),   # Song 6: 2 lines
            (12, 14),   # Song 7: 2 lines
            (14, 16),   # Song 8: 2 lines
            (16, 18),   # Song 9: 2 lines
            (18, 20),   # Song 10: 2 lines
        ]
    },
    {
        'title_pattern': '舞曲歌辭·柘枝詞三首',
        'author': '薛能',
        'line_count': 9,
        'num_songs': 3,
        'splits': [
            (0, 3),    # Song 1: 3 lines
            (3, 6),    # Song 2: 3 lines
            (6, 9),    # Song 3: 3 lines
        ]
    },
]

# Volume 23: Multi-song poems that need splitting
VOLUME_23_MULTISONG_SPLITS = [
    {
        'title_pattern': '琴曲歌辭·蔡氏五弄·秋思二首',
        'author': '鮑溶',
        'line_count': 21,
        'num_songs': 2,
        'splits': [
            (0, 14),    # Song 1: 14 lines
            (14, 21),   # Song 2: 7 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·蔡氏五弄·秋思二首',
        'author': '李白',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 8),    # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·蔡氏五弄·遊春辭二首',
        'author': '王涯',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·蔡氏五弄·遊春辭三首',
        'author': '令狐楚',
        'line_count': 6,
        'num_songs': 3,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
            (4, 6),    # Song 3: 2 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·蔡氏五弄·遊春曲二首',
        'author': '王涯',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·昭君怨二首',
        'author': '張祜',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·宛轉歌二首',
        'author': '劉方平',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 8),    # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·飛龍引二首',
        'author': '李白',
        'line_count': 11,
        'num_songs': 2,
        'splits': [
            (0, 5),    # Song 1: 5 lines
            (5, 11),   # Song 2: 6 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·蔡氏五弄·秋思二首',
        'author': '王涯',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '琴曲歌辭·胡笳十八拍',
        'author': '劉商',
        'line_count': 74,
        'num_songs': 18,
        'splits': [
            (0, 5),     # Part 1: 5 lines
            (5, 9),     # Part 2: 4 lines
            (9, 13),    # Part 3: 4 lines
            (13, 17),   # Part 4: 4 lines
            (17, 21),   # Part 5: 4 lines
            (21, 25),   # Part 6: 4 lines
            (25, 29),   # Part 7: 4 lines
            (29, 33),   # Part 8: 4 lines
            (33, 37),   # Part 9: 4 lines
            (37, 41),   # Part 10: 4 lines
            (41, 45),   # Part 11: 4 lines
            (45, 49),   # Part 12: 4 lines
            (49, 53),   # Part 13: 4 lines
            (53, 57),   # Part 14: 4 lines
            (57, 61),   # Part 15: 4 lines
            (61, 65),   # Part 16: 4 lines
            (65, 69),   # Part 17: 4 lines
            (69, 74),   # Part 18: 5 lines
        ]
    },
]

# Volume 24: Multi-song poems that need splitting
VOLUME_24_MULTISONG_SPLITS = [
    {
        'title_pattern': '雜曲歌辭·妾薄命三首',
        'author': '李端',
        'line_count': 14,
        'num_songs': 3,
        'splits': [
            (0, 7),     # Song 1: 7 lines
            (7, 12),    # Song 2: 5 lines
            (12, 14),   # Song 3: 2 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·薊門行五首',
        'author': '高適',
        'line_count': 15,
        'num_songs': 5,
        'splits': [
            (0, 3),     # Song 1: 3 lines
            (3, 6),     # Song 2: 3 lines
            (6, 9),     # Song 3: 3 lines
            (9, 12),    # Song 4: 3 lines
            (12, 15),   # Song 5: 3 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·出門行二首',
        'author': '孟郊',
        'line_count': 11,
        'num_songs': 2,
        'splits': [
            (0, 5),     # Song 1: 5 lines
            (5, 11),    # Song 2: 6 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·長安少年行十首',
        'author': '李廓',
        'line_count': 40,
        'num_songs': 10,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
            (12, 16),   # Song 4: 4 lines
            (16, 20),   # Song 5: 4 lines
            (20, 24),   # Song 6: 4 lines
            (24, 28),   # Song 7: 4 lines
            (28, 32),   # Song 8: 4 lines
            (32, 36),   # Song 9: 4 lines
            (36, 40),   # Song 10: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行三首',
        'author': '貫休',
        'line_count': 6,
        'num_songs': 3,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
            (4, 6),     # Song 3: 2 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行三首',
        'author': '杜甫',
        'line_count': 6,
        'num_songs': 3,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
            (4, 6),     # Song 3: 2 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行二首',
        'author': '杜牧',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 8),     # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行四首',
        'author': '令狐楚',
        'line_count': 8,
        'num_songs': 4,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
            (4, 6),     # Song 3: 2 lines
            (6, 8),     # Song 4: 2 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行三首',
        'author': '李嶷',
        'line_count': 9,
        'num_songs': 3,
        'splits': [
            (0, 3),     # Song 1: 3 lines
            (3, 6),     # Song 2: 3 lines
            (6, 9),     # Song 3: 3 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行二首',
        'author': '王昌齡',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行四首',
        'author': '王維',
        'line_count': 8,
        'num_songs': 4,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
            (4, 6),     # Song 3: 2 lines
            (6, 8),     # Song 4: 2 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·少年行三首',
        'author': '李白',
        'line_count': 21,
        'num_songs': 3,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 6),     # Song 2: 2 lines
            (6, 21),    # Song 3: 15 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·前有一尊酒行二首',
        'author': '李白',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
]

# Volume 25: Multi-song poems that need splitting
VOLUME_25_MULTISONG_SPLITS = [
    {
        'title_pattern': '雜曲歌辭·輕薄篇二首',
        'author': '貫休',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·長相思三首',
        'author': '李白',
        'line_count': 15,
        'num_songs': 3,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 11),    # Song 2: 5 lines
            (11, 15),   # Song 3: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·長相思二首',
        'author': '令狐楚',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·行路難五首',
        'author': '賀蘭進明',
        'line_count': 21,
        'num_songs': 5,
        'splits': [
            (0, 5),     # Song 1: 5 lines
            (5, 9),     # Song 2: 4 lines
            (9, 13),    # Song 3: 4 lines
            (13, 17),   # Song 4: 4 lines
            (17, 21),   # Song 5: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·行路難三首',
        'author': '李白',
        'line_count': 23,
        'num_songs': 3,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 14),    # Song 2: 8 lines
            (14, 23),   # Song 3: 9 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·行路難三首',
        'author': '顧況',
        'line_count': 18,
        'num_songs': 3,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 12),    # Song 2: 6 lines
            (12, 18),   # Song 3: 6 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·行路難二首',
        'author': '高適適',
        'line_count': 10,
        'num_songs': 2,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 10),    # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·行路難三首',
        'author': '柳宗元',
        'line_count': 20,
        'num_songs': 3,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 13),    # Song 2: 7 lines
            (13, 20),   # Song 3: 7 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·行路難五首',
        'author': '貫休',
        'line_count': 30,
        'num_songs': 5,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 13),    # Song 2: 7 lines
            (13, 18),   # Song 3: 5 lines
            (18, 26),   # Song 4: 8 lines
            (26, 30),   # Song 5: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·行路難二首',
        'author': '齊己',
        'line_count': 9,
        'num_songs': 2,
        'splits': [
            (0, 5),     # Song 1: 5 lines
            (5, 9),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·從軍中行路難二首',
        'author': '駱賓王',
        'line_count': 46,
        'num_songs': 2,
        'splits': [
            (0, 32),    # Song 1: 32 lines
            (32, 46),   # Song 2: 14 lines
        ]
    },
]

# Volume 26: Multi-song poems that need splitting
VOLUME_26_MULTISONG_SPLITS = [
    {
        'title_pattern': '雜曲歌辭·古別離二首',
        'author': '於濆',
        'line_count': 22,
        'num_songs': 2,
        'splits': [
            (0, 12),    # Song 1: 12 lines
            (12, 22),   # Song 2: 10 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·古別離二首',
        'author': '李端',
        'line_count': 38,
        'num_songs': 2,
        'splits': [
            (0, 16),    # Song 1: 16 lines
            (16, 38),   # Song 2: 22 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·古別離二首',
        'author': '施肩吾',
        'line_count': 14,
        'num_songs': 2,
        'splits': [
            (0, 6),     # Song 1: 6 lines
            (6, 14),    # Song 2: 8 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·古離別二首',
        'author': '孟郊',
        'line_count': 24,
        'num_songs': 2,
        'splits': [
            (0, 8),     # Song 1: 8 lines
            (8, 24),    # Song 2: 16 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·遠別離二首',
        'author': '令狐楚',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·荊州樂二首',
        'author': '劉禹錫',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·長干曲四首',
        'author': '崔顥',
        'line_count': 16,
        'num_songs': 4,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
            (12, 16),   # Song 4: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·長干行二首',
        'author': '李白',
        'line_count': 58,
        'num_songs': 2,
        'splits': [
            (0, 24),    # Song 1: 24 lines
            (24, 58),   # Song 2: 34 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·三台二首',
        'author': '韋應物',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·宮中三台二首',
        'author': '王建',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·江南三台四首',
        'author': '王建',
        'line_count': 16,
        'num_songs': 4,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
            (12, 16),   # Song 4: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·築城曲五解',
        'author': '元稹',
        'line_count': 20,
        'num_songs': 5,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
            (12, 16),   # Song 4: 4 lines
            (16, 20),   # Song 5: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·秋夜曲二首',
        'author': '王建',
        'line_count': 14,
        'num_songs': 2,
        'splits': [
            (0, 10),    # Song 1: 10 lines
            (10, 14),   # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·春江曲二首',
        'author': '張仲素',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·春遊樂二首',
        'author': '李端',
        'line_count': 16,
        'num_songs': 2,
        'splits': [
            (0, 8),     # Song 1: 8 lines
            (8, 16),    # Song 2: 8 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·春遊曲三首',
        'author': '張仲素',
        'line_count': 12,
        'num_songs': 3,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·樂府二首',
        'author': '劉言史',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·樂府三首',
        'author': '孟郊',
        'line_count': 12,
        'num_songs': 3,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
        ]
    },
    {
        'title_pattern': '雜曲歌辭·古曲五首',
        'author': '施肩吾',
        'line_count': 20,
        'num_songs': 5,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
            (8, 12),    # Song 3: 4 lines
            (12, 16),   # Song 4: 4 lines
            (16, 20),   # Song 5: 4 lines
        ]
    },
]

# Volume 85: Multi-part ritual music poems that need splitting
VOLUME_85_MULTISONG_SPLITS = [
    {
        'title_pattern': '唐封泰山樂章豫和六首',
        'author': '張說',
        'line_count': 24,
        'num_songs': 6,
        'splits': [
            (0, 4),     # Part 1: 4 lines
            (4, 8),     # Part 2: 4 lines
            (8, 12),    # Part 3: 4 lines
            (12, 16),   # Part 4: 4 lines
            (16, 20),   # Part 5: 4 lines
            (20, 24),   # Part 6: 4 lines
        ]
    },
    {
        'title_pattern': '唐享太廟樂章永和三首',
        'author': '張說',
        'line_count': 12,
        'num_songs': 3,
        'splits': [
            (0, 4),     # Part 1: 4 lines
            (4, 8),     # Part 2: 4 lines
            (8, 12),    # Part 3: 4 lines
        ]
    },
    {
        'title_pattern': '唐享太廟樂章雍和二首',
        'author': '張說',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Part 1: 4 lines
            (4, 8),     # Part 2: 4 lines
        ]
    },
    {
        'title_pattern': '唐享太廟樂章凱安三首',
        'author': '張說',
        'line_count': 12,
        'num_songs': 3,
        'splits': [
            (0, 4),     # Part 1: 4 lines
            (4, 8),     # Part 2: 4 lines
            (8, 12),    # Part 3: 4 lines
        ]
    },
]

# Volume 98: Multi-song poems that need splitting
VOLUME_98_MULTISONG_SPLITS = [
    {
        'title_pattern': '和尹懋秋夜遊㴩湖二首',
        'author': '趙冬曦',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
    {
        'title_pattern': '秋夜陪張丞相趙侍御游㴩湖二首',
        'author': '尹懋',
        'line_count': 8,
        'num_songs': 2,
        'splits': [
            (0, 4),     # Song 1: 4 lines
            (4, 8),     # Song 2: 4 lines
        ]
    },
]

# Volume 218: Multi-song poems that need splitting (Du Fu)
VOLUME_218_MULTISONG_SPLITS = [
    {
        'title_pattern': '遣興三首',
        'author': '杜甫',
        'line_count': 18,
        'num_songs': 3,
        'splits': [
            (0, 6),      # Song 1: 6 lines
            (6, 12),     # Song 2: 6 lines
            (12, 18),    # Song 3: 6 lines
        ]
    },
    {
        'title_pattern': '西枝村尋置草堂地夜宿贊公土室二首',
        'author': '杜甫',
        'line_count': 20,
        'num_songs': 2,
        'splits': [
            (0, 10),     # Song 1: 10 lines
            (10, 20),    # Song 2: 10 lines
        ]
    },
    {
        'title_pattern': '夢李白二首',
        'author': '杜甫',
        'line_count': 16,
        'num_songs': 2,
        'splits': [
            (0, 8),      # Song 1: 8 lines
            (8, 16),     # Song 2: 8 lines
        ]
    },
    {
        'title_pattern': '遣興五首',
        'author': '杜甫',
        'line_count': 25,
        'num_songs': 5,
        'splits': [
            (0, 5),      # Song 1: 5 lines
            (5, 10),     # Song 2: 5 lines
            (10, 15),    # Song 3: 5 lines
            (15, 20),    # Song 4: 5 lines
            (20, 25),    # Song 5: 5 lines
        ]
    },
    {
        'title_pattern': '遣興五首',
        'author': '杜甫',
        'line_count': 20,
        'num_songs': 5,
        'splits': [
            (0, 4),      # Song 1: 4 lines
            (4, 8),      # Song 2: 4 lines
            (8, 12),     # Song 3: 4 lines
            (12, 16),    # Song 4: 4 lines
            (16, 20),    # Song 5: 4 lines
        ]
    },
    {
        'title_pattern': '前出塞九首',
        'author': '杜甫',
        'line_count': 36,
        'num_songs': 9,
        'splits': [
            (0, 4),      # Song 1: 4 lines
            (4, 8),      # Song 2: 4 lines
            (8, 12),     # Song 3: 4 lines
            (12, 16),    # Song 4: 4 lines
            (16, 20),    # Song 5: 4 lines
            (20, 24),    # Song 6: 4 lines
            (24, 28),    # Song 7: 4 lines
            (28, 32),    # Song 8: 4 lines
            (32, 36),    # Song 9: 4 lines
        ]
    },
    {
        'title_pattern': '後出塞五首',
        'author': '杜甫',
        'line_count': 31,
        'num_songs': 5,
        'splits': [
            (0, 7),      # Song 1: 7 lines
            (7, 13),     # Song 2: 6 lines
            (13, 19),    # Song 3: 6 lines
            (19, 25),    # Song 4: 6 lines
            (25, 31),    # Song 5: 6 lines
        ]
    },
    {
        'title_pattern': '乾元中寓居同谷縣作歌七首',
        'author': '杜甫',
        'line_count': 28,
        'num_songs': 7,
        'splits': [
            (0, 4),      # Song 1: 4 lines
            (4, 8),      # Song 2: 4 lines
            (8, 12),     # Song 3: 4 lines
            (12, 16),    # Song 4: 4 lines
            (16, 20),    # Song 5: 4 lines
            (20, 24),    # Song 6: 4 lines
            (24, 28),    # Song 7: 4 lines
        ]
    },
]

# Volume 220: Multi-song poems that need splitting (Du Fu)
VOLUME_220_MULTISONG_SPLITS = [
    {
        'title_pattern': '憶昔二首',
        'author': '杜甫',
        'line_count': 19,
        'num_songs': 2,
        'splits': [
            (0, 8),      # Song 1: 8 lines
            (8, 19),     # Song 2: 11 lines
        ]
    },
]

# Volume 221: Multi-song poems that need splitting (Du Fu)
VOLUME_221_MULTISONG_SPLITS = [
    {
        'title_pattern': '雨二首',
        'author': '杜甫',
        'line_count': 16,
        'num_songs': 2,
        'splits': [
            (0, 8),      # Song 1: 8 lines
            (8, 16),     # Song 2: 8 lines
        ]
    },
]

# Volume 222: Multi-song poems that need splitting (Du Fu)
VOLUME_222_MULTISONG_SPLITS = [
    {
        'title_pattern': '寫懷二首',
        'author': '杜甫',
        'line_count': 24,
        'num_songs': 2,
        'splits': [
            (0, 12),     # Song 1: 12 lines
            (12, 24),    # Song 2: 12 lines
        ]
    },
    {
        'title_pattern': '秋風二首',
        'author': '杜甫',
        'line_count': 10,
        'num_songs': 2,
        'splits': [
            (0, 5),      # Song 1: 5 lines
            (5, 10),     # Song 2: 5 lines
        ]
    },
    {
        'title_pattern': '前苦寒行二首',
        'author': '杜甫',
        'line_count': 10,
        'num_songs': 2,
        'splits': [
            (0, 5),      # Song 1: 5 lines
            (5, 10),     # Song 2: 5 lines
        ]
    },
    {
        'title_pattern': '後苦寒行二首',
        'author': '杜甫',
        'line_count': 7,
        'num_songs': 2,
        'splits': [
            (0, 4),      # Song 1: 5 lines
            (4, 8),     # Song 2: 5 lines
        ]
    },
]

# Volume 223: Multi-song poems that need splitting (Du Fu)
VOLUME_223_MULTISONG_SPLITS = [
    {
        'title_pattern': '詠懷二首',
        'author': '杜甫',
        'line_count': 36,
        'num_songs': 2,
        'splits': [
            (0, 16),     # Song 1: 16 lines
            (16, 36),    # Song 2: 20 lines
        ]
    },
]

# Volume 224: Multi-song poems that need splitting (Du Fu)
VOLUME_224_MULTISONG_SPLITS = [
    {
        'title_pattern': '重過何氏五首',
        'author': '杜甫',
        'line_count': 20,
        'num_songs': 5,
        'splits': [
            (0, 4),      # Song 1: 4 lines
            (4, 8),      # Song 2: 4 lines
            (8, 12),     # Song 3: 4 lines
            (12, 16),    # Song 4: 4 lines
            (16, 20),    # Song 5: 4 lines
        ]
    },
]

# Volume 21: Multi-song poems that need splitting
# Note: 郭元振's 子夜四時歌六首 poems are handled by VOLUME_21_CUSTOM_SPLITS
VOLUME_21_MULTISONG_SPLITS = [
    {
        'title_pattern': '相和歌辭·大子夜歌二首',
        'author': '陸龜蒙',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·子夜警歌二首',
        'author': '陸龜蒙',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·讀曲歌五首',
        'author': '張祜',
        'line_count': 10,
        'num_songs': 5,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
            (4, 6),     # Song 3: 2 lines
            (6, 8),     # Song 4: 2 lines
            (8, 10),    # Song 5: 2 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·春江花月夜二首',
        'author': '張子容',
        'line_count': 6,
        'num_songs': 2,
        'splits': [
            (0, 3),    # Song 1: 3 lines
            (3, 6),    # Song 2: 3 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·採蓮曲三首',
        'author': '王昌齡',
        'line_count': 8,
        'num_songs': 3,
        'splits': [
            (0, 2),     # Song 1: 2 lines
            (2, 4),     # Song 2: 2 lines
            (4, 8),     # Song 3: 4 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·採蓮曲二首',
        'author': '戎昱',
        'line_count': 6,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 6),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·採蓮曲二首',
        'author': '鮑溶',
        'line_count': 5,
        'num_songs': 2,
        'splits': [
            (0, 3),    # Song 1: 3 lines
            (3, 5),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·烏夜啼二首',
        'author': '顧況',
        'line_count': 7,
        'num_songs': 2,
        'splits': [
            (0, 4),    # Song 1: 4 lines
            (4, 7),    # Song 2: 3 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·棲烏曲二首',
        'author': '劉方平',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·襄陽曲二首',
        'author': '崔國輔',
        'line_count': 4,
        'num_songs': 2,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
        ]
    },
    {
        'title_pattern': '相和歌辭·三閣詞四首',
        'author': '劉禹錫',
        'line_count': 8,
        'num_songs': 4,
        'splits': [
            (0, 2),    # Song 1: 2 lines
            (2, 4),    # Song 2: 2 lines
            (4, 6),    # Song 3: 2 lines
            (6, 8),    # Song 4: 2 lines
        ]
    },
]

def get_merge_rule(volume_num: int, title: str, first_line: str):
    """
    Checks if a poem entry should actually be a note merged into an adjacent poem.
    Returns the rule dict if found, None otherwise.
    """
    if volume_num not in POEMS_TO_MERGE_AS_NOTES:
        return None

    for rule in POEMS_TO_MERGE_AS_NOTES[volume_num]:
        if rule['title'] == title and rule['marker'] in first_line:
            return rule

    return None


def get_preface_merge_rule(volume_num: int, title: str, first_line: str, author: str = None):
    """
    Checks if a poem entry should actually be a preface merged into an adjacent poem.
    Returns the rule dict if found, None otherwise.

    Args:
        volume_num: Volume number
        title: Poem title (may have author prefix)
        first_line: First line of poem content
        author: Author recorded name (for stripping prefix)
    """
    import logging
    logger = logging.getLogger(__name__)

    if volume_num not in POEMS_TO_MERGE_AS_PREFACE:
        return None

    stripped_title = title
    if author and title.startswith(f"{author} "):
        stripped_title = title[len(author) + 1:]

    for rule in POEMS_TO_MERGE_AS_PREFACE[volume_num]:
        title_match = rule['title'] == stripped_title
        marker_match = rule['marker'] in first_line

        logger.debug(f"Checking preface rule: title='{rule['title']}' vs '{title}' (stripped='{stripped_title}', match={title_match})")
        logger.debug(f"  Marker check: '{rule['marker'][:50]}...' in '{first_line[:50]}...' (match={marker_match})")

        if title_match and marker_match:
            return rule

    return None


def is_forced_preface_part(volume_num: int, title: str, author: str) -> bool:
    """
    Check if a multi-part poem's part 1 should be treated as a preface
    even if it doesn't meet the automatic prose detection threshold.

    Args:
        volume_num: Volume number
        title: Poem title (should be the part 1 title with 其一/第一 marker)
        author: Author canonical name

    Returns:
        True if this should be force-treated as a preface part
    """
    if volume_num not in FORCE_PREFACE_PARTS:
        return False

    for rule in FORCE_PREFACE_PARTS[volume_num]:
        if rule['title'] == title and rule['author'] == author:
            return True

    return False

# Multi-part poems that appear as multiple div.poem blocks with same title
# These need part numbers added (其一, 其二, etc.)
# Format: {volume_num: {title: num_parts}}
MULTIPART_POEM_TITLES = {
    8: {
        '輓辭二首': 2,
        '沒了期歌二首': 2,
    },
    13: {
        '享太廟樂章 凱安四章': 4,
    },
}

# Title rewrite rules for poems with inconsistent hierarchical naming
# Format: {volume_num: {original_title: new_title}}
TITLE_REWRITES = {
    14: {
        '太清宮樂章 序入破第一奏': '太清宮樂章 序入破 第一奏',
        '太清宮樂章 第二奏': '太清宮樂章 序入破 第二奏',
        '太清宮樂章 第三奏': '太清宮樂章 序入破 第三奏',
    },
}

# Biography entries to remove
# These are biography paragraphs that were extracted as "poems"
# The content should be preserved in the author database before removal
# Format: {volume_num: [list of titles to remove]}
BIOGRAPHY_ENTRIES_TO_REMOVE = {
    2: [
        '高宗皇帝',
        '中宗皇帝',
        '睿宗皇帝',
    ],
    798: [
        '花蕊夫人徐氏',  # Biography entry before 宮詞
    ],
}

# Stub entries to remove
# These are duplicate entries or metadata-only stubs with no actual poem content
# Format: {volume_num: [list of (title, first_line) tuples for precise matching]}
STUB_ENTRIES_TO_REMOVE = {
    2: [
        ('十月誕辰內殿宴羣臣效柏梁體聯句', '聯句'),  # Duplicate stub before actual poem
    ],
}

# Fixes for broken couplets or OCR errors where periods appear mid-couplet
# Format: { 
#   (volume_int, "Title"): [
#       {
#           "target": ["Line A。", "Line B。"], 
#           "replacement": "Line A，Line B。"
#       }
#   ]
# }
BROKEN_COUPLET_FIXES = {
    (21, '相和歌辭·春江花月夜'): [
        {
            # The tool split these because of the period; we merge them and fix punctuation
            'target': ["江天一色無纖塵。", "皎皎空中孤月輪。"],
            'replacement': "江天一色無纖塵，皎皎空中孤月輪。"
        }
    ],
}

def get_couplet_fix(volume: int, title: str) -> list:
    """Returns list of fix dicts if they exist for this poem."""
    return BROKEN_COUPLET_FIXES.get((volume, title), [])

def is_multipart_poem(volume_num: int, title: str) -> int:
    """
    Check if a title is a known multi-part poem that needs part numbers.

    Args:
        volume_num: Volume number
        title: Poem title

    Returns:
        Number of parts if this is a multi-part poem, 0 otherwise
    """
    if volume_num not in MULTIPART_POEM_TITLES:
        return 0

    return MULTIPART_POEM_TITLES[volume_num].get(title, 0)


def apply_title_rewrite(volume_num: int, title: str) -> str:
    """
    Apply title rewrite rules for poems with inconsistent naming.

    Args:
        volume_num: Volume number
        title: Original poem title

    Returns:
        Rewritten title if a rule exists, otherwise original title
    """
    if volume_num not in TITLE_REWRITES:
        return title

    return TITLE_REWRITES[volume_num].get(title, title)


def should_remove_biography_entry(volume_num: int, title: str) -> bool:
    """
    Check if this entry is a biography that should be removed.

    Args:
        volume_num: Volume number
        title: Poem title

    Returns:
        True if this entry should be removed as a biography
    """
    if volume_num not in BIOGRAPHY_ENTRIES_TO_REMOVE:
        return False

    return title in BIOGRAPHY_ENTRIES_TO_REMOVE[volume_num]


def should_remove_stub_entry(volume_num: int, title: str, first_line: str) -> bool:
    """
    Check if this entry is a stub/duplicate that should be removed.

    Args:
        volume_num: Volume number
        title: Poem title
        first_line: First line of poem content

    Returns:
        True if this entry should be removed as a stub
    """
    if volume_num not in STUB_ENTRIES_TO_REMOVE:
        return False

    # Check if (title, first_line) tuple matches any stub entry
    for stub_title, stub_first_line in STUB_ENTRIES_TO_REMOVE[volume_num]:
        if title == stub_title and first_line == stub_first_line:
            return True

    return False


def get_custom_split_config(volume_num: int, title: str, author: str):
    """
    Get custom split configuration for a specific poem.

    Args:
        volume_num: Volume number
        title: Poem title
        author: Poem author (recorded name)

    Returns:
        Split configuration dict if found, None otherwise
    """
    # Check if there's a volume-specific custom splits dictionary
    volume_splits_name = f'VOLUME_{volume_num}_CUSTOM_SPLITS'
    if volume_splits_name in globals():
        volume_splits = globals()[volume_splits_name]
        return volume_splits.get((title, author))

    return None


def is_volume_8_ju_collection_poem(title: str, author: str) -> bool:
    """
    Check if a poem is part of the Volume 8 句 collection by 後主煜.

    Args:
        title: Poem title
        author: Poem author (recorded name)

    Returns:
        True if this poem is part of the 句 collection
    """
    import re
    if author != VOLUME_8_JU_COLLECTION_AUTHOR:
        return False
    return bool(re.match(VOLUME_8_JU_COLLECTION_PATTERN, title))


def get_volume_8_houzhuyu_ju_fragments(poem_lines: list) -> list:
    """
    Get hardcoded fragment splits for Volume 8 後主煜 句 section.

    Args:
        poem_lines: List of poem lines (already cleaned)

    Returns:
        List of (title_suffix, fragment_lines) tuples
    """
    clean_lines = [line for line in poem_lines if line]

    fragments = []
    for title_suffix, start, end in VOLUME_8_HOUZHUYU_JU_FRAGMENT_SPLITS:
        if end is None:
            frag_lines = clean_lines[start:]
        else:
            frag_lines = clean_lines[start:end]

        if frag_lines:
            fragments.append((title_suffix, frag_lines))

    return fragments


def get_volume_539_wuti_ershou_split(poem_lines: list) -> list:
    """
    Get split configuration for Volume 539 無題二首 poems by 李商隱.

    Volume 539 has TWO different "無題二首" poems. This function identifies
    which one it is based on the first line and returns the appropriate split.

    Args:
        poem_lines: List of poem lines

    Returns:
        List of (start, end) tuples for splitting, or None if not recognized
    """
    if not poem_lines:
        return None

    first_line = poem_lines[0] if poem_lines else ""

    # First 無題二首: 昨夜星辰昨夜風...
    # Split: 4 lines + 2 lines
    if first_line.startswith('昨夜星辰昨夜風'):
        return [
            (0, 4),   # Part 1 (其一): 4 lines
            (4, 6),   # Part 2 (其二): 2 lines
        ]

    # Second 無題二首: 八歲偷照鏡...
    # Split: 5 lines + 4 lines
    elif first_line.startswith('八歲偷照鏡'):
        return [
            (0, 5),   # Part 1 (其一): 5 lines
            (5, 9),   # Part 2 (其二): 4 lines
        ]

    return None


# =============================================================================
# REGISTRIES
# =============================================================================
# These registries replace the if-elif chains in post_process_splits.py
# They map volume numbers to their respective functions/configs.

# Registry for multisong splits - maps volume_num directly to config data
MULTISONG_SPLITS_DATA = {
    16: VOLUME_16_MULTISONG_SPLITS,
    17: VOLUME_17_MULTISONG_SPLITS,
    18: VOLUME_18_MULTISONG_SPLITS,
    19: VOLUME_19_MULTISONG_SPLITS,
    20: VOLUME_20_MULTISONG_SPLITS,
    21: VOLUME_21_MULTISONG_SPLITS,
    22: VOLUME_22_MULTISONG_SPLITS,
    23: VOLUME_23_MULTISONG_SPLITS,
    24: VOLUME_24_MULTISONG_SPLITS,
    25: VOLUME_25_MULTISONG_SPLITS,
    26: VOLUME_26_MULTISONG_SPLITS,
    85: VOLUME_85_MULTISONG_SPLITS,
    98: VOLUME_98_MULTISONG_SPLITS,
    218: VOLUME_218_MULTISONG_SPLITS,
    220: VOLUME_220_MULTISONG_SPLITS,
    221: VOLUME_221_MULTISONG_SPLITS,
    222: VOLUME_222_MULTISONG_SPLITS,
    223: VOLUME_223_MULTISONG_SPLITS,
    224: VOLUME_224_MULTISONG_SPLITS,
}

# Registry for named part sets - maps volume_num directly to config data
NAMED_PART_SETS_REGISTRY = {
    13: VOLUME_13_TEMPLE_MUSIC_SETS,
    21: VOLUME_21_SEASONAL_SETS,
    41: VOLUME_41_NAMED_PART_SETS,
    66: VOLUME_66_NAMED_PART_SETS,
    83: VOLUME_83_NAMED_PART_SETS,
    86: VOLUME_86_NAMED_PART_SETS,
    128: VOLUME_128_NAMED_PART_SETS,
    129: VOLUME_129_NAMED_PART_SETS,
    136: VOLUME_136_NAMED_PART_SETS,
    148: VOLUME_148_NAMED_PART_SETS,
    234: VOLUME_234_NAMED_PART_SETS,
    240: VOLUME_240_NAMED_PART_SETS,
    264: VOLUME_264_NAMED_PART_SETS,
    271: VOLUME_271_NAMED_PART_SETS,
    343: VOLUME_343_NAMED_PART_SETS,
    387: VOLUME_387_NAMED_PART_SETS,
    437: VOLUME_437_NAMED_PART_SETS,
    443: VOLUME_443_NAMED_PART_SETS,
    450: VOLUME_450_NAMED_PART_SETS,
    458: VOLUME_458_NAMED_PART_SETS,
    475: VOLUME_475_NAMED_PART_SETS,
    479: VOLUME_479_NAMED_PART_SETS,
    480: VOLUME_480_NAMED_PART_SETS,
    541: VOLUME_541_NAMED_PART_SETS,
    608: VOLUME_608_NAMED_PART_SETS,
    609: VOLUME_609_NAMED_PART_SETS,
    610: VOLUME_610_NAMED_PART_SETS,
    611: VOLUME_611_NAMED_PART_SETS,
    612: VOLUME_612_NAMED_PART_SETS,
    615: VOLUME_615_NAMED_PART_SETS,
    616: VOLUME_616_NAMED_PART_SETS,
    617: VOLUME_617_NAMED_PART_SETS,
    618: VOLUME_618_NAMED_PART_SETS,
    620: VOLUME_620_NAMED_PART_SETS,
    621: VOLUME_621_NAMED_PART_SETS,
    622: VOLUME_622_NAMED_PART_SETS,
    627: VOLUME_627_NAMED_PART_SETS,
    628: VOLUME_628_NAMED_PART_SETS,
    630: VOLUME_630_NAMED_PART_SETS,
    634: VOLUME_634_NAMED_PART_SETS,
    686: VOLUME_686_NAMED_PART_SETS,
    853: VOLUME_853_NAMED_PART_SETS,
}

# Registry for custom splits - maps volume_num directly to config data
CUSTOM_SPLITS_REGISTRY = {
    8: VOLUME_8_CUSTOM_SPLITS,
    17: VOLUME_17_CUSTOM_SPLITS,
    19: VOLUME_19_CUSTOM_SPLITS,
    20: VOLUME_20_CUSTOM_SPLITS,
    21: VOLUME_21_CUSTOM_SPLITS,
    26: VOLUME_26_CUSTOM_SPLITS,
    228: VOLUME_228_CUSTOM_SPLITS,
    229: VOLUME_229_CUSTOM_SPLITS,
    230: VOLUME_230_CUSTOM_SPLITS,
    231: VOLUME_231_CUSTOM_SPLITS,
    233: VOLUME_233_CUSTOM_SPLITS,
    264: VOLUME_264_CUSTOM_SPLITS,
    297: VOLUME_297_CUSTOM_SPLITS,
    298: VOLUME_298_CUSTOM_SPLITS,
    299: VOLUME_299_CUSTOM_SPLITS,
    302: VOLUME_302_CUSTOM_SPLITS,
    312: VOLUME_312_CUSTOM_SPLITS,
    314: VOLUME_314_CUSTOM_SPLITS,
    326: VOLUME_326_CUSTOM_SPLITS,
    328: VOLUME_328_CUSTOM_SPLITS,
    333: VOLUME_333_CUSTOM_SPLITS,
    337: VOLUME_337_CUSTOM_SPLITS,
    338: VOLUME_338_CUSTOM_SPLITS,
    340: VOLUME_340_CUSTOM_SPLITS,
    341: VOLUME_341_CUSTOM_SPLITS,
    342: VOLUME_342_CUSTOM_SPLITS,
    343: VOLUME_343_CUSTOM_SPLITS,
    346: VOLUME_346_CUSTOM_SPLITS,
    352: VOLUME_352_CUSTOM_SPLITS,
    354: VOLUME_354_CUSTOM_SPLITS,
    355: VOLUME_355_CUSTOM_SPLITS,
    356: VOLUME_356_CUSTOM_SPLITS,
    357: VOLUME_357_CUSTOM_SPLITS,
    388: VOLUME_388_CUSTOM_SPLITS,
    390: VOLUME_390_CUSTOM_SPLITS,
    394: VOLUME_394_CUSTOM_SPLITS,
    397: VOLUME_397_CUSTOM_SPLITS,
    400: VOLUME_400_CUSTOM_SPLITS,
    403: VOLUME_403_CUSTOM_SPLITS,
    410: VOLUME_410_CUSTOM_SPLITS,
    413: VOLUME_413_CUSTOM_SPLITS,
    414: VOLUME_414_CUSTOM_SPLITS,
    421: VOLUME_421_CUSTOM_SPLITS,
    424: VOLUME_424_CUSTOM_SPLITS,
    425: VOLUME_425_CUSTOM_SPLITS,
    429: VOLUME_429_CUSTOM_SPLITS,
    430: VOLUME_430_CUSTOM_SPLITS,
    431: VOLUME_431_CUSTOM_SPLITS,
    433: VOLUME_433_CUSTOM_SPLITS,
    434: VOLUME_434_CUSTOM_SPLITS,
    437: VOLUME_437_CUSTOM_SPLITS,
    439: VOLUME_439_CUSTOM_SPLITS,
    440: VOLUME_440_CUSTOM_SPLITS,
    441: VOLUME_441_CUSTOM_SPLITS,
    443: VOLUME_443_CUSTOM_SPLITS,
    444: VOLUME_444_CUSTOM_SPLITS,
    445: VOLUME_445_CUSTOM_SPLITS,
    446: VOLUME_446_CUSTOM_SPLITS,
    449: VOLUME_449_CUSTOM_SPLITS,
    450: VOLUME_450_CUSTOM_SPLITS,
    451: VOLUME_451_CUSTOM_SPLITS,
    453: VOLUME_453_CUSTOM_SPLITS,
    458: VOLUME_458_CUSTOM_SPLITS,
    459: VOLUME_459_CUSTOM_SPLITS,
    468: VOLUME_468_CUSTOM_SPLITS,
    485: VOLUME_485_CUSTOM_SPLITS,
    486: VOLUME_486_CUSTOM_SPLITS,
    494: VOLUME_494_CUSTOM_SPLITS,
    522: VOLUME_522_CUSTOM_SPLITS,
    527: VOLUME_527_CUSTOM_SPLITS,
    539: VOLUME_539_CUSTOM_SPLITS,
    540: VOLUME_540_CUSTOM_SPLITS,
    541: VOLUME_541_CUSTOM_SPLITS,
    608: VOLUME_608_CUSTOM_SPLITS,
    616: VOLUME_616_CUSTOM_SPLITS,
    685: VOLUME_685_CUSTOM_SPLITS,
    686: VOLUME_686_CUSTOM_SPLITS,
    690: VOLUME_690_CUSTOM_SPLITS,
    727: VOLUME_727_CUSTOM_SPLITS,
    740: VOLUME_740_CUSTOM_SPLITS,
    741: VOLUME_741_CUSTOM_SPLITS,
    745: VOLUME_745_CUSTOM_SPLITS,
    752: VOLUME_752_CUSTOM_SPLITS,
    754: VOLUME_754_CUSTOM_SPLITS,
    769: VOLUME_769_CUSTOM_SPLITS,
    770: VOLUME_770_CUSTOM_SPLITS,
    777: VOLUME_777_CUSTOM_SPLITS,
    785: VOLUME_785_CUSTOM_SPLITS,
    798: VOLUME_798_CUSTOM_SPLITS,
    800: VOLUME_800_CUSTOM_SPLITS,
    801: VOLUME_801_CUSTOM_SPLITS,
    804: VOLUME_804_CUSTOM_SPLITS,
    806: VOLUME_806_CUSTOM_SPLITS,
    807: VOLUME_807_CUSTOM_SPLITS,
    820: VOLUME_820_CUSTOM_SPLITS,
    826: VOLUME_826_CUSTOM_SPLITS,
    827: VOLUME_827_CUSTOM_SPLITS,
    830: VOLUME_830_CUSTOM_SPLITS,
    835: VOLUME_835_CUSTOM_SPLITS,
    842: VOLUME_842_CUSTOM_SPLITS,
    861: VOLUME_861_CUSTOM_SPLITS,
    862: VOLUME_862_CUSTOM_SPLITS,
    865: VOLUME_865_CUSTOM_SPLITS,
}


def get_multisong_split(volume_num: int, title: str, author: str,
                        poem_lines: list, num_songs: int) -> list:
    """
    Get multisong split for any volume using the data registry.

    This is the unified entry point that replaces all get_volume_N_split functions.

    Args:
        volume_num: Volume number
        title: Poem title
        author: Poem author
        poem_lines: List of poem lines
        num_songs: Expected number of songs

    Returns:
        List of split poem line lists, or None if no split configured
    """
    configs = MULTISONG_SPLITS_DATA.get(volume_num, [])

    for config in configs:
        # Check title pattern
        if config['title_pattern'] not in title:
            continue
        # Check line count
        if len(poem_lines) != config['line_count']:
            continue
        # Check num_songs
        if config['num_songs'] != num_songs:
            continue
        # Check author if specified (for disambiguation)
        if 'author' in config and author != config['author']:
            continue

        # Apply the splits
        return [poem_lines[start:end] for start, end in config['splits']]

    return None


def get_named_part_sets(volume_num: int) -> list:
    """
    Get named part sets configuration for any volume using the registry.

    This is the unified entry point that replaces the if-elif chain.

    Args:
        volume_num: Volume number

    Returns:
        List of named part set config dicts, or empty list if none configured
    """
    return NAMED_PART_SETS_REGISTRY.get(volume_num, [])


def get_custom_splits_for_volume(volume_num: int) -> dict:
    """
    Get custom splits configuration for a volume using the registry.

    Args:
        volume_num: Volume number

    Returns:
        Dict mapping (title, author) to split config, or empty dict if none
    """
    return CUSTOM_SPLITS_REGISTRY.get(volume_num, {})
