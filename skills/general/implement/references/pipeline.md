# The steps every ticket runs

Every ticket runs these twelve steps, whether it comes from an accepted intent or not, alone
or in a batch. `SKILL.md` runs first: it shows the start line and, for a ticket with no
accepted intent, stops once for plan approval. From here on the run goes to an open pull
request with no approval stop. The human hears from you only for an escalation, and at the
merge. Commands run from your working directory; `<skills>` is your tool's installed skills
directory, as in `SKILL.md`.

## Steps

1. **Worktree.** Run `bash <skills>/implement/scripts/gitflow.sh worktree add <branch>`, with
   the branch name only. Never pass a path: the script puts the worktree at
   `.magito/worktrees/<branch>` in the main checkout, which git ignores, and a path you pick
   can land among tracked files. Never run raw
   `git worktree add`: only `gitflow.sh` gives the branch a review marker (`docs/adr/0014`).
   The new branch starts from the base branch, wherever you run the command from.
2. **Red run.** Only when the ticket names a red check. Before any code change, run it. Save
   the command and its failing output. If it passes before any change, escalate with rule 4.
   Make no commits: the check proves nothing. A ticket with only a reviewable check skips
   this step.
3. **Build.** You build, or the worker the user named builds, per
   [worker-contract.md](./worker-contract.md). When step 2 ran, commit the test files from the
   red step first, in their own commit, and record that commit. Those test files are locked
   from then on. A test case that the builder adds after that commit goes in a
   second test file, such as `test_<name>_more.py`, registered wherever the first one is.
   Hold this floor at every seam. It applies even when the ticket's acceptance criteria say
   nothing about tests; they are a floor, not the ceiling:
   - Red-green where the behavior is specifiable in advance: watch the test fail for the right
     reason first. Pin-and-guard (characterization, eval threshold, smoke) where it is not.
   - ALWAYS invariant and schema checks at every data boundary the diff crosses:
     columns/dtypes/nullability, no NaN/inf where forbidden, values in range, row counts, key
     uniqueness, no train/test leakage.
   - Run typechecks and single test files as you go. Reach the `verifying` skill for the full
     method behind this floor.
   - Commit with `bash <skills>/implement/scripts/gitflow.sh commit "<conventional message>"
     <file>...`, which stages only the files you name. Curate into coherent commits; never
     `git add -A`. When a worker built, first look at every change the worker left, staged
     or not, as [worker-contract.md](./worker-contract.md) says.
4. **Check.** Run the repo's check command yourself. Read `check` from `.magito/config.toml`
   at the main worktree root. When that file is absent, use the check command that `CLAUDE.md`
   or `AGENTS.md` names. When you find no check command, escalate with rule 5. A worker's own
   "tests pass" never counts.
5. **Commit test.** Run `bash <skills>/implement/scripts/gitflow.sh ahead` in the worktree.
   It refuses a tree with uncommitted changes: commit or discard each change it lists, then
   run it again. It prints how many commits the branch has that the base lacks. When it
   prints `0`, the run made no change to merge: go to step 11. When it prints `1` or more,
   continue.
6. **Review.** Use the reviewer from the start line. There are two exceptions.
   - After step 8 exited 6, use the worker that the exit 6 message named, for this round and
     every later one.
   - When a round fails because the reviewer itself failed, choose the reviewer for the next
     round in two moves, with no judgment of your own. A reviewer fails when `worker.py
     review` exits with anything other than 0, 4, and 5: a timeout, a lost login, a used-up
     quota.
     1. Run `python3 <skills>/implement/scripts/worker.py reviewer <builder-family> --skip
        <name>`, with one `--skip` for every worker that has failed a round in this run, not
        only the latest. When it prints a worker, use that worker for the next round and for
        the record.
     2. When move 1 prints no worker, run `python3 <skills>/implement/scripts/worker.py
        reviewer <builder-family>` with no `--skip`. When it prints a worker, a worker that
        failed earlier still answers its probe: run the next round with the worker it prints.
        When it prints no worker, no roster worker of another family is working any more:
        review with a fresh-context subagent, and record `subagent` in step 8.

     Move 2 gives the same answer as step 8's own check: `worker.py record ... subagent` is
     refused exactly when plain `worker.py reviewer <builder-family>` prints a worker. So the
     run reaches a subagent only when the roster has no working reviewer, and never by choice.
     A failed round counts toward the limit of three in step 7. When the three are used
     without a pass, stop with escalation 2 and quote the reviewer's failure.

   How a round runs, whoever reviews. The builder family is the family of the model that
   wrote the code. The brief holds the ticket body, the output of `git diff <base>...HEAD`,
   the reply format in [worker-contract.md](./worker-contract.md), and the reviewer rules from
   that file. When step 2 ran, the brief also names the red-step commit and the locked test
   files. The reviewer answers `VERDICT PASS`, or one or more `VERDICT FIX: <finding>` lines,
   and changes no files. Write the brief to a file outside the worktree with your file-writing
   tool.
   - **A roster worker reviews.** Run the round as one command:
     `python3 <skills>/implement/scripts/worker.py review <reviewer> <worktree> <brief-file>`.
     It snapshots the worktree's tracked and untracked files, runs the reviewer, snapshots
     again, and prints only the verdict lines. It names the file holding the full output on
     stderr. Exit 4 means the reviewer changed files: discard its verdict, restore every file
     it changed to the committed state, delete any file it created, and review again. Exit 5
     means the reply held no verdict line: review again. Each such repeat counts toward the
     limit of three in step 7.
   - **A subagent reviews.** This happens when the start line said `reviewer: none from
     another family, using a subagent`, or when move 2 above printed no worker. Give the same
     brief to a fresh-context subagent. Prove it changed no files with the snapshot pair from
     `to-issues` step 5, using `<worktree>` as the root.
   - **Neither is possible.** When no roster worker is available and the tool you run in
     cannot start a fresh-context subagent, stop with escalation 7.
