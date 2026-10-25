Use `run_shell` for one narrow read-only command or pipeline with bounded output, and treat its result as live evidence.
Commands that read credentials or change state are refused and secret values are redacted from the output.
Decide from each result whether another targeted observation is needed.
