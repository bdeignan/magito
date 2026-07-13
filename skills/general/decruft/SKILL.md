---
name: decruft
description: Harsh, behavior-preserving structural review that hunts the cruft AI agents leave behind — redundant tests, defensive try/except, thin wrappers, dead fallbacks, speculative generality — and proposes ambitious simplifications without applying them. Use when asked to decruft, deep-clean, simplify aggressively, or audit code quality on working code.
disable-model-invocation: true
argument-hint: "[diff | file | module — defaults to the branch diff]"
---

<!-- Posture adapted from Cursor's thermo-nuclear-code-quality-review skill (cursor/plugins, MIT). -->

# Decruft

A structural-quality review of working code. Behavior stays fixed; the structure is on trial. You propose; the user applies — never edit files during this review.

## Scope

Default target: the current branch's diff against the base branch (`git diff main...HEAD`, substituting the repo's actual base branch). If the user names a file, module, or directory, review that instead. Read enough surrounding code to judge structure — a diff hunk alone can't tell you whether a helper duplicates an existing one.

## Posture

Be ambitious. Do not stop at "this could be a bit cleaner" — look for restructurings that make whole branches, helpers, modes, or layers disappear. Prefer the version that feels inevitable in hindsight. But report only what you're confident in: a few high-conviction findings beat a flood of nits. If the code is clean, say so and stop — a manufactured finding is worse than none.

## What to hunt

The cruft AI agents characteristically leave:

**Exception cruft**
- `try/except` that logs and continues, re-raises with nothing added, or swallows errors a caller should see
- Bare `except:` or `except Exception` where a specific exception exists
- Defensive checks re-validating what upstream code or the schema already guarantees

**Test cruft**
- Tests that mock the seam under test — green suite, real path untested
- Tests asserting implementation details (call counts, private attributes) instead of behavior
- Duplicate coverage: several tests exercising the same path with cosmetic variation
- Never propose deleting a test that is the only coverage of a real path — redundant is the bar, not merely ugly

**Indirection cruft**
- Thin wrappers, pass-through helpers, identity abstractions called from one place
- Speculative generality: unused parameters, config flags only ever passed one value, abstract bases with a single subclass
- `**kwargs` grab-bags and `Any`-typed boundaries where the real shape is known
- `# type: ignore` sprawl papering over a fixable boundary

**Flow cruft**
- New conditionals bolted into unrelated flows; special cases dropped into the middle of an already busy function
- Dead fallback branches for states that cannot occur
- Copy-paste near-duplicates of an existing helper — point at the canonical one
- Independent work serialized for no reason
- A file the change pushed past ~1000 lines without a strong structural reason

## Output

Ranked findings, capped at 7, highest-leverage first:

```
**[one-line claim]** — file:line
Why it's cruft: [1–2 lines]
Simplification: [concrete before → after sketch — what disappears]
Risk: [what could break, and how to check it doesn't]
```

End with a verdict: **Clean** | **Worth a pass** (name which findings) | **Needs restructuring** (spell out the restructuring move). Offer to apply the accepted findings as a separate, explicit next step.

## Rules

- Behavior-preserving only. A finding that changes observable behavior belongs in a bug report, not here.
- Propose, don't apply. Invoking this skill authorizes aggressive proposals, not edits.
- Don't re-flag what a prior review already surfaced.
