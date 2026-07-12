---
name: magi
description: A MAGI-inspired tribunal of three seats — ideally three model families — that votes on oracle-free questions — decisions no test or dry-run can settle, like architecture choices, ship/no-ship, "which approach". Poll mode for quick three-mind opinions; deliberate mode for expensive decisions. Never use this for code review — use reviewing-changes.
disable-model-invocation: true
argument-hint: "<question> | deliberate <decision> | config"
---

# Magi

Convene a three-seat tribunal to vote on questions with no oracle and high cost-of-error. Three seats — ideally three model families — vote independently in parallel; dissent is preserved.

Never use this for code review: point to `reviewing-changes` instead. If the question is settleable by a test, a dry-run, or five minutes of reading — do that instead.

## The bench

The three seats:

- **Melchior** = Claude, always a FRESH subagent at the session model — never answer from the main session yourself; you convened the tribunal and helped frame the question, so you are contaminated.
- **Balthasar** and **Casper** = shell-command seats, resolved from machine-local config.

**Seat resolution.** Read `~/.magito/bench.toml` if it exists. Each seat declares `cmd` — a shell command that takes the brief as its final argument and prints the verdict on stdout — and `family`, the model family that actually answers. Declare the family of the configured model, not the CLI vendor: BYOK (bring-your-own-key) CLIs run any provider's models, so the binary name is not a proxy for what's voting. A seat may also declare `model`: if `cmd` contains the literal placeholder `{model}`, substitute it before invocation; if `cmd` has no placeholder, `model` is documentation only. This keeps the durable choice — which model backs a seat — stable even when a CLI's flag syntax drifts. Example:

```toml
# ~/.magito/bench.toml — machine-local, never synced
[seats.balthasar]
cmd = "codex exec --sandbox read-only"
family = "openai"

[seats.casper]
cmd = "script -q /dev/null agy --sandbox -p --model {model}"
model = "claude-opus"
family = "anthropic"
```

The vetted roster of candidate CLIs — verified headless syntax, auth requirements, quirks — lives in [references/seat-candidates.md](references/seat-candidates.md).

**Probe first.** A seat is live only if its command answers a ping: send "Reply with exactly: VERDICT-OK" and confirm the token comes back on stdout. Missing binary, auth failure, quota exhaustion, and mid-protocol errors all count the same — the seat is EMPTY.

**Bootstrap.** If `~/.magito/bench.toml` doesn't exist, create it before convening: ping the roster candidates whose binaries are installed, seat the two live commands that maximize family diversity, and write the remaining candidates as commented-out entries the user can enable later. Tell the user what you wrote, then proceed with that bench. If fewer than two candidates answer, write the file anyway (live seats filled, the rest commented) and convene degraded. Never overwrite an existing `bench.toml` on your own initiative — it is the user's file. The one sanctioned exception is `/magi config` below, which always asks before writing.

**Degraded-seat fill:** When a seat is empty, fill it with a stanced subagent. First empty seat → **opus** (red-team the risk). Second empty seat → **sonnet** (voice pragmatics and cost). Never haiku — a weak model votes noise, and a noisy third vote can flip a ruling. Stanced seats get a FORCED STANCE to inject divergence when you don't have genuine model-family separation; seats backed by distinct model families get NO stance and NO persona — send identical neutral briefs to all three, or you can't tell genuine dissent from a costume performing its job.

**Loud degradation.** Report bench composition in every result, with each seat's family, e.g. `Bench: Melchior=<session model> (anthropic), Balthasar=codex (openai), Casper=DEGRADED→opus (anthropic, stance: risk)`. Count distinct families across the seated bench using the declared `family` values — Melchior and fill seats are anthropic. If the bench spans fewer than two families, print an unmissable banner in the output AND the dossier: `SAME-FAMILY BENCH — treat unanimity with suspicion.` If exactly two of three seats share a family, say so in the bench line: a majority that shares a family is weaker evidence than one that crosses families.

## `/magi config`

Re-probe the bench and repair `bench.toml` — standalone, no tribunal convened, no dossier written.

