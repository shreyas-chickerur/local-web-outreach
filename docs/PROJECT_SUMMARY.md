# local-web-outreach — full project summary

> **Accuracy note for résumé use.** Everything in §1–§9 is **built, tested, and running**.
> §10 lists what is **designed and specified but not yet implemented** — do not
> claim those as delivered. Verified metrics are in §8.

---

## 1. One-line description

A human-in-the-loop sales automation platform that finds local businesses with weak
or missing websites, researches each one to a sourced and corroborated confidence
standard, generates a complete replacement website as a private proposal, drafts a
compliant cold-outreach email, and requires explicit human approval — recorded on a
tamper-evident audit ledger — before anything reaches a real business.

## 2. The problem

Local-business web development is a real market, but cold outreach at scale has three
failure modes that make it either ineffective or actively harmful:

1. **Fabrication.** Automated personalization invents facts ("I loved your 2019
   remodel"). Sending a real business a false claim about itself destroys credibility
   instantly and is the fastest way to be marked as spam.
2. **No proof of value.** "I can build you a website" is worthless; "here is the
   website, already built, look at it" is not. But building a real site per lead is
   expensive.
3. **Legal and reputational risk.** US commercial email is regulated (CAN-SPAM):
   physical address required, functioning opt-out required, no deceptive subject
   lines. Deliverability collapses if bounce/complaint rates drift.

The platform's thesis: **automate everything except the judgment**, and make it
structurally impossible to send something false or non-compliant.

## 3. Architecture

Five design invariants, each enforced in code rather than convention:

| # | Invariant | Enforcement |
|---|---|---|
| 1 | No unverified fact ships | Claims need ≥2 **independent** sources to reach VERIFIED; the site generator renders only VERIFIED claims and raises `SiteIntegrityError` on any fact without a backing claim id |
| 2 | No side-effect without a signed approval | State machine refuses gated transitions unless a matching hashed `Approval` row exists |
| 3 | Everything is audited | Append-only, hash-chained event ledger; application guard + PostgreSQL triggers |
| 4 | Compliance enforced in code | CAN-SPAM footer, subject validation, suppression list, and a hard guard blocking sends while the sender address is a placeholder |
| 5 | Generated sites are private proposals | Unguessable token URLs, `noindex` meta + `X-Robots-Tag`, visible draft marker |

**The pipeline is a state machine.** A business moves
`DISCOVERED → QUALIFIED → RESEARCHED → SITE_DRAFTED → SITE_APPROVED → EMAIL_DRAFTED
→ EMAIL_APPROVED → SENT → REPLIED → …`, with terminal states `DISQUALIFIED`,
`SUPPRESSED`, `WON`, `LOST`. Illegal transitions raise. Two transitions are **gated**
and require a human approval bound by content hash.

**The database is the state** (8 tables): `businesses`, `research_claims`,
`site_weaknesses`, `websites`, `emails`, `approvals`, `audit_events`,
`suppression_list`. SQLAlchemy 2.0 with Alembic migrations; SQLite for dev/test,
PostgreSQL for production, tested against both.

## 4. Subsystems built

### 4.1 Discovery & qualification
- Google Places adapter with **Place Details enrichment**. Text Search alone returns
  neither website nor phone — a defect that made *every* business look like it had no
  website (see §7.1).
- Geo-gate (US-only, because CAN-SPAM is permissive while CASL/GDPR require consent).
- **Identity-based deduplication** — normalized name + address, stripping punctuation,
  casing, and legal suffixes, because Google returns the same business under multiple
  `place_id`s.
- Qualification **independently probes the live site** rather than trusting the
  directory: HTTPS, mobile viewport, copyright staleness, load time, reachability. Each
  weakness is stored with plain-language evidence explaining the cost to the owner.
- Only MEDIUM/HIGH weaknesses qualify a lead (a LOW-only finding is recorded but is not
  a selling reason).

### 4.2 Research & corroboration
- Multi-source collection: Google Business Profile, **OpenStreetMap/Nominatim** (free,
  keyless, rate-limited per their usage policy), **Yelp Fusion**, and the business's own
  website.
- **Entity resolution** before merging — a directory returns its best guess, which may be
  a different business entirely; look-alikes are refused and reported.
- **Corroboration engine**: ≥2 independent sources → VERIFIED; 1 → UNVERIFIED;
  disagreement → CONFLICT (never shipped as fact). Unverified required fields become
  explicit owner questions rather than guesses.
- **Field-aware comparison** — the subtle part (§7.2): addresses fold country suffixes,
  punctuation, street abbreviations and street-type words; phones compare as digits;
  ratings agree within a tolerance rather than exact match.
- Injectable `ClaimExtractor` — a Claude-backed extractor for production, a deterministic
  one for tests, so the entire suite runs with no API key and no network.
- Hard guard: no claim persists without a `source_url`.

### 4.3 Content extraction from the incumbent site
- Dependency-free parsing (regex over untrusted third-party HTML) for description, about
  copy, services, hours, photos, socials, and customer actions.
- **Menu/price-list extraction** anchored on price, since a price is the one unambiguous
  signal a line is an item for sale rather than prose or navigation. Handles the common
  case where a restaurant publishes its menu as a PDF or photo.
- **Contact-page crawling** for the owner's email — homepages rarely carry one. This took
  email discovery from 0 of 21 leads to 9 of 21.
- Guards learned from real data: award/press text is filtered out of offerings (social
  proof, not an offering); logos, icons and award badges are excluded from photography;
  registrar/parking links are not customer actions.

### 4.4 Website generation & rendering
- Industry-aware content model (restaurant / service / generic) assembled from VERIFIED
  claims plus the business's **self-attested** content, with explicit provenance.
- **The provenance distinction is the interesting design call**: a third-party claim
  needs corroboration, but content the business published about *itself* is
  self-attested — carrying it across is not fabrication. Sections carrying it must
  declare provenance or the integrity validator rejects them.
- Renderer produces a complete, self-contained responsive page — inline CSS/JS, system
  fonts, zero external requests — served at a tokenized `/preview/{token}` URL.
- **Actions are internalized**: a "Menu" button becomes an in-page anchor when we carry
  the menu and is dropped when we don't; links back to the business's current website are
  removed entirely, since a proposal that links to the site it replaces is a brochure for
  the incumbent. Genuine third-party flows (OpenTable, DoorDash) survive.
- Forbidden sections (reviews, testimonials, awards) raise on generation.

### 4.5 Outreach composition & compliance
- Deterministic template composer plus an injectable Claude composer.
- Copy **leads with the offer and never criticizes the recipient's current site** — a
  regression test runs every weakness combination against a list of critical wording.
- The weakness controls exactly one thing: whether it is truthful to say we looked at
  their site.
- CAN-SPAM: postal address + one-step opt-out in every footer, subject validation
  (rejects empty, shouting, `Re:` thread-faking, excessive punctuation), suppression list
  by address or whole domain, and `assert_real_sender_address` — sending is impossible
  while the configured address is a placeholder.

### 4.6 Operator console (human gates)
- FastAPI backend + a browser console served same-origin.
- Review queue serves both gates with the side-by-side context: research dossier with
  clickable sources and confidence, the generated site, the drafted email.
- **Content-hash binding** — an approval is bound to the exact bytes reviewed. If the
  draft changed since it was rendered, the decision is rejected with 409. Editing a draft
  re-hashes it, which deliberately invalidates any staged approval.
- Four actions: approve, reject, request changes, edit. Editing appends an audit event
  but never changes status and never records an approval.
- An edit cannot remove the compliance footer (re-attached) or set a deceptive subject
  (400).

### 4.7 Adversarial re-validation
A separate `validate` stage that re-checks drafted leads against **live** sources rather
than trusting collection-time corroboration:
- Is every stored fact still true?
- **Is the pitch still true?** A "no HTTPS" pitch fails the moment they add HTTPS; a
  "site is down" pitch fails once it comes back up. Sending a stale pitch is the
  embarrassing case.
- Distinguishes *wrong* (FAIL) from *unconfirmable* (WARN) — inability to re-check is not
  disproof.
- Requires an entity-name match before comparing, so a directory's wrong-business result
  can never be counted as evidence against our data.

### 4.8 Audit ledger
- Append-only, hash-chained: each event carries the previous event's hash; `verify_chain`
  detects any tampering or gap.
- Defense in depth: application-layer guard plus PostgreSQL triggers blocking UPDATE and
  DELETE.
- Concurrency-safe under Postgres advisory locks — proven with a test driving 8 threads ×
  25 appends and asserting gapless sequence numbers and an intact chain.

## 5. Engineering practices

- **323 tests**, 85% coverage, split unit / functional / performance, all passing.
- Tests never touch the network: adapters are protocols with injected fakes; HTTP is
  mocked at the transport layer.
- Dual-backend testing — the same suite runs on SQLite and PostgreSQL, with Postgres
  tests self-skipping when no server is present.
- **Capability evaluations** beyond unit tests: research accuracy vs. hand-verified
  ground truth with a zero-fabrication check; site-grounding; email compliance.
- `ruff`, `mypy` (strict, clean across 51 modules), `bandit`, `detect-secrets`.
- Secrets hygiene: `.env` gitignored and never committed, plus a pre-commit hook that
  blocks committing any `.env` or database file — tested against a forced `git add -f`.
- Alembic migrations designed to run against populated legacy databases.

## 6. Technology

Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL / SQLite · Pydantic ·
httpx · pytest (+cov, respx) · ruff · mypy · Anthropic Claude API · Google Places API ·
Yelp Fusion API · OpenStreetMap Nominatim · vanilla HTML/CSS/JS front end.

## 7. Notable problems solved

These are the strongest interview material — each was found by testing against real data,
not by reading code.

### 7.1 A silent API defect that would have sent 19 false claims
Google Places Text Search returns neither `website` nor `formatted_phone_number`; both
require a separate Place Details call. The adapter read them off the search result, so
they were always null. Consequence: **every** discovered business appeared to have no
website, all 19 leads "qualified," and the outreach email would have told each one *"I
noticed you don't have a website yet"* — while 17 of them had working sites. Fixing it
flipped the result: 17/19 had a site and phone, 13 correctly disqualified as healthy, 4
qualified on genuine evidenced weaknesses.

### 7.2 False conflicts from formatting, and a bucketing bug I introduced
Google writes `9500 Frisco St, Frisco, TX 75033`; Yelp appends `, USA`. Compared raw,
identical addresses became CONFLICTs — burying facts both sources agreed on. Worse, one
source often omits the street type (`Preston On The Lake Blvd` vs `Preston On The Lake`).
For ratings I first bucketed to the nearest half-star, which reported Google 4.7 vs Yelp
5.0 as a conflict purely because 4.7 falls below 4.75 — an artifact of an arbitrary
boundary. Replaced with a tolerance. Net effect on live data: verified claims up, false
conflicts down, with genuinely different addresses still conflicting correctly.

### 7.3 A validator that manufactured its own false positives
The re-validation stage flagged two roofers as having wrong phone numbers — both showing
the *same* live number, because Yelp had returned one unrelated business for both
queries. The validator was treating a stranger's data as disproof. Fixed by requiring an
entity-name match before comparing, and reporting the ignored hit instead. Bad evidence
now never counts as disproof.

### 7.4 A silent dead-end in the approval flow
Approving a site whose business had no contact email caused email composition to fail
silently; the lead parked in an intermediate state with nothing to review and no
explanation. Now the blocked composition records an audited reason.

### 7.5 Social proof leaking in through a side door
Award text was correctly filtered from offerings — but the award *badge image* was being
promoted to the page hero, which is the same invariant violation with a different
payload. Also exposed a regex bug: `\bnominat\b` cannot match "Nominated", so the filter
had never fired.

## 8. Verified metrics

| Metric | Value |
|---|---|
| Tests | **323 passing** |
| Coverage | **85%** |
| Application code | ~5,700 lines across 51 modules |
| Test code | ~4,400 lines across 45 files |
| Database tables | 8, with 6 Alembic migrations |
| Static analysis | ruff + mypy clean; bandit + detect-secrets in pre-commit |
| Live validation | run against real Google Places / Yelp / OSM data for Frisco, TX across restaurant, lawn, plumbing and roofing categories |

## 9. What it demonstrates

- Designing for **correctness under adversarial, messy real-world input** rather than
  happy-path demos.
- **Compliance and safety encoded as code paths**, not documentation.
- **Human-in-the-loop system design** — cryptographic content binding so approval means
  approval of specific bytes.
- Auditability: append-only hash-chained ledger with database-level enforcement.
- API integration across four third-party providers with graceful degradation when any is
  absent or wrong.
- Testing discipline: hermetic, dual-backend, plus capability evals for
  non-deterministic AI output.

---

## 10. Designed and specified, NOT yet built

**Do not claim these as delivered.** Phases 1–6 of a 12-phase plan are implemented; 7–12
are specified in `docs/MASTER_PLAN.md` with their guard tests defined.

- **Phase 7 — Send infrastructure**: provider adapter, inbox rotation, per-inbox daily
  caps, domain warmup tracking, and an automatic deliverability kill switch (pause a
  domain at >2% bounce or >0.3% complaint). *Nothing has been sent; there is no sending
  code.*
- **Phase 8 — Reply monitoring**: IMAP/Gmail polling, Claude classification
  (interested / question / not-interested / unsubscribe / complaint / auto-reply),
  automatic suppression on unsubscribe.
- **Phase 9 — Reply drafting** behind a third human gate.
- **Phase 10 — Payments**: Stripe deposit + subscription, provisioning on paid, no card
  data touched.
- **Phase 11 — Complaint handling and reporting.**
- **Phase 12 — Observability**: run health gate, alerting, dashboards.

### Known limitations (worth stating honestly if asked)
- Content extraction is regex-based over arbitrary third-party HTML; JavaScript-rendered
  sites yield little, and scraped "offerings" can still contain navigation text.
- Contact-email discovery succeeds for roughly 40% of leads.
- Lead yield is deliberately low — of 19 lawn-care businesses in one real run, 13 were
  correctly disqualified as already having healthy sites.

---

## 11. Résumé-ready framings (pick and trim)

**Concise:**
> Built a human-in-the-loop sales automation platform (Python/FastAPI/PostgreSQL, 323
> tests, 85% coverage) that discovers local businesses with weak websites, verifies every
> fact against ≥2 independent sources before use, auto-generates a replacement website,
> and enforces CAN-SPAM compliance and cryptographically-bound human approval on a
> tamper-evident audit ledger.

**Bullets:**
- Designed a multi-source research engine (Google Places, Yelp, OpenStreetMap, direct
  site crawl) with entity resolution and field-aware corroboration; facts require two
  independent sources to be presentable, and disagreements surface as conflicts rather
  than guesses.
- Implemented an append-only, hash-chained audit ledger with PostgreSQL trigger
  enforcement and advisory-lock concurrency safety, verified under 8-way concurrent
  writes.
- Built two human approval gates with content-hash binding, so an approval is valid only
  for the exact reviewed bytes and any edit invalidates it.
- Encoded CAN-SPAM compliance as executable guards — footer, subject validation,
  suppression list, and a send-blocking check on placeholder sender addresses.
- Caught and fixed a third-party API defect (Google Places omitting website/phone outside
  Place Details) that would have caused 19 factually false outreach emails; added
  regression coverage.
- Achieved 323 tests at 85% coverage with fully hermetic suites (protocol-injected
  adapters, transport-level HTTP mocking) running against both SQLite and PostgreSQL.
