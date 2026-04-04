"""Endpoints de Integrações Externas (Verra, Gold Standard, etc.)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import CarbonProject, IntegrationSync, User, CreditBatch, PortfolioPosition, ProjectRating

router = APIRouter(prefix="/integrations", tags=["Integrações"])


@router.get("/status")
async def integration_status(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retorna status de todas as integrações."""
    result = await db.execute(select(IntegrationSync).order_by(IntegrationSync.last_sync_at.desc()))
    syncs = result.scalars().all()
    return [
        {
            "source": s.source.value if hasattr(s.source, 'value') else str(s.source),
            "status": s.status, "last_sync_at": s.last_sync_at,
            "projects_synced": s.projects_synced, "projects_failed": s.projects_failed,
            "error_message": s.error_message,
        }
        for s in syncs
    ]


@router.post("/verra/search")
async def verra_search(query: str = Query(...), current_user: User = Depends(get_current_user)):
    """Busca projetos no Verra Registry."""
    from app.services.integrations.verra_client import search_verra_projects
    results = await search_verra_projects(query)
    return {"results": results, "count": len(results)}


@router.post("/verra/import")
async def verra_import(
    project_id: str = Query(..., description="Verra Project ID"),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """Importa um projeto do Verra Registry."""
    from app.services.integrations.verra_client import import_verra_project
    project = await import_verra_project(db, project_id)
    return {"message": f"Projeto '{project.name}' importado com sucesso", "project_id": project.id}


@router.post("/verra/sync")
async def verra_sync(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Força sincronização com Verra."""
    from app.services.integrations.verra_client import sync_verra_projects
    result = await sync_verra_projects(db)
    return result


@router.post("/gold-standard/search")
async def gs_search(query: str = Query(...), current_user: User = Depends(get_current_user)):
    from app.services.integrations.gold_standard_client import search_gs_projects
    results = await search_gs_projects(query)
    return {"results": results, "count": len(results)}


@router.post("/gold-standard/import")
async def gs_import(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    from app.services.integrations.gold_standard_client import import_gs_project
    project = await import_gs_project(db, project_id)
    return {"message": f"Projeto '{project.name}' importado", "project_id": project.id}


# ─── Satellite Endpoints ────────────────────────────────────────────────

satellite_router = APIRouter(prefix="/satellite", tags=["Sensoriamento Remoto"])


@satellite_router.get("/fire-alerts")
async def fire_alerts(db: AsyncSession = Depends(get_db)):
    """Retorna alertas de incêndio próximos a projetos."""
    from app.services.satellite.goes_fire_client import get_fire_alerts_near_projects
    return await get_fire_alerts_near_projects(db)


@satellite_router.get("/fire-alerts/{project_id}")
async def fire_alerts_for_project(project_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.satellite.goes_fire_client import get_fire_alerts_for_project
    return await get_fire_alerts_for_project(db, project_id)


@satellite_router.get("/ndvi/{project_id}")
async def ndvi_data(project_id: int, period: str = Query("12m"), db: AsyncSession = Depends(get_db)):
    """Retorna dados NDVI do projeto."""
    from app.services.satellite.landsat_sentinel_client import get_ndvi_timeseries
    return await get_ndvi_timeseries(db, project_id, period)


@satellite_router.get("/ghg/{project_id}")
async def ghg_data(project_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna dados de GHG (Sentinel-5P) para o projeto."""
    from app.services.satellite.copernicus_client import get_ghg_data
    return await get_ghg_data(db, project_id)


@satellite_router.get("/ghg/anomalies")
async def ghg_anomalies(db: AsyncSession = Depends(get_db)):
    from app.services.satellite.copernicus_client import get_ghg_anomalies
    return await get_ghg_anomalies(db)


@satellite_router.get("/xco2/{project_id}")
async def xco2_data(project_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.satellite.oco_client import get_xco2_data
    return await get_xco2_data(db, project_id)


@satellite_router.get("/deforestation-alerts")
async def deforestation_alerts(db: AsyncSession = Depends(get_db)):
    from app.services.satellite.landsat_sentinel_client import get_deforestation_alerts
    return await get_deforestation_alerts(db)


@satellite_router.get("/biomass-estimate/{project_id}")
async def biomass_estimate(project_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.satellite.landsat_sentinel_client import get_biomass_estimate
    return await get_biomass_estimate(db, project_id)


# ─── Web3 Endpoints ─────────────────────────────────────────────────────

web3_router = APIRouter(prefix="/web3", tags=["Web3 / Blockchain"])


@web3_router.get("/pool-stats")
async def pool_stats():
    """Retorna estatísticas dos pools Toucan (BCT/NCT)."""
    from app.services.integrations.toucan_client import get_pool_stats
    return await get_pool_stats()


@web3_router.get("/verify-token")
async def verify_token(address: str = Query(...)):
    from app.services.integrations.toucan_client import verify_token_address
    return await verify_token_address(address)


@web3_router.get("/project-tokenization/{project_id}")
async def project_tokenization(project_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.integrations.toucan_client import get_project_tokenization
    return await get_project_tokenization(db, project_id)


# ─── ESG / Carbon Accounting ────────────────────────────────────────────

esg_router = APIRouter(prefix="/esg", tags=["ESG / Contabilidade"])


@esg_router.post("/import-footprint")
async def import_footprint(
    data: dict,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    from app.models.models import CorporateEmission
    emissions = []
    for item in data.get("emissions", []):
        e = CorporateEmission(
            organization_id=current_user.organization_id,
            scope=item.get("scope", "1"),
            amount_tco2e=item.get("amount_tco2e", 0),
            year=item.get("year", 2025),
            category=item.get("category"),
            source_description=item.get("source_description"),
        )
        db.add(e)
        emissions.append(e)
    await db.commit()
    return {"message": f"{len(emissions)} emissões importadas", "count": len(emissions)}


@esg_router.get("/balance")
async def carbon_balance(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.models import CorporateEmission, CarbonBalance
    from sqlalchemy import func

    emissions = (await db.execute(
        select(func.sum(CorporateEmission.amount_tco2e))
        .where(CorporateEmission.organization_id == current_user.organization_id)
    )).scalar() or 0

    # Use CarbonBalance offsets for the org
    offsets_result = (await db.execute(
        select(func.sum(CarbonBalance.total_offsets))
        .where(CarbonBalance.organization_id == current_user.organization_id)
    )).scalar() or 0

    net = float(emissions) - float(offsets_result)
    return {
        "total_emissions_tco2e": round(float(emissions), 2),
        "total_offsets_tco2e": round(float(offsets_result), 2),
        "net_balance_tco2e": round(net, 2),
        "status": "net_zero" if net <= 0 else "positive_emissions",
        "offset_percentage": round((float(offsets_result) / max(float(emissions), 1)) * 100, 1),
    }


@esg_router.get("/offset-recommendations")
async def offset_recommendations(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Recomenda projetos para compensar emissões restantes."""
    from app.models.models import CorporateEmission
    from sqlalchemy import func

    emissions = (await db.execute(
        select(func.sum(CorporateEmission.amount_tco2e))
        .where(CorporateEmission.organization_id == current_user.organization_id)
    )).scalar() or 0

    # Buscar melhores projetos por score
    result = await db.execute(
        select(CarbonProject, ProjectRating)
        .join(ProjectRating, CarbonProject.id == ProjectRating.project_id)
        .order_by(ProjectRating.overall_score.desc())
        .limit(10)
    )
    projects = [
        {
            "project_id": p.id, "name": p.name, "country": p.country,
            "project_type": p.project_type.value if hasattr(p.project_type, 'value') else str(p.project_type),
            "available_credits": max(0, (p.total_credits_issued or 0) - (p.total_credits_retired or 0)),
            "score": r.overall_score, "grade": r.grade.value if hasattr(r.grade, 'value') else str(r.grade),
        }
        for p, r in result.all()
    ]
    return {"remaining_emissions_tco2e": round(float(emissions), 2), "recommended_projects": projects}


@esg_router.get("/net-zero-projection")
async def net_zero_projection(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Projeta quando a organização atinge Net Zero."""
    from app.models.models import CorporateEmission
    from sqlalchemy import func

    result = await db.execute(
        select(CorporateEmission.year, func.sum(CorporateEmission.amount_tco2e))
        .where(CorporateEmission.organization_id == current_user.organization_id)
        .group_by(CorporateEmission.year)
        .order_by(CorporateEmission.year)
    )
    yearly = {r[0]: float(r[1]) for r in result.all()}

    if len(yearly) < 2:
        return {"projection": "Dados insuficientes para projeção", "yearly_emissions": yearly}

    years = sorted(yearly.keys())
    values = [yearly[y] for y in years]
    avg_reduction = (values[0] - values[-1]) / max(len(values) - 1, 1)

    if avg_reduction <= 0:
        return {"projection": "Emissões estão aumentando - Net Zero não atingível com tendência atual", "yearly_emissions": yearly}

    years_to_zero = int(values[-1] / max(avg_reduction, 0.1))
    target_year = years[-1] + years_to_zero

    return {
        "current_emissions": values[-1],
        "avg_annual_reduction": round(avg_reduction, 1),
        "projected_net_zero_year": target_year,
        "years_remaining": years_to_zero,
        "yearly_emissions": yearly,
    }
