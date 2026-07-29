# The handoff is machine-local; catch-up trusts live state over it

**Status:** superseded in part, via ADR-0008 and then ADR-0010. The handoff-file half of
this decision is dead. `handoff` no longer writes `~/.magito/handoffs/<repo-slug>.md`; it
writes an entry to the session journal (`.magito/journal/`) instead — ADR-0008 first
moved this to a SQLite session ledger, and ADR-0010 replaced that ledger with the
journal. Existing handoff files stay on disk. The title's rule still holds: `catch-up`
still trusts live git and the tracker over the recorded summary when they disagree.

Session handoffs live outside the repo at `~/.magito/handoffs/<repo-slug>.md`
(machine-local, latest-wins) so they can't be committed or shared — which also means
they go stale silently, and a stale handoff kept steering sessions at an already-merged
issue. `handoff` now reconciles its claims against live git and the tracker before
writing, and `catch-up` treats live git/tracker as authoritative when the handoff
disagrees. Trade-off: we keep the handoff's durability and simplicity (a plain file, no
repo coupling) and pay for it with an explicit reconcile step, rather than promoting the
handoff to a committed, always-consistent repo artifact.
