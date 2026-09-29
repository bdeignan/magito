# The pipeline reviews between the gates

Status: accepted, 2026-09-29. Supersedes ADR 0013's premise that a human is present on the
pipeline path, and extends ADR 0014's marker from the fan-out alone to every pipeline branch.
Both ADRs stay accurate for the manual path.

ADR 0013 decided that gates belong where supervision is absent. It assumed a human who is
present and active, and it found one place with no such human: the parallel fan-out. ADR 0014
made that concrete. `gitflow.sh worktree add` writes a review marker for a branch, and only
the fan-out called it.

The pipeline changes that assumption. The pipeline is the path that starts from an accepted
intent, as `skills/general/implement/SKILL.md` defines it. The human acts at two gates. They
accept an intent, and they merge a pull request. Between those gates, agents build, check, and
review with no human watching. The pipeline path in
`skills/general/implement/references/pipeline.md` never asks the human to approve a plan and
never offers a review. It stops only for a named escalation. ADR 0013's premise that a human is
present no longer holds there.

The same rule that made the fan-out the exception now covers the whole pipeline path. Every
pipeline branch is created with `gitflow.sh worktree add`, so it gets a review marker. That
includes the integration branch of an integrated run, which
`skills/general/implement/references/integrate.md` describes. The gate in `gitflow.sh pr|merge`
applies to any branch with a marker at the moment that branch lands. This extends ADR 0014 from
the fan-out alone to the pipeline. The mechanism is unchanged. A branch with a marker is gated,
and a branch without one is not.

In an integrated run, the gate fires once, at the integration branch. Each ticket branch is
reviewed, but it never lands on the base branch: the driver merges it into the integration
branch with a raw `git merge`, which the gate does not see. So a ticket branch's marker stays
`pending`, and nothing enforces its review. What the gate enforces is the final review of the
whole integration branch, when its pull request opens.

The review on the pipeline path is automatic. It does not wait for the human to ask. It
comes from a different model family than the builder whenever the roster has a working worker
outside that family. The driver runs
`python3 <skills>/implement/scripts/worker.py reviewer <builder-family>`, and the command picks a
working worker outside the builder's family. A model reviewing its own family's code shares
that family's blind spots, and no human is there to catch them. When no such worker exists, the
driver reviews with a fresh-context subagent and says so in the pull request body. That
fallback is the one exception: a subagent can be the builder's own family, so the
different-family review is a strong default, not a guarantee. A `VERDICT
PASS` and a green check are what let the driver record `<sha> reviewed` and open the pull
request.

The manual path keeps ADR 0013's rule. A ticket that does not come from an accepted intent has
a human driving it. `worktree add` is not part of that path, so no marker exists and no gate
applies. The `implement` skill offers the review at the right moment and lets the human decide.
That offer is not forced, and a skip is recorded only when a marker already exists.

The trade-off is accepted, not solved. The pipeline spends model calls on reviews that the human
used to decide on case by case. It spends them on every pipeline branch, including small
changes that a human might have skipped. In exchange, the human does not have to watch the
build. Anyone who wants to cut this cost must first say who will watch the work instead.

Two limits from ADR 0014 carry over unchanged. The gate still does not read the decision text,
so a review can be recorded as `skipped`. The floor is still `gitflow.sh`, and `review-gate.py`
remains optional insurance for the raw commands a script cannot see.
