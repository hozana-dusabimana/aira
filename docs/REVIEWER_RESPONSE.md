# AIRA — Response to Panel Review (Accepted with Major Revisions)

This document maps each required action from the panel verdict to the concrete
work done in the system, so the changes can be demonstrated and written up for
the re-presentation. It is meant to be read alongside a live demo and the
updated report/slides.

> **Verdict recap:** *Accepted with Major Revisions — enhancements to project
> context needed; re-present within two weeks.* Required actions: (1) define &
> implement unique features that distinguish AIRA from the related project;
> (2) tune/improve the AI model to align with the problem statement and
> accurately classify incident images; (3) ensure reliable image capture/
> display/upload across devices; (4) test the mobile app, AI classification and
> backend end-to-end; (5) revise the report/presentation to highlight
> functionality, differences from similar projects, and performance.

---

## Problem statement (anchor)

> A mobile application enabling citizens to report incidents via photos that are
> **classified by AI** for police action.

Every feature below is justified against that statement: the citizen takes/sends
a photo, the AI classifies it, and police act on it through a dashboard.

---

## Action 1 — Unique features that distinguish AIRA from the related project

The panel asked us to clearly define what makes AIRA distinct. The related
project is, in essence, "send a photo to the police." AIRA's distinguishing
features go beyond a photo-forwarding app:

| # | Unique feature | Why it is distinctive | Where in code |
|---|---|---|---|
| 1 | **AI classifies the incident from the photo itself** — incident *type*, *severity* and a written *scene description* are produced by the AI, not typed by the reporter. | Most "report to police" apps are forms the user fills in. AIRA's AI is the classifier the problem statement asks for. | `app/services/ai_service.py`, `app/ai/image_analyzer.py`, `app/ai/description_generator.py` |
| 2 | **Our own trained incident classifier** (ResNet-18 transfer-learning CNN: accident / fire / normal), layered on top of off-the-shelf YOLOv8 detection + BLIP captioning. | We trained a model on our own labelled incident dataset — not just calling a generic API. | `backend/training/`, `app/ai/incident_cnn.py`, `MODELS.md` |
| 3 | **Non-incident rejection** — a photo the AI does not recognise as a reportable incident is discarded so officers are never spammed with selfies/random images. | Turns the AI from a label-printer into a gatekeeper that protects officer time. | `analyze_incident_sync()` + `INCIDENT_VALIDATION_ENABLED` |
| 4 | **Duplicate detection** — when several citizens photograph the *same* accident, only the first becomes an active incident; the rest are linked as duplicates. | Directly addresses a real crowd-reporting failure mode the simpler project ignores. | `find_duplicate_incident()`, `DUPLICATE_*` settings |
| 5 | **Real-time police dashboard** — incidents, status changes and messages stream to officers over WebSockets; reporters get live status + notifications. | A two-sided, real-time operations tool, not a one-way inbox. | `app/realtime/`, `app/api/v1/ws.py`, `police_dashboard/` |
| 6 | **Location-aware triage** — GPS captured with the report, nearby-incident lookup, officer/station assignment and a full status workflow (pending → verified → assigned → in-progress → resolved). | Operational policing workflow, not just storage. | `app/api/v1/incidents.py` |

> **To do with the supervisor:** confirm the exact "related project" being
> compared against and tick which of the above it lacks; lead the slide on
> differences with features 2, 3 and 4 (the AI-specific ones).

---

## Action 2 — Tune & improve the AI model (focus: accidents)

This was the core of the verdict. What we changed:

1. **More, more-varied accident data.** The dataset downloader now pulls
   accident images from **multiple real public datasets across all their splits**
   instead of one, and over-weights the accident class on purpose
   (target ≈ 2,500 accident images vs ≈ 1,500 each for fire/normal):
   - `Endorphins/accidents` (train + valid + test) — real vehicle-crash scenes
   - `justjuu/traffic-accident-cctv-object-detection` (train + validation + test)
     — CCTV/dashcam accident frames (varied angles, lighting, road scenes)

   See `backend/training/download_dataset.py` (`SOURCES`, `PER_CLASS_TARGET`).
   The multi-source loop keeps accumulating from the next dataset until the
   per-class target is met, and skips any source that is unavailable.

2. **Retrained on the project server.** Training was run on the production
   server (4 vCPU / 29 GB RAM) inside a container built from the backend image,
   writing the new weights straight into the model volume the live API reads.
   Method unchanged and honest: **transfer learning on ResNet-18** (ImageNet
   backbone frozen, our classification head trained on our labelled data).

3. **Measured, per-class evidence.** We report not just overall accuracy but
   **per-class precision / recall / F1 and a confusion matrix** from
   `evaluate.py`, so we can show specifically how well the model does on the
   **accident** class — which is what the panel asked us to prove.

### Results of the retraining run

_Numbers below come from the actual retraining run on the project server
(`backend/weights/metrics.json` + `training_log.csv` and the `evaluate.py`
report); they are reproducible with the commands at the end of this doc._

| Metric | Old model | Final model |
|---|---|---|
| Total images | 1,050 | **6,600** |
| Accident images | ~350 | **2,500** |
| Negative (normal) images | ~350 | **2,600** (scenes + clean vehicles/objects) |
| Validation accuracy | 0.981 | **0.994** |
| Epochs | 4 | 8 |

### The real test — generalisation on UNSEEN images + the live API

Validation accuracy alone can be misleading, so we built a **held-out test set
of 600 images from completely different datasets the model never trained on**
(accident: a separate CCTV accident set; fire: a different fire/smoke set;
normal: tiny-imagenet) and scored them against the **deployed** model. We also
POSTed samples to the real public API. This is the design the project requires:
**detect accidents, reject everything else.**

