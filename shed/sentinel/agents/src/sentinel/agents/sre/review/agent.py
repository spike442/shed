from datetime import datetime
from typing import Any

from knowledge.client.client import KnowledgeClient
from sentinel.agents.sre.knowledge import KnowledgeContext, reference_material
from sentinel.agents.sre.review.tools import REVIEW_TOOLS
from sentinel.core.contracts.history import PriorAttempt
from sentinel.core.contracts.reviews import PreparedPrReview, PrReviewResult, PullRequest
from sentinel.core.domain import AgentDomain, ReviewTrigger
from shed.agents.runner import AgentRun, AgentRunner, AgentTask
from shed.core.audit import AuditLog

REVIEW = AgentTask(
    agent=AgentDomain.PULL_REQUEST_REVIEW.value,
    action="review",
    tools=REVIEW_TOOLS,
    context_schema=KnowledgeContext,
    answer=PrReviewResult,
)


class ReviewAgent:
    def __init__(self, runner: AgentRunner, knowledge: KnowledgeClient):
        self.runner = runner
        self.knowledge = knowledge

    def generate_review(
        self, request: PreparedPrReview, diff: str, audit: AuditLog, deadline: datetime
    ) -> PrReviewResult:
        message = self.review_prompt(request, diff)
        run = self._run(REVIEW, request, message, audit=audit, deadline=deadline)
        review = self.runner.run(REVIEW, run)
        submitted = review.model_dump(mode="json")
        audit.record("review_submitted", submitted)
        return review

    def review_prompt(self, request: PreparedPrReview, diff: str) -> str:
        pull_request = request.pull_request
        references = reference_material(request.rag_context)
        facts = pull_request_facts(pull_request)
        earlier = attempt_history(request.history)
        operator = self._replay_instruction(request)
        return (
            f"Review pull request #{pull_request.number} in "
            f"{pull_request.owner}/{pull_request.repository}.\n\n"
            f"{facts}{earlier}{operator}\n\n"
            f"Diff:\n{diff}{references}"
        )

    def _replay_instruction(self, request: PreparedPrReview) -> str:
        if request.trigger is not ReviewTrigger.REPLAY or not request.prompt:
            return ""
        template = self.runner.load_prompt(REVIEW, request.repository.scope, "actions/replay.md")
        rendered = template.replace("{{operator_prompt}}", request.prompt)
        return f"\n\n{rendered}"

    def _run(
        self,
        task: AgentTask,
        request: PreparedPrReview,
        message: str,
        *,
        audit: AuditLog,
        deadline: datetime,
    ) -> AgentRun:
        pull_request = request.pull_request
        context = KnowledgeContext(
            audit=audit, deadline=deadline, knowledge=self.knowledge, repository=request.repository.scope
        )
        return AgentRun(
            scope=request.repository.scope,
            message=message,
            context=context,
            name=f"pr-{task.action}-{pull_request.repository}-{pull_request.number}",
            tags=[f"pr-{task.action}", pull_request.repository],
            metadata={
                "repository": pull_request.repository,
                "pull_request": pull_request.number,
                "head_sha": pull_request.head_sha,
                "trigger": request.trigger.value,
            },
        )


def pull_request_facts(pull_request: PullRequest) -> str:
    labels = ", ".join(pull_request.labels)
    return (
        f"Title: {pull_request.title}\n"
        f"Author: {pull_request.author}\n"
        f"Head branch: {pull_request.head_ref}\n"
        f"Labels: {labels}\n"
        f"Head SHA: {pull_request.head_sha}"
    )


def attempt_history(history: list[PriorAttempt]) -> str:
    if not history:
        return ""
    lines = ["\n\nEarlier attempts on this pull request:"]
    for attempt in history:
        head = attempt.head_sha[:12]
        heading = f"- Attempt {attempt.number} ({attempt.trigger}) of head {head} at {attempt.started_at}"
        lines.append(f"{heading}: {attempt.status}")
        if attempt.prompt:
            lines.append(f"  operator instruction: {attempt.prompt}")
        lines.extend(attempt_result(attempt.result))
    return "\n".join(lines)


def attempt_result(result: dict[str, Any]) -> list[str]:
    lines = []
    if result.get("decision_reason"):
        lines.append(f"  decision: {result['decision_reason']}")
    if result.get("summary"):
        lines.append(f"  summary: {result['summary']}")
    lines.extend(f"  finding: {finding}" for finding in result.get("findings", []))
    for check in result.get("checks", []):
        if not check["passed"]:
            lines.append(f"  failed check {check['name']}: {check.get('output', '')}")
    if result.get("error"):
        lines.append(f"  error: {result['error']}")
    return lines
