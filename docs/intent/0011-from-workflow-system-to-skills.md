# From a workflow system to a set of skills

Status: accepted · Opened: 2026-11-06 · Accepted: 2026-11-06

## Problem

magito was built to govern work nobody watched. So it grew a review gate, a review marker, a
roster of worker CLIs, an automatic review by another model family, worktree rules made for
VS Code, and scripts that skills address through a `<skills>` placeholder. Intent 0010 settled
that the user now watches every build in Claude Code Desktop, so most of that machinery
guards against a risk that no longer exists.

The machinery also costs the user directly. The first build session started from the new
workflows (#276) raised permission prompt after permission prompt. The prompts came from
four sources: agents filling in the `<skills>` placeholder with shell variables, chained
commands, skills that read and write in the main checkout from inside a worktree, and
bookkeeping commands such as `worker.py start` and `worker.py record`. A build session that
needs the user to approve every command defeats the point of a separate session.

## Proposed outcome

magito is a set of skills that serves the workflows in `docs/WORKFLOWS.md`. Every script,
hook, and config file left in the repo serves a named workflow step. The skills behave as
intent 0010 decided. One observable check proves the build path works: a Sonnet worker in
Auto mode runs `ticket-to-pr` (today's `implement`) on a small ticket and reaches "ready to
read" with zero permission prompts.

## Decisions so far

- **Scope:** Phases 1, 3, and 7 of the planning artifact "Magito overhaul"
  (https://claude.ai/artifact/J3CQywwbz4HabAM5gpZ9jR), the "hidden blockers" scope below, the
  build-session approval fixes below, and the skill behavior intent 0010 decided. Renames,
  the `README.md` and `CLAUDE.md` rewrites, and `which-workflow-now` belong to the renames
  intent. Plugins belong to the plugins intent.
- **Past ADRs and rules are inputs, not limits.** A rule survives only if it serves a step in
  `docs/WORKFLOWS.md`.
- **Hidden blockers.** Remove anything that creates a later obligation or holds work until
  someone signs off. Keep only checks that fail at once, in the same command, with the fix in
  the message.
  - Remove: `hooks/review-gate.py`; the review marker (`gitflow.sh worktree add` writes
    `pending`, and `pr` and `merge` refuse until `worker.py record` runs); the automatic
    cross-family review and its roster escalations in `implement` (`pipeline.md` steps 6 to
    8, and the fix rounds); the `to-issues` step 5 escalations (AMBIGUOUS, leftover FIX, no
    subagent, snapshot changed); and the "every implement change gets a recorded review" rule
    in `shared/SYSTEM-INSTRUCTIONS.md`.
  - Supersede ADRs 0011, 0013, 0014, 0018, and 0020 (see "Records" below).
  - Keep, but reword without "gate" or "guard" (use "check" or "refuses"): the plan stop for
    a ticket no accepted intent covers, and `gitflow.sh`'s immediate refusals (no files
    named, commit on the base branch, dirty tree, empty pull request body, title pattern, no
    commit ahead).
  - Add a rule to `docs/agents/CONVENTIONS.md`: a skill or script may stop work only with an
    immediate, explained refusal, never by creating a step that waits for a sign-off.
  - Replace "gate" and "guard" in the skills, scripts, and `docs/agents/*` files this intent
    rewrites. `CLAUDE.md` and `README.md` change in the renames intent.
- **Worktrees.** Remove every worktree rule: the `gitflow.sh worktree` subcommand,
  `.magito/worktrees/`, and ADR 0019. Desktop makes the worktree.
- **Build sessions run in Auto mode.**
  - `docs/WORKFLOWS.md` says the worker needs a mode that runs the build's edits and commands
    without asking, and that Auto does that today. This corrects the Accept edits line in
    #276.
  - `intent-to-tickets` offers each card with Sonnet, Worktree on, and Auto. A card can grant
    only a mode the planner has, so the planner runs in Auto too.
  - `"defaultMode": "auto"` takes effect only in `~/.claude/settings.json`, so `setup-magito`
    checks it and suggests it, and never writes it.
- **The zero-prompt check** above is this intent's acceptance test.
- **`gitflow.sh` and `issues.sh` are deleted.** Skills give plain `git` and `gh` commands
  instead, one per call. A wrapper script adds a prompt rather than removing one (#150), and
  Desktop worktrees mean a worker is never on the base branch.
  - The base branch is `git config --get magito.baseBranch`; when that prints nothing, it is
    the branch `origin/HEAD` points to. It is not a `.magito/config.toml` field, because
    `.magito/` is excluded from git and so is absent from a worker's worktree.
  - Explicit staging stays a rule in the shared instructions. The pull request title pattern
    and the "no empty body" rule move to `pr-body.md` as prose.
  - A repo with no remote merges in the planner, which runs `git merge --no-ff <branch>` in
    the main checkout after the user approves. A worker cannot do it: Claude Code's worktree
    isolation blocks `git -C <main checkout>` from inside a worktree session.
  - Evidence: on 2026-11-06 a Haiku subagent, given only these rules as prose, did every job
    `gitflow.sh` did, in a scratch repo built with its traps. It staged an edit, a deletion,
    and a new file by name while leaving a user's edit and an untracked file alone; read the
    base branch from git config (`develop`, with `origin/HEAD` pointing at `main`); counted
    commits ahead; pushed with upstream; wrote the `gh pr create` command with
    `--base develop`; and merged with `--no-ff` through the main checkout without switching
    branches in its worktree. All 13 commands exited 0. One run, so it shows the rules are
    followable, not that they never slip.
- **Both hooks are deleted:** `hooks/review-gate.py` and `hooks/staging-guard.py`, with
  `install.py`'s hook code (`merge_hook_settings`, the Codex `hooks.json` wiring, the `hooks`
  and `hooks_config` keys in `install.toml.example`) and `scripts/test_install_codex_hooks.py`.
  The staging rule stays in the shared instructions, which every tool reads. A slip shows in
  the user's diff read before any pull request exists.
- **`docs/agents/CONVENTIONS.md` gains a "Commands in skills" section** with four rules:
  1. Prefer reading a file to running a command; a file read needs no approval in any tool
     (#150).
  2. Prefer the real program to a wrapper: `gh issue view`, not a script around it (#150).
  3. One plain command per call: no `;`, `&&`, `|`, `$(...)`, or shell variables (#128).
  4. Where a skill names its own script through `<skills>`, the agent writes the real folder
     path into the command text, never into a shell variable such as `S=~/.claude/skills`.
- **A worker never leaves its worktree.**
  1. The ticket body carries everything the worker needs. Its `**Intent:**` line alone tells
     the worker its plan is approved; the worker never opens the intent doc.
  2. The planner works in the main checkout with Worktree off, so `.scratch/`,
     `.magito/journal/`, and `.magito/config.toml` are in its own folder. Every "resolve
     against the main worktree root" instruction is deleted, with
     `git worktree list --porcelain | head -1`.
  3. With the local tracker, the planner pastes the ticket body into the card's brief.
  4. On "accept", the planner commits the intent on `main` in the main checkout and pushes it
     before offering cards. This is required, not only tidy: new worktrees start from the
     remote's default branch (`worktree.baseRef` is `"fresh"` by default), so an unpushed
     intent never reaches a worker.
- **Gitignored files reach worktrees through `.worktreeinclude`.** A worktree is a fresh
  checkout, so `.env` and other ignored files are missing. Claude Code copies every file that
  matches a pattern in `.worktreeinclude` (gitignore syntax) and is also ignored by git, into
  each worktree it creates, Desktop sessions included.
  - `setup-magito` asks which ignored files a build needs (credentials, local config) and
    writes `.worktreeinclude` at the repo root. In guest mode it writes the file untracked and
    lists it in `.git/info/exclude`.
  - Dependency folders such as `.venv` and `node_modules` are not copied. The worker rebuilds
    them with the project's own setup command; in a uv project, `uv run` syncs the
    environment on first use.
  - Tested on 2026-11-06 with Claude Code 2.1.319: a listed `.env` and a file in a listed
    ignored folder were copied, and an unlisted `.env.local` was not. A file excluded only
    through `.git/info/exclude` (`.magito/config.toml`) was copied. An untracked
    `.worktreeinclude` that was itself only in `.git/info/exclude` still worked.
  - Each worktree holds its own copy of the secrets. Desktop removes an archived session's
    worktree about 30 days later.
- **`intent-to-tickets` keeps its spec review, run by a fresh-context subagent.** The
  subagent reads the intent and the drafts and changes no file. The review stops after three
  rounds and shows the user what is left. A reviewer from another model family returns
  through the Codex plugin in the plugins intent, not through the roster.
- **`worker.py standards` moves to its own script,**
  `skills/general/reviewing-changes/scripts/standards.py`, with its test. It lists the
  standards docs, the ADRs that bear on the changed files, and the doc lines that name
  something the diff removed or renamed. `ticket-conformance-check` is its only user. The rest
  of `worker.py` is deleted.
- **The plan stop is prose in `ticket-to-pr`, with no script:** a ticket with an
  `**Intent:**` line goes ahead (its plan was approved at "accept"); a small change (one file
  or a pure text change, and no new test needed) goes ahead; anything else shows its plan and
  waits.
- **Survivors, by the workflow rule** (skills the user calls directly are not judged by it):
  - Cut: the `executor` agent and `implement/references/parallel.md` (parallel work is
    separate Desktop sessions; a short batch rule in `ticket-to-pr` covers Workflow C's
    one-after-another batch); `implement/references/integrate.md` (one ticket per pull
    request); the `researcher-persona` and `production-safety-reviewer` agents; the `workers`
    skill.
  - Fold `finding-lacunae` into `challenging-assumptions`: its test of what force keeps a
    missing piece missing becomes an optional step there.
  - Keep `to-questionnaire`.
- **Tests and evals:**
  - Delete every `scripts/test_gitflow_*.py`, every `scripts/test_worker_*.py` except
    `test_worker_standards.py` (it moves with `standards.py`), and
    `scripts/test_install_codex_hooks.py`. `scripts/check.sh` drops the hook payload checks
    and the roster and marker checks, and its header list is updated. It keeps the
    `install.py --dry-run` check, `anti-slop.py` over every tracked markdown file, and the
    model-invocation check.
  - Delete `scripts/eval-workers.sh` and `scripts/eval-integrate.sh`, with their tests. Keep
    the intent, to-issues, implement, catch-up, and handoff evals. Each launches its subject
    with one fixed `claude -p --output-format json` command instead of `worker.py run`.
  - The implement eval carries the zero-prompt check: a Sonnet worker in Auto runs
    `ticket-to-pr` on a small fixture ticket in a scratch repo, and passes only when it
    reaches "ready to read" and the result's `permission_denials` list is empty. A headless
    run lists every command that would have prompted in `permission_denials` (tested
    2026-11-06: a refused `python3` command appeared there).
- **The stops in `ticket-to-pr`:** keep escalations 1 (an ambiguous ticket), 3 (a locked test
  or out-of-scope work must change), 4 (the red check passes before any change), and 5 (no
  check command). Escalation 2 (three failed review rounds) becomes the `/code-review` round
  cap from intent 0010. Escalations 6 (integrated runs) and 7 (no reviewer) go with
  `integrate.md` and the roster.
- **Records:** one ADR records the move to supervised work and supersedes ADRs 0011, 0012,
  0013, 0014, 0018, 0019, and 0020. ADR 0012 ("scripts are the enforcement floor") goes too,
  because `gitflow.sh` was that floor. `docs/agents/GLOSSARY.md` updates "escalation" (four
  reasons, not seven) and adds planner session, worker session, and Risk.
- **Intent 0010's skill behavior lands here:**
  - the planner stops after publishing tickets and offers one card per ready ticket;
  - the Risk field (Low, Normal, High) in the ticket template;
  - the worker's order: check, `/simplify`, `/code-review` capped at three rounds, `/verify`;
  - the "ready to read" message, with every finding answered and Pre-existing findings
    labeled;
  - a Low ticket opens its pull request before the user's read;
  - Testing and Risk fields in `pr-body.md`;
  - only planner sessions write journal entries.

## Affected users and systems

- The user, in planner and worker sessions on Desktop, local and SSH.
- Skills: `implement`, `to-issues`, `reviewing-changes`, `setup-magito`, `intent`,
  `catch-up`, `handoff`, `workers`, `finding-lacunae`, `to-questionnaire`, `verifying`,
  `decruft`, `magi`, `challenging-assumptions`.
- Scripts: `skills/general/implement/scripts/gitflow.sh`, `worker.py`, `issues.sh`;
  `skills/general/to-issues/scripts/worktree_snapshot.py`; `install.py`; `bin/`.
- Hooks: `hooks/review-gate.py`, `hooks/staging-guard.py`.
- Agents: `executor`, `researcher-persona`, `production-safety-reviewer`.
- Tests and checks: `scripts/check.sh`, about 25 `scripts/test_worker_*` and
  `scripts/test_gitflow_*` files, and the `scripts/eval-*.sh` evals.
- Docs: `docs/adr/`, `docs/agents/CONVENTIONS.md`, `docs/agents/GLOSSARY.md`,
  `docs/WORKFLOWS.md`, `shared/SYSTEM-INSTRUCTIONS.md`, `install.toml.example`,
  `.claude/settings.json`, the tracker templates in `skills/general/setup-magito/references/`.
- Other tools (Codex, Gemini CLI, omp), which read the same skills.

## Out of scope

- Renaming skills, rewriting `README.md` and `CLAUDE.md`, and building `which-workflow-now`
  (the renames intent).
- Other providers through plugins (the plugins intent).
- Read-only helper commands in `bin/`. The one candidate, the planner's "is this ticket
  ready" query, is already a single documented `gh issue view ... --jq` command in the
  tracker doc. Add a `bin/` command only when a documented read-only command fails in real
  runs, and then cover it with one allow rule.
- Turning on the Bash sandbox. It needs worker writes kept inside the worktree first, which
  this intent does.

## Constraints

- Stdlib-only Python 3.11+, no new dependencies.
- No workflow step depends on a hook; the work machine bans hooks.
- Auto mode pauses after 3 refusals in a row or 20 in total. Its classifier refused a compound
  command that built a path and wrote a file in one go (`CLAUDE.md`, "Permissions").
- `install.py` already links every `bin/*` file into `~/.magito/bin/` (ADR 0006), so a
  script moved to `bin/` gets a fixed path with no new install code.
- Desktop's worktree hook refuses file writes outside the session's worktree.

- **Inventory (2026-11-06), approximate files and lines:** review marker 34 / 225; roster 55 /
  300 (magi's `bench.toml` 7 / 13, kept apart); worktree rules 22 / 85; `<skills>` command lines
  22 / 65, plus 13 lines that define it; paths resolved against the main worktree root 17 /
  45; hooks 20 / 150; review and roster escalations 9 / 30. "gate" appears in 24 files and
  "guard" in 12; the "two-gate filter", the "corroboration gate", and guard clauses in code are
  other senses and stay. Fourteen test scripts exist only for the marker, roster, worktree, or
  hooks. Every paid eval launches its subject through `worker.py run`, so retiring `run`
  breaks all six eval scripts.

### What magito's history says about scripts and prompts

- **Where a script lives does not cause prompts (#108).** Claude Code matches permission rules
  against the command text. Moving a command into or out of `~/.magito/bin/` changes no
  prompt by itself.
- **A wrapper script never reduces prompts, and often adds one (#150).** Claude Code approves
  known read-only programs such as `gh issue list` on its own. A script name is on no such
  list, so `bash issues.sh list` prompts where the `gh` call inside it would not. In tools that
  sandbox or prompt on every command, a wrapper costs the same as the command it wraps. A
  wrapper earns its place only when it carries real behavior. Reading a file needs no
  approval in any of the four tools.
- **The `<skills>` placeholder exists because general skills install into five tools with five
  different skills folders (0d44310).** A path relative to the skill failed, because the
  agent's working folder is the project.
- **Claude Code's worktree isolation refuses some commands outright** (worktrees docs): an
  edit in the main checkout, a command whose working folder is the main checkout, any
  `git -C`, `--git-dir`, or `GIT_DIR` that points git at the main checkout, and any command
  whose git use it cannot verify from the text. The last check cannot be turned off.
- **`claude -p --worktree` leaves its worktree locked** after the run, so cleanup needs
  `git worktree unlock` first. This matters for evals that start sessions that way.
- **Auto mode's classifier refused compound commands that build values with `$(...)`, even a
  read-only one (#128).** Plain single commands ran.

## Not yet clear

- Whether `.worktreeinclude` applies to SSH sessions. The docs name `--worktree`, subagent,
  and Desktop worktrees only.

## Open questions

None.
