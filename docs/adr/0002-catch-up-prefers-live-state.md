# The handoff is machine-local; catch-up trusts live state over it

Session handoffs live outside the repo at `~/.magito/handoffs/<repo-slug>.md`
(machine-local, latest-wins) so they can't be committed or shared — which also means
they go stale silently, and a stale handoff kept steering sessions at an already-merged
issue. `handoff` now reconciles its claims against live git and the tracker before
writing, and `catch-up` treats live git/tracker as authoritative when the handoff
disagrees. Trade-off: we keep the handoff's durability and simplicity (a plain file, no
repo coupling) and pay for it with an explicit reconcile step, rather than promoting the
handoff to a committed, always-consistent repo artifact.
