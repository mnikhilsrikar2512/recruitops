# Recruitment System Phase 1 Demo Script

## Demo Goal
Show the live frontend instead of static mockups, using seeded demo data and role-based login to explain how the system works end to end.

This document now reflects the active lightweight prototype in `frontend/`, not the older raw Stitch export folders.

## Demo Login Accounts
- Admin: `admin@executiveconnection.com` / `Admin@123`
- Manager: `manav.reddy@executiveconnection.com` / `Manager@123`
- HR: `sneha.patel@executiveconnection.com` / `HR@123`
- Recruiter: `arjun.mehta@executiveconnection.com` / `Recruiter@123`

## Best Starting Page
- Launcher: [Frontend Launcher](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/index.html:1)
- Login: [Login](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/login.html:1)

## Recommended 10 Minute Flow

### 1. Open with Admin
- Login as `Admin`
- Show [Dashboard](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/dashboard.html:1)
- Talk track:
  This is the live oversight surface. Admin can verify session context, module visibility, current workload summary, and entry points into active operational pages.

### 2. Show Admin Control Areas
- Open [User Management](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/users.html:1)
- Open [Location Management](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/locations.html:1)
- Open [Notifications](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/notifications.html:1)
- Talk track:
  Admin controls user visibility, location setup, and notification review from the current live runtime connected to FastAPI APIs.

### 3. Switch to Manager
- Log out and log in as `Manager`
- Open [Dashboard](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/dashboard.html:1)
- Then show [Clients](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/clients.html:1)
- Then show [Requisitions](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/requisitions.html:1)
- Talk track:
  Manager sees the same shared shell with role-aware access, then moves into location-safe client and requisition execution views.

### 4. Move to HR Workflow
- Log in as `HR`
- Open [Dashboard](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/dashboard.html:1)
- Open [Requisitions](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/requisitions.html:1)
- Open [Candidates](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/candidates.html:1)
- Open [Pipeline](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/pipeline.html:1)
- Talk track:
  HR or delivery users move from intake visibility into candidate and pipeline tracking using the shared production-oriented shell instead of raw exported layouts.

### 5. Show Recruiter Intake Flow
- Log in as `Recruiter`
- Open [Candidates](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/candidates.html:1)
- Open [Pipeline](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/pipeline.html:1)
- Open [Daily Updates](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/daily-updates.html:1)
- Talk track:
  Recruiters can review sourced candidates, track pipeline movement on linked records, and submit daily updates through backend-connected forms.

### 6. Close with Reports
- Return to [Dashboard](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/dashboard.html:1)
- Revisit [Notifications](/Users/bhargavnikhil/Desktop/recrutment%20system/frontend/pages/notifications.html:1)
- Talk track:
  This MVP close focuses on role-aware operational visibility, not the older static reporting mockups. The shared dashboard and alerts show how the live prototype is now wired end to end.

## What Is Seeded For Demo
- Demo login credentials on the login page
- Notifications returned by the backend
- Candidate records returned by the backend
- Requisition records returned by the backend
- Daily update history plus submission flow

## Tips For Tomorrow
- Keep the launcher and login page open in one tab
- Keep dashboard, candidates, pipeline, and daily updates open in separate tabs
- Use the active pages in `frontend/pages/`, not the archived reference files in `frontend/pages/reference/`
- Use the Figma/PPT only as a backup, not the main presentation artifact
