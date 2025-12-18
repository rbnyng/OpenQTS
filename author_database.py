"""
Author database for managing Tang Poems author metadata and biographies.

Maintains a separate JSON database of all authors encountered across volumes,
including biographies, to avoid duplication in poem records.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from models import Author
from utils import period_inference, gender_inference, education_inference, occupation_inference
from utils import wikipedia_bio_extraction

logger = logging.getLogger(__name__)

# Pairs of author names that should NOT be merged even if they share a Wikidata ID.
# This handles cases where Wikidata incorrectly conflates different historical figures.
# Format: frozenset of name pairs that should remain separate
WIKIDATA_MERGE_EXCLUSIONS = {
    # 李適 (Lǐ Shì) - Tang poet/official vs 李适 (Lǐ Kuò) - Emperor Dezong of Tang
    # These are different people with different pronunciations despite similar characters
    frozenset({'李適', '李适'}),
}


class AuthorDatabase:
    """
    Manages a database of Tang Dynasty poet metadata and biographies.
    
    Stores author information separately from poems to avoid duplication.
    Tracks biography sources and merges information from multiple volumes.
    """
    
    def __init__(self, filepath: str = 'output/authors.json'):
        """
        Initialize the author database.
        
        Args:
            filepath: Path to the authors JSON file
        """
        self.filepath = Path(filepath)
        self.authors: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.authors = json.load(f)
                logger.info(f"Loaded {len(self.authors)} authors from {self.filepath}")
            except Exception as e:
                logger.error(f"Error loading authors database: {e}")
                self.authors = {}
        else:
            logger.info(f"No existing authors database found at {self.filepath}")
            self.authors = {}

    def _find_by_wikidata_id(self, wikidata_id: str) -> Optional[str]:
        """
        Find an existing author entry by Wikidata ID.

        Args:
            wikidata_id: Wikidata Q-ID to search for

        Returns:
            Canonical name of the existing author, or None if not found
        """
        if not wikidata_id:
            return None
        for canonical_name, entry in self.authors.items():
            if entry.get('wikidata_id') == wikidata_id:
                return canonical_name
        return None
    
    def add_or_update_author(self, author: Author, biography: Optional[str] = None,
                            source_volume: Optional[int] = None,
                            bio_source: Optional[str] = None):
        """
        Add or update an author in the database.

        If the author already exists, merges new information with existing data.
        Biography sources are tracked to know which volumes provided biographical info.

        Also merges authors with the same Wikidata ID (e.g., 呂岩 and 呂嵓 are the same
        person with different character variants).

        Args:
            author: Author object with metadata
            biography: Biographical text (optional)
            source_volume: Volume number where this info came from (optional, legacy)
            bio_source: Source of biography - either "wikipedia" or will be set from source_volume
        """
        canonical = author.canonical

        # Check if there's an existing entry with the same Wikidata ID (different canonical name)
        # This handles variant characters for the same person (e.g., 呂岩/呂嵓)
        merged_into_existing = False
        if author.wikidata_id:
            existing_by_wikidata = self._find_by_wikidata_id(author.wikidata_id)
            if existing_by_wikidata and existing_by_wikidata != canonical:
                # Check if this pair is in the exclusion list (different people with same Wikidata ID)
                name_pair = frozenset({canonical, existing_by_wikidata})
                if name_pair in WIKIDATA_MERGE_EXCLUSIONS:
                    logger.info(
                        f"Skipping merge of '{canonical}' with '{existing_by_wikidata}' "
                        f"(exclusion: different people despite shared Wikidata ID {author.wikidata_id})"
                    )
                else:
                    # Found existing author with same Wikidata ID but different canonical name
                    # Merge into the existing entry and add this canonical as a variant
                    logger.info(
                        f"Merging author '{canonical}' into '{existing_by_wikidata}' "
                        f"(same Wikidata ID: {author.wikidata_id})"
                    )
                    entry = self.authors[existing_by_wikidata]
                    # Add the new canonical name as a variant
                    if canonical not in entry['recorded_variants']:
                        entry['recorded_variants'].append(canonical)
                    # Use the existing canonical name for storage
                    canonical = existing_by_wikidata
                    merged_into_existing = True

        # Get existing entry or create new one (if not already set by wikidata merge above)
        if not merged_into_existing:
            if canonical in self.authors:
                entry = self.authors[canonical]
            else:
                entry = {
                    'canonical': canonical,
                    'recorded_variants': [],
                    'biographies': []
                }
        
        # Add recorded name variant if not already present
        if author.recorded and author.recorded not in entry['recorded_variants']:
            entry['recorded_variants'].append(author.recorded)
        
        # Update metadata (prefer non-None values)
        if author.wikidata_id:
            entry['wikidata_id'] = author.wikidata_id
        if author.english_name:
            entry['english_name'] = author.english_name
        if author.birth_year:
            entry['birth_year'] = author.birth_year
        if author.death_year:
            entry['death_year'] = author.death_year
        if author.period:
            entry['period'] = author.period
        if author.period_source:
            entry['period_source'] = author.period_source
        if author.gender:
            entry['gender'] = author.gender
        if author.gender_source:
            entry['gender_source'] = author.gender_source
        if author.cbdb_id:
            entry['cbdb_id'] = author.cbdb_id
        if author.viaf_id:
            entry['viaf_id'] = author.viaf_id
        if author.loc_id:
            entry['loc_id'] = author.loc_id
        if author.birth_place:
            entry['birth_place'] = author.birth_place
        if author.death_place:
            entry['death_place'] = author.death_place
        if author.occupations:
            # Merge occupations
            existing_occs = set(entry.get('occupations', []))
            existing_occs.update(author.occupations)
            entry['occupations'] = sorted(list(existing_occs))
            # Track source as wikidata (or update to combined if we already have inferred ones)
            if entry.get('occupations_source') == 'inferred_biography':
                entry['occupations_source'] = 'wikidata+inferred_biography'
            elif not entry.get('occupations_source'):
                entry['occupations_source'] = 'wikidata'
        if author.academic_degree:
            entry['academic_degree'] = author.academic_degree
        if author.notable_works:
            # Merge notable works
            existing_works = set(entry.get('notable_works', []))
            existing_works.update(author.notable_works)
            entry['notable_works'] = sorted(list(existing_works))
        if author.wikipedia_url:
            entry['wikipedia_url'] = author.wikipedia_url
        if author.wikisource_url:
            entry['wikisource_url'] = author.wikisource_url
        if author.image_url:
            entry['image_url'] = author.image_url
        if author.style_names:
            # Merge style names
            existing_names = set(entry.get('style_names', []))
            existing_names.update(author.style_names)
            entry['style_names'] = sorted(list(existing_names))

        # Add biography if provided and not already present
        if biography:
            # Determine source - prefer explicit bio_source, then source_volume
            if bio_source:
                source = bio_source
            elif source_volume:
                source = f"volume_{source_volume}"
            else:
                source = "unknown"

            bio_entry = {
                'text': biography,
                'source': source
            }

            # Check if this exact biography already exists
            existing_bios = entry.get('biographies', [])
            if not any(b.get('text') == biography for b in existing_bios):
                existing_bios.append(bio_entry)
                entry['biographies'] = existing_bios
                logger.debug(f"Added biography for {canonical} from {source}")

            # Infer period from biography if not already set
            if not entry.get('period'):
                inferred_period, period_source = period_inference.infer_period_from_biography(biography)
                if inferred_period:
                    entry['period'] = inferred_period
                    entry['period_source'] = period_source
                    logger.debug(f"Inferred period for {canonical}: {inferred_period} ({period_source})")

            # Infer gender from biography if not already set
            if not entry.get('gender'):
                inferred_gender, gender_source = gender_inference.infer_gender_from_biography(biography)
                if inferred_gender:
                    entry['gender'] = inferred_gender
                    entry['gender_source'] = gender_source
                    logger.debug(f"Inferred gender for {canonical}: {inferred_gender} ({gender_source})")

            # Infer academic degree from biography if not already set
            if not entry.get('academic_degree'):
                inferred_degree, degree_source = education_inference.extract_education_from_biography(biography)
                if inferred_degree:
                    entry['academic_degree'] = inferred_degree
                    entry['academic_degree_source'] = degree_source
                    logger.debug(f"Inferred academic degree for {canonical}: {inferred_degree} ({degree_source})")

            # Extract occupations from biography and merge with existing occupations
            extracted_occupations = occupation_inference.extract_occupations_from_biography(biography)
            if extracted_occupations:
                existing_occs = set(entry.get('occupations', []))
                new_occs = set(extracted_occupations)
                merged_occs = existing_occs.union(new_occs)
                if merged_occs != existing_occs:
                    entry['occupations'] = sorted(list(merged_occs))
                    added_occs = new_occs - existing_occs
                    logger.debug(f"Extracted occupations for {canonical} from biography: {sorted(list(added_occs))}")

                # Track source (update to combined if we already have wikidata ones)
                current_source = entry.get('occupations_source')
                if current_source == 'wikidata':
                    entry['occupations_source'] = 'wikidata+inferred_biography'
                elif not current_source:
                    entry['occupations_source'] = 'inferred_biography'

            # For Wikipedia bios, extract additional structured information
            if bio_source == "wikipedia":
                wiki_data = wikipedia_bio_extraction.extract_all_from_biography(biography)

                # Birth/death years (only if not already set from Wikidata)
                if wiki_data['birth_year'] and not entry.get('birth_year'):
                    entry['birth_year'] = wiki_data['birth_year']
                    entry['birth_year_source'] = 'wikipedia'
                    logger.debug(f"Extracted birth year for {canonical} from Wikipedia: {wiki_data['birth_year']}")

                if wiki_data['death_year'] and not entry.get('death_year'):
                    entry['death_year'] = wiki_data['death_year']
                    entry['death_year_source'] = 'wikipedia'
                    logger.debug(f"Extracted death year for {canonical} from Wikipedia: {wiki_data['death_year']}")

                # Birthplace (only if not already set)
                if wiki_data['birthplace'] and not entry.get('birth_place'):
                    entry['birth_place'] = wiki_data['birthplace']
                    entry['birth_place_source'] = 'wikipedia'
                    logger.debug(f"Extracted birthplace for {canonical} from Wikipedia: {wiki_data['birthplace']}")

                # Courtesy names (字) - merge with existing style_names
                if wiki_data['courtesy_names']:
                    existing_names = set(entry.get('style_names', []))
                    new_names = set(wiki_data['courtesy_names'])
                    merged = existing_names.union(new_names)
                    if merged != existing_names:
                        entry['style_names'] = sorted(list(merged))
                        added = new_names - existing_names
                        logger.debug(f"Extracted courtesy names for {canonical} from Wikipedia: {sorted(list(added))}")

                # Art names (號) - merge with existing style_names
                if wiki_data['art_names']:
                    existing_names = set(entry.get('style_names', []))
                    new_names = set(wiki_data['art_names'])
                    merged = existing_names.union(new_names)
                    if merged != existing_names:
                        entry['style_names'] = sorted(list(merged))
                        added = new_names - existing_names
                        logger.debug(f"Extracted art names for {canonical} from Wikipedia: {sorted(list(added))}")

                # Alternate names - add to recorded_variants
                if wiki_data['alternate_names']:
                    existing_variants = entry.get('recorded_variants', [])
                    for alt_name in wiki_data['alternate_names']:
                        if alt_name not in existing_variants and alt_name != canonical:
                            existing_variants.append(alt_name)
                            logger.debug(f"Added alternate name for {canonical} from Wikipedia: {alt_name}")
                    entry['recorded_variants'] = existing_variants

        self.authors[canonical] = entry
    
    def get_author(self, canonical_name: str) -> Optional[Dict]:
        """
        Get author data by canonical name.
        
        Args:
            canonical_name: Canonical name of the author
            
        Returns:
            Author data dictionary, or None if not found
        """
        return self.authors.get(canonical_name)
    
    def save(self):
        # Ensure output directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.authors, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.authors)} authors to {self.filepath}")
        except Exception as e:
            logger.error(f"Error saving authors database: {e}")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the authors database.
        
        Returns:
            Dictionary with statistics
        """
        total_authors = len(self.authors)
        authors_with_bio = sum(1 for a in self.authors.values() if a.get('biographies'))
        authors_with_wikidata = sum(1 for a in self.authors.values() if a.get('wikidata_id'))
        
        return {
            'total_authors': total_authors,
            'authors_with_biography': authors_with_bio,
            'authors_with_wikidata': authors_with_wikidata,
            'filepath': str(self.filepath)
        }
