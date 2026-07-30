# MASTER PLAN — Local Web Outreach Platform

> **Working name:** `local-web-outreach` (rename freely).
> **What this is:** the single source of truth for what we build, in what order, and how we
> prove each piece works. Both the human operator and Claude reference this doc. Update the
> **Changelog** at the bottom on every meaningful change.
>
> **One-line product:** given a location, find local businesses with no/weak websites, research
> each to *high, sourced confidence*, generate a state-of-the-art site as a private proposal,
> and run a fully-audited, human-approved cold-outreach → reply → payment pipeline.

---

## 0. How to use this document

- Every **Phase** below is a shippable increment. Do them in order; each has a **Definition of
  Done (DoD)** and a **Tests** block. A phase is not "done" until its tests are green in CI.
- **Guard tests** (named `test_guard_*`) encode non-negotiable invariants (compliance, no
  hallucination, no send without approval). They must never be weakened to make a build pass —
  if one fails, the behavior is wrong, not the test.
- **AI-capability evals** (Phase 0) prove Claude *can* do each cognitive job to a measured bar
  **before** we build the factory around it. Re-run them whenever prompts or models change.
- Design principle inherited from the operator's trading bot: **the database is the state, the
  pipeline is a state machine, every side-effect passes a hard gate, and everything is an
  append-only audit event.**

---

## 1. Non-negotiable invariants (the whole system exists to protect these)

1. **No unverified fact ships.** Nothing appears on a generated site as fact unless it traces to
   a stored `research_claim` at/above the confidence threshold. No invented reviews, testimonials,
   awards, credentials, or stats — ever.
2. **No side-effect without a signed approval.** No email send, site publish, reply send, or
   payment request happens without an immutable, hashed `approval` row authorizing that exact
   content. The operator approves **every website and every email**.
3. **Everything is audited.** Every state transition and every outbound action writes an
   append-only `audit_event` linked to the approval that authorized it.
4. **Compliance is enforced in code, not by habit.** Every outbound email carries a physical
   postal address + working opt-out (CAN-SPAM). Suppression list is checked at compose *and* send.
   Canada/EU recipients are geo-gated out unless they opted in.
5. **Deliverability is protected by a kill switch.** Bounce > 2% or spam-complaint > 0.3% on a
   sending domain auto-pauses that domain, same discipline as a trading halt.
6. **Generated sites are private proposals** until purchased. They represent the real business,
   built for that business, and never impersonate a third party.

---

## 2. Tech stack (pinned decisions)

| Layer | Choice | Notes |
|---|---|---|
| Language | **Python 3.11+** | operator is Python-heavy; matches trading bot |
| API/backend | **FastAPI** | async, typed, easy webhooks |
| Datastore | **Postgres 15+** | concurrent writers (senders, pollers, webhooks, console) — *not* SQLite |
| Migrations | **Alembic** | every schema change is a migration + a migration test |
| Queue/workers | Postgres-backed job table + worker loop (graduate to **Temporal** only if needed) | keep it boring first |
| LLM | **Claude API** | Opus for research/generation, Haiku for classification |
| Email send | **Instantly** or **Smartlead** (send + rotation + warmup) OR raw Google Workspace + SMTP | adapter interface either way |
| Reply capture | **Gmail API / IMAP** | poll on schedule |
| Client sites | **Next.js** static, hosted on **Vercel**; per-client subdomain → custom domain on sale | operator designs frontend in Claude design |
| Review console | internal **Next.js** app → FastAPI backend | operator designs frontend in Claude design |
| Payments | **Stripe** (Checkout/Payment Links + Billing/Subscriptions + Invoicing + webhooks) | never store card data |
| Places data | **Outscraper / Apify** actor, or **Google Places API**; **OSM Overpass** fallback | licensed data over raw scraping |
| Site quality probe | **Google PageSpeed/Lighthouse API** | powers weakness list |
| Reporting | **Slack** + daily digest email | approvals, complaints, health |
| Tests | **pytest** (+ `pytest-asyncio`), **respx/vcrpy** for HTTP mocking | fast suite + slow-marked integration |
| Secrets | env + a secrets manager (1Password/Doppler/AWS SM); never in repo | detect-secrets pre-commit |
| CI | GitHub Actions | fast suite on every push; slow + evals nightly |

---

## 3. Repository structure (target)

