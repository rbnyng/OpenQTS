#!/usr/bin/env python3
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
import numpy as np
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("husl")

# Create output directories
Path("figures").mkdir(exist_ok=True)
Path("tables").mkdir(exist_ok=True)

# Load data
print("Loading data...")
with open('output/all_poems.json', 'r', encoding='utf-8') as f:
    poems = json.load(f)

with open('output/authors.json', 'r', encoding='utf-8') as f:
    authors_data = json.load(f)

# Convert to DataFrames
df_poems = pd.json_normalize(poems)
print(f"Loaded {len(df_poems)} poems")
print(f"Loaded {len(authors_data)} authors")

if 'author.gender' in df_poems.columns:
    df_poems['author.gender'] = df_poems['author.gender'].fillna('unknown')
else:
    df_poems['author.gender'] = 'unknown'
    
# Create output file for statistics
output = open('analysis_results.txt', 'w', encoding='utf-8')

def write_stat(text):
    """Write to both console and file"""
    print(text)
    output.write(text + '\n')

write_stat("="*80)
write_stat("OpenQTS Dataset Analysis for Paper")
write_stat("="*80)
write_stat("")

# ============================================================================
# ANALYSIS 1: BASIC CORPUS STATISTICS
# ============================================================================
write_stat("="*80)
write_stat("1. BASIC CORPUS STATISTICS")
write_stat("="*80)

write_stat(f"Total poems: {len(df_poems):,}")
write_stat(f"Total authors: {len(authors_data):,}")
write_stat(f"Volumes: {df_poems['volume'].nunique()}")
write_stat(f"Date range: Tang Dynasty (618-907 CE)")
write_stat("")

# Poem length statistics
df_poems['poem_length'] = df_poems['poem'].apply(lambda x: len(x) if isinstance(x, list) else 0)
df_poems['total_characters'] = df_poems['poem'].apply(
    lambda x: len(''.join(x)) if isinstance(x, list) else 0
)

write_stat(f"Average lines per poem: {df_poems['poem_length'].mean():.1f}")
write_stat(f"Median lines per poem: {df_poems['poem_length'].median():.1f}")
write_stat(f"Average characters per poem: {df_poems['total_characters'].mean():.1f}")
write_stat("")

# ============================================================================
# ANALYSIS 2: TEMPORAL DISTRIBUTION (PERIOD CLASSIFICATION)
# ============================================================================
write_stat("="*80)
write_stat("2. TEMPORAL DISTRIBUTION BY TANG PERIOD")
write_stat("="*80)

df_poems['period_filled'] = df_poems['author.period'].fillna('Unclassified')
period_counts = df_poems['period_filled'].value_counts()
write_stat("\nPoems by period:")
for period, count in period_counts.items():
    pct = count / len(df_poems) * 100
    write_stat(f"  {period}: {count:,} poems ({pct:.1f}%)")


# Create period distribution plot
fig, ax = plt.subplots(figsize=(10, 6))
period_order = ['Pre-Tang', 'Early Tang', 'High Tang', 'Middle Tang', 'Late Tang', 'Five Dynasties / Song', 'Unclassified']
period_data = period_counts.reindex(period_order, fill_value=0)
bars = ax.bar(range(len(period_data)), period_data.values, color='steelblue', alpha=0.8)
ax.set_xticks(range(len(period_data)))
ax.set_xticklabels(period_data.index, rotation=45, ha='right')
ax.set_ylabel('Number of Poems', fontsize=12)
ax.set_xlabel('Period', fontsize=12)
ax.set_title('Distribution of Poems Across Dynasty Periods', fontsize=14, fontweight='bold')

# Add value labels on bars
for i, (bar, value) in enumerate(zip(bars, period_data.values)):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
            f'{value:,}', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig('figures/period_distribution.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/period_distribution.pdf', bbox_inches='tight')
plt.close()
write_stat("\n✓ Saved: figures/period_distribution.png")

# Period-based poem characteristics
write_stat("\nAverage poem length by period:")
for period in period_order:
    if period in df_poems['author.period'].values:
        period_poems = df_poems[df_poems['author.period'] == period]
        avg_length = period_poems['poem_length'].mean()
        write_stat(f"  {period}: {avg_length:.2f} lines")

write_stat("")

