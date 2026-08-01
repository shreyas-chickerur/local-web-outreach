# Operator Setup Guide — everything YOU do by hand

This is the human checklist for running the platform. The code handles the
pipeline; this covers the accounts, keys, domains, legal items, and decisions the
code can't make for you.

**Build status (2026-08-01):** built + tested through **Phase 6** (research → site
→ email, all approval-gated; 177 tests green). **Not built yet:** Phase 7 (actually
sending), Phase 8 (reply/complaint monitoring), Phase 10 (payments). Steps for
those are marked **[LATER]** — set the accounts up now (they have lead time), but
the software to use them lands in a later phase.

**Your progress so far (2026-08-01):**
- ☑ `GOOGLE_PLACES_API_KEY` in `.env`
- ☑ `ANTHROPIC_API_KEY` in `.env`
- ☑ `SENDER_NAME` + `SENDER_POSTAL_ADDRESS` lines present in `.env`
- ☑ Console wired to the backend — `make seed && make api` → http://127.0.0.1:8090
- ☐ **Edit `SENDER_POSTAL_ADDRESS` to a real mailing address** (still the placeholder;
  a send-time guard now refuses to send while it's a placeholder)
- ☐ Real-data dry run + your review (A8)
- ☐ Everything in Part B (needed before any send)

**Golden rule:** secrets live in a local `.env` (gitignored). Never commit them,
never paste them into chat. Use a password manager for every account below.

---

## Part A — Do now (works with what's built today)

### A1. Local setup
1. Install Python 3.11+, git, and a local PostgreSQL (or use SQLite for dev).
2. `git clone https://github.com/shreyas-chickerur/local-web-outreach.git`
3. `cd local-web-outreach && make install`
4. `make test-all` → expect all green. `make cov` for coverage.

### A2. Create the dedicated project Gmail (the "hub" account)
This one Google account owns everything and is your reply/complaint monitoring
inbox. **It is NOT what sends cold email** (that's Google Workspace on secondary
domains — see B2; Gmail's terms forbid bulk cold email from a free @gmail.com and
Google suspends accounts that do it).
1. Go to https://accounts.google.com/signup — create a NEW account.
2. Pick a professional handle tied to the business, not your name
   (e.g. `hello.<yourbrand>@gmail.com`). Write the exact address down.
3. Turn on 2-Step Verification and store the password + recovery codes in your
   password manager.
4. Use THIS account to log into everything below (GitHub, Google Cloud, the domain
   registrar, Google Workspace admin, Anthropic, Stripe). One identity, one place
   to monitor.

### A3. Google Places API key (lead discovery) — ☑ DONE (key in `.env`)
1. Log into https://console.cloud.google.com with the hub Gmail.
2. Create a project (e.g. "local-web-outreach").
3. Enable the **Places API** (and Maps if prompted).
4. Create an API key under **APIs & Services → Credentials**; restrict it to the
   Places API. Copy it into your password manager.
5. Note: billing must be enabled; Places has a monthly free tier, then per-call
   cost. Set a budget alert.

### A4. Anthropic API key (research + copy) — ☑ DONE (key in `.env`)
1. Sign up at https://console.anthropic.com with the hub Gmail.
2. Create an API key; copy it. Add a small credit + a spend limit.

### A5. Physical mailing address (legally required for email)
CAN-SPAM requires a real postal address in every email footer. Get one you're
comfortable publishing:
- a PO box, a registered-agent address, or a business mailing address.
Write it down exactly as it should appear.

### A6. Configure the app — ☑ mostly done
Your `.env` already has `GOOGLE_PLACES_API_KEY`, `ANTHROPIC_API_KEY`,
`SENDER_NAME`, and a placeholder `SENDER_POSTAL_ADDRESS`. `DATABASE_URL` is unset
(SQLite default — fine for dev). Remaining:
1. **Edit `SENDER_POSTAL_ADDRESS`** to your real A5 address (still the placeholder).
2. Verify: `make email-demo` — confirm your real address + the opt-out line show
   in the footer. (Nothing sends; no key needed for this.)

### A7. Wire the console to the backend — ☑ DONE
The console lives in `console/` and is served by FastAPI at the root, with its
data layer (`console/api.js`) calling the real endpoints — same origin, no CORS.
To run it:

```bash
make seed    # fill the DB with the bundled pipeline (both gates populated)
make api     # then open http://127.0.0.1:8090
```

`make seed --reset` wipes and reseeds. Both approval gates work end-to-end
(verified in-browser): approving an email advances EMAIL_DRAFTED →
EMAIL_APPROVED and writes a hashed approval to the log.

**Known gap:** the *Edit* button isn't wired — server-side draft editing needs an
endpoint that re-generates and re-hashes the draft. Approve / Reject / Request
changes are fully wired; Edit shows a clear message.

### A8. Real-data dry run + YOUR review (the real quality gate)
1. `export GOOGLE_PLACES_API_KEY=...` then `make discover LOCATION="Frisco, TX" CATEGORY=restaurant`
2. Take ~5 real leads all the way to an approved email (via the console).
3. **Read every generated site and every email yourself.** Only proceed if you'd
   confidently send each one under your name. Nothing is sent — this is review only.

---

## Part B — Before any real send (start now; multi-week lead time) [LATER to use]

### B1. Buy secondary sending domains
- At a registrar (Cloudflare/Namecheap), buy 3–5 brand-adjacent `.com` domains
  (NOT your main brand domain). Enable WHOIS privacy. Log in with the hub Gmail.

### B2. Google Workspace on the sending domains
- Sign up for Google Workspace (admin = the hub Gmail). Add each secondary domain.
- Create 2–3 mailboxes per domain. These are what SEND (10–20 emails/inbox/day max).

### B3. DNS authentication + monitoring
- For each sending domain set **SPF, DKIM, and DMARC** records (Workspace gives
  you the values). Verify each domain in **Google Postmaster Tools**.

### B4. Warm the inboxes (3–4 weeks BEFORE sending)
- Use a warmup tool (or your managed sender) to ramp each mailbox slowly. Sending
  cold before warmup burns the domain. This is the long pole — start it early.

### B5. Decide the sending approach
- **Managed** (Instantly / Smartlead): they handle rotation + warmup + reply
  capture. Simplest. — OR —
- **Raw** Google Workspace + the domains above.
This choice determines the Phase-7 sending adapter I build.

### B6. Recipient-email sourcing (required — the pipeline doesn't collect emails)
Discovery gives name/address/phone/website, NOT an email. Decide how you'll fill
`contact_email`: scrape the business's own site for a contact address, use an
enrichment provider, or enter them by hand. Prefer specific owner addresses over
generic `info@` (better deliverability, fewer complaints).

### B7. Production database + hosting [LATER]
- Managed Postgres (Supabase/Neon/RDS) for `DATABASE_URL`.
- Host the FastAPI backend (Railway/Render/Fly) and the console (Vercel).
- Run migrations: `make migrate`.

### B8. Stripe (payments) [LATER — Phase 10]
- Create a Stripe account (hub Gmail). You'll get keys when we build Phase 10.

---

## Part C — Daily operating loop (once Phase 7+ exist)
1. **Discover** new leads for a location.
2. **Review & approve** each generated site in the console (Gate 1).
3. **Review & approve** each outreach email (Gate 2).
4. **Send** — staged (see D3). Nothing goes out without your approval.
5. **Monitor** the hub inbox for replies and complaints; honor every opt-out.

---

## Part D — Compliance & safety (never skip)
1. **Every email** carries your physical address + a working opt-out (enforced in code).
2. **Honor opt-outs within 10 days** — add them to the suppression list immediately.
3. **US-only** to start (CAN-SPAM). Canada/EU need consent — the geo-gate excludes them.
4. **Deliverability kill switch:** auto-pause a domain at bounce >2% or spam >0.3%
   (built in Phase 7). Watch Postmaster Tools.
5. **Staged rollout for the first real send:** (a) send to your OWN test inbox,
   (b) a tiny batch of 5–10 with bounce/spam watched, (c) only then scale.

---

## What only you can do (I can't, by design)
Creating accounts, buying domains, entering passwords/API keys, completing OAuth,
setting DNS, and actually sending email are yours. I build and test the software;
you own the credentials and the send button.
