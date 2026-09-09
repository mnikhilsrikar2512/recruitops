# Recruitment System Phase 1 Demo Script

## Demo Goal
Show the live frontend instead of static mockups, using seeded demo data and role-based login to explain how the system works end to end.

This document reflects the live frontend in `frontend/` wired to the FastAPI backend.

## Demo Login Accounts
- Admin: `admin@executiveconnection.com` / `Admin@123`
- Manager: `manav.reddy@executiveconnection.com` / `Manager@123`
- HR: `sneha.patel@executiveconnection.com` / `HR@123`
- Recruiter: `arjun.mehta@executiveconnection.com` / `Recruiter@123`

## Best Starting Page
- Launcher: [Frontend Launcher](../../frontend/index.html)
- Login: [Login](../../frontend/pages/login.html)

## Recommended 10 Minute Flow

### 1. Open with Admin
- Login as `Admin`
- Show [Role Dashboard](../../frontend/pages/role-dashboard.html)
- Talk track:
  This is the live oversight surface. Admin can verify session context, module visibility, current workload summary, and entry points into active operational pages.

### 2. Show Admin Control Areas
- Open [User Management](../../frontend/pages/user-management.html)
- Open [Location Management](../../frontend/pages/location-management.html)
- Open [Notifications Center](../../frontend/pages/notifications-center.html)
- Talk track:
  Admin controls user visibility, location setup, and notification review from the current live runtime connected to FastAPI APIs.

### 3. Switch to Manager
- Log out and log in as `Manager`
- Open [Role Dashboard](../../frontend/pages/role-dashboard.html)
- Then show [Client Directory](../../frontend/pages/client-directory.html)
- Then show [Requisition List](../../frontend/pages/requisition-list.html)
- Talk track:
  Manager sees the same shared shell with role-aware access, then moves into location-safe client and requisition execution views.

### 4. Move to HR Workflow
- Log in as `HR`
- Open [Role Dashboard](../../frontend/pages/role-dashboard.html)
- Open [Requisition List](../../frontend/pages/requisition-list.html)
- Open [Candidate Profiles](../../frontend/pages/candidate-profiles.html)
- Open [Pipeline Board](../../frontend/pages/pipeline-board.html)
- Talk track:
  HR or delivery users move from intake visibility into candidate and pipeline tracking using the shared production-oriented shell.

### 5. Show Recruiter Intake Flow
- Log in as `Recruiter`
- Open [Candidate Profiles](../../frontend/pages/candidate-profiles.html)
- Open [Pipeline Board](../../frontend/pages/pipeline-board.html)
- Open [Daily Updates Workspace](../../frontend/pages/daily-updates-workspace.html)
- Talk track:
  Recruiters can review sourced candidates, track pipeline movement on linked records, and submit daily updates through backend-connected forms.

### 6. Close with Reports
- Return to [Role Dashboard](../../frontend/pages/role-dashboard.html)
- Revisit [Notifications Center](../../frontend/pages/notifications-center.html)
- Talk track:
  This MVP close focuses on role-aware operational visibility. The shared dashboard and alerts show how the live app is wired end to end.

## What Is Seeded For Demo
- Demo login credentials on the login page
- Notifications returned by the backend
- Candidate records returned by the backend
- Requisition records returned by the backend
- Daily update history plus submission flow

## Tips For Tomorrow
- Keep the launcher and login page open in one tab
- Keep the dashboard, candidate, pipeline, and daily-update pages open in separate tabs
