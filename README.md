# AIRA — AI Incident Reporting Application

A digital platform that lets citizens report incidents to the Rwanda National Police (RNP) by uploading a photo. AI analyzes the image, generates a structured description, and routes the incident to officers in real time.

## Repository layout

| Folder                | What's in it                                                          |
| --------------------- | --------------------------------------------------------------------- |
| `backend/`            | Python 3.11 + FastAPI server, SQLAlchemy models, AI pipeline, Celery, pytest |
| `police_dashboard/`   | React 18 + TypeScript + Vite dashboard for police                     |
| `mobile_app/`         | Flutter (Dart) citizen app                                            |
| `database/`           | MySQL 8.0 schema and seed SQL                                         |
| `docker-compose.yml`  | Orchestrates MySQL, Redis, FastAPI, Celery worker, dashboard          |
| `nginx.conf`          | Production reverse-proxy template                                     |

## Quick start (Docker — recommended)

```bash
docker compose up --build
```

| Service             | URL                                |
| ------------------- | ---------------------------------- |
| Backend (Swagger)   | <http://localhost:8000/docs>       |
| Police dashboard    | <http://localhost:5173>            |
| MySQL               | `localhost:3307` (user: `aira`)    |
| Redis               | `localhost:6379`                   |

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The first start auto-creates tables and seeds the default accounts (set `AUTO_SEED=false` in `.env` to opt out). For local dev, the default `.env.example` uses an empty-password XAMPP MySQL connection — adjust to your setup.

Run the test suite:

```bash
cd backend
pytest -q          # 31 tests pass
```

### Police dashboard

```bash
cd police_dashboard
npm install
npm run dev          # http://localhost:5173
```

Build for production:

```bash
npm run build
```

### Flutter mobile app

```bash
cd mobile_app
flutter pub get
flutter run --dart-define=AIRA_API_URL=http://192.168.1.64:8000   # Android emulator
```

See `mobile_app/README.md` for required Android/iOS permissions.

## Default seeded accounts

| Role     | Email                  | Password   | Login route                       |
| -------- | ---------------------- | ---------- | --------------------------------- |
| Admin    | admin@rnp.gov.rw       | Admin@123  | `POST /api/v1/auth/login`         |
| Officer  | officer1@rnp.gov.rw    | Officer@1  | `POST /api/v1/auth/officer/login` |
| Citizen  | citizen@example.com    | Citizen@1  | `POST /api/v1/auth/login`         |

## API surface

All endpoints in the original specification are implemented under `/api/v1/`:

- **Auth** — register, login, officer login, refresh, logout, forgot/reset password, verify email
- **Incidents** — submit (with image), list, detail, update status, assign, delete (admin), nearby, messages
- **AI** — analyze a standalone image, fetch analysis for an incident
- **Users** — `me`, update, change password, my incidents, my notifications
- **Officers** — list, create (admin), incidents-by-officer, stations
- **Notifications** — list, mark read, register device token (FCM/APNs)
- **Analytics** — overview, by-type, by-location, timeline, response metrics

Full schema is auto-generated at `/docs` (OpenAPI / Swagger UI) and `/redoc`.

## AI pipeline

Two analyzer backends:

- `StubAnalyzer` (default): no ML deps required. Inspects color stats and brightness to produce a plausible description and route categories. Used in tests and any environment without `torch`/`transformers`.
- `MLAnalyzer`: uses **YOLOv8n** (object detection) + **BLIP** (image captioning) — both pretrained, downloaded on first run. Activated by setting `AI_ENABLED=true` and uncommenting the AI extras in `requirements.txt`:

  ```
  torch
  torchvision
  transformers
  ultralytics
  ```

The AI service produces:

- Caption (free-form description)
- Scene label
- List of detected objects with confidence
- Mapped incident type (`fire`, `traffic`, `violent_crime`, `theft`, `vandalism`, `suspicious_activity`, `general`)
- Severity level (`low`/`medium`/`high`/`critical`)

These are persisted in the `ai_analysis` table and surfaced in the dashboard.

## Testing summary

| Component         | What was verified                                              |
| ----------------- | -------------------------------------------------------------- |
| Backend           | `pytest -q` → **31 / 31 passing** (auth, RBAC, incidents, AI, analytics, notifications, messaging) |
| Dashboard         | `tsc --noEmit` and `vite build` both succeed (936 modules)     |
| Flutter app       | Code is structurally complete; **not run** (requires Flutter SDK + emulator/device) |
| Docker            | Compose file is wired but not booted in this environment       |

The Flutter app, FCM/APNs delivery, and a production AI model trained on real incident imagery are the parts you'll need to validate yourself with the appropriate toolchain and data.

## Notes

- Real police-grade AI accuracy requires fine-tuning on a labeled dataset of incident photos. The pretrained YOLO/BLIP combo gives you a working pipeline to evaluate; treat its output as "best-effort" until you train a domain model.
- Push notifications: the code paths and `device_tokens` table are ready; wire your FCM/APNs credentials in `app/services/notification_service.py`.
- For production: change `JWT_SECRET`, enable HTTPS, swap MySQL credentials, set `AUTO_SEED=false`, and put the dashboard behind the `nginx.conf` template.
