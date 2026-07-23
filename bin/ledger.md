# ledger.md — inspecting the session ledger by hand

The session ledger is a single SQLite file, machine-local, never checked into
a repo. Default location: `~/.magito/ledger.db`. `clock` (installed at
`~/.magito/bin/clock`, alongside this doc) honors `$MAGITO_LEDGER_DB` if it's
set, pointing it at a different file instead — useful for testing without
touching your real ledger. `clock dump` honors the same override.

## Poking at it with the sqlite3 CLI

```sh
sqlite3 ~/.magito/ledger.db ".tables"
sqlite3 ~/.magito/ledger.db ".schema"
```

`.tables` lists every table and view. `.schema` prints the exact, current
`CREATE` statements for all of them — every column, every constraint. This
doc does not repeat that list: `clock` owns the schema, and a copy pasted
here would go stale the moment the schema changes. Always read `.schema`
straight from the database, not this doc.

To look at just one table or view:

```sh
sqlite3 ~/.magito/ledger.db ".schema clock_in"
sqlite3 -header -column ~/.magito/ledger.db "SELECT * FROM sessions ORDER BY started_ts DESC LIMIT 10;"
```

The `sessions` view is usually the best place to start: one row per session,
joining `clock_in` and `clock_out`, with `duration` and `unfinished` worked
out fresh on every read — nothing is stored for them.

A couple of queries worth keeping around:

```sh
# Every session still open (started but never clocked out)
sqlite3 -header -column ~/.magito/ledger.db \
  "SELECT session_id, alias, repo, started_ts FROM sessions WHERE unfinished = 1;"

# Everything that happened in one session, in order
sqlite3 -header -column ~/.magito/ledger.db \
  "SELECT ts, type, ref, summary FROM session_event WHERE session_id = '<id>' ORDER BY ts;"
```

## The append-only rule

All three tables (`clock_in`, `clock_out`, `session_event`) are insert-only.
Nothing in this ledger is ever `UPDATE`d or `DELETE`d — a session's state is
worked out entirely from which tables its `session_id` shows up in (see
issue #62/#63). Don't hand-edit a row. If a row turns out to be wrong, the
fix is a later row (a `note` event, say), not a mutation of history.

## Getting a snapshot instead

For scripting or archiving, prefer `clock dump` over hand-written SQL. It
emits one JSON object per line (JSONL, not CSV — a summary can contain
newlines, which breaks CSV) for every row in all three tables, each tagged
with `_table`:

```sh
~/.magito/bin/clock dump > ledger-snapshot.jsonl
~/.magito/bin/clock dump --table session_event
```

## Only `clock` writes

`clock`, installed at `~/.magito/bin/clock` (this doc sits alongside it,
installed from the same repo-root `bin/`), is the only thing that reads or
writes `ledger.db` from magito's own tooling. If some other script needs
data from the ledger, prefer shelling out to `clock status` or `clock dump`
over opening the database directly — that way a schema change only ever has
one caller to update.
