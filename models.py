"""
Data models for Complete Tang Poems scraper.

This module defines structured data types used throughout the scraper
to ensure type safety and consistency.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict


@dataclass
class Author:
    """represents a poem author with metadata."""

    canonical: str
    """canonical name from Author: link (URL-decoded)"""

    recorded: str
    """Name as displayed in the text"""

    wikidata_id: Optional[str] = None
    """wikidata Q-ID (e.g., 'Q9458')"""

    english_name: Optional[str] = None
    """English name from Wikidata"""

    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    period: Optional[str] = None
    period_source: Optional[str] = None
    """Source  of period information: 'wikidata', 'inferred_era_XXX', 'inferred_emperor_XXX'"""
    gender: Optional[str] = None
    gender_source: Optional[str] = None
    """Source of gender information: 'wikidata', 'inferred_female_marker:X', 'inferred_male_marker:X', 'inferred_volume_X'"""
    cbdb_id: Optional[str] = None
    """China Biographical Database ID"""

    viaf_id: Optional[str] = None
    """Virtual International Authority File ID"""

    loc_id: Optional[str] = None
    """Library of Congress authority ID"""

    birth_place: Optional[str] = None
    """Place of birth (label from Wikidata)"""

    death_place: Optional[str] = None
    """Place of death (label from Wikidata)"""

    occupations: List[str] = field(default_factory=list)
    """List of occupations (e.g., 'poet', 'politician', 'calligrapher')"""

    occupations_source: Optional[str] = None
    """source of occupations information: 'wikidata', 'inferred_biography', 'wikidata+inferred_biography'"""

    academic_degree: Optional[str] = None
    """Academic degree (e.g., 'jinshi', 'hongci')"""

    academic_degree_source: Optional[str] = None
    """Source of academic degree information: 'wikidata', 'inferred_education:XXX'"""

    notable_works: List[str] = field(default_factory=list)
    """List of notable works"""

    wikipedia_url: Optional[str] = None
    """English Wikipedia article URL"""

    zh_wikipedia_url: Optional[str] = None
    """Chinese Wikipedia article URL (Traditional Chinese)"""

    wikisource_url: Optional[str] = None
    """Chinese  Wikisource author page URL"""

    image_url: Optional[str] = None
    """Portrait/image  URL from Wikimedia Commons"""

    style_names: List[str] = field(default_factory=list)
    """List of Courtesy names (Zi) and Art names (Hao)"""

    def to_dict(self) -> Dict:
        # Combine birth/death into a formatted string for the JSON output
        data = {k: v for k, v in asdict(self).items() if v is not None}

        # Collapse empty lists
        for list_field in ['style_names', 'occupations', 'notable_works']:
            if list_field in data and not data[list_field]:
                del data[list_field]

        # Create the combined 'dates' field for cleaner JSON output
        if self.birth_year and self.death_year:
            data['dates'] = f"{self.birth_year}–{self.death_year}"
        elif self.birth_year:
            data['dates'] = f"{self.birth_year}–?"
        elif self.death_year:
            data['dates'] = f"?–{self.death_year}"

        return data

    def to_dict_minimal(self) -> Dict:
        """
        Convert to minimal dictionary for poem serialization.

        Includes only essential fields for self-contained poem usage:
        - canonical, recorded: name fields
        - gender, period: useful for filtering/analysis
        - english_name, wikidata_id: useful for lookups and non-Chinese readers
        """
        data = {
            'canonical': self.canonical,
            'recorded': self.recorded
        }

        # Add optional fields if present
        if self.gender:
            data['gender'] = self.gender
        if self.period:
            data['period'] = self.period
        if self.english_name:
            data['english_name'] = self.english_name
        if self.wikidata_id:
            data['wikidata_id'] = self.wikidata_id

        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Author':
        """Create Author from dictionary."""
        return cls(
            canonical=data.get('canonical', 'Unknown'),
            recorded=data.get('recorded', 'Unknown'),
            wikidata_id=data.get('wikidata_id'),
            english_name=data.get('english_name'),
            birth_year=data.get('birth_year'),
            death_year=data.get('death_year'),
            period=data.get('period'),
            period_source=data.get('period_source'),
            gender=data.get('gender'),
            gender_source=data.get('gender_source'),
            cbdb_id=data.get('cbdb_id'),
            viaf_id=data.get('viaf_id'),
            loc_id=data.get('loc_id'),
            birth_place=data.get('birth_place'),
            death_place=data.get('death_place'),
            occupations=data.get('occupations', []),
            occupations_source=data.get('occupations_source'),
            academic_degree=data.get('academic_degree'),
            academic_degree_source=data.get('academic_degree_source'),
            notable_works=data.get('notable_works', []),
            wikipedia_url=data.get('wikipedia_url'),
            zh_wikipedia_url=data.get('zh_wikipedia_url'),
            wikisource_url=data.get('wikisource_url'),
            image_url=data.get('image_url'),
            style_names=data.get('style_names', [])
        )
    
@dataclass
class Poem:
    """Represents a Tang Dynasty poem."""

    uid: str
    """unique identifier (format: QTS_VVV_EEE_PP)"""

    volume: int
    """Volume number (1-900)"""

    author: Author
    """Poem author with metadata"""

    title: str
    """Poem title"""

    poem: List[str]
    """List of poem lines"""

    notes: Optional[List[str]] = None
    """Editorial notes and annotations"""

    preface: Optional[str] = None
    """Authorial preface/序 providing context or background"""

    part_index: Optional[int] = None
    """Part number for multi-part poems (1-based)"""

    total_parts: Optional[int] = None
    """Total number of parts for multi-part poems"""

    variants: Optional[List[Dict]] = None
    """textual variants from different manuscript traditions"""

    # Internal note types that should be stripped from output
    INTERNAL_NOTE_TYPES = {'skip_autosplit'}

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            'uid': self.uid,
            'volume': self.volume,
            'author': self.author.to_dict_minimal(),
            'title': self.title,
            'poem': self.poem
        }

        if self.notes:
            # Filter out internal processing hints
            external_notes = [
                note for note in self.notes
                if not (isinstance(note, dict) and note.get('type') in self.INTERNAL_NOTE_TYPES)
            ]
            if external_notes:
                result['notes'] = external_notes
        if self.preface:
            result['preface'] = self.preface
        if self.part_index is not None:
            result['part_index'] = self.part_index
        if self.total_parts is not None:
            result['total_parts'] = self.total_parts
        if self.variants:
            result['variants'] = self.variants

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'Poem':
        """Create Poem from dictionary."""
        author_data = data.get('author', {})
        author = Author.from_dict(author_data) if isinstance(author_data, dict) else Author(
            canonical=str(author_data),
            recorded=str(author_data)
        )

        return cls(
            uid=data['uid'],
            volume=data['volume'],
            author=author,
            title=data['title'],
            poem=data['poem'],
            notes=data.get('notes'),
            preface=data.get('preface'),
            part_index=data.get('part_index'),
            total_parts=data.get('total_parts'),
            variants=data.get('variants')
        )


@dataclass
class VolumeMetadata:
    """Metadata about a volume."""

    volume_num: int
    """Volume number"""

    total_poems: int
    """Total number of poems in this volume"""

    multi_part_poems: int = 0
    """Number of multi-part poems"""

    format_type: str = "standard"
    """HTML format type used in this volume"""
