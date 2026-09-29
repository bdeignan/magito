# The integrated run

Read this only when `/implement` was handed two or more pipeline tickets (see the first rule
of [SKILL.md](../SKILL.md)) that link the same intent doc. Tickets from different intents, and
tickets that are not pipeline tickets, keep the paths in `SKILL.md`. Tickets from more than one
intent never share a run.

The human accepted one intent, so the human reviews one pull request that delivers all of it.
You build the tickets one at a time, merge each onto one integration branch, run the check
after every merge, review the whole result once against the intent, and open one pull request.
The run follows [pipeline.md](./pipeline.md) for each ticket, with the changes below. Commands
run from your working directory; `<skills>` is your tool's installed skills directory.

## The run

1. **Integration branch.** Name it `integrate/<NNNN>-<slug>` after the intent doc
   `docs/intent/<NNNN>-<slug>.md`. Create it from the base branch with
   `bash <skills>/implement/scripts/gitflow.sh worktree add integrate/<NNNN>-<slug>`, with the
   branch name only. If the branch already exists, this is a rerun: see "Resuming".
   Run `git config rerere.enabled true` in the repo.
2. **Order.** Read each ticket's blockers with the **blocking edges** section of
   `docs/agents/issue-tracker.md`. Build a ticket only after every ticket that blocks it is
   merged. Order tickets with no dependency between them by ticket identifier. Build one at a
   time.
3. **Build each ticket** with pipeline.md steps 1 to 6, with these changes:
   - Name the branch `feat/<ticket-id>-<slug>`. For a local ticket, `<ticket-id>` is the
     feature folder number and the file number (`0001-01`), and `<slug>` is the rest of the
     file name. For a tracker with issue numbers, `<ticket-id>` is the number.
   - Create the ticket's branch from the current integration branch, so the ticket sees every
     ticket merged before it.
   - Stop after a `VERDICT PASS` with a green check. Do not record a marker and do not open a
     pull request for the ticket.
4. **Merge.** In the integration worktree, run `git merge --no-ff <ticket-branch>`, then run
   the full check there.
   - A textual conflict that `rerere` or you resolve, followed by a green check, continues.
     Note each conflict and how you resolved it for the pull request body.
   - A merge that applies cleanly but turns the check red is a semantic conflict. Undo the
     merge with `git reset --hard HEAD^` so the integration branch stays green, keep the ticket
     branch, and stop with escalation 6 (below). Never edit a locked test to get past it.
5. **Final review.** After the last merge, pick the reviewer as in pipeline.md step 5. Give it
   the whole intent doc and the output of `git diff <base>...integrate/<NNNN>-<slug>`. Keep
   the before-and-after snapshot proof that it changed no files. It answers exactly one of
   these lines, plus any `VERDICT FIX: <defect>` lines:
   - `COVERAGE PASS`
   - `COVERAGE FIX: <missing or wrong outcome>`
   - `COVERAGE AMBIGUOUS: <what the intent does not settle>`

   On FIX, fix on the integration branch through the fix rounds in pipeline.md step 6, and run
   the check and the review again. On AMBIGUOUS, stop with escalation 1 from pipeline.md.
6. **One pull request.** On `COVERAGE PASS` with no `VERDICT FIX` and a green check, record
   `<sha> reviewed` in the integration branch's marker, as pipeline.md step 7 says. Then run
   `gitflow.sh push` and `gitflow.sh pr <first-ticket> "<title>" "<body>"` from the
   integration worktree. Never merge.
   - The script appends `Closes #<first-ticket>` itself. Put one `Closes #<n>` line in the body
     for every other ticket, as [pr-body.md](./pr-body.md) says. GitHub closes every issue
     named on a `Closes` line.
   - For a tracker that has no `Closes` lines, such as the local tracker, perform **close a ticket** for each ticket after
     the merge instead.
   - Beyond the sections in pr-body.md, the body lists each ticket with its review rounds, the
     merge order, each conflict you resolved and how, and the final coverage verdict.
   - With no remote (`git remote -v` prints nothing), stop at the no-PR checkpoint in step 8
     of `SKILL.md`, and ask about the merge of the integration branch.

## Resuming

A rerun with the integration branch present picks up where the last run stopped.

- A ticket is done when `git branch --merged integrate/<NNNN>-<slug>` lists its branch. Skip
  done tickets entirely: no build, no review, no second merge.
- A ticket branch that exists but is not merged resumes from its last commit. Run the check and
  the review again on it, then merge it as in step 4. Do not rebuild it, and do not rebase it
  or merge the integration branch into it.
- Do not create a second integration branch. `gitflow.sh worktree add` reuses the existing one.

## Escalations added by this run

Pipeline.md lists every stop, and all of them apply to each ticket in the run. One of them
arises only here:

- **Escalation 6, semantic conflict.** A merge applied cleanly, but the check is red on the
  integration branch. Name it "escalation 6" and "semantic conflict" in the message. Quote the
  ticket branch, the merge, and the failing check output. Open no pull request.

An ambiguous coverage verdict is escalation 1 in pipeline.md, quoted with the reviewer's
`COVERAGE AMBIGUOUS` line.
