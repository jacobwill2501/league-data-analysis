"""
Download champion icons from Data Dragon and save them locally.

Usage:
    python3 src/download_icons.py
    # or from web/:
    npm run download-icons
"""
import os
import sys
import time

import requests

# Allow importing from src/config.py regardless of working directory
sys.path.insert(0, os.path.dirname(__file__))
from config import DDRAGON_VERSIONS_URL, DDRAGON_CHAMPION_URL

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'web', 'public', 'images', 'champions')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Fetching latest DDragon version...")
    version = requests.get(DDRAGON_VERSIONS_URL, timeout=10).json()[0]
    print(f"Using version: {version}")

    print("Fetching champion list...")
    champion_data = requests.get(DDRAGON_CHAMPION_URL.format(version=version), timeout=10).json()
    champions = champion_data['data']

    total = len(champions)
    skipped = 0
    downloaded = 0
    failed = 0

    print(f"Found {total} champions. Downloading icons...")

    for champ_id, champ_info in champions.items():
        img_key = champ_info['id']  # DDragon filename key (e.g. "MonkeyKing" for Wukong)
        dest = os.path.join(OUTPUT_DIR, f"{img_key}.png")

        if os.path.exists(dest):
            skipped += 1
            continue

        url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{img_key}.png"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            with open(dest, 'wb') as f:
                f.write(resp.content)
            downloaded += 1
            print(f"  [{downloaded + skipped}/{total}] {img_key}.png")
        except Exception as e:
            print(f"  FAILED {img_key}: {e}")
            failed += 1

        time.sleep(0.05)

    print()
    print("--- Summary ---")
    print(f"DDragon version : {version}")
    print(f"Total champions : {total}")
    print(f"Downloaded      : {downloaded}")
    print(f"Skipped (exist) : {skipped}")
    print(f"Failed          : {failed}")
    print(f"Output dir      : {os.path.abspath(OUTPUT_DIR)}")
    if downloaded > 0 or skipped > 0:
        print()
        print(f"Update DDRAGON_VERSION in web/src/components/ChampionIcon.tsx to '{version}'")


if __name__ == '__main__':
    main()
