"""Gerador de Relatórios - Carbon Verify Produção."""
import os, json, csv, io
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Report, CarbonProject, ProjectRating, FraudAlert, Portfolio, PortfolioPosition, CarbonCredit


async def generate_report(db: AsyncSession, report: Report) -> tuple[str, int]:
    """Gera relatório e retorna (file_path, file_size)."""
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/{report.report_type}_{timestamp}.{report.format}"

    data = await _gather_report_data(db, report)

    if report.format == "json":
        content = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
    elif report.format == "csv":
        _write_csv(filename, data)
    elif report.format == "pdf":
        _write_pdf(filename, data, report)
    else:
        content = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

    file_size = os.path.getsize(filename)
    return filename, file_size


async def _gather_report_data(db: AsyncSession, report: Report) -> dict:
    """Coleta dados para o relatório."""
    rt = report.report_type if isinstance(report.report_type, str) else report.report_type.value

    if rt == "portfolio":
        return await _portfolio_data(db, report)
    elif rt == "fraud":
        return await _fraud_data(db)
    elif rt == "due_diligence":
        return await _due_diligence_data(db, report)
    elif rt == "esg":
        return await _esg_data(db, report)
    else:
        return await _executive_data(db)


async def _portfolio_data(db, report):
    projects = (await db.execute(
        select(CarbonProject, ProjectRating)
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
    )).all()
    return {
        "title": "Resumo de Portfólio",
        "generated_at": datetime.utcnow().isoformat(),
        "total_projects": len(projects),
        "projects": [
            {"name": p.name, "country": p.country, "type": p.project_type.value if hasattr(p.project_type, 'value') else str(p.project_type),
             "credits": p.total_credits_issued, "score": r.overall_score if r else 0,
             "grade": r.grade.value if r and hasattr(r.grade, 'value') else str(r.grade) if r else "N/A"}
            for p, r in projects
        ]
    }


async def _fraud_data(db):
    alerts = (await db.execute(
        select(FraudAlert, CarbonProject.name)
        .join(CarbonProject, FraudAlert.project_id == CarbonProject.id)
        .order_by(FraudAlert.severity.desc())
    )).all()
    return {
        "title": "Relatório de Alertas de Fraude",
        "generated_at": datetime.utcnow().isoformat(),
        "total_alerts": len(alerts),
        "alerts": [
            {"project": pn, "type": a.alert_type, "severity": a.severity.value if hasattr(a.severity, 'value') else a.severity,
             "title": a.title, "description": a.description, "recommendation": a.recommendation}
            for a, pn in alerts
        ]
    }


async def _due_diligence_data(db, report):
    params = report.parameters or {}
    pid = params.get("project_id")
    if not pid:
        return {"error": "project_id required in parameters"}
    result = await db.execute(select(CarbonProject).where(CarbonProject.id == pid))
    p = result.scalar_one_or_none()
    if not p:
        return {"error": "Project not found"}
    rating = (await db.execute(select(ProjectRating).where(ProjectRating.project_id == pid))).scalar_one_or_none()
    alerts = (await db.execute(select(FraudAlert).where(FraudAlert.project_id == pid))).scalars().all()
    return {
        "title": f"Due Diligence - {p.name}",
        "generated_at": datetime.utcnow().isoformat(),
        "project": {"name": p.name, "country": p.country, "type": p.project_type.value if hasattr(p.project_type, 'value') else str(p.project_type),
                     "registry": p.registry, "methodology": p.methodology, "area_ha": p.area_hectares,
                     "credits_issued": p.total_credits_issued, "vintage": p.vintage_year},
        "rating": {"score": rating.overall_score if rating else 0, "grade": rating.grade.value if rating else "N/A"} if rating else None,
        "fraud_alerts": len(alerts),
    }


async def _esg_data(db, report):
    data = await _portfolio_data(db, report)
    data["title"] = "Relatório ESG para Investidores"
    data["framework"] = "GHG Protocol / CSRD"
    return data


async def _executive_data(db):
    pc = (await db.execute(select(func.count(CarbonProject.id)))).scalar() or 0
    ac = (await db.execute(select(func.count(FraudAlert.id)))).scalar() or 0
    avg = (await db.execute(select(func.avg(ProjectRating.overall_score)))).scalar() or 0
    return {
        "title": "Resumo Executivo",
        "generated_at": datetime.utcnow().isoformat(),
        "total_projects": pc, "total_alerts": ac, "avg_quality_score": round(float(avg), 2),
    }


def _write_csv(filename, data):
    items = data.get("projects") or data.get("alerts") or []
    if not items:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("No data\n")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=items[0].keys())
        writer.writeheader()
        writer.writerows(items)


def _write_pdf(filename, data, report):
    """Gera PDF simples com reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(filename, pagesize=A4)
        w, h = A4
        y = h - 50
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, y, data.get("title", "Relatório Carbon Verify"))
        y -= 30
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Gerado em: {data.get('generated_at', '')}")
        y -= 30

        items = data.get("projects") or data.get("alerts") or []
        c.setFont("Helvetica", 9)
        for item in items[:50]:
            if y < 60:
                c.showPage()
                y = h - 50
            line = " | ".join([f"{k}: {v}" for k, v in item.items()][:5])
            c.drawString(50, y, line[:100])
            y -= 15

        c.save()
    except ImportError:
        content = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        with open(filename.replace(".pdf", ".json"), "w", encoding="utf-8") as f:
            f.write(content)
