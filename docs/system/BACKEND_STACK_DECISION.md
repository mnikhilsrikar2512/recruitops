# Backend Stack Decision

Date locked:

- Wednesday, August 19, 2026

## Purpose

This document locks the MVP backend implementation direction so the repository can move from planning into code.

## MVP Technical Choices

### Application Stack

- Runtime: `Node.js`
- Language: `TypeScript`
- HTTP framework: `Express`

Reason:

- fast MVP bootstrap
- simple route-first API build
- easy alignment with the current frontend and JS-heavy workflow
- low friction for building module by module from the existing API contracts

### Database

- Primary engine: `Microsoft SQL Server`
- Source-of-truth schema: [scripts/001_recruitment_system_mssql_schema.sql](/Users/bhargavnikhil/Desktop/recrutment%20system/scripts/001_recruitment_system_mssql_schema.sql)

Reason:

- the project already has an MSSQL-first schema and seed structure
- changing DB direction now would create unnecessary rework

### Migration Strategy

- Keep versioned SQL files in `backend/database/migrations/`
- Treat the root `scripts/` folder as the planning and bootstrap source until the migration files are fully split out
- Move toward one executable migration per change instead of editing one giant schema forever

### Authentication Strategy

- MVP auth style: opaque bearer session token
- Session persistence table: `user_sessions`
- Password storage: hashed password only

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

- request validation with `zod`
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

This first scaffold does not yet complete:

- real authentication
- real DB execution
- real file upload handling
- real permission resolution
- real audit logging

It exists to give the repository a clean implementation base that matches the locked product decisions.
