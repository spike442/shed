from shed.api.domains.domain import ConsoleDomain
from shed.api.domains.sre.domain import SreDomain

DOMAINS: tuple[ConsoleDomain, ...] = (SreDomain(),)
