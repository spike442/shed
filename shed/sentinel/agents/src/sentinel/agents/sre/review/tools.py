from langchain_core.tools import BaseTool
from sentinel.agents.sre.knowledge import search_knowledge_tool
from sentinel.core.domain import AgentDomain

search_knowledge = search_knowledge_tool(
    AgentDomain.PULL_REQUEST_REVIEW,
    "Search historical Sentinel knowledge about this repository; verify findings against the current PR and repository.",
)

REVIEW_TOOLS: dict[str, BaseTool] = {"search_knowledge": search_knowledge}