```
local-web-outreach/
├── docs/
│   ├── MASTER_PLAN.md              ← this file
│   ├── COMPLIANCE.md               ← CAN-SPAM/CASL/ToS/data-retention checklist
│   └── PROMPTS/                    ← versioned prompt templates (research, site, email, reply)
├── app/
│   ├── core/                       state machine, audit, config, db session
│   ├── models/                     SQLAlchemy models
│   ├── stages/                     one module per pipeline stage (discover, qualify, ...)
│   ├── ai/                         Claude clients + prompt runners + output validators
│   ├── adapters/                   places, email_send, inbox, stripe, hosting, slack
│   ├── api/                        FastAPI routers (console, webhooks)
│   └── workers/                    scheduled jobs (poll replies, send queue, warmup, health)
├── evals/                          AI-capability eval harness + golden datasets
├── migrations/                     Alembic
├── tests/
│   ├── unit/                       fast
│   ├── guards/                     invariant guard tests (never weaken)
│   ├── integration/                slow-marked; mocked externals
│   └── fixtures/                   golden businesses, labeled replies, sample sites
├── Makefile                        make test / make evals / make diagnose
└── pyproject.toml
```

---

## 4. Data model (authoritative)

Core tables (Alembic-managed). Types abbreviated; PKs are `id uuid`.

```
businesses        (id, location, name, category, address, phone, gbp_url, existing_site_url,
                   has_site bool, status enum, opportunity_score, geo_country, created_at)
research_claims   (id, business_id, field, value, source_url, source_type, confidence float,
                   corroborations int, extracted_at, model_version)
site_weaknesses   (id, business_id, issue, severity enum, evidence, detected_at)
websites          (id, business_id, version int, content_json, preview_url, preview_token,
                   state enum[draft|approved|live|rejected], content_hash, created_at)
emails            (id, business_id, kind enum[outreach|reply], subject, body, footer,
                   status enum[draft|approved|queued|sent|bounced|failed], inbox_used,
                   suppression_checked bool, sent_at)
approvals         (id, subject_type enum[site|email|reply], subject_id, decision enum,
                   approver, notes, content_hash, decided_at)             -- APPEND-ONLY
threads           (id, business_id, external_thread_id, state enum, last_msg_at)
messages          (id, thread_id, direction enum[in|out], body, classification, confidence,
                   external_msg_id UNIQUE, received_at)
inquiries         (id, business_id, stage enum, next_action, owner, updated_at)   -- the CRM
payments          (id, business_id, stripe_object_id, kind enum[deposit|subscription|invoice],
                   status, amount_cents, currency, created_at)
complaints        (id, source_msg_id, business_id, category, severity, reported_at, resolution)
suppression_list  (id, email, domain, reason, added_at)                    -- never re-contact
sending_domains   (id, domain, workspace_acct, warmup_started_at, daily_cap, state enum,
                   bounce_rate, complaint_rate, paused_reason)
audit_events      (id, ts, actor enum[system|human|worker], action, subject_type, subject_id,
                   before_json, after_json, approval_id NULL, prev_hash, hash)  -- HASH-CHAINED
jobs              (id, kind, payload_json, run_after, attempts, state, locked_by, created_at)
```

**Audit hash chain:** `hash = sha256(prev_hash || canonical_json(event))`. Any tampering breaks
the chain. Guard test verifies chain integrity.

**Business status enum (the state machine):**
`DISCOVERED → QUALIFIED → RESEARCHED → SITE_DRAFTED → SITE_APPROVED → EMAIL_DRAFTED →
EMAIL_APPROVED → SENT → REPLIED → NEGOTIATING → WON | LOST | SUPPRESSED | DISQUALIFIED`

Allowed transitions are a hard-coded table in `core/state_machine.py`. Illegal transitions raise.

---

## 5. AI-capability validation FIRST (Phase 0) — "can Claude actually do this?"

This is the phase that answers your core worry. Before building the factory, we prove each
cognitive capability against a **golden dataset** and a **measured bar**. Each capability gets an
eval script in `evals/` and a threshold; the factory is not built on a capability that fails.

| # | Capability | Golden input | Pass bar | Guard against |
|---|---|---|---|---|
| **A** | **Research → sourced, confidence-scored dossier** | 10 hand-picked real businesses w/ known truth | ≥90% of emitted claims correct; **0 claims without a source_url**; low-data business yields *questions*, not fabricated facts | hallucination |
| **B** | **Site content generation** (structured `content_json`, grounded) | dossiers from A | 100% of factual fields map to a claim_id; industry template correct; passes schema validation | fabricated/ungrounded copy |
| **C** | **Outreach email drafting** | dossiers from A | human rater says "would send" ≥8/10; every draft references ≥1 true specific; footer/opt-out present | generic spam, deception |
| **D** | **Reply classification** | 50–100 labeled real replies | ≥95% accuracy on `unsubscribe`+`complaint` (safety-critical), ≥85% overall | mislabeling an unsubscribe/complaint |
| **E** | **Reply drafting** | labeled threads | human rater "would send" ≥8/10; never contradicts dossier; never re-engages a suppressed contact | off-brand / non-compliant replies |

**Phase 0 Tests / DoD**
- `evals/run.py --capability A..E` produces a scored report; thresholds encoded, CI-checkable nightly.
- `tests/guards/test_guard_no_claim_without_source.py` — model output with a claim lacking
  `source_url` is rejected by the output validator.
