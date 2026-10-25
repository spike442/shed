from pydantic import BaseModel, Field


class RetrievedContext(BaseModel):
    content: str
    source: str
    score: float


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    collection: str = Field(min_length=1)
    tag: str = Field(min_length=1)


class KnowledgeSearchResponse(BaseModel):
    results: list[RetrievedContext]


class KnowledgeCollection(BaseModel):
    name: str
    tags: list[str]


class KnowledgeDomain(BaseModel):
    name: str
    collections: list[KnowledgeCollection]
    indexed: bool
