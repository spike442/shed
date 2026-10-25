from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Any

from shed.agents.prompts import PromptStore
from shed.agents.runner import AgentRunner
from stonks.core.http import HttpSource, http_client
from stonks.core.objects import ObjectStore, s3_client
from stonks.dividends.agent.agent import DividendAgent
from stonks.dividends.agent.tools import ResearchSources
from stonks.dividends.config.settings import ResearchSettings, Settings
from stonks.dividends.sources.pages import PageReader
from stonks.dividends.sources.searxng import SearxngSearch
from stonks.dividends.storage.store import DividendStore

PROMPT_SCOPE = "stonks"


@dataclass(frozen=True)
class DividendRuntime:
    settings: Settings
    store: DividendStore
    reader: PageReader


@dataclass(frozen=True)
class ResearchRuntime(DividendRuntime):
    settings: ResearchSettings
    agent: DividendAgent


@dataclass(frozen=True)
class Clients:
    s3: Any
    http: HttpSource
    store: DividendStore
    reader: PageReader


def open_clients(resources: ExitStack, settings: Settings) -> Clients:
    s3 = s3_client(settings)
    resources.callback(s3.close)
    client = http_client(settings.http)
    resources.callback(client.close)
    http = HttpSource(client, settings.http)
    reader = PageReader(http, settings.pages)
    objects = ObjectStore(s3, settings.s3)
    store = DividendStore(objects, settings.storage)
    return Clients(s3=s3, http=http, store=store, reader=reader)


@contextmanager
def dividend_runtime(settings: Settings) -> Iterator[DividendRuntime]:
    with ExitStack() as resources:
        clients = open_clients(resources, settings)
        yield DividendRuntime(settings=settings, store=clients.store, reader=clients.reader)


@contextmanager
def research_runtime(settings: ResearchSettings) -> Iterator[ResearchRuntime]:
    with ExitStack() as resources:
        clients = open_clients(resources, settings)
        search = SearxngSearch(clients.http, settings.search)
        prompts = PromptStore(clients.s3, settings.s3.bucket)
        sources = ResearchSources(search=search, reader=clients.reader)
        runner = AgentRunner(settings.agent, settings.llm_api_key, prompts)
        resources.callback(runner.close)
        agent = DividendAgent(runner, sources, settings.pages, PROMPT_SCOPE)
        yield ResearchRuntime(settings=settings, store=clients.store, reader=clients.reader, agent=agent)
