# Requirements v2 — Lead & Site Workbench

> **This replaces the outreach product.** No email is composed, approved, or sent.
> Outreach happens in person. This tool exists to research a company, build a
> site for it, and track where each lead stands.

---

## 1. Who it's for

One developer, working alone, walking into local businesses. Not a team, not a
campaign tool, not a CRM for salespeople. Everything that existed to make cold
email safe and legal is dead weight now and gets deleted.

## 2. The flow (this is the product)

```
  add a lead            →  brief              →  site              →  track
  URL or company name      facts + confidence    generate, then       where does
  + optional notes         + sources             iterate by chat      this stand
```

1. **Add a lead.** Paste a website URL, *or* a company name (with optional
   location), *or* both. Add free-text notes: anything you already know.
2. **Get a brief.** The system finds their site if you didn't give one, gathers
   what it can from independent sources, and shows you every fact with a
   confidence and its sources. You can correct or vouch for any of them.
3. **Generate a site.** Optionally with a free-text spec: *"dark, emphasize
   catering, they hate stock photos."*
4. **Iterate by chat.** *"Make the hero bigger." "Add their hours." "Less
   corporate."* Each turn produces a new version. Versions are kept; you can go
   back.
5. **Track.** Each lead has a status you control and a history of what happened.

## 3. What "simple" means here

The previous version had four screens, two approval gates, content hashes,
suppression lists, and a send pipeline. Concretely, v2:

- has **one primary screen**: a list of leads → open one → chat + preview
- has **no approval gates**. Nothing is irreversible, so nothing needs guarding.
  You mark a lead's status because *you* find it useful, not because the system
  demands a signature
- has **no content hashing**, no immutable approvals table, no compliance layer
- keeps a **plain activity log** per lead — readable history, not a hash chain

## 4. What is kept, and why

| Kept | Why |
|---|---|
| Multi-source research + confidence + sources | The core value. A brief you can trust is the reason to use this before walking in |
| "No unverified fact ships" | Still true. A site shown to an owner must not contain invented facts about them |
| Operator verification, attributed | You will know things the machine can't. Vouching stays, and stays attributed |
| Extraction from their existing site | Their menu/hours/services are what make a proposal credible |
| Site generation + preview URL | The deliverable |
| Per-lead activity log | Tracking, in plain language |

## 5. What is deleted

`stages/outreach.py`, `stages/send.py`, `core/compliance.py`,
`ai/email_composer.py`, `adapters/email_send.py`, `models/email.py`,
`models/suppression.py`, `models/sender_identity.py`, `models/approval.py`,
plus the email gate, send guards, suppression, CAN-SPAM validation, sender
identities, warmup, and the deliverability kill switch — and every test for them.

Bulk `discover` by location also goes: leads are added one at a time, on purpose.

## 6. Data model

Five tables, down from nine.

```
leads         (id, name, location, website_url, notes, status, created_at)
              status: NEW | RESEARCHED | SITE_READY | SHOWN | INTERESTED | WON | LOST | PARKED

facts         (id, lead_id, field, value, confidence, status, sources json,
               verified_by, verified_at, verified_note)
              status: verified | operator_verified | unverified | conflict

site_versions (id, lead_id, version, spec, content_json, preview_token,
               created_at)                       -- every iteration is kept

messages      (id, lead_id, role, text, version_id, created_at)
              role: user | assistant             -- the chat thread

activity      (id, lead_id, kind, summary, created_at)   -- readable history
```

## 7. Build order (each slice is testable on its own)

| # | Slice | Done when |
|---|---|---|
| 1 | **Brief** — name or URL + notes → facts with confidence and sources | You can run it on a real company and trust the output |
| 2 | **Lead store + tracking** — persist leads, statuses, activity | You can add several and see where each stands |
| 3 | **Site generation** with a free-text spec | A site you'd show someone |
| 4 | **Chat iteration** — instruct, regenerate, versioned | Getting to a site you like feels like a conversation |
| 5 | **The one screen** — leads list → chat + live preview | You'd actually use it daily |

Each slice ships with tests and gets reviewed before the next starts.

## 8. Non-goals

No email. No campaigns. No multi-user. No payments — for now. No CRM pipeline
automation. If a feature only makes sense at volume, it does not belong here.
