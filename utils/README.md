# Utils Module

## Modules

### `chinese_utils.py`
Chinese text processing utilities:
- `number_to_chinese(num)` - Convert Arabic numerals to Chinese numerals (1→一, 12→十二)
- `clean_chinese_text(text)` - Remove markup artifacts like [編輯]
- `is_part_indicator(line)` - Check if line is a part marker (其一, 其二, etc.)

### `text_utils.py`
General text processing utilities:
- `separate_annotation(line)` - Extract annotations from 〈〉 brackets
- `clean_line(line)` - Remove whitespace and zero-width characters
- `extract_notes_from_text(text)` - Find all annotations in text
- `remove_all_annotations(text)` - Strip all 〈〉 annotations

### `uid_generator.py`
UID generation for poems:
- `generate_uid(volume_num, poem_index)` - Generate format QTS_VVV_PPP

## Usage

```python
from utils import chinese_utils, text_utils, uid_generator

# Convert numbers
chinese_utils.number_to_chinese(8)  # → '八'

# Extract annotations
text_utils.separate_annotation('春眠不覺曉〈出處〉')
# → ('春眠不覺曉', '出處')

# Generate UID
uid_generator.generate_uid(5, 12)  # → 'QTS_005_012'
```
