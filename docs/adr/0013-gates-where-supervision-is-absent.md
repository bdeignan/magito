# Gates belong where supervision is absent

Status: supersedes ADR 0011's premise that every landing needs a recorded decision, and
makes ADR 0009 moot outside the fan-out path. Both remain accurate records of what was
believed when they were written; neither should be edited.

ADR 0009 refused to exempt a base-branch sync from the gate, on the reasoning that a real
sync and a laundered push are indistinguishable to a local hook. That reasoning still holds
wherever the gate applies. It simply stops arising in the ordinary path, because there is no
longer a gate there to seek an exemption from. Anyone re-reading 0009 and finding it
demanding a marker for `git merge origin/main` should read this ADR first.

The review gate refuses to land work until a marker records a decision for the current sha.
ADR 0011 already conceded that the gate verifies nothing: a local hook cannot tell whether a
review happened, so a gate that read the decision text would be theater. What is left is a
speed bump whose only function is to force a pause.

That pause is expensive. ADR 0011 records the marker being hand-written six times in one day
before its path moved, and the move did not fix it — the auto-mode classifier still refused
the write at the new path, twice in one session, including a command that only read. Each
refusal costs a stop, an explanation, and a command the human has to run.

The marker is also a record with no reader. It lives under `.magito/`, which is listed in
`.git/info/exclude`, so it never travels with the pull request and nobody else ever sees it.
A new commit makes it stale. Nothing reads it except the check that demands it.

So the gate was built for a reader who is no longer there. It was protecting against an
agent landing work that nobody looked at. Under ADR 0012 magito assumes a human in the loop
and active, and skills are mainly invoked by hand. A person who typed the skill, watched the
diff, and asked for a pull request has not forgotten to review — they decided. The gate
cannot tell those apart, and only the first was ever the problem.

The decision: gates belong where supervision is absent, not where it is present. That leaves
one place the review gate still earns its cost — the `dispatch` fan-out, which the skill
itself already calls the least supervised work this system does. There an artifact is worth
having precisely because the agent's own claim cannot be trusted; the session journal
records a worker reporting a completed task that never existed. Everywhere else,
`reviewing-changes` is a skill run when it is wanted, and `implement-issue` keeps offering
it at the right moment.

This also separates two jobs `gitflow.sh` had been doing at once. Encoding how to do
something correctly is knowledge worth keeping: refusing bulk staging, detecting the base
branch locally, building the pull-request body, refusing to commit on the base branch.
Refusing to act until an artifact exists is policy. The knowledge stays. The policy goes,
except on the fan-out path.

The trade-off is accepted, not solved. Nothing then stops an agent, or a tired human, from
landing something unlooked-at. Two things make that acceptable. `implement-issue` already
asks about reviewing at the right moment, so the prompt survives without the block. And ADR
0012 accepted the same trade for the same reason. Anyone restoring a mandatory gate should
first say what changed about the assumption that a human is present.

How the fan-out is detected is deliberately not settled here. A hook cannot ask who is
driving, so every candidate is a proxy — whether the command runs from a linked worktree, an
environment variable set by `dispatch`, a separate config flag. Choosing one by guess is how
the last two designs in this area went wrong. The decision above stands on its own; the
mechanism is a separate question with its own issue.
