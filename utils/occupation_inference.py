"""
Occupation extraction utilities for Tang Poems authors.

Extracts occupations from Chinese biography text based on official positions
and converts them to normalized English occupation categories.
"""

import re
from typing import Optional, List, Set

# Mapping of Chinese official positions to English occupation categories
# More specific positions first to ensure accurate matching
POSITION_TO_OCCUPATION = {
    # Educational/Academic positions
    r'校書郎': ['editor', 'librarian', 'scholar'],
    r'秘書監': ['librarian', 'scholar'],
    r'秘書郎': ['librarian', 'scholar'],
    r'正字': ['editor', 'librarian'],
    r'國子博士': ['educator', 'scholar'],
    r'國子祭酒': ['educator', 'scholar'],
    r'太常博士': ['scholar', 'ritualist'],
    r'祭酒': ['educator', 'scholar'],
    r'司業': ['educator'],
    r'著作郎': ['historian', 'scholar'],
    r'著作佐郎': ['historian', 'scholar'],
    r'史館': ['historian'],
    r'集賢院': ['scholar'],

    # Censors and surveillance
    r'監察御史': ['censor', 'government official'],
    r'殿中侍御史': ['censor', 'government official'],
    r'侍御史': ['censor', 'government official'],
    r'御史': ['censor', 'government official'],

    # Remonstrance officials
    r'諫議大夫': ['remonstrance official', 'government official'],
    r'諫議': ['remonstrance official', 'government official'],
    r'補闕': ['remonstrance official', 'government official'],
    r'拾遺': ['remonstrance official', 'government official'],
    r'給事中': ['consultant', 'government official'],

    # High ministers (Nine Courts)
    r'宰相': ['chancellor', 'government official'],
    r'丞相': ['chancellor', 'government official'],
    r'尚書': ['minister', 'government official'],
    r'侍郎': ['vice minister', 'government official'],
    r'衛尉卿': ['minister', 'military official'],
    r'太常卿': ['minister', 'ritualist'],
    r'光祿卿': ['minister', 'government official'],
    r'太僕卿': ['minister', 'government official'],
    r'大理卿': ['minister', 'judge'],
    r'鴻臚卿': ['minister', 'diplomat'],
    r'司農卿': ['minister', 'government official'],
    r'太府卿': ['minister', 'government official'],
    r'宗正卿': ['minister', 'government official'],

    # Secretariat and Chancellery
    r'中書令': ['government official'],
    r'門下侍中': ['government official'],
    r'中書舍人': ['government official', 'drafter'],
    r'起居郎': ['government official', 'recorder'],
    r'起居舍人': ['government official', 'recorder'],

    # Hanlin Academy
    r'翰林': ['academician', 'scholar'],
    r'學士': ['academician', 'scholar'],

    # Crown Prince household
    r'太子詹事': ['court official'],
    r'太子賓客': ['court official'],
    r'太子中允': ['court official'],
    r'太子洗馬': ['court official'],
    r'太子舍人': ['court official'],
    r'太子率更令': ['court official', 'military official'],

    # Regional officials
    r'觀察使': ['regional governor', 'government official'],
    r'節度使': ['regional governor', 'military official'],
    r'刺史': ['regional governor', 'government official'],
    r'太守': ['prefect', 'government official'],
    r'京兆尹': ['administrator', 'government official'],
    r'府尹': ['administrator', 'government official'],
    r'郡守': ['governor', 'government official'],
    r'郡牧': ['governor', 'government official'],
    r'縣令': ['magistrate', 'government official'],
    r'縣丞': ['magistrate', 'government official'],

    # Military positions
    r'將軍': ['general', 'military official'],
    r'都督': ['military governor', 'military official'],
    r'司馬': ['military official'],
    r'參軍': ['military official'],
    r'長史': ['military official', 'administrator'],
    r'校尉': ['military official'],
    r'都尉': ['military official'],
    r'龍武軍': ['military official'],
    r'羽林': ['military official'],

    # Judicial positions
    r'司法': ['judge', 'government official'],
    r'大理': ['judge', 'government official'],
    r'法曹': ['legal official', 'government official'],

    # Medical and divination
    r'太醫令': ['physician'],
    r'太卜令': ['diviner'],

    # General positions
    r'郎中': ['government official'],
    r'員外郎': ['government official'],
    r'員外': ['government official'],
    r'主簿': ['government official', 'registrar'],
    r'常侍': ['court official'],
    r'散騎常侍': ['court official'],
    r'賓客': ['court official'],
    r'使': ['envoy', 'government official'],

    # Buddhist and Daoist
    r'僧': ['monk', 'Buddhist monk'],
    r'釋': ['Buddhist monk'],
    r'沙門': ['Buddhist monk'],
    r'上人': ['Buddhist monk'],
    r'道士': ['Daoist priest'],
    r'真人': ['Daoist priest'],
}


def extract_occupations_from_biography(biography_text: Optional[str]) -> List[str]:
    """
    Extract occupation categories from biography text.

    Searches for official position titles in Chinese biography text
    and converts them to normalized English occupation categories.

    Args:
        biography_text: Biography text to analyze

    Returns:
        List of occupation categories (e.g., ["government official", "censor"])
        Returns empty list if no occupations detected

    Examples:
        "監察御史，與元稹同時。" -> ["censor", "government official"]
        "校書郎，貞元年間人。" -> ["librarian", "scholar"]
        "太子詹事，開元中人。" -> ["court official"]
    """
    if not biography_text:
        return []

    occupations: Set[str] = set()

    for pattern, occupation_list in POSITION_TO_OCCUPATION.items():
        if re.search(pattern, biography_text):
            occupations.update(occupation_list)

    # Convert to sorted list for consistent ordering
    return sorted(list(occupations))


def normalize_occupation_term(chinese_term: str) -> List[str]:
    """
    Normalize a Chinese position term to English occupation categories.

    Args:
        chinese_term: Chinese position term (e.g., "監察御史", "校書郎")

    Returns:
        List of occupation categories, or empty list if term not recognized
    """
    for pattern, occupation_list in POSITION_TO_OCCUPATION.items():
        if re.search(pattern, chinese_term):
            return occupation_list
    return []
