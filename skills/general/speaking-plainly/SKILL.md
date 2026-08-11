---
name: speaking-plainly
description: On-demand plain-language reset and rewriter. Translates dense text into clear, simple language while preserving all technical facts, identifiers, and numbers.
---

# Speaking Plainly

This skill helps you communicate clearly. Use it to reset your writing voice mid-session or rewrite dense text. It rewrites *text*; use `/wait-what` when you need to repair the conversation you are in.

## Mode 1: Reset Register
When a user asks to write in a plain register or reset, write to the plain-language floor from here on. Start from your system instructions' baseline voice rules (plain word choice, active voice, one idea per sentence, defining coined terms — magito installs these from `shared/SYSTEM-INSTRUCTIONS.md`). This skill adds:
- Write sentences under 20 words.
- Use contractions (*it's*, *don't*, *won't*).
- Never use AI-signature words (*delve*, *foster*, *leverage*, *transformative*). Consult [anti-ai-markers.md](./references/anti-ai-markers.md) for details.

## Mode 2: Rewrite Text
When given text to rewrite plainly:
1. **List all facts, numbers, and identifiers**: Extract key technical elements (e.g., variable names, functions, files, measurements) and acceptance criteria from the source. You must preserve these exactly. Never rename them.
2. **Consult reference files**:
   - [simple-wikipedia.md](./references/simple-wikipedia.md) (basic structure and tenses)
   - [plain-language-gov.md](./references/plain-language-gov.md) (sentence length, active voice)
   - [freddish.md](./references/freddish.md) (tone, positive phrasing)
   - [anti-ai-markers.md](./references/anti-ai-markers.md) (words and structures to avoid)
   - [semantic-slop.md](./references/semantic-slop.md) (pseudo-insight the word list can't catch)
3. **Draft the rewrite**: Keep it direct. Put your main point first. Do not summarize or add a conclusion.
4. **Verify fidelity**: Ensure every extracted acceptance criterion, fact, number, and identifier is present in the rewrite. Do not drop or rename any of these.
5. **Run the checkers** (both, relative to the skill directory):
   - Write the draft to a temporary file.
   - `python3 ./scripts/readability.py <temp_file>` — flags sentences over 25 words and passive stacking. Rewrite those sections.
   - `python3 ./scripts/anti-slop.py <temp_file>` — flags banned words, phrases, and structures from [anti-ai-markers.md](./references/anti-ai-markers.md). Fix every ERROR; judge each WARNING by hand (a warning marks a word with an innocent sense, like a literal "test harness"). The checker cannot see semantic pseudo-insight built from ordinary words, so read the draft once more against [semantic-slop.md](./references/semantic-slop.md) for the cadences no script catches.
6. **Output the final result**: Present the text to the user. Do not include introductory filler or chat preamble.
