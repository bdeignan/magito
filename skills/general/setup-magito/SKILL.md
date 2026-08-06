---
name: setup-magito
description: Inventory a repo's MAGITO configuration and fill the gaps in one idempotent pass — issue tracker, review gate and base branch, agent docs, permission allowlist, private-state excludes, the session journal, legacy-note import, delegation and magi rosters, Python toolchain, and stale managed symlinks. Reports each item configured/missing/stale before asking anything, then fills only the gaps. Safe to re-run. Run once per project, and again to change or repair.
disable-model-invocation: true
---

# Setup MAGITO

Bring a repo up to the configuration the MAGITO workflow skills expect — "magito-fy" it. The workflow skills (`catch-up`, `implement`, `to-issues`, `handoff`, `reviewing-changes`, the magi tribunal) assume certain files and settings exist; this skill is the one place that knows the full list and puts it in place.

**Run it to onboard a fresh repo, and re-run it any time to change a choice or repair drift** — it is idempotent, not a one-shot scaffolder. That re-runnability is the point: the model it improves on (Matt Pocock's setup skill) is explicitly *not* re-runnable.

Most of what it touches is **per-repo** (the tracker doc, review gate, `docs/agents/`, permissions, excludes, journal). Two items are **machine-global** and shared across every repo on this machine: `~/.magito/workers.toml` and `~/.magito/bench.toml`. For those it only checks and offers — it configures the project, not your machine.

**Inventory first, then fill gaps.** Read the starting state of every item, report each as **configured / missing / stale**, then walk only the unsettled ones — one section at a time, leading with the recommended answer. Re-running is safe by design: a second run finds everything configured and changes nothing. Never overwrite a user's answer or a user's file without asking.

Prompt-driven, not a script. Explore, present what you found, confirm, then write.

## 1. Inventory (before asking anything)

Read the starting state and classify each item. **Configured** = present and current. **Missing** = not there. **Stale** = present but drifted (an old tracker doc, a dangling symlink, a duplicate import). Show this table first — it is the whole map of what the walk will touch.

| Item | How to check | Where it lives |
|---|---|---|
| Issue tracker | `docs/agents/issue-tracker.md` present? | `docs/agents/issue-tracker.md` (see #112) |
| Review gate + base branch | `git config magito.reviewGate`, `git config magito.baseBranch` | git config |
| Agent docs | `docs/agents/` files + the `@docs/agents/INDEX.md` import | `docs/agents/`, `CLAUDE.md`/`AGENTS.md` |
| Permission allowlist | `.claude/settings.json` — has `allow`, has **no** `hooks` key | `.claude/settings.json` |
| Private-state excludes | `.magito/` and `.scratch/` in `.git/info/exclude` | `.git/info/exclude` |
| Session journal | `.magito/journal/` present (self-creates on first `/handoff`) | `.magito/journal/` |
| Legacy notes to import | scan for pre-magito notes (see §Legacy notes) | repo root, `docs/` |
| Delegation workers | `~/.magito/workers.toml` present | `~/.magito/workers.toml` |
| magi seats | `~/.magito/bench.toml` present | `~/.magito/bench.toml` |
| Python toolchain | `pyproject.toml`, `tests/`, `src/` layout | repo root |
| Managed symlinks | dangling magito-owned links in tool dirs | `~/.magito/bin`, tool skills/agents/hooks dirs |

Read, don't assume: `git remote -v` (is this GitHub?), `CLAUDE.md`/`AGENTS.md`, `docs/agents/` and which files it holds, whether `CLAUDE.md` already imports `@docs/agents/INDEX.md`, `docs/adr/`, `pyproject.toml`, `.scratch/`. A tracker doc or a `docs/agents/` file that already exists is a **diff-and-propose**, never an overwrite.

## 2. Walk the gaps

Take the unsettled items one at a time. Skip anything the inventory settled. For each, lead with the recommended answer and let the user redirect.

### Issue tracker

Where work is tracked. Skills never name a backend — `catch-up`, `to-issues`, `implement`, `handoff`, and `reviewing-changes` name an **operation** ("list open tickets", "fetch a ticket") and read `docs/agents/issue-tracker.md` to find out how to perform it here. This section writes that file.

Offer three choices:

- **GitHub** — the `gh` CLI against the repo's Issues. Propose this if a remote points at GitHub.
- **Local markdown** — tickets as files under `.scratch/<feature>/` (good for solo or remote-less repos).
- **Something else** — Jira, Linear, Beads, a wiki, a spreadsheet. Ask the user to describe the workflow in a paragraph; you record it as prose under the same operation headings, and nothing else has to change to support it.

Write `docs/agents/issue-tracker.md` from the matching template in [references/](./references/) — `issue-tracker-github.md.template`, `issue-tracker-local.md.template`, or `issue-tracker-other.md.template` for the third case. Create `docs/agents/` if it doesn't exist; this file is written whether or not the user accepts the agent-docs section, because every workflow skill depends on it. If the repo already has one, diff and propose — never overwrite.

[`issue-tracker-other-example.md`](./references/issue-tracker-other-example.md) is a worked example of the third case — one paragraph about a fictional Jira setup, and the file it produces. Read it before filling the skeleton freehand.

The **other** template doubles as the canonical list of the named operations. Fill every heading from the user's description and delete none of them: an operation their tracker can't do says **not supported here** and names what a skill should do instead, which is what stops a skill guessing. Adding or renaming a heading there means changing the GitHub and local templates to match.

### Review gate + base branch

- Run `git config magito.reviewGate true` — opts the repo into the merge/PR review gate. The gate applies only to branches the `/implement` fan-out created, since those alone carry a review-decision marker (ADR 0014); work done by hand lands with no gate. On a marked branch, landing is blocked until a fresh decision is recorded — a completed review, or a deliberate skip with a reason.
- If this repo merges into a trunk other than its GitHub default branch (e.g. a `develop`-based migration workflow), also run `git config magito.baseBranch <branch>` — do NOT set this by default.

### Permission allowlist

`.claude/settings.json` (committed) holds a read-only permission allowlist that cuts the approval prompts the workflow raises on every read-only `git` and `gh` call. Two rules, both from `CLAUDE.md`:

- **Permissions only — never a `hooks` key.** A `hooks` key here replaces the user-level hooks for this repo, silently disabling `staging-guard` and `review-gate`. If the file already carries one, flag it; do not add one.
- **Read-only verbs only, and no `deny` block.** `allow` rules merge across scopes, so this file only adds to the user's rules — it never restates them. A `deny` here is a false sense of enforcement, since the hooks are what actually block.

Missing? Offer to write a minimal permissions-only `allow` list for the read-only `git`/`gh` calls the skills use. Present but drifted (a stray `hooks` key, a `deny` block, write verbs)? Report it and propose the correction — never overwrite silently.

### Private-state excludes

Ensure both `.magito/` and `.scratch/` are in `.git/info/exclude` — append each if absent. Never `.gitignore`: that file is shared, and this is personal state. Both the session journal and the review-decision marker write under `.magito/`.

```
e="$(git rev-parse --git-common-dir)/info/exclude"
for p in .magito/ .scratch/; do grep -qxF "$p" "$e" 2>/dev/null || echo "$p" >> "$e"; done
```

(`--git-common-dir`, since inside a linked worktree `.git` is a file, not a directory.)

### Session journal

`.magito/journal/` is where per-session entries land. It self-creates the first time `/handoff` runs `~/.magito/bin/journal name`, so there is nothing to scaffold — it counts as **configured** once `.magito/` is excluded above. If the repo carries pre-magito notes worth keeping, offer to import them (next section).

### Legacy notes

Does this repo carry notes that predate magito? Scan for: an old magito handoff file (`~/.magito/handoffs/<slug>.md`), `NOTES.md`, `TODO.md`, `docs/decisions/`, a `.beads/` database or similar task store — or a system the user names when asked.

If something is found, offer to bring it into the session journal as entries. **The import procedure lives in [`references/importing-legacy-notes.md`](./references/importing-legacy-notes.md) — read it only when the inventory actually finds something.** It is never destructive: originals stay put, the user confirms the mapping before any file is written, entries stay under the journal word cap (the reference points at the live number — don't restate it here), and timestamps come from the source. Found nothing? Skip the section and never open that file.

### Delegation workers and magi seats

`~/.magito/workers.toml` (the `/implement` delegation roster) and `~/.magito/bench.toml` (the magi seat roster) are **the user's machine-local files**. Report each as present or missing. Never write or overwrite either without explicit confirmation (the convention is in `CLAUDE.md`). If one is missing, say so and point at where it bootstraps — `bench.toml` self-creates on the first `/magi` run and is repaired by `/magi config`; `workers.toml` self-creates the first time a worker is named during `/implement`. Offer to seed a missing file only if the user asks; do not fill it silently.

### Python toolchain

The conventions `implement` and `verifying` build to. Defaults, overridable per project:

- **uv** for environment and dependency management; the **uv build backend**.
- **`src/` layout** — the package under `src/<pkg>/`.
- **pytest**, tests under `tests/`.
- **ruff** for lint/format; **prek** (not pre-commit) runs the hooks.

Templates live in [references/](./references/) — copy and adapt, never regenerate freehand: fill `{{package}}`/`{{project}}`/`{{description}}`, drop pieces the user declines. For a project that already has one of these files, diff the template against the existing file and propose the diff — never overwrite. After scaffolding a fresh project, verify: `uv sync && uv run pytest` must pass on the skeleton.

### Managed symlinks

`install.py` links this repo's skills, agents, hooks, and `bin/` into each tool's config dirs. A renamed or deleted skill can leave a **dangling** link behind (the old name still points at a file that's gone). Report any you find as **stale**, and offer to run `python install.py` — which prunes magito-owned dangling links as part of a normal run (`--dry-run` shows what it would remove first). Do not delete links here yourself; `install.py` owns its destinations.

### Agent docs (`docs/agents/`)

Offer a `docs/agents/` context layer: the version-controlled home for project context an agent can't cheaply rederive from code, governed by a two-gate filter — content earns a place only if it is **non-rederivable** from the code AND **stable** across refactors. Only four files are scaffolded; the rest grow lazily as real content arrives.

Templates live in [references/](./references/) — copy and adapt, fill `{{project}}`, never regenerate freehand; for a repo that already has `docs/agents/`, diff each template against the existing file and propose the diff — never overwrite (same rule as the Python templates above). Scaffold exactly these four:

- `docs/agents/README.md` — the convention manifest (read once).
- `docs/agents/INDEX.md` — the routing table and auto-load entry point.
- `docs/agents/OVERVIEW.md` — intent-only stub; fill purpose / approach / rejected alternatives with the user, or leave the italic prompts for them (half-page cap).
- `docs/agents/GLOSSARY.md` — header only; add no invented terms.

Do NOT create `CONVENTIONS.md`, `GOTCHAS.md`, or `flows/` — those are pulled into existence by real content later, never scaffolded empty.

`docs/agents/issue-tracker.md` is not part of this scaffold — the tracker section already wrote it, as real content rather than an empty template. Add a routing row for it to `INDEX.md`: `| Where work is tracked, and how to perform a tracker operation | [issue-tracker.md](./issue-tracker.md) |`.

Wire the auto-load bundle with the same "whichever of `CLAUDE.md` / `AGENTS.md` exists" rule as the workflow block: `CLAUDE.md` is import-capable — add the single line `@docs/agents/INDEX.md`; `AGENTS.md` is not — give it the prose pointer `` Project agent docs live in `docs/agents/`; start with `INDEX.md`. `` If both exist, the import goes in `CLAUDE.md` and the pointer in `AGENTS.md`. If neither exists, the import (or pointer) rides on whichever file you create in the next step.

## 3. Confirm and write

Show a draft, let the user edit, then write only what the inventory marked missing or stale:

- An `## Agent workflow` block in whichever of `CLAUDE.md` / `AGENTS.md` already exists — edit that one; never create the other alongside it; if neither exists, ask which to create. The block records the toolchain conventions in a few lines, and names the tracker in one line pointing at `docs/agents/issue-tracker.md` — a summary, never a second copy of the operations.
- `docs/agents/issue-tracker.md`, from the tracker section.
- If the user chose local markdown, create `.scratch/` with a short `README.md` pointing at `docs/agents/issue-tracker.md` for the conventions.
- The review-gate, base-branch, and exclude git commands above.
- The `.claude/settings.json` permission allowlist, if it was missing or drifted — permissions only, no `hooks` key, no `deny` block.
- If the user accepted the agent-docs section, scaffold the four `docs/agents/` files, add the `@docs/agents/INDEX.md` import (or the `AGENTS.md` pointer), and give `INDEX.md` its `issue-tracker.md` routing row.

Close by telling the user what changed and what was already fine. Name the skills that read this config, and that they name operations rather than backends — so switching trackers later means rewriting one file, not editing every skill. If you scaffolded `docs/agents/`, name the four files, note that the auto-load bundle (INDEX + OVERVIEW + GLOSSARY) loads via the `@-import`, and that `CONVENTIONS.md` / `GOTCHAS.md` / `flows/` grow lazily. Everything here is editable directly later — and this skill is safe to re-run any time, to change a choice or repair drift.
