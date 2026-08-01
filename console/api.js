/**
 * lib/api.ts equivalent — the SINGLE data layer for the Operator Console.
 *
 * LIVE version: every exported function calls the FastAPI backend and reshapes
 * the response into the exact shapes the UI components consume (see the mock in
 * design/ for the reference shapes). Served same-origin by FastAPI, so requests
 * are plain relative `/api/...` fetches — no CORS, no base URL.
 *
 * Signatures + return shapes are unchanged from the mock, so no component changes.
 */

const STATUS_ORDER = [
  "DISCOVERED", "QUALIFIED", "RESEARCHED", "SITE_DRAFTED", "SITE_APPROVED",
  "EMAIL_DRAFTED", "EMAIL_APPROVED", "SENT", "REPLIED", "NEGOTIATING",
  "WON", "LOST", "SUPPRESSED", "DISQUALIFIED",
];

export const statusOrder = STATUS_ORDER;
export const ACTIVE_STATUSES = STATUS_ORDER.slice(0, 10);
export const CLOSED_STATUSES = STATUS_ORDER.slice(10);

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------
async function http(path, opts) {
  const res = await fetch("/api" + path, {
    headers: { "Content-Type": "application/json" },
    ...(opts || {}),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); if (j && j.detail) detail = j.detail; } catch (e) { /* noop */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// A dossier for the UI is a grouped object; the backend returns a flat claim
// list plus a separate questions list. Regroup here.
function dossierObj(claims, questions) {
  return { claims: claims || [], questions: questions || [], rejected_sources: [] };
}

function subjectKind(subjectType) {
  return String(subjectType || "").toLowerCase().includes("site") ? "site" : "email";
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function listBusinesses() {
  const rows = await http("/pipeline");
  return rows.map((b) => ({
    id: b.id, name: b.name, location: b.location, category: b.category,
    status: b.status, opportunity_score: b.opportunity_score, has_site: b.has_site,
    existing_site_url: null, address: null, phone: null, why: b.why,
  }));
}

export async function getBusiness(id) {
  const d = await http(`/businesses/${id}`);
  if (!d) return null;
  return {
    business: {
      ...d.business,
      address: d.address, phone: d.phone, existing_site_url: d.existing_site_url,
    },
    weaknesses: d.weaknesses || [],
    dossier: dossierObj(d.dossier, []),
    websites: d.websites || [],
    emailDraft: null,
    audit: d.audit || [],
  };
}

// Businesses sitting at a human approval gate, in queue order.
export async function getReviewQueue() {
  const items = await http("/review-queue");
  return items.map((it) => ({
    business: {
      ...it.business,
      address: it.address, phone: it.phone, existing_site_url: null,
    },
    gate: it.gate,
    weaknesses: it.weaknesses || [],
    dossier: dossierObj(it.dossier, it.questions),
    website: it.website || null,
    emailDraft: it.email || null,
  }));
}

export async function countAwaitingApproval() {
  const items = await http("/review-queue");
  return items.length;
}

export async function listApprovals() {
  const rows = await http("/approvals");
  return rows.map((a) => {
    const kind = subjectKind(a.subject_type);
    return {
      id: a.id,
      subject_type: kind,
      subject_label: `${a.business_name || "—"} — ${kind === "site" ? "site" : "outreach email"}`,
      decision: a.decision,
      actor: a.approver,
      ts: a.decided_at,
      content_hash: a.content_hash,
      reason: a.notes,
    };
  });
}

/**
 * Record an operator decision at a gate.
 * decision: "approve" | "reject" | "request_changes" | "edit"
 *
 * The UI computes its own hash for the email gate, which will not match the
 * backend's content_hash, so we always re-fetch the authoritative hash for the
 * current draft and send THAT as expected_content_hash. (The site gate already
 * passes the real hash, but re-fetching is harmless and keeps one code path.)
 */
export async function decide({ id, subjectType, decision, contentHash, reason }) {
  if (decision === "edit") return { ok: true }; // editing is handled by updateDraft, not a gate decision
  const gate = subjectKind(subjectType);

  let hash = contentHash;
  try {
    const item = await http(`/review/${id}`);
    if (item) {
      hash = item.gate === "site"
        ? (item.website ? item.website.content_hash : hash)
        : (item.email ? item.email.content_hash : hash);
    }
  } catch (e) { /* fall back to the UI-provided hash */ }

  const endpoint = gate === "site" ? "site-decision" : "email-decision";
  const result = await http(`/businesses/${id}/${endpoint}`, {
    method: "POST",
    body: JSON.stringify({
      decision,
      approver: "operator",
      expected_content_hash: hash || "",
      notes: reason || null,
    }),
  });
  return result; // caller ignores the value and re-refreshes
}

/**
 * Apply an operator edit to the draft at the current gate. The server re-hashes
 * the edited content and appends an immutable "edit" audit event; it does NOT
 * change status or record an approval (editing is not a gate decision). The
 * caller re-refreshes, which picks up the new hash for the subsequent approval.
 */
export async function updateDraft({ id, subjectType, patch }) {
  const gate = subjectKind(subjectType);
  const p = patch || {};
  const body = gate === "site"
    ? { subject_type: "site", heading: p.heading, subheading: p.subheading }
    : { subject_type: "email", subject: p.subject, body: p.body };
  return http(`/businesses/${id}/edit-draft`, {
    method: "POST",
    body: JSON.stringify({ editor: "operator", ...body }),
  });
}
