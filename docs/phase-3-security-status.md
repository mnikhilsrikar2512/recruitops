# Phase 3 — Account security and perimeter: status

**Branch:** `phase-3-security` (on top of `phase-2-tenancy`) · **Plan:** execution plan §4 Phase 3

## 3A — Tokens and sessions (3.1–3.4, 3.9)

| Item | Delivered |
|---|---|
| 3.1 JWT access | HS256, 15 min (`JWT_ACCESS_TTL_MINUTES`), claims `sub, tenant_id, sid, typ`. Key `JWT_SIGNING_KEY`; staging/production refuse to boot without a ≥32-char secret (dev uses a fixed dev-only key so reloads don't sign everyone out). Every request still checks the session row → revocation is immediate. |
| 3.2 Refresh tokens | Opaque, random, **HttpOnly + SameSite=Strict cookie** scoped to `/api/v1/auth` (Secure outside dev), SHA-256 at rest in `user_refresh_tokens`, **single use — rotated on every refresh**. Re-using a used token revokes the whole sign-in (family). Idle expiry 14 days (`REFRESH_TOKEN_TTL_DAYS`), absolute cap 30 days (`SESSION_ABSOLUTE_TTL_DAYS`); expired → full re-login. Revoked on logout, password change (other sign-ins), password reset (all), deactivation (all). |
| 3.3 Sessions | `GET /auth/sessions` (mine, current flagged), `DELETE /auth/sessions` (sign out other devices), `DELETE /auth/sessions/{id}`. `scripts/cleanup_sessions.py` deletes ended sign-ins older than N days (schedule daily). |
| 3.4 Cutover | `013_jwt_sessions.sql` revokes every pre-JWT session; opaque tokens answer 401 (test). Everyone signs in once more after deploy. |
| 3.9 Frontend | `apiRequest` renews an expired access token once from the cookie (single-flight) and retries; on failure the session is cleared → login. CORS now allows credentials for the exact allowlisted origins only. |
| Tests | `test_tokens.py` (expiry, wrong key, wrong type, `alg=none`), `test_jwt_sessions_db.py` (cookie flags, rotation, **refresh theft kills the family**, expired refresh, opaque cutover, tampered JWT, logout, sign-out-others, password change), live smoke 1.6–1.8. |


## 3B — Password policy, lockout, rate limits, perimeter (3.5, 3.7, 3.8)

| Item | Delivered |
|---|---|
| 3.5 Password policy | 12–128 characters, no composition rules or forced rotation (NIST). Refused when the password or its letters-only core is on the bundled common/breached list (`app/core/common_passwords.txt`), or is one repeated character. Optional live Have I Been Pwned range check (`PASSWORD_BREACH_CHECK=hibp`; only 5 hash characters leave the server; falls back to the list if unreachable). Applies to password change, setup and reset (422 with the reason). Forms now ask for 12+. |
| 3.5 Lockout | `014_login_lockout.sql`: after 5 wrong passwords in a row the account refuses sign-in for 15 minutes (429), even with the right password; a correct sign-in resets the count (`LOGIN_LOCKOUT_THRESHOLD`, `LOGIN_LOCKOUT_MINUTES`). |
| 3.7 Rate limits | `app/core/rate_limit.py`: login 5/min/IP + 10/min/account, forgot-password 5/min/IP + 3/min/account, password setup/reset 10/min/IP, refresh 30/min/IP → 429 + `Retry-After`. Redis when `REDIS_URL` is set (required in staging/production so instances share counters), in-process otherwise (dev). A broken cache never blocks sign-in. |
| 3.8 Perimeter | Security headers on every API response (nosniff, frame DENY, no-referrer, Permissions-Policy, COOP, CSP `default-src 'none'`, `Cache-Control: no-store`); in staging/production HSTS and an HTTP→HTTPS 308 redirect (via `X-Forwarded-Proto` from the load balancer). CORS: exact allowlist, credentials allowed only for those origins. TLS at the load balancer waits for the domain (I-3). |
| Tests | `test_auth_protection.py`: 8-char and common/breached passwords rejected, 429 at 5/min/IP and 10/min/account, forgot-password limit, headers, CORS probe from a disallowed origin, lockout after 5 wrong passwords. |

### Result of the 3A run (2026-10-06, commit `32ed6c9`)

Backend **456 passed**, 3 skipped (incl. refresh-theft, expired refresh, cutover) · live smoke **52/52** · sweeps admin + recruiter 101/101 · dev database on 013, dev backend verified (login JWT, refresh, sessions, logout).
