# The workflows for magito on Claude Code Desktop

Status: accepted · Opened: 2026-11-06 · Accepted: 2026-11-06

## Problem

magito was built as a development-workflow system for an unwatched pipeline. It has a review
gate, a review marker, a worker roster, and worktree rules made for VS Code. The user now works
in Claude Code Desktop, and Desktop changes how a session starts, branches, and shows a diff.
Many old rules may no longer earn their place. There is also no single written statement of how
the user is meant to work. So there is nothing to test each later change against.

## Proposed outcome

One accepted set of workflows (A to F in the planning artifact, as amended here) that says how
the user works from now on. Each step names who acts and which skill or Desktop action they
use. The workflows become `docs/WORKFLOWS.md`. Every later intent and ticket in this overhaul
names the workflow step it serves. A change that serves no step gets cut.

Source draft: Part 1 of the artifact "Magito overhaul",
https://claude.ai/artifact/J3CQywwbz4HabAM5gpZ9jR.

## Decisions so far

- The workflows are the grounding contract for magito's next version. Every later intent and
  ticket names the workflow step it serves.
- magito moves from a development-workflow system to a set of skills. Past ADRs and rules
  (worktrees, gates, the roster) are inputs, not limits.
- This is the first of five intents. The others: Phase 0 agents (tickets only); from workflow system
  to skills (Phases 1, 3, 7 plus the hidden-blockers scope); renames and instruction rewrites;
  plugins.
- The workflows are written for Claude Code Desktop, in local and SSH sessions. Skills stay
  usable in Codex, Gemini CLI, and omp. Where a skill uses a Desktop-only feature, it names a
  plain fallback, such as "open a new session" in place of a session card. No workflow
  promises to run fully outside Desktop. On a machine without Desktop, the workflows are a
  guide, not a contract.
- After "accept", `intent-to-tickets` runs on its own and publishes the tickets. Then the
  planner stops and builds nothing. It offers one new session per ticket that is ready to
  start, as a suggested-task card the user starts with a click. An independent ticket gets its
  card at once. A ticket that depends on another gets its card once that one is merged. In
  another tool, the fallback is a line such as "run `/ticket-to-pr 14` in a new session."
  Nothing builds unwatched, which is what lets the review gate and marker go.
- Two session roles:
  - **Planner:** Opus, in the main checkout, with Worktree off. It runs `intent-interview`,
    `intent-to-tickets`, `session-catch-up`, `session-handoff`, and the opt-in reviews.
  - **Worker:** Sonnet, with Worktree on. It runs `ticket-to-pr` and nothing else. The
    planner's session card sets the model.
- The workflows name a permission mode by what the role needs, never as a fixed mode. The
  planner needs a mode that allows file edits, because `intent-interview` writes its doc from
  the first question. Plan mode does not allow edits, so it is not the planner's mode. The
  worker needs a mode that edits without asking per file; Accept edits does that today.
  New modes can replace either one without a change to the workflows.
- The default review in Workflow B, in order: the worker runs the check; when it passes, the
  worker runs `/code-review` and applies the fixes; it stops and says the branch is ready to
  read; the user reads the diff and leaves line comments; the worker revises, repeating as
  needed; the user tells it to open the pull request. No pull request exists before the
  user's read. Heavier review is opt-in only: `ticket-conformance-check` for tickets that set
  contracts other tickets rely on, and a Codex review later (intent 5). Where `/code-review`
  does not exist, the user's read is the review.
