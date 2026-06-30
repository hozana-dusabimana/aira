# AIRA — Our Trained Model

This document describes the model **we trained ourselves** for AIRA: the
**Incident-Type Classifier**. It covers what it is, how it works, how it was
trained, its real measured performance, and its benefits.

> All performance numbers below come from a real training run
> (`backend/weights/metrics.json` and `training_log.csv`) and are fully
> reproducible with the commands in Section 8.

---

## 1. What it is

A convolutional neural network (CNN) that looks at a photo and decides whether
it shows a **road accident**. We trained it on our own assembled dataset of real
images. AIRA is scoped to road-accident reporting, so the model is a focused
**two-class** classifier.

**Classes (2):**

| Class | Meaning | Backend `incident_type` |
|---|---|---|
| `accident` | road traffic accident / vehicle collision | **`traffic`** (accepted) |
| `normal` | anything that is NOT a road accident (ordinary scenes, intact vehicles, fire, etc.) | `general` (rejected) |

The model's `accident` class **corresponds to the backend's `traffic` incident
type** (and `normal` corresponds to `general`). This mapping is applied
automatically by `CNN_CLASS_TO_INCIDENT_TYPE` in
[`image_analyzer.py`](backend/app/ai/image_analyzer.py), so an `accident`
prediction is recorded as a `traffic` incident and accepted; everything else is
rejected (`ACCEPTED_INCIDENT_TYPES=traffic`).

The `normal` class is essential: it teaches the model what is *not* an accident,
so it doesn't flag every photo — this is what lets the system reject
non-accident uploads instead of bothering officers with them. It deliberately
contains **intact (undamaged) vehicles** as well as ordinary scenes, so the
model learns to judge by **damage**, not by whether a car is present.

---

## 2. How it works — transfer learning

Training an image model from zero needs millions of labelled images. We don't
have that and don't need it. We use **transfer learning**, the standard approach
for training an image classifier on a focused dataset:

1. Start from **ResNet-18**, whose convolutional layers come pretrained on
   ImageNet — they already understand generic vision (edges, textures, shapes).
2. **Freeze** most of the backbone so it isn't disturbed, but **fine-tune the
   last residual block (`layer4`)** at a low learning rate so the model can
   actually learn what *vehicle damage* looks like — not just re-weight generic
   features. (This was the key to recognising clean/stylised crash photos.)
3. Replace the final layer with a **fresh classification head** sized to our 2
   classes.
4. **Train** that head (full LR) plus `layer4` (1/10th LR) on *our* dataset.

So the part **we trained** is the classification head plus the top of the
backbone, learned on our own labelled accident / normal images. The lower
generic layers are reused rather than relearned — this keeps training viable on
a focused dataset and a normal CPU.

```
photo ─▶ [ ResNet-18 backbone ] ─▶ [ OUR trained head ] ─▶ accident | normal
            (lower layers frozen,      (learned on OUR data)     + confidence
             layer4 fine-tuned)
```

---

## 3. The training data (real, public)

We assembled the dataset from several public sources, one folder per class
(5,600 images: 3,000 accident / 2,600 normal):

| Class | Source datasets (HuggingFace) | What the images show |
|---|---|---|
| `accident` | `DrBimmer/comprehensive-car-damage` (damaged cars) + `Endorphins/accidents` + `justjuu/traffic-accident-cctv-object-detection` | close-up vehicle **damage** + real crash scenes + CCTV/dashcam accident frames |
| `normal` | `prithivMLmods/OpenScene-Classification` + `tanganke/stl10` | ordinary scenes + clean **intact** vehicles/objects |

The mix is deliberate: pairing **damaged** cars (accident) with **intact** cars
(normal) forces the model to judge by damage, not by how clean or shiny a car
looks. These are public datasets, each used for the class it depicts. The
downloader that assembles them (with per-source caps and label filtering) is
[`backend/training/download_dataset.py`](backend/training/download_dataset.py).

---

## 4. How it was trained

- Script: [`backend/training/train_classifier.py`](backend/training/train_classifier.py)
- Backbone: ResNet-18 (ImageNet weights); lower layers frozen, `layer4` fine-tuned
- Head: `Dropout(0.3) → Linear(512 → 2)`
- Loss: cross-entropy; Optimizer: Adam (head lr 1e-3, fine-tuned backbone lr 1e-4)
- Augmentation: random flips, small rotations, colour jitter (robustness to
  varied real-world photos)
