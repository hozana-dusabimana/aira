"""Helper to organise raw images into the class-folder layout the trainer needs.

Two common starting points:

A) You already have images sorted loosely and just want to copy/move them into
   the canonical class folders. Edit the mapping below or pass --src and sort by
   hand — this script only guarantees the empty class folders exist:

       python prepare_dataset.py --init dataset

B) You have a CSV of (filename, label) pairs and a flat folder of images:

       python prepare_dataset.py --src raw_images --labels labels.csv --out dataset

   labels.csv format (header required):
       filename,label
       img001.jpg,fire
       img002.jpg,traffic
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

from classes import INCIDENT_CLASSES


def init_empty(out: Path) -> None:
    for cls in INCIDENT_CLASSES:
        (out / cls).mkdir(parents=True, exist_ok=True)
    print(f"Created class folders under {out}:")
    for cls in INCIDENT_CLASSES:
        print(f"  {out / cls}")
    print("\nNow drop your images into the matching folders, then run train_classifier.py")


def from_csv(src: Path, labels_csv: Path, out: Path) -> None:
    for cls in INCIDENT_CLASSES:
        (out / cls).mkdir(parents=True, exist_ok=True)
    copied, skipped = 0, 0
    with open(labels_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fname = (row.get("filename") or "").strip()
            label = (row.get("label") or "").strip()
            if label not in INCIDENT_CLASSES:
                print(f"  skip {fname}: unknown label {label!r}")
                skipped += 1
                continue
            src_path = src / fname
            if not src_path.exists():
                print(f"  skip {fname}: file not found in {src}")
                skipped += 1
                continue
            shutil.copy2(src_path, out / label / src_path.name)
            copied += 1
    print(f"Done. Copied {copied} image(s), skipped {skipped}. Dataset at {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Organise images into class folders")
    parser.add_argument("--init", metavar="OUT", help="Just create empty class folders at OUT")
    parser.add_argument("--src", help="Flat folder of source images (with --labels)")
    parser.add_argument("--labels", help="CSV mapping filename,label (with --src)")
    parser.add_argument("--out", default="dataset", help="Output dataset root")
    args = parser.parse_args()

    if args.init:
        init_empty(Path(args.init))
        return
    if args.src and args.labels:
        from_csv(Path(args.src), Path(args.labels), Path(args.out))
        return
    parser.error("Use --init OUT, or --src DIR --labels CSV [--out DIR]")


if __name__ == "__main__":
    main()
