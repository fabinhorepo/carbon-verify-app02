"""API Routes: Portfolio, Dashboard, Compliance, Market Intel, Workspace — Carbon Verify v3."""
import math
import random
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    Portfolio, PortfolioPosition, CreditBatch, CarbonProject, ProjectRating,
    User, Workspace, WorkspaceMembership, ComplianceFramework, ComplianceMapping,
    ApprovalFlow, ApprovalStep, CarbonPriceHistory, MarketPrice,
)
from app.models.schemas import PortfolioCreate, PositionCreate
from app.modules.portfolio.service import (
    calculate_portfolio_metrics, get_dashboard_metrics,
    calculate_risk_adjusted_tonnes,
)
from app.modules.compliance.service import (
    get_compliance_summary, map_project_to_csrd, map_project_to_sbti, map_project_to_icvcm,
)
from app.modules.market_intel.service import calculate_frontier, suggest_rebalance
from app.modules.workspace.service import (
    get_profile_config, get_all_profiles, check_permission, get_visible_modules,
)

# ═══════════════════════════════════════════════════════════════════════════
# PORTFOLIO ROUTES
# ═══════════════════════════════════════════════════════════════════════════

portfolio_router = APIRouter(prefix="/portfolios", tags=["Portfólio"])


@portfolio_router.get("")
async def list_portfolios(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Portfolio))
    portfolios = result.scalars().all()
    return [
        {"id": p.id, "name": p.name, "organization_id": p.organization_id,
         "description": p.description, "total_credits": p.total_credits,
         "total_value_eur": p.total_value_eur, "avg_quality_score": p.avg_quality_score,
         "created_at": p.created_at}
        for p in portfolios
    ]


@portfolio_router.post("", status_code=201)
async def create_portfolio(data: PortfolioCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    portfolio = Portfolio(name=data.name, description=data.description, organization_id=user.organization_id)
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return {"id": portfolio.id, "name": portfolio.name, "message": "Portfólio criado"}


@portfolio_router.get("/{portfolio_id}/metrics")
async def get_portfolio_metrics(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    return await calculate_portfolio_metrics(db, portfolio_id)


@portfolio_router.get("/{portfolio_id}/risk-adjusted")
async def get_risk_adjusted_tonnes(
    portfolio_id: int,
    target_impact: float = Query(100000, description="Target climate impact in tCO2e"),
    db: AsyncSession = Depends(get_db),
):
    metrics = await calculate_portfolio_metrics(db, portfolio_id)
    grade_dist = metrics.get("grade_distribution", {})

    total = sum(grade_dist.values())
    if total == 0:
        return {"message": "Portfólio vazio", "data": {}}

    grade_pcts = {g: (q / total * 100) for g, q in grade_dist.items()}
    result = calculate_risk_adjusted_tonnes(target_impact, grade_pcts)
    result["current_portfolio"] = {
        "nominal_tonnes": metrics.get("nominal_tonnes", 0),
        "risk_adjusted_tonnes": metrics.get("risk_adjusted_tonnes", 0),
        "discount_factor_avg": metrics.get("discount_factor_avg", 1.0),
        "portfolio_grade": metrics.get("portfolio_grade", "N/A"),
    }
    return result


@portfolio_router.post("/{portfolio_id}/positions", status_code=201)
async def add_position(portfolio_id: int, data: PositionCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    portfolio = (await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))).scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfólio não encontrado")
    position = PortfolioPosition(
        portfolio_id=portfolio_id, credit_id=data.credit_id,
        quantity=data.quantity, acquisition_price_eur=data.acquisition_price_eur,
        acquisition_date=data.acquisition_date,
    )
    db.add(position)
    await db.commit()
    return {"message": "Posição adicionada", "position_id": position.id}


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD ROUTES
# ═══════════════════════════════════════════════════════════════════════════

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard_router.get("/metrics")
async def dashboard_metrics(db: AsyncSession = Depends(get_db)):
    return await get_dashboard_metrics(db, 1)


@dashboard_router.get("/risk-matrix")
async def risk_matrix(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CarbonProject.id, ProjectRating.overall_score, func.count(FraudAlert.id))
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .outerjoin(FraudAlert, CarbonProject.id == FraudAlert.project_id)
        .group_by(CarbonProject.id, ProjectRating.overall_score)
    )
    from app.models.models import FraudAlert
    grid = {"high": {}, "medium": {}, "low": {}}
    for quality in ["high", "medium", "low"]:
        for risk in ["none", "low", "medium", "high"]:
            grid[quality][risk] = {"count": 0, "projects": []}
    for r in result.all():
        score = r[1] or 50
        alerts = r[2] or 0
        quality = "high" if score >= 60 else "medium" if score >= 40 else "low"
        risk = "high" if alerts >= 3 else "medium" if alerts >= 1 else "none"
        grid[quality][risk]["count"] += 1
    return {"grid": grid}


