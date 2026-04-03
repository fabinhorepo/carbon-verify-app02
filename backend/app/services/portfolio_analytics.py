"""Serviço de Analytics de Portfólio - Carbon Verify Produção."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.models.models import (Portfolio, PortfolioPosition, CarbonCredit, CarbonProject, ProjectRating, FraudAlert, RatingGrade)


async def calculate_portfolio_metrics(db: AsyncSession, portfolio_id: int) -> dict:
    result = await db.execute(
        select(PortfolioPosition, CarbonCredit, CarbonProject, ProjectRating)
        .join(CarbonCredit, PortfolioPosition.credit_id == CarbonCredit.id)
        .join(CarbonProject, CarbonCredit.project_id == CarbonProject.id)
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .where(PortfolioPosition.portfolio_id == portfolio_id)
    )
    rows = result.all()
    if not rows:
        return {"total_credits": 0, "total_value_eur": 0, "avg_quality_score": 0, "grade_distribution": {},
                "risk_exposure": {}, "project_type_distribution": {}, "country_distribution": {},
                "recommendations": [], "positions": []}

    total_credits = total_value = weighted_score = 0
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
        risk_flags = rat.risk_flags if rat and rat.risk_flags else []
        weighted_score += score * qty
        grade_dist[grade] = grade_dist.get(grade, 0) + qty
        pt = proj.project_type.value if hasattr(proj.project_type, 'value') else str(proj.project_type)
        type_dist[pt] = type_dist.get(pt, 0) + qty
        country_dist[proj.country] = country_dist.get(proj.country, 0) + qty
        if score < 40: risk_exp["high"] += qty
        elif score < 60: risk_exp["medium"] += qty
        else: risk_exp["low"] += qty

        pid = proj.id
        if pid not in project_agg:
            project_agg[pid] = {"project_id": pid, "project_name": proj.name, "project_type": pt, "country": proj.country,
                                "registry": proj.registry, "total_quantity": 0, "total_value": 0, "score": score, "grade": grade,
                                "risk_flags": risk_flags, "num_positions": 0}
        project_agg[pid]["total_quantity"] += qty
        project_agg[pid]["total_value"] += qty * price
        project_agg[pid]["num_positions"] += 1
        position_list.append({"position_id": pos.id, "project_id": proj.id, "project_name": proj.name, "project_type": pt,
                              "country": proj.country, "quantity": qty, "score": score, "grade": grade, "price_eur": price})

    avg_score = weighted_score / total_credits if total_credits > 0 else 0
    recs = _gen_recs(list(project_agg.values()), avg_score, type_dist, country_dist)
    return {"total_credits": total_credits, "total_value_eur": round(total_value, 2), "avg_quality_score": round(avg_score, 2),
            "grade_distribution": grade_dist, "risk_exposure": risk_exp, "project_type_distribution": type_dist,
            "country_distribution": country_dist, "recommendations": recs, "positions": position_list}


def _gen_recs(positions, avg_score, type_dist, country_dist):
    recs, priority, seen = [], 1, set()
    for pos in sorted(positions, key=lambda x: x["score"]):
        if pos["score"] < 40 and pos["project_id"] not in seen:
            seen.add(pos["project_id"])
            recs.append({"project_id": pos["project_id"], "project_name": pos["project_name"], "current_score": pos["score"],
                         "current_grade": pos["grade"], "total_quantity": pos.get("total_quantity", 0),
                         "action": "sell", "reason": f"Score muito baixo ({pos['score']:.0f}/100). Liquidar posição.",
                         "reasons": [f"Score crítico: {pos['score']:.0f}/100", "Alto risco de desvalorização"],
                         "risk_flags": pos.get("risk_flags", []), "risk_level": "high", "priority": priority})
            priority += 1
    for pos in sorted(positions, key=lambda x: x["score"]):
        if 40 <= pos["score"] < 60 and pos["project_id"] not in seen:
            seen.add(pos["project_id"])
            recs.append({"project_id": pos["project_id"], "project_name": pos["project_name"], "current_score": pos["score"],
                         "current_grade": pos["grade"], "total_quantity": pos.get("total_quantity", 0),
                         "action": "rebalance", "reason": f"Score mediano ({pos['score']:.0f}/100). Reduzir exposição.",
                         "reasons": [f"Score mediano: {pos['score']:.0f}/100"], "risk_flags": pos.get("risk_flags", []),
                         "risk_level": "medium", "priority": priority})
            priority += 1
    total = sum(type_dist.values())
    if total > 0:
        for pt, qty in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
            conc = qty / total
            if conc > 0.30:
                recs.append({"project_id": None, "project_name": f"Concentração: {pt}", "current_score": 0, "current_grade": "N/A",
                             "total_quantity": qty, "action": "rebalance", "reason": f"Concentração de {conc*100:.0f}% em {pt}.",
                             "reasons": [f"Concentração setorial {conc*100:.0f}%"], "risk_flags": [], "risk_level": "medium", "priority": priority})
                priority += 1
    for pos in sorted(positions, key=lambda x: x["score"], reverse=True):
        if pos["score"] >= 60 and pos["project_id"] not in seen:
            seen.add(pos["project_id"])
            recs.append({"project_id": pos["project_id"], "project_name": pos["project_name"], "current_score": pos["score"],
                         "current_grade": pos["grade"], "total_quantity": pos.get("total_quantity", 0),
                         "action": "hold", "reason": f"Boa qualidade ({pos['score']:.0f}/100). Manter.",
                         "reasons": [f"Score sólido: {pos['score']:.0f}/100"], "risk_flags": pos.get("risk_flags", []),
                         "risk_level": "low", "priority": priority})
            priority += 1
    return recs


def group_recommendations_by_action(recs, page=1, page_size=20):
    groups = {}
    for r in recs:
        a = r.get("action", "hold")
        groups.setdefault(a, []).append(r)
    result = {}
    for action, items in groups.items():
        items.sort(key=lambda x: x.get("priority", 999))
        total = len(items)
        tp = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size
        result[action] = {"items": items[offset:offset + page_size], "total": total, "page": page, "page_size": page_size, "total_pages": tp}
    return result


async def get_dashboard_metrics(db: AsyncSession, organization_id: int) -> dict:
    pc = (await db.execute(select(func.count(CarbonProject.id)))).scalar() or 0
    cc = (await db.execute(select(func.sum(CarbonCredit.quantity)))).scalar() or 0
    avg = (await db.execute(select(func.avg(ProjectRating.overall_score)))).scalar() or 0
    gd = {(r[0].value if hasattr(r[0], 'value') else str(r[0])): r[1] for r in (await db.execute(select(ProjectRating.grade, func.count(ProjectRating.id)).group_by(ProjectRating.grade))).all()}
    ac = (await db.execute(select(func.count(FraudAlert.id)))).scalar() or 0
    abs_ = {(r[0].value if hasattr(r[0], 'value') else str(r[0])): r[1] for r in (await db.execute(select(FraudAlert.severity, func.count(FraudAlert.id)).group_by(FraudAlert.severity))).all()}
    td = {(r[0].value if hasattr(r[0], 'value') else str(r[0])): r[1] for r in (await db.execute(select(CarbonProject.project_type, func.count(CarbonProject.id)).group_by(CarbonProject.project_type))).all()}
    cd = {r[0]: r[1] for r in (await db.execute(select(CarbonProject.country, func.count(CarbonProject.id)).group_by(CarbonProject.country).order_by(func.count(CarbonProject.id).desc()).limit(10))).all()}
    pv = (await db.execute(select(func.sum(PortfolioPosition.quantity * PortfolioPosition.acquisition_price_eur)))).scalar() or 0
    ppc = (await db.execute(select(func.count(func.distinct(CarbonCredit.project_id))).select_from(PortfolioPosition).join(CarbonCredit, PortfolioPosition.credit_id == CarbonCredit.id))).scalar() or 0
    avp = round(float(pv) / ppc, 2) if ppc > 0 else 0
    rr = (await db.execute(select(func.sum(case((ProjectRating.overall_score < 40, 1), else_=0)), func.sum(case((ProjectRating.overall_score.between(40, 60), 1), else_=0)), func.sum(case((ProjectRating.overall_score > 60, 1), else_=0))))).one()
    return {"total_projects": pc, "total_credits": cc, "avg_quality_score": round(float(avg), 2), "grade_distribution": gd,
            "risk_summary": {"high_risk": rr[0] or 0, "medium_risk": rr[1] or 0, "low_risk": rr[2] or 0},
            "fraud_alerts_count": ac, "fraud_alerts_by_severity": abs_, "project_type_distribution": td, "country_distribution": cd,
            "portfolio_value_eur": round(float(pv), 2), "portfolio_projects_count": ppc, "avg_value_per_project": avp}