1. Read `~/.magito/bench.toml` if present; treat an absent file the same as bootstrap's empty state.
2. Probe every candidate in `references/seat-candidates.md`, installed or not — whether it's currently live, commented out, or absent from the file entirely. A candidate installed since the last bootstrap or config run only gets picked up if you probe it here.
3. Diff against the current file: newly live, newly dead, unchanged. Preserve any existing seat's `model` field across the diff when its `cmd` template is unchanged; if a candidate row offers more than one usable model for a seat being newly configured, ask which to use.
4. Show the user the diff and the resulting bench (which seats would be live, their families), then ask once before writing. Write only on yes; leave the file untouched on no.

## Poll mode (default)

`/magi <question>`: Quick three-mind verdict on a question with essential context but no need for deep deliberation.

1. Build a short dossier: the question, essential context, options if any.
2. Send the identical brief to all three seats in parallel.
3. Collect structured verdicts: position, reasoning, confidence.
4. Tally in the main session and report: bench line, then the three positions with confidences.

No chairman, no artifact, no cost confirmation — this is the cheap tier. Never spawn a chairman subagent for a poll: you write the tally and report directly, in this response. If you notice yourself reaching for anonymization, a minority report, or a crux-of-disagreement writeup, stop — those are deliberate-mode-only concepts. If the vote splits (2-1 or 1-1-1), say so plainly and offer to escalate to deliberate mode, reusing these verdicts as round 1 — escalation pays only for the cross-review round and the chairman.

## Deliberate mode

`/magi deliberate <decision>`: Full tribunal for decisions where being wrong is expensive.

**Cost up front.** State the cost once and ask: roughly "Full tribunal: 3 seats × up to 2 rounds + chairman — 6–8 seat calls if the vote splits, several times the cost of a normal query. Convene?" Do not proceed without explicit consent. (A poll, by contrast, costs roughly 3× a normal query — that's why it needs no gate.)

**Round 1 — Parallel identical verdicts.** Send the same dossier to all three seats (question, context, options considered). Each returns position, reasoning, confidence. Every seat call is STATELESS: prompt in, structured verdict out; never resume a session.

**Unanimous (3-0).** Skip to the chairman. No cross-review on agreement.

**Split (2-1 or 1-1-1).** Proceed to **Round 2**, exactly one round, ever. Fresh invocation per seat containing:
- The same dossier.
- "Your previous verdict was X, because Y" (the seat's own round-1 output).
- Peer positions ANONYMIZED as "Position A" / "Position B" / "Position C" — strip anything that reveals which model wrote them, because brand priors corrupt review.
- Adversarial instruction: Attempt to refute the peer positions, then reaffirm or revise your vote once.

**Terminal states.** Never coerce convergence:
- **3-0 ruling** — move to chairman.
- **2-1 ruling** — move to chairman WITH a MINORITY REPORT: the dissent, its confidence, and what evidence would vindicate it. Never blend dissent into a smoothed summary.
- **1-1-1 hung** — no ruling. Report the three positions and the crux of disagreement. A full-diversity bench finding a question undecidable is itself a finding.

## The chairman

A fresh-context subagent (session model) that receives ONLY the dossier and the anonymized final verdicts — never this conversation. It writes the interpretive parts: ruling summary, crux of disagreement, minority report if any. Hard guardrail in its brief: it weighs, it never adds. It may not introduce arguments absent from the verdicts. If it believes all three seats missed something, that goes in a clearly-marked out-of-record **note**, never folded into the ruling. The main session is the clerk: tally the vote (arithmetic, not judgment), write the dossier file, present the result.

## The dossier

Deliberate mode always writes `docs/decisions/YYYY-MM-DD-<slug>.md` in the TARGET repo (create `docs/decisions/` if absent). The dossier includes: the question, bench composition (including any degradation), votes per round, the ruling, the minority report, and the chairman's note if any. Offer — don't force — to draft an ADR from the dossier when the decision is architectural. Polls are ephemeral; rulings are recorded.
