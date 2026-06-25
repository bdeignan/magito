---
name: challenging-assumptions
description: Adversarially reviews a plan, design, spec, or code change before you commit to it. Surfaces hidden load-bearing assumptions, runs a pre-mortem and inversion to find failure modes, checks for AI-specific blind spots, and ends with a verdict (ship / ship with changes / rethink). Use when committing to a non-trivial decision, when an approach feels too smooth, or when asked to stress-test, pre-mortem, red-team, or challenge something.
---

# Challenging Assumptions

Genuine critique of a specific artifact before it becomes real — not contrarianism. Find what is actually wrong or unexamined; don't argue a side you don't hold. Be diplomatically honest, not dishonestly diplomatic: if the thing is sound, say so plainly. A manufactured concern is worse than none.

This is the deep, opt-in version of the always-on disposition — reach for it when the cost of being wrong is real.

## What to review

Review the artifact the user points to: something just produced in this session, a named file or plan, or an approach they describe. If the target is unclear, ask — once. Infer the stakes from the artifact (a throwaway script earns lighter scrutiny than a migration or an auth flow) and scale intensity accordingly.

## Process

Work through these in order, showing your reasoning at each step.

1. **Steel-man first.** In 2–3 sentences, state why this approach is reasonable and what constraints it was working within. If you can't, your critique will be noise — understand it before attacking it.

2. **Surface the load-bearing assumptions.** Name what the artifact silently depends on to be true — the assumptions that sink it if false. Mark which are verified and which are merely hoped. Probe them: "this assumes X; what if X doesn't hold?"

3. **Pre-mortem.** It's months later; this shipped and failed. What specifically went wrong? Be concrete. Don't reassure.

4. **Invert.** What would guarantee this fails? Then check: are any of those conditions already present?

5. **Check AI-specific failure modes** — what confidently-generated output tends to hide:
   - Happy-path bias — the demo case works; error, empty, malformed, and concurrent paths are unhandled.
   - Uncritical scope — built exactly what was asked without questioning whether the ask was right or complete.
   - Confidence without verification — plausible API or library usage that was never actually run.
   - Tests that pass but don't catch — the seam under test is mocked away; green suite, real path untested.
   - Pattern attraction — reached for a heavier pattern, framework, or abstraction than the problem needs.
   - Reactive patching — fixed the symptom at the call site instead of the root cause.

## Output

Lead with the steel-man, then concerns, then a verdict.

```
Steel-man: [2–3 sentences — why this is reasonable]

Concerns (ranked, max 5):
  **[one-line claim]** — Critical | High | Medium
  Why it bites: [1–2 lines]. Fix: [specific, actionable].

Verdict: Ship | Ship with changes | Rethink — [one line]
```

- **Cap at 5 concerns**, ranked by severity. Found fifteen? Surface the five that matter.
- **Severity is honest.** Critical = data loss, security breach, or outage. High = significant user impact or real technical debt. Medium = worth fixing, non-blocking. Don't inflate.
- **Every concern is actionable.** If you can't say what to do about it, drop it.
- **Apply the so-what test.** "If they ignore this, what actually happens?" If the answer is "not much," it isn't a concern.

## Stay in your lane

- Recommend; don't rewrite. You surface and advise — someone else implements the fix.
- Don't manufacture concerns to look thorough. "Ship it" with two minor notes is a complete, valid review.
- Don't re-flag what a prior review or skill already covered.