- `tests/guards/test_guard_low_data_no_fabrication.py` — feed a near-empty business; assert output
  contains zero high-confidence factual claims and routes gaps to `questions_for_owner`.
- `tests/unit/test_content_json_schema.py` — generator output validates against JSON schema.
- **DoD:** all five capabilities meet bar on the golden set; guard tests green. If any capability
  fails, document the gap and either revise prompts/model or descope that stage.

---

## 6. Build phases

Each phase: **Goal → Build → Interfaces → Tests → DoD.** Guard tests are called out explicitly.

### Phase 1 — Data & audit spine  — ✅ BUILT (2026-07-29)
- **Goal:** durable state + immutable audit + enforced state machine. Nothing else works without this.
- **Status:** implemented and tested — 34 tests green (unit + functional + performance), run against
  SQLite *and* a real PostgreSQL 14 server; ruff + mypy clean. See "Build log & findings" below.
- **Build:** Alembic schema for all tables in §4; `core/db.py` session mgmt; `core/audit.py`
  (append-only writer + hash chain); `core/state_machine.py` (transition table + `advance()`).
- **Tests:**
  - `test_migration_up_down.py` — migrate up then down cleanly on empty + populated DB.
  - `test_guard_audit_append_only.py` — UPDATE/DELETE on `audit_events`/`approvals` is rejected
    (DB trigger or app-layer) ; hash chain verifies.
  - `test_guard_illegal_transition_raises.py` — every non-allowed status transition raises.
  - `test_state_machine_happy_path.py` — full legal path DISCOVERED→WON.
- **DoD:** can create a business, advance it through legal states, and produce a verifiable audit trail.

### Phase 2 — Discovery & qualification  — ✅ BUILT (2026-07-29)
- **Goal:** location in → scored, geo-gated, deduped qualified leads out.
- **CORE RULE (Frisco finding):** site presence and quality are decided by **independently probing
  the live site**, never by trusting the source's "has website" field. The directory's signal is
  unreliable in both directions (a "Facebook-only" business may have a real site → not a lead; a
  listed URL may be dead → a lead). `has_site` is set from the probe result only.
- **Built:**
  - `adapters/places.py` — `PlacesSource` ABC + `BusinessCandidate`; `StubPlacesSource`
    (fixture-backed, deterministic) and `GooglePlacesSource` (httpx, real).
  - `adapters/site_fetch.py` — `SiteFetcher` protocol + `HttpSiteFetcher` (httpx, timed, follows
    redirects so http→https is observable); injected into the prober for testability.
  - `stages/discover.py` — geo-gate (US-only), dedup by `place_id` (batch + DB), persist as
    DISCOVERED, audit each creation.
  - `stages/qualify.py` — `SiteProber` (no_site / site_unreachable / no_https /
    not_mobile_responsive / stale_content / slow_load), `opportunity_score()` (0–10, severity-
    weighted), franchise/chain exclusion; advances DISCOVERED→QUALIFIED or →DISQUALIFIED via the
    spine, persisting `SiteWeakness` evidence rows.
  - Models: `Business` extended (place_id, address, phone, existing_site_url, has_site,
    opportunity_score); new `SiteWeakness`; migration `0002_discovery`.
- **Tests (30 added, 64 total):**
  - `test_places_adapter.py` — `GooglePlacesSource` + `HttpSiteFetcher` contract (respx-mocked).
  - `test_discover.py::test_guard_geo_gate_excludes_non_us` — non-US never persisted.
  - `test_discover.py` — batch + DB dedup by `place_id`, audited creation.
  - `test_qualify.py::test_guard_site_presence_probed_not_trusted` — **the Frisco rule as a guard.**
  - `test_qualify.py` — each weakness type, healthy-site→DISQUALIFIED, franchise→DISQUALIFIED,
    monotonic scoring, audit chain intact.
  - `test_discovery_flow.py` — full Frisco batch end-to-end (SQLite + Postgres).
  - `test_migration_0002.py` — up/down (SQLite + Postgres) + migration-built schema accepts ORM
    writes and enforces the severity CHECK.
  - `test_qualify_perf.py` — throughput guardrail (~500 businesses/s).
- **Deferred (noted):** the "source hid a real site" direction needs a search-enrichment step (find
  the true URL when the directory gives none) — the probe covers the reachability direction now.
  PageSpeed/Lighthouse for real load metrics and broken-link crawling are future enrichments; the
  current prober uses cheap, deterministic HTML/HTTP signals.
- **FINDING — qualification must be deterministic (from a live run).** A live `make demo` flipped
  The Depot Cafe QUALIFIED↔DISQUALIFIED between runs: `slow_load` (LOW) fired only when the site's
  fetch happened to exceed 4s, and the original rule treated *any* weakness as a lead. **Fix:** only
  MEDIUM/HIGH structural weaknesses (no-site, unreachable, no-HTTPS, not-mobile, stale) qualify a
  site as a lead; a lone LOW signal like `slow_load` is recorded as evidence but is too noisy (a
  single fetch over a variable network) to flip the verdict. Locked by
  `test_qualify_low_only_weakness_is_not_a_lead`. Robust load timing (multi-sample / PageSpeed) is
  the eventual home for a *reliable* slow-site signal.
