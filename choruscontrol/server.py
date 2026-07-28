from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from choruscontrol.adapters.pins import package_version
from choruscontrol.app_state import build_state
from choruscontrol.api.routes import router
from choruscontrol.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.cc = await build_state(settings)
    yield
    cc = app.state.cc
    if cc.metrics_sampler:
        await cc.metrics_sampler.stop()
    await cc.audit.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.product_title, version=package_version(), lifespan=lifespan)
    app.include_router(router)

    ui_dir = Path(__file__).parent / "ui"
    templates = Jinja2Templates(directory=str(ui_dir / "templates"))
    static = ui_dir / "static"
    static.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static)), name="static")

    @app.middleware("http")
    async def license_middleware(request: Request, call_next):
        path = request.url.path
        open_paths = {
            "/healthz",
            "/readyz",
            "/api/v1/admin/license",
            "/api/v1/admin/license/online-check",
            "/api/v1/admin/auth",
            "/api/v1/fleet/join",
            "/api/v1/fleet/heartbeat",
            "/api/v1/fleet/ack",
            "/api/v1/fleet/ledger-batch",
            "/api/v1/fleet/logs-batch",
            # BUG-017: Assistant ask stays reachable in grace; mutating executes denied inside handler
            "/api/v1/assistant/ask",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
        if path.startswith("/static") or path in open_paths or path.startswith("/api/v1/fleet/nodes/") and path.endswith("/commands"):
            return await call_next(request)
        # UI pages allowed in grace (read-only banner)
        cc = getattr(request.app.state, "cc", None)
        if cc is None:
            return await call_next(request)
        await cc.refresh_license()
        st = cc.license_status.state
        if st == "missing" or st == "invalid":
            if path.startswith("/api/"):
                return JSONResponse({"detail": "LICENSE_INVALID", "message": cc.license_status.message}, status_code=503)
        if st == "grace" and request.method not in ("GET", "HEAD", "OPTIONS"):
            if path.startswith("/api/") and path not in open_paths:
                return JSONResponse(
                    {"detail": "LICENSE_GRACE", "message": "read-only during license grace"},
                    status_code=403,
                )
        response = await call_next(request)
        response.headers["X-Chorus-License"] = st
        return response

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz(request: Request):
        cc = request.app.state.cc
        await cc.refresh_license()
        lic_ok = cc.license_status.state in ("valid", "grace") or cc.settings.demo_mode
        pg_ok = True
        pg_detail = {"configured": False}
        if cc.settings.database_url:
            pg_detail["configured"] = True
            if cc.postgres:
                pg_ok = await cc.postgres.ping()
                pg_detail["ok"] = pg_ok
                pg_detail["error"] = cc.postgres.last_error
            else:
                pg_ok = False
                pg_detail["ok"] = False
                pg_detail["error"] = "postgres sink missing"
        # Postgres failure does not fail ready in demo; production expects sink healthy when configured
        ready = lic_ok and (pg_ok or cc.settings.demo_mode or not cc.settings.database_url)
        if cc.settings.database_url and not cc.settings.demo_mode:
            ready = lic_ok and pg_ok
        return JSONResponse(
            {
                "ready": ready,
                "license": cc.license_status.state,
                "postgres": pg_detail,
                "oidc_enabled": cc.settings.oidc_enabled,
                "adapters": cc.adapter_sources,
            },
            status_code=200 if ready else 503,
        )

    tabs = ["overview", "trace", "taxonomy", "cortex", "guard", "logs", "admin"]

    def _page(request: Request, tab_name: str):
        cc = request.app.state.cc
        return templates.TemplateResponse(
            request,
            "shell.html",
            {
                "title": settings.product_title,
                "tab": tab_name,
                "tabs": tabs,
                "license_state": cc.license_status.state,
                "support_url": settings.insightits_support_url,
                "demo_mode": settings.demo_mode,
                "demo_token": settings.admin_token if settings.demo_mode else "",
            },
        )

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        return _page(request, "overview")

    def _make_tab_handler(tab_name: str):
        async def handler(request: Request):
            return _page(request, tab_name)

        handler.__name__ = f"tab_{tab_name}"
        return handler

    for _tab in tabs:
        app.add_api_route(
            f"/{_tab}",
            _make_tab_handler(_tab),
            response_class=HTMLResponse,
            methods=["GET"],
            name=f"tab_{_tab}",
        )

    @app.get("/memory", response_class=HTMLResponse)
    async def memory_alias(request: Request):
        """AG-001 deliberate: Memory UI consolidated into Cortex; APIs stay under /api/v1/memory/*."""
        from starlette.responses import RedirectResponse

        return RedirectResponse(url="/cortex", status_code=307)

    return app


app = create_app()
