---
name: setup-magito
description: Audits a repo's MAGITO configuration in one idempotent pass: reports each item as configured, missing, or stale, then fills only the gaps. Use once per new project, or when asked to check or repair its configuration. Safe to re-run. Not part of ordinary session startup, because it asks setup questions nobody requested.
---

# Setup MAGITO

Bring a repo up to the configuration the MAGITO workflow skills expect — "magito-fy" it. The workflow skills (`catch-up`, `implement`, `to-issues`, `handoff`, `reviewing-changes`, the magi tribunal) assume certain files and settings exist; this skill is the one place that knows the full list and puts it in place.

**Run it to onboard a fresh repo, and re-run it any time to change a choice or repair drift.** It is idempotent.

Most of what it touches is **per-repo** (`.magito/config.toml`, the tracker doc, the check command, review gate, `docs/agents/`, permissions, excludes, journal). Two items are **machine-global** and shared across every repo on this machine: `~/.magito/workers.toml` and `~/.magito/bench.toml`. For those it only checks and offers — it configures the project, not your machine.

**Inventory first, then fill gaps.** Read the starting state of every item, report each as **configured / missing / stale**, then walk only the unsettled ones — one section at a time, leading with the recommended answer. Re-running is safe by design: a second run finds everything configured and changes nothing. Never overwrite a user's answer or a user's file without asking.

Prompt-driven. Explore, present what you found, confirm, then write.

## 1. Inventory (before asking anything)

Read the starting state and classify each item. **Configured** = present and current. **Missing** = not there. **Stale** = present but drifted (an old tracker doc, a dangling symlink, a duplicate import). Show this table first — it is the whole map of what the walk will touch.

| Item | How to check | Where it lives |
|---|---|---|
| Config file | `.magito/config.toml` exists and has every key: `mode`, `tracker`, `check`, `intent_dir`, `audited`, `audited_on` | `.magito/config.toml` |
| Mode | `mode` is set to `owner` or `guest`. For a new repo, ask the user once | `.magito/config.toml` |
| Check command | `check` is set and the command exits 0 when run now. If the repo has none, propose one from what exists | `.magito/config.toml` |
| Check command documented | Owner mode: `AGENTS.md`/`CLAUDE.md` names the check command. Guest mode: not required | `AGENTS.md`/`CLAUDE.md` |
| Gemini context | `GEMINI.md` exists, or `.gemini/settings.json` sets `contextFileName` to the repo's instruction file | `GEMINI.md`, `.gemini/settings.json` |
| Guest excludes | Guest mode only: every path this skill created is in `.git/info/exclude` and none shows in `git status` | `.git/info/exclude` |
| Audit version | `audited` matches the current magito commit. If older, newer checklist rows can be unchecked — re-run them | `.magito/config.toml` |
| Issue tracker | `docs/agents/issue-tracker.md` present? | `docs/agents/issue-tracker.md` |
| Review gate + base branch | `git config magito.reviewGate`, `git config magito.baseBranch` | git config |
| Pull request title | Guest mode only: `git config magito.prTitlePattern` is set when the repo's merged pull requests do not use Conventional Commits titles | git config |
| Agent docs | `docs/agents/` files + the `@docs/agents/INDEX.md` import | `docs/agents/`, `CLAUDE.md`/`AGENTS.md` |
| Permission allowlist | Claude Code only: `.claude/settings.json` — has `allow`, has **no** `hooks` key. Elsewhere: `skipped: not Claude Code` | `.claude/settings.json` |
| Private-state excludes | `.magito/` and `.scratch/` in `.git/info/exclude` | `.git/info/exclude` |
| Session journal | `.magito/journal/` present (self-creates on first `/handoff`) | `.magito/journal/` |
| Legacy notes to import | scan for pre-magito notes (see §Legacy notes) | repo root, `docs/` |
| Delegation workers | `~/.magito/workers.toml` present | `~/.magito/workers.toml` |
| magi seats | `~/.magito/bench.toml` present | `~/.magito/bench.toml` |
| Python toolchain | `pyproject.toml`, `tests/`, `src/` layout, and a `## Python` section in whichever of `CLAUDE.md`/`AGENTS.md` holds the repo's instructions that matches `references/python-rules.md.template`. No `pyproject.toml`, and the user does not ask for a Python scaffold: `skipped: not a Python project` | repo root, `CLAUDE.md`/`AGENTS.md` |
| Managed symlinks | dangling magito-owned links in tool dirs | `~/.magito/bin`, tool skills/agents/hooks dirs |

