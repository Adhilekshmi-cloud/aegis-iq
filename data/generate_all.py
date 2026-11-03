import subprocess
import sys
import os

data_dir = r"c:\Users\adhil\OneDrive\Desktop\sybil\aegis-knowledge-system\data"

scripts = [
    os.path.join(data_dir, "create_xlsx.py"),
    os.path.join(data_dir, "create_docx.py"),
    os.path.join(data_dir, "create_pptx.py"),
]

for s in scripts:
    print(f"Running {s}...")
    res = subprocess.run([sys.executable, s], capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
    if res.returncode != 0:
        print(f"FAILED: {s} with returncode {res.returncode}")
        sys.exit(res.returncode)

print("All generator scripts executed successfully!")
