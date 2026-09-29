# Select and carry a tracker adapter

A run uses one adapter for all its tickets. The adapter is a file containing the named
tracker operations. This reference owns selection; workflow skills consume the selected path.

Resolve private state against the main worktree root from `git worktree list --porcelain`.
Read the default tracker from that root's `.magito/config.toml`. When config is absent,
use the tracker described by `docs/agents/issue-tracker.md` at that root.

- With no intent override, or an override matching the default, use the repo's
  `docs/agents/issue-tracker.md`. A missing file is a setup gap; stop and report it.
- A different `Tracker: github` or `Tracker: local` selects the corresponding
  `issue-tracker-github.md.template` or `issue-tracker-local.md.template` beside this file.
- A different `Tracker: other` requires a user-supplied adapter path for that run.
  Stop and request it. A generic skeleton cannot describe the user's tracker.
- An unknown tracker value is an error. Do not change the repo default to accommodate a run.

Resolve the selected file to an absolute path. Read it before use and retain its contents
with the publication evidence. Pass the path and main worktree root to every consumer,
including `implement` and its parallel path. Commands address the selected repo; private
local ticket paths address the main worktree root, even when code lives in a linked worktree.

An explicit adapter passed by the caller wins over the repo default. A missing passed
adapter is an error, not permission to fall back to a different tracker. Standalone calls
with no passed adapter use the repo default. A resumed publication uses its saved adapter;
if the adapter contents or choice changed, stop and reconcile before further writes.