# ═══════════════════════════════════════════════════════════════════════════
# COMPLIANCE ROUTES
# ═══════════════════════════════════════════════════════════════════════════

compliance_router = APIRouter(prefix="/compliance", tags=["Compliance"])


@compliance_router.get("/frameworks")
async def list_frameworks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ComplianceFramework))
    frameworks = result.scalars().all()
    return [
        {"id": f.id, "code": f.code, "name": f.name,
         "framework_type": f.framework_type.value if hasattr(f.framework_type, 'value') else str(f.framework_type),
         "version": f.version, "is_active": f.is_active}
        for f in frameworks
    ]


@compliance_router.get("/mapping/{project_id}")
async def get_project_compliance(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CarbonProject).options(selectinload(CarbonProject.rating))
        .where(CarbonProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project_data = {
        "name": project.name,
        "project_type": project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type),
        "methodology": project.methodology,
        "registry": project.registry,
        "country": project.country,
        "total_credits_issued": project.total_credits_issued,
        "vintage_year": project.vintage_year,
        "external_id": project.external_id,
        "description": project.description,
    }
    rating_data = {}
    if project.rating:
        r = project.rating
        rating_data = {
            "grade": r.grade.value if hasattr(r.grade, 'value') else str(r.grade),
            "overall_score": r.overall_score,
            "carbon_integrity_score": r.carbon_integrity_score,
            "additionality_score": r.additionality_score,
            "permanence_score": r.permanence_score,
            "leakage_score": r.leakage_score,
            "co_benefits_score": r.co_benefits_score,
            "governance_score": r.governance_score,
            "discount_factor": r.discount_factor,
            "risk_flags": r.risk_flags or [],
        }

    return get_compliance_summary(project_data, rating_data)


@compliance_router.get("/portfolio/{portfolio_id}")
async def get_portfolio_compliance(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CarbonProject, ProjectRating)
        .join(CreditBatch, CarbonProject.id == CreditBatch.project_id)
        .join(PortfolioPosition, CreditBatch.id == PortfolioPosition.credit_id)
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .where(PortfolioPosition.portfolio_id == portfolio_id)
        .distinct()
    )
    rows = result.all()
    summary = {"csrd_esrs": {"items": [], "avg_coverage": 0}, "sbti": {"items": []}, "icvcm": {"items": []}}
    for proj, rat in rows:
        pd = {"name": proj.name, "project_type": proj.project_type.value if hasattr(proj.project_type, 'value') else str(proj.project_type),
              "registry": proj.registry, "methodology": proj.methodology, "total_credits_issued": proj.total_credits_issued,
              "vintage_year": proj.vintage_year, "external_id": proj.external_id, "description": proj.description}
        rd = {"grade": rat.grade.value if rat and hasattr(rat.grade, 'value') else "N/A",
              "discount_factor": rat.discount_factor if rat else 0.5, "risk_flags": rat.risk_flags if rat else []} if rat else {}
        cs = get_compliance_summary(pd, rd)
        for f in ["csrd_esrs", "sbti", "icvcm"]:
            summary[f]["items"].extend(cs[f]["items"])
    return summary


# ═══════════════════════════════════════════════════════════════════════════
# MARKET INTELLIGENCE ROUTES
# ═══════════════════════════════════════════════════════════════════════════

market_router = APIRouter(prefix="/market", tags=["Market Intelligence"])


