from dataclasses import dataclass

from sentinel.workflow.sre.reviews.snapshot import JsonObject


@dataclass(frozen=True)
class Acknowledged:
    incident_id: str | None = None


@dataclass(frozen=True)
class PrReviewClaimed:
    workflow_id: str
    trigger: str
    prompt: str
    base_sha: str
    head_sha: str


@dataclass(frozen=True)
class PrReviewFailed:
    workflow_id: str
    error: str
    audit_actions: tuple[JsonObject, ...] = ()
    tool_budget: JsonObject | None = None


@dataclass(frozen=True)
class ResultSaved:
    workflow_id: str
    result: JsonObject


@dataclass(frozen=True)
class Merged:
    sha: str


@dataclass(frozen=True)
class ReplayRejected:
    reason: str


@dataclass(frozen=True)
class MergeClaimed:
    workflow_id: str


@dataclass(frozen=True)
class MergeDeclined:
    reason: str


@dataclass(frozen=True)
class Deleted:
    pass


Event = (
    Acknowledged
    | PrReviewClaimed
    | PrReviewFailed
    | ResultSaved
    | Merged
    | ReplayRejected
    | MergeClaimed
    | MergeDeclined
    | Deleted
)
