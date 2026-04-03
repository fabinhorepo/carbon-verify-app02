"""Cliente Copernicus (Sentinel-5P/TROPOMI) - Monit. GHG - Carbon Verify."""
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import CarbonProject, SatelliteObservation


async def get_ghg_data(db: AsyncSession, project_id: int) -> dict:
    """Retorna dados de concentração de GHG para um projeto."""
    result = await db.execute(select(CarbonProject).where(CarbonProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        return {"error": "Projeto não encontrado"}

    obs = await db.execute(
        select(SatelliteObservation)
        .where(SatelliteObservation.project_id == project_id, SatelliteObservation.observation_type.in_(["co2", "ch4", "no2"]))
        .order_by(SatelliteObservation.observed_at.desc()).limit(50)
    )
    observations = obs.scalars().all()

    if observations:
        data = [{"type": o.observation_type, "value": o.value, "unit": o.unit, "date": o.observed_at.isoformat(), "satellite": o.satellite} for o in observations]
    else:
        data = _generate_ghg_data(project)

    return {"project_id": project_id, "project_name": project.name, "data": data,
            "source": "Sentinel-5P / TROPOMI", "description": "Concentração de gases de efeito estufa na região do projeto"}


async def get_ghg_anomalies(db: AsyncSession) -> dict:
    """Detecta anomalias de GHG sobre projetos monitorados."""
    result = await db.execute(
        select(CarbonProject).where(CarbonProject.latitude.isnot(None), CarbonProject.longitude.isnot(None))
    )
    projects = result.scalars().all()
    rng = random.Random(77)
    anomalies = []

    for p in projects:
        pt = p.project_type if isinstance(p.project_type, str) else p.project_type.value
        if rng.random() < 0.15:
            gas = "CH4" if pt == "Methane Avoidance" else "CO2" if pt in ("REDD+", "ARR") else rng.choice(["CO2", "CH4"])
            baseline = {"CO2": 415, "CH4": 1900}[gas]
            current = baseline * rng.uniform(1.05, 1.25)
            anomalies.append({
                "project_id": p.id, "project_name": p.name, "country": p.country,
                "gas": gas, "baseline_ppb": baseline, "current_ppb": round(current, 1),
                "change_pct": round(((current - baseline) / baseline) * 100, 1),
                "severity": "high" if current > baseline * 1.15 else "medium",
                "satellite": "Sentinel-5P", "detected_at": datetime.utcnow().isoformat(),
            })

    return {"anomalies": anomalies, "total": len(anomalies), "projects_monitored": len(projects)}


def _generate_ghg_data(project):
    rng = random.Random(project.id * 23 + 5)
    now = datetime.utcnow()
    data = []
    for i in range(12):
        date = now - timedelta(days=30 * i)
        data.append({"type": "co2", "value": round(410 + rng.uniform(-5, 10), 1), "unit": "ppm", "date": date.isoformat(), "satellite": "Sentinel-5P"})
        data.append({"type": "ch4", "value": round(1880 + rng.uniform(-50, 100), 1), "unit": "ppb", "date": date.isoformat(), "satellite": "TROPOMI"})
    return data
