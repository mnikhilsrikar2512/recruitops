# Backups, restore and disaster recovery

## Targets

| | Target | How |
|---|---|---|
| **RPO** (data you can lose) | ≤ 15 minutes for everyday failures; ≤ 24 hours if the database provider itself is lost | Provider point-in-time restore; nightly portable `.bacpac` |
| **RTO** (time to be back) | ≤ 2 hours | Restore drill measures it every month (first drill on the local stack: 18 s import for 79 tables / 623 rows; production will be larger, so trust the monthly report, not this number) |

## The four layers

1. **Database provider point-in-time restore (primary).** Turn it on and set
   retention to at least 14 days: Azure SQL (PITR 7–35 days + long-term
   retention), AWS RDS (automated backups), or SQL Server `BACKUP LOG` every
   15 minutes on a self-managed server. This is what you use for "someone
   deleted something an hour ago".
2. **Nightly portable backup (secondary, provider-independent).**
   `scripts/backup_db.py`, scheduled as `db_backup` at 02:00 IST in the ops
   image. Exports a `.bacpac` and a manifest (SHA-256, row counts per table,
   latest migration) to `BACKUP_S3_BUCKET` / `BACKUP_S3_PREFIX`. On Azure SQL it
   exports from a transactionally consistent database copy; elsewhere it
   records whether anything changed during the export. Retention: every
   backup for 35 days, then the first of each month for 12 months
   (`BACKUP_RETENTION_DAYS`, `BACKUP_MONTHLY_KEEP`).
3. **Uploaded files.** The file bucket must have **versioning on** (the backup
   job reports the bucket's versioning status in its result) and, for
   production, replication to a second region or provider. Deleting a
   company's files during a privacy purge is intentional, so set a
   lifecycle rule that expires noncurrent versions after 30 days.
4. **Secrets.** A restored database is useless without
   `MFA_ENCRYPTION_KEYS` (two-step seeds are encrypted with it). Keep every
   environment's secrets in the secret manager with its own backup/soft-delete
   (Azure Key Vault soft-delete + purge protection, AWS Secrets Manager
   recovery window). Never rotate away a key that a backup still needs:
   keep retired MFA keys for as long as the oldest backup (12 months).

Better still for layer 2: a **separate backup bucket** in another account or
subscription, with credentials the app doesn't have (`BACKUP_S3_BUCKET` plus
its own keys in the ops container) and object lock / immutability turned on,
so a compromised app server can't delete its own backups.

## Monthly restore drill

Scheduled as `restore_drill` (1st of the month, 04:00 IST). It restores the
newest backup into a scratch database, verifies it, times it, drops it, and
writes an evidence report to `<prefix>drills/<db>/<timestamp>.md`.

Checks: checksum; import succeeds; every table's row count matches the
manifest (inside the before/after window for live exports); the latest
migration matches; the app's own queries work (companies, users, Admin role
grants, legal documents in force, the reporting view). Any failure exits
non-zero, so the job heartbeat alerts the on-call owner.

Run one by hand (for the go/no-go evidence pack):

```bash
cd /opt/recruitops
docker compose --env-file production.env run --rm scheduler python scripts/restore_drill.py
```

The account the drill uses (`DRILL_DB_*`, default the backup credentials)
needs `CREATE DATABASE` on the server it restores to. On Azure SQL, point
`DRILL_DB_HOST` at a separate logical server so a drill never shares capacity
with production.

## Disaster scenarios

| What happened | What to do |
|---|---|
| Bad data written in the last hours (a buggy release, a mistaken bulk change) | Provider point-in-time restore to a **new** database just before the event; compare; copy the affected rows back, or switch `DB_NAME` and redeploy. Never restore over the live database. |
| Database lost or provider region down | Create a new database (other region/provider if needed); import the newest `.bacpac`: `sqlpackage /Action:Import /SourceFile:<file> /TargetConnectionString:"..."`; run `migrate.py` (it records nothing new if the backup was current); point `DB_*` at it; redeploy. Expect to lose up to a day of data (RPO of layer 2). |
| File bucket damaged | Restore previous object versions (versioning), or switch `S3_*` to the replica. |
| App host lost | New host, same `production.env` from the secret manager, run the Release workflow (or `deploy.sh <tag>`). Nothing on the host is state. |
| Secrets lost | Database is intact but two-step seeds can't be read without `MFA_ENCRYPTION_KEYS`: restore the key from the secret manager's recovery; as a last resort, `mfa_break_glass.py` per admin. JWT key loss only signs everyone out once. |

After any real restore: run the smoke checks (`/readyz`, sign in, open a
candidate, download a document), then write a short postmortem.

## Audit trail retention: owner decision needed

`audit_retention` is scheduled but **off**: audit rows are kept forever until
`AUDIT_RETENTION_DAYS` is set (at least 365 is enforced). How long to keep
them is a legal/contract question to settle with the final Privacy Policy and
DPA text. Purged companies' audit rows are already handled separately (90-day
hold, `privacy_jobs`).
