# CompanyIQ

AI-powered career intelligence for job seekers. Upload your resume + a company name and get a 13-section intelligence report, a tailored cover letter, JD fit analysis, company comparison, salary estimates, interview flashcards, and an application tracker — powered by GROQ's `compound-beta` model with live web search.

---

## Features

| Tool | What it does |
|------|--------------|
| 🔍 **Company Report** | 13-section deep-dive: overview, leadership, culture, red flags, interview questions, candidate fit. Exports PDF + Markdown + PPT prompt. |
| ✉️ **Cover Letter** | Personalised, human-sounding cover letter for a specific company + role. |
| 📋 **JD Fit Analyser** | Paste a job description → fit score, ATS keyword match, skill gaps, tailored pitch. |
| ⚖️ **Compare** | Two companies head-to-head for your profile, with a clear verdict. |
| 💰 **Salary Intel** | Realistic comp band + negotiation tips for a role at any company. |
| 🗂️ **Tracker** | Kanban-style application pipeline (saved → applied → interviewing → offer). |
| 📚 **Flashcards** | Real interview questions turned into a flip-card study deck. |

Accounts, per-user monthly quotas, redemption-code upgrades, and shareable report links are all built in.

---

## Quick start (local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
#   → set GROQ_API_KEY (get one free at https://console.groq.com)
#   → set a long random JWT_SECRET and a private ADMIN_KEY

# 3. Run
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000** — you'll be asked to create an account (stored locally in SQLite).

Landing/pricing page: **http://localhost:8000/landing.html**

---

## Environment variables

| Var | Required | Purpose |
|-----|----------|---------|
| `GROQ_API_KEY` | ✅ | GROQ API key |
| `JWT_SECRET` | ✅ (prod) | Signs login tokens. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_KEY` | ✅ (prod) | Required to mint redemption codes |
| `FREE_REPORTS_PER_MONTH` | — | Free-tier report cap (default 3) |
| `FREE_COVER_LETTERS_PER_MONTH` | — | default 2 |
| `FREE_JD_PER_MONTH` | — | default 2 |
| `FREE_COMPARE_PER_MONTH` | — | default 1 |
| `RATE_LIMIT` | — | Per-IP rate limit (default `60/hour`) |
| `DB_PATH` | — | SQLite path (default `data/companyiq.db`) |

---

## Selling to users (the money flow)

There's no payment gateway wired in by default (those need business verification). The built-in model works for selling to friends / a small audience today:

1. A user hits their free limit → the app shows your **UPI ID** and asks them to pay (₹199 Pro / ₹499 Lifetime).
2. They send you a payment screenshot (e.g. on WhatsApp).
3. You generate a **redemption code** and send it to them.
4. They paste it into the app → instantly upgraded.

**Generate codes** (replace the admin key with yours):

```bash
curl -X POST http://localhost:8000/api/admin/generate-codes \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"plan":"pro","duration_days":30,"count":5,"note":"march-batch"}'
```

Returns 5 codes like `IQ-AB3CD-EF7GH`. `plan` is `pro` or `lifetime`; for lifetime, `duration_days` is ignored.

> ⚠️ Set your real UPI ID in `frontend/app.js` (the `UPI_ID` constant near the top).

To automate later, swap the redemption step for **Razorpay** — the upgrade flow already has a clean integration point.

---

## Deployment

### Docker
```bash
docker-compose up --build   # serves on http://localhost:3000
```
Pass `GROQ_API_KEY`, `JWT_SECRET`, and `ADMIN_KEY` via environment.

### Vercel
`api/index.py` is the serverless entry point; `vercel.json` routes `/api/*` to it and serves the frontend statically. Set the env vars in the Vercel dashboard.

> **Note on persistence:** the app uses SQLite. On ephemeral/serverless hosts the DB resets on redeploy. For production, point `DB_PATH` at a mounted volume, or migrate to hosted Postgres/Turso (only `backend/utils/db.py`, `job_store.py`, and `user_store.py` touch the database).

---

## Architecture

```
backend/
  main.py              FastAPI app + router registration
  config.py            Settings, plan/quota definitions
  deps.py              get_current_user, enforce_quota
  models/schemas.py    Pydantic models
  services/            groq, cover_letter, jd_analyzer, compare, pdf, md, ppt, auth
  routes/              auth, admin, analyze, tools, history, share, tracker, health
  utils/               db, job_store, user_store
frontend/
  index.html  app.js  style.css   The single-page app
  landing.html                     Marketing / pricing page
  share.html                       Public shared-report view
```

Auth is JWT (Bearer token in `localStorage`). All `/api/*` tool routes require a valid token; metered actions are checked against the user's monthly quota and recorded in `usage_events`.
