"""API Routes: Projects, Ratings, Dashboard — Carbon Verify v3."""
import math
import random
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    CarbonProject, ProjectRating, FraudAlert, CreditBatch,
    PortfolioPosition, User, RatingPillar
)
from app.models.schemas import ProjectCreate, RatingResponse
from app.modules.rating.service import calculate_rating
from app.modules.fraud_ops.service import run_fraud_detection
from app.modules.compliance.service import get_compliance_summary

router = APIRouter(prefix="/projects", tags=["Projetos de Carbono"])
PAGE_SIZE = 40


def _serialize_project(project, rating=None, alert_count=0, has_position=False, credits_forecast=None):
    proj_dict = {
        "id": project.id,
        "external_id": project.external_id,
        "name": project.name,
        "description": project.description,
        "project_type": project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type),
        "methodology": project.methodology,
        "registry": project.registry,
        "country": project.country,
        "region": project.region,
        "latitude": project.latitude,
        "longitude": project.longitude,
        "proponent": project.proponent,
        "total_credits_issued": project.total_credits_issued,
        "total_credits_retired": project.total_credits_retired,
        "total_credits_available": project.total_credits_available,
        "vintage_year": project.vintage_year,
        "area_hectares": project.area_hectares,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "baseline_scenario": project.baseline_scenario,
        "additionality_justification": project.additionality_justification,
        "monitoring_frequency": project.monitoring_frequency,
        "buffer_pool_percentage": project.buffer_pool_percentage,
        "sdg_contributions": project.sdg_contributions,
        "integration_source": project.integration_source,
        "sinare_id": project.sinare_id,
        "created_at": project.created_at,
        "rating": None,
        "fraud_alert_count": alert_count,
        "has_position": has_position,
    }
    if credits_forecast is not None:
        proj_dict["credits_forecast"] = credits_forecast
    if rating:
        proj_dict["rating"] = {
            "id": rating.id, "project_id": rating.project_id,
            "overall_score": rating.overall_score,
            "grade": rating.grade.value if hasattr(rating.grade, 'value') else str(rating.grade),
            "carbon_integrity_score": rating.carbon_integrity_score,
            "additionality_score": rating.additionality_score,
            "permanence_score": rating.permanence_score,
            "leakage_score": rating.leakage_score,
            "mrv_score": rating.mrv_score,
            "co_benefits_score": rating.co_benefits_score,
            "governance_score": rating.governance_score,
            "satellite_confidence_score": rating.satellite_confidence_score,
            "confidence_level": rating.confidence_level,
            "discount_factor": rating.discount_factor,
            "explanation": rating.explanation,
            "risk_flags": rating.risk_flags,
            "rated_at": rating.rated_at,
        }
    return proj_dict


async def _get_project_ids_with_positions(db: AsyncSession) -> set:
    result = await db.execute(
        select(CreditBatch.project_id)
        .join(PortfolioPosition, PortfolioPosition.credit_id == CreditBatch.id)
        .distinct()
    )
    return {row[0] for row in result.all()}


