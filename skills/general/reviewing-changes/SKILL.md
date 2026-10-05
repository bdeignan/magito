---
name: reviewing-changes
description: Reviews a diff against a fixed point along two independent axes — Standards (does it follow the repo's documented conventions, domain language, and ADRs?) and Spec (does it faithfully implement the originating issue or PRD?). Runs the axes as parallel sub-agents when available and reports them side by side without reranking. Use on work done outside `implement` — a hand edit or quick fix before its PR, someone else's branch or PR, or changes made to address review feedback — or whenever asked to review a branch, diff, or work in progress. Do not use it inside an `implement` run: `implement` has its own review by another model family, and this review does not count toward that branch's review record.
---

# Reviewing Changes

Two-axis review of the diff between `HEAD` and a fixed point. The axes stay separate so neither masks the other: code can follow every standard yet build the wrong thing (Standards pass, Spec fail), or do exactly what was asked while breaking conventions (Spec pass, Standards fail).

## 1. Pin the fixed point

Whatever the user names — a SHA, branch, tag, `main`, `HEAD~5`. If none is given, ask. Confirm it resolves (`git rev-parse`) and the diff is non-empty *before* fanning out — a bad ref should fail here, not inside a sub-agent.

Capture once: `git diff <fixed-point>...HEAD` (three-dot, against the merge-base) and `git log <fixed-point>..HEAD --oneline`.

## 2. Find the sources

- **Spec** — the originating ticket, a path the user passed, or a PRD under `docs/` (or the intent doc under `docs/intent/` that a ticket links to; a local-markdown ticket's directory name starts with that intent's number). Find the ticket by scanning the commit messages for the identifier form `docs/agents/issue-tracker.md` describes (`#123`, `Closes #45`, `PROJ-88`, a file path), then use that file's **fetch a ticket** operation to read it. If there is none, the Spec axis reports "no spec available."
- **Standards** — do not gather these by hand. Run `python3 <skills>/implement/scripts/worker.py standards <fixed-point>` once, and give its whole output to the Standards axis. It lists the standards docs, the ADRs that bear on the changed files, and the doc lines that name something the diff removed or renamed. `<skills>` is your tool's installed skills directory, as in `implement`.

## 3. Run the two axes

**Right-size first — skip the fan-out for trivial diffs.** If the diff is small and low-risk — roughly under 30 changed lines, or docs/comments-only with no code or logic change — do not spawn the two sub-agent axes. Do a single lightweight inline review instead: read the diff, check it against its stated intent, run the command from section 2 and follow `<skills>/implement/references/standards-review.md` inline for its standards, and report in one pass. This is a judgment call, not a hard gate: if a small diff still carries real risk — it touches a hook, the review/merge gate, security, or a data boundary — run the full two axes anyway. When you take this path, present the report as one `## Review (lightweight)` section instead of the two axes, and never present it as if the two axes ran and passed.

If sub-agents are available, spawn both in parallel so they do not pollute each other's context; otherwise run them in sequence. Give each the diff command, the commit list, and its sources.

**Timebox and fallback for stalled axes:** Give each sub-agent axis a reasonable timebox, roughly 5–15 minutes depending on diff size and network latency. Treat an axis as stalled if it produces no output within that window. Stop waiting and run that axis inline in your own context instead. Say so at the time, not only in the final report. Disclose the fallback in the report too: mark the axis as `inline` rather than `sub-agent`. If the inline attempt also produces no meaningful output after a reasonable effort, mark that axis as `none` in the report. An axis with no result must never be reported as passed.

- **Standards brief**: "Follow the procedure in `<skills>/implement/references/standards-review.md`: its reviewer's steps and its rules on which source wins. Use the `worker.py standards` output below as your only list of docs and doc lines, even when its last two sections say `None.`. Report each blocking finding in one of the two forms that file gives, and list everything else as a note. Under 500 words."
- **Spec brief**: "(a) requirements the spec asked for that are missing or partial; (b) behavior not asked for (scope creep); (c) requirements that look implemented but wrong. Quote the spec line for each finding. Under 400 words."

## 4. Report

Present under `## Standards` and `## Spec`, verbatim or lightly cleaned. Under `## Standards`, each finding keeps one of the two forms from `standards-review.md`, and other remarks are listed as notes. Do **not** merge or rerank across axes. End with a one-line count per axis and the worst issue *within* each — never a single cross-axis winner. That reranking is exactly what the separation exists to prevent.

**Per-axis provenance:** Each axis heading must be labeled with its provenance — where the output came from. Use one of three tags:
- **`(sub-agent)`** — the axis was run by a sub-agent and produced output.
- **`(inline)`** — the sub-agent stalled or failed, so you ran the axis inline (in this session) as a fallback.
- **`(none)`** — the axis produced no meaningful output (either the sub-agent stalled and the inline fallback produced nothing, or the axis was not run at all).
- **`(lightweight)`** — the diff was trivial/low-risk, so the two-axis fan-out was skipped (per the right-size note in section 3) in favor of a single inline review, reported as one `## Review (lightweight)` section. This is a disclosed substitution — never present it as the two axes having passed.

**Invariant:** An axis with provenance `(none)` must **never** be reported as passed or omitted. If an axis returns no result, explicitly say so: "Standards (none): No output — this axis could not be evaluated." This prevents silent gaps from appearing as if they passed review.

Then check whether the branch has a review marker. This skill reads the marker and never writes it. Use the two separate reads below, then your file-*reading* tool on the resulting path. Do not compose them into one shell command.

```bash
git rev-parse --abbrev-ref HEAD           # the branch; replace every / with - for the slug
git worktree list --porcelain | head -1   # prints `worktree <path>`
```

Read `<path>/.magito/review-<branch-slug>`.

**No marker file:** you are done, and you create no file. Most reviews end here. Every branch that `implement` builds has a marker (ADR 0014, ADR 0020). A branch with no marker was made outside `implement`, and it meets no gate. Creating a marker here would gate a branch that was never meant to be gated, and the very next commit would block the merge.

**A marker file exists:** `implement` built this branch. Do not write to the file and do not delete it. Tell the user, in one line, that this review does not satisfy the gate, and that `worker.py record` writes this branch's record after the review in steps 6 to 8 of `pipeline.md`. That review is run by a roster worker through `worker.py review`, or by a fresh-context subagent when no roster worker of another family answers. Both paths end in `worker.py record`.
