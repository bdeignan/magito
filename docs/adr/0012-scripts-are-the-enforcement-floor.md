# Hooks become optional; the workflow scripts are the enforcement floor

`OVERVIEW.md` said skills ask and hooks enforce. That framing collapsed two different
mechanisms into one word, and the missing one carries most of the weight. Between a prose
rule in a skill and a PreToolUse hook sits deterministic code in a script the agent already
calls. `gitflow.sh` refusing to commit without explicit file arguments is not prose and not
a hook; it is a check in the path, and it holds on every machine and in every tool.

That middle tier is now the floor. magito's primary use is a work machine where Claude Code
hooks are prohibited by default, so a design whose backstop exists only in one tool on one
machine has no backstop where it is mostly used. Rules that need teeth move into
`gitflow.sh`, which every workflow skill already routes through. The hooks stay installed
where they are permitted, as optional insurance.

The pull toward hooks came from wanting a hands-off multi-agent build loop. That is no
longer the goal. magito assumes a human in the loop and active, and projects built for the
unattended case serve it better. Anthropic's own guidance points the same way: their
verification-loop skills recommend checks embedded in a skill and skills chained end to end,
not interception, and their Claude 5 context-engineering guidance cut over 80% of Claude
Code's system prompt on the grounds that capable models need fewer explicit rules. A hook is
a way to constrain a model you do not trust. Building around one runs against where the
models are going.

The three tiers, named so the next rule lands in the right one:

1. **Prose in a skill.** Fails when it needs the model to suppress a strong prior, or when
   it waits for a trigger that never fires.
2. **Deterministic code in a script the agent already calls.** Fails only when the agent
   goes around the script.
3. **A PreToolUse hook.** Catches what tiers 1 and 2 cannot see — raw `git add -A`, raw
   `git merge`, raw `gh pr create` — and exists in Claude Code alone.

The cost is real and is accepted rather than solved. A script can only guard the path
through it. An agent that hits an error in `gitflow.sh` will reach for raw `git`, and at
tier 2 nothing catches that. The staging rule and the review rule both exist because their
prose versions kept failing, so moving them to tier 2 takes some risk back. The mitigation
is that magito now assumes an active human, which is a weaker guarantee than a hook and an
honest one. Anyone restoring hooks as mandatory should first say what changed about that
assumption.

One consequence is worth stating plainly: magito must degrade cleanly when switched off.
`docs/agents/README.md` already promises this for one folder — remove magito and it degrades
to a well-documented folder, not a broken one. That now applies to the whole system, which
also makes it testable. When a new frontier model lands, run a real task with skills and
hooks disabled and see what is actually missed. Anything not missed was scaffolding.
