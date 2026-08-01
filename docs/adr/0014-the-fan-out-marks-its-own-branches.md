# The fan-out marks its own branches

Status: settles the mechanism ADR 0013 left open, and implements it. Supersedes ADR 0011's
marker semantics — the file is the same, but its absence now means "not gated" rather than
"no decision recorded".

ADR 0013 decided that gates belong where supervision is absent, leaving one place the review
gate still earns its cost: the `dispatch` fan-out. It deliberately did not say how a gate
tells an unsupervised fan-out from a human working by hand, because the three designs before
it went wrong by guessing.

The candidates all shared a flaw. Whether the command runs from a linked worktree, whether an
environment variable is set, whether a per-repo config flag is on — each tries to infer *who
is watching* from repo or process state. That fact is not in the repo, not in the environment,
and not in the process tree. Every proxy is therefore a guess, and the linked-worktree one was
already known to misfire in both directions.

There is a harder problem underneath, which is worth stating because it disqualifies the
mechanism the issue assumed. **A Claude Code hook can never fire in the unsupervised context.**
Shell workers launch through `worker.py` as ordinary subprocesses, so no PreToolUse hook
reaches them at all, and `dispatch` already reserves every commit, merge, and PR for the
orchestrator, which runs inside the human's session. When `review-gate.py` fires, it is always
firing on a supervised tool call. The hook cannot observe the thing ADR 0013 wants gated.

So the question was turned inside out. Nobody can detect a fan-out at landing time, but one
actor knows at one moment, as a positive act rather than an inference: `dispatch`, when it
creates the worktree. Not *is this landing unsupervised?* but *was this branch created by a
fan-out?* — recorded when the answer is known.

`gitflow.sh worktree add` creates the worktree and writes `pending` as the branch's review
decision. Nothing else writes a marker. The gate's rule becomes: a branch with no marker is
not gated; a branch with a marker must have one matching the current sha. `pending` never
matches a sha, so a fan-out branch is blocked until `reviewing-changes` overwrites it, and any
later commit stales it again. The gate's logic barely changed — only its default, from deny to
allow.

This beats the rejected candidates on their own failure modes. A file names the exact branches
`dispatch` created, so a worktree used by hand is not swept up. A file cannot leak downward
into a child process the way an environment variable can, which was bug #94. It is per-branch,
not per-repo, which is the axis the situation actually varies on. And it is not the tier-1
prose of "ask `dispatch` to record it", because the write lives inside a script `dispatch`
already calls.

Two consequences follow for the skills, and both are load-bearing. `reviewing-changes` and
`implement-issue`'s skip path must now write a marker **only when one already exists**. If
either created a marker on ordinary work, that branch would become gated the moment it was
reviewed, and the next commit would block the merge — turning the review offer into exactly
the blanket gate ADR 0013 removed. Teardown removes the marker, so it must happen after the
pull request is open.

Per ADR 0012 the floor is `gitflow.sh`, not the hook. That is not a formality here: `dispatch`
runs on the work machine, where Claude Code hooks are prohibited, so a gate living only in the
hook would be absent from a place fan-outs actually happen. The check therefore lives in
`gitflow.sh pr` and `gitflow.sh merge`, and `dispatch` step 5 now routes through the script
instead of calling `gh pr create` directly. `review-gate.py` keeps the same check as optional
insurance for the raw commands a script cannot see.

The cost is accepted rather than solved, in the same shape as ADR 0012's. An orchestrator that
hand-rolls `git worktree add` marks nothing, and its fan-out lands ungated. That fails open
toward the ordinary path, which ADR 0013 already decided needs no gate, and the skill says
plainly why the script is not optional. The gate also still refuses to read the decision text,
so a fan-out can be recorded as `skipped` — unchanged from ADR 0011, which conceded that a
local check judging the word would be theatre.

One old question closes quietly. ADR 0009 refused to exempt a base-branch sync from the gate.
`git merge origin/main` now passes, because `origin/main` has no marker — not because it won
an exemption. The reasoning in 0009 still holds wherever the gate applies; it just stops
arising. Anyone re-reading it should not add the special case it argued against.
