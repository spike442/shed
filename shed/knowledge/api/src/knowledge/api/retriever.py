from knowledge.api.config import RagConfig
from knowledge.api.embeddings import Embeddings
from knowledge.api.index_store import KnowledgeIndexStore
from knowledge.client.contracts import RetrievedContext


class RagRetriever:
    def __init__(self, config: RagConfig, embeddings: Embeddings):
        self.config = config
        self.embeddings = embeddings

    def retrieve_context(
        self, store: KnowledgeIndexStore, collection: str, tag: str, query: str
    ) -> list[RetrievedContext]:
        embedding = self.embeddings.embed_query(query)
        rows = store.search_chunks(collection, tag, embedding, self.config.candidate_results)
        contexts = []
        seen_content = set()
        budget = self.config.max_context_tokens
        for row in rows:
            content = row["content"]
            if content in seen_content:
                continue
            length = self.embeddings.count_tokens(content)
            if length > budget:
                continue
            seen_content.add(content)
            context = RetrievedContext(content=content, source=row["source"], score=row["score"])
            contexts.append(context)
            budget -= length
            if len(contexts) == self.config.max_results:
                break
        return contexts
