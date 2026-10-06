# Ponytail: less code from agents

Status: accepted · Opened: 2026-10-06 · Accepted: 2026-10-06

## Problem

Agents over-build. They add abstractions with one caller, scaffolding "for later," new
dependencies for what a few lines can do, and custom code for what the standard library
already does. More code is more to read and more to maintain. Training data makes this
worse: agents copy patterns that were common, not patterns that are lean.

magito's shared instructions say "Prefer the simplest thing that works. Resist premature
abstraction." That is one line. `decruft` reviews for over-building, but only after the
fact. Nothing in `implement`, the executor agent, or the review briefs gives the builder a
concrete procedure for writing less.

Ponytail (`inspo/repos/ponytail`) is a "lazy senior developer" prompt. Before writing code,
it climbs a ladder and stops at the first rung that holds: does this need to exist, is it
already in the codebase, does the standard library do it, does a native platform feature
cover it, does an installed dependency solve it, can it be one line, and only then the
minimum code. It ships as a plugin or rules file for many agents, including all five tools
magito installs into. It also ships five companion skills (review, audit, debt, gain, help).

The user wants ponytail's philosophy to be the core of code built during the software
lifecycle. Installing the plugin alongside magito could be preferable to adopting it
natively: less to maintain, and updates arrive upstream.

## Proposed outcome

Every agent magito configures climbs ponytail's ladder before it writes code, and
`implement`'s review blocks the two objective kinds of over-building.

- `shared/SYSTEM-INSTRUCTIONS.md`, "Engineering": the line "Prefer the simplest thing that
  works. Resist premature abstraction." is replaced by ponytail's ladder (does it need to
  exist; is it already in this codebase; the standard library; a native platform feature;
  an installed dependency; one line; only then the minimum code), the rule that the ladder
  runs after the problem is understood, the bug-fix rule, and the "never simplify away"
  list (input validation at trust boundaries, error handling that prevents data loss,
  security, accessibility, anything explicitly requested). About 20 lines, in magito's
  voice.
- `skills/general/decruft/SKILL.md` gains the six finding tags and what each one names.
- `skills/general/implement/references/worker-contract.md` gains one standing reviewer
  rule: `reuse` and `stdlib` findings can be a `VERDICT FIX` when they name the existing
  path or function; the other four tags are NOTEs.

Done when: the shared instructions carry the ladder and its exceptions in place of the old
line; `decruft` reports findings with the six tags; the reviewer brief carries the new rule;
and `bash scripts/check.sh` passes.

## Decisions so far

- This is its own intent, separate from the Python rules (intent 0009). Code-size rules
  apply in any language and ship independently.
- **Native adoption, only the parts that fit. No plugin.**
  - `shared/SYSTEM-INSTRUCTIONS.md` gets ponytail's ladder, its "never simplify away" list,
    and its bug-fix rule (check every caller, fix the shared function once), rewritten in
    magito's voice. They replace the one line "Prefer the simplest thing that works. Resist
    premature abstraction." That file is every tool's instruction file, so the rules reach
    all five tools, the executor subagent, and headless workers.
  - `decruft` gains ponytail-review's six finding tags: `delete`, `stdlib`, `native`,
    `reuse`, `yagni`, `shrink`.
  - Left out: the persona, the lite/full/ultra levels, the "code first, at most three
    lines" output rule, the test rule, the five companion skills, and the plugin.
  - Why not the plugin: in Claude Code it injects its whole prompt, output rule included,
    into every subagent (the executor, reviewers, Explore), where the output rule fights
    pull request bodies and review reports. Its levels and flag files add a mode the agent
    must track, and it nudges a statusline setup. Upstream updates are the cost; the churn
    is in its per-tool hook layer, and the ladder itself is short and stable.
- **`verifying` wins on tests.** Ponytail's test rule is left out, so the conflict with
  `verifying` does not arise.
