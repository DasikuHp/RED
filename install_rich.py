import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "rich", "--quiet"])
print("Rich installed")