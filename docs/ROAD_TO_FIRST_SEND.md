# Everything left before you can email a generated website to yourself

**Goal:** generate a real proposal site and receive the outreach email in your
own inbox. Not a customer — you.

Today the pipeline runs end to end and stops at `EMAIL_APPROVED`. **There is no
sending code at all.** Below is the complete remaining list, split by who does it.

---

## The short version

| # | What | Who | Effort |
|---|---|---|---|
| 1 | Real postal address in `.env` | **You** | 5 min (once you have one) |
| 2 | A public URL for preview links | You + me | ~1 hr |
| 3 | Build the send layer (Phase 7) | **Me** | ~1 day |
| 4 | An SMTP credential to send through | **You** | 15 min |
| 5 | A self-send safety mode | Me | ~2 hrs |
| 6 | Run it | You | 5 min |

**Blocking on you:** items 1 and 4. Everything else I can do.

---

## 1. A real postal address — **blocks everything**

CAN-SPAM requires a physical mailing address in every commercial email, and the
send guard refuses to run while yours reads `CHANGE ME`. Even for a test to
yourself, the code will not bypass it.

- Get a PO box (~$20–40/quarter), a registered-agent address, or use an address
  you're willing to publish.
- Put it in `.env` as `SENDER_POSTAL_ADDRESS=...`
- Verify with `make email-demo` — your real address should appear in the footer.

*Note: for a test to your own inbox this is arguably ceremony, but the guard is
deliberately absolute. I'd rather not add a bypass flag that could later be left
on.*

## 2. A public URL for the preview link

`PREVIEW_BASE_URL` is `http://127.0.0.1:8090`, which only resolves on your
machine. In an email to yourself opened on your laptop that technically works —
but it won't on your phone, and it proves nothing about the real flow.

Two options:
- **Quick (test only):** a tunnel — `ngrok http 8090` or `cloudflared tunnel` —
  then set `PREVIEW_BASE_URL` to the public hostname. ~10 minutes.
- **Proper:** deploy the API (Railway/Render/Fly) with a managed Postgres. ~1 hr.

I'd use the tunnel for the first self-send.

## 3. The send layer — Phase 7 (my work)

Does not exist. To build:

- `adapters/email_send.py` — a `Sender` protocol with an SMTP implementation and
  a `DryRunSender` that writes `.eml` files to disk instead of sending.
- A `send` stage that pulls `EMAIL_APPROVED` businesses and, **before every
  send**, re-checks: real postal address, recipient not suppressed, geo still
  US, the email still matches its approved content hash.
- `SENT` transition + audit event, with the provider's message id recorded.
- Per-inbox daily cap and inbox rotation.
- Deliverability tracking: bounce/complaint counters per domain, and the
  auto-pause kill switch (>2% bounce, >0.3% complaint).
- Guard tests: rate limit, auto-pause, suppression-and-geo-at-send, warmup gate,
  and the placeholder-address block.

**Dry-run is the default.** Real sending requires an explicit flag.

## 4. An SMTP credential — **the other thing only you can do**

For a self-send you do **not** need warmed domains or Google Workspace. Simplest
paths:

- **Gmail app password** on `friscooperator@gmail.com` (2FA → App passwords) —
  works immediately, fine for sending to yourself, **not** for real outreach.
- **A transactional provider** (Resend, Postmark, SendGrid) free tier — closer
  to production behaviour, still ~15 minutes.

Put it in `.env` as `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD`.
I never need to see the value.

*Do not use Gmail for real cold outreach — that's what the secondary domains and
warmup in the operator guide are for. This is strictly for testing.*

## 5. A self-send safety mode (my work)

So a test cannot become an accident:

- `SEND_MODE=self_test` restricts every recipient to an allow-list
  (`SEND_ALLOWLIST=you@example.com`). Any other recipient raises.
- The console shows a loud banner when self-test mode is on.
- The audit event records that the send was a test.

This is what makes step 6 safe to run without holding your breath.

## 6. Run it

```bash
.venv/bin/python -m app.cli reset
.venv/bin/python -m app.cli discover "Frisco, TX" --category restaurant
.venv/bin/python -m app.cli advance --limit 5
make api      # approve one site, then the email, in the console
.venv/bin/python -m app.cli send --dry-run     # writes an .eml you can open
.venv/bin/python -m app.cli send --to-me       # actually delivers, allow-list enforced
```

You get the email, click the preview link, and see the generated site as a
prospect would.

---

## One honest caveat

You can send to yourself with a Gmail app password and a tunnel in an afternoon.
**Sending to real businesses is a different project** — secondary domains,
Google Workspace, SPF/DKIM/DMARC, and 3–4 weeks of inbox warmup, all covered in
`OPERATOR_SETUP.md` Part B. Don't let a successful self-test convince you the
outreach infrastructure is ready; the self-test proves the *software* works, not
that your *deliverability* does.

---

## Beyond the first send (the rest of the 12-phase plan)

- **Phase 8** — reply monitoring and classification; unsubscribes auto-suppress.
- **Phase 9** — reply drafting behind a third human gate.
- **Phase 10** — Stripe deposit + subscription, provisioning on paid.
- **Phase 11** — complaint capture and reporting.
- **Phase 12** — health gate, alerting, dashboards.

And the two known quality gaps, independent of any phase:
- Content extraction is regex over arbitrary HTML; JS-heavy sites yield little,
  and scraped "offerings" can still contain navigation text.
- Contact emails are found for roughly 40% of leads.