- **DoD:** ✅ a location produces a ranked, US-only, deduped qualified list with concrete, evidenced
  weakness lists, fully audited.

### Phase 3 — Research (confidence-gated)  — ✅ BUILT (2026-07-29)
- **Status:** implemented + tested (83 tests total, SQLite + PostgreSQL, ruff/mypy clean). The
  Claude extraction path is unit-tested with a mocked client; its **live** behavior needs an
  `ANTHROPIC_API_KEY` to fully exercise (see Build log). A **no-key `research-demo`** runs the full
  corroboration/conflict/entity-resolution pipeline on bundled, hand-verified Frisco data and a
  **capability-A eval** scores it against known truth (5/5, bar 100%).
- **Goal:** per business, a dossier of atomic, sourced, confidence-scored claims. Enforces invariant #1.
- **PREREQUISITE — entity resolution (finding from the M0 demo):** aggregators routinely
  split/merge local businesses (the Galena landscaper surfaced as "Kane's Landscaping" vs "Dan
  Kane Landscaping & Lawn Service" vs "Kane's Landscaping and Property Maintenance" (USDOT
  4390691) vs "Kane Lawn and Garden" — 1–4 possibly-distinct entities). If we research a wrongly
  merged entity, **every downstream claim is poisoned.** So an explicit disambiguation step must
  run *before* claim extraction, resolving the target to a single canonical entity (place_id +
  address + phone triangulation) and refusing to merge sources it cannot confidently tie together.
- **Build:** `stages/entity_resolution.py` (canonicalize the target first); `stages/research.py`;
  source collectors (GBP, Yelp, Facebook, existing-site scrape, local news); `ai/research_runner.py`
  (Claude Opus, sources in-context); corroboration engine (≥2 independent sources → high
  confidence); conflict detection (disagreeing sources → 🔴 unverified, routed to owner — e.g. the
  New Earth Animals demo produced two different phone numbers); `ai/validators.py` rejects any
  claim missing `source_url`.
- **Tests:**
  - `test_guard_no_claim_without_source.py` (shared with Phase 0).
  - `test_guard_entity_disambiguation.py` — sources that can't be confidently tied to one entity
    are NOT merged into a single dossier.
  - `test_corroboration_requires_two_sources.py` — single-source claim stays below high-confidence.
  - `test_conflict_flagged_not_guessed.py` — two disagreeing values for a field → `unverified`,
    never silently one-of-them.
  - `test_confidence_threshold_enforced.py` — sub-threshold claims marked `unverified`.
  - `evals/A` golden dossier eval ≥ bar.
- **DoD:** dossiers meet the eval bar; entity is canonicalized first; no unsourced/fabricated/
  conflicting claim can persist as fact.

### Phase 4 — Website generation  — ✅ BUILT (2026-07-29)
- **Status:** implemented + tested (113 tests total, SQLite + PostgreSQL, ruff/mypy clean). The
  content model is **deterministic and fully grounded** — it uses only VERIFIED claims, every fact
  carries its `claim_id`, unverified fields are omitted (surfaced as "needs confirmation"), and
  social-proof sections are never fabricated. `app/stages/generate.py`, `Website` model, migration
  `0004`. No-key demo: `python -m app.cli site-demo`. **Capability-B eval: 8/8** (grounding, template,
  no fabrication, unverified-not-rendered — `python -m evals.site_eval`). LLM copy-polish is a later
  optional enhancement that must preserve claim_ids and pass the same validator.
- **Deferred within Phase 4:** the actual publish-to-host adapter (deploying the rendered site to a
  preview host) is coupled to the Claude-designed **renderer** + conversion — it can't be built
  before the renderer exists, so the DRAFT stores a tokenized `preview_url`/`noindex` now and real
  publishing lands with the renderer (frontend) and Phase 10/11 (conversion).
- (original plan follows)
- **Goal:** grounded, industry-aware `content_json` → rendered private preview; full fact traceability.
- **Build:** `ai/site_generator.py` (content model only, every fact carries `claim_id`);
  industry template selector; Next.js renderer; `adapters/hosting.py` publishes to
  `preview-{token}.host` (tokenized, noindex, not guessable).
- **Tests:**
  - `test_guard_every_fact_traces_to_claim.py` — every factual field in `content_json` has a valid `claim_id`.
  - `test_guard_no_fabricated_reviews.py` — generator output containing a review/testimonial not
    backed by a claim is rejected.
  - `test_guard_preview_is_private.py` — preview URL requires token; `noindex`; not enumerable.
  - `test_industry_template_selection.py` — category → correct template/section set.
  - `evals/B` ≥ bar.