# ============================================================================
# ANALYSIS 3: GENDER ANALYSIS
# ============================================================================
write_stat("="*80)
write_stat("3. GENDER ANALYSIS")
write_stat("="*80)

# Gender distribution in authors
gender_dist_authors = Counter()
gender_source_dist = Counter()

for author_name, author_data in authors_data.items():
    gender = author_data.get('gender', 'unknown')
    gender_dist_authors[gender] += 1
    source = author_data.get('gender_source', 'unknown')
    gender_source_dist[source] += 1

write_stat("\nAuthors by gender:")
for gender, count in sorted(gender_dist_authors.items()):
    pct = count / len(authors_data) * 100
    write_stat(f"  {gender}: {count:,} authors ({pct:.1f}%)")

write_stat("\nGender data sources:")
for source, count in sorted(gender_source_dist.items(), key=lambda x: x[1], reverse=True):
    pct = count / len(authors_data) * 100
    write_stat(f"  {source}: {count:,} ({pct:.1f}%)")

# Gender distribution in poems
df_poems['gender_filled'] = df_poems['author.gender'].fillna('unknown')
df_poems['gender_filled'] = df_poems.get('author.gender', 'unknown')
gender_dist_poems = df_poems['gender_filled'].value_counts()
write_stat("\nPoems by author gender:")
for gender, count in gender_dist_poems.items():
    pct = count / len(df_poems) * 100
    write_stat(f"  {gender}: {count:,} poems ({pct:.1f}%)")

# Create gender distribution visualization
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Authors by gender
gender_colors = {'male': '#4A90E2', 'female': '#E24A90', 'unknown': '#CCCCCC'}
authors_gender_data = pd.Series(gender_dist_authors)
colors_authors = [gender_colors.get(g, '#CCCCCC') for g in authors_gender_data.index]
wedges, texts, autotexts = ax1.pie(authors_gender_data.values, 
                                     labels=authors_gender_data.index,
                                     autopct='%1.1f%%',
                                     colors=colors_authors,
                                     startangle=90)
ax1.set_title('Authors by Gender', fontsize=14, fontweight='bold')

# Poems by gender
poems_gender_data = gender_dist_poems
colors_poems = [gender_colors.get(g, '#CCCCCC') for g in poems_gender_data.index]
wedges, texts, autotexts = ax2.pie(poems_gender_data.values,
                                    labels=poems_gender_data.index,
                                    autopct='%1.1f%%',
                                    colors=colors_poems,
                                    startangle=90)
