---
name: writing-for-agents
description: Write documents that agents read well. Use when creating or editing a skill, `AGENTS.md`, `CLAUDE.md`, an issue, a spec, or any prompt the model consumes.
---

Reference for writing any document an agent reads — a skill, `AGENTS.md`, `CLAUDE.md`, an issue, a spec, a runtime prompt. The packaging differs; the writing does not. The goal is always the same process in the agent's head, not the same output on the page.

## The two loads

Every document and pointer you add spends one of two budgets:

- **Context load** — the cost of always-loaded material on the window. A `CLAUDE.md` line, a skill description, anything that sits in context every turn whether or not it fires.
- **Cognitive load** — the cost on the human: which documents exist and when to reach for each. This is not a cost to minimise. It is the price of human agency; spend it where human judgement matters, remove it where it does not.

Material reached only through a pointer escapes context load at the price of the pointer's own line. Material with no pointer at all rides entirely on cognitive load.

## Progressive disclosure and co-location

A document is made of **steps** (ordered actions) and **reference** (facts consulted on demand). Push reference behind a pointer when only some branches reach it. Inline what every branch needs. Keep a concept's definition, rules, and caveats under one heading, so reading one part brings its neighbours with it.

## Leading words

A leading word is a compact concept already in the model's pretraining — *tight*, *red*, *tracer bullets*. Repeat it as a token, never as a sentence. It anchors a whole region of behaviour cheaply by recruiting priors the model already holds. Negation is the failure mode beside it: steering by prohibition drags the forbidden behaviour into context. Prompt the positive.

## The no-op test

The default move is deletion, not explanation. Read the document sentence by sentence and ask: if I delete this line, does the agent's *behaviour* change? The test is behavioural, not aesthetic. If the answer is no, the line pays context load and buys nothing. When a sentence fails, delete the whole sentence. Do not trim words from it; trimming leaves the no-op alive.

> **Warning:** Agents told to "streamline" optimise for length, because length is the thing they can see. Length is not the goal. Behaviour is the goal.

## Skill-specific mechanics

For the rules that govern skills themselves — frontmatter, user-invoked versus model-invocable choice, router skills, and seams between skills — see [`docs/agents/CONVENTIONS.md`](../../../docs/agents/CONVENTIONS.md). Do not restate those rules inside a skill; point at that file and keep this one about writing.
