"""
Gender inference utilities for Tang Poems authors.

Provides functions to infer gender from author names and titles when
Wikidata information is not available.
"""

import re
from typing import Optional, Tuple


# Female markers (high confidence)
FEMALE_MARKERS = [
    r'宮人',      # Palace women
    r'妻',        # Wife
    r'夫人',      # Lady
    r'妓',        # Courtesan/entertainer
    r'女子',      # Girl/woman
    r'女',        # Woman/daughter
    r'娘',        # Lady/maiden
    r'姬',        # Concubine/lady
    r'氏女',      # Daughter of (surname)
    r'婦',        # Woman/wife
    r'嬪',        # Imperial concubine
    r'妃',        # Consort
    r'后',        # Empress
]

# Male markers (high confidence)
MALE_MARKERS = [
    # Buddhist clergy
    r'僧',        # Monk
    r'釋',        # Buddhist monk
    r'沙門',      # Monk
    r'上人',      # Reverend

    # Daoist practitioners
    r'道士',      # Daoist priest
    r'真人',      # Immortal/adept
    r'仙',        # Immortal (when standalone)

    # Educational achievements (Tang Dynasty civil service exams were male-only)
    r'進士第一',  # Top jinshi degree (most specific first)
    r'擢進士第',  # Passed jinshi examination
    r'進士及第',  # Passed jinshi examination
    r'進士',      # Jinshi degree holder
    r'宏詞及第',  # Passed hongci examination
    r'明經',      # Ming jing degree
    r'秀才',      # Xiucai degree
    r'舉人',      # Juren degree
    r'登第',      # Passed examination
    r'及第',      # Passed examination

    # Central government officials
    r'宰相',      # Prime Minister
    r'丞相',      # Chancellor
    r'監察御史',  # Investigating Censor (more specific)
    r'殿中侍御史', # Palace Attendant Censor (more specific)
    r'侍御史',    # Palace Censor
    r'員外郎',    # Supernumerary Gentleman
    r'尚書',      # Minister
    r'侍郎',      # Vice Minister
    r'常侍',      # Palace Attendant
    r'學士',      # Academician
    r'郎中',      # Department Director
    r'員外',      # Supernumerary Official
    r'主簿',      # Registrar
    r'中書令',    # Secretariat Director
    r'門下侍中',  # Chancellery Vice Director
    r'中書舍人',  # Secretariat Drafter
    r'起居郎',    # Recorder of the Left
    r'起居舍人',  # Recorder of the Right
    r'校書郎',    # Collator (Palace Library)
    r'正字',      # Orthographer (Palace Library)
    r'中書',      # Secretariat
    r'門下',      # Chancellery
    r'翰林',      # Hanlin Academician
    r'諫議',      # Remonstrance Official
    r'諫議大夫',  # Remonstrance Official (more specific)
    r'補闕',      # Reminder
    r'拾遺',      # Omissioner
    r'給事中',    # Consultant
    r'散騎常侍',  # Cavalier Attendant-in-ordinary
    r'太常博士',  # Erudite of the Court of Imperial Sacrifices
    r'國子監',    # Directorate of Education
    r'國子博士',  # Erudite of the Imperial Academy
    r'祭酒',      # Libationer (head of academy)
    r'司業',      # Auxiliary in the Directorate of Education

    # Crown Prince (太子) household officials
    r'太子詹事',  # Grand Steward of the Crown Prince
    r'太子賓客',  # Guest of the Crown Prince (more specific than just 賓客)
    r'太子中允',  # Attendant Gentleman of the Crown Prince
    r'太子洗馬',  # Mounted Escort of the Crown Prince
    r'太子舍人',  # Palace Gentleman of the Crown Prince
    r'太子率更令', # Commandant of the Palace Guard (Crown Prince)

    # Regional and local officials
    r'觀察使',    # Regional Military Commissioner
    r'節度使',    # Military Governor
    r'刺史',      # Regional Inspector/Governor
    r'太守',      # Prefect
    r'京兆尹',    # Capital Administrator
    r'府尹',      # Prefecture Administrator
    r'郡守',      # Commandery Governor
    r'郡牧',      # Province Governor
    r'縣令',      # County Magistrate
    r'縣丞',      # County Vice Magistrate
    r'劇縣',      # Major county (position reference)
    r'丞',        # Vice Magistrate (general)

    # Military officials
    r'將軍',      # General
    r'都督',      # Military Governor
    r'司馬',      # Military Commissioner
    r'參軍',      # Military Advisor
    r'長史',      # Chief Administrator (military)
    r'校尉',      # Colonel
    r'都尉',      # Commandant
    r'龍武軍',    # Dragon Guard Army (unit reference)
    r'羽林',      # Feathered Forest Guard

    # Judicial and law enforcement
    r'司法',      # Judicial Official
    r'御史',      # Censor
    r'大理',      # Court of Judicial Review
    r'法曹',      # Legal official

    # Ministers and high officials (Nine Courts/九寺)
    r'衛尉卿',    # Minister of Guards
    r'太常卿',    # Minister of Ceremonies
    r'光祿卿',    # Minister of Imperial Banquets
    r'太僕卿',    # Minister of Imperial Stud
    r'大理卿',    # Minister of Justice
    r'鴻臚卿',    # Minister of State Ceremonies
    r'司農卿',    # Minister of Agriculture
    r'太府卿',    # Minister of Finance
    r'宗正卿',    # Minister of the Imperial Clan
    r'卿',        # Minister (general)
    r'少卿',      # Vice Minister
    r'丞',        # Vice Minister/Assistant (general)

    # Five Agencies (五監)
    r'國子祭酒',  # Director of the Directorate of Education
    r'將作監',    # Directorate of Palace Buildings
    r'軍器監',    # Directorate of Armaments
    r'都水監',    # Directorate of Waterways
    r'少監',      # Vice Director (of directorate)

    # Other specialized positions
    r'集賢院',    # Academy of Scholarly Worthies
    r'史館',      # Historiography Institute
    r'秘書監',    # Director of Palace Library
    r'秘書郎',    # Palace Library Official
    r'著作郎',    # Compiler
    r'著作佐郎',  # Assistant Compiler
    r'太醫令',    # Director of Imperial Medical Service
    r'太卜令',    # Director of Divination

    # Other official terms
    r'致仕',      # Retired official
    r'官',        # Official (when used as verb/title)
    r'賓客',      # Guest (official title like 太子賓客)
    r'使',        # Envoy/Commissioner (general)

    # Nobility titles (with end-of-string anchors to match only at end of name/phrase)
    r'太子',      # Crown Prince (compound, no anchor needed)
    r'王$',       # Prince/King (must be at end)
    r'公$',       # Duke (must be at end)
    r'侯$',       # Marquis (must be at end)
    r'伯$',       # Earl (must be at end)
    # Note: 子 (viscount) removed - too many false positives with honorifics (孔子, 孟子) and compounds (公子, 君子)
    r'帝$',       # Emperor (must be at end)
]


