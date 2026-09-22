# Working agreement

How to work on this project with its owner. These are preferences he has
stated, plus the habits that have actually worked. Following them is not
optional politeness — several were written down after something went wrong.

## Language

- **No acronyms or short forms.** Expand every term: "Agent Software
  Development Kit", "application programming interface". This applies to
  comments, documents and chat.
- **Never use the word "utilize".**
- For anything he will send under his own name: short sentences, plain
  language, no corporate polish, no parallel structures that read as
  machine-written, concrete technical anchors, and honest acknowledgment of
  gaps.
- Responses are concise. Say what happened and what it means; do not narrate
  each step, and do not recap what he watched you do.

## Decisions that are his, not yours

Prepare them fully, then ask. Never settle them yourself:

- What a confidence rating should mean.
- Which fields deserve a reviewer's attention.
- Whether a sentence sounds right in a business's voice.
- Whether a site is approved. Stage seven is deliberately a person.
- Anything he can judge manually and cheaply — leave it for him.

Ask with a real question and real options. "Which fields should the screen
offer?" produced a better build than guessing would have, in one exchange.

## Money and time

He has said twice: minimise credits, and design the flow so tokens are not
wasted. In practice:

- A rebuild costs a generation run. Only a real change earns one.
- Read a stored artifact before re-crawling.
- Do work where the files are. Staging a file into a cloud copy to read or edit
  it is the expensive mistake.
- Ask once, rather than building the wrong thing twice.

## Verification, which is the whole game

Apply the wiring check (`docs/wiring-check.md`) before reporting anything as
done. Specifically:

- Never report a fix on the strength of a passing test. Report it on the
  strength of having watched the real system produce the right value.
- When something cannot be verified in the session, say which step was skipped.
- If an earlier claim in the conversation turns out to be wrong, correct it
  explicitly. This has happened more than once here — a "fabrication" that was
  real, an "unwired" path that was wired — and saying so plainly is worth more
  than being consistent.

## Code

- Comments explain why, in full sentences, and usually name the bug that forced
  the shape of the code. Read `app/workbench/extract.py` before writing any.
- Tests are sentences. The docstring says what breaks in the real world.
- Old code is archived, never deleted.
- One responsive page; never a separate mobile and desktop design.
- Additive migrations only.

## The environment, if you are not running on his machine

- The project needs Python 3.11 or newer; `.venv` holds macOS binaries.
- A Linux sandbox reaching the files over a bridge can build its own
  environment: `uv python install 3.11`, `uv venv ~/vx`, then
  `VIRTUAL_ENV=~/vx uv pip install -e ".[dev]"`. Keep it outside the project
  folder. Note that an editable install writes `local_web_outreach.egg-info/`
  into the repository.
- A shell reaching the files over a bridge cannot delete anything and usually
  cannot reach a client's website. Long test runs exceed the per-command time
  limit; split them by directory.
- `make check` on his own machine is the real gate, because it runs the
  versions he ships with.
