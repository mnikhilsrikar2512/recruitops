# Deploying RecruitOps

Every deploy is the **Release** workflow (`.github/workflows/release.yml`):

```
push to main ──► CI green ──► build + scan images ──► staging ──► (approve) ──► production
                                 ghcr.io/<owner>/recruitops-{api,web}:<date>-<sha>
```

On each host, `deploy/server/deploy.sh <tag>` does the work:

1. **Pull** every image first, so a registry outage changes nothing.
2. **Migrate** (the gate): `migrate.py` applies pending migrations and the
   reference data under a database lock. If it fails, nothing is rolled out
   and the old version keeps serving.
3. **Roll out** api, scheduler and web.
4. **Verify**: `/readyz` inside the API container (database + Redis), then
   `https://<domain>/api/v1/health` through TLS.
5. **Roll back automatically** to the previous tag if step 3 or 4 fails.

Both rollback paths were rehearsed: a release that couldn't reach the
database stopped at the gate, and a release whose API never became ready
was replaced by the previous one within a minute.

## One-time setup

### 1. The host (staging and production each get one)

Any Linux VM with Docker Engine and the compose plugin (2 vCPU / 4 GB is
plenty to start; ClamAV alone wants ~1.5 GB).

```bash
sudo mkdir -p /opt/recruitops && sudo chown deploy:deploy /opt/recruitops
# as the deploy user, who is in the docker group:
cd /opt/recruitops
cp production.env.example production.env      # copy from deploy/server/, then fill it in
chmod 600 production.env
echo "<token with read:packages>" | docker login ghcr.io -u <github-user> --password-stdin
```

Open ports 80 and 443 only. Point the domain's DNS at the host; Caddy gets
and renews the Let's Encrypt certificate by itself.

### 2. Managed services (from your cloud's console)

| Need | Examples | Setting(s) |
|---|---|---|
| SQL Server | Azure SQL, AWS RDS for SQL Server, a managed VM | `DB_*`, `MIGRATE_DB_*` |
| Redis | Azure Cache, ElastiCache, Upstash | `REDIS_URL` (use `rediss://`) |
| Private bucket, versioning on | Azure Blob (S3 gateway), S3, R2, B2 | `S3_*` |
| SMTP | SendGrid, SES, Azure Communication Services, Postmark | `SMTP_*`, `EMAIL_*` |
| Error tracking (optional) | Sentry, GlitchTip | `SENTRY_DSN` |
| Job heartbeats (optional) | healthchecks.io, Cronitor | `JOB_HEARTBEAT_URL` |

Two database logins (see `deploy/sql/create_logins.sql`):
- `recruitops_migrator`: owns the schema; used only by the migrate step.
- `recruitops_app`: read/write data, execute; **no DDL**. The running API
  and scheduler use this one.

### 3. GitHub

Settings → Environments → create `staging` and `production`. On
`production`, add yourself under **Required reviewers**: that is the
approval gate. In each environment:

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | the host's address |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | a private key whose public half is in `~deploy/.ssh/authorized_keys` |
| `DEPLOY_KNOWN_HOSTS` | output of `ssh-keyscan -H <host>` |

| Variable | Value |
|---|---|
| `DEPLOY_PATH` | `/opt/recruitops` |
| `PUBLIC_URL` | `https://staging.<domain>` / `https://app.<domain>` |

Then Settings → Rulesets (on `main`): add the new **Security gates**
check to the required list, next to the two existing ones. Remember that
the ruleset lists checks by their job **names**; renaming a job means
updating the ruleset, or every PR will wait forever (round 34).

## Rules for migrations (they keep rollbacks safe)

The previous version must keep working on the migrated schema, because a
rollback only swaps code, never the schema.

- **Expand, then contract.** Add columns/tables first (nullable or with a
  default). Only drop or rename in a later release, once no running
  version reads the old shape.
- **Never edit an applied migration.** `migrate.py` refuses to run when an
  applied file's checksum changed. Fix forward with a new number.
- **Idempotent and self-checking**, like every file in `scripts/`: guard
  with `IF NOT EXISTS`, end with a `RAISERROR` check.
- Long data backfills go in their own migration (or a job), not inside a
  schema change.

## Everyday operations

```bash
# on the host
cd /opt/recruitops
./deploy.sh --status                 # what's running, current and previous tags
./deploy.sh --rollback               # back to the previous tag (schema stays)
IMAGE_REPO=ghcr.io/<owner> ./deploy.sh <tag>   # by hand, same steps as the pipeline
cat .deploy/history.log              # every deploy and rollback, who and when
docker compose --env-file production.env logs -f api   # JSON logs, one line per request
docker compose --env-file production.env run --rm api job privacy_jobs   # run a job now
```

Re-run a release without a new commit: Actions → Release → Run workflow.

## Known limits (accepted for launch)

- One API host: a deploy restarts the containers, so there are a few
  seconds of 502s. Two hosts behind a load balancer remove that; nothing in
  the images assumes one host (rate limits and sessions live in Redis and
  SQL Server).
- 17 pages still have inline `<script>` blocks, so the CSP allows
  `'unsafe-inline'` scripts. Moving them into files lets the CSP drop it.
