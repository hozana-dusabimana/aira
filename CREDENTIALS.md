# AIRA — Default Credentials

> **DEMO USE ONLY.** Every value below is committed to the repo. Before any non-local deployment, rotate **all** of them.

## Application accounts

These are auto-seeded the first time the backend starts (controlled by `AUTO_SEED=true` in `.env` / compose). The same passwords are written to the README.

| Role     | Email                  | Password    | Login endpoint                       |
| -------- | ---------------------- | ----------- | ------------------------------------ |
| Admin    | `admin@rnp.gov.rw`     | `Admin@123` | `POST /api/v1/auth/login`            |
| Officer  | `officer1@rnp.gov.rw`  | `Officer@1` | `POST /api/v1/auth/officer/login`    |
| Citizen  | `citizen@example.com`  | `Citizen@1` | `POST /api/v1/auth/login`            |

The mobile app's login screen pre-fills the citizen account; the dashboard's login screen pre-fills the officer account.

## MySQL

Defined in `docker-compose.yml`. The local schema is also accessible via the host port mapping (`3307` to avoid clashing with XAMPP's MySQL on 3306).

| Field                | Value                                                  |
| -------------------- | ------------------------------------------------------ |
| Host (host machine)  | `localhost`                                            |
| Host (in network)    | `mysql`                                                |
| Port (host machine)  | `3307`                                                 |
| Port (in network)    | `3306`                                                 |
| Database             | `aira`                                                 |
| App user             | `aira`                                                 |
| App password         | `airapass`                                             |
| Root password        | `rootpass`                                             |
| SQLAlchemy URL (app) | `mysql+pymysql://aira:airapass@mysql:3306/aira`        |
| Local-XAMPP URL      | `mysql+pymysql://root:@localhost:3306/aira` (empty pwd)|

Connect from the host machine:

```bash
docker exec -it aira-mysql-1 mysql -uaira -pairapass aira
# or, from the host:
mysql -h 127.0.0.1 -P 3307 -uaira -pairapass aira
```

## Redis

No authentication configured by default.

| Field             | Value                       |
| ----------------- | --------------------------- |
| Host (in network) | `redis`                     |
| Host (host)       | `localhost`                 |
| Port              | `6379`                      |
| URL (cache)       | `redis://redis:6379/0`      |
| URL (Celery broker) | `redis://redis:6379/1`    |
| URL (Celery results)| `redis://redis:6379/2`    |

## JWT signing secret

Set in two places — keep them aligned, and **always change for production** (must be ≥ 32 random characters).

| Location                          | Default value                                     |
| --------------------------------- | ------------------------------------------------- |
| `docker-compose.yml` (backend & worker `JWT_SECRET`) | `change-me-in-prod-please-32-chars-minimum` |
| `backend/.env.example`            | `change-this-in-production-please-32-chars-min`   |

Token lifetimes:

| Token   | Default lifetime           |
| ------- | -------------------------- |
| Access  | 15 minutes                 |
| Refresh | 7 days                     |

## Service URLs

| Service          | URL                                  |
| ---------------- | ------------------------------------ |
| Backend API      | <http://localhost:8000/api/v1>       |
| Backend health   | <http://localhost:8000/health>       |
| Swagger UI       | <http://localhost:8000/docs>         |
| ReDoc            | <http://localhost:8000/redoc>        |
| Police dashboard | <http://localhost:5173>              |
| Uploads (dev)    | <http://localhost:8000/uploads/...>  |

## Mobile app API base

The Flutter app defaults to `http://192.168.1.67:8000` (Android emulator → host).

Override per-build:

```bash
flutter run --dart-define=AIRA_API_URL=http://192.168.1.42:8000
```

## Generated test data

After running `pytest` the backend uses an in-memory SQLite database with a separate test fixture. Test accounts are:

| Role     | Email                            | Password    |
| -------- | -------------------------------- | ----------- |
| Admin    | `admin@aira.example.com`         | `Admin@123` |
| Officer  | `officer@aira.example.com`       | `Officer@1` |
| Citizen  | `citizen@aira.example.com`       | `Citizen@1` |

These exist only inside the test fixture and never touch your real database.

## Production checklist

Before exposing any of this beyond `localhost`:

- [ ] Set `AUTO_SEED=false` in the production env (so the demo accounts aren't recreated)
- [ ] Replace `JWT_SECRET` with a fresh ≥ 32-byte random string (`openssl rand -hex 32`)
- [ ] Change MySQL root + app user passwords
- [ ] Change the seeded admin/officer/citizen accounts (rotate passwords or delete demo accounts entirely)
- [ ] Add Redis `requirepass` and update the `REDIS_URL` / `CELERY_*` URLs accordingly
- [ ] Restrict `CORS_ORIGINS` to your real frontend hostnames
- [ ] Enable HTTPS at the Nginx layer (`nginx.conf` is the template)
- [ ] Don't commit `.env` — only `.env.example` is tracked
