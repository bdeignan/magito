---
name: speaking-plainly
description: Rewrites dense text into plain language (Simplified Technical English rules, with linters) and resets a writing voice that has drifted. Use when asked to simplify or plainen prose, or when prose has gone dense.
---

# Speaking Plainly

The always-on voice baseline lives in the output style (Claude Code) and in
`shared/SYSTEM-INSTRUCTIONS.md` (all tools). This skill is for two situations:

1. **Snap-back** — the voice has drifted mid-session. Re-assert the baseline rules fast,
   without a full rewrite pass.
2. **Deep rewrite** — given text to rewrite, run the full STE structural rules and linters.

This skill rewrites *text*. Use `/wait-what` when you need to repair the conversation
itself.

## Snap-back

When the user asks to reset the voice, re-read the baseline voice rules from
`shared/SYSTEM-INSTRUCTIONS.md` and re-assert them. No linters, no rewrite pass. The point
is speed: get back on track without a full audit.

Re-assert these rules:

- **No contractions.** Write full forms (do not, will not, it is).
- **Active voice.** One idea per sentence.
- **No AI-marker words or structures.** Consult [anti-ai-markers.md](./references/anti-ai-markers.md) for the full list.
- **Modal ladder in instructional context.** Use only can, will, and must.
- **Sentences under 20 words.**

## Deep rewrite

When given text to rewrite:

1. **Extract all facts, numbers, and identifiers** from the source. Preserve them exactly.
   Never rename a technical identifier.

2. **Consult reference files:**
   - [ste-rules.md](./references/ste-rules.md) — the primary structural reference (STE
     rules, modal ladder, substitution table, self-check)
   - [anti-ai-markers.md](./references/anti-ai-markers.md) — banned words, phrases,
     structures, contraction ban, modal ladder
   - [freddish.md](./references/freddish.md) — tone and positive phrasing
   - [semantic-slop.md](./references/semantic-slop.md) — pseudo-insight the word list
     cannot catch

3. **Draft the rewrite** following STE structural rules. Classify each passage as
   procedural or descriptive. Apply the sentence limits. Write one instruction per
   sentence. Put the condition before the command.

4. **Verify fidelity.** Every fact, number, and identifier from the source must appear in
   the rewrite.

5. **Run the linters** (both, relative to the skill directory):
   - Write the draft to a temporary file.
   - `python3 ./scripts/readability.py <temp_file>` — flags sentences over 20 words and
     passive stacking. Rewrite flagged sections.
   - `python3 ./scripts/anti-slop.py <temp_file>` — flags banned words, phrases,
     structures, and contractions. Fix every ERROR. Judge each WARNING by hand (a warning
     marks a word with an innocent sense, like a literal "test harness").
   - Read the draft once more against [semantic-slop.md](./references/semantic-slop.md)
     for cadences no script catches.

6. **Output the result.** No introductory filler or chat preamble.
