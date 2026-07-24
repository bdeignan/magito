# Replace per-repo handoff files with an append-only session ledger

Session handoffs used to live at `~/.magito/handoffs/<repo-slug>.md`, one markdown file
per repo, machine-local, with each write overwriting the last. Two sessions working the
same repo at once clobbered each other's file, and there was no way to query past
sessions or notice one left unfinished. We replaced the file with `~/.magito/ledger.db`,
an append-only SQLite database that only the `clock` command reads or writes. Every row
is inserted and never updated or deleted, and a session can only be closed once —
`clock_out` has `UNIQUE(session_id)`. A small pointer file under `~/.magito/run/` records
which session id a folder's last `clock in` used, so a later `clock out` in that folder
can find its way back to the right session. Trade-off: a plain markdown file needed no
tool to read and no schema to keep up to date; the ledger needs the `clock` command to
read it and a schema to migrate when it changes. In exchange we get concurrent safety
and a queryable history, instead of one file that the next write could silently erase.
