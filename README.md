# OpenQTS: Open Complete Tang Poems Dataset (全唐詩)

A machine-readable edition of the Quan Tang Shi (全唐詩), or Complete Tang Poems. OpenQTS provides a unique identifier (UID) for every poem and enriches ~4,000+ authors with biographical data linked to Wikidata, CBDB, and VIAF. Includes algorithmic inference for missing historical metadata and preserves editorial context like prefaces and interlinear notes.

## Overview

| Metric | Value |
|--------|-------|
| Volumes | 900 |
| Poems | ~50,000 |
| Authors | ~4,000+ |
| Time Period | Tang Dynasty (618–907 CE) |

## Features

- **Complete corpus**: All 900 volumes of the Quan Tang Shi
- **Structured format**: Clean json with unique identifiers (UIDs)
- **Rich author metadata**: Wikidata IDs, English names, birth/death years, gender, occupations, academic degrees
- **Authority file links**: CBDB, VIAF, and Library of Congress IDs where available
- **Period classification**: Authors tagged as Early/High/Middle/Late Tang
- **Multi-part poem handling**: Indexing for poem sequences (其一, 其二, etc.)
- **Editorial content**: Preserved prefaces (序), notes, and textual variants (where they're available)
- **Collaborative poems**: Proper attribution for 聯句 (linked verse)

## Dataset Structure

The dataset consists of two types of files:

### Volume Files (`volume_NNN.json`)

Individual JSON files for each of the 900 volumes, plus a combined file. Each contains an array of poem objects:

```json
{
  "uid": "QTS_001_003_01",
  "volume": 1,
  "author": {
    "canonical": "李世民",
    "recorded": "李世民",
    "wikidata_id": "Q9700",
    "english_name": "Emperor Taizong of Tang",
    "gender": "male",
    "period": "Early Tang"
  },
  "title": "帝京篇十首 一",
  "poem": [
    "秦川雄帝宅",
    "函谷壯皇居",
    "綺殿千尋起",
    "離宮百雉餘"
  ],
  "part_index": 1,
  "total_parts": 10,
  "preface": "予以萬幾之暇...",
  "notes": ["editorial annotations"]
}
```

#### Poem Fields

| Field | Type | Description |
|-------|------|-------------|
| `uid` | string | Unique identifier (format: `QTS_VVV_EEE_PP`) |
| `volume` | integer | Volume number (1–900) |
| `author` | object | Author metadata (see below) |
| `title` | string | Poem title |
| `poem` | array | Lines of the poem |
| `part_index` | integer? | Part number for multi-part poems (1-based) |
| `total_parts` | integer? | Total parts in a multi-part poem |
| `preface` | string? | Authorial preface (序) |
| `notes` | array? | Editorial annotations |
| `variants` | array? | Textual variants from manuscript traditions |

#### Embedded Author Fields (in poems)

Poems include a minimal author object for self-contained usage:

| Field | Type | Description |
|-------|------|-------------|
| `canonical` | string | Canonical name (from Wikisource Author: link) |
| `recorded` | string | Name as displayed in the source text |
| `wikidata_id` | string? | Wikidata Q-ID (e.g., `Q9700`) |
| `english_name` | string? | English name from Wikidata |
| `gender` | string? | `male`, `female`, or `unknown` |
| `period` | string? | `Early Tang`, `High Tang`, `Middle Tang`, or `Late Tang` |

### Author Database (`authors.json`)

A separate file containing full metadata for all authors, keyed by canonical name:

```json
  "李世民": {
    "canonical": "李世民",
    "recorded_variants": [
      "李世民"
    ],
    "biographies": [
      {
        "text": "帝姓李氏，諱世民，神堯次子，聰明英武。貞觀之治，庶幾成康，功德兼隆，由漢以來，未之有也。而銳情經術，初建秦邸，卽開文學館，召名儒十八人爲學士。旣卽位，殿左置弘文館，悉引內學士，番宿更休。聽朝之間，則與討論典籍，雜以文詠。或日昃夜艾，未嘗少怠。詩筆草隸，卓越前古。至於天文秀發，沈麗高朗，有唐三百年風雅之盛，帝實有以啓之焉。在位二十四年，謚曰文。集四十卷。《館閣書目》：詩一卷，六十九首。今編詩一卷。",
        "source_volume": 1
      }
    ],
    "wikidata_id": "Q9701",
    "english_name": "Emperor Taizong of Tang",
    "birth_year": 598,
    "death_year": 649,
    "period": "Early Tang",
    "period_source": "wikidata",
    "gender": "male",
    "gender_source": "wikidata",
    "cbdb_id": "0013060",
    "viaf_id": "67810502",
    "loc_id": "n82074092",
    "birth_place": "Wugong County",
    "death_place": "Hangfeng Hall",
    "occupations": [
      "academician",
      "emperor",
      "poet",
      "scholar"
    ],
    "occupations_source": "wikidata+inferred_biography",
    "wikipedia_url": "https://en.wikipedia.org/wiki/Emperor_Taizong_of_Tang",
    "wikisource_url": "https://zh.wikisource.org/wiki/Author%3A%E6%9D%8E%E4%B8%96%E6%B0%91",
    "image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Tang%20Taizong%20%28cropped%29.jpg"
  }
```

#### Full Author Fields

| Field | Type | Description |
|-------|------|-------------|
| `canonical` | string | Canonical name |
| `recorded_variants` | array | Name variants found in source texts |
| `wikidata_id` | string? | Wikidata Q-ID |
| `english_name` | string? | English name |
| `birth_year` | integer? | Year of birth |
| `death_year` | integer? | Year of death |
| `dates` | string? | Formatted date range (e.g., `701–762`) |
| `period` | string? | Tang dynasty period |
| `period_source` | string? | How period was determined |
| `gender` | string? | Gender |
| `gender_source` | string? | How gender was determined |
| `birth_place` | string? | Place of birth |
| `death_place` | string? | Place of death |
| `occupations` | array? | List of occupations |
| `occupations_source` | string? | Source of occupation data |
| `academic_degree` | string? | Highest academic degree (e.g., `jinshi`) |
| `academic_degree_source` | string? | Source of degree information |
| `style_names` | array? | Courtesy names (字) and art names (號) |
| `notable_works` | array? | Famous works |
| `cbdb_id` | string? | China Biographical Database ID |
| `viaf_id` | string? | Virtual International Authority File ID |
| `loc_id` | string? | Library of Congress authority ID |
| `wikipedia_url` | string? | English Wikipedia URL |
| `wikisource_url` | string? | Chinese Wikisource author page |
| `image_url` | string? | Portrait from Wikimedia Commons |
| `biographies` | array? | Biographical texts with source volumes |

## Quick Start

### For Researchers & Data Scientists
You do not need to run the code to use the data. We provide compiled releases of the dataset:

1.  **`all_poems.json`**: The complete corpus after processing.
2.  **`authors.json`**: The author database with rich metadata.

### Download the Dataset

*(Coming soon)*

### Usage Example

The data is designed to be easily usable in Python (Pandas) or R.

```python
import pandas as pd
import json

# load the dataset
with open('output/all_poems.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.json_normalize(data)

# Find all High Tang poems that mention the Moon
high_tang_moon = df[
    (df['author.period'] == 'High Tang') & 
    (df['poem'].apply(lambda lines: any('月' in line for line in lines)))
]

print(f"Found {len(high_tang_moon)} poems.")
```

### Build from Source for Developers

```bash
pip install -r requirements.txt

# Test on 3 volumes
python scraper.py --test

# Full extraction
python scraper.py --start 1 --end 900

# Post-process (splits multi-part poems, applies corrections)
python post_process_splits.py --start 1 --end 900

# Generate final combined dataset
python generate_dataset.py

# Validate output
python validate_output.py --dir output
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--start` | Starting volume (1–900) | 1 |
| `--end` | Ending volume (1–900) | 10 |
| `--output-dir` | Output directory | `output` |
| `--delay` | Delay between requests (seconds) | 1.5 |
| `--test` | Test mode (volumes 1–3 only) | — |

## Pipeline

```
Wikisource (900 volumes) → Scraper → Post-Processing → Validation → OpenQTS
         ↓
   Wikidata API (author metadata)
```

| Stage | Script | Purpose |
|-------|--------|---------|
| Extract | `scraper.py` | Fetch poems and author metadata from Wikisource |
| Enrich | `author_service.py` | Query Wikidata for author details |
| Process | `post_process_splits.py` | Split multi-part poems, apply corrections |
| Combine | `generate_dataset.py` | Combine all volumes into `all_poems.json` with statistics |
| Validate | `validate_output.py` | Check data integrity and UID uniqueness |

## Metadata Inference

When Wikidata lacks information, the pipeline infers metadata from biographical texts:

- **Period**: Detected from era names (年號) and imperial examination years
- **Gender**: Inferred from 100+ official titles and markers (e.g. 尚書, 女史)
- **Occupations**: Extracted from biographical descriptions
- **Academic degrees**: Detected from examination references (進士, 明經, etc.)

## Source & License

- **Data source**: [Chinese Wikisource — 全唐詩](https://zh.wikisource.org/zh-hant/全唐詩)
- **Dataset license**: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Code license**: [AGPL-3.0](LICENSE)

## Contributing

Contributions are welcome! Please see the validation scripts for data quality checks:

```bash
# Find potential issues
python validate_splits.py --start 1 --end 900

# Check output integrity
python validate_output.py --dir output
```

For corrections, it would be best to correct Wikisource directly; but code improvements and structural refactoring is welcome, the codebase is a heavily overgrown state machine.
