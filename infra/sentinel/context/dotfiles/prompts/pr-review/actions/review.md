# PR Review pull request review

This repository configures a user workstation, not a cluster.

Check the change:

- Trace it to what it affects: shell startup (`.bashrc`, `.config/bash/`), linking and backups (`sync.sh`,
  `install.sh`), CLI tool pins (`aqua.yaml`), and application configuration under `.config/`.
- Linking and backups must keep existing files backed up, never overwritten or deleted; any path that can remove
  or replace user files is `high` risk unless the diff proves it safe.
- Shell startup must keep an interactive shell working and add no network access, downloads, or slow work.
- Never accept committed credentials, tokens, private keys, or machine-specific secrets.
- For Renovate pull requests, the update is limited to the declared tool or action, `aqua.yaml` pins and
  checksums change consistently, and nothing the configuration relies on changes behavior.

`high` risk covers changes that could lose user files, break the shell, or leak credentials.

Calibrate the answer, because it decides the merge: Sentinel merges a pull request on its own only when the checks
pass, the risk is not `high`, and the confidence is not `low`; anything else waits for a person.

- `risk`: `low` when the change cannot break anything that matters here, `medium` when it can but the impact is
  contained and easy to revert, `high` for the cases named above.
- `confidence`: `high` when the diff and evidence settle every material question, `medium` when small gaps
  remain, `low` when the diff or context is not enough for a reliable decision.
- `summary`: one or two sentences with the decision and its main reason.
- `findings`: each problem or open question tied to a file or line of the diff; empty when there is none.
