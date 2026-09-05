"""What fraction of real feedback does the parser actually understand?

    .venv/bin/python tools/feedback_census.py

The corpus is the operator's own words about generated pages, verbatim where
they were written down, plus the ordinary asks any operator makes. Run it after
touching the parser.

The number that matters is not how much lands in the first group. It is whether
anything in the first two groups is a MISREAD rather than a hit — a miss is
visible to the operator as a grey chip, and a misread is not. Naming a section
used to mean "more of it", so every complaint about a section quietly promoted
that section.
"""

from app.site.iterate import DEFAULT_SPEC
from app.site.iterate import parse_iteration_instruction as parse

# Everything the operator actually said about a generated page this session,
# verbatim where it was written down, plus the ordinary asks any operator makes.
CORPUS = [
    # --- his own words, from .notes/feedback.md -------------------------- #
    "Our story doesn't actually have anything about their story",
    "the what we offer section looks very ai-generated and empty",
    "the back to top button does not work",
    "the pictures here are so small for the first picture",
    "the font and text is also super boring",
    "there is a lot of empty space",
    "why are the awards in the have a look around section",
    "why is there a picture of one of the awards next to dinner service",
    "what is this contrast",
    "the hero being generic veggies isn't something that would draw someone in",
    "the heritage table title is super small",
    "the have a look around gallery is weirdly spaced",
    "having a picture for their pitch to plan events which is cut off is odd",
    "the hero page is filled with a super low resolution photo",
    "some of the text on the page is super boring, there is no organization",
    # --- ordinary asks --------------------------------------------------- #
    "make it darker",
    "lead with the gallery",
    "the page should have more blue",
    "remove the reviews",
    "add a book a table button",
    "use a different hero photo",
    "warm and rustic, lead with the gallery, book a table",
    # --- plausible, unsupported ------------------------------------------ #
    "make the specials the star",
    "the copy is too long",
    "shorten the about section",
    "add more whitespace between sections",
    "make the logo bigger",
    "the headline should mention family owned",
    "put their phone number in the header",
    "two columns instead of three",
    "add a map",
    "the hours look cramped",
]

full, partial, none_ = [], [], []
for line in CORPUS:
    out = parse(line, dict(DEFAULT_SPEC))
    got, missed = out["understood"], out["ignored_tokens"]
    (full if got and not missed else partial if got else none_).append(
        (line, got, missed))

for label, group in (("UNDERSTOOD", full), ("PARTIAL", partial),
                     ("NOT UNDERSTOOD AT ALL", none_)):
    print(f"\n=== {label}  ({len(group)}/{len(CORPUS)}) ===")
    for line, got, missed in group:
        print(f"  {line!r}")
        if got:
            print(f"      got:     {got}")
        if missed:
            print(f"      grey:    {missed}")
