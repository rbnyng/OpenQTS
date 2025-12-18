"""
Period inference utilities for Tang Dynasty authors.

Infers historical period from:
1. Jinshi examination years in biographies
2. Era names (年號) in biographies or titles
3. Emperor/empress references in titles

Supports:
- Sui Dynasty (581-618)
- Tang Dynasty: Early/High/Middle/Late (618-907)
- Five Dynasties and Ten Kingdoms (907-979)
"""

import re
import logging
from typing import Optional, Tuple
from constants import PERIOD_RANGES

logger = logging.getLogger(__name__)

# Era Names (年號) with year ranges
# Includes Sui Dynasty, Tang Dynasty, and early Five Dynasties
# Source: Standard Chinese historical chronology
ERA_NAME_TO_YEARS = {
    # Sui Dynasty (581-618)
    '開皇': (581, 600),      # Kaihuang - Emperor Wen of Sui
    '仁壽': (601, 604),      # Renshou - Emperor Wen of Sui
    '大業': (605, 618),      # Daye - Emperor Yang of Sui

    # Early Tang (618-712)
    '武德': (618, 626),      # Wude - Emperor Gaozu
    '貞觀': (627, 649),      # Zhenguan - Emperor Taizong
    '永徽': (650, 655),      # Yonghui - Emperor Gaozong
    '顯慶': (656, 661),      # Xianqing - Emperor Gaozong
    '龍朔': (661, 663),      # Longshuo - Emperor Gaozong
    '麟德': (664, 665),      # Linde - Emperor Gaozong
    '乾封': (666, 668),      # Qianfeng - Emperor Gaozong
    '總章': (668, 670),      # Zongzhang - Emperor Gaozong
    '咸亨': (670, 674),      # Xianheng - Emperor Gaozong
    '上元': (674, 676),      # Shangyuan - Emperor Gaozong
    '儀鳳': (676, 679),      # Yifeng - Emperor Gaozong
    '調露': (679, 680),      # Tiaolu - Emperor Gaozong
    '永隆': (680, 681),      # Yonglong - Emperor Gaozong
    '開耀': (681, 682),      # Kaiyao - Emperor Gaozong
    '永淳': (682, 683),      # Yongchun - Emperor Gaozong
    '弘道': (683, 683),      # Hongdao - Emperor Gaozong
    '嗣聖': (684, 684),      # Sisheng - Emperor Zhongzong (brief)
    '文明': (684, 684),      # Wenming - Emperor Ruizong (brief)
    '光宅': (684, 684),      # Guangzhai - Empress Wu
    '垂拱': (685, 688),      # Chuigong - Empress Wu
    '永昌': (689, 689),      # Yongchang - Empress Wu
    '載初': (689, 690),      # Zaichu - Empress Wu
    '天授': (690, 692),      # Tianshou - Empress Wu
    '如意': (692, 692),      # Ruyi - Empress Wu
    '長壽': (692, 694),      # Changshou - Empress Wu
    '延載': (694, 694),      # Yanzai - Empress Wu
    '證聖': (695, 695),      # Zhengsheng - Empress Wu
    '天冊萬歲': (695, 696),  # Tiancewansui - Empress Wu
    '萬歲登封': (696, 696),  # Wansuidengfeng - Empress Wu
    '萬歲通天': (696, 697),  # Wansuitongtian - Empress Wu
    '神功': (697, 697),      # Shengong - Empress Wu
    '聖曆': (698, 700),      # Shengli - Empress Wu
    '久視': (700, 701),      # Jiushi - Empress Wu
    '大足': (701, 701),      # Dazu - Empress Wu
    '長安': (701, 704),      # Chang'an - Empress Wu
    '神龍': (705, 707),      # Shenlong - Emperor Zhongzong
    '景龍': (707, 710),      # Jinglong - Emperor Zhongzong
    '唐隆': (710, 710),      # Tanglong - Emperor Ruizong
    '景雲': (710, 712),      # Jingyun - Emperor Ruizong
    '太極': (712, 712),      # Taiji - Emperor Ruizong
    '延和': (712, 712),      # Yanhe - Emperor Ruizong

    # High Tang (713-765)
    '先天': (712, 713),      # Xiantian - Emperor Xuanzong
    '開元': (713, 741),      # Kaiyuan - Emperor Xuanzong (Golden Age)
    '天寶': (742, 756),      # Tianbao - Emperor Xuanzong
    '至德': (756, 758),      # Zhide - Emperor Suzong
    '乾元': (758, 760),      # Qianyuan - Emperor Suzong
    '上元': (760, 761),      # Shangyuan - Emperor Suzong
    '寶應': (762, 763),      # Baoying - Emperor Daizong
    '廣德': (763, 764),      # Guangde - Emperor Daizong
    '永泰': (765, 766),      # Yongtai - Emperor Daizong

    # Middle Tang (766-835)
    '大曆': (766, 779),      # Dali - Emperor Daizong
    '建中': (780, 783),      # Jianzhong - Emperor Dezong
    '興元': (784, 784),      # Xingyuan - Emperor Dezong
    '貞元': (785, 805),      # Zhenyuan - Emperor Dezong
    '永貞': (805, 805),      # Yongzhen - Emperor Shunzong
    '元和': (806, 820),      # Yuanhe - Emperor Xianzong
    '長慶': (821, 824),      # Changqing - Emperor Muzong
    '寶曆': (825, 827),      # Baoli - Emperor Jingzong
    '大和': (827, 835),      # Dahe - Emperor Wenzong
    '開成': (836, 840),      # Kaicheng - Emperor Wenzong

    # Late Tang (836-907)
    '會昌': (841, 846),      # Huichang - Emperor Wuzong
    '大中': (847, 860),      # Dazhong - Emperor Xuanzong
    '咸通': (860, 874),      # Xiantong - Emperor Yizong
    '乾符': (874, 879),      # Qianfu - Emperor Xizong
    '廣明': (880, 881),      # Guangming - Emperor Xizong
    '中和': (881, 885),      # Zhonghe - Emperor Xizong
    '光啟': (885, 888),      # Guangqi - Emperor Xizong
    '文德': (888, 888),      # Wende - Emperor Xizong
    '龍紀': (889, 889),      # Longji - Emperor Zhaozong
    '大順': (890, 891),      # Dashun - Emperor Zhaozong
    '景福': (892, 893),      # Jingfu - Emperor Zhaozong
    '乾寧': (894, 898),      # Qianning - Emperor Zhaozong
    '光化': (898, 901),      # Guanghua - Emperor Zhaozong
    '天復': (901, 904),      # Tianfu - Emperor Zhaozong
    '天祐': (904, 907),      # Tianyou - Emperor Ai

    # Five Dynasties and Ten Kingdoms (907-979)
    # Later Liang (後梁, 907-923)
    '開平': (907, 911),      # Kaiping - Emperor Taizu of Later Liang
    '乾化': (911, 915),      # Qianhua - Emperor Taizu/Moudi of Later Liang (interrupted)
    '鳳曆': (913, 915),      # Fengli - Emperor Moudi of Later Liang
    '貞明': (915, 921),      # Zhenming - Emperor Moudi of Later Liang
    '龍德': (921, 923),      # Longde - Emperor Modi of Later Liang

    # Later Tang (後唐, 923-936)
    '同光': (923, 926),      # Tongguang - Emperor Zhuangzong of Later Tang
    '天成': (926, 930),      # Tiancheng - Emperor Mingzong of Later Tang
    '長興': (930, 933),      # Changxing - Emperor Mingzong of Later Tang
    '應順': (934, 934),      # Yingshun - Emperor Mindi of Later Tang
    '清泰': (934, 936),      # Qingtai - Emperor Mindi of Later Tang

    # Later Jin (後晉, 936-947)
    '天福': (936, 944),      # Tianfu - Emperor Gaozu of Later Jin
    '開運': (944, 947),      # Kaiyun - Emperor Chudi of Later Jin

    # Later Han (後漢, 947-951)
    '天福': (947, 948),      # Tianfu - Emperor Gaozu of Later Han (reused era name)
    '乾祐': (948, 951),      # Qianyou - Emperor Yindi of Later Han

    # Later Zhou (後周, 951-960)
    '廣順': (951, 954),      # Guangshun - Emperor Taizu of Later Zhou
    '顯德': (954, 960),      # Xiande - Emperor Shizong/Gongdi of Later Zhou

    # Ten Kingdoms - Southern Tang (南唐, 937-975) - Li Yu's kingdom
    '昇元': (937, 943),      # Shengyuan - Li Bian
    '保大': (943, 957),      # Baoda - Li Jing
    '中興': (958, 958),      # Zhongxing - Li Jing
    '交泰': (958, 958),      # Jiaotai - Li Jing
    '建隆': (960, 963),      # Jianlong - Li Yu (overlaps with Song)
    '乾德': (963, 968),      # Qiande - Li Yu (overlaps with Song)
    '開寶': (968, 975),      # Kaibao - Li Yu (overlaps with Song)

    # Early Northern Song (960-979) - overlaps with Ten Kingdoms
    '建隆': (960, 963),      # Jianlong - Emperor Taizu of Song
    '乾德': (963, 968),      # Qiande - Emperor Taizu of Song
    '開寶': (968, 976),      # Kaibao - Emperor Taizu of Song
    '太平興國': (976, 984),  # Taiping Xingguo - Emperor Taizong of Song
}

