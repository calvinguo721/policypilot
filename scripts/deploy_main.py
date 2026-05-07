import base64, os

script_dir = os.path.dirname(os.path.abspath(__file__))
b64_file = os.path.join(script_dir, 'main_py_b64.txt')
target = '/var/www/policypilot/engine/main.py'

with open(b64_file, 'r') as f:
    encoded = f.read().strip()

content = base64.b64decode(encoded).decode('utf-8')

# Verify it's valid Python
import ast
try:
    ast.parse(content)
    print("Python syntax check: OK")
except SyntaxError as e:
    print(f"Python syntax check FAILED: {e}")
    exit(1)

# Backup old file
import shutil
if os.path.exists(target):
    shutil.copy2(target, target + '.bak')
    print(f"Backed up {target} to {target}.bak")

# Write new file
with open(target, 'w') as f:
    f.write(content)
print(f"Written {len(content)} bytes to {target}")

# Restart service
import subprocess
result = subprocess.run(['systemctl', 'restart', 'policypilot'], capture_output=True, text=True)
print(f"Service restart: exit={result.returncode}")

import time
time.sleep(3)

# Check service status
result2 = subprocess.run(['systemctl', 'is-active', 'policypilot'], capture_output=True, text=True)
print(f"Service status: {result2.stdout.strip()}")
