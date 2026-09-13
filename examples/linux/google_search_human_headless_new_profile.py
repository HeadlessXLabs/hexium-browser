"""Same Google humanize search, headless, fresh profile, highlighter + video."""

from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hexium_browser.config import get_profiles_root

from google_search_human import run


if __name__ == "__main__":
    profile = get_profiles_root() / f"google-search-human-{uuid4().hex[:8]}"
    print(f"New profile: {profile}", flush=True)
    run(
        headless=True,
        user_data_dir=profile,
        recording_name="google_search_human_headless_new_profile",
    )
