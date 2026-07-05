#!/usr/bin/env python3
"""
update_posts.py - Scan posts/ directory and generate manifest.json

Each post is a .md file. The first line (H1) is used as the title,
and the second line should contain a date in YYYY-MM-DD format.

Usage: python update_posts.py
"""

import os
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
POSTS_DIR = BASE_DIR / "posts"

def extract_metadata(filepath):
    """Extract title and date from a markdown post file."""
    with open(filepath, "r") as f:
        lines = f.readlines()

    title = None
    date_str = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not title and line.startswith("# "):
            title = line[2:].strip()
        elif not date_str and re.match(r"\d{4}-\d{2}-\d{2}", line.strip("* ")):
            date_str = re.search(r"(\d{4}-\d{2}-\d{2})", line).group(1)
        if title and date_str:
            break

    slug = filepath.stem
    return {
        "slug": slug,
        "title": title or slug.replace("-", " ").title(),
        "date": date_str or "Unknown",
        "file": filepath.name
    }

def main():
    if not POSTS_DIR.exists():
        print(f"Creating {POSTS_DIR}")
        POSTS_DIR.mkdir()

    posts = []
    for f in sorted(POSTS_DIR.glob("*.md"), reverse=True):
        post = extract_metadata(f)
        posts.append(post)

    manifest_path = POSTS_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(posts, f, indent=2)

    print(f"Manifest generated: {manifest_path}")
    for p in posts:
        print(f"  [{p['date']}] {p['title']} ({p['file']})")
    print("Done. Refresh blog.html to see changes.")

if __name__ == "__main__":
    main()
