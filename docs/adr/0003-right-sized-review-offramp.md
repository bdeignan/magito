# Right-size reviewing-changes for trivial diffs

`reviewing-changes` always fanned out two parallel sub-agent axes (Standards + Spec),
which over-serves a typo or docs-only change with sub-agent cost and latency. For small,
low-risk diffs the skill now skips the fan-out and does a single lightweight inline
review. Trade-off: thoroughness for cost on small diffs — mitigated by keeping the full
two axes whenever a small diff still touches a hook, the review/merge gate, security, or
a data boundary, and by never reporting a skipped axis as passed.
