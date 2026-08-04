---
name: setup-project
description: Configure a repo for the MAGITO workflow — set its issue tracker (GitHub or local) and Python toolchain conventions (uv, pytest, src/ layout), writing the per-repo config the workflow skills read. Run once per project.
disable-model-invocation: true
---

# Setup Project

Scaffold the per-repo configuration the workflow skills assume. Prompt-driven, not a script: explore, present what you found, confirm, then write. Walk the three sections **one at a time** — don't dump them all at once.

## 1. Explore

Read the starting state; don't assume. `git remote -v` (is this GitHub?), `CLAUDE.md`/`AGENTS.md`, `docs/agents/GLOSSARY.md`, `docs/agents/issue-tracker.md` (a tracker already configured — diff against it, don't overwrite), `docs/adr/`, `pyproject.toml`, `.scratch/`, and any existing `## Agent workflow` block. Also note whether `docs/agents/` already exists (and which of its files), and whether `CLAUDE.md` already imports `@docs/agents/INDEX.md` — so Section C can diff rather than overwrite, and never add a duplicate import.

## 2. Section A — Issue tracker

Where work is tracked. Skills never name a backend — `catch-up`, `to-issues`, `implement`, `handoff`, and `reviewing-changes` name an **operation** ("list open tickets", "fetch a ticket") and read `docs/agents/issue-tracker.md` to find out how to perform it here. This section writes that file.

Offer three choices:

- **GitHub** — the `gh` CLI against the repo's Issues. Propose this if a remote points at GitHub.
- **Local markdown** — tickets as files under `.scratch/<feature>/` (good for solo or remote-less repos).
- **Something else** — Jira, Linear, Beads, a wiki, a spreadsheet. Ask the user to describe the workflow in a paragraph; you record it as prose under the same operation headings. No new code, no new script branch.

Write `docs/agents/issue-tracker.md` from the matching template in [references/](./references/) — `issue-tracker-github.md.template`, `issue-tracker-local.md.template`, or `issue-tracker-other.md.template` for the third case. Create `docs/agents/` if it doesn't exist; this file is written whether or not the user accepts Section C, because every workflow skill depends on it. If the repo already has one, diff and propose — never overwrite.

The **other** template doubles as the canonical list of the named operations. Fill every heading from the user's description and delete none of them: an operation their tracker can't do says **not supported here** and names what a skill should do instead, which is what stops a skill guessing. Adding or renaming a heading there means changing the GitHub and local templates to match.

## 3. Section B — Python toolchain

The conventions `implement` and `verifying` build to. Defaults, overridable per project:

- **uv** for environment and dependency management; the **uv build backend**.
- **`src/` layout** — the package under `src/<pkg>/`.
- **pytest**, tests under `tests/`.
- **ruff** for lint/format; **prek** (not pre-commit) runs the hooks.

Templates live in [references/](./references/) — copy and adapt, never regenerate freehand: fill `{{package}}`/`{{project}}`/`{{description}}`, drop pieces the user declines. For a project that already has one of these files, diff the template against the existing file and propose the diff — never overwrite. After scaffolding a fresh project, verify: `uv sync && uv run pytest` must pass on the skeleton.

## 4. Section C — Agent docs (`docs/agents/`)

Offer a `docs/agents/` context layer: the version-controlled home for project context an agent can't cheaply rederive from code, governed by a two-gate filter — content earns a place only if it is **non-rederivable** from the code AND **stable** across refactors. Only four files are scaffolded; the rest grow lazily as real content arrives.

Templates live in [references/](./references/) — copy and adapt, fill `{{project}}`, never regenerate freehand; for a repo that already has `docs/agents/`, diff each template against the existing file and propose the diff — never overwrite (same rule as the Python templates above). Scaffold exactly these four:

- `docs/agents/README.md` — the convention manifest (read once).
- `docs/agents/INDEX.md` — the routing table and auto-load entry point.
- `docs/agents/OVERVIEW.md` — intent-only stub; fill purpose / approach / rejected alternatives with the user, or leave the italic prompts for them (half-page cap).
- `docs/agents/GLOSSARY.md` — header only; add no invented terms.

Do NOT create `CONVENTIONS.md`, `GOTCHAS.md`, or `flows/` — those are pulled into existence by real content later, never scaffolded empty.

`docs/agents/issue-tracker.md` is not part of this scaffold — Section A already wrote it, as real content rather than an empty template. Add a routing row for it to `INDEX.md`: `| Where work is tracked, and how to perform a tracker operation | [issue-tracker.md](./issue-tracker.md) |`.

Wire the auto-load bundle with the same "whichever of `CLAUDE.md` / `AGENTS.md` exists" rule as the workflow block: `CLAUDE.md` is import-capable — add the single line `@docs/agents/INDEX.md`; `AGENTS.md` is not — give it the prose pointer `` Project agent docs live in `docs/agents/`; start with `INDEX.md`. `` If both exist, the import goes in `CLAUDE.md` and the pointer in `AGENTS.md`. If neither exists, the import (or pointer) rides on whichever file you create in the next section.

## 5. Confirm and write

Show a draft, let the user edit, then write:

- An `## Agent workflow` block in whichever of `CLAUDE.md` / `AGENTS.md` already exists — edit that one; never create the other alongside it; if neither exists, ask which to create. The block records the toolchain conventions in a few lines, and names the tracker in one line pointing at `docs/agents/issue-tracker.md` — a summary, never a second copy of the operations.
- `docs/agents/issue-tracker.md`, from Section A.
- If the user chose local markdown, create `.scratch/` with a short `README.md` pointing at `docs/agents/issue-tracker.md` for the conventions.
- Run `git config magito.reviewGate true` — opts the repo into the merge/PR review gate. The gate applies only to branches the `/implement` fan-out created, since those alone carry a review-decision marker (ADR 0014); work done by hand lands with no gate. On a marked branch, landing is blocked until a fresh decision is recorded — a completed review, or a deliberate skip with a reason.
- Ensure `.magito/` is present in `.git/info/exclude` — append it if absent (never `.gitignore`, which is shared and this is personal state): `e="$(git rev-parse --git-common-dir)/info/exclude" && { grep -qxF '.magito/' "$e" 2>/dev/null || echo '.magito/' >> "$e"; }` (via `--git-common-dir`, since inside a linked worktree `.git` is a file, not a directory). Both the session journal and the review-decision marker write there.
- If this repo merges into a trunk other than its GitHub default branch (e.g. a `develop`-based migration workflow), also run `git config magito.baseBranch <branch>` — do NOT set this by default.
- If the user accepted Section C, scaffold the four `docs/agents/` files, add the `@docs/agents/INDEX.md` import (or the `AGENTS.md` pointer), and give `INDEX.md` its `issue-tracker.md` routing row.

Tell the user which skills now read this config, and that they name operations rather than backends — so switching trackers later means rewriting one file, not editing every skill. If you scaffolded `docs/agents/`, name the four files created, note that the auto-load bundle (INDEX + OVERVIEW + GLOSSARY) now loads via the `@-import`, and that `CONVENTIONS.md` / `GOTCHAS.md` / `flows/` grow lazily as real content arrives. They can edit any of it directly later — re-run this skill only to switch trackers or restart.