Read, do not assume: `git remote -v` (is this GitHub?), `CLAUDE.md`/`AGENTS.md`, `docs/agents/` and which files it holds, whether `CLAUDE.md` already imports `@docs/agents/INDEX.md`, `docs/adr/`, `pyproject.toml`, `.scratch/`, `.magito/config.toml`, `GEMINI.md`/`.gemini/settings.json`, and `.git/info/exclude`. A tracker doc or a `docs/agents/` file that already exists is a **diff-and-propose**, never an overwrite.

## 2. Walk the gaps

Take the unsettled items one at a time. Skip anything the inventory settled. For each, lead with the recommended answer and let the user redirect.

### Config file and mode

`.magito/config.toml` is the one file every later pipeline step reads to learn how this repo works with magito: its mode, its default tracker, its check command, where intent docs go, and when it was last audited. It lives in the main worktree root, under `.magito/`, never in a linked worktree. Resolve that root with `git worktree list --porcelain | head -1`, which prints `worktree <path>`, and write to `<path>/.magito/config.toml`. Never write it relative to the current directory: from a linked worktree, that creates a second config that nothing reads. The review marker is resolved the same way (ADR 0014). The directory `.magito/` is already in `.git/info/exclude` (see §Private-state excludes), so the file is never committed, in any repo, in either mode. Python 3.11's `tomllib` reads it; write it with your file-writing tool, no script is needed. It holds:

```toml
mode = "owner"            # "owner" or "guest"
tracker = "github"        # "github", "local", or "other" — the repo default
check = "bash scripts/check.sh"   # the one command that exits non-zero on failure
intent_dir = "docs/intent"        # where intent docs go
use_by_days = 14                  # optional; how long a local ticket stays fresh
audited = "<sha>"         # magito commit that last audited this repo
audited_on = "2026-09-28"
```

If the file is missing, ask the owner-or-guest question now, before any other section: **owner**, where magito files commit as usual, or **guest**, where the repo belongs to a team and magito's own files must stay out of the shared history. Recommend owner by default; recommend guest when the remote is not the user's own — a fork, or a shared team repo where the user is a contributor rather than an administrator. Ask this question at most once per repo: once `mode` is written, every later run reads it from the file instead of asking again. Changing it later means editing `.magito/config.toml` directly, the same as any other choice this skill writes.

