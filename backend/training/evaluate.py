"""Evaluate a trained incident classifier on a held-out / test dataset and print
a confusion matrix + per-class precision/recall/F1.

    python evaluate.py --data dataset --weights ../weights/incident_classifier.pt

The classification report it prints is real evidence you can screenshot/quote
when you show how the model performs.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the incident classifier")
    parser.add_argument("--data", required=True, help="Dataset root (class folders)")
    parser.add_argument("--weights", default=str(Path(__file__).resolve().parents[1] / "weights" / "incident_classifier.pt"))
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    try:
        import torch
        from torch.utils.data import DataLoader
        from torchvision import datasets, models, transforms
        from sklearn.metrics import classification_report, confusion_matrix
    except ImportError as exc:  # pragma: no cover
        print(f"Missing deps: {exc}\nRun: pip install -r training/requirements-train.txt")
        sys.exit(1)

    ckpt = torch.load(args.weights, map_location="cpu")
    class_names = ckpt["classes"]

    norm = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    tf = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        norm,
    ])
    ds = datasets.ImageFolder(args.data, transform=tf)
    if ds.classes != class_names:
        print(f"WARNING: dataset classes {ds.classes} != model classes {class_names}")
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False)

    import torch.nn as nn
    model = models.resnet18(weights=None)
    model.fc = nn.Sequential(nn.Dropout(0.3), nn.Linear(model.fc.in_features, len(class_names)))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    y_true, y_pred = [], []
    with torch.no_grad():
        for images, targets in loader:
            outputs = model(images)
            y_pred.extend(outputs.argmax(1).tolist())
            y_true.extend(targets.tolist())

    print("\n=== Classification report ===")
    print(classification_report(y_true, y_pred, target_names=class_names, zero_division=0))
    print("=== Confusion matrix (rows=true, cols=pred) ===")
    print("classes:", class_names)
    print(confusion_matrix(y_true, y_pred))


if __name__ == "__main__":
    main()
