# Backend Stack Decision

Date locked:

- Wednesday, August 19, 2026

## Purpose

This document locks the MVP backend implementation direction so the repository can move from planning into code.

## MVP Technical Choices

### Application Stack

- Runtime: `Python`
- Language: `Python 3.12+`
- HTTP framework: `FastAPI`

Reason:

- typed, validated request/response models via Pydantic
- simple route-first API build that aligns with the existing API contracts
- low friction for building module by module from the existing API contracts

### Database

- Primary engine: `Microsoft SQL Server`
- Source-of-truth schema: [backend/db/schema.sql](/Users/bhargavnikhil/Desktop/recrutment%20system/backend/db/schema.sql) (regenerate with `backend/scripts/dump_schema.py`)

Reason:

- the project already has an MSSQL-first schema and seed structure
- changing DB direction now would create unnecessary rework

### Migration Strategy

- Schema changes land in the live database and are committed to `backend/db/schema.sql` via `backend/scripts/dump_schema.py`
- CI replay: `backend/scripts/run_tests_ci.sh` rebuilds a throwaway database from the committed schema

### Authentication Strategy

- MVP auth style: opaque bearer session token
- Session persistence table: `user_sessions`
- Password storage: bcrypt password hashing (legacy unsalted hashes migrate on login)

Reason:

- this matches the existing schema direction and session planning
- it is simpler for MVP than full OAuth or SSO
- it supports login, logout, session revoke, and later device/session tracking

### Authorization Strategy

- server-side permission middleware
- server-side location-scope middleware
- role names are never trusted on their own
- permissions plus scope decide access

### Validation Strategy

- request validation with `pydantic`
- service-layer business validation for ownership, scope, transitions, and duplicate rules

### File Storage Strategy

- local file storage for MVP development
- configurable storage root through environment variables
- external object storage can be added later without changing API contracts

## Initial Backend Folder Ownership

The `backend/` folder will hold:

- app bootstrap
- environment config
- database connection and migration structure
- shared middleware
- module route files
- implementation placeholders aligned to the MVP build pack

## Non-Goals For This First Scaffold

Historical note: the original scaffold deliberately deferred authentication, DB execution,
file upload handling, permission resolution, and audit logging. All of those are implemented
now (see `backend/tests/` and the CI runner); this section is kept to explain the scaffold's
original intent.
