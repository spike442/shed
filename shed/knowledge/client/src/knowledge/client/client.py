import httpx
from knowledge.client.contracts import KnowledgeSearchRequest, KnowledgeSearchResponse, RetrievedContext
from shed.core.audit import AuditLog


class KnowledgeClient:
    """The knowledge service's ``/v1`` API, searching one domain's collections."""

    def __init__(self, endpoint: str, domain: str):
        self.domain = domain
        self.client = httpx.Client(base_url=endpoint, timeout=30)

    def search(self, request: KnowledgeSearchRequest) -> list[RetrievedContext]:
        body = request.model_dump(mode="json")
        response = self.client.post(f"/v1/domains/{self.domain}/search", json=body)
        response.raise_for_status()
        payload = response.json()
        answer = KnowledgeSearchResponse.model_validate(payload)
        return answer.results

    def search_text(self, request: KnowledgeSearchRequest, audit: AuditLog) -> str:
        try:
            results = self.search(request)
        except httpx.HTTPError as exc:
            error_type = type(exc).__name__
            audit.record("knowledge_search_failed", {"error": error_type})
            return "Knowledge search is unavailable; continue with the evidence you have."
        excerpts = [f"Source: {item.source}\nScore: {item.score:.3f}\n{item.content}" for item in results]
        return "\n\n".join(excerpts) or "No matching knowledge found."

    def close(self) -> None:
        self.client.close()
