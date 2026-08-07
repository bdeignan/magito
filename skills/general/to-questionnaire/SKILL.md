---
name: to-questionnaire
description: Turn a decision you can't answer alone into a questionnaire for one person to fill in async or work through in a meeting.
disable-model-invocation: true
---

Turn something the user cannot answer alone into a **questionnaire** — a Markdown document they hand to one person. The recipient holds knowledge the user lacks; the questionnaire pulls it out of them.

**Grill the send, not the subject.** Interview the user only about the *send*, which they can always answer: who it goes to, and what they need back. The questions in the document then target the gap between what the recipient knows and what the user needs.

**One recipient per run.** A questionnaire goes to one person and does not branch. If three people each hold part of the answer, that is three runs, not one document with three tracks.

1. **Who is it going to?** Ask, in one exchange, the recipient's role, expertise, and relationship to the user. Done when you know who the recipient is and what they know that the user does not.
2. **What do you need back?** Ask, in one exchange, the specific decisions or facts the user cannot resolve alone. Done when you have a concrete list of what the user must walk away able to do or decide.
3. **Write the questionnaire.** Draft questions aimed at the gap, following the structure below. Write it to a slugged file under `.scratch/` and report the path. Done when the file exists and every item from step 2 is covered.

## Document structure

Order questions most-important-first, because async means one pass. Group them under `##` headings by theme once there are more than a handful.

<questionnaire-template>
# <Questionnaire title>

**Purpose:** why this exists and the decision riding on it.
**From:** <user> — **To:** <recipient> — **How your answers will be used:** <where they go>

## Context
One paragraph orienting a recipient who was not in the user's head.

## How to answer
Deadline and rough effort. Partial answers and "I don't know" are useful — flag anything you are unsure of.

## <Theme heading>
One `##` section per theme. Each question is one idea — never compound — with an answer stub beneath, and a one-line _why this matters_ only where it could be misread.

### <A single-idea question>
_Why this matters: <one line, only where needed>._

>

## Anything else?
A closing catch-all: anything we did not ask that we should know?
</questionnaire-template>

## Limitation

This skill has no ingest phase. It must run in the same conversation as the grilling that surfaced the questions, or it knows nothing about them. Do not assume it can read prior turns from another session.
