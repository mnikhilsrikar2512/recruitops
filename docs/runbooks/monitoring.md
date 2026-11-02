# Monitoring, SLOs and alerts

## Service level objectives

| SLO | Target | Measured by |
|---|---|---|
| Availability | 99.5% of requests succeed, per calendar month (≈ 3.6 h of error budget) | `recruitops_http_requests_total` 5xx share; external uptime check |
| Read latency | p95 < 400 ms (GET, excluding reports) | `recruitops_http_request_duration_seconds` |
| Write latency | p95 < 800 ms | same, POST/PUT/PATCH/DELETE |
| Report latency | p95 < 2 s | same, `/reports/` routes |
| Scheduled jobs | every job runs on time and succeeds | job heartbeats |

## What sends signals

| Signal | Where | Notes |
|---|---|---|
| `/metrics` | API container, port 8000, `Authorization: Bearer $METRICS_TOKEN` | Requests and latency per route template, emails sent/failed. Summed across worker processes. Not reachable through the public edge. |
| `/livez`, `/readyz` | API container | Liveness (process) and readiness (database + Redis). Used by deploy.sh and the platform. |
| `https://<domain>/api/v1/health` | public | For an **external** uptime monitor. |
| JSON logs | stdout of every container | One line per request (`recruitops.access`) with `request_id`, `route`, `status`, `duration_ms`, `user_id`, `tenant_id`. Ship them with the platform's log agent (Azure Monitor agent, CloudWatch agent, Grafana Alloy, Vector). |
| Error tracking | `SENTRY_DSN` | Unhandled exceptions with the request id; no bodies, cookies or personal data. |
| Job heartbeats | `JOB_HEARTBEAT_URL` | Each job pings `<url>/<job>` on success and `<url>/<job>/fail` on failure (healthchecks.io / Cronitor convention). The service alerts on a failure **or a missing ping**, which also catches a dead scheduler. |

Every error response carries `X-Request-ID`; unexpected 500s also include it
in the body. Ask users for it, then search the logs for it.

## Alert rules

`deploy/monitoring/alerts.yml` (Prometheus format; tested by
`deploy/monitoring/alerts.test.yml` with `promtool test rules`):

| Alert | Severity | Fires when |
|---|---|---|
| RecruitOpsErrorBudgetFastBurn | page | 5xx share > 7.2% over 5 min **and** 1 h |
| RecruitOpsErrorBudgetSlowBurn | ticket | 5xx share > 1.5% for 30 min |
| RecruitOpsApiDown | page | the scraper can't reach `/metrics` for 2 min |
| RecruitOpsEmailFailing | page | > 3 failed emails and none sent in 30 min |
| RecruitOps{Read,Write,Report}LatencyHigh | ticket | p95 above target for 15–30 min |
| RecruitOpsNoTraffic | ticket | no requests for an hour |

Scrape configuration for any Prometheus-compatible collector:

```yaml
scrape_configs:
  - job_name: recruitops-api
    scrape_interval: 30s
    metrics_path: /metrics
    authorization: { type: Bearer, credentials_file: /etc/prometheus/recruitops-metrics-token }
    static_configs: [{ targets: ["<api-host-private-address>:8000"] }]
```

Plus, outside the hosting provider (so it still works when everything else is
down): an uptime check on `https://<domain>/api/v1/health` every minute,
alerting after 2 failures, and one on the certificate's expiry (Caddy renews
automatically; this catches it if it can't).

## Escalation

1. Pages go to the on-call owner's phone (the uptime service's app, or
   Alertmanager → PagerDuty/Opsgenie/SMS). Today that is the product owner
   (decision I-1: solo owner).
2. Acknowledge within 15 minutes during IST business hours, 60 minutes outside.
3. If a deploy caused it: `./deploy.sh --rollback` first, investigate after.
4. Follow `engineering:incident-response` for anything customer-visible; write
   a short postmortem within 3 working days.

Name a backup person before launch (go/no-go checklist).

## Prove that alerts reach you (go/no-go evidence)

1. Uptime monitor: pause the `edge` container for 3 minutes
   (`docker compose --env-file production.env stop edge`, then `start`) on
   **staging**. You should be paged.
2. Job heartbeat: `curl -fsS "$JOB_HEARTBEAT_URL/test-alert/fail"`. You should
   get the failed-job notification.
3. Prometheus path: `amtool alert add RecruitOpsTestAlert severity=page` against
   Alertmanager (or the collector's "send test notification" button).

Record the time each arrived; that's the evidence.

## Runbook entries

### errors
Look at the access log for `status >= 500` grouped by `route`; open the
matching Sentry issue by `request_id`. A spike right after a deploy → roll
back. `DATABASE_UNAVAILABLE` errors → check the database and `/readyz`.

### latency
Group slow requests by `route` in the access log. Reports first: the
metric-bucket view uses scalar functions (Phase 4 note), so check the query
plan under load. Then the database's DTU/vCore usage.

### down
`./deploy.sh --status`, then `docker compose ... logs --tail 200 api`.
`/livez` failing → the process; `/readyz` failing → a dependency.

### email
Check the SMTP provider's dashboard (suspended account, bounced domain,
expired credentials). Sign-up, invites and password resets queue nothing:
users simply don't get the email, so tell affected users to retry after the fix.
