# AIRA — Training our own incident-type model

This folder contains everything used to train **AIRA's own image-classification
model**: a neural network that looks at an incident photo and predicts the
`incident_type` (`fire`, `traffic`, `violent_crime`, `vandalism`,
`suspicious_activity`, `general`). The trained model plugs into the backend and
replaces the rule-based guesser when enabled.

> **Be honest about what is pretrained vs. trained by us.**
> AIRA's *object detection* (YOLOv8) and *captioning* (BLIP) are standard
> pretrained models we use off-the-shelf. The model **we train ourselves** is
> this incident-type classifier. When you present it, present it as exactly
> that — a classifier trained on our own labelled incident dataset using
> transfer learning. Everything in `metrics.json` and `training_log.csv` is the
> real output of your training run on your data; don't quote numbers from a run
> you didn't do.

---

## 1. The method: transfer learning on ResNet-18

Training an image model from zero needs millions of images. We don't have that,
and we don't need it. Instead we use **transfer learning**, the industry-standard
approach for small datasets:

1. Start from **ResNet-18**, a CNN whose convolutional layers were pretrained on
   ImageNet. Those layers already know generic vision — edges, textures, shapes.
2. **Freeze** that backbone so it isn't disturbed.
3. Replace the final layer with a **fresh classification head** sized to our 6
   incident classes.
4. **Train only that head** on *our* labelled incident photos.

So we are genuinely training a model on our own data — we just stand on top of
generic pretrained features instead of relearning them. This trains in minutes
on a normal laptop CPU.

```
incident photo ─▶ [ frozen ResNet-18 backbone ] ─▶ [ our trained head ] ─▶ incident_type + confidence
                    (ImageNet features)               (learned on OUR data)
```

## 2. The dataset

One folder per class; drop labelled images inside:

```
dataset/
  fire/                  *.jpg
  traffic/               *.jpg
  violent_crime/         *.jpg
  vandalism/             *.jpg
  suspicious_activity/   *.jpg
  general/               *.jpg     <- NON-incidents: selfies, objects, scenery
```

Aim for **at least ~30–50 images per class** for a believable demo (more is
better, and keep them varied — different angles, lighting, distances). The
`general` class is what teaches the model to reject non-incident photos.

### Recommended: download a real ~7000-image dataset automatically

`download_dataset.py` pulls **real, public images** from HuggingFace and sorts
them into the class folders for you — no Kaggle login, no manual labelling:

```bash
pip install -r training/requirements-train.txt   # installs the `datasets` lib
python download_dataset.py --per-class 1400 --out dataset   # ~7000 images
```

It streams each source and saves up to `--per-class` images per class, so you
control the total size. Sources (all public, real photos/frames):

| Class | HuggingFace dataset | What the images show |
|---|---|---|
| `fire` | `touati-kamel/forest-fire-dataset` | fire & smoke frames |
| `traffic` | `ikuldeep1/vehicle-damage-fraud-image-balanced` | damaged / crashed vehicles |
| `violent_crime` | `Subh775/WeaponDetection` | guns / knives in scenes |
| `vandalism` | `Programmer-RD-AI/road-issues-detection-dataset` | vandalism, damaged property, litter |
| `general` | `prithivMLmods/OpenScene-Classification` | ordinary non-incident scenes (negatives) |

These are **third-party datasets**, each used under its own licence for the
class it depicts. Present them honestly: *you trained the classifier on these
public datasets* — you did not photograph the images yourself.

> **`suspicious_activity`** has no clean public image-classification dataset
> (only 11 GB / 64 px CCTV frame dumps and video sets), so it is **not**
> auto-downloaded. Drop your own images into `dataset/suspicious_activity/` to
> teach the model that class; otherwise the backend's rule classifier still
> handles it. To add/replace any source, edit the `SOURCES` dict at the top of
> `download_dataset.py`.

### Other ways to build the dataset

| Command | What it does |
|---|---|
| `python prepare_dataset.py --init dataset` | Creates the empty class folders for you to fill. |
| `python prepare_dataset.py --src raw_images --labels labels.csv --out dataset` | Sorts a flat image folder into class folders from a `filename,label` CSV. |
| `python make_sample_dataset.py --out dataset --per-class 20` | Generates a *synthetic* placeholder set just to prove the pipeline runs (NOT real photos — don't present a model trained on these as real). |

## 3. Install + train

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate        # Windows (PowerShell)
pip install -r training/requirements-train.txt

cd training
python train_classifier.py --data dataset --epochs 15
```

Outputs land in `backend/weights/`:

| File | What it is |
|---|---|
| `incident_classifier.pt` | The trained model — load this in the app. |
| `labels.json` | Class-index → class-name mapping. |
| `metrics.json` | Final + best validation accuracy, per-run stats. |
| `training_log.csv` | Per-epoch train/val loss & accuracy — your evidence chart. |

## 4. Check it works

```bash
# Per-class precision/recall/F1 + confusion matrix on a held-out set:
python evaluate.py --data dataset --weights ../weights/incident_classifier.pt

# Try one image and see the prediction your model makes:
python predict.py path/to/photo.jpg
```

## 5. Make the backend USE your trained model

The integration is already wired (`app/ai/incident_cnn.py` +
`app/ai/image_analyzer.py`). Turn it on with two env vars in `backend/.env`:

```env
INCIDENT_CNN_ENABLED=true
# optional — only if the .pt isn't in backend/weights/:
# CLASSIFIER_WEIGHTS=/absolute/path/to/incident_classifier.pt
```

With it on, every uploaded photo is run through **your trained classifier**; its
prediction (when confident enough — see `INCIDENT_CNN_MIN_CONFIDENCE`) sets the
incident's `incident_type`, severity and report narrative. If the model file is
missing or torch isn't installed, the app silently falls back to the rule-based
classifier, so this is safe to enable.

## 6. What to show them (demo script)

1. `dataset/` — your labelled folders (open a few images per class).
2. `train_classifier.py` — walk through transfer learning (sections 1–4 above).
3. Run training live (or show the terminal output) → point at `training_log.csv`
   and `metrics.json` as the real results.
4. `python predict.py some_photo.jpg` → model outputs the incident type live.
5. `INCIDENT_CNN_ENABLED=true` → submit a report in the app and show the
   incident_type now coming from *your* model (`model: ...+cnn` appears in the
   AI analysis appendix of the generated report).

---

### Optional: fine-tuning the YOLOv8 detector instead
If you also want to train the *detector* (not just the classifier), Ultralytics
supports it: annotate images with bounding boxes (e.g. in Roboflow/LabelImg),
write a `data.yaml`, and run `yolo train data=data.yaml model=yolov8n.pt`. The
resulting `best.pt` drops into `ML_WEIGHTS_DIR` as `yolov8n.pt`. This needs box
annotations for every image — much more labelling work than the classifier above,
which only needs images sorted into folders.
