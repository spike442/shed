from typing import Any

from fastapi import Request
from sentinel.core.domain import AgentDomain, PrReviewStatus
from sentinel.core.persistence.queries import PrReviewReader
from sentinel.core.state import history
from sentinel.core.state import review_rules as rules
from sentinel.core.state.workflows import PR_REVIEW_FLOW
from shed.api.domains.contract import ActionPrompt, ActionRequest, RecordAction, RecordLink, Tone
from shed.api.domains.workflow import RecordWorkflow
from shed.api.requests import PrReviewWorkflowRequests

MERGE_CONFIRM = "Merge this pull request now, regardless of the review's verdict?"
REPLAY_PROMPT = "Replay this review. Optionally tell the reviewer what to reconsider."

TONES = {
    PrReviewStatus.ACKNOWLEDGED.value: Tone.ACTIVE,
    PrReviewStatus.RUNNING.value: Tone.ACTIVE,
    PrReviewStatus.BLOCKED.value: Tone.WAITING,
    PrReviewStatus.FAILED.value: Tone.FAILED,
    PrReviewStatus.MERGED.value: Tone.DONE,
    history.SUPERSEDED: Tone.CLOSED,
}


class ReviewWorkflow(RecordWorkflow):
    id = "reviews"
    label = "Reviews"
    agent = AgentDomain.PULL_REQUEST_REVIEW
    statuses = PrReviewStatus
    flow = PR_REVIEW_FLOW
    tones = TONES
    reader_type = PrReviewReader

    def title(self, record: dict[str, Any]) -> str:
        return f"{record['repository']} #{record['pull_request_number']}"

    def actions(self, record: dict[str, Any]) -> list[RecordAction]:
        status = record["status"]
        actions = []
        if status in rules.MERGEABLE:
            actions.append(RecordAction(name="merge", label="Merge", tone="primary", confirm=MERGE_CONFIRM))
        if status in rules.REPLAYABLE:
            actions.append(RecordAction(name="replay", label="Replay", prompt=ActionPrompt(message=REPLAY_PROMPT)))
        confirm = "Delete this review record?"
        actions.append(RecordAction(name="delete", label="Delete", tone="danger", confirm=confirm))
        return actions

    def links(self, record: dict[str, Any]) -> list[RecordLink]:
        incident_id = record.get("incident_id")
        if not incident_id:
            return []
        return [RecordLink(domain=AgentDomain.SRE.value, workflow="incidents", record_id=incident_id, label="Incident")]

    async def run_action(self, request: Request, record: dict[str, Any], name: str, body: ActionRequest) -> str:
        review_id = record["id"]
        requests = PrReviewWorkflowRequests(request.app.state.settings, self.reader(request))
        prompt = body.prompt.strip()
        if name == "merge":
            return await requests.merge_review(review_id)
        if name == "replay":
            return await requests.replay_review(review_id, prompt)
        return await requests.delete_review(review_id)
