---
name: to-issues
description: Break a plan, spec, or conversation into independently-grabbable issues using vertical slices, and publish them to the project's issue tracker (GitHub or local).
disable-model-invocation: true
---

# To Issues

Break a plan into independently-grabbable issues, each a **tracer bullet**: a thin vertical slice that cuts end-to-end through every layer it touches, not a horizontal slice of one. The issue tracker (GitHub via `gh`, or local markdown under `.scratch/`) is declared in the per-repo config — run `/setup-project` if it's missing.

## Process

1. **Gather context.** Work from the conversation. If the user passes an issue reference, fetch its body and comments.

2. **Explore (optional).** If you haven't, read the code to ground titles and descriptions in the project's domain glossary; respect ADRs in the area. Look for prefactoring that makes the change easy — "make the change easy, then make the easy change."

3. **Draft vertical slices.** Each slice delivers a narrow but COMPLETE path through every layer it touches and is verifiable on its own. For data/ML work the layers are typically **ingest → transform → feature → model → eval → artifact**, not schema/API/UI — slice through those end-to-end (e.g. "one feature computed, validated, and surfaced in the eval report"), never "build all the transforms." Prefactoring goes first.

4. **Quiz the user.** Present the breakdown as a numbered list — for each slice: **Title**, **Blocked by**, and **Covers** (which goals or user stories). Ask: is the granularity right (too coarse / too fine)? Are the dependencies correct? Should any be merged or split? Iterate until approved.

5. **Publish.** In dependency order (blockers first, so you can cite real identifiers), create each issue via the configured tracker using the template below. Mark them ready for an agent unless told otherwise. For a large body of work, optionally open one parent issue holding the problem statement and goals, and reference it from each slice.

<issue-template>
## What to build

The end-to-end behavior of this slice — not a layer-by-layer plan. Avoid file paths and code snippets; they go stale. (Exception: a small schema, type, or state-machine snippet that pins a decision more precisely than prose can.)

## Acceptance criteria

- [ ] ...

## Blocked by

The blocking issue, or "None — can start immediately."
</issue-template>

Do not close or modify any parent issue.
