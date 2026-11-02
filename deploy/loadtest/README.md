# Load test (Phase 6.7)

Targets (docs/runbooks/monitoring.md): reads p95 < 400 ms, writes p95 < 800 ms,
reports p95 < 2 s, errors < 1 %, at 3× planned peak (300 concurrent users).

1. Seed, inside the API container of the environment under test (never production):
   `docker compose exec api python scripts/seed_loadtest.py --out /tmp/loadtest.json`
   then copy it to `deploy/loadtest/fixture.json`. First run builds a separate
   "Loadtest Staffing" company (6 managers, 44 recruiters, 120 requisitions,
   3,000 candidates); later runs only issue fresh sign-ins. The fixture holds live
   tokens: it is 0600 and git-ignored.
2. Run: `BASE_URL=https://staging.<domain> deploy/loadtest/run.sh`
   (quick check: `VUS=20 HOLD=1m THINK_SECONDS=0.5`). Exits non-zero if a target is missed;
   the full report lands in `deploy/loadtest/reports/`.
3. Afterwards: `docker compose exec api python scripts/seed_loadtest.py --revoke`.

Sign-ins are issued by the seed through the login code path's own session helper,
because sign-in is rate-limited per IP; the rate limits stay on.

Shakedown 2026-11-02 (local Mac, 2 workers, 20 VUs, 13 users / 200 applications):
10,174 requests, 0 errors; p95 read 137 ms, write 425 ms, report 316 ms.
The real evidence run is 300 VUs against staging.
