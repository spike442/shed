import logging
from datetime import datetime

from sentinel.agents.sre.review.agent import ReviewAgent
from sentinel.core.contracts.reviews import DecidedPrReview, PreparedPrReview
from sentinel.core.kafka.contracts import RunFailure
from sentinel.sre.reviews.policy import decide_merge
from sentinel.sre.reviews.settings import Settings
from sentinel.sre.reviews.workspace import WorkspaceManager
from shed.core.audit import AuditLog
from shed.core.deadline import remaining_seconds

logger = logging.getLogger(__name__)


def log_tool_budget(audit: AuditLog, repository: str, number: int) -> None:
    budget = audit.tool_budget
    if budget.exhausted:
        exhausted = ",".join(budget.exhausted_tools)
        logger.warning(
            "PR review tool budget exhausted repository=%s number=%s limit=%s tools=%s calls=%s",
            repository,
            number,
            budget.limit,
            exhausted,
            budget.calls,
        )


class ReviewRun:
    def __init__(self, settings: Settings, workspace: WorkspaceManager, agent: ReviewAgent):
        self.settings = settings
        self.workspace = workspace
        self.agent = agent

    def review(self, request: PreparedPrReview, deadline: datetime) -> DecidedPrReview | RunFailure:
        pull_request, repository = request.pull_request, request.repository
        audit = AuditLog()
        try:
            remaining_seconds(deadline)
            with self.workspace.checkout_repository(pull_request, repository, audit, deadline) as checkout:
                checks = self.workspace.run_checks(checkout, pull_request, audit, deadline)
                max_diff_bytes = self.settings.review.max_diff_bytes
                diff = self.workspace.read_diff(checkout, pull_request, audit, deadline, max_diff_bytes)
                review = self.agent.generate_review(request, diff, audit, deadline)
        except Exception as error:
            logger.exception("PR review failed repository=%s number=%s", repository.name, pull_request.number)
            failure = type(error).__name__
            log_tool_budget(audit, repository.name, pull_request.number)
            return RunFailure(error=failure, audit_actions=audit.actions, tool_budget=audit.tool_budget)
        log_tool_budget(audit, repository.name, pull_request.number)
        checks_passed = all(check.passed for check in checks)
        decision = decide_merge(review, self.settings.review, checks_passed)
        logger.info(
            "PR review completed repository=%s number=%s risk=%s confidence=%s merge=%s",
            repository.name,
            pull_request.number,
            review.risk,
            review.confidence,
            decision.merge,
        )
        return DecidedPrReview(
            pull_request=pull_request,
            checks=checks,
            review=review,
            decision=decision,
            audit_actions=audit.actions,
            tool_budget=audit.tool_budget,
        )
