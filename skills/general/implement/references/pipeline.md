# The pipeline path

Use this path for one pipeline ticket, as `SKILL.md` defines it. The human already signed off
on what to build when they accepted the intent, so this path runs from build to an open pull
request without approval stops. The human hears from you only for an escalation, and at the
merge. Commands run from your working directory; `<skills>` is your tool's installed skills
directory, as in `SKILL.md`.

## Steps

1. **Worktree.** Run `bash <skills>/implement/scripts/gitflow.sh worktree add <branch>`, with
   the branch name only. Never pass a path: the script picks a folder beside the repo, and
   a path inside the repo nests the worktree in the main checkout. Never run raw
   `git worktree add`: only `gitflow.sh` gives the branch a review marker (`docs/adr/0014`).
2. **Red run.** Before any code change, run the ticket's red check if it has one. Save the
   command and its failing output. If it passes before any change, escalate with rule 4. Make
   no commits: the check proves nothing.
3. **Build.** Build it yourself, or through a worker per
   [worker-contract.md](./worker-contract.md). Commit the test files from the red step first,
   in their own commit, and record that commit. Those test files are locked from then on.
4. **Check.** Run the repo's check command yourself. Read `check` from `.magito/config.toml`
   at the main worktree root. When that file is absent, use the check command that `CLAUDE.md`
   or `AGENTS.md` names. When you find no check command, escalate with rule 5. A worker's own
   "tests pass" never counts.
5. **Review.** Pick the reviewer with
   `python3 <skills>/implement/scripts/worker.py reviewer <builder-family>`. The builder
   family is the family of the model that wrote the code. Give the reviewer the ticket body
   and the output of `git diff <base>...HEAD`, plus the reply format in
   [worker-contract.md](./worker-contract.md). It answers `VERDICT PASS`, or one or more
   `VERDICT FIX: <finding>` lines, and changes no files. Write the brief to a file outside the
   worktree with your file-writing tool, then run the round as one command:
   `python3 <skills>/implement/scripts/worker.py review <reviewer> <worktree> <brief-file>`.
   It snapshots the worktree's tracked and untracked files, runs the reviewer, snapshots
   again, and prints only the verdict lines. It names the file holding the full output on
   stderr. Exit 4 means the reviewer changed files: discard its verdict, revert the change,
   and review again. Exit 5 means the reply held no verdict line: review again.

   When `worker.py reviewer` finds no reviewer (exit 3), review with a fresh-context
   subagent instead, and say so in the pull request body. Prove it changed no files with the
   snapshot pair from `to-issues` step 5, using `<worktree>` as the root.
6. **Fix rounds.** On FIX, fix the findings, run the check again, and review again. Run at
   most three review rounds. Before you accept a fix round, run
   `git diff --name-only <red-step-commit> HEAD` and reject the round if it lists a locked
   test file. Passing that needs a locked test changed: escalate with rule 3.
7. **Pull request.** On PASS with the check green, record the review decision in the marker
   as `<sha> reviewed`. The marker is `<main-worktree-root>/.magito/review-<branch-slug>`,
   which `gitflow.sh worktree add` created in step 1. Read the sha, the branch, and the main
   worktree root with separate commands, then write the file with your file-writing tool,
   as the `reviewing-changes` skill does. Then
   run `gitflow.sh push` and `gitflow.sh pr <issue> "<title>" "<body>"`. Write the body per
   [pr-body.md](./pr-body.md), including its pipeline section. Never merge.
8. **No remote.** When `git remote -v` prints nothing, do not run step 7. Stop at the no-PR
   checkpoint in step 8 of `SKILL.md`. That checkpoint is the human's merge gate, so it stays
   a question: show the diff and the review summary, and ask whether to merge.

## Escalations: the only stops on this path

Stop and ask the human only when one of these holds. Every other decision belongs to you:
make it, and list it in the pull request body.

1. The ticket is ambiguous in a way the intent doc does not settle.
2. Three fix rounds end without `VERDICT PASS` and a green check.
3. Passing needs a locked test changed, or work outside the ticket.
4. The red check passes before any change.
5. No check command exists.
6. In an integrated run ([integrate.md](./integrate.md)), a merge applies cleanly but the
   check is red on the integration branch: a semantic conflict.

Each escalation message names the rule number and quotes the evidence: the ambiguous
sentence, the last verdicts and check output, the changed locked file, the red check output,
or the places you looked for a check command, or the merge and the failing check. Apart
from these six, the only stop is the
no-remote merge checkpoint in step 8.
