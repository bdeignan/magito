# Adopting the session journal in an existing project

For a project that already has its own notes or handoff habit — including magito's own
retired SQLite ledger. It covers what changes, what doesn't, and the one-time import.

## What the journal is, and isn't

The session journal is a directory of markdown files, `.magito/journal/` inside the
project, one file per session. It is personal state: keep `.magito/` in
`.git/info/exclude`, never in `.gitignore`, so it stays out of a shared ignore file.

It replaces magito's own session record — first the per-repo handoff files, then the
SQLite ledger. It touches nothing else. The project's `README`, its ADRs,
`docs/agents/GLOSSARY.md`, and any other notes stay exactly as they are. The journal is
not a substitute for project documentation.

## Per-project setup

None beyond the exclude line. After `python install.py` puts `~/.magito/bin/journal` on
a machine, `/catch-up` reads the journal at the start of a session and `/handoff` writes
one entry at the end. The directory is created on first write.

## The one-time step: importing the old ledger

On a machine that still has `~/.magito/ledger.db`, run this once per project:

```bash
~/.magito/bin/journal import
```

It reads the ledger read-only, writes one entry file per closed session using that
session's real timestamp, and skips any entry that already exists — so running it twice
is safe. Sessions that never got a summary are skipped rather than imported blank.
Nothing in the ledger is modified or deleted.

## Checking it worked

```bash
~/.magito/bin/journal read 2
```

The newest two entries print, newest first, with a count of any older ones withheld.

## Why one file per entry

Two reasons, both load-bearing:

- **No write contention.** Each session creates its own new file, so concurrent agents
  never write the same path. There is no last-write-wins to lose to — a stronger
  guarantee than the ledger's, which needed a UNIQUE constraint, a pointer file, and an
  env-var guard to approximate it.
- **No context rot.** An entry is read whole or not at all, and `read N` bounds the cost
  exactly. There is no single growing file whose middle quietly falls out of the window.