**The guest-mode rule:** in guest mode, `setup-magito` never edits a file the team already tracks in git — an existing `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` is read, never written. When `setup-magito` creates a file in a guest repo, it adds that exact path to `.git/info/exclude` in the same step it creates the file, so nothing it wrote ever shows up in `git status`. The paths this applies to are `docs/agents/`, `docs/intent/`, an untracked `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, an untracked `.claude/settings.json`, and a magito-written check script, which goes at `.magito/check.sh` in guest mode rather than `scripts/check.sh` (see §Check command).

Write `mode` and a default `intent_dir` of `docs/intent` as soon as the mode question is settled. `tracker`, `check`, `audited`, and `audited_on` are filled by the sections that own them, below.

### Issue tracker

Where work is tracked. Skills never name a backend — `catch-up`, `to-issues`, `implement`, `handoff`, and `reviewing-changes` name an **operation** ("list open tickets", "fetch a ticket") and read `docs/agents/issue-tracker.md` to find out how to perform it here. This section writes that file.

Offer three choices:

- **GitHub** — the `gh` CLI against the repo's Issues. Propose this if a remote points at GitHub.
- **Local markdown** — tickets as files under `.scratch/<feature>/` (good for solo or remote-less repos).
- **Something else** — Jira, Linear, Beads, a wiki, a spreadsheet. Ask the user to describe the workflow in a paragraph; you record it as prose under the same operation headings, and nothing else has to change to support it.

Write `docs/agents/issue-tracker.md` from the matching template in [references/](./references/) — `issue-tracker-github.md.template`, `issue-tracker-local.md.template`, or `issue-tracker-other.md.template` for the third case. Create `docs/agents/` if it does not exist; this file is written whether or not the user accepts the agent-docs section, because every workflow skill depends on it. If the repo already has one, diff and propose — never overwrite. The chosen tracker also becomes `tracker` in `.magito/config.toml`: `github`, `local`, or `other` for the third case, matching the template used. `other` covers Jira, Linear, and every other prose-backed tracker, because `docs/agents/issue-tracker.md` holds the details (ADR 0015). It is the repo default an intent doc can later override (out of scope here; see the `intent` and `to-issues` steps).

[`issue-tracker-other-example.md`](./references/issue-tracker-other-example.md) is a worked example of the third case — one paragraph about a fictional Jira setup, and the file it produces. Read it before filling the skeleton freehand.

The **other** template doubles as the canonical list of the named operations. Fill every heading from the user's description and delete none of them: an operation their tracker cannot do says **not supported here** and names what a skill should do instead, which is what stops a skill guessing. Adding or renaming a heading there means changing the GitHub and local templates to match.

### Check command

`check` in `.magito/config.toml` names the one command that exits non-zero on failure — the floor the agentic pipeline trusts after every build step. Configured when `check` is set and running it now exits 0.

If the repo has none, propose one from what already exists: a test runner (`pytest`, `npm test`, `cargo test`), a linter (`ruff check .`, `eslint .`), or a type checker, in that order, picking whichever one actually finds something to run. For magito itself, that command is `bash scripts/check.sh`.

If nothing in the repo can serve as a check command, offer to write one. In owner mode it goes at `scripts/check.sh`. In guest mode it goes at `.magito/check.sh` and gets excluded in the same step it is created, per the guest-mode rule above.

### Check command documented

Owner mode: `AGENTS.md` or `CLAUDE.md` — whichever already holds the repo's `## Agent workflow` block (see §3) — names the check command in one line. Guest mode: not required. This follows from the guest-mode rule: that file is one the team tracks, so `setup-magito` never edits it; the check command lives only in `.magito/config.toml`, and the tracked file is left alone.

### Gemini context

Gemini CLI reads `GEMINI.md` by default. Configured when either `GEMINI.md` exists, or `.gemini/settings.json` sets `contextFileName` to whichever of `AGENTS.md`/`CLAUDE.md` already holds the repo's instructions — so Gemini CLI reads the same instructions as every other tool instead of nothing.

If missing, recommend the `contextFileName` setting over a second file: it points Gemini at instructions that already exist, rather than creating a copy that can drift out of sync. Offer to create a dedicated `GEMINI.md` only if the user prefers that. Either write follows the guest-mode rule: an existing `.gemini/settings.json` the team tracks is never edited; a new `GEMINI.md` gets excluded in the same step it is created.

### Review gate + base branch

- Run `git config magito.reviewGate true` — opts the repo into the merge/PR review gate. The gate applies to every branch that `implement` built, since `gitflow.sh worktree add` gives each one a review-decision marker (ADR 0014, ADR 0020); work done outside `implement` has no marker and lands with no gate. On a marked branch, landing is blocked until a fresh decision is recorded: a completed review, recorded with `worker.py record`.
- If this repo merges into a trunk other than its GitHub default branch (e.g. a `develop`-based migration workflow), also run `git config magito.baseBranch <branch>` — do NOT set this by default.

### Pull request title

