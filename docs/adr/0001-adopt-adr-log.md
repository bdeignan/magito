# Adopt an ADR log; defer CONTEXT.md

magito ships `domain-modeling` guidance telling projects to record decisions in
`docs/adr/` and domain terms in `CONTEXT.md`, but kept neither for itself — so real
decisions (the review-gate marker design, the `issues.sh pr` scope cut) were getting
lost in machine-local handoffs. We adopt `docs/adr/` going forward, writing ADRs as
decisions arise rather than backfilling past ones. We defer `CONTEXT.md` until a domain
term is actually contested; `CLAUDE.md` carries magito's domain language adequately for
a repo this size.
