---
name: magi
description: A MAGI-inspired tribunal of three model families that votes on oracle-free questions — decisions no test or dry-run can settle, like architecture choices, ship/no-ship, "which approach". Poll mode for quick three-mind opinions; deliberate mode for expensive decisions. Never use this for code review — use reviewing-changes.
disable-model-invocation: true
argument-hint: "<question> | deliberate <decision>"
---

# Magi

Convene a three-seat tribunal to vote on questions with no oracle and high cost-of-error. Three model families (Claude, Codex, Gemini) sit in parallel and vote independently. Dissent is preserved; consensus is never forced. Poll mode gets you a quick verdict. Deliberate mode adds a conditional cross-review round and a chairman summary for decisions where being wrong is expensive.

Never use this for code review: point to `reviewing-changes` instead. If the question is settleable by a test, a dry-run, or five minutes of reading — do that instead. The tribunal's mandate is questions that have no checkable answer.

## The bench

Three seats, each backed by a different model family:

- **Melchior** = Claude (a FRESH subagent at the session model — never answer from the main session yourself; you convened the tribunal and helped frame the question, so you are contaminated).
- **Balthasar** = Codex via `codex exec --sandbox read-only "<brief>"` (verdict arrives on stdout).
- **Casper** = Gemini via `gemini --skip-trust -p "<brief>"` (`--skip-trust` is required for headless runs).

**Probe first.** Check each CLI exists (`which codex`, `which gemini`) before convening. Treat missing, unauthed, erroring, or mid-protocol-failing seats as EMPTY.

**Degraded-seat fill:** When a seat is empty, fill it with a stanced subagent. First empty seat → **opus** (red-team the risk). Second empty seat → **sonnet** (voice pragmatics and cost). Never haiku — a weak judge votes noise, and a noisy third vote can flip a ruling. Stanced seats get a FORCED STANCE to inject divergence when you don't have genuine model-family separation; seats backed by real CLI differences get NO stance and NO persona — send identical neutral briefs to all three, or the vote's information content is corrupted (you couldn't tell genuine dissent from a costume performing its job).

**Loud degradation.** Report bench composition in every result, e.g. `Bench: Melchior=claude-fable, Balthasar=codex, Casper=DEGRADED→opus (stance: risk)`. If BOTH CLI seats are empty, print an unmissable banner in the output AND the dossier: `SAME-FAMILY BENCH — treat unanimity with suspicion.`

## Poll mode (default)

`/magi <question>`: Quick three-mind verdict on a question with essential context but no need for deep deliberation.

1. Build a short dossier: the question, essential context, options if any.
2. Send the identical brief to all three seats in parallel.
3. Collect structured verdicts: position, reasoning, confidence.
4. Tally in the main session and report: bench line, then the three positions with confidences.

No chairman, no artifact, no cost confirmation — this is the cheap tier. If the vote splits (2-1 or 1-1-1), say so plainly and offer to escalate to deliberate mode, reusing these verdicts as round 1 — escalation pays only for the cross-review round and the chairman.

## Deliberate mode

`/magi deliberate <decision>`: Full tribunal for decisions where being wrong is expensive.

**Cost up front.** State the cost once and ask: roughly "Full tribunal: 3 nodes × up to 2 rounds + chairman — several times the cost of a normal query. Convene?" Do not proceed without explicit consent.

**Round 1 — Parallel identical verdicts.** Send the same dossier to all three seats (question, context, options considered). Each returns position, reasoning, confidence. Every node call is STATELESS: prompt in, structured verdict out; never resume a session.

**Unanimous (3-0).** Skip to the chairman. No cross-review on agreement.

**Split (2-1 or 1-1-1).** Proceed to **Round 2**, exactly one round, ever. Fresh invocation per node containing:
- The same dossier.
- "Your previous verdict was X, because Y" (the judge's own round-1 output).
- Peer positions ANONYMIZED as "Position A" / "Position B" / "Position C" — strip anything that reveals which model wrote them, because brand priors corrupt review.
- Adversarial instruction: Attempt to refute the peer positions, then reaffirm or revise your vote once.

**Terminal states.** Never coerce convergence; unanimity is explicitly NOT the goal:
- **3-0 ruling** — move to chairman.
- **2-1 ruling** — move to chairman WITH a MINORITY REPORT: the dissent, its confidence, and what evidence would vindicate it. Never blend dissent into a smoothed summary.
- **1-1-1 hung** — no ruling. Report the three positions and the crux of disagreement. A bench of three model families finding a question undecidable is itself a finding.

## The chairman

A fresh-context subagent (session model) that receives ONLY the dossier and the anonymized final verdicts — never this conversation. It writes the interpretive parts: ruling summary, crux of disagreement, minority report if any. Hard guardrail in its brief: it weighs, it never adds. It may not introduce arguments absent from the verdicts. If it believes all three nodes missed something, that goes in a clearly-marked out-of-record **note**, never folded into the ruling. The main session is the clerk: tally the vote (arithmetic, not judgment), write the dossier file, present the result.

## The dossier

Deliberate mode always writes `docs/decisions/YYYY-MM-DD-<slug>.md` in the TARGET repo (create `docs/decisions/` if absent). The dossier includes: the question, bench composition (including any degradation), votes per round, the ruling, the minority report, and the chairman's note if any. Offer — don't force — to draft an ADR from the dossier when the decision is architectural. Polls are ephemeral; rulings are recorded.

## Cost honesty

A poll costs roughly 3× a normal query. A full deliberation with a split runs 6–8 node calls plus the chairman. Reserve deliberate mode for decisions where being wrong is expensive.