`gitflow.sh pr` refuses a title that does not match `git config magito.prTitlePattern`, and unset means Conventional Commits (see `<skills>/implement/references/pr-body.md`, where `<skills>` is the folder that holds this skill's own folder: the parent of the directory its `SKILL.md` is in). Owner mode: leave it unset. Guest mode: read the titles of the last 20 merged pull requests with `gh pr list --state merged --limit 20 --json title`. If most of them already match `type(scope): summary`, leave the pattern unset. Otherwise recommend `git config magito.prTitlePattern off`, so the agent matches the house style by eye. When the titles follow one clear house pattern, such as a ticket key prefix, offer that pattern as an extended regular expression instead. Skip this step when the repo is not on GitHub, and say so in the report.

### Permission allowlist

This section applies only when the user runs Claude Code. For any other tool, report `skipped: not Claude Code` and write nothing here.

`.claude/settings.json` (committed) holds a read-only permission allowlist that cuts the approval prompts the workflow raises on every read-only `git` and `gh` call. Two rules, both from `CLAUDE.md`:

- **Permissions only — never a `hooks` key.** A `hooks` key here replaces the user-level hooks for this repo, silently disabling `staging-guard` and `review-gate`. If the file already carries one, flag it; do not add one.
- **Read-only verbs only, and no `deny` block.** `allow` rules merge across scopes, so this file only adds to the user's rules — it never restates them. A `deny` here is a false sense of enforcement, since the hooks are what actually block.

Missing? Offer to write a minimal permissions-only `allow` list for the read-only `git`/`gh` calls the skills use. Present but drifted (a stray `hooks` key, a `deny` block, write verbs)? Report it and propose the correction — never overwrite silently.

### Private-state excludes

Ensure both `.magito/` and `.scratch/` are in `.git/info/exclude` — add each if absent. Never `.gitignore`: that file is shared, and this is personal state. Both the session journal and the review-decision marker write under `.magito/`.

Run `git rev-parse --git-common-dir` (`--git-common-dir`, since inside a linked worktree `.git` is a file, not a directory) to get the exclude file's directory, then read `<that>/info/exclude` with your file-reading tool, then add whichever of `.magito/` and `.scratch/` is not already a line in it, using your file-editing tool. Idempotent by construction — a line already present is left alone.

On a tool with no file-editing tool, fall back to the shell form:

```
e="$(git rev-parse --git-common-dir)/info/exclude"
for p in .magito/ .scratch/; do grep -qxF "$p" "$e" 2>/dev/null || echo "$p" >> "$e"; done
```

### Session journal

`.magito/journal/` is where per-session entries land. It self-creates the first time `/handoff` composes a filename (`.magito/journal/YYYY-MM-DD-HHMMSS-<slug>-<hex>.md`) and writes the entry directly, so there is nothing to scaffold — it counts as **configured** once `.magito/` is excluded above. If the repo carries pre-magito notes worth keeping, offer to import them (next section).

### Legacy notes

Does this repo carry notes that predate magito? Scan for: an old magito handoff file (`~/.magito/handoffs/<slug>.md`), `NOTES.md`, `TODO.md`, a `.beads/` database or similar task store — or a system the user names when asked.

If something is found, offer to bring it into the session journal as entries. **The import procedure lives in [`references/importing-legacy-notes.md`](./references/importing-legacy-notes.md) — read it only when the inventory actually finds something.** It is never destructive: originals stay put, the user confirms the mapping before any file is written, entries stay under the journal word cap (the reference points at the live number — do not restate it here), and timestamps come from the source. Found nothing? Skip the section and never open that file.

### Delegation workers and magi seats

`~/.magito/workers.toml` (the `/implement` delegation roster) and `~/.magito/bench.toml` (the magi seat roster) are **the user's machine-local files**. Report each as present or missing. Never write or overwrite either without explicit confirmation (the convention is in `CLAUDE.md`). If one is missing, say so and point at where it bootstraps — `bench.toml` self-creates on the first `/magi` run and is repaired by `/magi config`; `workers.toml` is created and checked by the `workers` skill (`/workers`). Offer to seed a missing `bench.toml` only if the user asks; do not fill it silently.

For `workers.toml`, report present or missing and stop there. The `workers` skill creates a
missing roster and checks an existing one: send the user to `/workers`.

### Python toolchain

The conventions `implement` and `verifying` build to, written into the project itself so that every agent in every tool follows them, with or without magito installed.

**The rules section.** Copy [references/python-rules.md.template](./references/python-rules.md.template) into whichever of `CLAUDE.md`/`AGENTS.md` holds the repo's `## Agent workflow` block, as a `## Python` section after that block. Copy it as is; it has no placeholders. If a `## Python` section already exists, diff the template against it and propose the diff — never overwrite. In guest mode, show the section and never write it into a file the team tracks (the guest-mode rule).

The section replaces the toolchain lines that earlier runs wrote into the `## Agent workflow` block: any lines there about uv, the `src/` layout, pytest, ruff, or prek. When you add the `## Python` section to a project whose workflow block holds such lines, remove them in the same diff-and-propose step, so the project never carries the Python rules twice. The block keeps its tracker and check-command lines. In guest mode, the removal is only proposed, like the section itself.

After writing the section, count the lines of the file that holds it (`wc -l`). The file is meant to stay at or under about 200 lines. If it is over 200, tell the user the count and the line count of each `## ` section, and leave the choice of what to cut to them. Never trim the `## Python` section to fit.

**A fresh project.** Scaffold in this order. Never type a version number from memory into any of these files: every version comes from a tool on the day it runs.

1. Run `uv self update --dry-run`. `uv init` takes the `uv_build` bounds from the installed uv, so a stale uv writes stale bounds. If the dry run says it would update, uv must be updated before step 2: offer to run `uv self update`. If that fails because a package manager installed uv, tell the user the installed and latest versions from the dry-run output, and ask them to update uv with that package manager. Do not run step 2 until `uv self update --dry-run` no longer offers an update. If the user declines to update, stop the scaffold and report that uv is out of date.
2. Inside the project folder, with no name argument, run `uv init --lib` for a library, or `uv init --package` for a CLI or app. uv takes the project name from the folder name; create the folder first if it does not exist. Both give the `src/` layout and the `uv_build` backend. `uv init` writes a `.gitignore` only when it creates the git repository itself. If the folder has no `.gitignore` after `uv init`, write one with exactly this content, which is what uv writes when it creates the repository. If a `.gitignore` already exists, leave it alone.

   ```
   # Python-generated files
   __pycache__/
   *.py[oc]
   build/
   dist/
   wheels/
   *.egg-info

   # Virtual environments
   .venv
   ```

3. Append [references/pyproject.toml.template](./references/pyproject.toml.template) to the `pyproject.toml` that `uv init` wrote, and set `requires-python = ">=3.12"`. Then run `uv python pin 3.12`, so `.python-version` matches the minimum the project supports. Run the pin after the `requires-python` edit: uv refuses a pin below the declared minimum.
4. Add `tests/test_smoke.py` as [references/src-layout.md](./references/src-layout.md) describes, filling its `{{package}}` placeholder.
5. `uv add --dev pytest ruff pyrefly`.
6. Copy [references/pre-commit-config.yaml.template](./references/pre-commit-config.yaml.template) to `.pre-commit-config.yaml` and run `uvx prek autoupdate`. It needs a git repository; run `git init` first if there is none.
7. Copy the rules section, as above.
8. Verify: `uv sync && uv run pytest && uv run ruff check . && uv run pyrefly check` must pass on the skeleton.

**An existing project.** For each of these files that the project already has, diff the template against the existing file and propose the diff — never overwrite.

### Managed symlinks

`install.py` links this repo's skills, agents, hooks, and `bin/` into each tool's config dirs. A renamed or deleted skill can leave a **dangling** link behind (the old name still points at a file that is gone). Report any you find as **stale**, and offer to run `python install.py` from the magito checkout (found as the Audit version section describes), not from this repo — which prunes magito-owned dangling links as part of a normal run (`--dry-run` shows what it would remove first). Do not delete links here yourself; `install.py` owns its destinations.

### Agent docs (`docs/agents/`)

Offer a `docs/agents/` context layer: the version-controlled home for project context an agent cannot cheaply rederive from code, governed by a two-gate filter — content earns a place only if it is **non-rederivable** from the code AND **stable** across refactors. Only four files are scaffolded; the rest grow lazily as real content arrives.

Templates live in [references/](./references/) — copy and adapt, fill `{{project}}`, never regenerate freehand; for a repo that already has `docs/agents/`, diff each template against the existing file and propose the diff — never overwrite (same rule as the Python templates above). Scaffold exactly these four:

- `docs/agents/README.md` — the convention manifest (read once).
- `docs/agents/INDEX.md` — the routing table and auto-load entry point.
- `docs/agents/OVERVIEW.md` — intent-only stub; fill purpose / approach / rejected alternatives with the user, or leave the italic prompts for them (half-page cap).
- `docs/agents/GLOSSARY.md` — header only; add no invented terms.

Do NOT create `CONVENTIONS.md`, `GOTCHAS.md`, or `flows/` — those are pulled into existence by real content later, never scaffolded empty.

`docs/agents/issue-tracker.md` is not part of this scaffold — the tracker section already wrote it, as real content rather than an empty template. Add a routing row for it to `INDEX.md`: `| Where work is tracked, and how to perform a tracker operation | [issue-tracker.md](./issue-tracker.md) |`.

Wire the auto-load bundle with the same "whichever of `CLAUDE.md` / `AGENTS.md` exists" rule as the workflow block: `CLAUDE.md` is import-capable — add the single line `@docs/agents/INDEX.md`; `AGENTS.md` is not — give it the prose pointer `` Project agent docs live in `docs/agents/`; start with `INDEX.md`. `` If both exist, the import goes in `CLAUDE.md` and the pointer in `AGENTS.md`. If neither exists, the import (or pointer) rides on whichever file you create in the next step.

### Guest excludes

Guest mode only. Configured when every path this skill created — `docs/agents/`, `docs/intent/`, an untracked `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, an untracked `.claude/settings.json`, `.magito/check.sh` — is listed in `.git/info/exclude`, and `git status --short` shows none of them. Run that command at the end of the walk. Anything it shows is a path a write step forgot to exclude; add it before the run finishes.

### Audit version

`audited` in `.magito/config.toml` holds the magito commit that last audited this repo. Find the current one from the installed skill's own file: resolve the symlink it is installed as, back to the magito checkout it points into, and run `git rev-parse HEAD` there. Configured when `audited` matches that commit.

If `audited` is older, do not trust "configured" from a previous run at face value: a newer magito commit can carry checklist rows this repo has never seen. Re-read the whole inventory table above and walk whatever it finds unsettled. At the end of a clean run, write `audited` to the current commit and `audited_on` to today's date.

## 3. Confirm and write

Show a draft, let the user edit, then write only what the inventory marked missing or stale. In guest mode, every bullet below that creates a file follows the guest-mode rule: exclude the path in the same step it is created, and never touch a file the team already tracks.

- `.magito/config.toml` — write `mode` and `intent_dir` as soon as the mode question is settled (§Config file and mode); fill in `tracker` once the issue-tracker section settles, and `check` once the check-command section settles; stamp `audited` and `audited_on` at the end of a clean run (§Audit version).
- An `## Agent workflow` block in whichever of `CLAUDE.md` / `AGENTS.md` already exists — edit that one; never create the other alongside it; if neither exists, ask which to create; in guest mode, only if neither is a file the team already tracks. The block names the tracker in one line pointing at `docs/agents/issue-tracker.md` and, in owner mode, names the check command — a summary, never a second copy of the operations. The Python toolchain lives in its own `## Python` section, not in this block.
- `docs/agents/issue-tracker.md`, from the tracker section.
- For a Python project, the `## Python` section from `references/python-rules.md.template`, written as §Python toolchain describes: after the `## Agent workflow` block, replacing any toolchain lines in that block, and followed by the line count check.
- If the user chose local markdown, create `.scratch/` with a short `README.md` pointing at `docs/agents/issue-tracker.md` for the conventions.
- The review-gate, base-branch, and exclude git commands above.
- The check command script, if the check-command section had to write one (`scripts/check.sh` in owner mode, `.magito/check.sh` in guest mode).
- The Gemini context fix — a `contextFileName` setting in `.gemini/settings.json`, or a new `GEMINI.md`.
- The `.claude/settings.json` permission allowlist, if the user runs Claude Code and it was missing or drifted — permissions only, no `hooks` key, no `deny` block.
- If the user accepted the agent-docs section, scaffold the four `docs/agents/` files, add the `@docs/agents/INDEX.md` import (or the `AGENTS.md` pointer), and give `INDEX.md` its `issue-tracker.md` routing row.

Close by telling the user what changed and what was already fine. Name the skills that read this config, and that they name operations rather than backends — so switching trackers later means rewriting one file, not editing every skill. If you scaffolded `docs/agents/`, name the four files, note that the auto-load bundle (INDEX + OVERVIEW + GLOSSARY) loads via the `@-import`, and that `CONVENTIONS.md` / `GOTCHAS.md` / `flows/` grow lazily. Everything here is editable directly later — and this skill is safe to re-run any time, to change a choice or repair drift.
