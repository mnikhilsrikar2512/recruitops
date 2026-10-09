# Runbook — set up a company for a customer (ops provisioning)

Use this when a customer **isn't** signing up themselves at `/pages/signup.html`, for example after a sales-led contract with a DPA signed on paper.

## Before you start
- You have the company name, the first admin's full name and work email, and the head-office city.
- The customer has signed the Data Processing Addendum offline. Note who signed it and the document reference.
- You can run commands in `backend/` against the right database (`backend/.env`).

## Steps
1. **Create the company.** It starts as *pending*: no one can sign in yet.
   ```
   cd backend
   .venv/bin/python scripts/provision_company.py --company "Acme Staffing" \
       --admin-name "Priya Rao" --admin-email priya@acme.example --city Hyderabad \
       --dpa-signed-by "Priya Rao (Director), DPA ref ACME-2026-01"
   ```
   It prints the company id, its **slug**, and a one-time **password setup link** that is valid for 24 hours.
2. **Send the link** to the admin through a channel you trust, such as their verified work email.
3. The admin opens the link and sets a password. This also confirms their email address.
4. **Activation happens automatically.** Right after setting the password, the admin is taken to set up two-step verification (required for admins in staging and production). When that's done, the company becomes **active**. In development, with two-step verification not enforced, the company is active as soon as the password is set.
   - If the admin lost the page part-way, reissue a setup link with `.venv/bin/python scripts/provision_company.py --reissue-link <their email>` (the old link stops working). Then check with `.venv/bin/python scripts/activate_company.py --slug <slug>`, which lists anyone still missing two-step verification.
5. The admin signs in. They're asked to accept the Terms and Privacy Policy; the DPA is already recorded for the company.

## Check
- Admin → Audit Log shows `company.provisioned` and, later, `legal.accepted`.
- `Admin → Data Export/Delete Requests` is reachable for the admin.

## Undo (company created by mistake, nobody has used it)
Purge it through the privacy flow (Admin → Data Export/Delete Requests → Delete). Or, as ops, call `app.services.tenant_purge.purge_company(engine, tenant_id, 0)` from a Python shell. Both keep the audit trail on hold for 90 days.
