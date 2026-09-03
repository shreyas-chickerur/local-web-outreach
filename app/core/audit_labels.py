"""Human-readable titles for audit events.

The ledger stores machine actions (``advance:SITE_DRAFTED->SITE_APPROVED``)
because those are precise and greppable. A person reading a timeline wants a
sentence. This maps one to the other; the raw action stays visible as subtext so
the timeline is still auditable, not just readable.
"""

from __future__ import annotations

# Exact-match actions.
_EXACT = {
    "discover:created": "Found this business",
    "research:dossier_built": "Researched the business",
    "outreach:blocked": "Could not draft the outreach email",
    "approval:recorded": "Decision recorded",
    "edit": "Operator edited the draft",
    "claim:operator_verified": "Operator verified a fact",
}

# Status transitions, keyed by the destination state.
_TRANSITIONS = {
    "QUALIFIED": "Qualified as a lead",
    "DISQUALIFIED": "Set aside — not a lead",
    "RESEARCHED": "Research complete",
    "SITE_DRAFTED": "Website drafted",
    "SITE_APPROVED": "You approved the website",
    "EMAIL_DRAFTED": "Outreach email drafted",
    "EMAIL_APPROVED": "You approved the email",
    "SENT": "Email sent",
    "REPLIED": "They replied",
    "NEGOTIATING": "In conversation",
    "WON": "Won",
    "LOST": "Lost",
    "SUPPRESSED": "Suppressed — will not be contacted",
}


def humanize(action: str) -> str:
    """A readable headline for one audit action."""
    if action in _EXACT:
        return _EXACT[action]
    if action.startswith("advance:"):
        _, _, arrow = action.partition(":")
        destination = arrow.split("->")[-1].strip()
        if destination in _TRANSITIONS:
            return _TRANSITIONS[destination]
        return f"Moved to {destination.replace('_', ' ').lower()}"
    if ":" in action:
        head, _, tail = action.partition(":")
        return f"{head.capitalize()} — {tail.replace('_', ' ')}"
    return action.replace("_", " ").capitalize()
