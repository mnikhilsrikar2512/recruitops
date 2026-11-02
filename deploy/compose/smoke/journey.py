"""User-journey smoke test against the running stack, through the TLS edge:
pages and headers, sign-up -> emailed link -> two-step set-up -> sign-in,
forgot-password by email, inviting a user by email.

    pip install httpx && python deploy/compose/smoke/journey.py
"""
import re, sys, time, json, hmac, hashlib, base64, struct, os
import httpx

BASE = os.environ.get("SMOKE_BASE_URL", "https://localhost:8443")
MAIL = os.environ.get("SMOKE_MAIL_API", "http://localhost:8025")
c = httpx.Client(base_url=BASE, verify=False, timeout=30, trust_env=False)
httpx_get = httpx.get
httpx.get = lambda *a, **k: httpx_get(*a, trust_env=False, **k)
ok = []

def check(name, cond, detail=""):
    ok.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))

def totp(secret, t=None):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    counter = int((t or time.time()) // 30)
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 15
    return f"{(struct.unpack('>I', h[o:o+4])[0] & 0x7fffffff) % 1000000:06d}"

def mail_for(to, subject_part, after=0):
    for _ in range(30):
        msgs = httpx.get(f"{MAIL}/api/v1/messages").json().get("messages", [])
        for m in msgs:
            if any(r["Address"] == to for r in m["To"]) and subject_part in m["Subject"] and m["ID"] not in after_ids:
                return httpx.get(f"{MAIL}/api/v1/message/{m['ID']}").json()
        time.sleep(1)
    return None
after_ids = set()

# --- edge, headers, probes
r = c.get("/pages/login.html")
check("login page over TLS", r.status_code == 200)
check("CSP on pages", "default-src 'self'" in r.headers.get("content-security-policy", ""))
check("HSTS on pages", "max-age=31536000" in r.headers.get("strict-transport-security", ""))
check("short URL /login works", c.get("/login").status_code == 200)
check("unknown page -> 404 page", c.get("/nope-xyz").status_code == 404)
check("dotfile blocked", c.get("/.env").status_code == 404)
r = c.get("/api/v1/health")
check("API via edge", r.status_code == 200 and r.json()["database_status"] == "ok", r.text)
check("request id echoed", len(r.headers.get("x-request-id", "")) >= 16)
check("API HSTS", "max-age" in r.headers.get("strict-transport-security", ""))
r = c.get("/shared/global.css")
check("assets cached immutable", "immutable" in r.headers.get("cache-control", ""))

# --- signup -> verification email -> MFA -> active
docs = c.get("/api/v1/legal/documents").json()
items = docs.get("items", docs if isinstance(docs, list) else [])
accepted = {d["doc_type"] if "doc_type" in d else d["type"]: d["version"] for d in items}
email = f"owner{int(time.time())}@acme-e2e.io"
pw = "correct-horse-battery-staple-91"
r = c.post("/api/v1/signup/", json={"company_name": "Acme E2E", "admin_name": "Olivia Owner", "email": email,
                                   "password": pw, "city": "Pune", "accepted": accepted})
check("signup accepted", r.status_code == 202, r.text)
check("no dev token leaked in staging", r.json().get("dev_verify_token") is None)
m = mail_for(email, "Confirm your email")
check("verification email delivered (STARTTLS)", m is not None)
token = re.search(r"signup-verify\.html\?token=([A-Za-z0-9_\-%]+)", m["Text"]).group(1)
check("link uses FRONTEND_BASE_URL", "https://localhost:8443/pages/signup-verify.html" in m["Text"])
r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
check("pending company can't sign in", r.status_code in (401, 403), r.status_code)
r = c.post("/api/v1/signup/verify", json={"token": httpx.URL("x?t=" + token).params["t"]})
check("verify -> mfa next", r.status_code == 200 and r.json()["next"] == "mfa", r.text)
setup = r.json()["setup_token"]
secret = c.post("/api/v1/signup/mfa/start", json={"setup_token": setup}).json()["secret"]
r = c.post("/api/v1/signup/mfa/confirm", json={"setup_token": setup, "code": totp(secret)})
check("mfa confirm activates company", r.status_code == 200, r.text)

# --- MFA secret is encrypted at rest
row = os.popen(f"cd {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))} && docker compose --env-file staging.env exec -T sqlserver "
               f"/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"$(grep ^MSSQL_SA_PASSWORD staging.env | cut -d= -f2-)\" -C -d recruitops -h -1 -W "
               f"-Q \"SET NOCOUNT ON; SELECT m.totp_secret FROM dbo.user_mfa m JOIN dbo.users u ON u.id=m.user_id WHERE u.email=N'{email}'\"").read().strip()
check("TOTP seed stored encrypted", row.startswith("enc:v1:local1:") and secret not in row, row[:40])

# --- sign in with MFA (next 30s window so the code isn't reused)
time.sleep(31 - (time.time() % 30))
r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
check("login asks for second factor", r.status_code == 200 and r.json().get("mfa_required"), r.text)
r = c.post("/api/v1/auth/mfa/challenge", json={"mfa_token": r.json()["mfa_token"], "code": totp(secret)})
check("mfa challenge signs in", r.status_code == 200 and r.json().get("token"), r.text)
auth = {"Authorization": f"Bearer {r.json()['token']}"}
me = c.get("/api/v1/auth/me", headers=auth).json()
uid = me.get("id") or me.get("user", {}).get("id")
check("signed in as admin", uid is not None, json.dumps(me)[:200])

# --- forgot password -> email -> reset
after_ids |= {m["ID"] for m in httpx.get(f"{MAIL}/api/v1/messages").json()["messages"]}
r = c.post("/api/v1/auth/password/forgot", json={"email": email})
check("forgot-password 200", r.status_code == 200, r.text)
m = mail_for(email, "Reset Your Password")
check("reset email delivered", m is not None)
rtok = re.search(r"reset-password\.html\?token=([^\s]+)", m["Text"]).group(1)
r = c.post("/api/v1/auth/password/reset", json={"token": httpx.URL("x?t=" + rtok).params["t"], "new_password": pw + "-new"})
check("reset with emailed link works", r.status_code == 200, r.text)
pw = pw + "-new"

# re-login after reset (reset revokes sessions)
time.sleep(31 - (time.time() % 30))
r = c.post("/api/v1/auth/login", json={"email": email, "password": pw})
r = c.post("/api/v1/auth/mfa/challenge", json={"mfa_token": r.json()["mfa_token"], "code": totp(secret)})
auth = {"Authorization": f"Bearer {r.json()['token']}"}
r = c.get("/api/v1/legal/acceptances", headers=auth)
check("legal status readable", r.status_code == 200, r.text)

# --- invite a user -> invitation email -> password setup
office = c.get("/api/v1/locations/?page_size=5", headers=auth).json()["items"][0]["id"]
roles = c.get("/api/v1/roles/?page_size=50", headers=auth).json()["items"]
role = c.post("/api/v1/roles/", headers=auth, json={"name": "Recruiter", "code": f"rec{int(time.time())}",
                                                    "description": "e2e"}).json()
check("custom role created", "id" in role, json.dumps(role)[:200])
invitee = f"rita{int(time.time())}@acme-e2e.io"
after_ids |= {m["ID"] for m in httpx.get(f"{MAIL}/api/v1/messages").json()["messages"]}
r = c.post("/api/v1/users/", headers=auth, json={"full_name": "Rita Recruiter", "email": invitee,
           "employee_code": f"E{int(time.time())}", "primary_location_id": office, "primary_role_id": role["id"]})
check("user created", r.status_code == 201, r.text)
m = mail_for(invitee, "Set Up Your Password")
check("invitation email delivered", m is not None and "Olivia Owner" in m["HTML"])
stok = re.search(r"password-setup\.html\?token=([^\s]+)", m["Text"]).group(1)
r = c.post("/api/v1/auth/password/setup", json={"token": httpx.URL("x?t=" + stok).params["t"], "new_password": "another-long-passphrase-77"})
check("invitee sets password from email", r.status_code == 200, r.text)
r = c.post("/api/v1/auth/login", json={"email": invitee, "password": "another-long-passphrase-77"})
check("invitee can sign in", r.status_code == 200 and (r.json().get("token") or r.json().get("mfa_required") is not None), r.text)

print("RESULT", sum(ok), "/", len(ok))
sys.exit(0 if all(ok) else 1)
