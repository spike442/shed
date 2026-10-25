from collections.abc import Sequence

from stonks.core.cli import configure_logging, parse_step_arguments, run_step
from stonks.dividends.config.settings import ResearchSettings, Settings
from stonks.dividends.runtime import dividend_runtime, research_runtime
from stonks.dividends.steps.research import ResearchStep
from stonks.dividends.steps.validate import ValidateStep

STEPS = {"research": ResearchStep, "validate": ValidateStep}
SETTINGS = {"research": ResearchSettings, "validate": Settings}
RUNTIMES = {"research": research_runtime, "validate": dividend_runtime}


def main(argv: Sequence[str] | None = None) -> None:
    arguments = parse_step_arguments("stonks-dividends", STEPS, argv)
    settings_class = SETTINGS[arguments.step]
    settings = settings_class()
    configure_logging(settings.logging.level)
    open_runtime = RUNTIMES[arguments.step]
    with open_runtime(settings) as runtime:
        run_step(STEPS, runtime, arguments.step, arguments.trade_date)


if __name__ == "__main__":
    main()
