"""Endpoints de Market Data e Histórico de Preços."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.models import CarbonPriceHistory
from app.services.carbon_price import get_carbon_price, get_market_summary

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/carbon-price")
async def carbon_price():
    return await get_carbon_price()


@router.get("/summary")
async def market_summary():
    return get_market_summary()


@router.get("/price-history")
async def price_history(
    period: str = Query("24h", description="24h, 7d, 30d"),
    db: AsyncSession = Depends(get_db),
):
    """Retorna histórico de preços armazenados."""
    from datetime import datetime, timezone, timedelta
    now = datetime.utcnow()
    delta_map = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
    delta = delta_map.get(period, timedelta(hours=24))
    since = now - delta

    result = await db.execute(
        select(CarbonPriceHistory)
        .where(CarbonPriceHistory.recorded_at >= since)
        .order_by(CarbonPriceHistory.recorded_at.asc())
    )
    records = result.scalars().all()
    return {
        "period": period,
        "count": len(records),
        "data": [
            {
                "price_eur": r.price_eur,
                "change_pct_24h": r.change_pct_24h,
                "day_high_eur": r.day_high_eur,
                "day_low_eur": r.day_low_eur,
                "source": r.source,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in records
        ],
    }


@router.get("/portfolio-impact")
async def portfolio_impact(
    price_change_pct: float = Query(0, description="Variação percentual simulada"),
    db: AsyncSession = Depends(get_db),
):
    """Simula impacto de variação de preço no portfólio."""
    from app.models.models import PortfolioPosition, CarbonCredit
    from sqlalchemy import func

    current_price = await get_carbon_price()
    base_price = current_price.get("price_eur", 68.50)
    simulated_price = base_price * (1 + price_change_pct / 100)

    total_credits_result = await db.execute(select(func.sum(PortfolioPosition.quantity)))
    total_credits = total_credits_result.scalar() or 0

    total_value_result = await db.execute(
        select(func.sum(PortfolioPosition.quantity * PortfolioPosition.acquisition_price_eur))
    )
    current_value = total_value_result.scalar() or 0
    simulated_value = total_credits * simulated_price

    return {
        "current_price_eur": base_price,
        "simulated_price_eur": round(simulated_price, 2),
        "price_change_pct": price_change_pct,
        "total_credits": total_credits,
        "current_portfolio_value": round(current_value, 2),
        "simulated_portfolio_value": round(simulated_value, 2),
        "value_change_eur": round(simulated_value - current_value, 2),
        "value_change_pct": round(((simulated_value - current_value) / max(current_value, 1)) * 100, 2),
    }
