"""Endpoints de Fraud Detection."""
import math
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import FraudAlert, CarbonProject, User, AlertStatus
from app.models.schemas import FraudAlertResponse, FraudAlertUpdate

router = APIRouter(prefix="/fraud-alerts", tags=["Fraud Detection"])
PAGE_SIZE = 20

FRAUD_TYPE_EXPLANATIONS = {
    "overcrediting": {
        "title": "Overcrediting (Créditos em Excesso)",
        "what_is": "Overcrediting ocorre quando um projeto de carbono emite mais créditos do que a quantidade real de carbono que foi efetivamente removida ou evitada. Em termos simples, é como se o projeto \"inflasse\" seus números, declarando ter compensado mais emissões do que realmente compensou.",
        "consequences": "Quando créditos em excesso são vendidos no mercado, compradores acreditam estar compensando suas emissões, mas na realidade a compensação não aconteceu integralmente. Isso mina a credibilidade do mercado de carbono e contribui para o greenwashing corporativo.",
        "ideal_situation": "O ideal é que o projeto utilize metodologias conservadoras de cálculo, com verificação independente por terceiros credenciados. A quantidade de créditos emitidos deve ser igual ou inferior à quantidade real de carbono sequestrado/evitado.",
        "icon": "alert-triangle", "severity_typical": "high",
    },
    "vintage_age": {
        "title": "Vintage Antigo (Créditos Envelhecidos)",
        "what_is": "Vintage age refere-se a créditos de carbono que foram gerados há muitos anos (tipicamente mais de 5 anos) e ainda não foram aposentados. Créditos muito antigos podem não refletir as condições atuais do projeto.",
        "consequences": "Créditos antigos podem representar reduções de emissões que já não são adicionais. O projeto pode ter mudado, sido abandonado ou degradado desde a emissão dos créditos.",
        "ideal_situation": "O ideal é que créditos sejam utilizados dentro de 3-5 anos após sua emissão. Projetos devem manter monitoramento contínuo.",
        "icon": "clock", "severity_typical": "medium",
    },
    "retirement_anomaly": {
        "title": "Anomalia de Aposentadoria",
        "what_is": "Uma anomalia de aposentadoria ocorre quando o padrão de aposentadoria dos créditos apresenta comportamento incomum - volume muito grande de uma só vez, datas suspeitas, ou padrões que sugerem manipulação contábil.",
        "consequences": "Padrões anômalos podem indicar tentativas de manipulação do mercado, dupla contagem ou fraude direta. Isso compromete a integridade do sistema de rastreamento.",
        "ideal_situation": "O ideal é que aposentadorias sigam um padrão regular e proporcional ao tamanho do projeto. Cada crédito deve ter identificador único e ser aposentado apenas uma vez.",
        "icon": "repeat", "severity_typical": "high",
    },
    "missing_area": {
        "title": "Área do Projeto Ausente ou Inconsistente",
        "what_is": "Este alerta indica que o projeto não possui informações geográficas adequadas sobre sua área de atuação, ou que a área declarada é inconsistente com imagens de satélite.",
        "consequences": "Sem dados geográficos confiáveis, é impossível verificar se o projeto realmente existe fisicamente. Projetos fantasma são uma das formas mais graves de fraude.",
        "ideal_situation": "Todo projeto deve ter coordenadas geográficas precisas, com verificação por imagens de satélite atualizadas. A área deve ser validada por auditores independentes.",
        "icon": "map-pin", "severity_typical": "medium",
    },
    "governance_gaps": {
        "title": "Lacunas de Governança",
        "what_is": "Lacunas de governança referem-se à ausência de informações essenciais sobre a gestão, transparência e conformidade do projeto.",
        "consequences": "Projetos com governança fraca são mais suscetíveis a fraudes, conflitos com comunidades locais e falhas operacionais.",
        "ideal_situation": "O projeto deve ter documentação completa e pública: relatório de validação, relatórios de monitoramento periódicos, consentimento das comunidades locais (FPIC).",
        "icon": "file-warning", "severity_typical": "medium",
    },
    "insufficient_buffer": {
        "title": "Buffer de Permanência Insuficiente",
        "what_is": "O buffer de permanência é uma reserva de créditos que o projeto mantém como \"seguro\" contra riscos de reversão (incêndio, desmatamento).",
        "consequences": "Se ocorrer reversão e o buffer for insuficiente, os créditos já vendidos não poderão ser compensados.",
        "ideal_situation": "Projetos florestais devem manter buffer mínimo de 15-20% dos créditos emitidos, ajustado conforme perfil de risco.",
        "icon": "shield-off", "severity_typical": "high",
    },
    "fire_proximity": {
        "title": "Incêndio Próximo ao Projeto",
        "what_is": "Este alerta é gerado automaticamente quando dados de satélite (GOES-R / NASA FIRMS) detectam focos de calor (hotspots) próximos à área do projeto.",
        "consequences": "Incêndios podem destruir vegetação e liberar carbono sequestrado, anulando créditos já emitidos. Representa risco direto de reversão de permanência.",
        "ideal_situation": "Projetos devem ter planos de contingência contra incêndios, seguro contra reversão, e monitoramento remoto contínuo.",
        "icon": "flame", "severity_typical": "critical",
    },
    "deforestation_detected": {
        "title": "Desmatamento Detectado por Satélite",
        "what_is": "Dados de satélite (Landsat/Sentinel-2) mostram queda significativa no índice de vegetação (NDVI) na área do projeto, indicando possível desmatamento.",
        "consequences": "Desmatamento em projetos REDD+ invalida completamente os créditos, pois o carbono sequestrado foi liberado.",
        "ideal_situation": "A cobertura vegetal deve ser mantida ou aumentada ao longo do tempo. Monitoramento por satélite deve confirmar permanência.",
        "icon": "tree-deciduous", "severity_typical": "critical",
    },
}


