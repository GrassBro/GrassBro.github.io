#!/usr/bin/env python3
"""
update_gallery.py - Scan image directories and update gallery.html

Put photos in:
  images/animals/  - animal photos
  images/scenery/  - scenery photos
  images/food/     - food photos

Supported formats: jpg, jpeg, png, gif, webp

Usage: python update_gallery.py
"""

import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

def scan_category(category_name):
    folder = IMAGES_DIR / category_name
    if not folder.exists():
        return []
    return sorted(
        [f.name for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXTS]
    )

def main():
    animals = scan_category("animals")
    scenery = scan_category("scenery")
    food = scan_category("food")

    # Build simple manifest
    manifest = {
        "animals": animals,
        "scenery": scenery,
        "food": food,
    }

    # Write JSON manifest
    manifest_path = IMAGES_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest generated: {manifest_path}")
    print(f"  Animals: {len(animals)} photos")
    print(f"  Scenery: {len(scenery)} photos")
    print(f"  Food: {len(food)} photos")
    print("Done. Refresh gallery.html to see changes.")

if __name__ == "__main__":
    main()
