# Eventora

Full-stack event booking and ticketing platform with a Docker, GitHub Actions, and Terraform pipeline for building, testing, and deploying the application.

## Overview

Eventora lets users browse events and book tickets, and gives admins a panel to manage events, categories, users, bookings, and notifications. The backend is a FastAPI service on PostgreSQL, with JWT authentication and Cloudinary for image storage. The application is containerized with Docker, tested and deployed through a GitHub Actions pipeline, and its infrastructure (Render + Aiven) is provisioned with Terraform instead of through the provider dashboards.

## Features

- JWT-based authentication and role-based access (user / admin)
- Event browsing with search, category, and status filters
- Three inventory models per event: general admission, zone-based, and fixed-seat
- Concurrency-safe inventory holds during checkout, using time-limited lock tokens so two users cannot claim the same seat, zone slot, or general ticket at once
- Admin panel with separate pages for Dashboard, Events, Categories, Users, Bookings, Analytics, and Notifications
- Ticket types and per-event pricing
- Category management with live event counts per category
- Image uploads through Cloudinary
- Booking and payment records (payment provider currently mocked, structured to swap in a real gateway)

## Tech Stack

**Backend**
- FastAPI (Python)
- PostgreSQL, hosted on Aiven
- SQLAlchemy ORM
- Alembic for schema migrations
- JWT for authentication

**Frontend**
- HTML, CSS, and vanilla JavaScript
- Bootstrap

**Third-party services**
- Cloudinary — image hosting
- Render — application hosting

**DevOps / Infrastructure**
- Docker — containerizes the backend for consistent local and production environments
- GitHub Actions — runs linting, tests, and migration checks on every push and pull request, and builds/deploys on merge
- Terraform — provisions the Render web service and Aiven PostgreSQL instance as code

## Architecture Notes

- Inventory is modeled generically: an `Inventory` row can represent a physical seat, a zone slot, or a general-admission unit, each carrying its own status and lock state, so all three booking types share the same underlying hold-and-purchase logic instead of three separate code paths.
- A hold on any inventory unit uses a lock token with an expiry (`Inventory.lock_token` / `Inventory.locked_until`, and `SeatLock` for individual seats), which prevents two users from booking the same unit at the same time without needing a database-level table lock.
- The admin panel is built as separate pages (one HTML/CSS/JS set per section) rather than a single-page app, so each admin page loads only the script it needs.

## Project Structure

```
Event-Booking-App/
├── event-booking-api/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   ├── core/
│   │   └── security.py
│   ├── routers/
│   │   ├── events.py
│   │   ├── admin.py
│   │   ├── engagement.py
│   │   ├── analytics.py
│   │   └── seating.py
│   ├── utils/
│   │   └── helpers.py
│   ├── alembic/
│   │   └── versions/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/
│   │   ├── event-details.html
│   │   └── booking-confirmation.html
│   ├── admin/
│   │   ├── admin.html
│   │   ├── pages/
│   │   │   ├── admin_event.html
│   │   │   ├── admin_categories.html
│   │   │   ├── admin_users.html
│   │   │   ├── admin_bookings.html
│   │   │   ├── admin_analytics.html
│   │   │   └── admin_notifications.html
│   │   ├── css/
│   │   └── js/
│   │       ├── admin_event.js
│   │       ├── admin_categories.js
│   │       ├── admin_users.js
│   │       ├── admin_bookings.js
│   │       ├── admin_analytics.js
│   │       └── admin_notifications.js
│   ├── js/
│   │   ├── admin.js
│   │   └── event-details.js
│   ├── css/
│   └── images/
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── terraform/
│   ├── main.tf
│   └── variables.tf
├── docker-compose.yml
└── README.md
```

## CI/CD Pipeline

On every push and pull request, GitHub Actions:
1. Installs backend dependencies
2. Runs the linter
3. Runs the pytest suite against a disposable PostgreSQL service container
4. Applies Alembic migrations against that container to confirm they run cleanly

On merge to `main`, the pipeline builds a Docker image and deploys it to Render. Branch protection requires the pipeline to pass before a merge is allowed, so a deploy only happens after tests and migrations succeed.

## Infrastructure

The Render web service and the Aiven PostgreSQL instance are defined in Terraform rather than created by hand through their dashboards, so the infrastructure configuration is versioned alongside the application code and can be recreated from scratch if needed.

## Getting Started

### Prerequisites
- Python 3.10+
- Docker (optional, for running the full stack locally without installing PostgreSQL directly)

### Run locally
```
cd event-booking-api
pip install -r requirements.txt
uvicorn main:app --reload
```

### Run with Docker
```
docker-compose up --build
```
This starts the API together with a local PostgreSQL container, so local development does not touch the production database.

### Frontend
Serve the `frontend` folder with any static file server, or open its pages directly in a browser while the API is running locally.

## Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Secret used to sign and verify JWTs |
| `CLOUDINARY_URL` | Cloudinary account credentials |

## API Documentation

FastAPI generates interactive API docs automatically at `/docs` while the server is running.

## Roadmap

- Wire the booking flow to the inventory hold endpoints for all three ticket types
- Payment gateway integration to replace the current mock provider
- Azure Pipelines as a second CI/CD pipeline, running alongside GitHub Actions

## Author

Priyanka Srivastava