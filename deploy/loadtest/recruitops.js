// RecruitOps load test (Phase 6.7) — k6.
//
// 3× the planned peak (100 concurrent people → 300 virtual users), doing what
// recruiters and managers actually do, with think time between actions. The
// run FAILS (non-zero exit) when any target in docs/runbooks/monitoring.md is
// missed:
//   reads   p95 < 400 ms     writes  p95 < 800 ms     reports p95 < 2 s
//   errors  < 1 %            checks  > 99 %
//
//   k6 run -e BASE_URL=https://staging.<domain> -e FIXTURE=fixture.json recruitops.js
// See deploy/loadtest/README.md (fixture, run.sh, reading the report).

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import { Counter } from 'k6/metrics';

const BASE = (__ENV.BASE_URL || 'https://localhost:8443').replace(/\/$/, '');
const API = `${BASE}/api/v1`;
const VUS = parseInt(__ENV.VUS || '300', 10);
const HOLD = __ENV.HOLD || '10m';
const THINK = parseFloat(__ENV.THINK_SECONDS || '5'); // mean pause between actions

const fixture = JSON.parse(open(__ENV.FIXTURE || './fixture.json'));
const users = new SharedArray('users', () => fixture.users);
const requisitions = new SharedArray('requisitions', () => fixture.requisitions);
const managers = users.filter((u) => u.role === 'manager');
const recruiters = users.filter((u) => u.role === 'recruiter');
const unexpected = new Counter('unexpected_status');

