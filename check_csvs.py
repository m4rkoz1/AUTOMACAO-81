import pandas as pd
import glob

files = glob.glob("test_*.csv")
for f in files:
    try:
        with open(f, "rb") as fl:
            content = fl.read().decode("latin-1", errors="replace")
        lines = content.split('\n')
        print(f"File: {f} -> Lines: {len(lines)}")
    except Exception as e:
        print(f"Failed to read {f}: {e}")
