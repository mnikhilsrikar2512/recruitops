# Secrets: where they live, how to rotate them

Production and staging never read `backend/.env`. Every secret is provided
by the platform, either as an environment variable or as a file in
`SECRETS_DIR` (one file per setting, named exactly like the variable, e.g.
`/run/secrets/JWT_SIGNING_KEY`). Both work with any secret manager: Azure
Key Vault, AWS Secrets Manager, GCP Secret Manager, Doppler, Vault, or
Docker/Kubernetes secrets. An environment variable wins over a file.

The API refuses to boot in staging/production when a required secret is
missing or weak (`validate_settings()` in `app/core/config.py`).

| Setting | What it protects | Generate | Rotate | How to rotate |
|---|---|---|---|---|
| `DB_PASSWORD` | Database login of the app | from the DB / secret manager | 90 days | Create the new password on the login, update the secret, redeploy, then remove the old one. |
| `JWT_SIGNING_KEY` | Access tokens (15 min) | `python -c "import secrets;print(secrets.token_urlsafe(48))"` | 180 days, or at once if leaked | Replace and redeploy. Access tokens signed with the old key stop working; browsers renew silently from their refresh cookie (refresh tokens are not JWTs), so nobody is signed out. |
| `MFA_ENCRYPTION_KEYS` | Two-step verification seeds at rest | `python -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"` | Yearly, or at once if leaked | 1. Put the new key **first**, keep the old one: `new:<key>,old:<key>`. 2. Deploy. 3. Run `scripts/encrypt_mfa_secrets.py` (it re-wraps every row). 4. Remove the old key and deploy. Never remove a key before step 3 — the seeds under it can no longer be read and those users need break-glass. |
| `SMTP_PASSWORD` | Outbound email | from the email provider | Provider policy / 180 days | Create a second credential at the provider, swap, delete the old one. |
| `S3_SECRET_ACCESS_KEY` (or workload identity) | File storage | from the provider | 90 days (prefer workload identity: nothing to rotate) | Create a second access key, swap, delete the old one. |
| `REDIS_URL` (password inside) | Rate-limit counters | from the provider | 180 days | Provider dual-password, swap, retire. |
| `METRICS_TOKEN` | `/metrics` | `secrets.token_urlsafe(32)` | 180 days | Update the scraper and the app together. |
| `SENTRY_DSN` | Error tracking ingest | from Sentry/GlitchTip | when staff change | Rotate the DSN key in the project. |

## Rules

- Secrets never go in git, images, logs or tickets. Images are built
  without them; `.env` is in `.gitignore`.
- One secret per environment: staging and production never share a value.
- Whoever rotates writes the date in the release notes. A secret that might
  have leaked is rotated the same day, regardless of schedule.
- After rotating `MFA_ENCRYPTION_KEYS` or `JWT_SIGNING_KEY`, check
  `/readyz` and sign in once with an admin account (two-step code included).

## Encrypting existing two-step seeds (one time, on the first deploy with 032)

```
cd backend
.venv/bin/python scripts/apply_migration.py 032_encrypt_mfa_secrets.sql   # or the deploy pipeline's migrate step
MFA_ENCRYPTION_KEYS=... .venv/bin/python scripts/encrypt_mfa_secrets.py --dry-run
MFA_ENCRYPTION_KEYS=... .venv/bin/python scripts/encrypt_mfa_secrets.py
```

Plaintext seeds keep working until then, so the order is safe.
