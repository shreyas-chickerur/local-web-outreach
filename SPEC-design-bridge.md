# Spec: the design bridge

Status: decided 23 September 2026; building. Roadmap phase 3, the half not
built: "Claude Design runs per lead through the Agent SDK, returning HTML to
disk" (`Claude outputs/pivot-to-claude-design-roadmap.pdf`, locked).

## Objective

One command turns a lead and a design prompt into a new version of its site,
with no person writing markup: `make design LEAD=8 PROMPT=prompts/fish-shack/v2.md`.
Today every version of The Heritage Table and Fish Shack was written by hand in
a Claude session and loaded into the database by hand. The bridge makes that a
run with a recorded cost, a recorded prompt, and the checks run on its output.

## How a run works

1. **Workspace.** A fresh folder, `runs/<slug>/<timestamp>/`, holding the
   prompt, the lead's photographs as local files (`photos/0.jpg` …, from the
   paid-once cache in `.cache/photos`), and nothing else.
2. **The agent.** `claude_agent_sdk.query` with `cwd` set to that folder,
   `allowed_tools` of `Read`, `Write`, `Edit` and `Glob` only, and `Bash`,
   `WebFetch` and `WebSearch` denied: it can read the prompt, look at the
   photographs and write `index.html`, and nothing outside the folder.
   `max_budget_usd` and `max_turns` stop a runaway run.
3. **Into the workbench.** Local photo paths are rewritten to
   `/photo/<lead>/<n>?w=1600`, the page is saved with `sites.save` as a new
   version with its parent, and the version's notes record the prompt file and
   its hash, the brief hash, the model, `total_cost_usd`, the number of turns,
   and how the run ended.
4. **The checks.** Run in memory against the brief, and the counts printed. A
   review is opened only when Shreyas opens it on the page, as now.

A run that hits its ceiling or fails saves nothing and says what it spent.

## Producers and consumers, for the wiring check

| Seam | Producer | Consumer |
|---|---|---|
| Prompt | `prompts/<slug>/vN.md` (written from the brief and the playbook) | the agent, read from the workspace |
| Photographs | `app/adapters/photos.fetch` (cached) | the agent as files; the page as `/photo/<lead>/<n>` after rewriting |
| The page | the agent's `index.html` | `sites.save` → the workbench, the checks, the review |
| Cost | `ResultMessage.total_cost_usd` (an estimate) | the version's notes, and the command's output |

## Boundaries

- **Always:** a ceiling on every run; the cost recorded whether it succeeds or not.
- **Ask first:** adding `claude-agent-sdk` as a dependency (this spec asks).
- **Never:** let the agent run commands or reach the network; overwrite a version.

## Out of scope

Publishing to the Claude Design canvas (still done from a session, as for
Fish Shack); writing the prompt itself (still `prompts/<slug>/vN.md`); hosting.

## Decisions (Shreyas, 23 September 2026)

1. **Model:** Claude Opus 5.5 (`claude-opus-5-5`).
2. **Ceiling:** $5 per run (`max_budget_usd=5.0`).
3. **One pass.** No automatic revision; each change Shreyas asks for is its
   own run with a parent.

## Success criteria

- [ ] `make design` on Fish Shack with `prompts/fish-shack/v2.md` produces a new
      version that the workbench serves, with its photographs loading.
- [ ] Its notes carry the cost, the model and the prompt hash.
- [ ] A run given a tiny ceiling stops, saves nothing, and reports what it spent.
- [ ] The agent cannot write outside its workspace (a test proves the options).
- [ ] `make check` passes.