@market_router.get("/carbon-price")
async def get_carbon_price(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarbonPriceHistory).order_by(CarbonPriceHistory.recorded_at.desc()).limit(1))
    price = result.scalar_one_or_none()
    if not price:
        rng = random.Random(42)
        base = round(rng.uniform(62, 78), 2)
        change = round(rng.uniform(-3, 3), 2)
        return {"price_eur": base, "previous_close_eur": base - change, "change_24h": change,
                "change_pct_24h": round(change / base * 100, 2), "day_high_eur": base + 1.5,
                "day_low_eur": base - 2.0, "market": "EU ETS", "source": "simulated"}
    return {"price_eur": price.price_eur, "previous_close_eur": price.previous_close_eur,
            "change_24h": price.change_24h, "change_pct_24h": price.change_pct_24h,
            "day_high_eur": price.day_high_eur, "day_low_eur": price.day_low_eur,
            "market": price.market, "source": price.source}


@market_router.get("/frontier")
async def get_price_quality_frontier(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CarbonProject.id, CarbonProject.name, CarbonProject.project_type,
               ProjectRating.grade, ProjectRating.overall_score, ProjectRating.discount_factor)
        .join(ProjectRating, CarbonProject.id == ProjectRating.project_id)
    )
    rng = random.Random(99)
    credits = []
    for r in result.all():
        grade = r[3].value if hasattr(r[3], 'value') else str(r[3])
        pt = r[2].value if hasattr(r[2], 'value') else str(r[2])
        base_price = {"AAA": 25, "AA": 20, "A": 16, "BBB": 12, "BB": 8, "B": 5, "CCC": 3, "CC": 2, "C": 1, "D": 0.5}
        price = round(base_price.get(grade, 5) * rng.uniform(0.6, 1.5), 2)
        credits.append({
            "project_id": r[0], "project_name": r[1], "project_type": pt,
            "grade": grade, "price_eur": price, "rating_score": r[4],
            "liquidity_score": round(rng.uniform(0.3, 1.0), 2),
        })
    return calculate_frontier(credits)


@market_router.get("/opportunities")
async def get_opportunities(db: AsyncSession = Depends(get_db)):
    frontier = await get_price_quality_frontier(db)
    return {"opportunities": frontier.get("opportunities", []), "stats": frontier.get("stats", {})}


@market_router.post("/rebalance")
async def suggest_portfolio_rebalance(portfolio_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    from app.modules.portfolio.service import calculate_portfolio_metrics
    metrics = await calculate_portfolio_metrics(db, portfolio_id)
    positions = metrics.get("positions", [])
    frontier = await get_price_quality_frontier(db)
    opportunities = frontier.get("opportunities", [])
    suggestions = suggest_rebalance(positions, opportunities)
    return {"suggestions": suggestions, "current_portfolio_grade": metrics.get("portfolio_grade", "N/A")}


# ═══════════════════════════════════════════════════════════════════════════
# WORKSPACE ROUTES
# ═══════════════════════════════════════════════════════════════════════════

workspace_router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@workspace_router.get("")
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace))
    workspaces = result.scalars().all()
    return [
        {"id": w.id, "name": w.name, "organization_id": w.organization_id,
         "profile_type": w.profile_type.value if hasattr(w.profile_type, 'value') else str(w.profile_type),
         "visible_modules": w.visible_modules, "is_default": w.is_default}
        for w in workspaces
    ]


@workspace_router.get("/profiles")
async def list_profiles():
    return get_all_profiles()


@workspace_router.get("/{workspace_id}/config")
async def get_workspace_config(workspace_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")
    profile_type = ws.profile_type.value if hasattr(ws.profile_type, 'value') else str(ws.profile_type)
    config = get_profile_config(profile_type)
    return {
        "workspace": {"id": ws.id, "name": ws.name, "profile_type": profile_type},
        "config": config,
    }


@workspace_router.post("", status_code=201)
async def create_workspace(name: str = Query(...), profile_type: str = Query("sustainability"),
                           db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    ws = Workspace(name=name, organization_id=user.organization_id, profile_type=profile_type)
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return {"id": ws.id, "name": ws.name, "message": "Workspace criado"}


@workspace_router.get("/{workspace_id}/approvals")
async def list_approval_flows(workspace_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ApprovalFlow).options(selectinload(ApprovalFlow.steps))
        .where(ApprovalFlow.workspace_id == workspace_id)
    )
    flows = result.scalars().all()
    return [
        {"id": f.id, "name": f.name, "flow_type": f.flow_type,
         "required_steps": f.required_steps, "is_active": f.is_active,
         "steps": [{"id": s.id, "step_order": s.step_order, "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
                    "user_id": s.user_id, "decided_at": s.decided_at} for s in (f.steps or [])]}
        for f in flows
    ]
