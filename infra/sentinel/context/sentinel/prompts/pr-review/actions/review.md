# PR Review pull request review

This repository is Shed: one uv workspace under `shed/` with three modules, `shed` (the API and UI in one image),
`sentinel` (the SRE domain: workflow, SRE agents, executor, knowledge), and `stonks` (the Stonks data platform),
and each module's infrastructure under `infra/<module>/` (its Helm chart, and its agent context, SQL schemas, or
Airflow DAGs). There is no live cluster to inspect from this review.

Check the change against the repository's rules:

- State changes go through a domain's pure state machine and `postgres.apply_event`; a new status change adds
  its edge to the graphs in `sentinel.core.state.workflows`.
- The workflow reads what it decides on but changes GitHub or the cluster only through executor commands, and the
  Shed API holds no GitHub credentials.
- Agents never read secrets, and credentials stay `SecretStr` until a client boundary. Any weakening of the agent
  command allow-lists, secret redaction, credential handling, RBAC, or the merge policy is `high` risk.
- Installs are fresh: a schema change edits the current `infra/sentinel/sql/<version>/` folder with no
  migration and requires recreating the database; name that in the findings.
- Kafka contracts stay compatible between the producer and consumer the diff changes, and chart values, config
  files, and the settings models that read them change together.
- Stonks keeps raw data immutable, stores a dividend fact only after the `validate` step's checks, and uses only
  free data sources; DAG changes in `infra/stonks/airflow/dags/` must work with the Stonks images they run.
- Code carries no comments (functional ones aside), and tests stay one startup test per deployable module.
- For Renovate pull requests, the update is limited to the declared package, image, chart, or action, and
  `shed/uv.lock` and `package-lock.json` change consistently with their manifests.

`high` risk covers changes that could break an agent safety boundary, corrupt or drop stored state, or ship a
deployment change that cannot be validated.

Calibrate the answer, because it decides the merge: Sentinel merges a pull request on its own only when the checks
pass, the risk is not `high`, and the confidence is not `low`; anything else waits for a person.

- `risk`: `low` when the change cannot break anything that matters here, `medium` when it can but the impact is
  contained and easy to revert, `high` for the cases named above.
- `confidence`: `high` when the diff and evidence settle every material question, `medium` when small gaps
  remain, `low` when the diff or context is not enough for a reliable decision.
- `summary`: one or two sentences with the decision and its main reason.
- `findings`: each problem or open question tied to a file or line of the diff; empty when there is none.
