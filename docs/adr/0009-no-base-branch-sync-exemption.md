# The review gate does not exempt syncing the base branch from its own remote

`review-gate.py` blocks `git merge <ref>` onto the base branch unless a fresh
`reviewing-changes` marker matches the sha being landed. Merging the base branch's own
upstream looks like an obvious false positive, so the pre-release audit exempted it. The
two-axis review caught the regression that introduced. Push unreviewed work straight to
origin's `main`, then run `git merge origin/main` on `main`, and it lands through the
exemption — a path the gate denied before. The exemption cannot be narrowed into safety. A
real sync and a laundered push are the same ref with the same upstream relationship.
Telling them apart needs the provenance of the commits already on origin, which a local
hook cannot see. So the exemption was reverted. Trade-off: merging your own upstream now
demands a review marker. That false positive is deliberate, and a future reader will take
it for a bug. The cost is near zero, because `git pull` is the normal way to sync a base
branch and this hook has never gated it. Anyone re-adding the exemption must first answer
how the hook tells the two cases apart. If the answer is "it cannot", the exemption is the
bug.
