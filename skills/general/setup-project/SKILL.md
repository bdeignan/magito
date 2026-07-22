---
name: setup-project
description: Configure a repo for the MAGITO workflow — set its issue tracker (GitHub or local) and Python toolchain conventions (uv, pytest, src/ layout), writing the per-repo config the workflow skills read. Run once per project.
disable-model-invocation: true
---

# Setup Project

Scaffold the per-repo configuration the workflow skills assume. Prompt-driven, not a script: explore, present what you found, confirm, then write. Walk the two sections **one at a time** — don't dump both at once.

## 1. Explore

Read the starting state; don't assume. `git remote -v` (is this GitHub?), `CLAUDE.md`/`AGENTS.md`, `CONTEXT.md`, `docs/adr/`, `pyproject.toml`, `.scratch/`, and any existing `## Agent workflow` block.

## 2. Section A — Issue tracker

Where issues live; `to-issues`, `implement-issue`, and `reviewing-changes` read this to know whether to call `gh` or write files.

- **GitHub** — the `gh` CLI against the repo's Issues (propose this if a remote points at GitHub).
- **Local markdown** — issues as files under `.scratch/<feature>/` (good for solo or remote-less repos).

## 3. Section B — Python toolchain

The conventions `implement-issue` and `verifying` build to. Defaults, overridable per project:

- **uv** for environment and dependency management; the **uv build backend**.
- **`src/` layout** — the package under `src/<pkg>/`.
- **pytest**, tests under `tests/`.
- **ruff** for lint/format; **prek** (not pre-commit) runs the hooks.

Templates live in [references/](./references/) — copy and adapt, never regenerate freehand: fill `{{package}}`/`{{project}}`/`{{description}}`, drop pieces the user declines. For a project that already has one of these files, diff the template against the existing file and propose the diff — never overwrite. After scaffolding a fresh project, verify: `uv sync && uv run pytest` must pass on the skeleton.

## 4. Confirm and write

Show a draft, let the user edit, then write:

- An `## Agent workflow` block in whichever of `CLAUDE.md` / `AGENTS.md` already exists — edit that one; never create the other alongside it; if neither exists, ask which to create. The block records the issue-tracker choice and the toolchain conventions in a few lines.
- If the user chose local issues, create `.scratch/` with a short `README.md` describing the convention.
- Run `git config magito.reviewGate true` — opts the repo into the merge/PR review gate; where the tool supports hooks, landing work on the base branch is blocked unless a fresh `reviewing-changes` marker exists.
- If this repo merges into a trunk other than its GitHub default branch (e.g. a `develop`-based migration workflow), also run `git config magito.baseBranch <branch>` — do NOT set this by default.

Tell the user which skills now read this config, and that they can edit the block directly later — re-run this skill only to switch trackers or restart.
