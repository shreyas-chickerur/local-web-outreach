# Phase 0 — speed, and a real screenshot-determinism bug found chasing it

No output changed: `ruler d2f37ed7` and `rule 95f4d93e` are both unchanged
before and after every item below. That is the proof, not an assertion.

## 0a/0b/0c — parallel capture, skip-unchanged, --widths

`shoot()` calls are independent subprocess invocations writing to separate
files, so `ThreadPoolExecutor(max_workers=MAX_WORKERS=6)` runs them
concurrently. A manifest (`.reviews/sheet/.captured.json`, committed) maps
`slug:width` to a SHA-256 of the exact HTML the PNG was shot from; a match
with the PNG still on disk is skipped, `--force` bypasses it.
`test_the_committed_sheet_shows_the_corpus_that_shipped` is untouched and
still catches a stale PNG — the manifest only skips a RE-shoot, it never
substitutes for that check.

**Required proof, done twice.** Three fixtures (`barbecue`, `law`,
`salon-rich`) across all five widths, shot serially and shot in parallel:
15 of 15 byte-identical, both times, same hashes both times. One transient
mismatch on `barbecue`/`mobile` appeared on a first attempt and did not
reproduce on either of the two clean runs that followed — noted rather than
hidden, and it did not affect `page` or `fold`, the two the ground truth is
judged from, which were identical every time across every attempt.

**Timing.** Full 95-shot capture (19 fixtures x 5 widths), cold:
**2:20 (140s)**, parallel, deterministic. Serial baseline: two independent
15-shot serial measurements agreed to 0.2s (73.8s, 74.0s) — 4.93s/shot,
extrapolating to **~468s (7.8 min)** for 95 shots. Warm (nothing changed):
**7.6s**, all 95 skipped by the manifest.

## A real, pre-existing nondeterminism bug, found proving 0a

Before touching concurrency at all: the SAME file, SAME width, shot three
times in a row with NO parallelism whatsoever, came back byte-different
roughly one time in three. Parallelising `shoot()` was going to make an
existing flaw far more likely to bite, not introduce one.

Two independent causes, both in `shoot()`, neither about the width chosen:

1. **No profile isolation.** Every invocation launched against Chrome's real
   default profile — captured stderr showed genuine account activity
   (`docs.google.com`/`mail.google.com` PWA-install checks) that has nothing
   to do with the page being screenshotted. `--user-data-dir` pointed at a
   fresh directory was tried and DROPPED: on this Chrome build a non-default
   profile directory made `--headless=new` hang on exit — the file was
   written correctly and the process then declined to die inside the
   60-second budget. `--disable-background-networking` and its neighbours
   (`--disable-sync`, `--disable-default-apps`, `--disable-component-update`,
   `--metrics-recording-only`, `--no-default-browser-check`,
   `--no-service-autorun`, `--disable-features=Translate,OptimizationHints`)
   get the same isolation without touching the profile directory at all.
2. **Network-dependent fonts.** Every generated page loads its font from
   `fonts.googleapis.com` with `display=swap` — paint immediately in a
   fallback face, repaint once the real one downloads. Chrome's
   `--screenshot` fires on the load event, which can land on either side of
   that repaint depending on how fast the network answers. This is the exact
   failure this project's fixtures were built to escape (`BRIEF`: "runs with
   no key, no cache and no network") — it had just never been checked against
   the SCREENSHOTS the fixtures are judged from, only the data.
   `--host-resolver-rules` sends both font hosts to `127.0.0.1`, so the
   request fails immediately and the fallback face renders, every time, with
   nothing to race.

Fixing both left ONE further source, found chasing the second down: hero and
card elements reveal on a CSS transition (`[data-reveal]`, added by a
`reveals` class late enough to land mid-transition). Already conditional on
`prefers-reduced-motion` in the stylesheet — `--force-prefers-reduced-motion`
tells Chrome the visitor asked for it, a real supported preference rather
than a workaround.

All three together: four repeats of the same file, same width, byte-identical.

