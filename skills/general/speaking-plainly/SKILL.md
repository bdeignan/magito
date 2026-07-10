---
name: speaking-plainly
description: On-demand plain-language reset and rewriter. Translates dense text into clear, simple language while preserving all technical facts, identifiers, and numbers.
---

# Speaking Plainly

This skill helps you communicate clearly. Use it to reset your writing voice mid-session or rewrite dense text.

## Mode 1: Reset Register
When a user asks to write in a plain register, adjust your tone immediately. Follow these constraints:
- Use everyday language. Avoid jargon.
- Write sentences under 20 words. Focus on one idea per sentence.
- Always use active voice.
- Use contractions (*it's*, *don't*, *won't*).
- Never use AI-signature words (*delve*, *foster*, *leverage*, *transformative*). Consult [anti-ai-markers.md](file:///Users/brian/code/magito/skills/general/speaking-plainly/references/anti-ai-markers.md) for details.

## Mode 2: Rewrite Text
When given text to rewrite plainly:
1. **List all facts, numbers, and identifiers**: Extract key technical elements (e.g., variable names, functions, files, measurements) from the source. You must preserve these exactly. Never rename them.
2. **Consult reference files**:
   - [simple-wikipedia.md](file:///Users/brian/code/magito/skills/general/speaking-plainly/references/simple-wikipedia.md) (basic structure and tenses)
   - [plain-language-gov.md](file:///Users/brian/code/magito/skills/general/speaking-plainly/references/plain-language-gov.md) (sentence length, active voice)
   - [freddish.md](file:///Users/brian/code/magito/skills/general/speaking-plainly/references/freddish.md) (tone, positive phrasing)
   - [anti-ai-markers.md](file:///Users/brian/code/magito/skills/general/speaking-plainly/references/anti-ai-markers.md) (words and structures to avoid)
3. **Draft the rewrite**: Keep it direct. Put your main point first. Do not summarize or add a conclusion.
4. **Verify fidelity**: Ensure every extracted fact, number, and identifier is present in the rewrite.
5. **Run the readability checker**:
   - Write the draft to a temporary file.
   - Run the script: `python skills/general/speaking-plainly/scripts/readability.py <temp_file>`.
   - If the script flags sentences over 25 words or passive voice, rewrite those sections.
6. **Output the final result**: Present the text to the user. Do not include introductory filler or chat preamble.
