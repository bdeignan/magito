# How the user works with magito on Claude Code Desktop

This file says how the user works with magito on Claude Code Desktop. It is the contract
every change to magito serves. Every later intent and ticket in this overhaul
names the workflow step it serves. A change that serves no step here gets cut.

This is the target way of working. It was accepted in `docs/intent/0010-desktop-workflows.md`
on 2026-11-06. Skills are being changed to match it. Until a skill is changed, where this
file and that skill's `SKILL.md` differ, the skill says what it does today.

The workflows are written for Desktop, in local and SSH sessions. Skills stay usable in
Codex, Gemini CLI, and omp. Where a step uses a Desktop-only feature, a plain fallback is
named. On a machine without Desktop, this file is a guide, not a contract.

## Names used here, and today's names

This file uses the new skill names. Some skills do not have them yet.

| Name in this file | Today's name |
|---|---|
| `intent-interview` | `intent` |
| `intent-to-tickets` | `to-issues` |
| `ticket-to-pr` | `implement` |
| `ticket-conformance-check` | `reviewing-changes` |
| `session-catch-up` | `catch-up` |
| `session-handoff` | `handoff` |
| `audit-code-cruft` | `decruft` |
| `which-workflow-now` | not built yet |

`/code-review`, `/simplify`, `/verify`, and `/fork` are built into Claude Code.

## Session roles

- **Planner:** Opus, in the main checkout, with Worktree off. It runs `intent-interview`,
  `intent-to-tickets`, `session-catch-up`, `session-handoff`, `audit-code-cruft`, and
  `ticket-conformance-check`.
- **Worker:** Sonnet, with Worktree on. It runs `ticket-to-pr` and nothing else. The
  planner's session card sets its model.

A role's permission mode is named by what the role needs, never as a fixed mode:

- The planner needs a mode that allows file edits, because `intent-interview` writes its doc
  from the first question. Plan mode allows no edits, so it is not the planner's mode.
- The worker needs a mode that runs the build's edits and commands without asking.
  Auto does that today. A session card can grant only a mode the planner itself has, so the
  planner runs in Auto too.
- A new mode can replace either one without a change to this file.

## Risk levels

Every ticket carries a Risk field, set by `intent-to-tickets`. It sets both how the user
reviews the change and how much testing it gets.

| Risk | Covers | The user's review | Tests |
|---|---|---|---|
| Low | Docs, comments, copy, deleting dead code | Read the pull request summary and the check output only. The worker opens a Low ticket's pull request right after its "ready to read" message: the one exception to "no pull request before your read" | The existing check passes |
| Normal | Ordinary changes; the default | Read the diff | One test for the new behavior; for a bug, a failing test first |
| High | A contract other tickets rely on, data at external edges, security, CI or install config | Read the diff and run `ticket-conformance-check`. The worker runs `/code-review` at a higher effort | Data checks at the boundaries it touches |

The worker can raise a ticket's risk when the code proves riskier than the ticket said. It
never lowers it.

## Desktop basics

A short list, for a reader new to the app:

- Worktrees are off by default. Turn on Worktree before starting a worker session.
- Cmd/Ctrl+Shift+D toggles the diff pane. The changed-line counts sit in the Changes card and
  in the title bar's Changes button.
- To comment on a line, click the + by its line number, type, and press Enter.
  Cmd/Ctrl+Enter submits several comments. Claude revises and shows a new diff.
- `/code-review` is how Claude reviews its own diff. There is no review button.
- Split view: Option/Alt-click a session, or right-click it, then Open in, then Split view.
  Cmd/Ctrl-click opens a session in its own window. Ctrl+Tab cycles sessions.