**A related operational gotcha, found recovering from an unrelated incident
this same session** (see the commit message for the full story): after
killing a `--redecide` mid-run, `artifacts/fixtures.db` can retain state from
the aborted attempt even once the fixture JSON files themselves are restored
from git — `contact_sheet.py`'s recomputed axes did not match a fresh,
in-memory recomputation from the (correctly restored) files until the stale
db was deleted. `artifacts/` is already gitignored and the db is already
documented as a disposable cache; the gotcha is that "restore the tracked
files" is not the same as "the cache is trustworthy again" and nothing said
so. Noting it here rather than building a check for it now — it did not
recur once the db was cleared, and the cost of getting it wrong is a failing
`test_the_committed_sheet_shows_the_corpus_that_shipped`, not a silent one.

## 0d — preflight

One cheap Anthropic ping plus a report of which directory APIs
(`available_directories()`) are configured, before either the normal research
path or `--redecide` spends anything. Verified: with the key present it
prints "reachable, has credit"; the failure path was exercised for real
earlier in the same session (a genuine "credit balance is too low" error, not
a synthetic test) and confirmed to raise `claude.ClaudeError` on the first
call rather than eight fixtures in.

## 0e — refuse to redecide over untracked fixtures

`git status --porcelain -- tests/fixtures/briefs` before `--redecide` does
anything; any `??` entry refuses with the file names and the fix (`git add`
them, or commit, then redecide). Proven twice: (1) a throwaway untracked file
dropped into the fixtures directory triggers the refusal correctly, and the
guard reports `False` again the moment it is removed; (2) the version of
this check that was NOT yet written would have let a redecide proceed a
second time this same session — see the commit message.

Three standing tests in `tests/test_make_fixtures_guards.py`: the refusal
fires on an untracked file, does not fire on a clean tree, and (the premise
the guard depends on) every fixture actually on disk is `git ls-files`-tracked
right now — so a fixture added to the directory without ever being `git add`ed
would be caught directly rather than by trusting the guard was exercised.

## 0f — NOT DONE, and why, stated rather than silently skipped

Vision labelling is genuinely order-independent and a real parallelisation
target, but making it concurrent ACROSS fixtures during a `--redecide`
without touching per-fixture lead-id lifecycle turned out to need a real
restructure: `freeze_vision()` calls `leads.save_brief()` fresh inside its own
per-fixture loop, so a photographs-only pre-pass across all nineteen fixtures
before the serial direction+page pass would need lead-ids assigned ahead of
that pre-pass and threaded through to the later serial pass — a change to the
lifecycle of the exact tool this project's corpus integrity depends on, for a
secondary win (direction calls still have to run serially regardless, and
they are comparable in latency to vision per fixture). Given the real,
higher-value, lower-risk work waiting in Phases 1-3 — including a confirmed
correctness bug in 1a — I chose not to spend the remaining time on this
restructure this round. Flagged here as a specific, scoped follow-up rather
than silently dropped.

## 0g/0h

Followed as working discipline for the rest of this session (batch every
redecide-forcing change within a phase; run only the affected test file
during iteration, full `make check` before every commit) rather than as a
code change.

## An incident during this phase, and how it was handled

Testing 0e's refusal path required a git-status check on the fixtures
directory. Between sessions the fixtures had all been committed (a prior
`bb0de5c`), which I did not confirm before invoking `--redecide` "to see the
guard refuse it" — since nothing was untracked, the guard correctly did
NOT refuse, and a real, unintended, full nineteen-fixture redecide started
running. Killed within seconds of noticing (the files turning `M` one at a
time in `git status` mid-run was the tell). Because every fixture was
already `git add`ed, `git checkout -- tests/fixtures/briefs/` restored the
exact pre-redecide state instantly and completely — confirmed field-by-field
against fingerprints recorded before the incident, and confirmed again via
775 passing tests. This is the exact scenario 0e exists to make survivable,
demonstrated by accident rather than by the test suite, and it is the reason
`artifacts/fixtures.db` needed clearing per the note above. No fixture
content, judged verdict, or pinned hash was lost.

## Numbers (unchanged, which is the point)

    ruler d2f37ed7 · rule 95f4d93e — both identical to before this phase
    tests 778 (775 + 3 new guard tests)
    make check: clean

## Literal output

### `make check`

```
........................................................................ [ 46%]
........................................................................ [ 55%]
........................................................................ [ 64%]
........................................................................ [ 74%]
........................................................................ [ 83%]
........................................................................ [ 92%]
..........................................................               [100%]
778 passed in 21.72s
```