# Emperor/Empress references with reign years
EMPEROR_TO_YEARS = {
    # Sui Dynasty Emperors
    '隋文帝': (581, 604),    # Emperor Wen of Sui (full title)
    '隋煬帝': (604, 618),    # Emperor Yang of Sui (full title)

    # Tang Dynasty Emperors by temple name (廟號)
    '高祖': (618, 626),      # Emperor Gaozu (Li Yuan)
    '太宗': (626, 649),      # Emperor Taizong (Li Shimin)
    '高宗': (649, 683),      # Emperor Gaozong
    '中宗': (684, 684, 705, 710),  # Emperor Zhongzong (two reigns)
    '睿宗': (684, 690, 710, 712),  # Emperor Ruizong (two reigns)
    '玄宗': (712, 756),      # Emperor Xuanzong
    '肅宗': (756, 762),      # Emperor Suzong
    '代宗': (762, 779),      # Emperor Daizong
    '德宗': (779, 805),      # Emperor Dezong
    '順宗': (805, 805),      # Emperor Shunzong
    '憲宗': (806, 820),      # Emperor Xianzong
    '穆宗': (820, 824),      # Emperor Muzong
    '敬宗': (824, 826),      # Emperor Jingzong
    '文宗': (827, 840),      # Emperor Wenzong
    '武宗': (840, 846),      # Emperor Wuzong
    '宣宗': (846, 859),      # Emperor Xuanzong (Dazhong era)
    '懿宗': (859, 873),      # Emperor Yizong
    '僖宗': (873, 888),      # Emperor Xizong
    '昭宗': (888, 904),      # Emperor Zhaozong
    '哀帝': (904, 907),      # Emperor Ai (last Tang emperor)

    # Special reference
    '武后': (690, 705),      # Empress Wu Zetian
}