- **DoD:** a business yields a good, fully-traceable private preview; unverified facts cannot render.

### Phase 5 — Approval console + GATE 1 (site)  — ✅ BACKEND BUILT (2026-07-29)
- **Status:** FastAPI backend implemented + tested (125 tests total, incl. 11 TestClient tests;
  live uvicorn HTTP smoke passed). `app/api/` — read endpoints (`/api/pipeline`, `/api/review-queue`,
  `/api/review/{id}`, `/api/businesses/{id}`, `/api/approvals`) + the Gate-1 write endpoint
  (`POST /api/businesses/{id}/site-decision`). Field names mirror the console's `api.js` contract, so
  the frontend swaps that one file to go live. `make api` runs it. The **console UI itself is the
  Claude-designed artifact** (validated separately) — this phase is its backend.
- **Gate-1 guarantees enforced here:** the decision endpoint binds a hashed `approval` to the exact
  reviewed draft (`expected_content_hash` must match the current `websites.content_hash`, else 409
  Stale — "you approved *this* version"); approve advances SITE_DRAFTED→SITE_APPROVED via the spine
  (hashed approval required by the gate), reject → DISQUALIFIED, request_changes → no state change
  (re-draft). Illegal-state decisions → 409; missing business → 404.
- **Deferred to Phase 6:** the email gate (`/email-decision`) — needs the Email model. Auth is a
  single-operator no-auth localhost dev setup (CORS `*`); real auth + tightened CORS before deploy.
- **Goal:** operator approves every site with full context; state cannot advance without a signed approval.
- **Build:** `api/console.py` — `GET /review/site/{id}` returns side-by-side payload:
  **company brief**, **existing-site weakness list** (or "no site today"), **new-site feature
  bullets**, **live preview URL**, **confidence flags** (unverified items highlighted).
  `POST /review/site/{id}` = approve/edit/reject/request-changes → writes hashed `approval`.
- **Tests:**
  - `test_guard_no_advance_without_approval.py` — `SITE_DRAFTED → SITE_APPROVED` requires an approval row.
  - `test_approval_hash_matches_content.py` — approval hash == hash of the exact reviewed `content_json`.
  - `test_edit_creates_new_version.py` — editing bumps `websites.version`, old version retained.
  - `test_reject_halts_pipeline.py` — reject → business does not advance to email.
  - `test_review_payload_shape.py` — payload includes all five side-by-side elements.
- **DoD:** operator can approve/edit/reject a site; approvals are immutable and content-bound.

### Phase 6 — Email composition + GATE 2 (email)
- **Goal:** compliant, personalized outreach email; operator approves every one; enforces invariants #2, #4.
- **Build:** `ai/email_composer.py` (personalized from dossier, one CTA = preview link);
  `core/compliance.py` footer injector (physical postal address + one-click opt-out); suppression
  check at compose. `GET/POST /review/email/{id}` mirrors Phase 5 side-by-side (email + brief + approved site).
- **Tests:**
  - `test_guard_email_has_physical_address_and_optout.py` — CAN-SPAM footer present on every draft.
  - `test_guard_suppressed_recipient_blocked_at_compose.py` — suppressed email cannot produce a draft.
  - `test_guard_no_send_without_email_approval.py` — `EMAIL_DRAFTED → EMAIL_APPROVED` needs approval row.
  - `test_subject_not_deceptive.py` — subject reflects body (heuristic/LLM check).
  - `evals/C` ≥ bar.
- **DoD:** every outreach email is compliant, personalized, and approval-gated.

### Phase 7 — Send infrastructure & deliverability kill switch
- **Goal:** deliver approved emails safely; protect domain reputation automatically.
- **Build:** `adapters/email_send.py` (Instantly/Smartlead or SMTP); inbox rotation;
  per-inbox daily cap (**10–20/day**); warmup tracking (3–4 weeks before live);
  `workers/deliverability.py` monitors bounce/complaint per domain and **auto-pauses** on
  bounce > 2% or complaint > 0.3%; SPF/DKIM/DMARC verified via config check.
- **Tests:**
  - `test_guard_rate_limit_enforced.py` — >cap sends/inbox/day are queued, not sent.
  - `test_guard_autopause_on_bounce_or_complaint.py` — thresholds trip → domain `paused`.
  - `test_guard_suppression_and_geo_at_send.py` — final send re-checks suppression + geo.
  - `test_rotation_distributes.py` — sends spread across inboxes.
  - `test_warmup_gate.py` — domain younger than warmup window can't send live campaigns.
- **DoD:** approved emails go out within safe limits; a degrading domain pauses itself.

