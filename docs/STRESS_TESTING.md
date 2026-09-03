# Stress-testing this platform yourself

The suite proves the code does what I intended. It cannot prove I intended the
right thing — that is what you are testing for. Everything below is safe:
**nothing sends**, and any state you break can be rebuilt in two minutes.

Reset at any point with:

```bash
cd ~/CascadeProjects/local-web-outreach
.venv/bin/python -m app.cli reset
.venv/bin/python -m app.cli discover "Frisco, TX" --category restaurant
.venv/bin/python -m app.cli advance --limit 10
make api
```

---

## 1. Attack the research (the thing most likely to embarrass you)

The one unrecoverable failure is emailing a business something false about
itself. Try to make that happen.

| Try this | What should happen | If it doesn't |
|---|---|---|
| Open a lead, click every `sources (n)` link in the dossier | Every VERIFIED fact is confirmed by both linked pages | **Tell me immediately** — corroboration is too loose |
| Find a CONFLICT claim and read both candidate values | They are genuinely different, not the same value formatted two ways | Normalization has a gap |
| Check a business you know personally | Facts match reality | — |
| Run `discover` on a category you know well (`--category dentist`) | Businesses with good sites get DISQUALIFIED; only genuinely weak ones qualify | Qualification is too loose/tight |
| Look at any "no HTTPS" lead and visit their site | Browser really does say "Not secure" | The evidence is stale |

Then run the automated version of the same thing:

```bash
.venv/bin/python -m app.cli validate
```
It re-queries every source live and reports **FAIL** (a stored fact or the pitch
is now wrong) versus **WARN** (unconfirmable, but not false).

## 2. Attack the approval gates

These exist so nothing ships without you. Try to get around them.

1. **Approve, then check the hash.** Approve a site, open Approvals log, confirm
   the content hash matches the one in the confirm dialog.
2. **Edit after approving.** Press `E` on an item, change the copy, save. The
   draft re-hashes and your earlier approval no longer matches — it must be
   re-approved.
3. **Double-approve.** Approve the same item twice quickly. The second attempt
   should fail (409), not silently duplicate.
4. **Reject then look for the data.** Rejecting disqualifies but must not delete
   the business, its claims, or its audit trail. Check the CLOSED column.
5. **Verify a fact, then read the ledger.** Use *I verified this* on a conflict,
   then open the business detail. The timeline must name you, the time, and how
   you said you confirmed it.

## 3. Attack the compliance guards

```bash
# every generated email must carry a physical address and an opt-out
make email-demo
```
Then try to break it in the console: press `E` on an email draft, delete the
footer entirely, and save. It must come back. Try setting the subject to
`Re: your invoice` — that must be rejected with an error, not saved.

```bash
# and prove nothing can leave while the address is a placeholder
.venv/bin/python -c "
from app.core.compliance import assert_real_sender_address
from app.core import config
assert_real_sender_address(config.sender_postal_address())"
```
That should raise. If it ever prints nothing, the send guard is off.

## 4. Attack the data itself

| Try this | Expected |
|---|---|
| `discover` the same city+category twice | No duplicates on the board — identity dedup catches the same business under different Google place_ids |
| `discover` a tiny town with few businesses | Small or empty result, no crash |
| `discover "Toronto, ON"` | Nothing — non-US is geo-gated for CAN-SPAM reasons |
| `advance --limit 50` when only 3 qualify | Advances 3, exits cleanly |
| Run `advance` twice in a row | Second run finds nothing to do |
| Kill the server mid-approval (`Ctrl-C`) then restart | No half-written state; the ledger still verifies |

## 5. Attack the console

- Resize to a narrow window — the board scrolls horizontally, nothing overlaps.
- Toggle Appearance (light/dark) on every screen.
- Use only the keyboard: `A` `E` `R` `X`, arrows, `Esc`. Never get stuck.
- Open the preview link from a review item; confirm the DRAFT marker is present
  and the page does **not** link back to the business's current website.
- Turn on "reduce motion" in macOS accessibility settings — all animation stops.

## 6. Prove the audit ledger is real

```bash
.venv/bin/python -c "
from app.core.db import make_engine, make_session_factory
from app.core.config import database_url
from app.core.audit import verify_chain
s = make_session_factory(make_engine(database_url()))()
print('chain valid:', verify_chain(s))"
```

Now try to tamper with it:

```bash
sqlite3 local_web_outreach.db "UPDATE audit_events SET actor='someone_else' WHERE seq=2;"
```
Re-run the check — it must report the chain broken and name the first bad
sequence number. (Then `reset` and rebuild.)

---

## What the automated suite covers

**334 tests, 85% coverage** — 248 unit, 80 functional, 5 performance. All pass;
`ruff` and `mypy` are clean.

| Area | Tested |
|---|---|
| State machine | Every legal transition, every illegal one rejected, both gates refuse without a matching approval |
| Audit ledger | Append-only enforced in app **and** by database triggers; hash chain detects tampering; gapless under 8 concurrent writers |
| Approvals | Content-hash binding; stale hash → 409; edits invalidate a staged approval |
| Research | Corroboration thresholds; conflict handling; address/phone/rating normalization incl. the real Camero's and Heritage cases; no claim without a source |
| Entity resolution | Look-alike businesses refused; a directory's wrong-business hit never counts as evidence |
| Discovery | Geo-gate; identity dedup (the real 3× `JC's Landscaping` case); Place Details enrichment; failure degrades gracefully |
| Site generation | Only shippable facts render; forbidden sections raise; self-attested content must declare provenance; a field renders once |
| Extraction | Menus (priced items and PDF/photo), hours, socials, actions; awards/logos/badges excluded; junk hosts dropped |
| Compliance | Footer, subject validation, suppression by address and domain, placeholder-address send block |
| Email copy | Never criticises their site, across every weakness combination |
| Operator verification | Attribution recorded; already-corroborated claims refused; vouched facts reach the site |
| Migrations | Run against **populated** legacy databases, including widening a CHECK constraint |
| Console | Template tag balance, every screen reachable, API wired to real endpoints |

**What the suite does not cover, honestly:** live third-party API behaviour
(mocked at the transport layer), the visual design (no screenshot tests), and
anything in the unbuilt phases — sending, replies, payments.
