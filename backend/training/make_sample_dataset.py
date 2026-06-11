"""Generate a TINY synthetic dataset so you can prove the training pipeline runs
end-to-end before you have real photos.

IMPORTANT: these are procedurally-drawn placeholder images (coloured shapes),
NOT real incident photos. A model trained on them is only a smoke-test that the
code works — it is NOT a credible incident detector. For the real model you
present, replace these folders with genuine labelled photos and re-run the
trainer. Do not represent a model trained on this synthetic data as trained on
real incidents.

    python make_sample_dataset.py --out dataset --per-class 20
    python train_classifier.py --data dataset --epochs 5
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from classes import INCIDENT_CLASSES

# A distinctive palette per class so the smoke-test model has *some* signal to
# learn (purely so accuracy isn't random — it proves the training loop works).
_PALETTE = {
    "fire": [(200, 60, 20), (230, 120, 30), (180, 40, 10)],
    "traffic": [(90, 90, 100), (120, 120, 130), (70, 80, 110)],
    "violent_crime": [(40, 40, 40), (80, 20, 20), (60, 60, 70)],
    "vandalism": [(110, 90, 60), (130, 110, 80), (90, 80, 60)],
    "suspicious_activity": [(20, 20, 40), (30, 30, 55), (15, 15, 30)],
    "general": [(150, 170, 190), (180, 200, 210), (160, 180, 200)],
}


def _draw_image(seed: int, base: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (256, 256), base)
    draw = ImageDraw.Draw(img)
    # A few deterministic-but-varied shapes so images within a class differ.
    rng = (seed * 2654435761) & 0xFFFFFFFF
    for i in range(5):
        rng = (rng * 1103515245 + 12345) & 0xFFFFFFFF
        x = rng % 200
        rng = (rng * 1103515245 + 12345) & 0xFFFFFFFF
        y = rng % 200
        rng = (rng * 1103515245 + 12345) & 0xFFFFFFFF
        size = 20 + rng % 60
        shade = tuple(min(255, max(0, c + (i * 13 - 26))) for c in base)
        draw.ellipse([x, y, x + size, y + size], fill=shade)
    return img


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic smoke-test dataset")
    parser.add_argument("--out", default="dataset")
    parser.add_argument("--per-class", type=int, default=20)
    args = parser.parse_args()

    out = Path(args.out)
    for cls in INCIDENT_CLASSES:
        cls_dir = out / cls
        cls_dir.mkdir(parents=True, exist_ok=True)
        palette = _PALETTE.get(cls, [(128, 128, 128)])
        for i in range(args.per_class):
            base = palette[i % len(palette)]
            img = _draw_image(seed=hash((cls, i)) & 0xFFFFFFFF, base=base)
            img.save(cls_dir / f"{cls}_{i:03d}.jpg", quality=85)
    total = len(INCIDENT_CLASSES) * args.per_class
    print(f"Wrote {total} synthetic images to {out} ({args.per_class}/class).")
    print("NOTE: synthetic placeholders only — replace with real photos for a real model.")


if __name__ == "__main__":
    main()
