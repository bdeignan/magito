# Magi tribunal votes once per seat, then reviews only on split

The magi skill uses vote-first deliberation: each seat votes once, and a single
cross-review round runs only when the verdicts split — never rounds of consensus-seeking
debate. Seats are backed by heterogeneous CLIs (Codex, Gemini CLI), degrading loudly to
stanced Claude subagents when a CLI is missing or unauthed. Dissent is preserved as a
minority report rather than smoothed into a consensus summary. The 2025–2026 literature
on multi-agent debate motivates all three choices: unanimity-seeking causes sycophantic
convergence, voting captures most of debate's measured gain at a fraction of the cost,
and model-family diversity is the strongest lever for genuine disagreement. Trade-off: a
runtime dependency on sibling CLIs being installed and authed — mitigated by the
degradation ladder (stanced opus, then sonnet subagents) and by reporting bench
composition in every ruling so the reader can weigh the verdict accordingly.
