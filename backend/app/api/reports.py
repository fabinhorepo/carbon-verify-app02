"""Endpoints de Relatórios."""
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import Report, ReportStatus, User
from app.models.schemas import ReportCreate, ReportResponse

router = APIRouter(prefix="/reports", tags=["Relatórios"])


@router.get("")
async def list_reports(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    base = select(Report).where(Report.organization_id == current_user.organization_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    offset = (page - 1) * page_size
    result = await db.execute(base.order_by(desc(Report.created_at)).offset(offset).limit(page_size))
    reports = result.scalars().all()
    return {
        "items": [ReportResponse.model_validate(r) for r in reports],
        "total": total, "page": page, "page_size": page_size, "total_pages": total_pages,
    }


@router.post("", status_code=201)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = Report(
        name=data.name,
        report_type=data.report_type,
        format=data.format,
        parameters=data.parameters,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        status=ReportStatus.PENDING,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Em produção, isso seria processado async por um worker
    # Por enquanto, geramos inline
    try:
        report.status = ReportStatus.GENERATING
        await db.commit()
        from app.services.report_generator import generate_report
        file_path, file_size = await generate_report(db, report)
        report.file_path = file_path
        report.file_size_bytes = file_size
        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.utcnow()
    except Exception as e:
        report.status = ReportStatus.FAILED
        report.error_message = str(e)
    await db.commit()
    await db.refresh(report)
    return ReportResponse.model_validate(report)


@router.get("/templates")
async def list_templates():
    return [
        {"id": "portfolio_summary", "name": "Resumo Executivo de Portfólio", "type": "portfolio", "description": "Visão geral do portfólio com métricas de risco e qualidade"},
        {"id": "due_diligence", "name": "Due Diligence Completa", "type": "due_diligence", "description": "Análise detalhada de um projeto específico"},
        {"id": "fraud_report", "name": "Relatório de Alertas de Fraude", "type": "fraud", "description": "Resumo de todos os alertas com recomendações"},
        {"id": "esg_investor", "name": "Relatório ESG para Investidores", "type": "esg", "description": "Relatório formatado para compliance ESG"},
        {"id": "executive_summary", "name": "Resumo Executivo Mensal", "type": "executive", "description": "KPIs e métricas do mês"},
    ]


@router.get("/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return ReportResponse.model_validate(report)
