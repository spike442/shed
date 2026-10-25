from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class KnowledgeDocument:
    key: str
    tags: list[str]
    collection: str
    revision: str
    content: str