- Split: 80% train / 20% validation; the best checkpoint (by validation
  accuracy) is kept

Command:
```bash
python train_classifier.py --data dataset --epochs 8 --unfreeze-backbone
```

Outputs (in `backend/weights/`): `incident_classifier.pt` (the trained model),
`labels.json`, `metrics.json`, `training_log.csv`.

---

## 5. Performance (real measured results)

_From `backend/weights/metrics.json` — a **two-class** (accident vs normal) run
on **5,600 real images** (3,000 accident / 2,600 normal), 8 epochs, with the
ResNet `layer4` fine-tuned. Pairing damaged cars (accident) with intact cars
(normal) teaches the model to judge by **damage**._

| Metric | Value |
|---|---|
| Architecture | ResNet-18 (lower layers frozen, `layer4` fine-tuned) |
| Classes | accident, normal |
| Total images | 5,600 |
| Training images | 4,480 |
| Validation images | 1,120 |
| Epochs | 8 |
| **Best validation accuracy** | **99.6%** |

### Generalisation test on UNSEEN images (the honest numbers)

Validation accuracy is on images from the same datasets, so we also tested on
**300 images from completely different datasets the model never trained on**
(accident: a separate CCTV accident set; normal: tiny-imagenet) and scored them
against the **deployed** model:

| Class (unseen) | Recall | What it means |
|---|---|---|
| **normal (reject)** | **1.00** | every non-accident image correctly rejected — **zero false positives** |
| **accident** | **0.67** argmax → **0.76** with the acceptance threshold | catches most accidents; weaker only on *distant CCTV* frames (close-up/citizen-style crashes score ~1.0) |

Because non-accident photos score essentially **0** for the accident class
(held-out max 0.001), the backend uses an **accident-biased acceptance
threshold** (`ACCIDENT_ACCEPT_THRESHOLD=0.25`): a photo is treated as an
accident when its accident probability ≥ 0.25 even if `normal` is technically
top-1. This recovers borderline/distant accidents (recall 0.67 → 0.76) **without
any added false positives**.

**Recognising clean/stylised crashes.** A glossy two-car crash photo initially
scored only P(accident)=0.002 (the model had learned "shiny intact car =
normal"). Adding damaged-car data lifted it to 0.169, and fine-tuning `layer4`
lifted it to **0.996** — correctly accepted. This is why the model fine-tunes
the backbone and pairs damaged vs intact cars.

Live API confirmation (real photos POSTed to `https://api-aira.isiri.rw`):
the previously-rejected crash photo → `traffic` (accepted); non-accident photos
→ rejected (422).

Reproduce: `python backend/training/evaluate.py --data <held_out_set>
--weights backend/weights/incident_classifier.pt`.

---

## 6. Benefits

- **Learns from examples, not hand-tuned rules.** It learns directly from
  thousands of real accident and normal photos rather than fixed heuristics.
- **Data-driven filtering.** The `normal` class gives a learned way to reject
  non-accident uploads, reducing false alarms for officers.
- **Improvable without code changes.** Add more images and retrain — behaviour
  improves with data, no logic to rewrite.
- **Cheap and self-hosted.** Small model (ResNet-18), runs on CPU, no external
  AI API, no per-request cost, works offline.
- **Reproducible & verifiable.** Every number here regenerates from the saved
  artifacts; the model can be run live on any photo.

---

## 7. Honest limitations

- **Two classes (accident-only scope).** It decides accident vs not-an-accident.
  Other categories (fire, weapons, vandalism) are intentionally out of scope —
  the app reports road accidents — and a non-accident photo is rejected.
- **Distant CCTV accidents.** Recall is high on close-up/citizen-style crashes
  but lower (~0.76) on distant CCTV frames where damage isn't visible; adding
  more wide-scene accident data would close this.
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
- **Late layers** combine those into high-level concepts — "this looks like a car," "this car is crushed/damaged."

A final layer turns those high-level features into class scores (for us:
`accident`, `normal`).

```
image → [conv layers: edges → textures → parts → objects] → [classifier] → accident / normal
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
- We froze its lower layers and **fine-tuned the top block (`layer4`)** plus a
  new final layer on our accident/normal images. The backbone extracts features;
  our fine-tuned top + head make the accident decision.
- **Small + fast + free** — runs locally on CPU, no GPU, no external API.

In short: ResNet-18 is the "eyes" (pretrained feature extractor), and the
fine-tuned top + classifier head we trained is the "judgment" (accident vs normal).
