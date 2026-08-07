---
name: wait-what
description: Re-pitch the last message when it did not land.
disable-model-invocation: true
---

Wait — that last message did not land. Re-pitch it: give the context I was missing, use fewer words, and speak in this project's vocabulary.

`/tldr` names the output, so the model clips words and loses you further. **Wait** names *your* state instead — comprehension failed here — which asks for fewer words *and* the missing premise at the same time.

Use the voice rules from `shared/SYSTEM-INSTRUCTIONS.md` and the terms in `docs/agents/GLOSSARY.md`. Do not rewrite a block of text; repair the conversation you are in. For a plain-language rewrite of dense text, use `/speaking-plainly` instead.
