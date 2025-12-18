"""
Author metadata service for Complete Tang Poems scraper.

Handles fetching and caching author metadata from Wikisource and Wikidata.
"""

import logging
import re
import time
from typing import Optional, Tuple
from urllib.parse import quote, unquote
from bs4 import Tag

from models import Author
from http_client import HttpClient
from cache import PersistentCache
from utils import gender_inference, period_inference
from constants import (
    AUTHOR_URL_TEMPLATE,
    WIKIDATA_API_URL,
    DEFAULT_DELAY_SECONDS,
    WIKIDATA_PROP_BIRTH,
    WIKIDATA_PROP_DEATH,
    WIKIDATA_PROP_GENDER,
    WIKIDATA_PROP_CBDB_ID,
    WIKIDATA_PROP_COURTESY_NAME,
    WIKIDATA_PROP_PSEUDONYM,
    WIKIDATA_PROP_VIAF_ID,
    WIKIDATA_PROP_LOC_ID,
    WIKIDATA_PROP_BIRTH_PLACE,
    WIKIDATA_PROP_DEATH_PLACE,
    WIKIDATA_PROP_OCCUPATION,
    WIKIDATA_PROP_ACADEMIC_DEGREE,
    WIKIDATA_PROP_NOTABLE_WORK,
    WIKIDATA_PROP_IMAGE,
    GENDER_MAP,
    PERIOD_RANGES
)

logger = logging.getLogger(__name__)

# Hardcoded Wikidata ID overrides for authors where automatic lookup returns wrong results.
# This handles cases where Wikipedia/Wikisource redirects to a different person with similar name.
WIKIDATA_ID_OVERRIDES = {
    # 李適 (Lǐ Shì) - Tang dynasty poet/official, NOT Emperor Dezong (李适, Lǐ Kuò, Q9755)
    '李適': 'Q45502998',
}


def normalize_author_name(author_name: str) -> str:
    """
    Normalize author name by removing common title prefixes.

    Buddhist monks are often referred to with the "僧" (monk) prefix,
    but their canonical author pages use just the dharma name.

    Examples:
        "僧貫休" → "貫休"
        "僧齊己" → "齊己"
        "李白" → "李白" (no change)

    Args:
        author_name: Author name that may have title prefix

    Returns:
        Normalized author name with title prefix removed
    """
    if not author_name:
        return author_name

    # Strip Buddhist monk title "僧" if the name is 3+ characters
    # (to avoid stripping when "僧" is part of the actual name)
    if author_name.startswith('僧') and len(author_name) >= 3:
        return author_name[1:]  # Remove the first character

    return author_name


def parse_author_name(author_text: str) -> Tuple[str, str]:
    """
    Parse author name, handling special formats like ritual music attributions.

    Ritual music pieces often use format: "PieceName (ActualAuthor)"
    where PieceName is the musical piece and ActualAuthor is the composer.

    Returns canonical name (normalized, without title prefixes) and recorded name
    (as it appears in the text).

    Ignores volume section markers like "貫休（一）" where the content in
    parentheses is only Chinese numerals.

    Args:
        author_text: Author text from link or heading

    Returns:
        Tuple of (canonical_name, recorded_name)
        - canonical_name: Normalized name for lookups (e.g., "貫休" from "僧貫休")
        - recorded_name: Name as it appears in text (e.g., "僧貫休")

    Examples:
        "慶和 (趙光逢)" → ("趙光逢", "趙光逢")
        "（郭子儀）" → ("郭子儀", "郭子儀")  # Just parentheses
        "僧貫休" → ("貫休", "僧貫休")  # Monk title stripped from canonical
        "李白" → ("李白", "李白")
        "郊廟歌辭" → ("郊廟歌辭", "郊廟歌辭")
        "貫休（一）" → ("貫休（一）", "貫休（一）")  # Section marker, not author format
    """
    if not author_text:
        return author_text, author_text

    # Check for ONLY parenthetical content: "（AuthorName）"
    # This is common in ritual music volumes where the link text is just the author
    match_only_parens = re.fullmatch(r'[（(]([^）)]+)[）)]', author_text.strip())
    if match_only_parens:
        content = match_only_parens.group(1).strip()
        if not re.fullmatch(r'[一二三四五六七八九十百千萬]+', content):
            canonical = normalize_author_name(content)
            return canonical, content
        # if it is a section marker, return as-is
        return author_text, author_text

    # Check for parenthetical author format: "PieceName (ActualAuthor)"
    # Match pattern: any text followed by space and content in parentheses
    match = re.search(r'^(.+?)\s*[（(]([^）)]+)[）)]$', author_text)

    if match:
        content_in_parens = match.group(2).strip()

        # Check if content is only Chinese numerals (section marker)
        # chinese numerals: 一二三四五六七八九十百千萬
        if re.fullmatch(r'[一二三四五六七八九十百千萬]+', content_in_parens):
            # Return the full text as-is
            return author_text, author_text

        # Check if content looks like a note/annotation rather than an author name
        # common annotation patterns: 原註:..., 一作..., 并序, 序, etc.
        # These should NOT be extracted as the author name
        note_patterns = [
            r'^原註[：:]',        # Editorial note: "原註：..."
            r'^一作',             # Variant: "一作..."
            r'^作',               # Variant: "作..."
            r'^并序$',            # Preface marker: "并序"
            r'^序$',              # Preface marker: "序"
            r'^自.*?至',          # Geographic/time note: "自京竄至鳳翔"
        ]
        if any(re.search(pattern, content_in_parens) for pattern in note_patterns):
            # Return the full text as-is (don't extract the parenthetical content)
            return author_text, author_text

        # Exract the name in parentheses - normalize for canonical, keep original for recorded
        canonical = normalize_author_name(content_in_parens)
        return canonical, content_in_parens

    # No parentheses found - normalize for canonical, keep original for recorded
    canonical = normalize_author_name(author_text)
    return canonical, author_text


