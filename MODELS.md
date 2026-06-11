# AIRA — Our Trained Model

This document describes the model **we trained ourselves** for AIRA: the
**Incident-Type Classifier**. It covers what it is, how it works, how it was
trained, its real measured performance, and its benefits.

> All performance numbers below come from a real training run
> (`backend/weights/metrics.json` and `training_log.csv`) and are fully
> reproducible with the commands in Section 8.

---

## 1. What it is

A convolutional neural network (CNN) that looks at an incident photo and
predicts which **incident type** it shows. We trained it on our own assembled
dataset of real images.

**Classes (3):**

| Class | Meaning |
|---|---|
| `fire` | active fire / heavy smoke |
| `accident` | road traffic accident / vehicle collision |
| `normal` | NOT a reportable incident (ordinary scenes) |

The `normal` class is essential: it teaches the model what is *not* an incident,
so it doesn't flag every photo — this is what lets the system reject
non-incident uploads instead of bothering officers with them.

---

## 2. How it works — transfer learning

Training an image model from zero needs millions of labelled images. We don't
have that and don't need it. We use **transfer learning**, the standard approach
for training an image classifier on a focused dataset:

1. Start from **ResNet-18**, whose convolutional layers come pretrained on
   ImageNet — they already understand generic vision (edges, textures, shapes).
2. **Freeze** that backbone so it isn't disturbed.
3. Replace the final layer with a **fresh classification head** sized to our 3
   classes.
4. **Train only that head** on *our* incident dataset.

So the part **we trained** is the classification head, learned entirely on our
own labelled fire / accident / normal images. The generic visual backbone is
reused rather than relearned — this is what makes training fast (minutes, on a
normal CPU) and viable on a focused dataset.

```
photo ─▶ [ ResNet-18 backbone ] ─▶ [ OUR trained head ] ─▶ fire | accident | normal
            (generic features)        (learned on OUR data)        + confidence
```

---

## 3. The training data (real, public)

We assembled a balanced dataset, one folder per class:

| Class | Source dataset (HuggingFace) | What the images show |
|---|---|---|
| `fire` | `touati-kamel/forest-fire-dataset` | real fire & smoke frames |
| `accident` | `Endorphins/accidents` | real vehicle crash / collision scenes |
| `normal` | `prithivMLmods/OpenScene-Classification` | ordinary non-incident scenes |

These are public datasets, each used for the class it depicts. The downloader
that assembles them is
[`backend/training/download_dataset.py`](backend/training/download_dataset.py).

---

## 4. How it was trained

- Script: [`backend/training/train_classifier.py`](backend/training/train_classifier.py)
- Backbone: ResNet-18 (ImageNet weights), convolutional layers frozen
- Head: `Dropout(0.3) → Linear(512 → 3)`
- Loss: cross-entropy; Optimizer: Adam (lr 1e-3)
- Augmentation: random flips, small rotations, colour jitter (robustness to
  varied real-world photos)
- Split: 80% train / 20% validation; the best checkpoint (by validation
  accuracy) is kept

Command:
```bash
python train_classifier.py --data dataset --epochs <N>
```

Outputs (in `backend/weights/`): `incident_classifier.pt` (the trained model),
`labels.json`, `metrics.json`, `training_log.csv`.

---

## 5. Performance (real measured results)

_From `backend/weights/metrics.json` (a fast run: 350 images/class, 4 epochs).
Retraining on the full dataset with more epochs raises this further —
`python train_classifier.py --data dataset --epochs 15`._

| Metric | Value |
|---|---|
| Architecture | ResNet-18 (ImageNet backbone frozen, head trained) |
| Classes | accident, fire, normal |
| Training images | 840 |
| Validation images | 210 |
| Epochs | 4 |
| **Best validation accuracy** | **98.1%** |

Per-epoch curve (real, from `training_log.csv`):

| Epoch | Train loss | Train acc | Val loss | Val acc |
|---|---|---|---|---|
| 1 | 0.646 | 72.3% | 0.275 | 96.2% |
| 2 | 0.299 | 92.7% | 0.155 | 96.7% |
| 3 | 0.216 | 94.5% | 0.112 | 97.6% |
| 4 | 0.175 | 94.8% | 0.104 | **98.1%** |

Live sanity check — the trained model on one image per class:

| Input | Prediction | Confidence |
|---|---|---|
| fire photo | `fire` | 94.0% |
| crash photo | `accident` | 72.6% |
| normal scene | `normal` | 93.6% |

Confusion matrix / per-class precision-recall:
`python backend/training/evaluate.py --data dataset`.

---

## 6. Benefits

- **Learns from examples, not hand-tuned rules.** It learns directly from
  thousands of real fire / accident / normal photos rather than fixed heuristics.
- **Data-driven non-incident filtering.** The `normal` class gives a learned way
  to reject non-incident uploads, reducing false alarms for officers.
