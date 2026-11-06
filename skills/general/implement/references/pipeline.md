# The steps every ticket runs

## Contents

- Steps
- The stops

Every ticket runs these steps, whether it comes from an accepted intent or not, alone or in a
batch. `SKILL.md` runs first: for a ticket with no accepted intent, it stops once for plan
approval. The user watches the session, and reads the diff after the "ready to read" message
in step 11. Run each command as one plain call, with no `;`, `&&`, `|`, `$(...)`, or shell
variables (`docs/agents/CONVENTIONS.md`, "Commands in skills").

## Steps

1. **Where you work.** You are already in the session's own worktree; Desktop made it. Never
   create a worktree, and never run `git -C` against another checkout. Read and write only
   files inside your worktree. Fetch the ticket with the **fetch a ticket** operation in
   `docs/agents/issue-tracker.md`. With the local tracker, the ticket body is in the session's
   brief: never read the planner's `.scratch/`. The ticket body carries everything you need.
   Run `git branch --show-current`. If it prints the base branch (step 2), first create a
   branch for the ticket with `git switch -c <type>/<ticket>-<slug>`, for example
   `git switch -c fix/142-empty-body`.
2. **Base branch.** Run `git config --get magito.baseBranch`. If it prints a name, that is the
   base branch. If it prints nothing, run `git symbolic-ref --short refs/remotes/origin/HEAD`
   and drop the leading `origin/` from what it prints. Never assume `main`.
3. **Red run.** Only when the ticket names a red check, or the "Done when" that the plan stop
   stated does. Before any code change, run it. Save the command and its failing output. If it
   passes before any change, that is stop 3. Make no commit for this step: the check proves
   nothing yet. A ticket with only a reviewable check skips this step.
   When this step ran and the work adds test files for the red check, commit those test files
   first, in their own commit, and note that commit. Those test files are locked from then on.
   The build never edits a locked file. A test case added after that commit goes in a second
   test file, such as `test_<name>_more.py`, registered wherever the first one is.
4. **Build.** The test floor follows the ticket's `**Risk:**` line. A ticket with no Risk line
   counts as Normal.
   - **Low** (docs, comments, copy, deleting dead code): the existing check passes.
   - **Normal:** one test for the new behavior. For a bug, write a failing test first.
   - **High:** data checks at the boundaries the change touches: columns, types, nulls,
     ranges, row counts, key uniqueness.
   The `verifying` skill holds the full method behind these floors. If the code proves riskier
   than the Risk line says, raise the level and say so in the "ready to read" message. Never
   lower it.
5. **Check.** Read `check` from `.magito/config.toml` in your worktree (`setup-magito` lists
   that file in `.worktreeinclude`, so Claude Code copies it into each worktree). If the file
   or the key is missing, use the check command named in the repo's `CLAUDE.md` or
   `AGENTS.md`. If neither names one, that is stop 4. The check must pass.
6. **Commit** whenever the check passes: after the build, after `/simplify`, and after each
   round of review fixes. Run `git add <file>` for each file you changed, by name, then
   `git commit -m "<title>"` with a Conventional Commits title. Leave changes you did not make
   unstaged. Never run `git add -A`, `git add .`, or `git commit -a`.
7. **Simplify.** On Normal and High tickets, run `/simplify`, then the check again, then
   commit. It runs before `/code-review` because it changes code.
8. **Review.** Run `/code-review` and fix what it finds. On High tickets, run it at a higher
   effort. After each round's fixes, run the check and commit. Run at most three rounds.
   Rounds 2 and 3 review only the new diff. If findings remain after round 3, stop and tell the
   user the approach may need rethinking. A finding in code the ticket did not touch is
   labeled Pre-existing: do not fix it; list it for the planner in step 11.
9. **Verify.** Run `/verify` when the change has something to run: an app or a command-line
   tool. A library skips this step.

   Where `/simplify`, `/code-review`, or `/verify` does not exist in the tool you run in: in
   place of `/simplify`, apply the build ladder in the shared instructions. In place of
   `/verify`, do one manual run. In place of `/code-review`, say that none ran, because the
   user's read is then the review.
10. **Commit test.** Run `git rev-list --count <base>..HEAD`. If it prints `0`, the branch
    holds no change: perform the **comment on a ticket** operation with your findings, in
    ordinary words, and open nothing. Leave the ticket open.
11. **"Ready to read".** Send one message. It holds each command you ran and its output (not a
    claim that it passed), each finding marked fixed or dismissed with a reason, the
    Pre-existing findings, and the ticket's risk. On a High ticket, add that the user's read
    includes `reviewing-changes` (the conformance check). On a Normal or High ticket, stop
    after this message and wait for the user.
12. **Pull request.** When `git remote -v` shows a GitHub remote: on a Low ticket, open it now,
    right after the "ready to read" message. On Normal and High tickets, open it only when the
    user says to. First run `git status --short`. If it shows a change you made that is not
    committed, commit it, or stop and say why. Then run `git push -u origin <branch>`, then
    `gh pr create --base <base> --title "<title>" --body "<body>"`. Write the body per
    [pr-body.md](./pr-body.md) and pass it as one argument. Write no file for it.
13. **No GitHub remote.** When `git remote -v` prints nothing, or a remote that is not on
    GitHub, open nothing. Tell the user the branch is ready, and that the planner merges it in
    the main checkout with `git merge --no-ff <branch>` after the user approves.
14. **Never merge.** Never press "Merge when ready" and never ask GitHub to merge.

## The stops

Apart from the plan stop in `SKILL.md` and the "ready to read" stop in step 11, stop and ask
the user only for these four. Each message quotes the evidence.

1. The ticket is ambiguous in a way it does not settle. Quote the sentence.
2. Passing needs a locked test changed, or work outside the ticket. Name the file or the work.
3. The red check passes before any change. Quote its output.
4. No check command exists. Name the places you looked.

The three-round cap in step 8 is the only other stop. Every other decision belongs to you:
make it, and list it in the pull request body as "Chose X over Y because Z".
