"""Carbon Verify v3 — Main Application (Production)."""
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

# ─── Routes (v3 modular) ────────────────────────────────────────────────
from app.api.auth import router as auth_router, org_router
from app.modules.projects.routes import router as projects_router
from app.modules.fraud_ops.routes import router as fraud_ops_router
from app.modules.portfolio.routes import (
    portfolio_router, dashboard_router,
    compliance_router, market_router, workspace_router,
)

PREFIX = settings.API_V1_PREFIX

# Auth
app.include_router(auth_router, prefix=PREFIX)
app.include_router(org_router, prefix=PREFIX)

# Core v3 modules
app.include_router(projects_router, prefix=PREFIX)
app.include_router(fraud_ops_router, prefix=PREFIX)
app.include_router(portfolio_router, prefix=PREFIX)
app.include_router(dashboard_router, prefix=PREFIX)
app.include_router(compliance_router, prefix=PREFIX)
app.include_router(market_router, prefix=PREFIX)
app.include_router(workspace_router, prefix=PREFIX)

# Legacy routes that still work
try:
    from app.api.reports import router as reports_router
    app.include_router(reports_router, prefix=PREFIX)
except Exception as e:
    print(f"⚠️ Legacy reports routes not loaded: {e}")

try:
    from app.api.analytics import router as analytics_router
    app.include_router(analytics_router, prefix=PREFIX)
except Exception as e:
    print(f"⚠️ Legacy analytics routes not loaded: {e}")

# Try to load optional integration routes
try:
    from app.api.integrations import router as integrations_router
    app.include_router(integrations_router, prefix=PREFIX)
    from app.api.integrations import satellite_router, web3_router, esg_router
    app.include_router(satellite_router, prefix=PREFIX)
    app.include_router(web3_router, prefix=PREFIX)
    app.include_router(esg_router, prefix=PREFIX)
except Exception as e:
    print(f"⚠️ Integration routes not loaded: {e}")

# Legacy fraud/portfolio/market routes
try:
    from app.api.fraud import router as legacy_fraud_router
    app.include_router(legacy_fraud_router, prefix=PREFIX)
except Exception:
    pass

try:
    from app.api.portfolio import router as legacy_portfolio_router
    from app.api.market import router as legacy_market_router
    app.include_router(legacy_portfolio_router, prefix=PREFIX)
    app.include_router(legacy_market_router, prefix=PREFIX)
except Exception:
    pass


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
