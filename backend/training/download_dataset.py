"""Download a real, labelled incident dataset from public HuggingFace datasets
and organise it into the class-folder layout train_classifier.py expects.

Each AIRA incident class is mapped to a public HF image dataset whose images
depict that class. We stream each dataset (no full download) and save up to
``--per-class`` images into ``dataset/<class>/``. Streaming + a per-class cap is
what keeps this to a few thousand images instead of pulling entire multi-GB sets.

    pip install -r training/requirements-train.txt   # installs `datasets`
    python download_dataset.py --per-class 1400 --out dataset
    python train_classifier.py --data dataset --epochs 15

Sources (all public, real photos/frames):
  fire      -> Vertex-Test/FireSmokeDataset          (fire & smoke images)
  accident  -> Endorphins/accidents                  (real vehicle crash scenes)
  normal    -> prithivMLmods/OpenScene-Classification (ordinary non-incident scenes)

`normal` is the negative class: it teaches the model what is NOT a reportable
incident, so it doesn't flag every photo. The class names map to the backend's
incident_type vocabulary as: accident -> traffic, normal -> general.

Be honest when you present this: these are REAL third-party datasets, each used
under its own licence (mostly CC0 / open) for the class it depicts. You trained
the classifier on them; you did not author the photos.
"""
from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("download")

# class -> LIST of sources. Each source is (repo_id, split, image_column).
# config=None uses the default config. Multiple sources per class let us
# ACCUMULATE images from several public datasets until the per-class target is
# reached; if one repo is unavailable/small we simply move on to the next.
#
# ``accident`` is the class the reviewer asked us to focus on, so it has the
# most sources — we pull crash/collision photos from several datasets to give
# the model the widest, most varied view of real accident scenes.
SOURCES: dict[str, list[dict]] = {
    "normal": [
        {"repo": "prithivMLmods/OpenScene-Classification", "split": "train", "image_col": "image", "fast": True},
    ],
    "accident": [
        # Real vehicle-crash scenes (train/valid/test pulled separately to
        # maximise the number of distinct accident photos from this source).
        {"repo": "Endorphins/accidents", "split": "train", "image_col": "image", "fast": False},
        {"repo": "Endorphins/accidents", "split": "validation", "image_col": "image", "fast": False},
        {"repo": "Endorphins/accidents", "split": "test", "image_col": "image", "fast": False},
        # CCTV / dashcam traffic-accident frames — adds varied real-world
        # angles, lighting and road scenes so the model generalises beyond
        # close-up crash photos.
        {"repo": "justjuu/traffic-accident-cctv-object-detection", "split": "train", "image_col": "image", "fast": False},
        {"repo": "justjuu/traffic-accident-cctv-object-detection", "split": "validation", "image_col": "image", "fast": False},
        {"repo": "justjuu/traffic-accident-cctv-object-detection", "split": "test", "image_col": "image", "fast": False},
    ],
    "fire": [
        {"repo": "touati-kamel/forest-fire-dataset", "split": "train", "image_col": "image", "fast": False},
    ],
}

# Per-class image target. Accident is over-weighted on purpose: the reviewer
# asked us to make the model reliable on ACCIDENTS specifically, so we feed it
# more accident examples than the other classes (the training split stays
# usefully balanced because fire/normal still have plenty).
PER_CLASS_TARGET: dict[str, int] = {
    "accident": 2500,
    "fire": 1500,
    "normal": 1500,
}


def _to_pil(value):
    """Coerce a streamed image cell into a PIL.Image (RGB)."""
    from PIL import Image

    if value is None:
        return None
    if isinstance(value, Image.Image):
        return value.convert("RGB")
    if isinstance(value, dict):
        if value.get("bytes"):
            return Image.open(io.BytesIO(value["bytes"])).convert("RGB")
        if value.get("path"):
            return Image.open(value["path"]).convert("RGB")
    return None


