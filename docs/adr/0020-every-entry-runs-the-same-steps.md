# Every entry runs the same steps

Status: accepted, 2026-10-01. Replaces ADR 0013's rule for work a person starts by hand, and
the sentence in ADR 0018 that puts the reviewer's fallback in the pull request body. Both
ADRs stay accurate records of what was believed when they were written; neither is edited.

ADR 0013 put gates where no one supervises, and found one such place: the parallel fan-out.
ADR 0018 added the pipeline, the path from an accepted intent to a pull request. Every other
ticket kept a person in the loop: `implement` asked for plan approval, offered a review that
defaulted to a skip on a small diff, reviewed with the builder's own model family, and waited
for a second approval before the pull request.

That left one switch controlling three separate things. Whether a ticket linked an accepted
intent decided who approved what to build, whether the run stopped for the person, and how
strong the review was. The person had no way to get one without the others, and no way to tell
in advance which behavior a run was going to choose. The path the README recommended for work the
person already understood got the most stops and the weakest review.

The premise behind that split no longer holds. A person who approves a plan and walks away is
not watching the build. After that approval, a hand-started ticket is as unsupervised as a
ticket from an accepted intent. By ADR 0013's own rule, the same review and the same gate
belong there.

## Decision

**No entry point to the workflow gets a route of its own.** `implement` has one set of steps:
a worktree, the check, and then, when the branch has a commit ahead of its base, a review and
a pull request. The review comes from another model family when the roster has a reviewer
that answers, and from a fresh-context subagent when it has none. A ticket
without an accepted intent enters the usual route partway and runs the steps from there. A
batch runs the same steps for several tickets at once. Later work on any skill must fit a new
case into these steps, and must not add a second set beside them.

One difference between tickets remains. A ticket with no accepted intent stops once, for plan
approval, because no one has agreed on what to build. A small change skips that stop. A ticket
from an accepted intent has no stop.

Every branch `implement` builds is made by `gitflow.sh worktree add`, so it carries a review
marker and meets the gate from ADR 0014. One command opens every run and names the builder
and the reviewer. The review decision is written through `worker.py record`, which refuses to
record a subagent review while a roster reviewer from another family answers its probe. A run
therefore reaches the weaker review only when the machine has no stronger one to offer.

**Nothing a teammate reads carries magito's own vocabulary or bookkeeping.** A pull request
body never says who reviewed, lists no review rounds, and does not describe how magito
produced the change. The run's last message to the user carries those facts.

## Scope

The rule covers work that goes through `implement`. A quick fix the user asks an agent for
directly, with no skill, is outside it. That work gets no worktree and no paid review, and
the user decides about reviewing it. A branch that `implement` did not build has no marker
and meets no gate, as ADR 0014 decided.

One exception sits inside the rule. A branch with no commit ahead of its base holds no change
to review. It gets no review and no pull request, and the run posts its findings on the
ticket. The test is the commit count on the branch, read by `gitflow.sh ahead`, and it makes
no judgment of whether a change is large enough to matter.

## Costs

- Every `implement` run gets a worktree, and every branch with a commit ahead of its base
  gets a paid review, including one for a one-line fix. The person used to decide that case
  by case.
- A small change run through `implement` can reach a pull request with no stop at all. The
  merge is then the only gate, and the person still owns it.
- The review record still cannot prove a review ran. `gitflow.sh` reads only the commit in
  the marker, as ADR 0011 and ADR 0014 decided. `worker.py record` closes one path, the
  subagent record while a roster reviewer answers, and nothing more.
- A machine with no roster reviewer and a tool with no subagents cannot review at all. A run
  there stops and asks before it builds.