def _alert_to_dict(alert, project_name: str) -> dict:
    data = FraudAlertResponse.model_validate(alert).model_dump()
    data["project_name"] = project_name
    return data


@router.get("")
async def list_fraud_alerts(
    page: int = Query(1, ge=1), page_size: int = Query(PAGE_SIZE, ge=1, le=100),
    severity: Optional[str] = None, status: Optional[str] = None,
    project_id: Optional[int] = None, alert_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    base = select(FraudAlert, CarbonProject.name.label("pn")).join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
    count_base = select(FraudAlert.id)
    for q in [base, count_base]:
        if severity:
            q = q.where(FraudAlert.severity == severity)
        if status:
            q = q.where(FraudAlert.status == status)
        if project_id:
            q = q.where(FraudAlert.project_id == project_id)
        if alert_type:
            q = q.where(FraudAlert.alert_type == alert_type)
    # rebuild with filters
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


@router.get("/grouped-by-type")
async def fraud_alerts_grouped_by_type(page_size: int = Query(10, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    type_result = await db.execute(
        select(FraudAlert.alert_type, func.count(FraudAlert.id)).group_by(FraudAlert.alert_type).order_by(func.count(FraudAlert.id).desc())
    )
    type_counts = {r[0]: r[1] for r in type_result.all()}
    grouped = {}
    for at, tc in type_counts.items():
        tp = math.ceil(tc / page_size) if tc > 0 else 1
        rows = (await db.execute(
            select(FraudAlert, CarbonProject.name.label("pn")).join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
            .where(FraudAlert.alert_type == at).order_by(FraudAlert.severity.desc(), FraudAlert.created_at.desc()).limit(page_size)
        )).all()
        explanation = FRAUD_TYPE_EXPLANATIONS.get(at, {"title": at.replace("_", " ").title(), "what_is": "N/A", "consequences": "N/A", "ideal_situation": "N/A", "icon": "alert-circle", "severity_typical": "medium"})
        grouped[at] = {"items": [_alert_to_dict(r[0], r[1]) for r in rows], "total": tc, "page": 1, "page_size": page_size, "total_pages": tp, "explanation": explanation}
    return {"types": grouped, "total_types": len(type_counts), "total_alerts": sum(type_counts.values())}


@router.get("/grouped-by-type/{alert_type}")
async def fraud_alerts_by_type(alert_type: str, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(select(FraudAlert.id).where(FraudAlert.alert_type == alert_type).subquery()))).scalar() or 0
    tp = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    rows = (await db.execute(
        select(FraudAlert, CarbonProject.name.label("pn")).join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
        .where(FraudAlert.alert_type == alert_type).order_by(FraudAlert.severity.desc(), FraudAlert.created_at.desc()).offset(offset).limit(page_size)
    )).all()
    explanation = FRAUD_TYPE_EXPLANATIONS.get(alert_type, {"title": alert_type.replace("_", " ").title(), "what_is": "N/A", "consequences": "N/A", "ideal_situation": "N/A", "icon": "alert-circle", "severity_typical": "medium"})
    return {"items": [_alert_to_dict(r[0], r[1]) for r in rows], "total": total, "page": page, "page_size": page_size, "total_pages": tp, "explanation": explanation}


@router.get("/summary")
async def fraud_summary(db: AsyncSession = Depends(get_db)):
    sev = {r[0].value if hasattr(r[0], 'value') else str(r[0]): r[1] for r in (await db.execute(select(FraudAlert.severity, func.count(FraudAlert.id)).group_by(FraudAlert.severity))).all()}
    sts = {r[0].value if hasattr(r[0], 'value') else str(r[0]): r[1] for r in (await db.execute(select(FraudAlert.status, func.count(FraudAlert.id)).group_by(FraudAlert.status))).all()}
    byt = {r[0]: r[1] for r in (await db.execute(select(FraudAlert.alert_type, func.count(FraudAlert.id)).group_by(FraudAlert.alert_type))).all()}
    top = (await db.execute(
        select(FraudAlert.project_id, CarbonProject.name, func.count(FraudAlert.id).label("c"))
        .join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
        .group_by(FraudAlert.project_id, CarbonProject.name).order_by(func.count(FraudAlert.id).desc()).limit(5)
    )).all()
    return {"total_alerts": sum(sev.values()), "by_severity": sev, "by_status": sts, "by_type": byt,
            "top_affected_projects": [{"project_id": r[0], "project_name": r[1], "alert_count": r[2]} for r in top]}


@router.patch("/{alert_id}")
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
    alert.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(alert)
    pn = (await db.execute(select(CarbonProject.name).where(CarbonProject.id == alert.project_id))).scalar() or "N/A"
    return _alert_to_dict(alert, pn)