- The spike in Workflow A is a paragraph in `docs/WORKFLOWS.md`, not a skill. It holds the
  prompt shape ("Spike: get X working end to end on one real fixture. One smoke run only, no
  other tests, no refactoring. Stop when the fixture produces output."), run in a worker
  session with Worktree on. A failed spike is archived. `intent-interview`'s "When not to use
  this" gains one line: "Not sure the approach works? Spike first." If the user keeps
  retyping the prompt, that is the signal to make it a skill.
- Only planner sessions write journal entries. Each planner writes one entry when its work
  ends, through `session-handoff`; in practice, once a day. Worker sessions never write one:
  a worker's record is its pull request and its ticket. `session-catch-up` runs only in a
  planner. A gotcha found in a worker reaches the journal when the user tells the planner,
  and the pull request body keeps the worker's own decisions.
- Workflow E (rationalize an existing codebase) is reduced to three steps. A planner runs
  `audit-code-cruft` on one area at a time; it lists what to cut, with evidence. The user
  picks which findings to accept, and each accepted group becomes a ticket. Each ticket goes
  through Workflow B as one small pull request. E adds one rule: before cutting, confirm a
  check would fail if behavior changed. For a library, that is tests that call its public
  functions; for an app, one real end-to-end use. If no such check exists, the first ticket
  writes one. The terms "golden files", "runs", "passes", and "measure" are dropped.
- Every ticket carries a **Risk** field (Low, Normal, High), written by `intent-to-tickets`.
  It sets both the review and the test depth, and it replaces the per-project rigor setting
  from the artifact's Phase 3:
  - **Low** (docs, comments, copy, deleting dead code): the user reads the pull request
    summary and the check output only. Tests: the existing check passes.
  - **Normal** (the default): the user's diff read. Tests: one for the new behavior; for a
    bug, a failing test first.
  - **High** (a contract other tickets rely on, data at external edges, security, CI or
    install config): the user's diff read, `ticket-conformance-check`, and `/code-review` at a
    higher effort. Tests: data checks at the boundaries it touches.
  The worker can raise a ticket's risk when the code proves riskier than the ticket said. It
  never lowers it.
- The user may press Desktop's "Merge when ready" in local sessions. Pressing it is the
  user's own merge, made after their read, so "the user owns every merge" holds. It waits for
  CI and squash-merges. In SSH sessions, where it is disabled, the user merges on GitHub. A
  worker never presses it and never asks GitHub to merge.
- Practices adopted from the Anthropic post:
  - **Round cap (Workflow B):** the worker's `/code-review`-then-fix loop stops after three
    rounds. Later rounds re-review only the new diff. After round three, the worker stops
    and tells the user the approach may need rethinking. The user's own comment rounds have
    no cap.
  - **Pre-existing (Workflow B):** a finding in code the ticket did not touch is not fixed in
    this change. It goes to the planner as "ticket it" (Workflow D).
  - **Answer every finding (Workflow B):** the worker's "ready to read" message lists each
    finding as fixed, or dismissed with a reason.
  - **Fix at the source (Workflow F):** when the same review comment recurs, the planner
    tickets a change to the skill or `CLAUDE.md` that let it through.
  - **Pull request body:** `pr-body.md` gains Testing and Risk (the ticket's level). "How to
    revert" appears only when reverting the pull request is not enough, such as a data
    migration or a config change.
  - **Explain first (Workflow B):** before reading a diff in an unfamiliar area, the user asks
    the worker to explain the module.
  - **`REVIEW.md` is deferred.** It is not confirmed that `/code-review` reads it. Add one in a
    repo once the same review comment keeps coming back.
- After the build, the worker runs, in order: the check; `/simplify` on Normal and High
  tickets, then the check again; `/code-review`, at most three rounds; `/verify` when the
  change has something to run (an app or a command-line tool; a library skips it); then the
  "ready to read" message. `/simplify` comes before `/code-review` because it changes code.
  Where these commands do not exist, the fallbacks are the build ladder in the shared
  instructions and one manual run.
- Workflows C (a backlog day), D (side quests), and F (start and end of day) stand as drafted
  in the artifact, amended by the decisions above. Workflow D's claim that a new worktree
  starts from the default remote branch is not in the Desktop docs; check it on first use.

## Affected users and systems

- The user, working in Claude Code Desktop on a laptop (local sessions) and on a VM (SSH
  sessions).
- Every skill in `skills/general/` and `skills/claude/`. They also install into Codex, Gemini
  CLI, and omp.
- `README.md` ("Cheat sheet", "Which skill when"), which describes today's workflow.

## Out of scope

- Building any change to skills, scripts, or hooks. Later intents do that.
- Renaming skills. The workflows use the new names from the artifact as working names, and
  intent 4 settles them.
- Other providers through plugins (intent 5).

## Constraints

- No workflow step can depend on a hook. The work machine bans hooks.
- On an SSH session, config is read from the VM, not the laptop.
- Shell environment variables do not reach the Desktop app.

### Desktop facts, checked against the official docs on 2026-11-06

Sources: code.claude.com/docs/en/desktop.md, sub-agents.md, agent-view.md,
code-review-local.md, cross-session-messaging.md. These correct the planning artifact.

- **Worktrees are off by default.** The user turns on Worktree before starting a session. The
  docs do not say which branch a new worktree starts from.
- **Diff:** Cmd/Ctrl+Shift+D toggles the diff pane. The +N −M counts sit in the Changes card
  and the title bar's Changes button. Line comments work: click the + by a line number, type,
  press Enter; Cmd/Ctrl+Enter submits several. Claude revises and shows a new diff.
- **No "Review code" button.** Review is the `/code-review` command, a bundled skill that
  reviews branch changes for correctness bugs. Its card offers "Walk through in diff" and
  "Apply fixes." A personal skill named `code-review` replaces it.
- **Split view** is Option/Alt-click, or right-click, then Open in, then Split view.
  Cmd/Ctrl-click opens a session in its own window. Ctrl+Tab cycles sessions.
- **The terminal** (Ctrl+`) works in local and SSH sessions.
- **Permission modes:** Manual, Accept edits, Plan, Auto, Bypass permissions. A mode persists
  per folder in local sessions. Plan applies to one session only.
- **SSH:** Desktop installs Claude Code under `~/.claude/remote/` on first connect, and reads
  skills from the remote `~/.claude/skills/`. The docs do not say where agents and
  `CLAUDE.md` come from.
- **Environment:** the local environment editor (gear icon) holds `KEY=value` lines.
  Exports in `~/.zshrc` apply after Desktop is quit and reopened.
- **`/fork`** copies the conversation into a new background session with the same model,
  permission mode, and effort.
- **Explore** runs on the main session's model. A user agent named `Explore` overrides it and
  keeps its own `model` field. Agents with no `model` field inherit the session's model.
- **Notifications** fire when a session you are not viewing finishes. The docs do not mention
  a notification for "needs input."
- **Cross-session messaging:** sessions on one machine can list and message each other. The
  Code tab's session list does not show CLI sessions.
- **Suggested tasks:** a session can propose work as a card with Start, Do it here, Options,
  and Start all. This is how a planner offers one session per ticket.
- **Pull requests:** Auto-fix answers review comments, and "Merge when ready" requests a
  squash merge. Both need `gh`, and both are disabled in SSH sessions.
- **Archive:** Desktop removes an archived worktree after about 30 days. Uncommitted changes
  can be lost.

### Outside guidance: Anthropic's "Solving code review at Anthropic" post

Source: https://claude.dev/blog/solving-code-review-at-anthropic/, read 2026-11-06. The user
wants the workflows to rest on outside expertise like this, not on magito's own history.
Practices that fit a solo developer (team-only ones, such as two-person approval, merge
queues, and staged releases, are left out):

- The agent runs the tests, build, and linter and shows the output, not a claim of success.
  Giving the agent a way to check its own work is the biggest single gain.
- A fresh-context review runs before the pull request exists (`/code-review`).
- Review depth matches the risk of the change, set by what the change touches, not by who
  wrote it. Low risk (docs, copy, additive flagged changes) needs no human read once checks
  pass.
- Review rounds are capped. After three rounds, the reviewer asks the author to rethink the
  approach. Later rounds re-review only the new diff. One finding names the whole class of bug
  so every instance gets fixed.
- Style-only findings are dropped. Noise costs more with agents: each nit becomes a commit and
  another round.
- Each finding is labeled Important, Nit, or Pre-existing. Old bugs in untouched code are
  labeled, not fixed in the current change.
- Every finding is answered: fixed, or dismissed with a reason.
- A recurring problem is fixed at its source: a skill, a lint rule, or `CLAUDE.md`.
- A `REVIEW.md` says what failure looks like in the repo, caps nits, requires file-and-line
  evidence, and starts the summary with a count.
- The pull request template asks how the change was tested, its risk, and how to revert it.
- Changes stay small. Most pull requests over 1,000 lines get findings.
- To understand code before changing it, ask Claude to explain the module, rather than read
  trivial diffs line by line.

### Outside guidance: Anthropic's Claude Code docs on cleanup and tests

Sources: code.claude.com/docs/en/best-practices, common-workflows, commands,
code-review-local; anthropic.com/engineering/harness-design-long-running-apps. Read
2026-11-06. Anthropic publishes nothing on how many tests to write, on mocks, on
characterization tests, or on a project-wide rigor setting.

- Before a refactor, give Claude a pass/fail check: a test file, a build exit code, a linter,
  or a script that compares output with a saved example. Refactor in small, testable steps
  and run the tests after each.
- Ask for the command run and its output. "All tests pass" alone tells you very little.
- A reviewer told to find problems will always find something. Fixing every finding can add
  tests for cases that cannot happen.
- For a bug, write a failing test that reproduces it, then fix it.
- `/simplify` is a bundled skill. It reviews changed code for reuse, simplification,
  efficiency, and abstraction level, and applies the fixes. It does not look for bugs, and it
  looks only at changed code, not at a whole existing module.
- `/code-review` has effort levels: `low` reports only its most confident findings; higher
  levels widen coverage. `--fix` applies findings and `--max-findings` caps the count.
- `/verify` builds and runs the app and watches the result, instead of relying on tests.
- Depth scales by the change, not the project: raise effort for bugs in code you did not
  write, flaky tests, or schema changes with many readers; lower it for renames.

## Open questions

None.
