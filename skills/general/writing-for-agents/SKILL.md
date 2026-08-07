---
name: writing-for-agents
description: Write documents that agents read well. Use when creating or editing a skill, `AGENTS.md`, `CLAUDE.md`, an issue, a spec, or any prompt the model consumes.
---

Reference for writing any document an agent reads — a skill, `AGENTS.md`, `CLAUDE.md`, an issue, a spec, a runtime prompt. The format changes, the craft does not. You are writing so the agent takes the same steps each run, not so it produces the same words.

## The two loads

Every document and pointer you add spends one of two budgets:

- **Context load** — the cost of always-loaded material on the window. A `CLAUDE.md` line, a skill description, anything that sits in context every turn whether or not it fires.
- **Cognitive load** — the cost on the human: which documents exist and when to reach for each. This is not a cost to minimise. It is the price of human agency; spend it where human judgement matters, remove it where it does not.

Material reached only through a pointer escapes context load at the price of the pointer's own line. Material with no pointer at all rides entirely on cognitive load.

## Progressive disclosure and co-location

A document is made of **steps** (ordered actions) and **reference** (facts consulted on demand). A **branch** is a case the document handles on some runs but not others. Push reference behind a pointer when only some branches reach it; inline what every branch needs. Keep a concept's definition, rules, and caveats under one heading, so reading one part brings its neighbours with it.

## Leading words

A leading word is a compact concept the model already knows from pretraining — *tight*, *red*, *tracer bullets*. Pick one such word for a recurring idea and reuse that same word on every mention, rather than re-describing the idea in a fresh phrase each time. "A *tight* loop" and later "keep it *tight*" builds meaning onto the word; rewriting "a fast, deterministic, low-overhead loop" each time just spends tokens and hands the reader no shorthand. The repeated word works because it pulls in knowledge the model already has, so the behaviour you want arrives anchored to one cheap word.

**Don't steer by negation.** A prohibition names the behaviour you don't want, and naming it pulls it into the agent's attention — tell someone not to think of an elephant and the elephant is all they see. State the positive target instead: write "keep comments to one line", not "don't write long comments".

## The no-op test

The default move is deletion, not explanation. Read the document sentence by sentence and ask: if I delete this line, does the agent's *behaviour* change? The test is behavioural, not aesthetic. If the answer is no, the line pays context load and buys nothing. When a sentence fails, delete the whole sentence. Do not trim words from it; trimming leaves the no-op alive.

> **Warning:** Agents told to "streamline" optimise for length, because length is the thing they can see. The goal is changed behaviour, not fewer words.

## Skill-specific mechanics

For the rules that govern skills themselves — frontmatter, user-invoked versus model-invocable choice, router skills, and seams between skills — see `docs/agents/CONVENTIONS.md`. Do not restate those rules inside a skill; point at that file and keep this one about writing.
