"""Quick CLI to test the trained classifier on a single image.

    python predict.py path/to/photo.jpg

Useful in a demo: show an image going in and the predicted incident_type +
confidence coming out of YOUR trained model.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict incident type for one image")
    parser.add_argument("image", help="Path to an image file")
    parser.add_argument("--weights", default=str(Path(__file__).resolve().parents[1] / "weights" / "incident_classifier.pt"))
    parser.add_argument("--img-size", type=int, default=224)
    args = parser.parse_args()

    try:
        import torch
        import torch.nn as nn
        from torchvision import models, transforms
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        print(f"Missing deps: {exc}\nRun: pip install -r training/requirements-train.txt")
        sys.exit(1)

    ckpt = torch.load(args.weights, map_location="cpu")
    class_names = ckpt["classes"]

    model = models.resnet18(weights=None)
    model.fc = nn.Sequential(nn.Dropout(0.3), nn.Linear(model.fc.in_features, len(class_names)))
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    norm = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    tf = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        norm,
    ])
    img = Image.open(args.image).convert("RGB")
    x = tf(img).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(model(x), dim=1)[0]
    ranked = sorted(zip(class_names, probs.tolist()), key=lambda kv: kv[1], reverse=True)

    print(f"\nImage: {args.image}")
    print(f"Prediction: {ranked[0][0]}  (confidence {ranked[0][1]:.1%})\n")
    print("All classes:")
    for name, p in ranked:
        print(f"  {name:22s} {p:.1%}")


if __name__ == "__main__":
    main()
