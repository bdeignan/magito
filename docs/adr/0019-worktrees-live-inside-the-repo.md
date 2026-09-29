# Worktrees live inside the repo, under `.magito/worktrees/`

Status: accepted, 2026-09-29. Reverses the sibling-directory default that `gitflow.sh`
carried before issue #209.

`gitflow.sh worktree add <branch>` used to create each worktree beside the repo, in
`<repo>.worktrees/<branch>`. The script's comment gave a technical reason: a worktree nested
inside the repo lands in git's own scan and in build-tool globs. Both evals failed any run
that left a worktree inside the repo.

The owner works in an IDE opened at the repo root. A sibling folder is out of that view, so
following a fan-out or a pipeline run meant opening a second window or adding a folder to
the workspace by hand. The owner asked for the worktrees inside the repo.

## Decision

The default path is `<main-worktree-root>/.magito/worktrees/<branch-slug>`.

`.magito/` is magito's private-state folder, and it is already excluded from git in every
repo `setup-magito` has configured. An ignored folder answers the old objection. `git status`
never lists it, and tools that honor git's ignore files skip it, including ripgrep and the
search tools built on it. When nothing ignores `.magito/` yet, `worktree add` adds it to
`.git/info/exclude` before it creates anything. That line also hides the review marker the
same command writes, which used to show as untracked in a repo nobody had configured.

`git config magito.worktreeDir <dir>` still overrides the default, and an explicit path
argument still wins over both. The evals now fail only a worktree inside the repo that sits
outside `.magito/worktrees/`: that is a path an agent picked by hand, among tracked files.

## Costs

- A tool that ignores git's ignore files sees each worktree as a second copy of the repo.
  Examples are `grep -r`, `find`, and a Python `rglob` from the repo root. magito's own
  scripts scan only tracked files or named folders, so none of them is affected today.
- A coding agent started inside a worktree can also pick up instruction files from the
  directories above it. Claude Code, for one, reads `CLAUDE.md` files from parent
  directories, so a worker in a worktree can load the main checkout's `CLAUDE.md` as well as
  the branch's own. The two are usually identical. They differ only on a branch that edits
  `CLAUDE.md`.
- Removing `.magito/` by hand now also removes live worktrees. Remove them with
  `gitflow.sh worktree remove` first.
