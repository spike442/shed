# Sentinel configuration, releases, and operational diagnosis

Repository: `shed`. Scope: startup prerequisites and safe delivery.

## Configuration and credentials

Each process keeps non-secret YAML under `infra/sentinel/chart/config/`, loaded with pydantic-settings from
`SENTINEL_CONFIG_DIR` (default `/etc/sentinel`, where the chart mounts it). Those files hold no site values:
Kafka bootstrap servers, consumer group, and topic names, S3, database and ClickHouse hosts and names, the
Prometheus URL, and the enabled agents come only from chart values, which `templates/_config.tpl` overlays. External
Secrets inject environment credentials. The Shed API holds database and Kafka credentials only.
Workflow also holds the GitHub App credentials, which it uses only to mint read-only installation tokens for
discovery, replay, and fix reads; sentinel-executor holds them for pushes, pull requests, and merges; `workflow.yaml` supplies shared knowledge settings and
separates incident and review settings under `sre` and `pr_review`.
`common/llm.yaml` supplies the shared agent endpoint and model; agent files supply
their own LLM settings.
The current default is the OpenAI API (`https://api.openai.com/v1`) with the model named in `common/llm.yaml`,
called through LangChain's OpenAI client and the Responses API. `LLM_API_KEY` holds the OpenAI API key; it is
delivered by the Homelab secret and never committed here. `request_timeout_seconds` bounds each model request and
`max_retries` its retries.
Homelab supplies PostgreSQL and ClickHouse database and role names through `postgres` and
`clickhouse` chart values. It supplies Kafka users and the consumer group through `kafka` values. The chart's `kafka.topics`
map defines each topic's name and partitions once: the chart renders it into each process's
configuration and into Strimzi `KafkaTopic`s in `kafka.topicNamespace` (with `kafka.topicReplicas`
and `kafka.topicRetentionMs`), annotated to survive an uninstall.
Fix commits are created through the GitHub API with GitHub App installation tokens, so GitHub signs them
as the App and there is no SSH deploy or signing key. The platform shares one S3
credential, `S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY` from the `sentinel` item, for knowledge,
SRE and PR Review prompts, and `task artifacts`. The knowledge service owns read-only
PostgreSQL and ClickHouse credentials for indexing and retrieval. SRE and PR Review own their
model and Kafka credentials.
All Sentinel credentials live in the single 1Password item `sentinel`, and each `sentinel-secrets` key matches its
field name. Exact field names belong
in current settings classes and ExternalSecrets, not in long-lived examples.

S3 context is grouped by repository under `context/<repository>/`. Mandatory agent prompts
live in `prompts/<agent>/` and retrieved documents live in `shed/sentinel/knowledge/`. Missing prompt
credentials or objects fail startup or the relevant action. Both agents load each prompt once per
process through `PromptStore`; restart a worker to pick up an uploaded prompt change.
Knowledge indexing has a separate lifecycle from prompt refresh.

HOME, KUBECONFIG, and mounted service-account material belong in the container/deployment
environment. Only the SRE pod (both agents) and the sentinel-executor pod mount a service-account token; the API
and workflow pods do not. The SRE pod runs as the `sre` service account, whose kubeconfig grants only the read-only `sre-read` ClusterRole;
sentinel-executor's grants only the manual-action operations of its `sentinel-executor` ClusterRole. Workers use internal cluster Services, not public ingress.

## Build and release

CI and Publish call one reusable workflow, `shed.yml`; Publish sets `publish: true` and the version of each module it releases.
Every run checks Python (format, lint, startup tests), the UI build, the Stonks Airflow DAG import, and each chart values file of
the three charts (`infra/shed/chart/`, `infra/sentinel/chart/`, and `infra/stonks/chart/`), and audits dependencies (`pip-audit`,
`npm audit`) without blocking. `shed/<module>/Dockerfile` is the image `<module>` and every `shed/<module>/<member>/Dockerfile` the image `<module>-<member>` (today `shed`,
which builds the UI into the API image, `sentinel-workflow`, `sentinel-sre` with both SRE agents' workers, `sentinel-executor`, `sentinel-knowledge`,
`stonks-api`, `stonks-ingest`, `stonks-dividends`, `stonks-spark`). A pull request builds only the images of the modules whose paths
changed (`dorny/paths-filter`: the module's `shed/` and `infra/` folders, the workspace files, and the Sentinel libraries the shed
and Stonks images copy), and every other run builds all of them. Outside pull requests each built image is scanned with Trivy (HIGH
and CRITICAL with a fix) and reported to GitHub code scanning under `image-<image>`; CI also runs weekly so new advisories surface
without a change.

