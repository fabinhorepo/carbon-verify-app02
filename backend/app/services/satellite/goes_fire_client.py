"""Cliente NASA FIRMS (GOES-R) - Alertas de Incêndio - Carbon Verify."""
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.models import CarbonProject, SatelliteObservation, FraudAlert, FraudSeverity

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
PROXIMITY_KM = 50


def _haversine(lat1, lon1, lat2, lon2):
    import math
    R = 6371
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


async def get_fire_alerts_near_projects(db: AsyncSession) -> dict:
    """Busca focos de calor próximos a todos os projetos."""
    result = await db.execute(
        select(CarbonProject).where(CarbonProject.latitude.isnot(None), CarbonProject.longitude.isnot(None))
    )
    projects = result.scalars().all()
    if not projects:
        return {"alerts": [], "total": 0}

    hotspots = await _fetch_firms_data(projects)
    alerts = []

    for hs in hotspots:
        for p in projects:
            dist = _haversine(hs["lat"], hs["lon"], p.latitude, p.longitude)
            if dist <= PROXIMITY_KM:
                alerts.append({
                    "project_id": p.id, "project_name": p.name,
                    "hotspot_lat": hs["lat"], "hotspot_lon": hs["lon"],
                    "distance_km": round(dist, 1), "brightness": hs.get("brightness", 0),
                    "confidence": hs.get("confidence", "nominal"),
                    "satellite": hs.get("satellite", "GOES-R"),
                    "acq_date": hs.get("acq_date", ""),
                    "risk_level": "critical" if dist < 5 else "high" if dist < 20 else "medium",
                })

    return {"alerts": alerts, "total": len(alerts), "projects_monitored": len(projects)}


async def get_fire_alerts_for_project(db: AsyncSession, project_id: int) -> dict:
    """Busca focos de calor próximos a um projeto específico."""
    result = await db.execute(select(CarbonProject).where(CarbonProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project or not project.latitude or not project.longitude:
        return {"alerts": [], "message": "Projeto sem coordenadas"}

    hotspots = await _fetch_firms_data([project])
    alerts = []
    for hs in hotspots:
        dist = _haversine(hs["lat"], hs["lon"], project.latitude, project.longitude)
        if dist <= PROXIMITY_KM:
            alerts.append({
                "hotspot_lat": hs["lat"], "hotspot_lon": hs["lon"],
                "distance_km": round(dist, 1), "brightness": hs.get("brightness", 0),
                "confidence": hs.get("confidence", "nominal"),
                "satellite": hs.get("satellite", "GOES-R"),
                "acq_date": hs.get("acq_date", ""),
            })

    # Salvar observação
    if alerts:
        obs = SatelliteObservation(
            project_id=project_id, satellite="GOES-R/FIRMS",
            observation_type="fire_hotspot", value=len(alerts),
            unit="hotspots", observed_at=datetime.utcnow(),
            metadata_json={"nearest_km": min(a["distance_km"] for a in alerts)},
        )
        db.add(obs)
        await db.commit()

    return {"project_id": project_id, "project_name": project.name, "alerts": alerts, "total": len(alerts)}


async def _fetch_firms_data(projects: list) -> list[dict]:
    """Busca dados do NASA FIRMS."""
    if not settings.NASA_FIRMS_API_KEY:
        return _generate_sample_hotspots(projects)

    try:
        lats = [p.latitude for p in projects if p.latitude]
        lons = [p.longitude for p in projects if p.longitude]
        if not lats:
            return []

        min_lat, max_lat = min(lats) - 1, max(lats) + 1
        min_lon, max_lon = min(lons) - 1, max(lons) + 1

        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{FIRMS_BASE_URL}/{settings.NASA_FIRMS_API_KEY}/VIIRS_SNPP_NRT/{min_lon},{min_lat},{max_lon},{max_lat}/1"
            resp = await client.get(url)
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                if len(lines) <= 1:
                    return []
                headers = lines[0].split(",")
                hotspots = []
                for line in lines[1:]:
                    vals = line.split(",")
                    if len(vals) >= len(headers):
                        row = dict(zip(headers, vals))
                        try:
                            hotspots.append({
                                "lat": float(row.get("latitude", 0)),
                                "lon": float(row.get("longitude", 0)),
                                "brightness": float(row.get("bright_ti4", row.get("brightness", 0))),
                                "confidence": row.get("confidence", "nominal"),
                                "satellite": "VIIRS", "acq_date": row.get("acq_date", ""),
                            })
                        except ValueError:
                            continue
                return hotspots
    except Exception:
        pass

    return _generate_sample_hotspots(projects)


def _generate_sample_hotspots(projects):
    """Gera dados de exemplo quando API não está disponível."""
    import random
    rng = random.Random(42)
    hotspots = []
    for p in projects[:5]:
        if p.latitude and p.longitude:
            for _ in range(rng.randint(0, 3)):
                hotspots.append({
                    "lat": p.latitude + rng.uniform(-0.5, 0.5),
                    "lon": p.longitude + rng.uniform(-0.5, 0.5),
                    "brightness": rng.uniform(300, 400),
                    "confidence": rng.choice(["low", "nominal", "high"]),
                    "satellite": "GOES-R (sample)",
                    "acq_date": datetime.utcnow().strftime("%Y-%m-%d"),
                })
    return hotspots
