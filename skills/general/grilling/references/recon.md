# Reconnaissance

A survey of the code and its context that runs **before** the first question — or, for a
build, before the plan. It fixes one failure: an agent asks from ignorance, or builds what
the codebase already solves, because it never looked. A check that fires at question time
cannot fix this. By the time there is a question, the looking has already not happened. So
recon is unconditional and comes first.

Recon settles what the code can settle. It does not replace the human questions — a
preference, a priority, or a trade-off call still goes to the user. It upgrades them. "How
should we handle retries?" asked cold becomes "three callers already retry with the backoff
helper in `lib/` — follow it, or does this one differ?" The second is faster to answer and
surfaces drift as a decision instead of letting it happen silently. Fewer questions is a
side effect, not the goal: don't tune for it.

## When to skip

There is one skip. If you already surveyed this same area earlier in this session, don't
repeat the full survey — do the delta for whatever is new. Judge this from the conversation,
not from a file: recon writes no state to read back.

## Procedure

1. **Read the context layer**, in this order:
   - `docs/agents/GLOSSARY.md`, plus any per-area glossaries routed from
     `docs/agents/INDEX.md`. This is why your questions and your brief speak the project's
     own vocabulary instead of inventing synonyms for terms it already defines.
   - `docs/adr/` — the decisions already made, so you don't re-litigate them.
   - `docs/agents/CONVENTIONS.md` and `docs/agents/GOTCHAS.md`, where they exist.

2. **Read the code in the area under discussion.** Not the whole repo — the modules the
   plan or issue actually touches, plus their immediate callers. Look for what already does
   this job, the established pattern for it, and anything already solved that the plan might
   re-solve.

3. **Write a short brief.** A handful of lines, not a report: what the codebase already does
   here, the patterns in force, the past decisions that bear on the work, and what is already
   solved. Short is load-bearing — the brief is read in-conversation, and a long one spends
   the tokens the survey was meant to save.

4. **Show the brief to the user before questioning (or planning) starts.** This is the point
   of recon, not a courtesy. It is the checkpoint where a wrong inference gets caught before
   it is baked into the plan.

5. **Promote anything durable — a numbered step, not a virtue.** Reading code with fresh eyes
   is the best moment to feed `docs/agents/`. For each candidate, apply **both** gates right
   here at the point of decision:
   - **Gate A — non-rederivable:** could a codebase-investigator agent reconstruct this
     cheaply from the code? If yes, it does not belong in the docs. This excludes structure —
     module maps, call graphs, feature-to-file.
   - **Gate B — stable:** will it survive the next handful of PRs? A pure refactor that moves
     code without changing intent must not invalidate it.

   Anything clearing both gates goes to its existing home. Recon adds no new file type:

   | Finding | Home |
   |---|---|
   | An established pattern the code doesn't announce | `docs/agents/CONVENTIONS.md` |
   | A trap spanning 2+ areas | `docs/agents/GOTCHAS.md` (create it if this is the first such trap) |
   | Hard to reverse, surprising without context, and a real trade-off — all three | `docs/adr/` |
   | A term that was ambiguous | `docs/agents/GLOSSARY.md` |

   Promotion needs judgment every time, and judgment is the same thing that fails elsewhere.
   That is why this is a numbered step with the gates written here, not a virtue you are
   trusted to remember. It is better than a rule stated somewhere else, not airtight.

## The brief is not filed

Do not write the brief to `docs/agents/`, `docs/adr/`, or `.magito/journal/`. It is a
snapshot of a moving target ("the auth layer currently works like this"), not a historical
fact ("we chose X over Y, because Z"). Filing it immutably guarantees it rots. It is
rederivable by construction: an agent reading the code produced it, so an agent can produce a
fresh, correct one next time. A stored brief is worse than none, because an agent that finds
one reads it instead of looking — the exact failure recon exists to fix. What persists is the
journal (what *happened*, which stays true) and any promotion above (what the two gates
admit).