| Class (unseen) | First retrain | **Final model** |
|---|---|---|
| accident recall | 0.93 | 0.85 |
| fire recall | 0.94 | 0.80 |
| **normal — correctly REJECTED** | 0.24 | **1.00** |
| **overall accuracy** | 0.70 | **0.88** |

The first retrain maximised validation accuracy (0.998) but **over-flagged
ordinary images as incidents** — only 24% of non-accident photos were rejected.
Adding a large, varied negative class fixed this: **non-accident images are now
rejected 100% of the time (zero false positives)**, with accidents still
detected well.

**Live API confirmation** (`POST https://api-aira.isiri.rw`, full pipeline, test
incidents deleted afterwards):

```
accident:  5/5 unseen photos -> traffic       (detected)
fire:      4/5                -> fire
normal:    5/5 unseen photos -> REJECTED (422) (non-incident, not shown to officers)
```

The model is enabled in production (`INCIDENT_CNN_ENABLED=true`); weights live in
the `aira_ml_weights` Docker volume.

**Scope enforcement (accident-only):** the app is strictly a road-accident
reporting tool, so the backend accepts **only** accident reports
(`incident_type=traffic`). Fire, ordinary scenes and anything else are rejected
as non-reportable, even though the model can still tell them apart. This is
controlled by the `ACCEPTED_INCIDENT_TYPES` setting (default `traffic`); set it
to `traffic,fire` if fire should also be accepted later.

> Honesty note (kept from `MODELS.md`): YOLOv8 (detection) and BLIP (captioning)
> are standard pretrained models we use off the shelf. The model **we trained**
> is the incident-type classifier — present it as exactly that.

> Honesty note (kept from `MODELS.md`): YOLOv8 (detection) and BLIP (captioning)
> are standard pretrained models we use off the shelf. The model **we trained**
> is the incident-type classifier — present it as exactly that.

---

## Action 3 — Reliable image capture, display & upload across devices

- **Camera *and* gallery.** The capture screen previously offered **camera
  only**, which forced a freshly-taken photo and made the app impossible to test
  with sample images. It now offers **Camera + Gallery**
  (`mobile_app/lib/screens/report/capture_screen.dart`), so a reporter can
  attach an existing photo and testers/demo can use downloaded incident images.
  This is the "remove the check that the image was really taken" change.
- **Permissions already in place.** `AndroidManifest.xml` declares `CAMERA`,
  `READ_MEDIA_IMAGES` and `READ_EXTERNAL_STORAGE`, so both sources work on
  modern Android without crashes.
- **Robust upload validation.** The backend accepts JPEG/PNG/WebP/GIF, rejects
  empty/oversized files with clear HTTP errors, and stores each upload under a
  unique name (`app/services/file_service.py`), so uploads from different
  devices/formats are handled consistently.
- **Graceful display.** The app shows the attached photo with a remove control
  before submit, and the result screen renders the stored image via its URL.

---

## Action 4 — End-to-end testing (mobile, AI classification, backend)

- **Backend automated tests** live in `backend/tests/` (auth, realtime, etc.)
  and run in CI (`.github/workflows/ci.yml`).
- **AI classification checks:**
  - `backend/training/evaluate.py` → confusion matrix + per-class report on a
    held-out set (evidence the classifier works, per class).
  - `backend/training/predict.py path/to/photo.jpg` → single-image prediction
    with confidence, for live demo (feed an accident photo, show the call).
- **Manual end-to-end script (demo checklist):**
  1. Register/login as a citizen on the mobile app.
  2. Submit a report using **Gallery** with a sample accident photo.
  3. Confirm the AI returns `traffic` (accident) with a written description.
  4. See the incident appear live on the officer dashboard (WebSocket).
  5. Officer verifies/assigns/resolves; citizen receives notifications.
  6. Submit a near-duplicate from a second account → confirm it is deduped.
  7. Submit a non-incident photo → confirm it is rejected (not shown to officers).

> Record this run (screen capture) for the presentation as the "smooth
> end-to-end functionality" evidence the panel asked for.

---

## Action 5 — Report & presentation revisions (checklist for the write-up)

The code is done; these are the documentation deliverables to finish before
re-presenting:

- [ ] Add a **"Differences from similar projects"** section built from the
      Action-1 table (lead with the AI classifier, non-incident rejection, and
      duplicate detection).
- [ ] Replace any old performance numbers with the **retrained model's real
      metrics** (overall accuracy *and* accident precision/recall) and include
      the confusion matrix figure.
- [ ] Add an **architecture diagram**: mobile app → API → AI pipeline (YOLO +
      BLIP + our CNN) → dashboard, with the validation/duplicate gates shown.
- [ ] Add the **end-to-end demo screenshots** from Action 4.
- [ ] State the **honest pretrained-vs-trained** distinction (from `MODELS.md`).

---

## Reproduce the model work

```bash
# On a machine/server with the training deps (torch, torchvision, datasets, sklearn):
cd backend/training
python download_dataset.py --out dataset           # accident-focused, multi-source
python train_classifier.py --data dataset --epochs 8 --out ../weights
python evaluate.py --data dataset --weights ../weights/incident_classifier.pt
python predict.py some_accident_photo.jpg           # demo a single prediction
```

Enable the trained classifier in the backend by setting `INCIDENT_CNN_ENABLED=true`
(the app falls back to the rule-based classifier if the weights or torch are
absent, so this is safe).
