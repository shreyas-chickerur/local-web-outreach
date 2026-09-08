# Slice B, axis one — the first-screen contract

Per axis, not per slice: every axis moves the ruler by definition, and the
brief asks for review when a number moves. Bundling them would mean reasoning
about several ruler changes and several predictions at once, which is the
"re-pin, then measure — never both" trap under a different name.

## Changed

    app/site/firstscreen.py    the axis: five positions, and which ones a
                               business can actually support
    app/site/render.py         `_hero` renders each position; `_proof_points`
    app/site/styles.py         the CSS that makes them differ above the fold
    app/site/opening.py        the direction call chooses one, from what is
                               offerable
    app/site/fingerprint.py    the axis enters the vector, weighted highest —
                               it IS the first screen
    app/site/understand.py     the model's action carries no words of its own
    tests/sitegen/test_first_screen.py   proof that each position manifests

## Decisions

    First-screen contract before page architecture — two pages identical above
      the fold are the same site to the owner being shown them, and
      architecture is mostly below it. Forecloses nothing; architecture is
      still axis four.

    `proof` is a photograph band above type on the theme's ground, not a
      photograph behind type with a list — as first built it was `photo` with
      bullets, which is not a position. Forecloses using `proof` for a business
      whose photography is the selling point.

    The model chooses a call-to-action KIND and no words. Forecloses the model
      phrasing a button; an operator typing "book a table" still gets those
      words, because that is their phrasing.

    Labels record which rendering they judged. Forecloses carrying a verdict
      across a change to the page it described.

## Numbers

    agreement   40 of 40 cross-pairs, ruler 575db030, labels 449b9ddb
    census      same-trade mean 52% distance = 48% identical
                worst pair barbecue / restaurant-rich at 20%
    tests       740

## Assumptions I could not verify

    That `dentist`/`law` reading as different pages is right. It is my blind
    re-look at the current render, and it is one pair of eyes on the pair that
    the binding claim turned on. The screenshots are in `.reviews/sheet`.

    That `proof` is worth having with one proof point. The roofer has no
    corroborated address or hours, so its ruled row holds a single figure.
    Slice C's trade profiles are what give it substance; until then the
    position is thin for exactly the trades it exists for.

## Questions I want answered before the next axis

    Whether `barbecue` and `restaurant-rich` both choosing `photo` is a
    failure of the axis or the absence of the gate. My reading is the second —
    both genuinely have strong photography and nothing yet tells the direction
    call what the last ten sites did. If it is the first, type treatment will
    not fix it either and the budget has to come before more axes.
