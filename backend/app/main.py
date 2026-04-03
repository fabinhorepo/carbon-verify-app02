"""Carbon Verify - Aplicação Principal (Produção)."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Tentar rodar seed no primeiro init
    try:
        from app.data.seed import run_seed
        await run_seed()
    except Exception as e:
        import traceback
        print(f"⚠️ Seed error: {e}")
        traceback.print_exc()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────────────────
from app.api.auth import router as auth_router, org_router
from app.api.projects import router as projects_router
from app.api.fraud import router as fraud_router
from app.api.portfolio import router as portfolio_router, dashboard_router
from app.api.market import router as market_router
from app.api.reports import router as reports_router
from app.api.analytics import router as analytics_router
from app.api.integrations import router as integrations_router, satellite_router, web3_router, esg_router

PREFIX = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=PREFIX)
app.include_router(org_router, prefix=PREFIX)
app.include_router(projects_router, prefix=PREFIX)
app.include_router(fraud_router, prefix=PREFIX)
app.include_router(portfolio_router, prefix=PREFIX)
app.include_router(dashboard_router, prefix=PREFIX)
app.include_router(market_router, prefix=PREFIX)
app.include_router(reports_router, prefix=PREFIX)
app.include_router(analytics_router, prefix=PREFIX)
app.include_router(integrations_router, prefix=PREFIX)
app.include_router(satellite_router, prefix=PREFIX)
app.include_router(web3_router, prefix=PREFIX)
app.include_router(esg_router, prefix=PREFIX)


# ─── Health Check ────────────────────────────────────────────────────────
@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}


# ─── Serve Frontend Static Files ────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))
