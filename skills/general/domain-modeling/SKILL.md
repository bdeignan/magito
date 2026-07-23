---
name: domain-modeling
description: Build and sharpen a project's domain model as you design — challenge terms against the glossary, sharpen fuzzy language, stress-test with edge-case scenarios, and write decisions down in docs/agents/GLOSSARY.md and ADRs the moment they crystallize. Use when pinning down terminology or a ubiquitous language, recording an architectural decision, or when another skill needs to maintain the domain model.
---

# Domain Modeling

Actively build and sharpen the project's shared language as you design — the *active* discipline of changing the model, not merely reading it. A tight glossary pays off every session: consistent names, easier navigation, fewer tokens spent decoding jargon. (Merely reading `docs/agents/GLOSSARY.md` for vocabulary is a one-line habit any skill can do — this skill is for when you're changing the model.)

## Files

Single context (most repos): one `docs/agents/GLOSSARY.md`, plus a root `docs/adr/`. Multi-context (a monorepo, or a project with distinct subsystems): a `CONTEXT-MAP.md` at the root pointing to per-area `GLOSSARY.md` files. Create files lazily — `docs/agents/GLOSSARY.md` when the first term resolves, `docs/adr/` when the first ADR is needed. Formats: [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md), [ADR-FORMAT.md](./ADR-FORMAT.md).

## During the session

- **Challenge against the glossary.** When a term conflicts with `docs/agents/GLOSSARY.md`, call it out: "your glossary defines *fold* as X, but you seem to mean Y — which is it?"
- **Sharpen fuzzy language.** An overloaded term gets a precise canonical one: "you're saying *sample* — do you mean a row, a draw, or a participant? Those are different things."
- **Stress-test with scenarios.** Invent edge cases that force precision about the boundaries between concepts.
- **Cross-reference the code.** When the user states how something works, check the code agrees; surface contradictions.
- **Update `docs/agents/GLOSSARY.md` inline.** Capture each term the moment it resolves — don't batch. The glossary is *only* a glossary: tight definitions of what terms mean, devoid of implementation detail. Not a spec, not a scratchpad.

## ADRs, sparingly

Offer an ADR only when all three hold: **hard to reverse**, **surprising without context**, and **the result of a real trade-off**. If any is missing, skip it. An ADR is one to three sentences recording *that* a decision was made and *why*.
