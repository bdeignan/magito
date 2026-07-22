---
name: to-issues
description: Break a plan, spec, or conversation into independently-grabbable issues using vertical slices, and publish them to the project's issue tracker (GitHub or local).
disable-model-invocation: true
---

# To Issues

Break a plan into independently-grabbable issues, each a **tracer bullet**: a thin vertical slice that cuts end-to-end through every layer it touches, not a horizontal slice of one. The issue tracker (GitHub via [`implement-issue/scripts/issues.sh`](../implement-issue/scripts/issues.sh), or local markdown under `.scratch/`) is declared in the per-repo config — run `/setup-project` if it's missing.

## Write for a less-capable implementer

Assume the agent that picks up each issue is weaker than the one writing it — less taste, less judgement, no memory of this conversation. The issue body must carry everything:

- Spell out the full deliverable in the body. If the issue asks for a document, config, or skill, include the complete text to write (or an exact copy-from path) — never "write something like X".
- Links are background only. Everything needed to build must be in the body; a link may corroborate a decision, never substitute for its content.
- Exact commands over descriptions: "run `python install.py`", not "reinstall".
- Decisions are made here, not downstream. If a choice is still open, resolve it with the user before publishing — an issue containing an open question is not ready.
- Acceptance criteria must be checkable by a weak agent: observable behavior, file contents, command output — never "code is clean" or "works well".
- Write the body in Simple English: short sentences, one idea each, the plainest common word that fits. Keep technical identifiers exact — never rename `clock_in` or `PRAGMA foreign_keys` to sound simpler; define them in plain words instead. This lowers the reading level for a weaker implementer without losing precision. It governs word choice and sentence length, not structure — keep the labeled headings and the checkbox acceptance criteria.

## Process

1. **Gather context.** Work from the conversation. If the user passes an issue reference, fetch its body and comments.

2. **Explore (optional).** If you haven't, read the code to ground titles and descriptions in the project's domain glossary; respect ADRs in the area. Look for prefactoring that makes the change easy — "make the change easy, then make the easy change."

3. **Draft vertical slices.** Each slice delivers a narrow but COMPLETE path through every layer it touches and is verifiable on its own. For data/ML work the layers are typically **ingest → transform → feature → model → eval → artifact**, not schema/API/UI — slice through those end-to-end (e.g. "one feature computed, validated, and surfaced in the eval report"), never "build all the transforms." Prefactoring goes first. **Every slice needs at least one invariant or edge-case AC** grounded in the data/behavior it touches — data boundaries (schema: columns/dtypes/nullability; value ranges; NaN/inf policy; row counts / key uniqueness; train-test leakage) or behavioral edges (empty input, boundary values at every bin/threshold edge, duplicates). Happy-path-only ACs are incomplete — flag it now, don't publish it. Before finalizing each AC, check it against the repo's domain contract — the invariants and definitions written down in `CONTEXT.md` or an equivalent glossary. If an AC asks to re-validate an invariant the contract already guarantees downstream, don't write it. Cite the contract line instead. That's the **redundant re-validation** anti-pattern: an AC that checks something already proven true elsewhere, splitting the same guarantee across spec and review without adding safety. If the repo has no domain contract, say so in the draft — "no contract found — ACs unverified against domain" — and never invent one.

4. **Quiz the user.** Present the breakdown as a numbered list — for each slice: **Title**, **Blocked by**, and **Covers** (which goals or user stories). Ask: is the granularity right (too coarse / too fine)? Are the dependencies correct? Should any be merged or split? Iterate until approved.

5. **Publish.** In dependency order (blockers first, so you can cite real identifiers), create each issue via the configured tracker — `bash implement-issue/scripts/issues.sh create "<title>" "<body>"` in GitHub mode, or a new file under `.scratch/` in local mode — using the template below. Mark them ready for an agent unless told otherwise. **Parent spec (optional).** If the breakdown produced 4+ slices, or the user asks for an epic, offer to publish the spec as a parent issue first, using the template below. Create the parent, then each slice, then link every slice as a native GitHub sub-issue of the parent: `bash implement-issue/scripts/issues.sh sub-add <parent-number> <child-number>`. In local mode, write the spec to `.scratch/<feature>/SPEC.md` and list the ticket files under it. The chain stays optional — small work skips the spec entirely, and nothing downstream requires one to exist.

<issue-template>
## What to build

The end-to-end behavior of this slice — not a layer-by-layer plan. Avoid file paths and code snippets; they go stale. (Exception: a small schema, type, or state-machine snippet that pins a decision more precisely than prose can.)

## Acceptance criteria

- [ ] ...

**Invariants / edge cases** (at least one)
- [ ] ...

## Blocked by

The blocking issue, or "None — can start immediately."
</issue-template>

<spec-template>
## Problem

The problem being solved, from the user's perspective — a paragraph, not user stories.

## Approach

The chosen solution in a few sentences, plus alternatives rejected and why (one line each).

## Decisions

Implementation decisions already made while shaping: modules touched, interfaces, schema changes, contracts. Same snippet rule as slices: no file paths or code, unless a small snippet pins a decision more precisely than prose.

## Testing

What makes a good test for this work; which seams get tested; prior art in the codebase.

## Out of scope

Explicit non-goals.

## Slices

Tracked as sub-issues — GitHub renders progress on the parent automatically.
</spec-template>

Do not close or modify any parent issue.
