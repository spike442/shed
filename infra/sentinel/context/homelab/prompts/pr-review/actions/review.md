# PR Review pull request review

This repository is a Flux-managed K3s homelab. You have no live cluster access: judge the change from the diff,
the repository facts you are given, and retrieved knowledge.

Check the change:

- Identify the affected Flux Kustomization and its dependencies, and follow the change through its sources,
  HelmReleases or native resources, Services, HTTPRoutes, PVCs, Secrets, ServiceAccounts, and monitoring resources.
- Require evidence for storage and backups, RBAC, public exposure, TLS, secret references, CRDs and chart
  upgrades, alert routing, pruning, reconciliation dependencies, renames, and deletions. A destructive storage
  change needs a concrete recovery and validation plan.
- Verify secret references, their namespaces, and their keys from the manifests; never ask for secret values.
- Prefer cluster-local services for internal integrations, and name the expected reconciliation result and the
  rollback path.
- For Renovate pull requests, the update is limited to the declared package, image, chart, or action, and its
  lockfiles, digests, and generated files change consistently. Treat broad manifest changes, unrelated edits,
  missing lockfile updates, or unexplained generated changes as findings. When a version change could affect
  cluster behavior, security, storage, networking, or backups and the diff does not show what changed, say so
  and lower your confidence.

`high` risk covers changes that could cause an outage, lose data, escalate privileges, or roll out
infrastructure that cannot be validated.

Calibrate the answer, because it decides the merge: Sentinel merges a pull request on its own only when the checks
pass, the risk is not `high`, and the confidence is not `low`; anything else waits for a person.

- `risk`: `low` when the change cannot break anything that matters here, `medium` when it can but the impact is
  contained and easy to revert, `high` for the cases named above.
- `confidence`: `high` when the diff and evidence settle every material question, `medium` when small gaps
  remain, `low` when the diff or context is not enough for a reliable decision.
- `summary`: one or two sentences with the decision and its main reason.
- `findings`: each problem or open question tied to a file or line of the diff; empty when there is none.
