"""Run isolated CPU checks; Linux is required for flock/orchestration tests."""
import subprocess
import sys
from pathlib import Path

scripts=Path(__file__).parent
for path in sorted(scripts.glob('test-*.py')):
    subprocess.run([sys.executable,str(path)],check=True,cwd=scripts)