export const options = {
  insecureSkipTLSVerify: __ENV.INSECURE === '1', // local compose stack only (self-signed)
  scenarios: {
    // 85 % recruiters, 15 % managers — roughly the shape of a staffing team.
    recruiters: {
      executor: 'ramping-vus', exec: 'recruiter', startVUs: 0, gracefulRampDown: '30s',
      stages: [{ duration: '3m', target: Math.round(VUS * 0.85) }, { duration: HOLD, target: Math.round(VUS * 0.85) },
               { duration: '1m', target: 0 }],
    },
    managers: {
      executor: 'ramping-vus', exec: 'manager', startVUs: 0, gracefulRampDown: '30s',
      stages: [{ duration: '3m', target: Math.round(VUS * 0.15) }, { duration: HOLD, target: Math.round(VUS * 0.15) },
               { duration: '1m', target: 0 }],
    },
  },
  thresholds: {
    'http_req_duration{kind:read}': ['p(95)<400'],
    'http_req_duration{kind:write}': ['p(95)<800'],
    'http_req_duration{kind:report}': ['p(95)<2000'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99'],
    unexpected_status: ['count<1'],
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

function pick(list) { return list[Math.floor(Math.random() * list.length)]; }
function pause() { sleep(THINK * (0.5 + Math.random())); }
function headers(user) {
  return { headers: { Authorization: `Bearer ${user.token}`, 'Content-Type': 'application/json',
                      'X-Request-ID': `lt-${__VU}-${__ITER}-${Date.now()}` } };
}

// One request, tagged by kind (read/write/report) and by a stable route name so
// the summary groups /candidates/123 and /candidates/456 together.
function call(user, method, path, kind, name, body, ok = [200]) {
  const params = Object.assign(headers(user), { tags: { kind, name } });
  const res = http.request(method, `${API}${path}`, body === undefined ? null : JSON.stringify(body), params);
  const good = check(res, { [`${name} ${ok.join('/')}`]: (r) => ok.includes(r.status) });
  if (!good) {
    unexpected.add(1, { name, status: String(res.status) });
    if (__ENV.DEBUG) console.warn(`${method} ${path} -> ${res.status} ${String(res.body).slice(0, 200)}`);
  }
  return res;
}

function json(res) { try { return res.json(); } catch (_) { return null; } }

export function recruiter() {
  const me = recruiters[(__VU - 1) % recruiters.length];
  group('start of day', () => {
    call(me, 'GET', '/auth/me', 'read', 'auth/me');
    call(me, 'GET', '/dashboards/my-work', 'read', 'dashboards/my-work');
    call(me, 'GET', '/notifications/?page_size=20', 'read', 'notifications');
  });
  pause();

  group('work the pipeline', () => {
    call(me, 'GET', `/pipeline/board?owner_user_id=${me.id}`, 'read', 'pipeline/board');
    pause();
    if (!me.applications.length) return;
    const appId = pick(me.applications);
    const detail = json(call(me, 'GET', `/pipeline/applications/${appId}`, 'read', 'pipeline/application'));
    call(me, 'GET', `/pipeline/applications/${appId}/history`, 'read', 'pipeline/history');
    pause();
    // Move between two open stages; a note makes backward moves legal (4.6).
    if (detail && detail.application_status === 'active' && Math.random() < 0.5) {
      const to = detail.current_stage === 'interview' ? 'screening' : 'interview';
      call(me, 'PATCH', `/pipeline/applications/${appId}/stage`, 'write', 'pipeline/stage-move',
           { to_stage: to, notes: 'load test move' });
    }
  });
  pause();

  group('candidates', () => {
    const page = 1 + Math.floor(Math.random() * 5);
    call(me, 'GET', `/candidates/?page=${page}&page_size=20&owner_user_id=${me.id}`, 'read', 'candidates/list');
    call(me, 'GET', `/candidates/?search=${pick(['Sharma', 'Iyer', 'Khan', 'Rao', 'Patel'])}&page_size=20`,
         'read', 'candidates/search');
    if (me.candidates.length) {
      const cid = pick(me.candidates);
      call(me, 'GET', `/candidates/${cid}`, 'read', 'candidates/detail');
      pause();
      if (Math.random() < 0.3) {
        call(me, 'PATCH', `/candidates/${cid}`, 'write', 'candidates/update',
             { current_designation: pick(['Associate', 'Senior Associate', 'Lead', 'Manager']) });
      }
    }
    if (Math.random() < 0.1) { // a new candidate now and then
      const n = `${__VU}${__ITER}${Date.now() % 100000}`;
      call(me, 'POST', '/candidates/', 'write', 'candidates/create', {
        full_name: `Load Candidate ${n}`, email: `lt${n}@new.loadtest.example.com`,
        source_type: 'LinkedIn', primary_owner_user_id: me.id, save_mode: 'draft',
      }, [201]);
    }
  });
  pause();

  group('requisitions', () => {
    call(me, 'GET', `/requisitions/?page_size=20&primary_owner_user_id=${me.id}`, 'read', 'requisitions/list');
    call(me, 'GET', `/requisitions/${pick(requisitions)}`, 'read', 'requisitions/detail');
  });
  pause();
}

export function manager() {
  const me = managers[(__VU - 1) % managers.length];
  group('overview', () => {
    call(me, 'GET', '/dashboards/role', 'read', 'dashboards/role');
    call(me, 'GET', '/dashboards/location-summary', 'read', 'dashboards/location-summary');
    call(me, 'GET', '/requisitions/?page_size=20', 'read', 'requisitions/list');
    call(me, 'GET', '/approvals/?page_size=20', 'read', 'approvals/list');
  });
  pause();
  group('reports', () => {
    const report = pick(['placements', 'time-to-fill', 'client-summary', 'source-effectiveness', 'withdrawal-reasons']);
    call(me, 'GET', `/reports/${report}`, 'report', `reports/${report}`);
  });
  pause();
  group('drill in', () => {
    call(me, 'GET', `/requisitions/${pick(requisitions)}`, 'read', 'requisitions/detail');
    call(me, 'GET', '/pipeline/board', 'read', 'pipeline/board-all');
  });
  pause();
}

export function handleSummary(data) {
  const out = { stdout: textSummary(data) };
  out[__ENV.SUMMARY || 'loadtest-summary.json'] = JSON.stringify(data, null, 1);
  return out;
}

// Compact, dependency-free text summary: one line per kind and per route.
function textSummary(data) {
  const m = data.metrics;
  const line = (label, metric) => {
    if (!metric) return `  ${label.padEnd(34)} (no requests)`;
    const v = metric.values;
    return `  ${label.padEnd(34)} p95 ${v['p(95)'].toFixed(0).padStart(6)} ms   p99 ${v['p(99)'].toFixed(0).padStart(6)} ms   max ${v.max.toFixed(0).padStart(6)} ms`;
  };
  const rows = ['', 'RecruitOps load test', `  target ${BASE}, ${VUS} virtual users, hold ${HOLD}`, ''];
  rows.push(line('reads   (target p95 < 400 ms)', m['http_req_duration{kind:read}']));
  rows.push(line('writes  (target p95 < 800 ms)', m['http_req_duration{kind:write}']));
  rows.push(line('reports (target p95 < 2000 ms)', m['http_req_duration{kind:report}']));
  const failed = m.http_req_failed ? (m.http_req_failed.values.rate * 100).toFixed(2) : '0';
  rows.push(`  failed requests ${failed} %   requests ${m.http_reqs ? m.http_reqs.values.count : 0}` +
            `   (${m.http_reqs ? m.http_reqs.values.rate.toFixed(1) : 0}/s)`);
  const crossed = Object.entries(m).filter(([, v]) => v.thresholds && Object.values(v.thresholds).some((t) => !t.ok))
    .map(([k]) => k);
  rows.push('', crossed.length ? `  ✗ FAILED: ${crossed.join(', ')}` : '  ✓ every target met', '');
  return rows.join('\n');
}
