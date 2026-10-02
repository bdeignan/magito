# The integrated run

Read this only when `/implement` was handed two or more tickets from the same accepted
intent: each ticket's `**Intent:**` line links the same intent doc, and the start line says
`plan: already approved`. Tickets from different intents, and tickets with no accepted
intent, follow `SKILL.md` and [parallel.md](./parallel.md). Tickets from more than one intent
never share a run.

The human accepted one intent, so the human reviews one pull request that delivers all of it.
You build the tickets one at a time, merge each onto one integration branch, run the check
after every merge, review the whole result once against the intent, and open one pull request.
The run follows [pipeline.md](./pipeline.md) for each ticket, with the changes below. Commands
run from your working directory; `<skills>` is your tool's installed skills directory.

## The run

0. **Start lines.** Before any build, run `worker.py start` with `--intent <path>` for the
   shared intent doc, once for each distinct builder, and show every line to the user, so
   that every builder is named. That is one line with `--family <your-family>` when you build
   at least one ticket yourself, and one line with `--builder <worker>` for each distinct
   roster worker the user named. A run where you build some tickets and named workers build
   the rest prints both kinds of line. The reviewer on the first line serves every review in
   the run.

   **No reviewer at all.** When a start line says `reviewer: none from another family, using
   a subagent` and the tool you run in cannot start a fresh-context subagent, no review of
   any kind is possible. Stop here, before the integration branch and before any build, with
   escalation 7 from pipeline.md.

   **One builder family per run.** The reviewer must come from a family other than the
   builder's, and the run has one final review. So every ticket in the run is built by
   builders of one family: you alone, roster workers the user named whose `family` values
   all equal each other, or you together with named workers of your own family. Check this on the start lines: every line must show the same family in
   its builder part. When the lines show more than one family, say so, name the families,
   and stop before any build so the user can pick one.
1. **Integration branch.** Name it `integrate/<NNNN>-<slug>` after the intent doc
   `docs/intent/<NNNN>-<slug>.md`. Create it from the base branch with
   `bash <skills>/implement/scripts/gitflow.sh worktree add integrate/<NNNN>-<slug>`, with the
   branch name only. If the branch already exists, this is a rerun: see "Resuming".
   Run `git config rerere.enabled true` in the repo.
2. **Order.** Read each ticket's blockers with the **blocking edges** section of
   `docs/agents/issue-tracker.md`. Build a ticket only after every ticket that blocks it is
   finished. A ticket is finished when it is merged, or when its commit test printed `0`
   (step 3): that ticket has nothing to merge, so a ticket it blocks can start. Order tickets
   with no dependency between them by ticket identifier. Build one at a time.
3. **Build each ticket** with pipeline.md steps 1 to 7 (worktree, red run, build, check,
   commit test, review, fix rounds), with these changes:
   - Name the branch `feat/<ticket-id>-<slug>`. For a local ticket, `<ticket-id>` is the
     feature folder number and the file number (`0001-01`), and `<slug>` is the rest of the
     file name. For a tracker with issue numbers, `<ticket-id>` is the number.
   - Create the ticket's branch from the current integration branch, so the ticket sees every
     ticket merged before it.
   - In pipeline.md step 5, the commit test for a ticket branch is
     `gitflow.sh ahead integrate/<NNNN>-<slug>`. When it prints `0`, do not review and do not
     merge that branch. Post the findings on the ticket as a comment, name them in the last
     message, remove that ticket's worktree with `gitflow.sh worktree remove <path>`, and go
     on to the next ticket. When the findings show that a ticket it blocks cannot be built as
     written, stop with escalation 1 and quote the findings.
   - Stop a ticket after a `VERDICT PASS` with a green check. Skip pipeline.md steps 8 to 10
     for the ticket: no record and no pull request per ticket.
4. **Merge.** In the integration worktree, run `git merge --no-ff <ticket-branch>`, then run
   the full check there.
   - A textual conflict that `rerere` or you resolve, followed by a green check, continues.
     Note each conflict and how you resolved it for the pull request body.
   - A merge that applies cleanly but turns the check red is a semantic conflict. Undo the
     merge with `git reset --hard HEAD^` so the integration branch stays green, keep the ticket
     branch, and stop with escalation 6 (below). Never edit a locked test to get past it.
