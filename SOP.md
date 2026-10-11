# Eventora — DevOps SOP

Standard operating procedure for setting up, running, and operating the CI/CD pipeline and infrastructure for Eventora. This document is written phase by phase, in the same order the pipeline was actually built, so each phase only assumes what the previous phases already put in place.

## Phases

1. Test environment setup — done, verified (10/10 tests passing)
2. Docker (containerize the backend) — this document
3. GitHub Actions CI pipeline — not yet written
4. Terraform infrastructure — not yet written
5. Deployment and monitoring — not yet written

---

## Phase 1: Test environment setup

### Purpose

Before any CI pipeline can run tests automatically, the tests need to exist and need to be runnable in an isolated environment — one that does not depend on the real Aiven database or real production secrets. This phase sets up that isolated environment and adds the first working tests.

### Why this is the starting point

Everything downstream depends on this:
- The CI pipeline (Phase 3) cannot "run tests" if there are no tests, or if the tests would try to hit the real production database.
- The Docker image (Phase 2) is only worth building once there is something automated to verify it still works correctly.
- Terraform and deployment (Phases 4–5) only matter once there is a tested, containerized application to deploy.

So Phase 1 has no dependencies on anything else, and everything else depends on it.

### What was added

| File | Purpose |
|---|---|
| `event-booking-api/requirements-dev.txt` | Test-only dependencies (`pytest`, `httpx`, `pytest-cov`), kept separate from `requirements.txt` so the production Docker image doesn't install test tooling it will never use |
| `event-booking-api/conftest.py` | Sets test environment variables before any application code is imported |
| `event-booking-api/tests/test_security.py` | Unit tests for the pure functions in `core/security.py` |

### Connection flow — why conftest.py has to come first

`core/security.py` reads `SECRET_KEY`, `PHONE_ENCRYPTION_KEY`, and `PHONE_HMAC_SECRET` from the environment **at import time**, and raises `RuntimeError` immediately if any of them are missing. That means the moment any test file writes `from core import security`, those three variables must already be set — not set later in the test function, but before the import line even runs.

pytest loads `conftest.py` before it collects or imports any test file. Placing the `os.environ.setdefault(...)` calls in `event-booking-api/conftest.py` (same folder as `main.py`) guarantees they run first, every time, regardless of which test file or test runner invokes pytest. This is the reason the values are set in `conftest.py` and not inside `test_security.py` itself.

The values themselves are dummy values, valid enough in *format* to satisfy the checks (for example, `PHONE_ENCRYPTION_KEY` has to be a real Fernet key, or `Fernet(...)` raises its own error — so a random string will not work here) but never used anywhere outside a local test run or CI.

`conftest.py` also pins `DATABASE_URL` to its own local SQLite file (`test.db`), separate from whatever a locally running server might be pointed at, so a test run can never accidentally read or write real data.

### What Phase 1 does NOT cover yet

- Tests for endpoints that need a database (registration, login, booking, admin routes) — these need `utils/helpers.py` first, so the test suite can override the exact `get_db` dependency the routers actually use. Without that exact function reference, a database override silently fails to apply.
- Running these tests automatically on every push — that's Phase 3 (GitHub Actions).

### How to run this locally

```
cd event-booking-api
pip install -r requirements-dev.txt
pytest -v
```

Expected result: 10 tests pass, all in `tests/test_security.py`, no database or network access required.

### Troubleshooting

| Symptom | Likely cause |
|---|---|
| `RuntimeError: SECRET_KEY not set` | `conftest.py` isn't being picked up — confirm it's in `event-booking-api/`, the same folder pytest is run from |
| `PHONE_ENCRYPTION_KEY is invalid` | The value isn't a real Fernet key. Generate one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and use that instead of typing an arbitrary string |
| `ModuleNotFoundError: core` | pytest run from the wrong directory — must be run from inside `event-booking-api/`, not the repo root |

---

## Phase 2: Docker

### Purpose

Package the backend so it runs the same way on any machine — a laptop, a CI runner, or Render — instead of depending on whatever Python version and packages happen to already be installed on that machine.

### What was added

| File | Purpose |
|---|---|
| `event-booking-api/Dockerfile` | Builds the backend into a container image |
| `event-booking-api/.dockerignore` | Keeps test files, local databases, and dev-only dependencies out of the image |
| `docker-compose.yml` (repo root) | Runs the API together with a local PostgreSQL container, for local development |

### Connection flow — why the Dockerfile is ordered this way

Docker builds an image one instruction at a time, and caches the result of each instruction as a layer. If an instruction and everything before it are unchanged since the last build, Docker reuses the cached layer instead of re-running it.

`requirements.txt` is copied and installed *before* the rest of the source code is copied in. That ordering means: as long as `requirements.txt` doesn't change, editing a router file and rebuilding the image reuses the cached dependency-install layer rather than reinstalling every package again. If the source code were copied before `pip install`, any code change would invalidate that layer and force a full reinstall every time — much slower rebuilds for no reason.

No compiler (`gcc`/`build-essential`) is installed in the image. `psycopg2-binary`, `bcrypt`, and `cryptography` — the three packages in `requirements.txt` that would normally need to compile C extensions — all ship prebuilt wheels for standard Linux images, so `pip install` just downloads the compiled wheel instead of building from source. This is also why `python:3.12-slim` was used instead of the full `python:3.12` image: nothing here needs the extra several hundred MB of build tooling the full image carries.

Secrets (`SECRET_KEY`, `DATABASE_URL`, etc.) are not in the Dockerfile or the image at all — they get passed in at runtime, either by `docker-compose.yml`'s `environment:` block locally, or by Render's environment variable settings in production. An image that had secrets baked in at build time would leak them to anyone who pulled that image.

### How to run this locally

Build and run just the API image:
```
cd event-booking-api
docker build -t eventora-api .
docker run -p 8000:8000 --env-file .env eventora-api
```

Or run the API together with a local Postgres, from the repo root:
```
docker-compose up --build
```
This starts a local PostgreSQL container alongside the API, so local testing never touches the real Aiven database. The API is reachable at `http://localhost:8000` either way.

### What Phase 2 does NOT cover yet

- Nothing runs this automatically yet — that's Phase 3 (GitHub Actions builds and, on `main`, pushes this image).
- The image is not yet pushed anywhere (GitHub Container Registry comes in Phase 3).

### Troubleshooting

| Symptom | Likely cause |
|---|---|
| `docker build` fails on `pip install` | Usually a transient package index issue — retry; if it persists, check the exact package/version in the error against `requirements.txt` |
| Container starts then immediately exits | Check `docker logs <container>` — almost always a missing required environment variable (`SECRET_KEY`, `PHONE_ENCRYPTION_KEY`, `PHONE_HMAC_SECRET`, or `DATABASE_URL`) |
| `/login` returns an error inside the container | Known, pre-existing issue — `main.py` serves it from a `frontend/` path relative to `event-booking-api/`, but `frontend/` is a sibling folder, not nested inside it. Not caused by Docker; not yet fixed |