def _generate_credits_forecast(project):
    total_issued = project.total_credits_issued or 0
    total_retired = project.total_credits_retired or 0
    total_available = project.total_credits_available or 0
    vintage = project.vintage_year or 2020
    start_year = project.start_date.year if project.start_date else vintage - 2
    end_year = project.end_date.year if project.end_date else vintage + 15
    rng = random.Random(project.id * 7 + 42)
    annual_rate = total_issued / max(1, vintage - start_year + 1) if vintage > start_year else total_issued

    past, remaining_issued, remaining_retired = [], total_issued, total_retired
    for year in range(vintage - min(3, vintage - start_year), vintage + 1):
        if year < start_year:
            continue
        yp = min(int(annual_rate * rng.uniform(0.7, 1.3)), remaining_issued)
        yr = min(int(yp * rng.uniform(0.85, 1.05)), yp + int(yp * 0.05))
        yrt = min(remaining_retired, int(yr * rng.uniform(0.3, 0.8)))
        remaining_retired -= yrt
        remaining_issued -= yp
        past.append({
            "vintage_year": year, "type": "emitido", "planned_quantity": yp,
            "planned_date": f"{year}-{rng.choice([3,6,9,12]):02d}",
            "realized_quantity": yr,
            "realized_date": f"{year}-{max(1,min(12, rng.choice([3,6,9,12])+rng.randint(-2,4))):02d}",
            "retired_quantity": yrt, "status": "concluído",
            "completion_pct": round(min(100, (yr / max(1, yp)) * 100), 1),
        })

    future = []
    current_year = datetime.now(timezone.utc).year
    for i in range(1, min(6, end_year - current_year + 1)):
        fy = current_year + i
        if fy > end_year:
            break
        decay = max(0.5, 1.0 - (i * 0.08))
        pq = int(annual_rate * decay * rng.uniform(0.8, 1.1))
        future.append({
            "vintage_year": fy, "type": "projeção", "planned_quantity": pq,
            "planned_date": f"{fy}-{rng.choice([6,9,12]):02d}",
            "realized_quantity": None, "realized_date": None,
            "retired_quantity": None, "status": "pendente", "completion_pct": 0,
        })

    tp = sum(v["planned_quantity"] for v in past)
    tr = sum(v["realized_quantity"] for v in past)
    return {
        "summary": {
            "total_issued": total_issued, "total_retired": total_retired,
            "total_available": total_available, "total_planned_past": tp,
            "total_realized_past": tr,
            "total_projected_future": sum(v["planned_quantity"] for v in future),
            "realization_rate_pct": round((tr / max(1, tp)) * 100, 1),
            "project_start": start_year, "project_end": end_year,
        },
        "vintages": past + future,
    }


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1), page_size: int = Query(PAGE_SIZE, ge=1, le=100),
    project_type: Optional[str] = None, country: Optional[str] = None,
    registry: Optional[str] = None, min_score: Optional[float] = None,
    max_score: Optional[float] = None, search: Optional[str] = None,
    has_position: Optional[str] = None,
    sort_field: Optional[str] = None, sort_dir: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    ids_with_position = await _get_project_ids_with_positions(db)
    base_query = select(CarbonProject)
    if project_type:
        base_query = base_query.where(CarbonProject.project_type == project_type)
    if country:
        base_query = base_query.where(CarbonProject.country == country)
    if registry:
        base_query = base_query.where(CarbonProject.registry == registry)
    if search:
        base_query = base_query.where(CarbonProject.name.ilike(f"%{search}%"))
    if has_position == "true" and ids_with_position:
        base_query = base_query.where(CarbonProject.id.in_(ids_with_position))
    elif has_position == "true":
        base_query = base_query.where(CarbonProject.id == -1)
    elif has_position == "false" and ids_with_position:
        base_query = base_query.where(CarbonProject.id.notin_(ids_with_position))

    needs_join = False
    if min_score is not None or max_score is not None:
        needs_join = True
        base_query = base_query.join(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        if min_score is not None:
            base_query = base_query.where(ProjectRating.overall_score >= min_score)
        if max_score is not None:
            base_query = base_query.where(ProjectRating.overall_score <= max_score)

    count_q = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    order_clause = CarbonProject.id
    sort_fn = asc if sort_dir != "desc" else desc
    if sort_field:
        field_map = {
            "name": CarbonProject.name, "project_type": CarbonProject.project_type,
            "country": CarbonProject.country, "registry": CarbonProject.registry,
            "credits": CarbonProject.total_credits_issued,
        }
        if sort_field in field_map:
            order_clause = field_map[sort_field]
        elif sort_field in ("score", "grade"):
            if not needs_join:
                base_query = base_query.outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
            order_clause = ProjectRating.overall_score

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query.options(selectinload(CarbonProject.rating), selectinload(CarbonProject.fraud_alerts))
        .order_by(sort_fn(order_clause)).offset(offset).limit(page_size)
    )
    projects = result.scalars().unique().all()
    items = [
        _serialize_project(p, p.rating, len(p.fraud_alerts) if p.fraud_alerts else 0, p.id in ids_with_position)
        for p in projects
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}