def _download_from_source(load_dataset, name, spec, cls_dir, per_class, min_side, saved, min_pixels) -> int:
    """Stream one source dataset into ``cls_dir`` until ``per_class`` is met.

    ``saved`` is the running count of images already in the folder (from earlier
    sources). Returns the new running count.
    """
    repo, split, col = spec["repo"], spec["split"], spec["image_col"]
    speed = "fast (parquet)" if spec.get("fast") else "slower (per-file index) — be patient"
    logger.info("[%s] streaming %s split=%s [%s] target=%d (have %d) ...",
                name, repo, split, speed, per_class, saved)
    try:
        ds = load_dataset(repo, name=spec.get("config"), split=split, streaming=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[%s] could not open %s (%s). Trying next source.", name, repo, exc)
        return saved

    start = saved
    seen = 0
    for row in ds:
        if saved >= per_class:
            break
        seen += 1
        try:
            img = _to_pil(row.get(col))
            if img is None:
                continue
            if min(img.size) < min_side:  # drop tiny/thumbnail images
                continue
            if img.size[0] * img.size[1] < min_pixels:
                continue
            img.save(cls_dir / f"{name}_{saved:05d}.jpg", quality=88)
            saved += 1
            if saved % 50 == 0:
                logger.info("[%s] %d/%d saved...", name, saved, per_class)
        except Exception:  # noqa: BLE001 - skip a bad row, keep going
            continue
        if seen > 2000 and saved == start:
            logger.warning("[%s] read %d rows from %s without a usable image; moving on.",
                           name, seen, repo)
            break
    logger.info("[%s] +%d from %s (running total %d)", name, saved - start, repo, saved)
    return saved


def download_class(load_dataset, name: str, specs: list, out_dir: Path, per_class: int, min_side: int, min_pixels: int) -> int:
    cls_dir = out_dir / name
    cls_dir.mkdir(parents=True, exist_ok=True)
    saved = len(list(cls_dir.glob("*.jpg")))
    if saved >= per_class:
        logger.info("[%s] already has %d images (>= %d) — skipping.", name, saved, per_class)
        return saved

    for spec in specs:
        if saved >= per_class:
            break
        saved = _download_from_source(
            load_dataset, name, spec, cls_dir, per_class, min_side, saved, min_pixels
        )
    if saved < per_class:
        logger.warning("[%s] only gathered %d/%d images from %d source(s).",
                       name, saved, per_class, len(specs))
    logger.info("[%s] done: %d images in %s", name, saved, cls_dir)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a real incident dataset from HuggingFace")
    parser.add_argument("--out", default="dataset", help="Output dataset root")
    parser.add_argument("--per-class", type=int, default=0,
                        help="Override target images per class. 0 (default) uses the per-class "
                             "targets in PER_CLASS_TARGET (accident is weighted higher).")
    parser.add_argument("--min-side", type=int, default=80, help="Skip images whose shorter side is below this")
    parser.add_argument("--min-pixels", type=int, default=12000,
                        help="Skip images with fewer than this many total pixels (drops thumbnails)")
    parser.add_argument("--classes", nargs="*", default=list(SOURCES.keys()),
                        help="Subset of classes to download (default: all configured)")
    args = parser.parse_args()

    try:
        from datasets import load_dataset
    except ImportError:
        logger.error(
            "The `datasets` library is required. Install it:\n"
            "    pip install -r training/requirements-train.txt\n"
            "(or: pip install datasets pillow)"
        )
        sys.exit(1)

    out_dir = Path(args.out)
    totals = {}
    for name in args.classes:
        if name not in SOURCES:
            logger.warning("No source configured for class %r — skipping. (Add it to SOURCES.)", name)
            continue
        target = args.per_class if args.per_class > 0 else PER_CLASS_TARGET.get(name, 1500)
        totals[name] = download_class(
            load_dataset, name, SOURCES[name], out_dir, target, args.min_side, args.min_pixels
        )

    grand = sum(totals.values())
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE — %d images total across %d classes:", grand, len(totals))
    for name, n in totals.items():
        logger.info("    %-20s %d", name, n)
    logger.info("Dataset root: %s", out_dir.resolve())
    logger.info("Next: python train_classifier.py --data %s --epochs 15", args.out)


if __name__ == "__main__":
    main()