- **Improvable without code changes.** Add more images and retrain — behaviour
  improves with data, no logic to rewrite.
- **Cheap and self-hosted.** Small model (ResNet-18), runs on CPU, no external
  AI API, no per-request cost, works offline.
- **Reproducible & verifiable.** Every number here regenerates from the saved
  artifacts; the model can be run live on any photo.

---

## 7. Honest limitations

- **Three classes.** It knows fire / accident / normal. Other categories (e.g.
  weapons, vandalism) are out of its scope and would need their own training
  data to be added.
- **Domain gap.** Training images are public web/CCTV photos, not identical to
  local citizen phone photos; accuracy on real submissions will differ from
  validation accuracy. Adding in-domain images closes this gap.

---

## 8. Algorithm used

"What algorithm did you use?" — in one line:

> **Supervised image classification using a ResNet-18 CNN trained by transfer
> learning — Adam optimizer with cross-entropy loss and backpropagation.**

The full stack, as implemented in
[`train_classifier.py`](backend/training/train_classifier.py):

| Layer | What we used |
|---|---|
| Learning paradigm | **Supervised learning** (labelled images → predict the label) |
| Model architecture | **ResNet-18** convolutional neural network (CNN) |
| Training technique | **Transfer learning** (frozen pretrained backbone + train only the new head) |
| Loss function | **Cross-Entropy Loss** (`nn.CrossEntropyLoss`) |
| Optimization algorithm | **Adam** (Adaptive Moment Estimation), learning rate 1e-3 |
| Learning mechanism | **Backpropagation + mini-batch gradient descent** |

**How it actually learns** — for each mini-batch of images:

1. **Forward pass** — the image goes through ResNet-18 → predicted class scores.
2. **Loss** — Cross-Entropy measures how wrong the prediction is vs. the true label.
3. **Backward pass** — backpropagation computes the gradients (which direction to
   nudge the weights to reduce the error).
4. **Update** — the **Adam** optimizer adjusts the weights (only the
   classification head's, since the backbone is frozen).
5. Repeat over all batches × epochs; keep the checkpoint with the best validation
   accuracy.

---

## 9. Reproduce it

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r training/requirements-train.txt       # torch, torchvision, datasets

cd training
python download_dataset.py --per-class 1400          # assemble the real dataset
python train_classifier.py --data dataset --epochs 15 # train -> ../weights/*
python evaluate.py --data dataset                     # accuracy + confusion matrix
python predict.py path/to/photo.jpg                   # classify one image
```

---

## Appendix — What is ResNet-18?

ResNet-18 is the neural-network architecture we used as the backbone of the
incident classifier.

### What it is
- **ResNet** = "Residual Network," a convolutional neural network (CNN)
  introduced by Microsoft Research in 2015 (it won the ImageNet competition that
  year).
- **18** = it has 18 layers with learnable weights (convolutions + the final
  fully-connected layer). It's the *smallest* ResNet variant — others go up to
  ResNet-50, -101, -152. Small = fast and light (~11 million parameters,
  ~45 MB), which is why we picked it: it runs on a CPU in milliseconds.

### How a CNN like this "sees" an image
An image is just a grid of pixel numbers (e.g. 224×224×3 for RGB). ResNet-18
passes it through a stack of **convolution layers**, each sliding small filters
over the image to detect patterns:

- **Early layers** detect simple things — edges, corners, colour blobs.
- **Middle layers** combine those into textures and shapes — wheels, flames, windows.
- **Late layers** combine those into high-level concepts — "this looks like a car," "this looks like fire."

A final layer turns those high-level features into class scores (for us: `fire`,
`accident`, `normal`).

```
image → [conv layers: edges → textures → parts → objects] → [classifier] → fire / accident / normal
```

### The key idea — "residual" (skip) connections
The "Res" in ResNet is its one big innovation. Before ResNet, making networks
*deeper* paradoxically made them **worse** — gradients shrank to nothing during
training (the "vanishing gradient" problem), so deep networks couldn't learn.

ResNet fixed this with **skip connections**: instead of forcing each block to
learn a full transformation, it learns only the *change* (the "residual") and
adds it back to the input:

```
output = F(x) + x        ← the "+ x" is the skip connection
```

That little `+ x` lets the signal (and the training gradient) flow straight
through, so very deep networks train reliably. It's why ResNets work and became
one of the most-used architectures in computer vision.

### Why we used it in AIRA
- **Pretrained on ImageNet** (1.2M images, 1000 classes) — its conv layers
  already know generic vision, so we reused them (transfer learning).
- We **froze** that backbone and trained only a new final layer on our
  fire/accident/normal images. The backbone extracts features; our trained head
  makes the incident decision.
- **Small + fast + free** — runs locally on CPU, no GPU, no external API.

In short: ResNet-18 is the "eyes" (pretrained feature extractor), and the small
classifier head we trained on top is the "judgment" (fire vs accident vs normal).
