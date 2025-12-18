#!/usr/bin/env python3
"""
Generate the final complete Tang poems dataset from processed volume files.

This script combines all individual volume JSON files from the output/ directory
into a single unified dataset file (all_poems.json).
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

OUTPUT_DIR = Path("output")
DATASET_FILE = OUTPUT_DIR / "all_poems.json"
STATS_FILE = OUTPUT_DIR / "dataset_stats.json"
VOLUME_RANGE = range(1, 901)  # Volumes 1-900

def load_volume(volume_num: int) -> List[Dict[str, Any]]:
    volume_file = OUTPUT_DIR / f"volume_{volume_num:03d}.json"

    if not volume_file.exists():
        print(f"Warning: {volume_file.name} not found, skipping.")
        return []

    try:
        with open(volume_file, 'r', encoding='utf-8') as f:
            poems = json.load(f)
            return poems if isinstance(poems, list) else []
    except json.JSONDecodeError as e:
        print(f"Error reading {volume_file.name}: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error reading {volume_file.name}: {e}")
        return []

def collect_all_poems() -> List[Dict[str, Any]]:
    all_poems = []
    volumes_loaded = 0

    print(f"Loading poems from {len(VOLUME_RANGE)} volumes.")

    for volume_num in VOLUME_RANGE:
        poems = load_volume(volume_num)

        if poems:
            all_poems.extend(poems)
            volumes_loaded += 1

            if volume_num % 100 == 0:
                print(f"   Loaded {volume_num}/900 volumes ({len(all_poems):,} poems so far).")

    print(f"Loaded {volumes_loaded} volumes with {len(all_poems):,} total poems")
    return all_poems


def generate_statistics(poems: List[Dict[str, Any]]) -> Dict[str, Any]:
    stats = {
        "total_poems": len(poems),
        "total_volumes": 0,
        "poems_by_volume": defaultdict(int),
        "poems_by_author": defaultdict(int),
        "poems_by_period": defaultdict(int),
        "poems_by_gender": defaultdict(int),
        "multi_part_poems": 0,
        "poems_with_preface": 0,
        "poems_with_notes": 0,
        "unique_authors": set(),
        "line_count_distribution": defaultdict(int),
    }

    for poem in poems:
        # Volume stats
        volume = poem.get("volume", 0)
        stats["poems_by_volume"][volume] += 1

        # Author stats
        author_info = poem.get("author", {})
        canonical_name = author_info.get("canonical", "Unknown")
        stats["poems_by_author"][canonical_name] += 1
        stats["unique_authors"].add(canonical_name)

        # Period stats
        period = author_info.get("period", "Unknown")
        stats["poems_by_period"][period] += 1

        # Gender stats
        gender = author_info.get("gender", "unknown")
        stats["poems_by_gender"][gender] += 1

        # Multi-part poems
        if poem.get("total_parts") and poem.get("total_parts") > 1:
            stats["multi_part_poems"] += 1

        # Content features
        if poem.get("preface"):
            stats["poems_with_preface"] += 1

        if poem.get("notes"):
            stats["poems_with_notes"] += 1

        # Line count distribution
        line_count = len(poem.get("poem", []))
        stats["line_count_distribution"][line_count] += 1

    # Convert sets and defaultdicts for JSON serialization
    stats["unique_authors"] = len(stats["unique_authors"])
    stats["total_volumes"] = len(stats["poems_by_volume"])

    # Get top authors
    top_authors = sorted(
        stats["poems_by_author"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:20]

    stats["top_20_authors"] = [
        {"name": name, "poem_count": count}
        for name, count in top_authors
    ]

    # Convert defaultdicts to regular dicts
    stats["poems_by_volume"] = dict(stats["poems_by_volume"])
    stats["poems_by_author"] = dict(stats["poems_by_author"])
    stats["poems_by_period"] = dict(stats["poems_by_period"])
    stats["poems_by_gender"] = dict(stats["poems_by_gender"])
    stats["line_count_distribution"] = dict(stats["line_count_distribution"])

    return stats


def main():
    """Main function to generate the final dataset."""
    print("=" * 60)
    print("Complete Tang Poems Dataset Generator")
    print("=" * 60)
    print()

    # Check if output directory exists
    if not OUTPUT_DIR.exists():
        print(f"Error: Output directory '{OUTPUT_DIR}' not found!")
        print("   Please run post_process_splits.py first to generate processed volumes.")
        return 1

    # Collect all poems
    all_poems = collect_all_poems()

    if not all_poems:
        print("No poems found! Cannot generate dataset.")
        return 1

    print()

    # Generate statistics
    print("Generating statistics.")
    stats = generate_statistics(all_poems)

    # Save combined dataset
    print(f"Saving complete dataset to {DATASET_FILE}.")
    with open(DATASET_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_poems, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_poems):,} poems to {DATASET_FILE}")

    # Save statistics
    print(f"Saving statistics to {STATS_FILE}.")
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Saved statistics to {STATS_FILE}")
    print()

    # Print summary
    print("=" * 60)
    print("Dataset Summary")
    print("=" * 60)
    print(f"Total poems:      {stats['total_poems']:,}")
    print(f"Total volumes:    {stats['total_volumes']}")
    print(f"Unique authors:   {stats['unique_authors']:,}")
    print(f"Multi-part poems: {stats['multi_part_poems']:,}")
    print(f"With prefaces:    {stats['poems_with_preface']:,}")
    print(f"With notes:       {stats['poems_with_notes']:,}")
    print()
    print("By Period:")
    for period, count in sorted(stats['poems_by_period'].items()):
        print(f"  {period:20s}: {count:,}")
    print()
    print("By Gender:")
    for gender, count in sorted(stats['poems_by_gender'].items()):
        print(f"  {gender:20s}: {count:,}")
    print()
    print("Top 5 Most Prolific Authors:")
    for i, author in enumerate(stats['top_20_authors'][:5], 1):
        print(f"  {i}. {author['name']:20s}: {author['poem_count']:,} poems")
    print()
    print("=" * 60)
    print("Dataset generation complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
