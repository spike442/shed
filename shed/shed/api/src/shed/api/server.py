import mimetypes
from importlib.metadata import version
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sentinel.core.errors import Conflict, NotFound, SentinelError
from shed.api.domains.domain import domain_router
from shed.api.domains.registry import DOMAINS
from shed.api.lifespan import application_lifespan
from sqlalchemy import text
from starlette.exceptions import HTTPException
from starlette.types import Scope

ERROR_STATUS = {NotFound: 404, Conflict: 409}
API_PREFIX = "/api"
UI_DIRECTORY = Path("/app/ui")
IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"

mimetypes.add_type("application/manifest+json", ".webmanifest")


class ShedUi(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path.startswith("api/") or path.startswith("assets/"):
                raise
            response = await super().get_response("index.html", scope)
        response.headers["Cache-Control"] = IMMUTABLE if path.startswith("assets/") else REVALIDATE
        return response


async def domain_error(_request: Request, error: Exception) -> JSONResponse:
    status = next((code for kind, code in ERROR_STATUS.items() if isinstance(error, kind)), 400)
    return JSONResponse(status_code=status, content={"detail": str(error)})


def create_app() -> FastAPI:
    release = version("sentinel-core")
    application = FastAPI(title="Shed", version=release, lifespan=application_lifespan)
    application.add_exception_handler(SentinelError, domain_error)

    @application.get(f"{API_PREFIX}/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": release}

    @application.get(f"{API_PREFIX}/readyz")
    def readyz() -> dict[str, str]:
        probe = text("SELECT 1")
        with application.state.database.engine.connect() as connection:
            connection.execute(probe)
        return {"status": "ready"}

    for domain in DOMAINS:
        router = domain_router(domain)
        application.include_router(router, prefix=API_PREFIX)
    if UI_DIRECTORY.is_dir():
        ui = ShedUi(directory=UI_DIRECTORY, html=True)
        application.mount("/", ui, name="ui")
    return application


app = create_app()