5. **Final review.** After the last ticket, run `gitflow.sh ahead` in the integration
   worktree. Decide from that number, never from whether this run's tickets made commits: on
   a resumed run the branch can hold merges from an earlier run.
   - `0`: the branch holds no change. Run no final review, write no review record, and open
     no pull request. Each ticket already has its findings comment, and each ticket's worktree
     was removed at its own commit test. Remove the integration worktree with
     `gitflow.sh worktree remove <path>`, so that the run leaves no worktree behind, and end
     with the last message in its "No commit" form, covering every ticket.
   - `1` or more: review the whole branch, even when no ticket in this run added a commit.
     First run the full check in the integration worktree, whatever earlier steps ran: the
     final review and the record in step 6 rest on a green check run after the last commit
     on the branch. A red check here, with no merge left to undo, is a semantic conflict from
     an earlier merge: stop with escalation 6. Then use the reviewer from the start line and run the round as pipeline.md step 6 describes,
     against the integration worktree. Give it the whole intent doc and the output of
     `git diff <base>...integrate/<NNNN>-<slug>`. It answers exactly one of these lines, plus
     any `VERDICT FIX: <defect>` lines:
     - `COVERAGE PASS`
     - `COVERAGE FIX: <missing or wrong outcome>`
     - `COVERAGE AMBIGUOUS: <what the intent does not settle>`

     On FIX, fix on the integration branch through the fix rounds in pipeline.md step 7,
     which include running the check again on the integration branch after each fix and
     before the next final review. On AMBIGUOUS, stop with escalation 1 from pipeline.md.
6. **One pull request.** On `COVERAGE PASS` with no `VERDICT FIX` and a green check, run
   `worker.py record <integration-worktree> <builder-family> <reviewer>`, as pipeline.md step
   8 describes. Exit 6 means the record was refused because a roster worker answers its
   probe: run the final review of step 5 again with the worker the message named, on the
   whole diff against the intent doc, and act on its `COVERAGE` and `VERDICT` lines as
   before. That review counts toward the final review's limit of three rounds. When the three
   are used, stop with escalation 2 and quote the exit 6 message. Record only after that
   worker's review passes. Then open the pull request as pipeline.md step 9 describes: run
   `gitflow.sh push` and `gitflow.sh pr <first-ticket> "<title>" "<body>"` from the
   integration worktree. Never merge.
   - The script appends `Closes #<first-ticket>` itself. Put one `Closes #<n>` line in the body
     for every other ticket, as [pr-body.md](./pr-body.md) says. GitHub closes every issue
     named on a `Closes` line.
   - For a tracker that has no `Closes` lines, such as the local tracker, perform **close a ticket** for each ticket after
     the merge instead.
   - Beyond the sections in pr-body.md, the body lists each ticket it delivers, and each
     merge conflict with how you resolved it. It lists nothing about the reviews: the rules
     in pr-body.md hold for this pull request too.
   - With no remote (`git remote -v` prints nothing), stop at the merge checkpoint in
     pipeline.md step 10, and ask about the merge of the integration branch.
7. **Last message.** The run ends with one last message for the whole run, in the form
   pipeline.md step 12 gives.

## Resuming

A rerun with the integration branch present picks up where the last run stopped.

- Before anything else, run the full check in the integration worktree. The earlier run can
  have stopped between a merge and its check, so a merged branch does not prove a green
  branch. When the check is red, the last merge is a semantic conflict: undo it as step 4
  says and stop with escalation 6.
- A ticket is done when `git branch --merged integrate/<NNNN>-<slug>` lists its branch. Skip
  done tickets entirely: no build, no review, no second merge.
- A ticket branch that exists but is not merged resumes from its last commit. First run the
  commit test for it, `gitflow.sh ahead integrate/<NNNN>-<slug>`. When it prints `0`, treat it
  like any other ticket with no commit: no review, no merge, a findings comment on the ticket
  unless an earlier run already posted one, and the ticket's worktree removed. Otherwise run
  the check and the review again on it, then merge it as in step 4. Do not rebuild it, and do
  not rebase it or merge the integration branch into it.
- Do not create a second integration branch. `gitflow.sh worktree add` reuses the existing one.

## Escalations added by this run

Pipeline.md lists every stop, and all of them apply to each ticket in the run. One of them
arises only here:

- **Escalation 6, semantic conflict.** A merge applied cleanly, but the check is red on the
  integration branch. That includes a red check found at the start of a resumed run, or just
  before the final review. Name it "escalation 6" and "semantic conflict" in the message. Quote the
  ticket branch, the merge, and the failing check output. Open no pull request.

An ambiguous coverage verdict is escalation 1 in pipeline.md, quoted with the reviewer's
`COVERAGE AMBIGUOUS` line.