- The terminal (Ctrl+`) works in local and SSH sessions.
- In an SSH session, Desktop installs Claude Code under `~/.claude/remote/` on first connect
  and reads skills from the VM. Run `python install.py` from the magito checkout on the VM,
  and keep both checkouts current with `git pull`.
- Shell environment variables do not reach the app. Put what a session needs in the local
  environment editor (the gear icon), one `KEY=value` per line.
- Desktop sends a notification when a session you are not viewing finishes. Turn
  notifications on.
- A session can offer work as a suggested-task card with Start, Do it here, and Start all.
- "Merge when ready" and Auto-fix need `gh` and are disabled in SSH sessions.
- Archiving a session: Desktop removes its worktree about 30 days later. Uncommitted changes
  can be lost.

## Workflow A: from an idea to working code

For an idea whose approach is not yet known to work.

1. **Spike (worker).** Open a worker session with Worktree on. Give it this prompt shape:
   "Spike: get X working end to end on one real fixture. One smoke run only, no other tests,
   no refactoring. Stop when the fixture produces output." Do not watch it.
2. **Keep or toss (user).** Run it once yourself. If the approach fails, archive the session.
   If it works, write two sentences on what you learned about the shape of the solution.
3. **`intent-interview` (planner).** Paste the two sentences and name the spike branch.
   Answer one question at a time. Say "accept" when no open question is left.
4. **`intent-to-tickets` (planner).** It runs on its own after "accept" and publishes the
   tickets. Then the planner stops and builds nothing. It offers one session card per ticket
   that is ready to start. A ticket that depends on no other gets its card at once. A ticket
   that depends on another gets its card once that one is merged. Outside Desktop, the
   fallback is a line such as "run `/ticket-to-pr 14` in a new session."
5. **Workflow B for each ticket.**

Skip the spike when the change already fits one ticket and you can state its "done when" now.
Then tell the planner "ticket it", and go to Workflow B. If you keep retyping the spike
prompt, that is the signal to make it a skill.

## Workflow B: one ticket, start to merge

1. **Start the worker.** Click the planner's card, or open a session yourself with Sonnet,
   Worktree on, and Auto. Do not run `session-catch-up`: the ticket is the worker's whole context.
2. **`/ticket-to-pr <n>`.** It fetches the ticket and builds it. For a ticket no accepted
   intent covers, it stops once to show a plan for you to approve.
3. **The worker's checks, in this order:**
   1. Run the check command.
   2. On Normal and High tickets: run `/simplify`, then the check again. `/simplify` comes
      before `/code-review` because it changes code.
   3. Run `/code-review` and fix what it finds, at most three rounds. On High tickets, run it
      at a higher effort. Later rounds re-review only the new diff. After round three, the
      worker stops and says the approach can need rethinking.
   4. Run `/verify` when the change has something to run: an app or a command-line tool. A
      library skips it.

   A finding in code the ticket did not touch is labeled Pre-existing. It is not fixed in
   this change. It goes to the planner as "ticket it" (Workflow D).
4. **"Ready to read".** The worker stops and sends one message: the commands it ran and their
   output (not a claim that they passed), each finding marked fixed or dismissed with a
   reason, and the ticket's risk. No pull request exists yet, except on a Low ticket: the
   worker opens its pull request now (see Risk levels).
5. **Your read, by risk** (see Risk levels). For a diff in an area you do not know, first ask
   the worker to explain the module. Leave line comments where you want changes.
6. **Revise.** The worker revises from your comments. Repeat step 5 as needed. Your rounds
   have no cap.
7. **Open the pull request.** On Normal and High tickets, tell the worker to open it. Every
   pull request body, a Low ticket's included, has a Testing field and a Risk field (the
   ticket's level). It has a "How to revert" field only when reverting the pull request is
   not enough, such as a data migration or a config change.
8. **Merge and archive.** You own every merge. In a local session you can press "Merge when
   ready": it waits for CI, then squash-merges. In an SSH session, merge on GitHub. A worker
   never presses it and never asks GitHub to merge. Then archive the session and start the
   next ticket in a fresh one.

Outside Desktop, where `/simplify`, `/code-review`, or `/verify` does not exist: the fallback
for `/simplify` is the build ladder in the shared instructions, and the fallback for
`/verify` is one manual run. Your own read is the review.

## Workflow C: a backlog day

1. **Pick the day's tickets (planner).** Run `session-catch-up`, then ask: "List the unblocked
   tickets. Which two or three do not touch the same files?"
2. **Workflow B for each ticket.** One session at a time by default. Two at once only when
   the planner said they are independent.
3. **Batch small tickets.** Three small, well-specified tickets can go to one worker as
   `/ticket-to-pr 14 15 16`. It builds each in turn and stops at "ready to read" for each,
   as in Workflow B step 4. Pull requests open as in Workflow B: a Low ticket's opens right
   after its "ready to read" message. A Normal or High ticket's opens only after you have read
   that ticket's diff and told the worker to. Each ticket gets its own pull request.
4. **Design questions go to the planner.** If a worker finds its ticket ambiguous, stop it,
   ask the planner, and either amend the ticket or write the answer into the worker's
   session.

## Workflow D: side quests

The rule behind every row: one ticket per pull request, so each diff stays small enough to
read.

| What you found | What to do | Where |
|---|---|---|
| Independent and small: a bug elsewhere, a typo | Fix it now, in its own pull request | A new worker session: "ticket it" first, then Workflow B; or just fix it if it is one line |
| Needs what the current session already knows | `/fork` the session, then ask it to work in a new worktree | Inside the current worker |
| A prerequisite for the current ticket | Pause the feature. Build the prerequisite as its own pull request off the base branch, merge it, then have the paused worker rebase | A new session for the prerequisite |
| "I built this slightly wrong earlier" | Do not fix it inline; it changes the design. Tell the planner "ticket this". If it changes a contract other tickets rely on, the planner amends those tickets | The planner |
| Big, or not urgent, or a Pre-existing finding | Ticket it and keep going | The planner: "ticket it: <one line>" |

`/fork` copies the conversation into a new background session with the same model,
permission mode, and effort. Which branch a new Desktop worktree starts from is not in the
Desktop docs. Check it the first time you use this table.

## Workflow E: rationalize an existing codebase

For a codebase with too much code and too many tests. The goal is to shrink it without
changing what it does.

1. **Audit (planner).** Run `audit-code-cruft` on one area at a time. It lists what to cut,
   with evidence.
2. **Tickets (user and planner).** Pick which findings to accept. Each accepted group becomes
   a ticket.
3. **Build.** Each ticket goes through Workflow B as one small pull request.

One rule of its own: before cutting, confirm a check fails when behavior changes. For a
library, that is tests that call its public functions. For an app, it is one real end-to-end
use. If no such check exists, the first ticket writes one.

## Workflow F: start and end of day

1. **Morning (planner).** Run `session-catch-up`. It reads the newest two journal entries,
   the docs, open tickets, git state, and pull requests. When live state and the journal
   disagree, live state wins.
2. **Lost the thread.** Reread this file. `which-workflow-now` will answer "where was I?"
   once it is built.
3. **Evening (planner).** Run `session-handoff`. It writes one journal entry, under 300
   words, most of it the gotcha. Name the next day's focus.
   - Only planner sessions write journal entries, one when the planner's work ends. Worker
     sessions never write one: a worker's record is its pull request and its ticket.
   - A gotcha found in a worker reaches the journal when you tell the planner about it.
4. **Fix at the source.** When the same review comment comes up again, the planner tickets a
   change to the skill or `CLAUDE.md` that let it through.

Resuming a session from the sidebar reloads its whole history. That is fine after a short
break, but costly after a long day. A fresh planner plus the journal is cheaper.