- **`implement`'s review checks for over-building, split by tag.** One new standing rule in
  the reviewer brief (`skills/general/implement/references/worker-contract.md`, "Reviewer
  replies in a run"):
  - `reuse` and `stdlib` can be a `VERDICT FIX`: the change duplicates code already in the
    repo, or adds a dependency for what the standard library does. The finding must name
    the existing path or the standard-library function, so the builder can verify it.
  - `delete`, `native`, `yagni`, and `shrink` are always a NOTE. They are taste, and
    letting taste block repeats the five-round review chase the journal recorded on #229.
- **The rules are rewritten in magito's voice, not pasted.** The shared instructions follow
  the user's voice rules (no contractions, plain words, no persona). The source and its
  MIT license are credited in this doc and in the commit message, not in the instruction
  file, where a credit line would cost tokens on every session.
- **No shortcut-comment convention.** Ponytail's `ponytail:` comment is left out. A comment
  that names a known limit is ordinary good commenting, and the convention only pays off
  with `ponytail-debt`, which is not adopted.

## Affected users and systems

- The user, building with agents across Claude Code, Codex, and other tools.
- If adopted natively: `shared/SYSTEM-INSTRUCTIONS.md`, the `implement` skill, the executor
  agent, the review briefs, `decruft`, and `verifying`.
- If installed as a plugin: each tool's plugin setup, outside magito.

## Out of scope

- Python tooling choices. That is intent 0009.

## Constraints

- magito installs into five tools. Anything adopted has to work in each, or degrade cleanly.
- Hooks are optional insurance, never the floor (ADR 0012).

## Open questions

_None._

## Research findings (2026-10-06)

Read in the ponytail source unless marked as inferred.

- **What the plugin adds over plain text:** In Claude Code, Node hooks put the ponytail
  prompt in at every session start, resume, clear, and compact, and into **every subagent**
  through a `SubagentStart` hook. They also track `lite`, `full`, and `ultra` levels, write
  flag files, and once nudge the agent to offer a statusline setup. Codex gets the same
  hooks once trusted. Gemini CLI and Antigravity get always-on `AGENTS.md` text only. omp
  runs a pi extension that adds the rules every turn.
- **It reaches magito's workers:** `claude -p` loads user plugins, so the `claude` workers
  get it. `SubagentStart` reaches the executor unless `PONYTAIL_SUBAGENT_MATCHER` excludes
  it. Whether `codex exec` runs the hooks is inferred, not checked.
- **Conflicts with magito:**
  - The Output rule ("code first, then at most three short lines") competes with the pull
    request body ("Chose X over Y because Z") and with structured review reports, because a
    skill asks for those, not the user.
  - The test rule ("one runnable check, no frameworks, no fixtures") contradicts
    `verifying` on any data or pipeline work.
  - "ACTIVE EVERY RESPONSE," levels, and flag files are a new concept the agent must hold.
    That works against magito's rule of staying in the background.
  - `ponytail-review` and `ponytail-audit` overlap `decruft`.
- **Maintenance:** MIT license, one author, 311 commits since 2026-06-12, three releases on
  2026-10-05 alone. Many commits fix specific hosts, so the hook layer churns.
- **Benchmark:** Haiku 4.5 only, 4 runs, 12 small tickets. The headline 54% is summed
  lines, dominated by two front-end tasks where a native `<input>` replaced a component.
  Averaged per task it is about 35%. Feature correctness was not checked: a task scored as
  correct if it added any lines.
- **Worth keeping:** the ladder, the "not lazy about" list, the bug-fix rule (fix the
  shared function once, after checking every caller), and maybe the `ponytail:` comment for
  a deliberate shortcut. The six review tags (`delete`, `stdlib`, `native`, `reuse`,
  `yagni`, `shrink`) could fold into `decruft`. `ponytail-gain` and `ponytail-help` add
  nothing.
- **Researcher's recommendation:** a mix that leans native. Write the ladder and the "not
  lazy about" list into `shared/SYSTEM-INSTRUCTIONS.md`, without the persona, levels,
  Output rule, or test rule. Extend `decruft` with the six tags. Do not install the plugin.
