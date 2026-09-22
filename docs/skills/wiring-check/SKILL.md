---
name: wiring-check
description: Verify a change is wired end to end — producer, consumer, real stored artifact — before reporting any code work as done.
---

# The wiring check

Apply this to any code change before saying it is finished. Most shipped bugs
are wiring bugs, not logic bugs: two modules that each work, connected by an
assumption nobody tested. A passing test suite does not detect them, because
the test and the code share the wrong assumption.

## Before starting

1. **Name the producer and the consumer.** For every file, table, or
   dictionary key the change touches, state what writes it and what reads it.
   If either answer is "something presumably does", go find out before writing
   code.
2. **Grep for the other consumers.** The one being changed is rarely the only
   one. Search the whole tree for the filename, table name, or key.

## Before reporting it done

3. **One round-trip test per seam.** The real producer writes, the real
   consumer reads, nothing hand-made in between. A hand-written fixture only
   tests the belief about the format — which is the belief that was wrong.
4. **Look at the real stored artifact.** Open the actual file, query the
   actual table, read the actual generated output, for real data — not the
   test output. Thirty seconds here catches what the suite cannot.
5. **Run the real entry point end to end** — the command or screen the user
   actually uses — and confirm the value changed.
6. **Ask what regenerates it.** An artifact nothing refreshes is a wrong
   answer with a timestamp on it. If nothing in the codebase writes it, say so.
7. **Name what is now downstream and stale.** A change to what gets stored
   leaves everything computed from the old version behind: caches, derived
   rows, generated pages, prior runs. Either re-run them or tell the user
   which ones are stale.

## Worked examples from this project

- `review/run.py` read `briefs/<slug>/current.json` as a brief. The writer,
  `store/brief_archive.py`, had been changed to put a three-key pointer there.
  Every claim check ran against an empty dictionary and reported "unsourced"
  while the screen said a brief had loaded. Step 1 would have caught it in
  thirty seconds.
- `make brief` wrote only to the archive, never to the database the workbench
  reads. Two copies of the same brief drifted for two weeks. Step 4 caught it.
- An override reached `facts` but not `published`, which is where a generated
  page's words come from. Corrections changed a screen and nothing a visitor
  would see. Step 1, again.

## The rule

Never report a fix as done on the strength of a passing test. Report it on the
strength of having watched the real system produce the right value. When that
is not possible in the session, say which of the seven steps was not done.

## Reporting

When the work is finished, state plainly: what was changed, which seam was
round-tripped, what real artifact was inspected, and what is left stale. If an
earlier claim in the conversation turns out to have been wrong, correct it
explicitly rather than quietly moving on.
