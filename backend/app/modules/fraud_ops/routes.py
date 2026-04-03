"""API Routes: Fraud Ops — Carbon Verify v3."""
import math
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import FraudAlert, CarbonProject, User, Entity, EntityRelation
from app.models.schemas import FraudAlertResponse, FraudAlertUpdate
from app.modules.fraud_ops.service import FRAUD_TYPE_EXPLANATIONS, calculate_fraud_ops_score

router = APIRouter(prefix="/fraud-ops", tags=["Fraud Ops"])
PAGE_SIZE = 20


def _alert_to_dict(alert, project_name: str) -> dict:
    data = FraudAlertResponse.model_validate(alert).model_dump()
    data["project_name"] = project_name
    return data


@router.get("/alerts")
async def list_fraud_alerts(
    page: int = Query(1, ge=1), page_size: int = Query(PAGE_SIZE, ge=1, le=100),
    severity: Optional[str] = None, status: Optional[str] = None,
    project_id: Optional[int] = None, alert_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    base = select(FraudAlert, CarbonProject.name.label("pn")).join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
    count_base = select(FraudAlert.id)
    if severity:
        base = base.where(FraudAlert.severity == severity)
        count_base = count_base.where(FraudAlert.severity == severity)
    if status:
        base = base.where(FraudAlert.status == status)
        count_base = count_base.where(FraudAlert.status == status)
    if project_id:
        base = base.where(FraudAlert.project_id == project_id)
        count_base = count_base.where(FraudAlert.project_id == project_id)
    if alert_type:
        base = base.where(FraudAlert.alert_type == alert_type)
        count_base = count_base.where(FraudAlert.alert_type == alert_type)

    total = (await db.execute(select(func.count()).select_from(count_base.subquery()))).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    rows = (await db.execute(base.order_by(FraudAlert.created_at.desc()).offset(offset).limit(page_size))).all()
    items = [_alert_to_dict(r[0], r[1]) for r in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


@router.get("/alerts/grouped")
async def fraud_alerts_grouped(page_size: int = Query(10, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    type_result = await db.execute(
        select(FraudAlert.alert_type, func.count(FraudAlert.id))
        .group_by(FraudAlert.alert_type)
        .order_by(func.count(FraudAlert.id).desc())
    )
    type_counts = {r[0]: r[1] for r in type_result.all()}
    grouped = {}
    for at, tc in type_counts.items():
        tp = math.ceil(tc / page_size) if tc > 0 else 1
        rows = (await db.execute(
            select(FraudAlert, CarbonProject.name.label("pn"))
            .join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
            .where(FraudAlert.alert_type == at)
            .order_by(FraudAlert.severity.desc(), FraudAlert.created_at.desc())
            .limit(page_size)
        )).all()
        explanation = FRAUD_TYPE_EXPLANATIONS.get(at, {
            "title": at.replace("_", " ").title(), "what_is": "N/A",
            "consequences": "N/A", "ideal_situation": "N/A",
            "icon": "alert-circle", "severity_typical": "medium",
        })
        grouped[at] = {
            "items": [_alert_to_dict(r[0], r[1]) for r in rows],
            "total": tc, "page": 1, "page_size": page_size, "total_pages": tp,
            "explanation": explanation,
        }
    return {"types": grouped, "total_types": len(type_counts), "total_alerts": sum(type_counts.values())}


@router.get("/summary")
async def fraud_summary(db: AsyncSession = Depends(get_db)):
    sev = {r[0].value if hasattr(r[0], 'value') else str(r[0]): r[1]
           for r in (await db.execute(select(FraudAlert.severity, func.count(FraudAlert.id)).group_by(FraudAlert.severity))).all()}
    sts = {r[0].value if hasattr(r[0], 'value') else str(r[0]): r[1]
           for r in (await db.execute(select(FraudAlert.status, func.count(FraudAlert.id)).group_by(FraudAlert.status))).all()}
    byt = {r[0]: r[1] for r in (await db.execute(select(FraudAlert.alert_type, func.count(FraudAlert.id)).group_by(FraudAlert.alert_type))).all()}
    top = (await db.execute(
        select(FraudAlert.project_id, CarbonProject.name, func.count(FraudAlert.id).label("c"))
        .join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
        .group_by(FraudAlert.project_id, CarbonProject.name)
        .order_by(func.count(FraudAlert.id).desc()).limit(5)
    )).all()
    return {
        "total_alerts": sum(sev.values()), "by_severity": sev, "by_status": sts, "by_type": byt,
        "top_affected_projects": [{"project_id": r[0], "project_name": r[1], "alert_count": r[2]} for r in top],
    }


@router.get("/score/{project_id}")
async def get_fraud_ops_score(project_id: int, db: AsyncSession = Depends(get_db)):
    alerts = (await db.execute(select(FraudAlert).where(FraudAlert.project_id == project_id))).scalars().all()
    score = calculate_fraud_ops_score(alerts)
    return {
        "project_id": project_id,
        "fraud_ops_score": score,
        "risk_level": "critical" if score >= 60 else "high" if score >= 40 else "medium" if score >= 20 else "low",
        "total_alerts": len(alerts),
        "alerts_by_severity": {},
    }


@router.get("/graph/{entity_id}")
async def get_entity_graph(entity_id: int, db: AsyncSession = Depends(get_db)):
    entity = (await db.execute(select(Entity).where(Entity.id == entity_id))).scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=404, detail="Entidade não encontrada")
    relations = (await db.execute(
        select(EntityRelation)
        .where((EntityRelation.source_entity_id == entity_id) | (EntityRelation.target_entity_id == entity_id))
    )).scalars().all()
    related_ids = set()
    for r in relations:
        related_ids.add(r.source_entity_id)
        related_ids.add(r.target_entity_id)
    related_ids.discard(entity_id)
    related_entities = (await db.execute(select(Entity).where(Entity.id.in_(related_ids)))).scalars().all() if related_ids else []
    return {
        "center": {"id": entity.id, "name": entity.name, "entity_type": entity.entity_type.value, "risk_score": entity.risk_score},
        "related": [{"id": e.id, "name": e.name, "entity_type": e.entity_type.value, "risk_score": e.risk_score} for e in related_entities],
        "relations": [{"source": r.source_entity_id, "target": r.target_entity_id, "type": r.relation_type} for r in relations],
    }


@router.patch("/alerts/{alert_id}")
async def update_fraud_alert(alert_id: int, data: FraudAlertUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(FraudAlert).where(FraudAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    if data.status:
        alert.status = data.status
    if data.review_notes:
        alert.review_notes = data.review_notes
    if data.reviewed_by:
        alert.reviewed_by = data.reviewed_by
    alert.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    pn = (await db.execute(select(CarbonProject.name).where(CarbonProject.id == alert.project_id))).scalar() or "N/A"
    return _alert_to_dict(alert, pn)
