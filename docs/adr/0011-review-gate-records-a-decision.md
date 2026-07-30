# The review gate records a decision, not a review

The marker `reviewing-changes` writes meant "a review happened at this sha", and
`review-gate.py` refused to land anything without one. Making the review optional (#110)
breaks that outright. The moment a review is legitimately skipped on a docs-only change,
the work cannot land unless someone hand-writes an attestation for a review that never
ran. That is a lie written into the one artifact whose whole purpose is attestation.

So the marker now records the decision. It holds one line, `<sha> <decision>`, where the
decision is either `reviewed` or `skipped: <reason>`. The gate checks that a decision
exists and is fresh, which is the property actually worth enforcing: nothing lands by
default or by forgetting. Skipping stays deliberate, recorded, and reviewable after the
fact.

The gate does not read the decision text, and that is deliberate. A local hook cannot
verify that a review happened, so a gate that inspected the word would be theater. Three
things keep the record honest instead, and none of them is enforcement. `reviewing-changes`
is the only writer of `reviewed`, and it writes it as its own last step. The skip path in
`implement-issue` writes only `skipped: <reason>`, with the reason coming from the user's
answer. The deny message points at the skill and at the skip path rather than pasting a
ready-made command for writing `reviewed`, which would be handing over the very thing the
rule forbids. An agent determined to lie can still lie. The design removes the reason to,
by making the honest skip as cheap as the dishonest one. Treat the acceptance criterion
"nothing lets an agent record `reviewed` when no review ran" as mitigated, not met.

The marker also moved, from `<git-common-dir>/magito/reviewed-<branch>` to
`<main-worktree-root>/.magito/review-<branch>`. Claude Code's auto-mode classifier refuses
agent writes under `.git/` even when a permission rule allows them, because permissions
and the classifier are independent gates (#108). The cost was a manual step at the prompt
on every single PR, written by hand six times in one day. `.magito/` is an ordinary
directory already kept out of git through `.git/info/exclude`, and already home to the
session journal, so writing there is a normal file write.

One trap guards that move. The old path came from `git rev-parse --git-common-dir`
specifically so a review performed inside a linked worktree still counted when merging
from the main tree, and `dispatch` depends on that, since every parallel executor works in
its own worktree. Resolving the new path against the current directory would give each
worktree its own `.magito/` and silently break it. The main worktree is therefore resolved
explicitly, from the first entry of `git worktree list --porcelain`. Anyone rewriting this
to a cwd-relative path will not see the breakage until a fan-out fails to land.

There is no migration. A marker goes stale on the next commit regardless, so old files
under `.git/magito/` are simply no longer read. A branch that was in flight when this
landed re-records its decision, which costs one command. The reader still accepts a file
holding a bare sha and no decision word, but that is tolerance for a hand-written marker,
not a migration path — nothing writing to the new location omits the decision.
