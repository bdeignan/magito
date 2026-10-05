# A batch of tickets

Read this only when `/implement` was handed **more than one** ticket and the tickets do not
all come from the same accepted intent. Tickets from one accepted intent follow
[integrate.md](./integrate.md). A batch is the ordinary steps in [pipeline.md](./pipeline.md),
run for several tickets at once: this file says only how to split the batch and run it.
`<skills>` is the folder that holds this skill's own folder: the parent of the directory its `SKILL.md` is in, as in [SKILL.md](../SKILL.md).

Carry the caller's selected tracker adapter and main worktree root through every ticket
operation below. The adapter-selection contract in [SKILL.md](../SKILL.md) applies here too.
Read local ticket files from the main root before preparing worker briefs.

## Process

1. **Collect the tickets.** From the identifiers given, or with the **list open tickets**
   operation from `docs/agents/issue-tracker.md`, keeping whatever that file says marks a
   ticket ready for an agent. Read each one with **fetch a ticket**.

2. **Split the batch.** Explore to estimate which files each ticket touches. Tickets with
   separate files run **at the same time**. Tickets that share files run **in order**, one
   after another: parallel work on the same files would only collide at merge.

3. **Decide who builds each ticket.** The rule is the one for a single ticket: you build
   unless the user names a worker. One exception follows from what a session can do. It
   cannot build several tickets at the same moment.
   - A ticket that runs in order is built by you, or by the roster worker the user named
     for it.
   - A ticket that runs at the same time as others is built by an executor. Pick it by the
     first of these that applies:
     1. The roster worker the user named for it.
     2. In Claude Code, the `executor` subagent.
     3. In any other tool that can start subagents, one subagent of that tool per ticket,
        given the same brief. Use it only when you know which model that subagent runs, and
        so its model family. When you cannot tell, treat the tool as case 4: the reviewer
        must come from a family other than the builder's, and that needs the builder's family.
     4. In a tool that cannot start subagents, there is no executor. Say so, and run those
        tickets in order with you building.

   When the user names a roster worker, run `python3 <skills>/implement/scripts/worker.py
   workers` first and name only a worker it prints. If the user names a worker it does not
   print, say so and stop. Probe a named worker once with `worker.py probe <worker>`, and
   degrade loudly per [worker-contract.md](./worker-contract.md). When the user names no
   roster worker, do not run `worker.py workers` at all: a machine with no roster file still
   runs the batch. When `worker.py thrifty` prints `on`, use the cheapest subagent model for
   in-session executors. In Claude Code, pass `model: haiku` when you start `executor`. When
   thrifty mode is off, or the command exits non-zero because the machine has no roster file,
   pass no model, so the agent file's `sonnet` applies. One setting beats the model you pass:
   on a machine that sets `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, thrifty mode cannot change
   the executor's model.

4. **Print a start line for every ticket.** Run `worker.py start` once per ticket and show
   each line to the user with its ticket. Pass `--family <your-family>` for a ticket you
   build, `--builder <worker>` for a roster worker, and `--family <executor-family> --label
   <executor-name>` for a subagent executor. The family is that of the model the subagent
   runs, which can differ from yours. In Claude Code that is `--family anthropic --label
   executor`, so the line says `builder: executor (anthropic)`; in another tool
   use `--label subagent` with that subagent's family. A subagent's line never says "this
   session". Add `--intent <path>` and `--small` for that ticket by the rules in `SKILL.md`.
   Each line names that ticket's builder, its reviewer, and whether it needs a plan.

   A subagent executor is the builder, not the reviewer. On a machine with no roster, each
   line reads `reviewer: none from another family, using a subagent`: a separate
   fresh-context subagent reviews each ticket. In a tool that cannot start subagents (case 4
   above), that line means the ticket cannot be reviewed at all: stop the batch before any
   build with escalation 7 from `pipeline.md`, "No reviewer is available".

5. **One stop for the whole batch.** Before any executor starts, show the user: which
   tickets run at the same time, which run in order and why, who builds each ticket, how many
   executors will start and which worker backs each, and a short plan for every ticket whose
   start line ends with `plan: I will show it and wait for you`. That plan includes the
   ticket's "Done when" when the ticket has none, as `SKILL.md` step 4 says. Tickets that run in order
   each get their own pull request from the base branch, so those pull requests can conflict
   with each other: name the order to merge them in. Then stop and wait for approval, once.
   When no ticket's start line asks for a plan, state the split and the builders and go on
   without a stop.

6. **Run `pipeline.md` in full for every ticket, each in its own worktree.** That includes
   the tickets that share files: each gets a worktree from the base branch, made with
   `bash <skills>/implement/scripts/gitflow.sh worktree add <branch>`. Nothing is built in the
   main checkout. A ticket that runs in order follows `pipeline.md` with no change.

   For a ticket that an executor builds, the one change is who does the build in step 3 of
   `pipeline.md`: the executor. You do every other step yourself, in the order `pipeline.md`
   gives. So before the executor starts, and when the ticket (or the "Done when" its plan
   stated) names a red check, you create
   the worktree, write the test files the red check needs, run it, save the failing output,
   and commit those test files in a commit of their own. That commit is the first on the
   branch, and the test files are locked from then on. A ticket with no red check skips this.
   Write the brief per the worker contract; it says the tests exist, names them, and forbids
   changing them. Launch a shell worker with `python3 <skills>/implement/scripts/worker.py
   run <worker> <worktree> <brief-file> [timeout]`, never a hand-built command line. Collect
   each executor's `DONE` (with its staged files) or `BLOCKED`. Background executors notify
   on completion — never poll, busy-wait, or schedule wakeups while one runs.

   After the executor reports, work inside that worktree: commit the work the executor
   left, staged or not, as [worker-contract.md](./worker-contract.md) says, as
   conventional commits, then go on from step 4 of `pipeline.md` — the check, the commit
   test, the review with the reviewer from that ticket's start line, the fix rounds, the
   record with `worker.py record`, the push, and the pull request. Those steps live in
   `pipeline.md`; this file adds none of its own.

7. **Tear down.** After a ticket's pull request is open, remove its worktree with
   `gitflow.sh worktree remove <path>`, which also clears the branch's marker. A dirty
   worktree makes it refuse: read what is there before deciding to pass `--force`. Surface
   any `BLOCKED` ticket back to the user instead of guessing.

## Cost honesty

State up front exactly how many executors you are about to launch and which worker backs each.
If the tickets turn out to share more files than expected, say so and run them in order
rather than forcing parallelism that will just conflict.