def infer_gender_from_name(recorded_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer gender from recorded author name based on explicit markers.
    
    Uses high-confidence patterns like titles, roles, and explicit gender markers
    to infer gender when Wikidata information is not available.
    
    Args:
        recorded_name: The author name as recorded in the text
        
    Returns:
        Tuple of (gender, source) where:
        - gender: "male", "female", or None if unable to infer
        - source: Description of inference method (e.g., "inferred_female_title")
    """
    if not recorded_name:
        return None, None
    
    # Check for female markers (higher priority - more specific)
    for marker in FEMALE_MARKERS:
        if re.search(marker, recorded_name):
            return "female", f"inferred_female_marker:{marker}"
    
    # Check for male markers
    for marker in MALE_MARKERS:
        if re.search(marker, recorded_name):
            return "male", f"inferred_male_marker:{marker}"
    
    # Unable to infer with high confidence
    return None, None


def infer_gender_from_biography(biography_text: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer gender from biography text based on official titles and roles.

    In Tang Dynasty China, official government positions were exclusively held by men.
    If a biography mentions official titles like 御史 (censor), 司法 (judicial official),
    刺史 (prefectural governor), etc., we can infer with high confidence that the
    person was male.

    Args:
        biography_text: Biography text to analyze

    Returns:
        Tuple of (gender, source) where:
        - gender: "male", "female", or None if unable to infer
        - source: Description of inference method with the matched marker
    """
    if not biography_text:
        return None, None

    # Check for female markers first (higher priority)
    for marker in FEMALE_MARKERS:
        if re.search(marker, biography_text):
            return "female", f"inferred_biography_female:{marker}"

    # Check for male markers (official titles, clergy, etc.)
    for marker in MALE_MARKERS:
        if re.search(marker, biography_text):
            return "male", f"inferred_biography_male:{marker}"

    # Unable to infer with high confidence
    return None, None


def infer_gender_from_volume(volume_num: int, recorded_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer gender based on volume number patterns.

    Certain volumes are dedicated to specific gender groups:
    - 卷797-805: Female poets (palace women, courtesans, named female poets)
    - 卷806-851: Buddhist clergy (predominantly male)
    - 卷852-862: Daoist practitioners (predominantly male)

    Args:
        volume_num: Volume number
        recorded_name: Author name (used to check for conflicting markers)

    Returns:
        Tuple of (gender, source)
    """
    # First check if name has explicit markers that override volume inference
    name_gender, name_source = infer_gender_from_name(recorded_name)
    if name_gender:
        return name_gender, name_source

    # Female-focused volumes
    if 797 <= volume_num <= 805:
        return "female", "inferred_volume_female"

    # Buddhist clergy volumes (predominantly male)
    if 806 <= volume_num <= 851:
        return "male", "inferred_volume_buddhist"

    # Daoist practitioner volumes (predominantly male)
    if 852 <= volume_num <= 862:
        return "male", "inferred_volume_daoist"

    # Unable to infer from volume
    return None, None
