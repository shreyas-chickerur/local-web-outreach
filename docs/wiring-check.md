# The wiring check

Run this before calling any piece of work done. Every bug this project has
shipped so far has been a wiring bug, not a logic bug: two modules that each
worked, connected by an assumption nobody tested.

The three that reached the running system:

- `review/run.py` read `briefs/<slug>/current.json` as a brief. The writer
  (`store/brief_archive.py`) had been changed to put a three-key *pointer*
  there. Every claim check ran against an empty dictionary and reported
  "unsourced" while the screen said a brief was loaded.
- The phone reader matched ten digits anywhere in the markup and published a
  WordPress timestamp out of an image filename as the number to ring.
- The address reader required a comma before the town. The business writes
  "7110 Main St. Frisco, TX 75033". The fact sat at one source forever.

None of these failed a test. All three were visible in thirty seconds of
looking at what the running system had actually stored.

## Before starting

1. **Name the producer and the consumer.** For every file, table or dictionary
   key the change touches, write down what writes it and what reads it. If
   either answer is "I assume something does", go find out.
2. **Grep for the other consumers.** The one you are changing is rarely the
   only one. `grep -rn "current.json" --include=*.py app` is the whole step.

## Before saying it is done

3. **One round-trip test per seam.** The producer writes, the consumer reads,
   nothing hand-made in between. A fixture written by hand tests your belief
   about the format, which is the belief that was wrong.
4. **Look at the real stored artifact.** Open the actual file, query the
   actual table, read the actual generated page. Not the test output — the
   thing on disk, for a real lead.
5. **Check it on the real lead end to end.** Run the command the operator
   runs. Confirm the number moved.
6. **Ask what regenerates it.** `captures/` has no writer anywhere in the
   codebase: it is hand-made and two weeks stale, and the claim inventory
   judges against it. An artifact nothing refreshes is a wrong answer with a
   timestamp on it.
7. **Check what is now downstream and stale.** A fix that changes what gets
   stored leaves everything computed from the old version behind — the review
   rows, the generated page, the archived brief. Say which, or re-run them.

## The rule

Do not report a fix as done on the strength of a passing test. Report it on
the strength of having watched the real system produce the right value.
