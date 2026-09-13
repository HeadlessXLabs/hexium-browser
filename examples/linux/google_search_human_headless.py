"""Same Google humanize search as google_search_human.py, headless + highlighter + video."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from google_search_human import run

if __name__ == "__main__":
    run(headless=True, recording_name="google_search_human_headless")
