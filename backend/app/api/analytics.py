"""Endpoints de Analytics Avançado."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    CarbonProject, ProjectRating, FraudAlert, MetricSnapshot,
    CarbonPriceHistory, PortfolioPosition, CarbonCredit, User
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/trends")
async def get_trends(
    metric: str = Query("score", description="score, alerts, portfolio_value, price"),
    period: str = Query("6m", description="1m, 3m, 6m, 12m"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna tendências temporais de uma métrica."""
    from datetime import datetime, timezone, timedelta
    delta_map = {"1m": 30, "3m": 90, "6m": 180, "12m": 365}
    days = delta_map.get(period, 180)
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.metric_name == metric, MetricSnapshot.recorded_at >= since)
        .order_by(MetricSnapshot.recorded_at.asc())
    )
    snapshots = result.scalars().all()
    return {
        "metric": metric,
        "period": period,
        "data": [{"value": s.value, "date": s.recorded_at.isoformat(), "metadata": s.metadata_json} for s in snapshots],
    }


@router.get("/correlations")
async def get_correlations(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retorna dados de correlação entre score e outros fatores."""
    result = await db.execute(
        select(
            CarbonProject.project_type, CarbonProject.country,
            ProjectRating.overall_score, CarbonProject.total_credits_issued,
            func.count(FraudAlert.id).label("fraud_count"),
        )
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .outerjoin(FraudAlert, CarbonProject.id == FraudAlert.project_id)
        .group_by(CarbonProject.id, CarbonProject.project_type, CarbonProject.country,
                  ProjectRating.overall_score, CarbonProject.total_credits_issued)
    )
    data = [
        {
            "project_type": r[0].value if hasattr(r[0], 'value') else str(r[0]),
            "country": r[1], "score": r[2] or 0, "credits": r[3] or 0, "fraud_count": r[4],
        }
        for r in result.all()
    ]

    # Heatmap: tipo × tipo de fraude
    heatmap_result = await db.execute(
        select(CarbonProject.project_type, FraudAlert.alert_type, func.count(FraudAlert.id))
        .join(FraudAlert, CarbonProject.id == FraudAlert.project_id)
        .group_by(CarbonProject.project_type, FraudAlert.alert_type)
    )
    heatmap = {}
    for r in heatmap_result.all():
        pt = r[0].value if hasattr(r[0], 'value') else str(r[0])
        at = r[1]
        if pt not in heatmap:
            heatmap[pt] = {}
        heatmap[pt][at] = r[2]

    return {"scatter_data": data, "heatmap": heatmap}


@router.get("/performance-kpis")
async def get_performance_kpis(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retorna KPIs de performance."""
    from app.models.models import AlertStatus
    total_alerts = (await db.execute(select(func.count(FraudAlert.id)))).scalar() or 0
    resolved = (await db.execute(
        select(func.count(FraudAlert.id)).where(FraudAlert.status.in_([AlertStatus.CONFIRMED, AlertStatus.DISMISSED]))
    )).scalar() or 0
    avg_score = (await db.execute(select(func.avg(ProjectRating.overall_score)))).scalar() or 0
    total_value = (await db.execute(
        select(func.sum(PortfolioPosition.quantity * PortfolioPosition.acquisition_price_eur))
    )).scalar() or 0

    return {
        "alert_resolution_rate": round((resolved / max(total_alerts, 1)) * 100, 1),
        "total_alerts": total_alerts,
        "resolved_alerts": resolved,
        "avg_portfolio_score": round(float(avg_score), 1),
        "total_portfolio_value_eur": round(float(total_value), 2),
    }
