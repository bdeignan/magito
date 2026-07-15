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

**Right-size first — skip the fan-out for trivial diffs.** If the diff is small and low-risk — roughly under 30 changed lines, or docs/comments-only with no code or logic change — don't spawn the two sub-agent axes. Do a single lightweight inline review instead: read the diff, check it against the obvious conventions and its stated intent, and report in one pass. This is a judgment call, not a hard gate: if a small diff still carries real risk — it touches a hook, the review/merge gate, security, or a data boundary — run the full two axes anyway. When you take this path, present the report as one `## Review (lightweight)` section instead of the two axes, and never present it as if the two axes ran and passed.

If sub-agents are available, spawn both in parallel so they don't pollute each other's context; otherwise run them in sequence. Give each the diff command, the commit list, and its sources.

**Timebox and fallback for stalled axes:** Give each sub-agent axis a reasonable timebox, roughly 5–15 minutes depending on diff size and network latency. Treat an axis as stalled if it produces no output within that window. Stop waiting and run that axis inline in your own context instead. Say so at the time, not only in the final report. Disclose the fallback in the report too: mark the axis as `inline` rather than `sub-agent`. A fallback is not a failure. It's a pragmatic substitution that keeps the review moving. If the inline attempt also produces no meaningful output after a reasonable effort, mark that axis as `none` in the report. An axis with no result must never be reported as passed.

- **Standards brief**: "Every place the diff violates a documented standard — cite the file and the rule. Separate hard violations from judgement calls. Skip anything tooling enforces. Flag tests that mock the seam under test or assert on implementation details. Under 400 words."
- **Spec brief**: "(a) requirements the spec asked for that are missing or partial; (b) behavior not asked for (scope creep); (c) requirements that look implemented but wrong. Quote the spec line for each finding. Under 400 words."

## 4. Report

Present under `## Standards` and `## Spec`, verbatim or lightly cleaned. Do **not** merge or rerank across axes. End with a one-line count per axis and the worst issue *within* each — never a single cross-axis winner. That reranking is exactly what the separation exists to prevent.

**Per-axis provenance:** Each axis heading must be labeled with its provenance — where the output came from. Use one of three tags:
- **`(sub-agent)`** — the axis was run by a sub-agent and produced output.
- **`(inline)`** — the sub-agent stalled or failed, so you ran the axis inline (in this session) as a fallback.
- **`(none)`** — the axis produced no meaningful output (either the sub-agent stalled and the inline fallback produced nothing, or the axis was not run at all).
- **`(lightweight)`** — the diff was trivial/low-risk, so the two-axis fan-out was skipped (per the right-size note in section 3) in favor of a single inline review, reported as one `## Review (lightweight)` section. This is a disclosed substitution — never present it as the two axes having passed.

**Invariant:** An axis with provenance `(none)` must **never** be reported as passed or omitted. If an axis returns no result, explicitly say so: "Standards (none): No output — this axis could not be evaluated." This prevents silent gaps from appearing as if they passed review.

Then record that the review happened, so tooling (e.g. a merge/PR gate) can verify it — the marker pins the review to this branch at this exact commit; any later commit makes it stale and the gate will ask for a re-review.

```bash
d="$(git rev-parse --git-common-dir)/magito" && mkdir -p "$d" && git rev-parse HEAD >| "$d/reviewed-$(git rev-parse --abbrev-ref HEAD | tr '/' '-')"
```

(`>|` forces the overwrite even under zsh's `noclobber`, so a re-review can refresh an existing marker.)