# Chinese numerals for year parsing
CHINESE_NUMERALS = {
    '元': 1, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
}


def parse_chinese_year(year_str: str) -> Optional[int]:
    """
    Parse Chinese year number to integer.

    Examples:
        元 → 1
        二 → 2
        十 → 10
        十五 → 15
        二十 → 20

    Args:
        year_str: Chinese year string

    Returns:
        Year number or None if parsing fails
    """
    year_str = year_str.strip()

    if year_str in CHINESE_NUMERALS:
        return CHINESE_NUMERALS[year_str]

    # Handle compound numbers like 十五 (15), 二十 (20), 二十三 (23)
    if '十' in year_str:
        if year_str == '十':
            return 10
        elif year_str.startswith('十'):  # 十五 → 15
            ones = year_str[1:]
            return 10 + CHINESE_NUMERALS.get(ones, 0)
        elif year_str.endswith('十'):  # 二十 → 20
            tens = year_str[0]
            return CHINESE_NUMERALS.get(tens, 0) * 10
        else:  # 二十三 → 23
            parts = year_str.split('十')
            if len(parts) == 2:
                tens = CHINESE_NUMERALS.get(parts[0], 0)
                ones = CHINESE_NUMERALS.get(parts[1], 0)
                return tens * 10 + ones

    return None


def get_period_from_year(year: int) -> Optional[str]:
    """
    Get historical period from a year.

    Handles Sui Dynasty (581-618), Tang Dynasty (618-907),
    and Five Dynasties and Ten Kingdoms (907-979).

    Args:
        year: Year (e.g., 821)

    Returns:
        Period name or None
    """
    # Sui Dynasty
    if 581 <= year <= 618:
        return "Sui Dynasty"

    # Tang Dynasty (use existing PERIOD_RANGES)
    for period_name, start_year, end_year in PERIOD_RANGES:
        if start_year <= year <= end_year:
            return period_name

    # Five Dynasties and Ten Kingdoms (includes poets like Li Yu 李煜)
    # Extends to 979 when Northern Song unified China
    if 907 <= year <= 979:
        return "Five Dynasties and Ten Kingdoms"

    return None


