# Semantic voice: the judgment layer

[anti-ai-markers.md](./anti-ai-markers.md) lists the banned tokens and the structure rules that a
reader, or the `anti-slop.py` linter, can check by shape. This file covers what neither can:
pseudo-insight built from ordinary, allowed words. A sentence can pass every keyword check and still
read like a machine wrote it.

Every test here is a judgment call. Use it as a lens while reading, not a checklist a tool runs.

The rule under all of them: **a sentence earns its place by changing what the reader knows or does.**
If it only adds rhythm, emphasis, or contrast for its own sake, cut it or flatten it.

## Test 1 — False antithesis
Defining a thing by what it is *not*: "X, not Y", "not just X — Y", "X isn't about A, it's about B",
"only narrowed, not closed".

Delete the negation clause. Does the sentence still deliver its fact or instruction?

- Loses nothing, cut the clause. "It is idempotent, not a one-shot scaffolder" becomes "It is
  idempotent."
- Loses something, keep the contrast only when Y is a real wrong-thing the reader is tempted to do,
  and the contrast is the shortest warning against it. "Produce decisions, not deliverables" stays,
  because producing deliverables is the tempting mistake.

State X in the positive first. Add "not Y" only when the warning earns it.

## Test 2 — Performative assertion
Insisting something is important, real, or hard instead of showing it: "This matters", "X is real",
"it cannot be overstated". Does the sentence carry a fact or instruction, or only assert importance?
If only asserting, cut it or replace it with the concrete thing that makes it matter.

## Test 3 — Hollow elevation
Inflating the ordinary into the profound: "not just a script, a philosophy", "this is where it gets
interesting". Is the elevation doing work, or flattering the subject? Cut the flattery; keep the
plain claim.

## Test 4 — Restated for rhythm
Re-saying the previous point in a punchier form: triads like "No X. No Y. Just Z.", or an echo that
follows a plain statement with a rhythmic repeat. Does the sentence add new information, or
re-perform the last one? If it re-performs, cut it.

## Test 5 — Hollow abstraction
A general-sounding line that hands the reader nothing to do: "at its core, X is about tradeoffs",
"it's a balance". Can the reader act differently after reading it? If not, cut it or make it
concrete.

## Working the rubric

- **Fix at the natural scope.** A clunky sentence is often a symptom that the paragraph around it
  needs rework. Rewrite as far out as the problem reaches, not sentence-by-sentence in isolation.
- **Change voice, never meaning.** Preserve every fact, number, identifier, and acceptance criterion
  exactly. If a rewrite would alter what a skill instructs, stop and raise it instead.
- **Prefer cutting to rewriting.** Deletion is the best fix for filler.
- **Keep a real distinction.** When a cut would lose a genuine contrast the reader needs, leave it.
  Precision over zeal.
- **Don't trade one tic for another.** Re-read your own rewrite against
  [anti-ai-markers.md](./anti-ai-markers.md) before you settle.