Each module (`shed`, `sentinel`, `stonks`) has its own version, recorded in the repository like a Maven multi-module build: every project of the module, its libraries included, `uv.lock`, and
its chart's `version` and `appVersion` hold its last released version. The `core` module (`shed-core`: audit log, deadline, digests,
secret redaction, and `LLMConfig`) is shared by every module and released as its own module (`core-<version>`, with no image or chart; the workspace root carries its version); a `core` release releases every module too. Publish runs by hand on `main`: `paulhatch/semantic-version` versions each module from its own last
`<module>-<version>` tag and the Conventional Commits since (`feat:` minor, `!:` or `BREAKING CHANGE:` major, otherwise patch), and
only modules whose paths changed are released. Their images are built with the version stamped into their packages through the
Dockerfile's `VERSION` build argument (so `importlib.metadata` reports it), pushed, and signed, and their charts are published as
`oci://ghcr.io/spike442/charts/shed/<module>`. After everything is published, Publish writes each released module's version into its projects,
`uv.lock`, and chart, commits that to `main`, tags that version commit `<module>-<version>`, and notifies Homelab Renovate, which moves the released charts, and for Stonks the Airflow `STONKS_VERSION` and the
`stonks` release tag Airflow git-syncs the DAGs from, in one group. The `setup-shed` composite action installs uv, Python, and the
locked workspace; the Python version comes from `shed/pyproject.toml`.

Each deployable module has its own image. Workloads pull with `imagePullPolicy: IfNotPresent`: a version tag is never reused, so a cached image is always the released one. The `shed` image is the API serving the built React app; one workflow image
runs one Deployment for both enabled workflows. Each agent and sentinel-executor image installs only its module dependencies. The knowledge image
includes the pinned local model.
Sentinel runs no Spark; Spark belongs to Stonks only (`stonks-spark`, the daily bars batch). Dotfiles own workstation CLI tools; CI installs its pinned Helm
version directly, and each Docker image installs only the CLI tools it needs. Each module's
`pyproject.toml` declares its direct runtime dependencies. CLI availability and Python
dependency installation are separate prerequisites. The root Taskfile coordinates setup,
deployment, and knowledge indexing.

## Diagnose by failure layer

Startup: check Secret delivery, YAML validation, prompt objects, model connectivity,
PostgreSQL platform state, ClickHouse schema, local embedding model,
and Kafka authentication/topic existence. The Shed API's health/version (the `shed` Deployment, from the shed chart,
which mounts `sentinel-config`) and the UI's `domains.json` must be reachable; check the workflow pod, the sentinel-executor pod, and Kafka consumption separately.

Missing work: trace monitoring or GitHub discovery, request and command topics, consumer lag,
worker logs, active state, stored decision, and notification. A blocked
diagnosis is different from a transport error. GitHub failures surface in sentinel-executor's logs
and in the result the workflow records; a refused commit or branch update (a branch
that moved, a missing contents write permission) is different from GitHub API authentication. An Alertmanager event whose handling fails marks its incident failed and is skipped without retry;
inspect the workflow logs and `sentinel_cluster_alert_events_total` before replaying them. A UI error can be backend schema/configuration failure, not missing frontend assets.

Rollout: publish the Sentinel images, change their Homelab declarations, and let Flux reconcile.
Do not apply schema resets, upload S3 files, trigger work, or mutate cluster state merely while
reviewing documentation. Never log settings objects or decrypted secret values.

Sources: `.github/workflows/`, `.github/actions/`, `Taskfile.yml`,
`sentinel/*/Dockerfile`,
`shed/sentinel/sre/src/sentinel/sre/incidents/settings.py`, `shed/sentinel/sre/src/sentinel/sre/reviews/settings.py`,
`shed/sentinel/core/src/sentinel/core/config/`, `shed/shed/api/src/shed/api/config.py`, and
`shed/sentinel/core/src/sentinel/core/config/workflow.py`.
