# Install the session-ledger command to `~/.magito/bin/`, not nested in a skill

`clock` has three unrelated consumers — `catch-up`, `handoff`, and `gitflow.sh` — and
none of them owns it. It used to live in `implement-issue/scripts/`, so the other two
reached it sideways via `../implement-issue/scripts/clock`. That is the cross-skill-reference
anti-pattern Anthropic's plugin docs warn against: a component reaching outside its own
directory with `../` to borrow another component's file, which breaks the moment either
directory moves. magito is not a Claude Code plugin, so it has no `${CLAUDE_PLUGIN_ROOT}`
to anchor a shared `bin/` the way a plugin would. `install.py` emulates that pattern
instead: a repo-root `bin/` holds `clock` and its `ledger.md`, and `install.py` symlinks
every file in it to `~/.magito/bin/`, a machine-global location every consumer reaches by
the same absolute path regardless of which skill or script is calling. The trade-off is
one more thing for `install.py` to manage — a new install lane and a `~/.magito/bin/`
directory that, like `ledger.db` and `run/`, is magito-managed rather than a user file —
in exchange for retiring the sideways reference and giving all three consumers one stable
path.