def infer_period_from_biography(biography_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer period from biography text by extracting era names and years.

    Patterns matched:
    - XXX年進士 (jinshi in year XXX)
    - XXX元年進士第 (jinshi in 1st year of era XXX)
    - XXX二年 (2nd year of era XXX)
    - XXX時 (during emperor XXX's reign)

    Args:
        biography_text: Biography text

    Returns:
        Tuple of (period, period_source) or (None, None)
    """
    if not biography_text:
        return None, None

    # These are common patterns in biographies
    for emperor, years in EMPEROR_TO_YEARS.items():
        if emperor in biography_text[:100]:  # Check first 100 chars
            # Handle emperors with multiple reigns (use last reign)
            if len(years) == 2:
                start_year, end_year = years
            else:
                # Multiple reigns - use the latter one
                start_year, end_year = years[-2], years[-1]

            mid_year = (start_year + end_year) // 2
            period = get_period_from_year(mid_year)
            if period:
                source = f"inferred_emperor_{emperor}_biography"
                logger.debug(f"Inferred period from emperor in biography: {period} ({source})")
                return period, source

    # Pattern: Era name + year number + 年
    # Examples: 長慶元年, 開元二年, 天寶十五年
    pattern = r'([^，。；：\s]{2,4})([元一二三四五六七八九十]+)年'
    matches = re.findall(pattern, biography_text[:200])  # Check first 200 chars

    for era_name, year_str in matches:
        if era_name in ERA_NAME_TO_YEARS:
            # Parse the year number
            year_num = parse_chinese_year(year_str)
            if year_num:
                era_start, era_end = ERA_NAME_TO_YEARS[era_name]
                western_year = era_start + year_num - 1

                # Verify it's within the era range
                if era_start <= western_year <= era_end:
                    period = get_period_from_year(western_year)
                    if period:
                        source = f"inferred_era_{era_name}_{year_str}年_{western_year}"
                        logger.debug(f"Inferred period from biography: {period} ({source})")
                        return period, source

    # Also check for just era name without specific year
    for era_name, (era_start, era_end) in ERA_NAME_TO_YEARS.items():
        if era_name in biography_text[:100]:
            # Use midpoint of era for period assignment
            mid_year = (era_start + era_end) // 2
            period = get_period_from_year(mid_year)
            if period:
                source = f"inferred_era_{era_name}"
                logger.debug(f"Inferred period from era name in biography: {period} ({source})")
                return period, source

    return None, None


def infer_period_from_title(recorded_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer period from title/name based on imperial references.

    Patterns matched:
    - XXX宮人 (court lady of emperor/era XXX)
    - XXX妃 (consort of emperor XXX)
    - XXX朝 (dynasty/reign of emperor XXX)

    Args:
        recorded_name: Author's recorded name/title

    Returns:
        Tuple of (period, period_source) or (None, None)
    """
    if not recorded_name:
        return None, None

    for emperor, years in EMPEROR_TO_YEARS.items():
        if emperor in recorded_name:
            # Handle emperors with multiple reigns (use last reign)
            if len(years) == 2:
                start_year, end_year = years
            else:
                # Multiple reigns - use the latter one
                start_year, end_year = years[-2], years[-1]

            mid_year = (start_year + end_year) // 2
            period = get_period_from_year(mid_year)
            if period:
                source = f"inferred_emperor_{emperor}"
                logger.debug(f"Inferred period from title: {period} ({source})")
                return period, source

    for era_name, (era_start, era_end) in ERA_NAME_TO_YEARS.items():
        if era_name in recorded_name:
            mid_year = (era_start + era_end) // 2
            period = get_period_from_year(mid_year)
            if period:
                source = f"inferred_era_{era_name}_title"
                logger.debug(f"Inferred period from era in title: {period} ({source})")
                return period, source

    return None, None


def infer_period(biography_text: Optional[str] = None,
                recorded_name: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer Tang period from biography text and/or recorded name.

    Tries biography first (more precise), then falls back to title.

    Args:
        biography_text: Biography text
        recorded_name: Author's recorded name/title

    Returns:
        Tuple of (period, period_source) or (None, None)
    """
    if biography_text:
        period, source = infer_period_from_biography(biography_text)
        if period:
            return period, source

    # Fall back to title/name
    if recorded_name:
        period, source = infer_period_from_title(recorded_name)
        if period:
            return period, source

    return None, None
