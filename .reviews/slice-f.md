# Slice F — fixtures, the census, the instrument

## Changed

    app/site/fingerprint.py    the vector: seven axes, weighted by visibility x
                               decidedness, versioned so a change of ruler
                               cannot be read as a result
    app/site/agreement.py      scores the vector against hand-judged pairs by
                               rank; no threshold, so nothing is fitted
    app/site/pipeline.py       the build in stages, each answer persisted;
                               `open_site` unchanged in behaviour
    app/site/render.py         hero floor, trade-aware action wording,
                               `trade_kind` derived from `trade`
    app/store/messages.py      the workspace conversation, and the boundary
                               that keeps model prose off a page
    tools/quality_census.py    the numbers, and the two assertions
    tests/fixtures/briefs/     eleven real businesses, self-sufficient
    tests/fixtures/pairs.json  fifteen pairs judged blind
    tests/sitegen/test_axes_are_real.py   the standing test

## Decisions

    Weight by visibility AND decidedness, `min` — a consequence of the brief is
      not a design decision. Forecloses nothing yet; `min` suppresses a
      deliberate below-fold choice and must be revisited when the signature
      device lands.

    layout_bias removed — a pure function of `mood`, double-counting it. It
      returns when page architecture becomes independently settable, which is
      what it was standing in for.

    Rank, not a threshold — a cut chosen on ten pairs and scored on the same
      ten is fitted. Forecloses a pass/fail gate until a cut is derived from
      the labels and recorded as fitted.

    The hero floor reads the sign of `usable` — condemnation, not mediocrity.
      Shape and low quality are reasons to crop. Forecloses using the floor to
      express "we would rather not lead with this".

    Model prose lives in `messages` and nowhere else — enforced by an AST test
      over `app/site`, not by remembering.

    Headless Chrome, not Playwright — Chrome is present, the capture is one
      command per width, 150MB of browsers buys nothing yet.

## Numbers

    agreement  35 of 36 cross-pairs, ruler 563eaa0b, labels 747e4ef5
    census     same-trade mean 52% distance = 48% identical
               worst pair contractor-bare / roofer at 27%
               standing inversion dentist / law
    tests      706

## Assumptions I could not verify

    That the fifteen pair judgements are right. They are mine, from the fold
    screenshots, and the four "different" verdicts in the first version were
    contaminated by the vector's own vocabulary. The re-judge is blind but it
    is still one pair of eyes, and it is the ground truth everything else is
    scored against.

    That 720px thumbnails are enough to answer "same tool?". The full sheets
    are 400MB and cannot go in the repository; the committed row is half scale.

    That `min` is right for the axes that exist. It is the safe direction given
    the vector overstates, and it is untested against an axis where the two
    principles disagree the other way.

## Questions I want answered before the next slice

    `claude/site-quality-prompt.md` is not in the repository, on this branch or
    on main, and not anywhere on this machine. Slice B is meant to be built
    from it, and it supersedes a brief whose amendments were contradicting each
    other — so I have not started, rather than working from the version it
    replaces.

    Whether the two `unsure` pairs are unsure. Both are `threadbare` against a
    photographic page, and the question is whether a stranger reads its
    emptiness as a different kind of page or as a broken one. That judgement
    changes what the type-led first screen has to achieve.