@router.get("/geo")
async def list_projects_geo(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            CarbonProject.id, CarbonProject.name, CarbonProject.latitude, CarbonProject.longitude,
            CarbonProject.project_type, CarbonProject.country,
            ProjectRating.overall_score, ProjectRating.grade,
            func.count(FraudAlert.id).label("alert_count"),
        )
        .outerjoin(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .outerjoin(FraudAlert, CarbonProject.id == FraudAlert.project_id)
        .where(CarbonProject.latitude.isnot(None), CarbonProject.longitude.isnot(None))
        .group_by(CarbonProject.id, CarbonProject.name, CarbonProject.latitude, CarbonProject.longitude,
                  CarbonProject.project_type, CarbonProject.country,
                  ProjectRating.overall_score, ProjectRating.grade)
    )
    return [
        {"id": r[0], "name": r[1], "lat": r[2], "lng": r[3],
         "project_type": r[4].value if hasattr(r[4], 'value') else str(r[4]),
         "country": r[5], "score": r[6] or 0,
         "grade": r[7].value if hasattr(r[7], 'value') else str(r[7]) if r[7] else "N/A",
         "alert_count": r[8]}
        for r in result.all()
    ]


@router.get("/compare")
async def compare_projects(ids: str = Query(...), db: AsyncSession = Depends(get_db)):
    project_ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()][:5]
    if not project_ids:
        raise HTTPException(status_code=400, detail="Forneça ao menos 1 ID")
    result = await db.execute(
        select(CarbonProject).options(selectinload(CarbonProject.rating), selectinload(CarbonProject.fraud_alerts))
        .where(CarbonProject.id.in_(project_ids))
    )
    return [_serialize_project(p, p.rating, len(p.fraud_alerts) if p.fraud_alerts else 0) for p in result.scalars().unique().all()]


@router.get("/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CarbonProject)
        .options(selectinload(CarbonProject.rating), selectinload(CarbonProject.fraud_alerts), selectinload(CarbonProject.credits))
        .where(CarbonProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    ids_pos = await _get_project_ids_with_positions(db)
    forecast = _generate_credits_forecast(project)
    data = _serialize_project(project, project.rating, len(project.fraud_alerts) if project.fraud_alerts else 0, project_id in ids_pos, forecast)

    # Add compliance summary
    if project.rating:
        project_data = {k: v for k, v in data.items() if k != "rating"}
        rating_data = data.get("rating", {})
        data["compliance"] = get_compliance_summary(project_data, rating_data)

    return data


@router.post("", status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = CarbonProject(**data.model_dump())
    db.add(project)
    await db.flush()
    rating, pillars = calculate_rating(project)
    db.add(rating)
    await db.flush()
    for pillar in pillars:
        pillar.rating_id = rating.id
        db.add(pillar)
    alerts = run_fraud_detection(project)
    for a in alerts:
        db.add(a)
    await db.commit()
    await db.refresh(project)
    return _serialize_project(project, rating, len(alerts))


@router.get("/{project_id}/rating")
async def get_project_rating(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectRating)
        .options(selectinload(ProjectRating.pillars))
        .where(ProjectRating.project_id == project_id)
    )
    rating = result.scalar_one_or_none()
    if not rating:
        raise HTTPException(status_code=404, detail="Rating não encontrado")
    return {
        "id": rating.id, "project_id": rating.project_id,
        "overall_score": rating.overall_score,
        "grade": rating.grade.value if hasattr(rating.grade, 'value') else str(rating.grade),
        "carbon_integrity_score": rating.carbon_integrity_score,
        "additionality_score": rating.additionality_score,
        "permanence_score": rating.permanence_score,
        "leakage_score": rating.leakage_score,
        "mrv_score": rating.mrv_score,
        "co_benefits_score": rating.co_benefits_score,
        "governance_score": rating.governance_score,
        "discount_factor": rating.discount_factor,
        "confidence_level": rating.confidence_level,
        "explanation": rating.explanation,
        "risk_flags": rating.risk_flags,
        "pillars": [
            {"pillar_name": p.pillar_name, "score": p.score, "weight": p.weight, "details": p.details}
            for p in rating.pillars
        ] if rating.pillars else [],
        "rated_at": rating.rated_at,
    }


@router.post("/{project_id}/recalculate-rating")
async def recalculate_rating(project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(CarbonProject).where(CarbonProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    existing = await db.execute(select(ProjectRating).where(ProjectRating.project_id == project_id))
    old = existing.scalar_one_or_none()
    if old:
        await db.execute(select(RatingPillar).where(RatingPillar.rating_id == old.id))
        await db.delete(old)
        await db.flush()
    new_rating, pillars = calculate_rating(project)
    db.add(new_rating)
    await db.flush()
    for pillar in pillars:
        pillar.rating_id = new_rating.id
        db.add(pillar)
    await db.commit()
    return {"message": "Rating recalculado", "new_score": new_rating.overall_score, "new_grade": new_rating.grade.value}