ax2.set_title('Poems by Author Gender', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('figures/gender_distribution.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/gender_distribution.pdf', bbox_inches='tight')
plt.close()
write_stat("\n✓ Saved: figures/gender_distribution.png")

# Female poets by period
write_stat("\nFemale poets by period:")
female_by_period = df_poems[df_poems['author.gender'] == 'female']['author.period'].value_counts()
for period, count in female_by_period.items():
    write_stat(f"  {period}: {count:,} poems")

# Top female poets
write_stat("\nTop 10 female poets by poem count:")
female_poems = df_poems[df_poems['author.gender'] == 'female']
top_female = female_poems['author.canonical'].value_counts().head(10)
for i, (name, count) in enumerate(top_female.items(), 1):
    # Get English name if available
    author_info = authors_data.get(name, {})
    english_name = author_info.get('english_name', '')
    display = f"{name} ({english_name})" if english_name else name
    write_stat(f"  {i}. {display}: {count} poems")

write_stat("")

# ============================================================================
# ANALYSIS 4: AUTHORITY FILE COVERAGE
# ============================================================================
write_stat("="*80)
write_stat("4. AUTHORITY FILE INTEGRATION")
write_stat("="*80)

# Calculate coverage
wikidata_count = sum(1 for a in authors_data.values() if a.get('wikidata_id'))
cbdb_count = sum(1 for a in authors_data.values() if a.get('cbdb_id'))
viaf_count = sum(1 for a in authors_data.values() if a.get('viaf_id'))
loc_count = sum(1 for a in authors_data.values() if a.get('loc_id'))
english_name_count = sum(1 for a in authors_data.values() if a.get('english_name'))
any_authority = sum(1 for a in authors_data.values() 
                    if a.get('wikidata_id') or a.get('cbdb_id') or a.get('viaf_id'))

total_authors = len(authors_data)

write_stat("\nAuthority file coverage:")
write_stat(f"  Wikidata ID: {wikidata_count:,} ({wikidata_count/total_authors*100:.1f}%)")
write_stat(f"  CBDB ID: {cbdb_count:,} ({cbdb_count/total_authors*100:.1f}%)")
write_stat(f"  VIAF ID: {viaf_count:,} ({viaf_count/total_authors*100:.1f}%)")
write_stat(f"  Library of Congress: {loc_count:,} ({loc_count/total_authors*100:.1f}%)")
write_stat(f"  Any authority file: {any_authority:,} ({any_authority/total_authors*100:.1f}%)")
write_stat(f"  English name: {english_name_count:,} ({english_name_count/total_authors*100:.1f}%)")

# Create authority file coverage table
coverage_data = {
    'Authority File': ['Wikidata', 'CBDB', 'VIAF', 'Library of Congress', 'Any Authority File', 'English Name'],
    'Count': [wikidata_count, cbdb_count, viaf_count, loc_count, any_authority, english_name_count],
    'Coverage (%)': [
        f"{wikidata_count/total_authors*100:.1f}",
        f"{cbdb_count/total_authors*100:.1f}",
        f"{viaf_count/total_authors*100:.1f}",
        f"{loc_count/total_authors*100:.1f}",
        f"{any_authority/total_authors*100:.1f}",
        f"{english_name_count/total_authors*100:.1f}"
    ]
}

df_coverage = pd.DataFrame(coverage_data)

# Save as LaTeX table
latex_table = df_coverage.to_latex(index=False, caption='Authority File Coverage Statistics',
                                    label='tab:authority_coverage')
with open('tables/authority_coverage.tex', 'w') as f:
    f.write(latex_table)
write_stat("\n✓ Saved: tables/authority_coverage.tex")

# Visualize coverage
fig, ax = plt.subplots(figsize=(10, 6))
coverage_names = ['Wikidata', 'CBDB', 'VIAF', 'LoC', 'Any\nAuthority', 'English\nName']
coverage_values = [wikidata_count, cbdb_count, viaf_count, loc_count, any_authority, english_name_count]
coverage_pcts = [v/total_authors*100 for v in coverage_values]

bars = ax.bar(range(len(coverage_names)), coverage_pcts, color='#2E7D32', alpha=0.8)
ax.set_xticks(range(len(coverage_names)))
ax.set_xticklabels(coverage_names, fontsize=11)
ax.set_ylabel('Coverage (%)', fontsize=12)
ax.set_xlabel('Authority File / Metadata Type', fontsize=12)
ax.set_title('Author Metadata Coverage', fontsize=14, fontweight='bold')
ax.set_ylim(0, 100)
ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, linewidth=1)

