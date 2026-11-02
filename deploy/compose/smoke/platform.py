"""Platform smoke test against the running compose stack: files through S3 +
ClamAV, spoofed-IP rate limiting, metrics, readiness, scheduler, JSON logs.
Run after journey.py (it uses up the sign-in rate limit on purpose).

    pip install httpx && python deploy/compose/smoke/platform.py
"""
import re, sys, time, json, hmac, hashlib, base64, struct, os, subprocess
import httpx

BASE = os.environ.get("SMOKE_BASE_URL", "https://localhost:8443"); MAIL = os.environ.get("SMOKE_MAIL_API", "http://localhost:8025")
c = httpx.Client(base_url=BASE, verify=False, timeout=60, trust_env=False)
ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
def totp(secret):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    h = hmac.new(key, struct.pack(">Q", int(time.time() // 30)), hashlib.sha1).digest(); o = h[-1] & 15
    return f"{(struct.unpack('>I', h[o:o+4])[0] & 0x7fffffff) % 1000000:06d}"
def compose(*args):
    return subprocess.run(["docker", "compose", "--env-file", "staging.env", *args], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          capture_output=True, text=True)
def mail_for(to, subj):
    for _ in range(30):
        for m in httpx.get(f"{MAIL}/api/v1/messages", trust_env=False).json()["messages"]:
            if any(r["Address"] == to for r in m["To"]) and subj in m["Subject"]:
                return httpx.get(f"{MAIL}/api/v1/message/{m['ID']}", trust_env=False).json()
        time.sleep(1)

# fresh company + admin
docs = c.get("/api/v1/legal/documents").json(); items = docs.get("items", docs)
accepted = {(d.get("doc_type") or d.get("type")): d["version"] for d in items}
email = f"files{int(time.time())}@acme-e2e.io"; pw = "a-very-long-and-unusual-passphrase-5"
c.post("/api/v1/signup/", json={"company_name": "Files Co", "admin_name": "Fay Files", "email": email, "password": pw, "accepted": accepted})
tok = re.search(r"token=([^\s]+)", mail_for(email, "Confirm")["Text"]).group(1)
setup = c.post("/api/v1/signup/verify", json={"token": httpx.URL("x?t=" + tok).params["t"]}).json()["setup_token"]
secret = c.post("/api/v1/signup/mfa/start", json={"setup_token": setup}).json()["secret"]
c.post("/api/v1/signup/mfa/confirm", json={"setup_token": setup, "code": totp(secret)})
time.sleep(31 - (time.time() % 30))
r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
r = c.post("/api/v1/auth/mfa/challenge", json={"mfa_token": r.json()["mfa_token"], "code": totp(secret)})
auth = {"Authorization": f"Bearer {r.json()['token']}"}
me = c.get("/api/v1/auth/me", headers=auth).json(); uid = me.get("id") or me["user"]["id"]
r = c.put(f"/api/v1/users/{uid}/extra-permissions", headers=auth,
          json={"permission_codes": ["candidate.create", "candidate.read", "candidate.update", "candidate.resume.upload"]})
check("grant upload permissions", r.status_code == 200, r.text[:300])
r = c.post("/api/v1/candidates/", headers=auth, json={"full_name": "Carla Candidate", "email": "carla@cand-e2e.io",
           "source_type": "referral", "primary_owner_user_id": uid, "save_mode": "draft"})
check("candidate created", r.status_code == 201, r.text[:300]); cid = r.json()["id"]

pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
r = c.post(f"/api/v1/candidates/{cid}/upload?document_type=resume", headers=auth, files={"file": ("cv.pdf", pdf, "application/pdf")})
check("clean PDF uploaded (ClamAV scan + S3)", r.status_code == 201, r.text[:300]); doc = r.json()
eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
# EICAR is only recognised at the start of a file, so it can't also be a valid PDF: check the scanner itself.
r = compose("exec", "-T", "api", "python", "-c", "from app.core.malware import get_scanner;"
            "print(get_scanner().scan(b'X5O!P%@AP[4\\\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*'))")
check("real ClamAV flags EICAR", "clean=False" in r.stdout and "clamav" in r.stdout, r.stdout + r.stderr)
exe = b"MZ" + b"\x00" * 200
r = c.post(f"/api/v1/candidates/{cid}/upload?document_type=resume", headers=auth, files={"file": ("cv.pdf", exe, "application/pdf")})
check(".exe renamed .pdf refused", r.status_code == 422, r.text[:200])
r = c.get(f"/api/v1/candidates/{cid}/documents/{doc['id']}/link", headers=auth)
check("signed link issued", r.status_code == 200, r.text[:300])
url = r.json().get("url", "")
check("link is a presigned S3 URL under the company prefix", "s3.localhost:8333/recruitops-files/tenant_" in url and "X-Amz-Signature" in url, url[:120])
got = httpx.get(url.replace("s3.localhost", "127.0.0.1"), headers={"Host": "s3.localhost:8333"}, trust_env=False)
check("presigned link downloads the file", got.status_code == 200 and got.content == pdf, got.status_code)
raw = httpx.get(url.split("?")[0].replace("s3.localhost", "127.0.0.1"), headers={"Host": "s3.localhost:8333"}, trust_env=False)
check("bucket is private without the signature", raw.status_code in (401, 403), raw.status_code)

# spoofed X-Forwarded-For can't buy fresh rate-limit buckets
codes = [c.post("/api/v1/auth/login", json={"email": f"nobody{n}@x-e2e.io", "password": "wrong-password-x"},
                headers={"X-Forwarded-For": f"9.9.9.{n}"}).status_code for n in range(7)]
check("login IP limit holds against spoofed X-Forwarded-For", 429 in codes, codes)

# metrics (inside the network only, token required)
tokenline = [l for l in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "staging.env")) if l.startswith("METRICS_TOKEN=")][-1].strip().split("=", 1)[1]
m1 = compose("exec", "-T", "api", "python", "-c", "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/metrics').status)")
check("metrics refuse without token", "401" in (m1.stdout + m1.stderr))
m2 = compose("exec", "-T", "api", "python", "-c", f"import urllib.request as u;r=u.Request('http://127.0.0.1:8000/metrics',headers={{'Authorization':'Bearer {tokenline}'}});print(u.urlopen(r).read().decode())")
check("metrics with token", "recruitops_http_requests_total" in m2.stdout and 'route="/api/v1/candidates/{candidate_id}/upload"' in m2.stdout, m2.stderr[-300:])
check("emails counted", 'recruitops_emails_total{result="sent"}' in m2.stdout)
check("/metrics not reachable through the public edge", c.get("/metrics").status_code == 404)
r = compose("exec", "-T", "api", "python", "-c", "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/readyz').read().decode())")
check("readyz ok (db + redis)", '"database": "ok"' in r.stdout.replace('":"', '": "') or '"database":"ok"' in r.stdout, r.stdout + r.stderr)

# scheduler
r = compose("exec", "-T", "scheduler", "python", "scripts/scheduler.py", "--run-once", "housekeeping")
check("scheduler job runs once", r.returncode == 0, r.stdout[-300:] + r.stderr[-300:])
logs = compose("logs", "scheduler").stdout
check("scheduler ran privacy_jobs on start", '"job": "privacy_jobs"' in logs and '"outcome": "ok"' in logs, logs[-500:])

# structured logs
logs = compose("logs", "--no-log-prefix", "api").stdout.splitlines()
access = [json.loads(l) for l in logs if l.startswith("{") and '"recruitops.access"' in l]
check("API logs are JSON with request ids", access and all("request_id" in a for a in access[-20:]))
check("access log has route templates, no tokens", not any("token=" in a.get("msg", "") for a in access))
check("tenant/user ids on authenticated lines", any("tenant_id" in a and "user_id" in a for a in access))
print("RESULT", sum(ok), "/", len(ok)); sys.exit(0 if all(ok) else 1)
