# Every skill is model-invocable

Sixteen skills carried `disable-model-invocation: true` in their `SKILL.md` frontmatter:
`magi`, `ask-magito`, `catch-up`, `challenging-assumptions`, `decruft`, `finding-lacunae`,
`grilling`, `handoff`, `implement`, `research`, `setup-magito`, `teach`, `to-issues`,
`to-questionnaire`, `wait-what`, and `wayfinder`. The flag blocked the model from starting
the skill on its own, and it blocked one skill from calling another — `Skill catch-up cannot
be used with Skill tool due to disable-model-invocation` was the exact failure. Fifteen of
those skills carried a matching Codex policy, `policy.allow_implicit_invocation: false` in
`agents/openai.yaml`, since Codex does not read Claude Code frontmatter. `install.py` ran
`validate_invocation_policies` on every install to keep the two aligned.

The intent doc for the agentic pipeline (`docs/intent/0001-agentic-pipeline.md`, migration
step 1) decided "Skills can call skills": the new pipeline chains `intent` into `to-issues`
into `implement` with no human retyping a command between them. A skill nothing else can
call cannot be a step in that chain. The flag this ADR removes is exactly the thing that
would have blocked it.

The argument for the flag, when it was added, was memorability: a workflow you type stays
legible because you remember what you typed, and a skill that chains itself invisibly
teaches you nothing about its own shape. That argument does not disappear so much as change
what has to carry it. With no flag, the `description:` field is the only thing left that
decides when a skill fires — for the model, and for one skill calling another. A description
that says plainly when to use the skill, and when not to where firing on the wrong prompt
would be disruptive, does the same job the flag did, at the one place an agent actually reads
before invoking anything. `handoff`, `catch-up`, `setup-magito`, and `implement` needed the
most explicit "when not to" clauses, because a wrong trigger for any of the four lands somewhere
disruptive: closing a session that has not wrapped up, re-orienting mid-task, auditing
configuration nobody asked to revisit, or building against an issue with no definition of
done.

What this replaces: `disable-model-invocation` in every `SKILL.md`, the `agents/openai.yaml`
files that mirrored it for Codex, and `install.py`'s `validate_invocation_policies` function
and its call site, which existed only to keep the two in sync. `scripts/check.sh` gained a
check that fails if any `SKILL.md` under `skills/` carries the flag again, so the mechanism
does not come back by accident on a copy-pasted frontmatter block.

The cost accepted here: a description now carries more weight than it used to, and a vague
one can misfire — either failing to trigger when it should, or triggering somewhere
disruptive. That risk existed already for every skill that never carried the flag; this
change extends it to the sixteen that did, in exchange for making all of them usable as
pipeline steps.
