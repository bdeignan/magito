# Select and carry a tracker adapter

A run uses one adapter for all its tickets. The adapter is a file containing the named
tracker operations. This reference owns selection; workflow skills consume the selected path.

Read the default tracker from `.magito/config.toml` in the current folder. When config is
absent, use the tracker described by the repo's `docs/agents/issue-tracker.md`.

- With no intent override, or an override matching the default, use the repo's
  `docs/agents/issue-tracker.md`. A missing file is a setup gap; stop and report it.
- A different `Tracker: github` or `Tracker: local` selects the corresponding
  `issue-tracker-github.md.template` or `issue-tracker-local.md.template` beside this file.
- A different `Tracker: other` requires a user-supplied adapter path for that run.
  Stop and request it. A generic skeleton cannot describe the user's tracker.
- An unknown tracker value is an error. Do not change the repo default to accommodate a run.

Resolve the selected file to an absolute path and read it before use. Pass the path to every
consumer, including `implement`. Commands address the selected repo. Private local ticket
paths are in the planner's own checkout, the main one. A worker gets a local ticket's body in
its session card, and never reads `.scratch/`.

An explicit adapter passed by the caller wins over the repo default. A missing passed
adapter is an error, not permission to fall back to a different tracker. Standalone calls
with no passed adapter use the repo default. A rerun of the same intent selects the same
adapter, because the choice comes from the intent's header and the repo default.