# Add value labels
for bar, value, pct in zip(bars, coverage_values, coverage_pcts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
            f'{pct:.1f}%\n({value:,})', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('figures/authority_coverage.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/authority_coverage.pdf', bbox_inches='tight')
plt.close()
write_stat("✓ Saved: figures/authority_coverage.png")

write_stat("")

# ============================================================================
# ANALYSIS 5: MULTI-PART POEMS
# ============================================================================
write_stat("="*80)
write_stat("5. MULTI-PART POEM ANALYSIS")
write_stat("="*80)

# Count poems with part indices
has_part_index = df_poems['part_index'].notna()
multi_part_count = has_part_index.sum()
single_part_count = len(df_poems) - multi_part_count

write_stat(f"\nSingle-part poems: {single_part_count:,}")
write_stat(f"Multi-part poems: {multi_part_count:,} ({multi_part_count/len(df_poems)*100:.1f}%)")

# Distribution of multi-part poems
if multi_part_count > 0:
    total_parts_dist = df_poems[df_poems['total_parts'].notna()]['total_parts'].value_counts().sort_index()
    write_stat("\nDistribution by total parts:")
    for parts, count in total_parts_dist.head(10).items():
        write_stat(f"  {int(parts)} parts: {count:,} sequences")
    
    max_parts = int(df_poems['total_parts'].max())
    write_stat(f"\nLongest sequence: {max_parts} parts")
    
    # Find examples of longest sequences
    longest = df_poems[df_poems['total_parts'] == max_parts].head(3)
    write_stat("\nExamples of longest sequences:")
    for idx, row in longest.iterrows():
        write_stat(f"  - {row['title']} by {row['author.canonical']}")

write_stat("")

# ============================================================================
# ANALYSIS 6: METADATA COMPLETENESS
# ============================================================================
write_stat("="*80)
write_stat("6. METADATA COMPLETENESS")
write_stat("="*80)

# Birth/death year coverage
birth_year_count = sum(1 for a in authors_data.values() if a.get('birth_year'))
death_year_count = sum(1 for a in authors_data.values() if a.get('death_year'))
both_years_count = sum(1 for a in authors_data.values() 
                       if a.get('birth_year') and a.get('death_year'))

write_stat(f"\nBirth year known: {birth_year_count:,} ({birth_year_count/total_authors*100:.1f}%)")
write_stat(f"Death year known: {death_year_count:,} ({death_year_count/total_authors*100:.1f}%)")
write_stat(f"Both years known: {both_years_count:,} ({both_years_count/total_authors*100:.1f}%)")

# Period classification coverage
period_count = sum(1 for a in authors_data.values() if a.get('period'))
write_stat(f"Period classification: {period_count:,} ({period_count/total_authors*100:.1f}%)")

# Occupation data
occupation_count = sum(1 for a in authors_data.values() if a.get('occupations'))
write_stat(f"Occupation data: {occupation_count:,} ({occupation_count/total_authors*100:.1f}%)")

# Academic degree data
degree_count = sum(1 for a in authors_data.values() if a.get('academic_degree'))
write_stat(f"Academic degree: {degree_count:,} ({degree_count/total_authors*100:.1f}%)")

write_stat("")

# ============================================================================
# ANALYSIS 8: EXAMPLE POEMS (for paper)
# ============================================================================
write_stat("="*80)
write_stat("8. EXAMPLE POEMS FOR PAPER")
write_stat("="*80)

# Find a famous poet with good metadata
famous_poets = ['李白', '杜甫', '白居易', '王維', '李商隱']
for poet_name in famous_poets:
    if poet_name in authors_data:
        poet_data = authors_data[poet_name]
        poet_poems = df_poems[df_poems['author.canonical'] == poet_name]
        
        if len(poet_poems) > 0:
            write_stat(f"\nExample author: {poet_name}")
            write_stat(f"  English name: {poet_data.get('english_name', 'N/A')}")
            write_stat(f"  Birth-Death: {poet_data.get('birth_year', '?')}-{poet_data.get('death_year', '?')}")
            write_stat(f"  Period: {poet_data.get('period', 'Unknown')}")
            write_stat(f"  Wikidata: {poet_data.get('wikidata_id', 'N/A')}")
            write_stat(f"  CBDB: {poet_data.get('cbdb_id', 'N/A')}")
            write_stat(f"  Poems in corpus: {len(poet_poems)}")
            
            # Get one example poem
            example = poet_poems.iloc[0]
            write_stat(f"\n  Example poem UID: {example['uid']}")
            write_stat(f"  Title: {example['title']}")
            write_stat(f"  Lines: {len(example['poem'])}")
            
            break

write_stat("")

# ============================================================================
# TEMPORAL ANALYSIS: Poem characteristics over time
# ============================================================================
print("Generating temporal analysis...")

# Calculate poem length by period
df_poems['poem_length'] = df_poems['poem'].apply(lambda x: len(x) if isinstance(x, list) else 0)
df_poems['char_count'] = df_poems['poem'].apply(lambda x: len(''.join(x)) if isinstance(x, list) else 0)

period_stats = df_poems.groupby('author.period').agg({
    'poem_length': ['mean', 'median', 'std'],
    'char_count': ['mean', 'median'],
    'uid': 'count'
}).round(2)

print("\nPoem characteristics by period:")
print(period_stats)

# Visualize temporal trends
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

period_order = ['Early Tang', 'High Tang', 'Middle Tang', 'Late Tang']
period_data = df_poems[df_poems['author.period'].isin(period_order)]

# Box plot of poem lengths
period_data_plot = [period_data[period_data['author.period'] == p]['poem_length'].values 
                    for p in period_order]
bp = ax1.boxplot(period_data_plot, labels=period_order, patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('#4A90E2')
    patch.set_alpha(0.7)
ax1.set_ylabel('Lines per Poem', fontsize=12)
ax1.set_xlabel('Period', fontsize=12)
ax1.set_title('Poem Length Distribution by Period', fontsize=13, fontweight='bold')
ax1.tick_params(axis='x', rotation=45)

# Average poem length over periods
avg_lengths = period_data.groupby('author.period')['poem_length'].mean().reindex(period_order)
ax2.plot(range(len(period_order)), avg_lengths.values, marker='o', linewidth=2, 
         markersize=8, color='#2E7D32')
ax2.set_xticks(range(len(period_order)))
ax2.set_xticklabels(period_order, rotation=45, ha='right')
ax2.set_ylabel('Average Lines per Poem', fontsize=12)
ax2.set_xlabel('Period', fontsize=12)
ax2.set_title('Average Poem Length Over Time', fontsize=13, fontweight='bold')
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('figures/temporal_characteristics.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/temporal_characteristics.pdf', bbox_inches='tight')
plt.close()
print("✓ Saved: figures/temporal_characteristics.png")

# ============================================================================
# GENDER OVER TIME: Female poet representation by period
# ============================================================================
print("\nGenerating gender-over-time analysis...")

female_by_period = df_poems[df_poems['author.gender'] == 'female'].groupby('author.period').size()
total_by_period = df_poems.groupby('author.period').size()
female_pct = (female_by_period / total_by_period * 100).reindex(period_order, fill_value=0)

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(range(len(period_order)), female_pct.values, color='#E24A90', alpha=0.8)
ax.set_xticks(range(len(period_order)))
ax.set_xticklabels(period_order, rotation=45, ha='right')
ax.set_ylabel('Percentage of Poems by Female Authors (%)', fontsize=12)
ax.set_xlabel('Period', fontsize=12)
ax.set_title('Female Poet Representation Across Tang Dynasty', fontsize=14, fontweight='bold')

# Add value labels
for i, (bar, value) in enumerate(zip(bars, female_pct.values)):
    count = female_by_period.get(period_order[i], 0)
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
            f'{value:.2f}%\n({count:,})', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('figures/female_poets_by_period.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/female_poets_by_period.pdf', bbox_inches='tight')
plt.close()
print("✓ Saved: figures/female_poets_by_period.png")

# ============================================================================
# PROLIFIC AUTHORS: Top poets by output
# ============================================================================
print("\nAnalyzing prolific authors...")

author_counts = df_poems['author.canonical'].value_counts()
top_20 = author_counts.head(20)

# Get English names for top authors
top_authors_data = []
for name, count in top_20.items():
    author_info = authors_data.get(name, {})
    english_name = author_info.get('english_name', '')
    period = author_info.get('period', 'Unknown')
    gender = author_info.get('gender', 'unknown')
    
    display_name = f"{name}\n({english_name})" if english_name else name
    top_authors_data.append({
        'name': name,
        'display': display_name,
        'english': english_name,
        'count': count,
        'period': period,
        'gender': gender
    })

df_top = pd.DataFrame(top_authors_data)

# Visualize top 15 poets
fig, ax = plt.subplots(figsize=(12, 8))
y_pos = np.arange(15)
bars = ax.barh(y_pos, df_top['count'].head(15), color='#4A90E2', alpha=0.8)
ax.set_yticks(y_pos)
ax.set_yticklabels(df_top['display'].head(15), fontsize=10)
ax.invert_yaxis()
ax.set_xlabel('Number of Poems', fontsize=12)
ax.set_title('Top 15 Most Prolific Poets in the Corpus', fontsize=14, fontweight='bold')

# Add value labels
for i, (bar, value) in enumerate(zip(bars, df_top['count'].head(15))):
    ax.text(value + 10, bar.get_y() + bar.get_height()/2,
            f'{value:,}', va='center', fontsize=9)

plt.tight_layout()
plt.savefig('figures/top_poets.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/top_poets.pdf', bbox_inches='tight')
plt.close()
print("✓ Saved: figures/top_poets.png")

# Save table for paper
top_10_table = df_top[['name', 'english', 'period', 'count']].head(10)
top_10_table.columns = ['Name (Chinese)', 'Name (English)', 'Period', 'Poems']
latex_table = top_10_table.to_latex(index=False, 
                                     caption='Top 10 Most Prolific Poets',
                                     label='tab:top_poets')
with open('tables/top_poets.tex', 'w', encoding='utf-8') as f:
    f.write(latex_table)
print("✓ Saved: tables/top_poets.tex")

# ============================================================================
# VOLUME DISTRIBUTION: Coverage across volumes
# ============================================================================
print("\nAnalyzing volume distribution...")

poems_per_volume = df_poems.groupby('volume').size()

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(poems_per_volume.index, poems_per_volume.values, linewidth=1.5, alpha=0.7)
ax.fill_between(poems_per_volume.index, poems_per_volume.values, alpha=0.3)
ax.set_xlabel('Volume Number', fontsize=12)
ax.set_ylabel('Number of Poems', fontsize=12)
ax.set_title('Poem Distribution Across 900 Volumes', fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Add statistics
mean_poems = poems_per_volume.mean()
median_poems = poems_per_volume.median()
ax.axhline(y=mean_poems, color='red', linestyle='--', alpha=0.5, 
           label=f'Mean: {mean_poems:.1f}')
ax.axhline(y=median_poems, color='green', linestyle='--', alpha=0.5,
           label=f'Median: {median_poems:.1f}')
ax.legend()

plt.tight_layout()
plt.savefig('figures/volume_distribution.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/volume_distribution.pdf', bbox_inches='tight')
plt.close()
print("✓ Saved: figures/volume_distribution.png")

print(f"\nVolume statistics:")
print(f"  Mean poems per volume: {mean_poems:.1f}")
print(f"  Median poems per volume: {median_poems:.1f}")
print(f"  Min: {poems_per_volume.min()}")
print(f"  Max: {poems_per_volume.max()}")

# ============================================================================
# OCCUPATIONS: Most common occupations
# ============================================================================
print("\nAnalyzing occupations...")

all_occupations = []
for author_data in authors_data.values():
    occupations = author_data.get('occupations', [])
    if occupations:
        all_occupations.extend(occupations)

occupation_counts = Counter(all_occupations)
top_occupations = occupation_counts.most_common(15)

print("\nTop 15 occupations:")
for occ, count in top_occupations:
    print(f"  {occ}: {count:,}")

# Visualize
fig, ax = plt.subplots(figsize=(12, 8))
occs, counts = zip(*top_occupations)
y_pos = np.arange(len(occs))
bars = ax.barh(y_pos, counts, color='#2E7D32', alpha=0.8)
ax.set_yticks(y_pos)
ax.set_yticklabels(occs, fontsize=11)
ax.invert_yaxis()
ax.set_xlabel('Number of Authors', fontsize=12)
ax.set_title('Most Common Occupations Among Tang Poets', fontsize=14, fontweight='bold')

for i, (bar, value) in enumerate(zip(bars, counts)):
    ax.text(value + 5, bar.get_y() + bar.get_height()/2,
            f'{value:,}', va='center', fontsize=9)

plt.tight_layout()
plt.savefig('figures/occupations.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/occupations.pdf', bbox_inches='tight')
plt.close()
print("✓ Saved: figures/occupations.png")

# ============================================================================
# CHARACTER FREQUENCY: Most common characters in poems
# ============================================================================
print("\nAnalyzing character frequency...")

all_chars = Counter()
for poem_lines in df_poems['poem']:
    if isinstance(poem_lines, list):
        text = ''.join(poem_lines)
        all_chars.update(text)

# Top 20 characters
top_chars = all_chars.most_common(30)
print("\nTop 20 most frequent characters:")
for char, count in top_chars[:20]:
    print(f"  {char}: {count:,}")


# ============================================================================
# SUMMARY STATISTICS FOR ABSTRACT
# ============================================================================
write_stat("="*80)
write_stat("SUMMARY STATISTICS FOR ABSTRACT/INTRO")
write_stat("="*80)

write_stat(f"""
Key numbers for paper:
- {len(df_poems):,} poems across {df_poems['volume'].nunique()} volumes
- {len(authors_data):,} authors with biographical metadata
- {any_authority:,} authors ({any_authority/total_authors*100:.1f}%) linked to authority files (Wikidata/CBDB/VIAF)
- {english_name_count:,} authors ({english_name_count/total_authors*100:.1f}%) with English names
- {gender_dist_authors['female']} female poets identified ({gender_dist_authors['female']/total_authors*100:.1f}%)
- {both_years_count:,} authors ({both_years_count/total_authors*100:.1f}%) with both birth and death years
- Period classification covering {period_count:,} authors ({period_count/total_authors*100:.1f}%)
- {multi_part_count:,} multi-part poems properly indexed
""")

output.close()
print("\n" + "="*80)
print("Analysis complete")
print("="*80)
