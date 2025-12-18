import json
import glob
from pathlib import Path

def find_empty_poems(output_dir='output'):
    print(f"Scanning {output_dir} for empty poems...")
    print("-" * 60)
    print(f"{'UID':<18} | {'Vol':<4} | {'Author':<10} | {'Title'}")
    print("-" * 60)

    count = 0
    
    # Look for volume files
    files = sorted(glob.glob(f"{output_dir}/volume_*.json"))
    
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                poems = json.load(f)
                
                for p in poems:
                    # Check if poem list is empty or contains only whitespace
                    content = p.get('poem', [])
                    is_empty = False
                    
                    if not content:
                        is_empty = True
                    elif all(not line.strip() for line in content):
                        is_empty = True
                        
                    if is_empty:
                        count += 1
                        uid = p.get('uid', 'Unknown')
                        vol = p.get('volume', '???')
                        # Handle author object or string
                        auth_data = p.get('author', {})
                        author = auth_data.get('recorded') if isinstance(auth_data, dict) else str(auth_data)
                        title = p.get('title', 'Unknown')
                        
                        print(f"{uid:<18} | {vol:<4} | {author:<10} | {title}")
                        
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    print("-" * 60)
    print(f"Total empty poems found: {count}")

if __name__ == "__main__":
    find_empty_poems()