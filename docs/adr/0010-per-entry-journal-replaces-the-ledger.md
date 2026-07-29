# Replace the SQLite session ledger with a per-entry journal

ADR 0008 replaced per-repo handoff files with `~/.magito/ledger.db` because two sessions
working the same repo at once clobbered each other's single handoff file. The session
journal (`.magito/journal/`, one markdown file per session, landed in #114/#115) is not a
smaller version of that same bug fix — it removes the shared resource the bug depended
on. A handoff file and the ledger both had exactly one thing every session had to write
through: one path, one database. Concurrent writers to a shared resource is what produces
a last-write-wins race, however careful the write path is. The journal gives every
session its own new file, named by timestamp and slug, so two sessions never address the
same path and there is nothing to race over. That is a stronger guarantee than the
ledger's: the ledger needed a `UNIQUE` constraint on `clock_out(session_id)`, a pointer
file under `~/.magito/run/` to find a session again from its folder, and an env-var guard
(#94, after a worker inherited its driver's environment and closed the driver's own
session) to approximate what the journal gets for free by construction.

The second reason is about where truth lives. `clock` stored session summaries in a
SQLite database, so reading them was never a plain file read — the Read tool cannot open
a binary database, so every `catch-up` had to shell out to `clock`, and every shell call
is an approval prompt. The journal fixes this by making the markdown files themselves the
record; `bin/journal read` is a convenience wrapper around what an agent could already do
by reading files directly. If querying the journal ever becomes genuinely useful — dates,
tags, cross-project search — the right shape is a disposable SQLite index built *from*
the journal files, rebuilt on demand, never checked in, never the source of truth. The
database must never again be the authoritative record. That inversion, a database an
agent cannot read directly standing in as the record of what happened, is what produced
the ledger's long issue tail: #62, #63, #64, #65, #66, #67, #75, #76, #78, #82, #84, #94,
#96, #99, #103.

The ledger's own usage argued the same way. Across its lifetime it recorded 9 sessions,
all in this one repo — the cross-project, cross-machine querying that justified a
machine-global database was never actually exercised. `clock_amendment`, added in #96 to
let a session correct a wrong summary after the fact, ended its life with zero rows.
And the token cost ran the wrong way for a tool meant to save context: `clock in`'s
orientation dump printed on the order of 3,525 tokens per session, against roughly 359
for `journal read 2`.

Trade-off: the ledger could answer a query no journal file grep can — "every session that
touched issue #94," say — without writing one. We give that up. What we get in exchange
is a session record an agent can read with the same tool it reads any other file with, no
shell approval, no schema, and no shared file for two sessions to race over.
