"""Portfolio Service v3 — Risk-Adjusted Tonnes & Optimizer.

BeZero-style risk-adjusted tonnes calculation:
- Each rating grade has a discount factor
- Portfolio rating based on composition
- Simulation and rebalancing recommendations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.models.models import (
    Portfolio, PortfolioPosition, CreditBatch, CarbonProject,
    ProjectRating, FraudAlert, RatingGrade, PortfolioRating
)
from app.modules.rating.service import GRADE_DISCOUNT_FACTORS, GRADE_BOUNDARIES


def _get_grade(score: float) -> str:
    for threshold, grade in GRADE_BOUNDARIES:
        if score >= threshold:
            return grade.value
    return "D"


async def calculate_portfolio_metrics(db: AsyncSession, portfolio_id: int) -> dict:
    result = await db.execute(
        select(PortfolioPosition, CreditBatch, CarbonProject, ProjectRating)
        .join(CreditBatch, PortfolioPosition.credit_id == CreditBatch.id)
        .join(CarbonProject, CreditBatch.project_id == CarbonProject.id)
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .where(PortfolioPosition.portfolio_id == portfolio_id)
    )
    rows = result.all()
    if not rows:
        return {
            "total_credits": 0, "total_value_eur": 0, "avg_quality_score": 0,
            "grade_distribution": {}, "risk_exposure": {}, "project_type_distribution": {},
            "country_distribution": {}, "recommendations": [], "positions": [],
            "risk_adjusted_tonnes": 0, "nominal_tonnes": 0, "discount_factor_avg": 1.0,
            "portfolio_grade": "N/A",
        }

    total_credits = total_value = weighted_score = 0
    nominal_tonnes = risk_adjusted = 0.0
    grade_dist, type_dist, country_dist = {}, {}, {}
    risk_exp = {"high": 0, "medium": 0, "low": 0}
    project_agg, position_list = {}, []

    for pos, credit, proj, rat in rows:
        qty = pos.quantity
        total_credits += qty
        price = pos.acquisition_price_eur or credit.price_eur or 0
        total_value += qty * price
        score = rat.overall_score if rat else 50
        grade = rat.grade.value if rat else "N/A"
        discount = rat.discount_factor if rat else 0.5
        risk_flags = rat.risk_flags if rat and rat.risk_flags else []
        weighted_score += score * qty

        # Risk-adjusted tonnes calculation
        nominal_tonnes += qty
        risk_adjusted += qty * discount

        grade_dist[grade] = grade_dist.get(grade, 0) + qty
        pt = proj.project_type.value if hasattr(proj.project_type, 'value') else str(proj.project_type)
        type_dist[pt] = type_dist.get(pt, 0) + qty
        country_dist[proj.country] = country_dist.get(proj.country, 0) + qty

        if score < 40:
            risk_exp["high"] += qty
        elif score < 60:
            risk_exp["medium"] += qty
        else:
            risk_exp["low"] += qty

        pid = proj.id
        if pid not in project_agg:
            project_agg[pid] = {
                "project_id": pid, "project_name": proj.name, "project_type": pt,
                "country": proj.country, "registry": proj.registry,
                "total_quantity": 0, "total_value": 0, "score": score, "grade": grade,
                "discount_factor": discount, "risk_flags": risk_flags, "num_positions": 0,
            }
        project_agg[pid]["total_quantity"] += qty
        project_agg[pid]["total_value"] += qty * price
        project_agg[pid]["num_positions"] += 1

        position_list.append({
            "position_id": pos.id, "project_id": proj.id, "project_name": proj.name,
            "project_type": pt, "country": proj.country, "quantity": qty,
            "score": score, "grade": grade, "price_eur": price,
            "discount_factor": discount,
            "risk_adjusted_qty": round(qty * discount, 2),
        })

    avg_score = weighted_score / total_credits if total_credits > 0 else 0
    discount_avg = risk_adjusted / nominal_tonnes if nominal_tonnes > 0 else 1.0
    portfolio_grade = _get_grade(avg_score)
    recs = _gen_recs(list(project_agg.values()), avg_score, type_dist, country_dist)

    return {
        "total_credits": total_credits,
        "total_value_eur": round(total_value, 2),
        "avg_quality_score": round(avg_score, 2),
        "portfolio_grade": portfolio_grade,
        "grade_distribution": grade_dist,
        "risk_exposure": risk_exp,
        "project_type_distribution": type_dist,
        "country_distribution": country_dist,
        "recommendations": recs,
        "positions": position_list,
        "risk_adjusted_tonnes": round(risk_adjusted, 2),
        "nominal_tonnes": round(nominal_tonnes, 2),
        "discount_factor_avg": round(discount_avg, 4),
    }


def calculate_risk_adjusted_tonnes(
    target_impact: float,
    grade_distribution: dict,
) -> dict:
    """Given a target impact (e.g. 100,000 tCO2e), calculate how many credits
    of each grade to buy to achieve that impact after risk adjustment.

    Args:
        target_impact: desired net climate impact in tCO2e
        grade_distribution: current or desired grade mix as percentages

    Returns:
        dict with breakdown by grade
    """
    result = {}
    remaining = target_impact

    # Sort by discount factor (best ratings first)
    sorted_grades = sorted(
        grade_distribution.items(),
        key=lambda x: GRADE_DISCOUNT_FACTORS.get(x[0], 0.5),
        reverse=True,
    )

    for grade, pct in sorted_grades:
        discount = GRADE_DISCOUNT_FACTORS.get(grade, 0.5)
        allocation = remaining * (pct / 100)
        nominal_needed = allocation / discount if discount > 0 else 0
        result[grade] = {
            "target_impact": round(allocation, 2),
            "discount_factor": discount,
            "nominal_credits_needed": round(nominal_needed, 2),
            "risk_adjusted_impact": round(nominal_needed * discount, 2),
            "over_purchase_factor": round(1 / discount, 2) if discount > 0 else 0,
        }

    total_nominal = sum(v["nominal_credits_needed"] for v in result.values())
    return {
        "target_impact": target_impact,
        "total_nominal_needed": round(total_nominal, 2),
        "over_purchase_ratio": round(total_nominal / target_impact, 2) if target_impact > 0 else 0,
        "grade_breakdown": result,
    }


def _gen_recs(positions, avg_score, type_dist, country_dist):
    recs, priority, seen = [], 1, set()

    for pos in sorted(positions, key=lambda x: x["score"]):
        if pos["score"] < 40 and pos["project_id"] not in seen:
            seen.add(pos["project_id"])
            recs.append({
                "project_id": pos["project_id"], "project_name": pos["project_name"],
                "current_score": pos["score"], "current_grade": pos["grade"],
                "total_quantity": pos.get("total_quantity", 0),
                "action": "sell",
                "reason": f"Score muito baixo ({pos['score']:.0f}/100). Liquidar posição.",
                "reasons": [f"Score crítico: {pos['score']:.0f}/100", "Alto risco de desvalorização",
                           f"Discount factor: {pos.get('discount_factor', 0.5):.0%}"],
                "risk_flags": pos.get("risk_flags", []),
                "risk_level": "high", "priority": priority,
            })
            priority += 1

    for pos in sorted(positions, key=lambda x: x["score"]):
        if 40 <= pos["score"] < 60 and pos["project_id"] not in seen:
            seen.add(pos["project_id"])
            recs.append({
                "project_id": pos["project_id"], "project_name": pos["project_name"],
                "current_score": pos["score"], "current_grade": pos["grade"],
                "total_quantity": pos.get("total_quantity", 0),
                "action": "rebalance",
                "reason": f"Score mediano ({pos['score']:.0f}/100). Considerar substituição por créditos de maior qualidade.",
                "reasons": [f"Score mediano: {pos['score']:.0f}/100"],
                "risk_flags": pos.get("risk_flags", []),
                "risk_level": "medium", "priority": priority,
            })
            priority += 1

    total = sum(type_dist.values())
    if total > 0:
        for pt, qty in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            conc = qty / total
            if conc > 0.30:
                recs.append({
                    "project_id": None, "project_name": f"Concentração: {pt}",
                    "current_score": 0, "current_grade": "N/A",
                    "total_quantity": qty, "action": "rebalance",
                    "reason": f"Concentração de {conc*100:.0f}% em {pt}. Diversificar.",
                    "reasons": [f"Concentração setorial {conc*100:.0f}%"],
                    "risk_flags": [], "risk_level": "medium", "priority": priority,
                })
                priority += 1

    for pos in sorted(positions, key=lambda x: x["score"], reverse=True):
        if pos["score"] >= 60 and pos["project_id"] not in seen:
            seen.add(pos["project_id"])
            recs.append({
                "project_id": pos["project_id"], "project_name": pos["project_name"],
                "current_score": pos["score"], "current_grade": pos["grade"],
                "total_quantity": pos.get("total_quantity", 0),
                "action": "hold",
                "reason": f"Boa qualidade ({pos['score']:.0f}/100). Manter posição.",
                "reasons": [f"Score sólido: {pos['score']:.0f}/100",
                           f"Discount factor: {pos.get('discount_factor', 1.0):.0%}"],
                "risk_flags": pos.get("risk_flags", []),
                "risk_level": "low", "priority": priority,
            })
            priority += 1

    return recs


async def get_dashboard_metrics(db: AsyncSession, organization_id: int) -> dict:
    pc = (await db.execute(select(func.count(CarbonProject.id)))).scalar() or 0
    cc = (await db.execute(select(func.sum(CreditBatch.quantity)))).scalar() or 0
    avg = (await db.execute(select(func.avg(ProjectRating.overall_score)))).scalar() or 0
    gd = {
        (r[0].value if hasattr(r[0], 'value') else str(r[0])): r[1]
        for r in (await db.execute(
            select(ProjectRating.grade, func.count(ProjectRating.id))
            .group_by(ProjectRating.grade)
        )).all()
    }
    ac = (await db.execute(select(func.count(FraudAlert.id)))).scalar() or 0
    abs_ = {
        (r[0].value if hasattr(r[0], 'value') else str(r[0])): r[1]
        for r in (await db.execute(
            select(FraudAlert.severity, func.count(FraudAlert.id))
            .group_by(FraudAlert.severity)
        )).all()
    }
    td = {
        (r[0].value if hasattr(r[0], 'value') else str(r[0])): r[1]
        for r in (await db.execute(
            select(CarbonProject.project_type, func.count(CarbonProject.id))
            .group_by(CarbonProject.project_type)
        )).all()
    }
    cd = {
        r[0]: r[1]
        for r in (await db.execute(
            select(CarbonProject.country, func.count(CarbonProject.id))
            .group_by(CarbonProject.country)
            .order_by(func.count(CarbonProject.id).desc())
            .limit(10)
        )).all()
    }
    pv = (await db.execute(
        select(func.sum(PortfolioPosition.quantity * PortfolioPosition.acquisition_price_eur))
    )).scalar() or 0
    ppc = (await db.execute(
        select(func.count(func.distinct(CreditBatch.project_id)))
        .select_from(PortfolioPosition)
        .join(CreditBatch, PortfolioPosition.credit_id == CreditBatch.id)
    )).scalar() or 0
    avp = round(float(pv) / ppc, 2) if ppc > 0 else 0

    rr = (await db.execute(select(
        func.sum(case((ProjectRating.overall_score < 40, 1), else_=0)),
        func.sum(case((ProjectRating.overall_score.between(40, 60), 1), else_=0)),
        func.sum(case((ProjectRating.overall_score > 60, 1), else_=0)),
    ))).one()

    # Calculate risk-adjusted tonnes for portfolio
    rat_result = await db.execute(
        select(
            func.sum(PortfolioPosition.quantity).label("nominal"),
            func.sum(PortfolioPosition.quantity * ProjectRating.discount_factor).label("adjusted"),
        )
        .select_from(PortfolioPosition)
        .join(CreditBatch, PortfolioPosition.credit_id == CreditBatch.id)
        .join(CarbonProject, CreditBatch.project_id == CarbonProject.id)
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
    )
    rat_row = rat_result.one()
    risk_adjusted = round(float(rat_row[1] or 0), 2)

    return {
        "total_projects": pc, "total_credits": cc,
        "avg_quality_score": round(float(avg), 2),
        "grade_distribution": gd,
        "risk_summary": {"high_risk": rr[0] or 0, "medium_risk": rr[1] or 0, "low_risk": rr[2] or 0},
        "fraud_alerts_count": ac, "fraud_alerts_by_severity": abs_,
        "project_type_distribution": td, "country_distribution": cd,
        "portfolio_value_eur": round(float(pv), 2),
        "portfolio_projects_count": ppc, "avg_value_per_project": avp,
        "risk_adjusted_tonnes": risk_adjusted,
    }