7. **Fix rounds.** A review round is one run of step 6, by a roster worker or by a subagent.
   The builder's family writes the fixes. The reviewer was picked to differ from the
   builder's family, and that pick covers nothing another family writes. So fix the
   findings yourself only when you built, or when your family equals the builder's. When a
   worker of another family built, send the findings back to that worker with a new brief
   per [worker-contract.md](./worker-contract.md), and commit the fix it left, staged or
   not, as that file says. Write no fix yourself on that branch.
   On a FIX verdict, do these in order: fix the findings, commit the fix with
   `gitflow.sh commit`, run the check again as in step 4, and only when the check is green
   run the next review round on that commit. Never carry a check result across a fix: the
   check that counts for step 8 is the one run after the last commit. Run at most three
   review rounds. Before you accept a fix round, run
   `git diff --name-only <red-step-commit> HEAD` and reject the round if it lists a locked
   test file. Passing that needs a locked test changed: escalate with rule 3. Committing every
   fix before the next round and before step 8 also means the review record names the commit
   that holds the fixes, and `gitflow.sh pr` refuses a tree with uncommitted changes.
8. **Record.** On PASS with the check green, where the check ran after the last commit, run
   `python3 <skills>/implement/scripts/worker.py record <worktree> <builder-family>
   <reviewer>`. `<reviewer>` is the worker's name, or the word `subagent`. The command writes
   the review marker that `gitflow.sh worktree add` created in step 1, and that `gitflow.sh
   pr` and `gitflow.sh merge` require. Never write the marker file in any other way. This
   step runs whether or not the repo has a remote. Exit 6 names a roster worker that answers
   its probe: go back to step 6 and review with that worker. That review is the next round
   under the same limit of three. When the three rounds are already used, stop with
   escalation 2 and quote the exit 6 message.
9. **Pull request.** When `git remote -v` prints a remote, run `gitflow.sh push` and
   `gitflow.sh pr <issue> "<title>" "<body>"`. Write the body per [pr-body.md](./pr-body.md).
   PR creation stays on `gitflow.sh pr` and never routes through the tracker config
   (`docs/adr/0015`). Never merge: the merge button is the human's gate.
10. **No remote.** When `git remote -v` prints nothing, skip step 9. There is no pull request
    to gate, so this checkpoint is the human's merge gate, and it stays a question. Show the
    diff and the review summary, stop, and ask whether to merge. Only on explicit approval run
    `gitflow.sh merge`, a `--no-ff` merge into the base branch, then perform the **close a
    ticket** operation. Never merge without that approval.
11. **No commit.** This is the ending for a branch with no commit ahead of the base. The
    review runs when the branch has a commit, and a branch with none holds no change to
    review. Perform the **comment on a ticket** operation with the findings, in ordinary words
    and with no magito term. Leave the ticket open: the user decides what happens next. Open
    no pull request, run no review, and write no review record. Remove the worktree with
    `gitflow.sh worktree remove <path>`.
12. **Last message.** Write no file for this. The run's last message to the user has one of
    three forms:
    - After a pull request: who built, who reviewed (the worker's name and family, or a
      subagent), how many review rounds ran, what the reviewer found, and the pull request
      link.
    - At the checkpoint with no remote (step 10): the message that asks whether to merge is
      this last message. It holds a summary of the diff, the branch name, who built, who
      reviewed, how many review rounds ran, and what the reviewer found, and it ends with the
      question. After the user approves and the merge is done, one short line confirms the
      merge.
    - After the "No commit" ending: who did the work, that no review ran because the run made
      no change, and the findings.

    The pull request body carries none of the review facts. This message is where the user
    reads them.

## Escalations: the only stops on these steps

Stop and ask the human only when one of these holds. Every other decision belongs to you:
make it, and list it in the pull request body.

1. The ticket is ambiguous in a way the intent doc does not settle.
2. Three fix rounds end without `VERDICT PASS` and a green check.
3. Passing needs a locked test changed, or work outside the ticket.
4. The red check passes before any change.
5. No check command exists.
6. In an integrated run ([integrate.md](./integrate.md)), a merge applies cleanly but the
   check is red on the integration branch: a semantic conflict.
7. No reviewer is available. No roster worker of another family answers, and the tool you
   run in cannot start a fresh-context subagent.

Each escalation message names the rule number and quotes the evidence: the ambiguous
sentence, the last verdicts and check output, the changed locked file, the red check output,
the places you looked for a check command, the merge and the failing check, or the start line
or the output of `worker.py reviewer`. A message for rule 7 also tells the user to run the
`workers` skill to see why no roster worker answers. A run stopped by rule 7 never runs
`worker.py record ... subagent`: that would record a review that did not happen.

Apart from these seven, the only stops are the plan stop in `SKILL.md` and the merge
checkpoint in step 10.