class AuthorMetadataService:
    """
    Service for fetching and caching author metadata.

    Fetches canonical names, Wikidata IDs, and English names for poem authors.
    Uses persistent caching to avoid redundant API requests.
    """

    def __init__(self, http_client: HttpClient, cache: Optional[PersistentCache] = None):
        """
        Initialize the author metadata service.

        Args:
            http_client: HTTP client for making requests
            cache: Persistent cache for author metadata (creates new if None)
        """
        self.http_client = http_client
        self.cache = cache or PersistentCache()

    def extract_author_from_element(self, element: Tag) -> tuple[Optional[str], Optional[str]]:
        """
        Extract both canonical and recorded author names from an HTML element.

        Handles special formats like ritual music: "PieceName (ActualAuthor)"

        Args:
            element: BeautifulSoup Tag element containing author information

        Returns:
            Tuple of (canonical_name, recorded_name)
            - Both are the actual author's name (extracted from parentheses if needed)
        """
        # Try to extract canonical name from an Author: link if present
        link = element.find('a')
        has_author_link = False
        recorded_name = None
        canonical_name = None

        if link:
            href = link.get('href', '')

            if 'Author:' in href:
                has_author_link = True
                author_part = href.split('Author:')[-1]
                # remove any anchors or query params
                # For redlinks: /w/index.php?title=Author:NAME&action=edit&redlink=1
                # For normal links: /wiki/Author:NAME or /wiki/Author:NAME#section
                author_part = author_part.split('#')[0].split('?')[0].split('&')[0]
                # URL decode
                canonical_name = unquote(author_part)

                # Remove disambiguation suffixes like "_(唐)" or "_(五代)"
                # These are used in Wikisource URLs to distinguish people with same names
                # Pattern: underscore followed by parenthesized text at end
                canonical_name = re.sub(r'_\([^)]+\)$', '', canonical_name)

                # For Author: links, always parse the canonical name to extract
                # the actual person name from ritual music format like "PieceName（Author）"
                canonical_name, _ = parse_author_name(canonical_name)

                # For recorded name, use the link text (which may be just "（Author）")
                # or fall back to full element text
                link_text = link.get_text(strip=True)
                if link_text:
                    recorded_name, _ = parse_author_name(link_text)
                else:
                    # Fallback to full element text
                    recorded_name = element.get_text(strip=True)
                    recorded_name, _ = parse_author_name(recorded_name)
            else:
                # No Author: link - return None to let caller extract full text with their own logic
                canonical_name = None
                recorded_name = None
        else:
            # No link at all - return None to let caller extract full text with their own logic
            canonical_name = None
            recorded_name = None

        # In  volumes like 808, section headings have format "慧淨著" meaning "composed by Huijing"
        # the "著" is part of the heading format, not the actual author name
        #
        # IMPORTANT: For very short names (1 char without 著), the 著 might be part of the actual name
        # example: "曹著" could be a person's name, not "曹" with "authored by" marker
        # For 2+ char names, the 著 is just "authored by" (2-char names like 李白, 杜甫 are very common)
        # Example: "慧淨著" means "authored by 慧淨", so strip to "慧淨"

        if canonical_name and canonical_name.endswith('著'):
            name_without_zhu = canonical_name[:-1]
            # Keep 著 only if the name would be very short (1 char) without it
            if len(name_without_zhu) >= 2:
                canonical_name = name_without_zhu
            # else: keep the 著 as part of the name (e.g., 曹著)

        if recorded_name and recorded_name.endswith('著'):
            name_without_zhu = recorded_name[:-1]
            # Keep 著 only if the name would be very short (1 char) without it
            if len(name_without_zhu) >= 2:
                recorded_name = name_without_zhu
            # else: keep the 著 as part of the name (e.g., 曹著)

        return canonical_name, recorded_name

    def get_author_details(self, wikidata_id):
        """
        Fetch comprehensive author metadata from Wikidata.

        Retrieves English name, dates, gender, CBDB ID, and style names in one call.
        """
        cache_key = f"details:{wikidata_id}"
        if self.cache.has(cache_key):
            cached_value = self.cache.get(cache_key)
            logger.debug(f"Cache hit for details {wikidata_id}")
            return cached_value

        # Default empty result
        result = {
            'english_name': None,
            'birth_year': None,
            'death_year': None,
            'period': None,
            'gender': None,
            'cbdb_id': None,
            'viaf_id': None,
            'loc_id': None,
            'birth_place': None,
            'death_place': None,
            'occupations': [],
            'academic_degree': None,
            'notable_works': [],
            'wikipedia_url': None,
            'zh_wikipedia_url': None,
            'wikisource_url': None,
            'image_url': None,
            'style_names': []
        }

        try:
            params = {
                'action': 'wbgetentities',
                'ids': wikidata_id,
                'props': 'labels|claims|sitelinks',  # Fetch labels, claims, and sitelinks
                'languages': 'en|zh',  # English and Chinese
                'format': 'json'
            }

            data = self.http_client.fetch_json(WIKIDATA_API_URL, params=params)

            if not data or 'entities' not in data or wikidata_id not in data['entities']:
                self.cache.set(cache_key, result)
                return result

            entity = data['entities'][wikidata_id]

            if 'labels' in entity and 'en' in entity['labels']:
                result['english_name'] = entity['labels']['en']['value']

            claims = entity.get('claims', {})

            # Dates
            result['birth_year'] = self._extract_year(claims.get(WIKIDATA_PROP_BIRTH))
            result['death_year'] = self._extract_year(claims.get(WIKIDATA_PROP_DEATH))
            
            # Period Calculation
            result['period'] = self._calculate_period(result['birth_year'], result['death_year'])

            # Gender
            if WIKIDATA_PROP_GENDER in claims:
                try:
                    q_id = claims[WIKIDATA_PROP_GENDER][0]['mainsnak']['datavalue']['value']['id']
                    result['gender'] = GENDER_MAP.get(q_id)
                except (KeyError, IndexError, TypeError):
                    pass

            # CBDB ID
            if WIKIDATA_PROP_CBDB_ID in claims:
                try:
                    result['cbdb_id'] = claims[WIKIDATA_PROP_CBDB_ID][0]['mainsnak']['datavalue']['value']
                except (KeyError, IndexError, TypeError):
                    pass

            # Style Names (Zi/Hao) - Collect unique values
            names = set()
            self._extract_strings_to_set(claims.get(WIKIDATA_PROP_COURTESY_NAME), names)
            self._extract_strings_to_set(claims.get(WIKIDATA_PROP_PSEUDONYM), names)
            result['style_names'] = sorted(list(names))

            # VIAF ID
            if WIKIDATA_PROP_VIAF_ID in claims:
                try:
                    result['viaf_id'] = claims[WIKIDATA_PROP_VIAF_ID][0]['mainsnak']['datavalue']['value']
                except (KeyError, IndexError, TypeError):
                    pass

            # Library of Congress ID
            if WIKIDATA_PROP_LOC_ID in claims:
                try:
                    result['loc_id'] = claims[WIKIDATA_PROP_LOC_ID][0]['mainsnak']['datavalue']['value']
                except (KeyError, IndexError, TypeError):
                    pass

            # Collect all Q-IDs that need labels
            q_ids_to_fetch = []
            q_ids_to_fetch.extend(self._extract_q_ids(claims.get(WIKIDATA_PROP_BIRTH_PLACE)))
            q_ids_to_fetch.extend(self._extract_q_ids(claims.get(WIKIDATA_PROP_DEATH_PLACE)))
            q_ids_to_fetch.extend(self._extract_q_ids(claims.get(WIKIDATA_PROP_OCCUPATION)))
            q_ids_to_fetch.extend(self._extract_q_ids(claims.get(WIKIDATA_PROP_ACADEMIC_DEGREE)))
            q_ids_to_fetch.extend(self._extract_q_ids(claims.get(WIKIDATA_PROP_NOTABLE_WORK)))

            # Batch fetch labels for all Q-IDs
            label_cache = self._batch_fetch_labels(q_ids_to_fetch) if q_ids_to_fetch else {}

            # Birth place (get label)
            result['birth_place'] = self._extract_place_label(claims.get(WIKIDATA_PROP_BIRTH_PLACE), label_cache)

            # Death place (get label)
            result['death_place'] = self._extract_place_label(claims.get(WIKIDATA_PROP_DEATH_PLACE), label_cache)

            # Occupations (get labels)
            result['occupations'] = self._extract_item_labels(claims.get(WIKIDATA_PROP_OCCUPATION), label_cache)

            # Academic degree (get first label)
            if WIKIDATA_PROP_ACADEMIC_DEGREE in claims:
                degree_labels = self._extract_item_labels(claims.get(WIKIDATA_PROP_ACADEMIC_DEGREE), label_cache)
                if degree_labels:
                    result['academic_degree'] = degree_labels[0]

            # Notable works (get labels)
            result['notable_works'] = self._extract_item_labels(claims.get(WIKIDATA_PROP_NOTABLE_WORK), label_cache)

            # Image URL
            if WIKIDATA_PROP_IMAGE in claims:
                try:
                    filename = claims[WIKIDATA_PROP_IMAGE][0]['mainsnak']['datavalue']['value']
                    result['image_url'] = self._get_commons_url(filename)
                except (KeyError, IndexError, TypeError):
                    pass

            sitelinks = entity.get('sitelinks', {})

            # English Wikipedia
            if 'enwiki' in sitelinks:
                title = sitelinks['enwiki']['title']
                result['wikipedia_url'] = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"

            # Chinese Wikisource author page
            if 'zhwikisource' in sitelinks:
                title = sitelinks['zhwikisource']['title']
                result['wikisource_url'] = f"https://zh.wikisource.org/wiki/{quote(title)}"

            # Chinese Wikipedia (Traditional Chinese)
            if 'zhwiki' in sitelinks:
                title = sitelinks['zhwiki']['title']
                result['zh_wikipedia_url'] = f"https://zh.wikipedia.org/zh-hant/{quote(title)}"

            logger.debug(f"Fetched details for {wikidata_id}: {result}")
            self.cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.warning(f"Error fetching details from Wikidata for {wikidata_id}: {e}")
            return result

    def _extract_strings_to_set(self, claim_list, target_set):
        """helper to extract string values from claims into a set."""
        if not claim_list:
            return

        for claim in claim_list:
            try:
                val = claim['mainsnak']['datavalue']['value']
                # Sometimes it's a simple string, sometimes a monolingual text dict
                if isinstance(val, dict) and 'text' in val:
                    target_set.add(val['text'])
                elif isinstance(val, str):
                    target_set.add(val)
            except (KeyError, IndexError, TypeError):
                continue

    def _extract_q_ids(self, claim_list):
        q_ids = []
        if not claim_list:
            return q_ids

        for claim in claim_list:
            try:
                q_id = claim['mainsnak']['datavalue']['value']['id']
                if q_id and q_id.startswith('Q'):
                    q_ids.append(q_id)
            except (KeyError, IndexError, TypeError):
                continue

        return q_ids

    def _batch_fetch_labels(self, q_ids):
        """
        Fetch labels for multiple Q-IDs in a single API call.

        Args:
            q_ids: List of Wikidata Q-IDs

        Returns:
            Dictionary mapping Q-ID to label (English or Chinese)
        """
        if not q_ids:
            return {}

        # wikidata API has a limit of ~50 entities per request
        # for safety, batch in groups of 50
        labels = {}

        for i in range(0, len(q_ids), 50):
            batch = q_ids[i:i+50]
            batch_str = '|'.join(batch)

            try:
                params = {
                    'action': 'wbgetentities',
                    'ids': batch_str,
                    'props': 'labels',
                    'languages': 'en|zh',  # Prefer English, fallback to Chinese
                    'format': 'json'
                }

                data = self.http_client.fetch_json(WIKIDATA_API_URL, params=params)

                if data and 'entities' in data:
                    for q_id, entity in data['entities'].items():
                        if 'labels' in entity:
                            # Prefer English label, fallback to Chinese
                            if 'en' in entity['labels']:
                                labels[q_id] = entity['labels']['en']['value']
                            elif 'zh' in entity['labels']:
                                labels[q_id] = entity['labels']['zh']['value']

            except Exception as e:
                logger.warning(f"Error batch fetching labels for {batch}: {e}")
                continue

        return labels

    def _extract_place_label(self, claim_list, label_cache=None):
        """Extract place label from a place claim (returns first match)."""
        if not claim_list:
            return None

        try:
            q_id = claim_list[0]['mainsnak']['datavalue']['value']['id']
            if label_cache and q_id in label_cache:
                return label_cache[q_id]
        except (KeyError, IndexError, TypeError):
            pass

        return None

    def _extract_item_labels(self, claim_list, label_cache=None):
        """Extract labels from item claims (e.g., occupations, works)."""
        if not claim_list:
            return []

        labels = []
        for claim in claim_list:
            try:
                q_id = claim['mainsnak']['datavalue']['value']['id']
                if label_cache and q_id in label_cache:
                    labels.append(label_cache[q_id])
            except (KeyError, IndexError, TypeError):
                continue

        return labels

    def _get_commons_url(self, filename):
        """Convert  Wikimedia Commons filename to URL."""
        import hashlib
        # MD5 hash of filename for URL structure
        md5 = hashlib.md5(filename.replace(' ', '_').encode('utf-8')).hexdigest()
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}"

    def _extract_year(self, claim_list):
        """Parse Wikidata time string (e.g., '+0701-00-00T00:00:00Z') -> 701."""
        if not claim_list:
            return None
        
        try:
            time_str = claim_list[0]['mainsnak']['datavalue']['value']['time']
            match = re.search(r'^\+?0*(\d+)-', time_str)
            if match:
                return int(match.group(1))
        except (KeyError, IndexError, TypeError):
            pass
        return None
    
    def _calculate_period(self, birth, death):
        """Determine Tang period based on life midpoint."""
        target_year = None
        
        if birth and death:
            target_year = (birth + death) // 2
        elif birth:
            target_year = birth + 30 # Approx peak activity
        elif death:
            target_year = death - 30
            
        if not target_year:
            return None

        for period_name, start, end in PERIOD_RANGES:
            if start <= target_year <= end:
                return period_name
        
        # fallback for pre/post Tang
        if target_year < 618:
            return "Pre-Tang"
        if target_year > 907:
            return "Five Dynasties / Song"
            
        return None
    
    def get_wikidata_id_from_wikipedia(self, canonical_name: str) -> Optional[str]:
        """
        Try to fetch Wikidata ID from Chinese Wikipedia as fallback.

        When Wikisource doesn't have a linked author page, Wikipedia often does.
        Also performs basic verification that the article is about a Tang Dynasty person.

        Args:
            canonical_name: Canonical author name

        Returns:
            Wikidata Q-ID (e.g., 'Q8070523') or None if not found
        """
        # Try Chinese Wikipedia URL
        wikipedia_url = f"https://zh.wikipedia.org/zh-hant/{quote(canonical_name)}"

        logger.debug(f"Trying Wikipedia fallback for {canonical_name}: {wikipedia_url}")
        soup = self.http_client.fetch_page(wikipedia_url)

        if soup is None:
            return None

        # Look for Wikidata link in the sidebar (same format as Wikisource)
        wikidata_link = soup.find('a', href=re.compile(r'https://www\.wikidata\.org/wiki/Q\d+'))
        if not wikidata_link:
            return None

        href = wikidata_link.get('href', '')
        match = re.search(r'Q\d+', href)
        if not match:
            return None

        wikidata_id = match.group(0)

        # Basic semantic check: verify the article mentions relevant dynasties to reduce false positives
        # (e.g., ensure we don't mtach a modern person with the same name)
        page_text = soup.get_text()
        relevant_dynasties = ['唐', '隋', '五代']  # Tang, Sui, Five Dynasties
        if not any(dynasty in page_text[:2000] for dynasty in relevant_dynasties):
            logger.debug(f"Wikipedia article for {canonical_name} doesn't mention Tang/Sui/Five Dynasties, skipping")
            return None

        logger.info(f"Found Wikidata ID from Wikipedia for {canonical_name}: {wikidata_id}")
        return wikidata_id

    def get_wikipedia_biography(self, canonical_name: str, wikipedia_url: Optional[str] = None) -> Optional[str]:
        """
        Fetch biography from Chinese Wikipedia for an author.

        Extracts the first paragraph (lead section) from the Wikipedia article,
        which typically contains biographical information like birth/death years,
        courtesy names, origin, and notable achievements.

        Args:
            canonical_name: Canonical author name (used for cache key and fallback URL)
            wikipedia_url: Optional explicit Wikipedia URL (from Wikidata). If provided,
                          uses this URL instead of constructing one from the name.

        Returns:
            Biography text or None if not found/not relevant

        Example output:
            "李澣（？—962年），又作李瀚。字日新。京兆萬年（今陝西西安）人，五代十國、遼代文學家，李濤的弟弟。"
        """
        cache_key = f"wiki_bio:{canonical_name}"
        if self.cache.has(cache_key):
            cached = self.cache.get(cache_key)
            logger.debug(f"Cache hit for Wikipedia bio: {canonical_name}")
            return cached if cached else None

        # Use provided URL or construct from name
        if not wikipedia_url:
            wikipedia_url = f"https://zh.wikipedia.org/zh-hant/{quote(canonical_name)}"
        logger.debug(f"Fetching Wikipedia biography for {canonical_name}: {wikipedia_url}")

        soup = self.http_client.fetch_page(wikipedia_url)
        if soup is None:
            self.cache.set(cache_key, "")
            return None

        # Basic semantic check: verify the article mentions relevant dynasties
        page_text = soup.get_text()
        relevant_dynasties = ['唐', '隋', '五代', '宋']
        if not any(dynasty in page_text[:2000] for dynasty in relevant_dynasties):
            logger.debug(f"Wikipedia article for {canonical_name} doesn't mention relevant dynasties, skipping bio")
            self.cache.set(cache_key, "")
            return None

        # Find the content div (mw-parser-output contains main article content)
        content_div = soup.find('div', class_='mw-parser-output')
        if not content_div:
            self.cache.set(cache_key, "")
            return None

        # Find the first <p> tag that has substantial content
        # Skip empty paragraphs, coordinate info, etc.
        bio_text = None
        for p_tag in content_div.find_all('p', recursive=False):
            # Skip paragraphs that are just coordinates or empty
            text = p_tag.get_text(strip=True)
            if len(text) < 20:
                continue
            # Skip if it's just a disambiguation notice
            if '消歧義' in text or '重定向' in text:
                continue
            # Found a substantial paragraph - this is likely the bio
            bio_text = text
            break

        if not bio_text:
            self.cache.set(cache_key, "")
            return None

        # Clean up the text
        # Remove citation/footnote markers like [1], [2], [a], [b], [需要更多來源], etc.
        bio_text = re.sub(r'\[[^\]]*\]', '', bio_text)
        # Remove excessive whitespace
        bio_text = ' '.join(bio_text.split())

        # Skip surname/family name pages (百家姓)
        # These are about the surname itself, not a specific person
        surname_indicators = ['姓為', '百家姓', '複姓', '單姓', '姓氏', '漢字姓氏', '中國姓氏']
        if any(indicator in bio_text[:100] for indicator in surname_indicators):
            logger.debug(f"Wikipedia article for {canonical_name} is about a surname, not a person, skipping")
            self.cache.set(cache_key, "")
            return None

        # Validate it looks like a biography (should mention the person's name or have biographical markers)
        bio_markers = ['字', '號', '人', '年', '生', '卒', '詩人', '官', '進士']
        if not any(marker in bio_text for marker in bio_markers):
            logger.debug(f"Wikipedia text for {canonical_name} doesn't look like a biography, skipping")
            self.cache.set(cache_key, "")
            return None

        logger.info(f"Fetched Wikipedia biography for {canonical_name}: {bio_text[:60]}...")
        self.cache.set(cache_key, bio_text)
        return bio_text

    def get_wikidata_id(self, canonical_name: str) -> Optional[str]:
        """
        Fetch Wikidata ID from author's Wikisource page.

        Args:
            canonical_name: Canonical author name

        Returns:
            Wikidata Q-ID (e.g., 'Q9458') or None if not found

        Uses cache to avoid duplicate requests. For 404 errors (author page
        doesn't exist), retries once then caches None to avoid future lookups.
        """
        # check hardcoded overrides first (for names where automatic lookup is wrong)
        if canonical_name in WIKIDATA_ID_OVERRIDES:
            wikidata_id = WIKIDATA_ID_OVERRIDES[canonical_name]
            logger.info(f"Using hardcoded Wikidata ID override for {canonical_name}: {wikidata_id}")
            return wikidata_id

        # then chekc cache
        cache_key = f"wikidata:{canonical_name}"
        if self.cache.has(cache_key):
            cached_value = self.cache.get(cache_key)
            logger.debug(f"Cache hit for {canonical_name}: {cached_value}")
            return cached_value

        author_url = AUTHOR_URL_TEMPLATE.format(quote(canonical_name))

        for attempt in range(2):  # Try twice (initial + 1 retry)
            soup = self.http_client.fetch_page(author_url)

            if soup is None:
                if attempt == 0:
                    logger.debug(f"Author page fetch failed, retrying once: {canonical_name}")
                    time.sleep(1)  # Brief wait before retry
                    continue
                else:
                    logger.debug(f"Author page confirmed missing: {canonical_name}")
                    # Don't return yet - try Wikipedia fallback
                    break

            # Look for wikidata link in the sidebar
            # Format: <a href="https://www.wikidata.org/wiki/Q11095411">
            wikidata_link = soup.find('a', href=re.compile(r'https://www\.wikidata\.org/wiki/Q\d+'))
            if wikidata_link:
                href = wikidata_link.get('href', '')
                match = re.search(r'Q\d+', href)
                if match:
                    wikidata_id = match.group(0)
                    self.cache.set(cache_key, wikidata_id)
                    logger.debug(f"Found Wikidata ID for {canonical_name}: {wikidata_id}")
                    return wikidata_id

            # Page exists but no Wikidata link found - try Wikipedia fallback
            break

        # If Wikisource didn't have the ID, try Wikipedia as fallback
        wikidata_id = self.get_wikidata_id_from_wikipedia(canonical_name)
        if wikidata_id:
            self.cache.set(cache_key, wikidata_id)
            return wikidata_id

        # No Wikidata ID found from either source
        self.cache.set(cache_key, None)
        return None

    def create_author(self, canonical_name: Optional[str], recorded_name: Optional[str],
                     volume_num: Optional[int] = None) -> Author:
        """
        Create Author object with full metadata.

        Fetches Wikidata ID and English name if canonical name is provided.
        If Wikidata info is not available, applies gender inference based on
        name markers and volume patterns.

        Args:
            canonical_name: Canonical name from Author: link
            recorded_name: Name as displayed in text
            volume_num: Volume number (used for gender inference)

        Returns:
            Author object with all available metadata
        """
        # Default to "Unknown" if no name provided
        canonical = canonical_name or "Unknown"
        recorded = recorded_name or "Unknown"

        author = Author(canonical=canonical, recorded=recorded)

        if canonical_name and canonical_name != "Unknown":
            wikidata_id = self.get_wikidata_id(canonical_name)
            if wikidata_id:
                author.wikidata_id = wikidata_id

                # Fetch details
                details = self.get_author_details(wikidata_id)

                # Validate temporal consistency with Tang Dynasty (618-907 AD, with buffer)
                # Birth years: Tang/Five Dynasties period with buffer (~580-979)
                # Death years: Can extend into early Song for poets born during Five Dynasties
                #   Example: Born 910 (Five Dynasties) → could live to 990 (age 80)
                # If dates are clearly outside these ranges, the Wikidata entry
                # is likely for a different person with the same name
                TANG_MIN_YEAR = 500   # Buffer before Tang founding
                BIRTH_MAX_YEAR = 979  # End of Five Dynasties period (Northern Han conquest)
                DEATH_MAX_YEAR = 1100 # Allow for poets born during Five Dynasties to live into early Song

                is_temporally_valid = True
                if details['birth_year'] and (details['birth_year'] < TANG_MIN_YEAR or details['birth_year'] > BIRTH_MAX_YEAR):
                    logger.warning(f"Rejecting Wikidata {wikidata_id} for {canonical_name}: birth_year {details['birth_year']} outside range ({TANG_MIN_YEAR}-{BIRTH_MAX_YEAR})")
                    is_temporally_valid = False
                elif details['death_year'] and (details['death_year'] < TANG_MIN_YEAR or details['death_year'] > DEATH_MAX_YEAR):
                    logger.warning(f"Rejecting Wikidata {wikidata_id} for {canonical_name}: death_year {details['death_year']} outside range ({TANG_MIN_YEAR}-{DEATH_MAX_YEAR})")
                    is_temporally_valid = False

                # Only apply Wikidata metadata if temporally valid
                if is_temporally_valid:
                    author.english_name = details['english_name']
                    author.birth_year = details['birth_year']
                    author.death_year = details['death_year']
                    author.period = details['period']
                    author.period_source = "wikidata" if details['period'] else None
                    author.gender = details['gender']
                    author.gender_source = "wikidata" if details['gender'] else None
                    author.cbdb_id = details['cbdb_id']
                    author.viaf_id = details['viaf_id']
                    author.loc_id = details['loc_id']
                    author.birth_place = details['birth_place']
                    author.death_place = details['death_place']
                    author.occupations = details['occupations']
                    author.occupations_source = "wikidata" if details['occupations'] else None
                    author.academic_degree = details['academic_degree']
                    author.academic_degree_source = "wikidata" if details['academic_degree'] else None
                    author.notable_works = details['notable_works']
                    author.wikipedia_url = details['wikipedia_url']
                    author.zh_wikipedia_url = details['zh_wikipedia_url']
                    author.wikisource_url = details['wikisource_url']
                    author.image_url = details['image_url']
                    author.style_names = details['style_names']
                else:
                    # Keep wikidata_id but don't apply metadata (for debugging/blacklist)
                    logger.info(f"Wikidata metadata rejected for {canonical_name}, will use biography-based inference")

        # Apply gender inference if no gender from Wikidata
        if not author.gender and recorded_name:
            if volume_num:
                inferred_gender, gender_source = gender_inference.infer_gender_from_volume(
                    volume_num, recorded_name
                )
            else:
                # Fall back to name-only inference
                inferred_gender, gender_source = gender_inference.infer_gender_from_name(
                    recorded_name
                )

            if inferred_gender:
                author.gender = inferred_gender
                author.gender_source = gender_source

        # Hybrid approach: Apply low-confidence male default for verified real people
        # Only applies to authors with Wikidata IDs but no gender field
        # (excludes  truly anonymous authors like "Unknown")
        if not author.gender and author.wikidata_id:
            author.gender = "male"
            author.gender_source = "inferred_default_historical"
            logger.debug(f"Applied low-confidence male default for {canonical_name} (has Wikidata: {author.wikidata_id})")

        # Apply period inference from title/name if no period from Wikidata
        # (Biography-based  inference happens in author_database.add_or_update_author)
        if not author.period and recorded_name:
            inferred_period, period_source = period_inference.infer_period_from_title(
                recorded_name
            )
            if inferred_period:
                author.period = inferred_period
                author.period_source = period_source

        return author

    def get_author_wikipedia_bio(self, author: Author) -> Optional[str]:
        """
        Get Wikipedia biography for an author if they have a Wikidata ID.

        This is used to enrich authors who don't have biographies from QTS volumes
        with biographical information from Chinese Wikipedia.

        Prefers the Wikidata-provided zh_wikipedia_url (which links to the correct
        article) over name-based lookup (which may hit disambiguation or surname pages).

        Args:
            author: Author object (must have wikidata_id to fetch bio)

        Returns:
            Biography text from Wikipedia, or None if not available
        """
        if not author.wikidata_id:
            return None

        # Prefer Wikidata-provided Chinese Wikipedia URL (more reliable)
        if author.zh_wikipedia_url:
            return self.get_wikipedia_biography(author.canonical, author.zh_wikipedia_url)

        # Fall back to name-based lookup
        return self.get_wikipedia_biography(author.canonical)

    def clear_cache(self):
        self.cache.clear()

    def cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            'total_entries': len(self.cache),
            'cache_file': str(self.cache.cache_file)
        }
