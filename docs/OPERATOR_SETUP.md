# Operator Setup Guide — everything YOU do by hand

This is the human checklist for running the platform. The code handles the
pipeline; this covers the accounts, keys, domains, legal items, and decisions the
code can't make for you.

**Build status (2026-08-01):** built + tested through **Phase 6** (research → site
→ email, all approval-gated; 228 tests green). **Not built yet:** Phase 7 (actually
sending), Phase 8 (reply/complaint monitoring), Phase 10 (payments). Steps for
those are marked **[LATER]** — set the accounts up now (they have lead time), but
the software to use them lands in a later phase.

**Your progress so far (2026-08-01):**
- ☑ `GOOGLE_PLACES_API_KEY` + `ANTHROPIC_API_KEY` in `.env` (gitignored, never pushed)
- ☑ `SENDER_NAME` + `SENDER_POSTAL_ADDRESS` lines present in `.env`
- ☑ Console fully wired — all four actions (Approve/Reject/Request changes/Edit)
- ☑ Live source collection + contact-email scraping (`advance`)
- ☑ Independent directories (OpenStreetMap + Yelp) so facts can reach VERIFIED
- ☑ Identity-based dedup (the 3× `JC's Landscaping` bug)
- ☑ Pre-commit hook blocking any `.env` / `.db` commit
- ☑ **A2 — hub Gmail: `friscooperator@gmail.com`**
- ☐ **A4b — get the free Yelp API key** ← do this before the next run
- ☐ **Edit `SENDER_POSTAL_ADDRESS` to a real mailing address** (still the placeholder;
  a send-time guard refuses to send while it's a placeholder)
- ☐ **A8 — real-data dry run + your review** ← the next real milestone
- ☐ Everything in Part B (needed before any send; **B4 warmup takes ~4 weeks — start early**)

**Shortest path from here:** A4b (Yelp key, 5 min) → re-run A8 (`discover` +
`advance`, judge the output) → B1–B4 (domains + warmup, in parallel, because of
the ~4-week warmup clock).

---

## Findings from your first real run (Frisco lawn, 19 businesses) — all addressed

**1. Site drafts were empty ("0 verified facts") — root-caused and fixed.**
All 19 leads have no website, so Google Places was the *only* source, and a fact
needs **two independent** sources to become VERIFIED. Fixed by adding independent
directories: **OpenStreetMap** (free, keyless, always on) and **Yelp** (free key
— see A4b). Verified live: OSM has good storefront coverage but **almost none for
service-area businesses**, which is why the Yelp key is the one that actually
matters for your segment. *Set `YELP_API_KEY` before your next run.*

**2. Duplicate businesses — fixed.** `JC's Landscaping LLC` was discovered 3×
because Google returns one business under several `place_id`s. Discovery now
dedups on a normalized name+address identity (strips punctuation, casing, and
legal suffixes, so "JC's Landscaping LLC" == "Jc's landscaping"), both within a
batch and against rows already in the DB. Locked by tests using that exact case.

**3. Only 2 of 19 had an email.** Email scraping reads the business's own site,
and none of these have one. Unchanged — see B6 for how to source those.

---

## Part A — Do now (works with what's built today)

### A1. Local setup
1. Install Python 3.11+, git, and a local PostgreSQL (or use SQLite for dev).
2. `git clone https://github.com/shreyas-chickerur/local-web-outreach.git`
3. `cd local-web-outreach && make install`
4. `make test-all` → expect all green. `make cov` for coverage.

### A1b. Secrets hygiene (already enforced)
`.env` is gitignored, has never been committed, and is **not** on GitHub (only
`.env.example` is). A pre-commit hook in `.githooks/pre-commit` additionally
blocks any commit containing a `.env` or a `.db` file — even `git add -f`.
If you clone this repo fresh on another machine, re-arm the hook once:

```bash
git config core.hooksPath .githooks
```

Never paste real keys into chat, screenshots, or issues.

### A2. Create the dedicated project Gmail (the "hub" account)
**Why a separate account:** it keeps this business's identity, billing, and
inbound mail out of your personal Gmail, and gives you one place to watch for
replies and complaints. **It is NOT what sends cold email** (that's Google
Workspace on secondary domains — see B2; Gmail's terms forbid bulk cold email
from a free @gmail.com and Google suspends accounts that do it).

**☑ DONE — the hub account is `friscooperator@gmail.com`.**

Remaining housekeeping on it:
1. Add a recovery phone/email so you can't get locked out.
2. Turn on **2-Step Verification** (myaccount.google.com → Security); save the
   password + backup codes in a password manager.
3. Use **this** account for everything from here: the Yelp developer key (A4b),
   the domain registrar (B1), Google Workspace admin (B2), Postmaster Tools
   (B3), and Stripe (B8). One identity, one inbox to monitor.

(It is also the contact address in the OpenStreetMap client's User-Agent, per
their usage policy.)

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

### A4b. Yelp API key — **do this before your next A8 run** (5 minutes, free)
**Why this matters more than it sounds:** a fact needs **two independent
sources** to become VERIFIED. Google Places is one. OpenStreetMap is now wired in
free and keyless — but OSM maps *storefronts*, and it has **almost no coverage of
service-area businesses** (lawn care, plumbing, locksmiths), which is your
segment. I verified this live: OSM found Randy's Steakhouse but none of your 19
lawn-care leads. **Yelp does cover them, with address and phone.** Without it,
your site drafts stay mostly empty.

1. Go to https://www.yelp.com/developers/v3/manage_app (log in as the hub Gmail).
2. Create an app — name it anything ("Local Web Outreach"), pick any industry.
3. Copy the **API Key** into `.env` as `YELP_API_KEY=...`.
4. Free tier is 500 calls/day, which is far more than this pipeline needs.

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

All four actions are wired: **Approve, Reject, Request changes, and Edit.**
Editing re-hashes the draft and appends an audit event; it never changes status
and never records an approval, so you still approve afterwards. An edit cannot
remove the CAN-SPAM footer (it's re-attached) or set a deceptive subject (400).

### A8. Real-data dry run + YOUR review (the real quality gate)

**Everything below is safe: nothing sends. This is the step where you judge
whether the output is good enough to put your name on.**

**Step 1 — pull real businesses from Google Places.** Your key is already in
`.env`, so just run (pick any city and category you like):

```bash
cd ~/CascadeProjects/local-web-outreach
.venv/bin/python -m app.cli discover "Frisco, TX" --category restaurant
```

It prints each business with a status and a WHY. Expect a mix of QUALIFIED (weak
or missing site — these are leads) and DISQUALIFIED (healthy site — correctly
skipped). *If everything comes back DISQUALIFIED, that's the system being honest,
not a bug — try a category more likely to have weak sites (lawn, plumbing,
locksmith, salon, roofing).*

**Step 2 — check what landed in the database:**

```bash
.venv/bin/python -m app.cli status
```

**Step 3 — research → site → email for the qualified leads.** This is one
command; it walks each QUALIFIED business to a drafted site and (where an email
address exists) a drafted outreach email:

```bash
.venv/bin/python -m app.cli advance --limit 5
```

**Step 4 — open the console and review each one:**

```bash
make api      # then open http://127.0.0.1:8090
```

Go to **Review queue**. For each item, read:
- the **research dossier** — is every VERIFIED fact actually right? Click the
  source links. Anything wrong here is the thing to fix before scaling.
- the **generated site** — would a real owner be impressed?
- the **outreach email** (Gate 2) — does it sound like a person, not a bot?

Then act: **A** approve · **E** edit · **R** request changes · **X** reject.

**Step 5 — the honest judgment.** You're ready to move on only if you'd send
these emails, as written, under your own name. If not, tell me exactly what felt
wrong (too salesy, wrong facts, generic) and I'll tune the composer/generator.

**Note on emails:** most discovered businesses won't have a `contact_email` yet
(Google Places doesn't return one), so they'll stop at the site gate. That's
expected — see **B6**, which is the decision you make before Phase 7.

---

## Part B — Before any real send (start now; multi-week lead time) [LATER to use]

### B1. Buy secondary sending domains
**Why:** if a cold-email domain gets burned, it must not be the domain your real
business email runs on. Sacrificial domains protect your primary.
1. At a registrar (Cloudflare or Namecheap), buy **3–5** domains that look like
   your brand: `getbrandsites.com`, `brandwebstudio.com`, etc. ~$10/yr each.
2. Do **not** use your main brand domain.
3. Enable WHOIS privacy. Register while logged in as the hub Gmail (A2).

### B2. Google Workspace on the sending domains
**Why:** these mailboxes do the sending. Free Gmail cannot (it's against their
terms for bulk cold outreach and gets suspended).
1. Sign up at workspace.google.com — admin account = the hub Gmail.
2. Add each secondary domain (Admin console → Domains → Manage domains).
3. Create **2–3 mailboxes per domain** (e.g. `shreyas@`, `hello@`).
4. Budget: ~$7/user/month. **Cap: 10–20 emails per inbox per day, forever.**

### B3. DNS authentication + monitoring
**Why:** without SPF/DKIM/DMARC your mail goes straight to spam.
1. In your registrar's DNS for each sending domain, add the **SPF**, **DKIM**,
   and **DMARC** records Google Workspace gives you (Admin → Apps → Gmail →
   Authenticate email). Start DMARC at `p=none`.
2. Verify each domain at **postmaster.google.com** — this is where you'll watch
   spam rate and reputation once sending starts.
3. Check your work at mxtoolbox.com (SPF/DKIM/DMARC lookups).

### B4. Warm the inboxes — START ~4 WEEKS BEFORE YOU WANT TO SEND
**Why:** a brand-new domain that suddenly sends cold email gets filtered
immediately. Warmup builds a sending history.
1. Connect each mailbox to a warmup tool (Instantly/Smartlead include this).
2. Let it ramp automatically for **3–4 weeks**. Don't shortcut this.
3. **This is the long pole — start it before anything else in Part B.**

### B5. Decide the sending approach — **recommendation: managed (Instantly or Smartlead)**

Both options need the same Google Workspace mailboxes (B2). The question is only
whether you buy the sending layer or build it.

| | Managed (Instantly / Smartlead) | Raw Workspace + our own code |
|---|---|---|
| Mailboxes | Workspace, ~$7/mailbox/mo | same, ~$7/mailbox/mo |
| Sending layer | ~$37–94/mo | $0 |
| Warmup | **included** | separate tool, ~$30–50/mo |
| Inbox rotation | included | I build it |
| Reply capture | included | I build it (Phase 8) |
| Deliverability reporting | included | I build it |
| **Realistic monthly (6 mailboxes)** | **~$80–140** | **~$70–120** |
| Time to first send | days | weeks |

**Managed is both cheaper in practice and far better here**, because the "free"
column silently costs a warmup subscription anyway — and warmup is the one part
you cannot skip or hand-roll safely. It also removes the riskiest custom code
(rotation + throttling) from a system whose failure mode is a burned domain.

Take raw Workspace only if you later scale past a few hundred sends/day and want
the margin. The Phase-7 adapter is an interface either way, so switching later is
a contained change, not a rewrite.

### B6. Recipient-email sourcing — ☑ partly solved
The pipeline now **scrapes the business's own public contact email** from their
website during `advance` (preferring `info@`/`contact@`/`hello@`). Businesses
with no website, or no email published on it, will have no address and stop at
the site gate.

**Your decision:** for those, either (a) skip them, (b) look the address up by
hand and add it, or (c) pay an enrichment provider. Start with (a)+(b) — it's
free and higher quality. Note generic `info@` addresses bounce and complain more
than a real owner address.

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
