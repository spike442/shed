import logging

import httpx
from sentinel.core.config.workflow import PrReviewSettings
from sentinel.core.contracts.executor import MergeOutcome, MergePullRequest, MergeStatus
from sentinel.core.contracts.reviews import PullRequest, RepositoryConfig, configured_repository
from sentinel.core.github import GitHubReader
from sentinel.core.kafka.contracts import ExecutorAction, ExecutorReturn, WorkflowRequest
from sentinel.workflow.messages import DomainMessages
from sentinel.workflow.routing import required_record
from sentinel.workflow.sre.reviews.repository import PrReviewRepository

logger = logging.getLogger(__name__)


class Merge:
    def __init__(
        self,
        settings: PrReviewSettings,
        reviews: PrReviewRepository,
        github: GitHubReader,
        messages: DomainMessages,
    ):
        self.repositories = settings.repositories
        self.merge_method = settings.merge_method
        self.reviews = reviews
        self.github = github
        self.messages = messages

    def on_request(self, workflow_request: WorkflowRequest) -> None:
        review_id = required_record(workflow_request)
        workflow_id = workflow_request.workflow_id
        review = self.reviews.get(review_id)
        if review is None:
            logger.warning("Merge for a deleted review review_id=%s", review_id)
            return
        repository = configured_repository(self.repositories, review["repository"], review["owner"])
        if repository is None:
            self.reviews.decline_merge(review_id, "The review repository is no longer configured.")
            return
        current = self.reviewed_revision(review_id, review, repository)
        if current is None:
            return
        claimed = self.reviews.claim_merge(review_id, workflow_id)
        if claimed:
            self.start_merge(review_id, current, workflow_id)

    def reviewed_revision(self, review_id: str, review: dict, repository: RepositoryConfig) -> PullRequest | None:
        try:
            state = self.github.pull_request_state(repository, review["pull_request_number"], review["head_sha"])
        except httpx.HTTPError as exc:
            error_type = type(exc).__name__
            self.reviews.decline_merge(review_id, f"GitHub lookup failed: {error_type}.")
            return None
        if state.merged_sha:
            self.reviews.mark_merged(review_id, state.merged_sha)
            return None
        current = state.pull_request
        if current is None:
            self.reviews.decline_merge(review_id, "The pull request is closed.")
            return None
        if current.head_sha != review["head_sha"]:
            self.reviews.decline_merge(
                review_id, "The PR changed since its review; Check now reviews its latest revision."
            )
            return None
        return current

    def start_merge(self, review_id: str, pull_request: PullRequest, workflow_id: str) -> None:
        merge = MergePullRequest(pull_request=pull_request, merge_method=self.merge_method)
        self.messages.command_executor(ExecutorAction.MERGE_PULL_REQUEST, review_id, workflow_id, merge)

    def on_executor_return(self, executor_return: ExecutorReturn) -> None:
        review_id = executor_return.record_id
        workflow_id = executor_return.workflow_id
        if executor_return.result is None:
            self.messages.fail(
                review_id, workflow_id, f"GitHub merge failed: {executor_return.error or 'ExecutorFailed'}"
            )
            return
        outcome = MergeOutcome.model_validate(executor_return.result)
        if outcome.status is not MergeStatus.MERGED:
            self.messages.fail(review_id, workflow_id, "GitHub no longer reports the PR mergeable and clean")
            return
        self.reviews.mark_merged(review_id, outcome.sha)
