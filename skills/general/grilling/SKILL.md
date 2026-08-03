---
name: grilling
description: Interview the user relentlessly about a plan or design, one question at a time, to reach a shared understanding before building. Opens with a mandatory reconnaissance pass so questions build on what the code already does instead of re-solving it. Reach for it when a plan needs stress-testing and the open questions are worth walking through in order.
disable-model-invocation: true
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

**Before the first question, run reconnaissance** — unconditionally, per [references/recon.md](./references/recon.md). Survey the area the plan touches and show me a short brief of what the codebase already does there: the established patterns, the past decisions that bear on it, and what is already solved. Then question only what the survey could not settle. The failure this prevents is asking from ignorance and re-solving what already exists; a conditional "look if you suspect an answer" never fires when the agent has no suspicion, so recon is not conditional.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.
