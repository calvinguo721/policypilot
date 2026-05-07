import subprocess, re, sys

# Read main.py
result = subprocess.run(['cat', '/var/www/policypilot/engine/main.py'], capture_output=True, text=True)
content = result.stdout

if not content:
    print("ERROR: Could not read main.py")
    sys.exit(1)

changed = False

# Strategy 1: Simple string replacements
replacements = [
    ('daily_limit=1', 'daily_limit=999'),
    ('"daily_limit": 1', '"daily_limit": 999'),
    ("'daily_limit': 1", "'daily_limit': 999"),
]

new_content = content
for old, new in replacements:
    if old in new_content:
        new_content = new_content.replace(old, new)
        changed = True
        print(f"Replaced: {old} -> {new}")

# Strategy 2: Regex for any remaining patterns
if not changed:
    pattern = r'(daily_limit[\s*=:"\']+\d+)'
    matches = re.findall(pattern, new_content)
    print(f"Regex found: {matches}")
    def replace_limit(m):
        return re.sub(r'\d+$', '999', m.group(0))
    new_content2 = re.sub(pattern, replace_limit, new_content)
    if new_content2 != new_content:
        new_content = new_content2
        changed = True
        print("Replaced via regex")

if changed:
    with open('/var/www/policypilot/engine/main.py', 'w') as f:
        f.write(new_content)
    print("SUCCESS: daily_limit changed to 999")
else:
    # Debug: show lines with 'daily' or 'limit'
    print("WARNING: No daily_limit pattern matched. Showing relevant lines:")
    for i, line in enumerate(content.split('\n')):
        if 'daily' in line.lower() or 'limit' in line.lower() or 'rate' in line.lower():
            print(f"  Line {i+1}: {line.strip()}")

# Restart service
result = subprocess.run(['systemctl', 'restart', 'policypilot'], capture_output=True, text=True)
print(f"Service restart: {result.returncode}")
