# Slice B — the diversity budget

Out of order on purpose. The gate was meant to come "partway through Slice B",
after more axes; it comes before axis two because the premise for deferring it
was re-checked and had expired.

## Changed

    app/site/identity.py         the gate: ask again naming what is taken,
                                 then perturb deterministically, then say so
    app/store/fingerprints.py    what this workbench has already shipped
    app/site/opening.py          the direction call can be told what to avoid
    app/site/pipeline.py         the gate runs at `direction`, history is
                                 written at `page`
    docs/BRIEF.md §2.5           the deferral reason, and why it expired

## Decisions

    Build the gate before axis two — "with eight axes it would reject nearly
      everything" was true at seven and false at eight: one same-trade pair in
      ten collided, not nine. Forecloses claiming a later axis fixed a
      collision the gate would have fixed anyway.

    A replayed direction is never re-gated — the gate ran when it was first
      decided. Forecloses the gate being order-sensitive on rebuild, and it is
      what keeps a keyless reviewer reproducing the same numbers.

    No key means perturb, not ask again — asking falls through to the trade
      table, which is not a different answer but a worse one. Forecloses the
      keyless path getting the retry's benefit; it gets variety instead.

    History is written when a page is BUILT, not when a direction is decided.
      Forecloses counting a site that was rejected by the content gate.

## Numbers

    agreement   40 of 40 cross-pairs, ruler 575db030, labels 449b9ddb
    census      same-trade mean 62% distance = 38% identical
                was 52% / 48% before the gate
                worst pair bare-trade / law at 35%, was barbecue /
                restaurant-rich at 20%
    tests       748

    BASELINE_IS_FRESH is back to True — this commit re-pins. Flip it to False
    on the next commit that touches the baseline, or the message goes stale in
    the other direction.

## Assumptions I could not verify

    That REQUIRED_AXES=4 and WINDOW=10 are right. They are the brief's numbers
    and they have never been tuned — eleven fixtures is too few to tune
    against, and tuning them on the corpus they are scored against is the
    fitted-threshold mistake. They need a few dozen real leads.

    That the perturbation order — first screen, then accent — is the right
    preference. It reaches for what a person sees soonest, which is the same
    argument as the axis ordering, but nothing has measured it.

## Questions I want answered before axis two

    Whether `bare-trade` / `law` at 35% is now the real target. Two attorneys
    sharing accent, action, first screen and mood. The gate did not separate
    them because 35% clears the four-axis rule — so either the rule is too
    loose for same-trade pairs, or type treatment is exactly what they need.
    I would rather know which before building the axis that assumes the second.
