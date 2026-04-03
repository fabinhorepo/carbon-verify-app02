"""Endpoints de Portfólio e Dashboard."""
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    Portfolio, PortfolioPosition, CarbonCredit, CarbonProject,
    User, ProjectRating, FraudAlert
)
from app.models.schemas import PortfolioCreate, PortfolioResponse, PositionCreate, PositionResponse, DashboardMetrics
from app.services.portfolio_analytics import calculate_portfolio_metrics, get_dashboard_metrics, group_recommendations_by_action

router = APIRouter(prefix="/portfolios", tags=["Portfólios"])
PAGE_SIZE = 20


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Portfolio).where(Portfolio.organization_id == current_user.organization_id))
    return [PortfolioResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(data: PortfolioCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    portfolio = Portfolio(name=data.name, description=data.description, organization_id=current_user.organization_id)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioResponse.model_validate(portfolio)


@router.get("/{portfolio_id}")
async def get_portfolio_detail(
    portfolio_id: int, page: int = Query(1, ge=1), page_size: int = Query(PAGE_SIZE, ge=1, le=100),
    rec_page: int = Query(1, ge=1), rec_page_size: int = Query(PAGE_SIZE, ge=1, le=100),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfólio não encontrado")
    if portfolio.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    metrics = await calculate_portfolio_metrics(db, portfolio_id)
    all_pos = metrics.get("positions", [])
    total_pos = len(all_pos)
    tp = math.ceil(total_pos / page_size) if total_pos > 0 else 1
    offset = (page - 1) * page_size
    metrics["positions"] = all_pos[offset:offset + page_size]
    metrics["positions_pagination"] = {"total": total_pos, "page": page, "page_size": page_size, "total_pages": tp}
    recs = metrics.get("recommendations", [])
    metrics["recommendations_grouped"] = group_recommendations_by_action(recs, page=rec_page, page_size=rec_page_size)
    metrics["total_recommendations"] = len(recs)
    return {"portfolio": PortfolioResponse.model_validate(portfolio), "metrics": metrics}


@router.post("/{portfolio_id}/positions", response_model=PositionResponse, status_code=201)
async def add_position(portfolio_id: int, data: PositionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfólio não encontrado")
    if portfolio.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    cr = await db.execute(select(CarbonCredit).where(CarbonCredit.id == data.credit_id))
    if not cr.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Crédito não encontrado")
    position = PortfolioPosition(portfolio_id=portfolio_id, **data.model_dump())
    db.add(position)
    portfolio.total_credits += data.quantity
    if data.acquisition_price_eur:
        portfolio.total_value_eur += data.quantity * data.acquisition_price_eur
    await db.commit()
    await db.refresh(position)
    return PositionResponse.model_validate(position)


# ─── Dashboard ───────────────────────────────────────────────────────────

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard_router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    metrics = await get_dashboard_metrics(db, current_user.organization_id)
    return DashboardMetrics(**metrics)


@dashboard_router.get("/risk-matrix")
async def get_risk_matrix(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(CarbonProject.id, CarbonProject.name, CarbonProject.project_type, CarbonProject.registry,
               ProjectRating.overall_score, ProjectRating.grade, func.count(FraudAlert.id).label("fc"))
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .outerjoin(FraudAlert, CarbonProject.id == FraudAlert.project_id)
        .group_by(CarbonProject.id, CarbonProject.name, CarbonProject.project_type, CarbonProject.registry, ProjectRating.overall_score, ProjectRating.grade)
    )
    projects = [{"project_id": r[0], "name": r[1], "project_type": r[2].value if hasattr(r[2], 'value') else str(r[2]) if r[2] else "N/A",
                 "registry": r[3] or "N/A", "quality_score": r[4] or 0, "grade": r[5].value if hasattr(r[5], 'value') else str(r[5]) if r[5] else "N/A", "fraud_alerts": r[6]} for r in result.all()]

    quality_levels = [{"key": "high", "label": "Alta Qualidade (Score > 60)", "min": 60.01, "max": 100},
                      {"key": "medium", "label": "Qualidade Média (Score 40-60)", "min": 40, "max": 60},
                      {"key": "low", "label": "Baixa Qualidade (Score < 40)", "min": 0, "max": 39.99}]
    risk_levels = [{"key": "none", "label": "Sem Alertas", "min": 0, "max": 0},
                   {"key": "low", "label": "Baixo (1-2)", "min": 1, "max": 2},
                   {"key": "medium", "label": "Médio (3-4)", "min": 3, "max": 4},
                   {"key": "high", "label": "Alto (5+)", "min": 5, "max": 999}]

    def cq(s): return "high" if s > 60 else "medium" if s >= 40 else "low"
    def cr(f): return "none" if f == 0 else "low" if f <= 2 else "medium" if f <= 4 else "high"

    grid = {ql["key"]: {rl["key"]: {"projects": [], "count": 0} for rl in risk_levels} for ql in quality_levels}
    for p in projects:
        cell = grid[cq(p["quality_score"])][cr(p["fraud_alerts"])]
        cell["projects"].append(p)
        cell["count"] += 1
    return {"grid": grid, "quality_levels": quality_levels, "risk_levels": risk_levels, "total_projects": len(projects)}
