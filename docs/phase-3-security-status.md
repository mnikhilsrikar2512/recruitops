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

Next: 3B — password policy (3.5), rate limiting (3.7), perimeter headers (3.8). 3C — MFA (3.6).
