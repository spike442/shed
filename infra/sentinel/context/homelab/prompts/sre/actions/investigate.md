Investigate the alert with the fewest targeted tool calls that establish its cause. Correlate it with the live
state, the metrics, and the synchronized repository, and find the desired-state file that owns the failing
resource before proposing a change.

When the desired state is already correct, look for reconciliation or live-state drift and report what you
found; never invent a no-op pull request or bypass GitOps. Then choose the decision the evidence supports: a
repository fix, manual actions, or a blocked result.
