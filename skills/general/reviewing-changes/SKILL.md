---
name: reviewing-changes
description: Reviews a diff against a fixed point along two independent axes — Standards (does it follow the repo's documented conventions, domain language, and ADRs?) and Spec (does it faithfully implement the originating issue or PRD?). Runs the axes as parallel sub-agents when available and reports them side by side without reranking. Use before opening a PR, when addressing review feedback, or when asked to review a branch, diff, or work in progress.
---

# Reviewing Changes

Two-axis review of the diff between `HEAD` and a fixed point. The axes stay separate so neither masks the other: code can follow every standard yet build the wrong thing (Standards pass, Spec fail), or do exactly what was asked while breaking conventions (Spec pass, Standards fail).

## 1. Pin the fixed point

Whatever the user names — a SHA, branch, tag, `main`, `HEAD~5`. If none is given, ask. Confirm it resolves (`git rev-parse`) and the diff is non-empty *before* fanning out — a bad ref should fail here, not inside a sub-agent.

Capture once: `git diff <fixed-point>...HEAD` (three-dot, against the merge-base) and `git log <fixed-point>..HEAD --oneline`.

## 2. Find the sources

- **Spec** — the originating issue (`#123`/`Closes #45` in the commit messages, fetched per the issue-tracker config), a path the user passed, or a PRD under `docs/`/`.scratch/`. If there's none, the Spec axis reports "no spec available."
- **Standards** — `CONTEXT.md` (domain language), `docs/adr/`, `CODING_STANDARDS.md`/`CONTRIBUTING.md`, and the project's declared toolchain conventions.

## 3. Run the two axes

If sub-agents are available, spawn both in parallel so they don't pollute each other's context; otherwise run them in sequence. Give each the diff command, the commit list, and its sources.

- **Standards brief**: "Every place the diff violates a documented standard — cite the file and the rule. Separate hard violations from judgement calls. Skip anything tooling enforces. Flag tests that mock the seam under test or assert on implementation details. Under 400 words."
- **Spec brief**: "(a) requirements the spec asked for that are missing or partial; (b) behavior not asked for (scope creep); (c) requirements that look implemented but wrong. Quote the spec line for each finding. Under 400 words."

## 4. Report

Present under `## Standards` and `## Spec`, verbatim or lightly cleaned. Do **not** merge or rerank across axes. End with a one-line count per axis and the worst issue *within* each — never a single cross-axis winner. That reranking is exactly what the separation exists to prevent.

Then record that the review happened, so tooling (e.g. a merge/PR gate) can verify it — the marker pins the review to this branch at this exact commit; any later commit makes it stale and the gate will ask for a re-review.

```bash
d="$(git rev-parse --git-common-dir)/magito" && mkdir -p "$d" && git rev-parse HEAD > "$d/reviewed-$(git rev-parse --abbrev-ref HEAD | tr '/' '-')"
```