### Phase 8 — Reply monitoring & classification
- **Goal:** capture replies, classify, auto-handle unsubscribes/complaints. Enforces invariant #4.
- **Build:** `workers/poll_replies.py` (Gmail API/IMAP, dedup by `external_msg_id`);
  `ai/classifier.py` (Haiku → `interested|question|not-interested|unsubscribe|complaint|auto-reply|OOO`,
  confidence-thresholded; low-confidence → human); thread state; unsubscribe → suppression immediately.
- **Tests:**
  - `test_guard_unsubscribe_added_to_suppression.py` — classified unsubscribe → suppression in same run.
  - `test_guard_complaint_routed.py` — complaint → `complaints` row + Phase 11 report.
  - `test_dedup_polled_messages.py` — same external message polled twice inserts once.
  - `evals/D` ≥ bar (esp. ≥95% on unsubscribe/complaint).
- **DoD:** replies are captured, classified, and safety categories auto-handled reliably.

### Phase 9 — Reply drafting & HITL response gate
- **Goal:** human-like, on-brand replies; **human-approved initially**; enforces invariant #2.
- **Build:** `ai/reply_drafter.py` (grounded in thread + dossier); `POST /review/reply/{id}` gate;
  config flag to later auto-send only safe categories (OOO/simple scheduling).
- **Tests:**
  - `test_guard_reply_requires_approval.py` — no outbound reply without approval (initial mode).
  - `test_guard_no_reply_after_unsubscribe.py` — suppressed/unsubscribed thread cannot be replied to.
  - `test_reply_thread_continuity.py` — reply attaches to correct thread, preserves history.
  - `evals/E` ≥ bar.
- **DoD:** operator approves replies; drafts are contextual and never violate suppression.

### Phase 10 — Payments (Stripe)
- **Goal:** collect deposit + monthly hosting on a "yes"; provision on paid. Enforces "no card data."
- **Build:** `adapters/stripe.py` — Payment Link/Checkout for **deposit**, **Subscription** for
  hosting/maintenance, **Invoicing** for one-offs; `api/webhooks.py` (signature-verified,
  idempotent); on `paid` → provision (preview → live, attach custom domain), advance to WON.
- **Tests:**
  - `test_guard_webhook_signature_verified.py` — unsigned/forged webhook rejected.
  - `test_guard_webhook_idempotent.py` — duplicate event id processed once.
  - `test_paid_triggers_provisioning.py` — `paid` → site live + status WON + audit event.
  - `test_guard_no_card_data_stored.py` — no PAN/CVC fields anywhere in models/logs.
  - `test_failed_payment_handling.py` — failed/refunded → correct status, no provisioning.
- **DoD:** client pays on Stripe-hosted pages; success provisions the live site; all audited.

### Phase 11 — Complaint pickup & reporting
- **Goal:** detect complaints in the operator's inbox, report to operator, never auto-act. Enforces invariant #3.
- **Build:** `workers/complaint_watch.py` parses the operator's inbox (live-site issues, billing,
  outreach complaints); classify + link to business; report via Slack + daily digest.
- **Tests:**
  - `test_guard_complaint_never_autoacts.py` — a complaint only creates a report, no outbound action.
  - `test_complaint_linked_to_business.py` — matched to correct business when identifiable.
  - `test_complaint_dedup.py` — same complaint thread reported once.
- **DoD:** any complaint surfaces to the operator promptly with context and a suggested action.

### Phase 12 — Observability, health gate, ops
- **Goal:** know the system is healthy; recover from failure; mirror the trading bot's run-health discipline.
- **Build:** `workers/health.py` → `run_health.json` (GREEN/YELLOW/RED, allow-list gate);
  daily digest (sent, replies, approvals pending, domains paused, payments); dead-man's switch
  (healthchecks.io); nightly DB backup + **restore test**.
- **Tests:**
  - `test_health_gate_allow_list.py` — only GREEN/YELLOW pass; RED blocks/alerts.
  - `test_backup_restore.py` — backup restores to a working DB.
  - `test_digest_contents.py` — digest includes required sections.
- **DoD:** operator gets a daily digest, alerts on failure, and a proven backup/restore.

---

## 7. Cross-cutting requirements

### 7.1 Security & secrets
- No secret in repo; detect-secrets pre-commit; secrets via manager/env only.
- Stripe webhook signature verification mandatory (Phase 10).
- Preview URLs tokenized + `noindex`; console behind auth.
- PII minimization: store only business-contact data needed for outreach; documented retention.

### 7.2 Legal / compliance (see `docs/COMPLIANCE.md`)
- **CAN-SPAM:** physical postal address + working opt-out on every email; honor opt-out
  (we do it instantly); non-deceptive subject/from. *Physical address requirement means the
  operator needs a real mailing address / PO box / registered agent.*
- **CASL (Canada):** express consent required → geo-gate CA out (Phase 2 & 7 guards).
- **GDPR/EU:** geo-gate EU out initially; revisit before EU expansion.
- **Scraping ToS:** prefer licensed providers (Outscraper/Apify) / official APIs over raw scraping.
- **No fabrication / no impersonation:** invariants #1 and #6, enforced by Phase 3–4 guards.
- **Data retention & deletion:** suppression is permanent; define retention for non-converted leads.

