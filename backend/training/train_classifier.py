"""Train the AIRA incident-type image classifier.

This is OUR own model: a convolutional neural network that looks at an
incident photo and predicts its ``incident_type`` (fire / traffic /
violent_crime / vandalism / suspicious_activity / general).

We use **transfer learning**: we start from a ResNet-18 backbone pretrained on
ImageNet (generic visual features — edges, textures, shapes), freeze most of it,
and train a fresh classification head on OUR incident dataset. This is the
standard, honest way to train an image classifier with a small dataset: you are
genuinely training a model on your own labelled data, you just don't waste weeks
re-learning low-level vision from scratch.

--------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------
1. Put your labelled images under a dataset root, one folder per class:

       dataset/
         fire/             *.jpg
         traffic/          *.jpg
         violent_crime/    *.jpg
         vandalism/        *.jpg
         suspicious_activity/ *.jpg
         general/          *.jpg

   (Use prepare_dataset.py to split a flat folder, or make_sample_dataset.py
   to generate a tiny synthetic set just to prove the pipeline runs.)

2. Train:

       python train_classifier.py --data dataset --epochs 15

3. Outputs are written to ../weights/ (or --out):
       incident_classifier.pt   <- the trained model (load this in the app)
       labels.json              <- index -> class-name mapping
       metrics.json             <- final accuracy / per-class metrics
       training_log.csv         <- per-epoch loss & accuracy (your evidence)

Everything in metrics.json / training_log.csv is produced by a REAL run on
YOUR data — nothing is hard-coded. That is what you show.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train")


def _import_torch():
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, random_split
        from torchvision import datasets, models, transforms
        return torch, nn, DataLoader, random_split, datasets, models, transforms
    except ImportError as exc:  # pragma: no cover - environment dependent
        logger.error(
            "PyTorch / torchvision not installed. Run:\n"
            "    pip install -r training/requirements-train.txt\n(%s)", exc,
        )
        sys.exit(1)


def build_transforms(transforms, img_size: int):
    """Train-time augmentation + eval-time normalisation.

    ImageNet mean/std are used because the backbone was pretrained on ImageNet.
    Augmentation (flips, rotation, colour jitter) makes the model robust to the
    messy, varied conditions of real citizen phone photos.
    """
    norm = transforms.Normalize(
        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    )
    train_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(12),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        norm,
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        norm,
    ])
    return train_tf, eval_tf


def build_model(torch, nn, models, num_classes: int):
    """ResNet-18 backbone (ImageNet weights) with a fresh, trainable head."""
    weights = models.ResNet18_Weights.IMAGENET1K_V1
    model = models.resnet18(weights=weights)
    # Freeze the convolutional backbone so we only train the new head. This is
    # what makes training fast and viable on a tiny dataset / CPU.
    for p in model.parameters():
        p.requires_grad = False
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, num_classes),
    )
    return model


def run_epoch(torch, nn, model, loader, criterion, optimizer, device, train: bool):
    model.train(train)
    total_loss, correct, seen = 0.0, 0, 0
    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for images, targets in loader:
            images, targets = images.to(device), targets.to(device)
            if train:
                optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, targets)
            if train:
                loss.backward()
                optimizer.step()
            total_loss += float(loss.item()) * images.size(0)
            correct += int((outputs.argmax(1) == targets).sum().item())
            seen += images.size(0)
    if seen == 0:
        return 0.0, 0.0
    return total_loss / seen, correct / seen


def main() -> None:
    parser = argparse.ArgumentParser(description="Train AIRA incident-type classifier")
    parser.add_argument("--data", required=True, help="Dataset root (one folder per class)")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "weights"),
                        help="Output dir for weights + metrics (default: backend/weights)")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--val-split", type=float, default=0.2, help="Fraction held out for validation")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch, nn, DataLoader, random_split, datasets, models, transforms = _import_torch()
    torch.manual_seed(args.seed)

    data_root = Path(args.data)
    if not data_root.exists():
        logger.error("Dataset root does not exist: %s", data_root)
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training device: %s", device)

    train_tf, eval_tf = build_transforms(transforms, args.img_size)

    # ImageFolder reads the class names from the sub-directory names.
    full = datasets.ImageFolder(str(data_root), transform=train_tf)
    class_names = full.classes
    if len(class_names) < 2:
        logger.error("Need at least 2 class folders under %s (found %s)", data_root, class_names)
        sys.exit(1)
    logger.info("Classes (%d): %s", len(class_names), class_names)
    logger.info("Total images: %d", len(full))

    n_val = max(1, int(len(full) * args.val_split))
    n_train = len(full) - n_val
    gen = torch.Generator().manual_seed(args.seed)
    train_ds, val_ds = random_split(full, [n_train, n_val], generator=gen)
    # Validation set should NOT use random augmentation.
    val_ds.dataset.transform = eval_tf  # type: ignore[attr-defined]

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    model = build_model(torch, nn, models, len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss()
    # Only the new head has requires_grad=True, so only those params are optimised.
    optimizer = torch.optim.Adam(
        (p for p in model.parameters() if p.requires_grad), lr=args.lr
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "training_log.csv"

    best_val_acc = 0.0
    history = []
    logger.info("Starting training for %d epochs...", args.epochs)
    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc = run_epoch(torch, nn, model, train_loader, criterion, optimizer, device, train=True)
        va_loss, va_acc = run_epoch(torch, nn, model, val_loader, criterion, optimizer, device, train=False)
        logger.info(
            "epoch %2d/%d | train loss %.4f acc %.3f | val loss %.4f acc %.3f",
            epoch, args.epochs, tr_loss, tr_acc, va_loss, va_acc,
        )
        history.append({
            "epoch": epoch,
            "train_loss": round(tr_loss, 5),
            "train_acc": round(tr_acc, 5),
            "val_loss": round(va_loss, 5),
            "val_acc": round(va_acc, 5),
        })
        # Save the best checkpoint by validation accuracy.
        if va_acc >= best_val_acc:
            best_val_acc = va_acc
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "classes": class_names,
                    "arch": "resnet18",
                    "img_size": args.img_size,
                },
                out_dir / "incident_classifier.pt",
            )

    # Write evidence artefacts -------------------------------------------------
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "train_acc", "val_loss", "val_acc"])
        writer.writeheader()
        writer.writerows(history)

    (out_dir / "labels.json").write_text(
        json.dumps({str(i): name for i, name in enumerate(class_names)}, indent=2)
    )
    (out_dir / "metrics.json").write_text(json.dumps({
        "best_val_accuracy": round(best_val_acc, 5),
        "final_epoch": history[-1] if history else None,
        "num_classes": len(class_names),
        "classes": class_names,
        "num_images": len(full),
        "train_images": n_train,
        "val_images": n_val,
        "epochs": args.epochs,
        "arch": "resnet18 (ImageNet pretrained backbone, trained head)",
    }, indent=2))

    logger.info("Done. Best val accuracy: %.3f", best_val_acc)
    logger.info("Saved -> %s", out_dir / "incident_classifier.pt")
    logger.info("Metrics -> %s | Log -> %s", out_dir / "metrics.json", log_path)


if __name__ == "__main__":
    main()