### 7.3 AI safety guardrails
- Output validators reject unsourced claims and fabricated social proof (Phase 3–4).
- Confidence thresholds are config, changes are audited.
- Human gates on all external comms; auto-send only for explicitly-whitelisted safe categories.
- Prompts are versioned in `docs/PROMPTS/`; model + prompt version stamped on every AI output row.

### 7.4 Testing strategy
- `make test` = fast unit + guard suite (every push).
- `make evals` = capability evals against golden set (nightly + on prompt/model change).
- Integration tests slow-marked, mock all externals (respx/vcrpy); no live sends in CI.
- **Guard tests are load-bearing** — a failing guard means stop and fix behavior.

---

## 8. Milestones (sequencing — don't build all 12 at once)

- **M0 — Validate (Phase 0):** prove Claude can do A–E on 10 real businesses. *Gate: bar met.*
- **M1 — Manual single-business loop (Phases 1–6):** one business, manual trigger, one warmed
  inbox, both approval gates working. *Gate: operator sends one approved email about one approved site.*
- **M2 — Replies + responses (Phases 8–9).**
- **M3 — Payments (Phase 10).**
- **M4 — Complaints + ops (Phases 11–12).**
- **M5 — Scale send infra (Phase 7 full):** multi-domain rotation + warmup automation. *Last — worthless before quality is proven.*

---

## 9. Open decisions / TODO (resolve as we go)
- [ ] Places provider: Outscraper vs Apify vs Places API (cost + ToS trade-off).
- [ ] Send layer: managed (Instantly/Smartlead) vs raw Workspace SMTP.
- [ ] Pricing model: deposit + monthly hosting amounts; free-preview vs paid-preview.
- [ ] Physical mailing address for CAN-SPAM footer.
- [ ] Where the review console is hosted; auth method.
- [ ] Model/version pins for Opus vs Haiku per stage; cost budget per business.

---

## Build log & findings

### M0 capability demo (research, Galena IL)
- **Capability A passes and fails safe.** On two real businesses, claims traced to sources,
  corroboration drove confidence, conflicts were flagged (New Earth Animals: two different phone
  numbers → 🔴, not guessed), and gaps became owner-questions (unknown owner name → not fabricated).
- **New finding → entity resolution** is now a hard Phase 3 prerequisite (see Phase 3). Aggregators
  conflate/split local businesses; researching the wrong merged entity poisons everything downstream.

### Phase 1 build (data & audit spine)
Decisions and findings baked into the code:
- **Tests default to SQLite, invariants enforced in the app layer** (portable, zero-dependency),
  **plus PostgreSQL trigger hardening** (`lwo_prevent_mutation` BEFORE UPDATE/DELETE on
  `audit_events`/`approvals`) as defense-in-depth. Both layers are tested; the PG-trigger tests run
  against a real server and self-skip when none is reachable.
- **Hash-chain design:** each `audit_events` row stores `seq` (total order), `prev_hash`, and
  `hash = sha256(canonical_json(payload))`. `seq`/`prev_hash` are assigned under a per-chain lock —
  a Postgres transaction-scoped advisory lock (`pg_advisory_xact_lock`); a no-op on SQLite (writes
  already serialized). `verify_chain()` recomputes the whole chain and returns the first bad `seq`.
  The canonical `ts` is stored as an explicit ISO-8601 string so the hash is stable across dialects
  (avoids SQLite's naive-vs-aware datetime round-trip changing the hash).
- **FINDING — enum name-vs-value storage bug (fixed).** SQLAlchemy's `Enum` persists the member
  **name** by default, and SQLAlchemy 2.0 defaults `create_constraint=False`. So `SubjectType.SITE`
  was being stored as `"SITE"` (not `"site"`), inconsistent with the audit payload's `"site"` and
  with the migration's declared domain — and **no CHECK constraint was actually created.** The other
  functional tests missed it because they build the schema with `create_all`, not the migration.
  **Fix:** `values_callable=enum_values` forces value-based storage, `create_constraint=True` emits
  the CHECK, and a new regression test (`test_schema_enum_storage.py`) builds the schema **via the
  migration** and inserts through the ORM, asserting stored values are the lowercase `.value` and
  that an out-of-domain value is rejected. *Lesson for later phases: at least one functional test per
  schema must exercise the migration-built schema, not just `create_all`.*
- **Append-only reject reads clean:** the app-layer guard is a `Session before_flush` listener that
  matches by table name (`audit_events`, `approvals`) so it needs no model import (no import cycle).
- **Performance (SQLite, single writer):** ~1,000 audit appends/s, chain-verify of 2,000 events in
  ~0.12s, ~700 state transitions/s — comfortably above the daily-batch workload. Guardrail tests
  assert conservative floors and print measured rates.
- **Deferred to a later phase (noted, not yet built):** true multi-writer concurrency test for the
  advisory lock; the remaining tables from §4 (websites, emails, threads, payments, etc.) — Phase 1
  implements only Business + AuditEvent + Approval, the minimum to make the spine real. Approvals
  currently bind `subject_id` to the business id; when Website/Email tables land they should bind to
  those rows instead.

### Phase 3 build (research)
- **AI boundary is injectable.** `app/ai/research_runner.py` defines `ClaimExtractor`;
  `ClaudeClaimExtractor` (Claude, `claude-opus-5`) takes an injectable `client`, so tests use a
  fake (no network, no key) and the live path reads `ANTHROPIC_API_KEY`. The extractor **stamps
  `source_url` from the owning source** — the model never supplies provenance, so a claim can't
  lack one; `app/ai/validators.py` enforces it as a hard guard regardless.
- **Corroboration engine** (`app/stages/research.py`): group by field → group by normalized value →
  ≥2 distinct `source_url`s = VERIFIED (conf ≥0.85), 1 = UNVERIFIED (0.5), disagreeing values =
  CONFLICT (value carries both candidates, conf 0.3, never ships). Required fields without a
  VERIFIED claim become owner questions — gaps surfaced, never fabricated.
- **Entity resolution first** (`app/stages/entity_resolution.py`): conservative triangulation —
  a source is kept only on a phone/address match or high name-similarity with no conflicting phone;
  a disagreeing phone is a hard reject. Guards against the Kane's/Amigos merge trap.
- **HONEST LIMIT:** the live Claude extraction and real source collectors (GBP/Yelp/etc. fetching)
  are **not** exercised end-to-end here — no key in this environment, and web collectors are
  deferred (ToS + scope). What's proven: the deterministic core (resolution/corroboration/conflict/
  validators/persistence) on real data, and the extractor's prompt-build + parse logic under mock.
  The `research-demo` bundles the *actual* Frisco research (the extraction a human/Claude did in
  M0) so the pipeline runs and is eval-scored with no key. Live wiring = drop in `ANTHROPIC_API_KEY`
  + a real `SourceCollector`.
- **Verified live:** `python -m app.cli research-demo` → Depot Cafe address+phone VERIFIED (2
  sources), single-source facts UNVERIFIED, owner→question, J.S.M. Lawn Care rejected by entity
  resolution. `python -m evals.research_eval` → 5/5.

## Changelog
- **2026-07-29** — Initial master plan created (architecture, phases 0–12, tests, invariants).
- **2026-07-29** — M0 research demo run (Galena IL); added entity-resolution prerequisite to Phase 3.
- **2026-07-29** — Phase 1 built and tested (34 tests, SQLite + PostgreSQL, ruff/mypy clean);
  recorded the enum name-vs-value finding and the migration-schema test lesson.
- **2026-07-29** — M0 research demo run for Frisco TX; confirmed that in affluent markets
  qualification (not research) is the filter, and that aggregator "no website" signals are
  unreliable — folded into Phase 2 as the "verify, don't trust" core rule + guard.
- **2026-07-29** — Phase 2 (discovery & qualification) built and tested (64 tests total, SQLite +
  PostgreSQL, ruff/mypy clean); site presence is probe-determined; weaknesses persisted as evidence.
- **2026-07-29** — Phase 3 (research, confidence-gated) built and tested (83 tests total, SQLite +
  PostgreSQL, ruff/mypy clean). Entity resolution + corroboration/conflict/confidence + injectable
  Claude extractor + capability-A eval (5/5). Live LLM extraction + real collectors deferred to
  live wiring (needs `ANTHROPIC_API_KEY`); documented honestly in the build log.
- **2026-07-29** — Qualification hardened: deterministic across network latency (only MEDIUM/HIGH
  weaknesses qualify a lead), plain-English WHY on every decision (audit-backed), 31 qualify tests.
- **2026-07-29** — Phase 4 (website generation) built and tested (113 tests total, SQLite +
  PostgreSQL, ruff/mypy clean). Grounded content model (every fact → VERIFIED claim_id), no
  fabricated social proof, private DRAFT preview; advances to SITE_DRAFTED. Ready for a
  Claude-designed frontend (renderer + operator console).
- **2026-07-29** — Operator Console frontend built via Claude design (self-contained artifact);
  validated (renders, keyboard approve + auto-advance, content-hash confirm, status colors, grounding
  visualized, light/dark). Wired through a single `api.js` seam.
- **2026-07-29** — Phase 5 backend (Operator Console API) built and tested (125 tests total, incl. 11
  API TestClient tests + a live uvicorn HTTP smoke; ruff/mypy clean). Read endpoints + Gate-1
  site-decision with stale-content-hash guard; matches the `api.js` contract. Email gate deferred to
  Phase 6.
