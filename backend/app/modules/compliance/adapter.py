"""Regulatory Adapter — Jurisdiction-aware compliance and rating adjustments.

Provides a stable interface for jurisdiction-specific regulatory rules.
Currently implements BrazilAdapter with SINARE, biome, and PRODES stubs.
"""
from typing import Optional, Protocol
from abc import ABC, abstractmethod


# ─── Adapter Interface ──────────────────────────────────────────────────

class RegulatoryAdapter(ABC):
    """Interface for jurisdiction-specific regulatory adapters."""

    @abstractmethod
    def validate_requirements(self, project_data: dict) -> dict:
        """Validate minimum requirements for the jurisdiction.
        Returns dict with 'valid', 'issues', 'warnings'.
        """
        ...

    @abstractmethod
    def interpret_rating(self, rating_data: dict, project_data: dict) -> dict:
        """Interpret rating in the context of local regulations.
        Returns dict with adjusted context and recommendations.
        """
        ...

    @abstractmethod
    def get_regulatory_context(self) -> dict:
        """Return static regulatory context for this jurisdiction."""
        ...

    @abstractmethod
    def get_data_source_stubs(self) -> list[dict]:
        """Return available/planned data source integrations."""
        ...


# ─── Brazil Adapter ─────────────────────────────────────────────────────

BRAZIL_BIOMES = {
    "Amazônia": {
        "risk_level": "critical",
        "deforestation_baseline": "high",
        "monitoring_sources": ["INPE/PRODES", "INPE/DETER", "MapBiomas"],
        "notes": "Bioma sob maior pressão. Projetos REDD+ requerem monitoramento contínuo.",
    },
    "Cerrado": {
        "risk_level": "high",
        "deforestation_baseline": "very_high",
        "monitoring_sources": ["INPE/PRODES Cerrado", "MapBiomas"],
        "notes": "Segunda frente de desmatamento no Brasil. Conversão agrícola é principal driver.",
    },
    "Mata Atlântica": {
        "risk_level": "medium",
        "deforestation_baseline": "low",
        "monitoring_sources": ["SOS Mata Atlântica", "MapBiomas"],
        "notes": "Bioma altamente fragmentado. Projetos de restauração são mais comuns.",
    },
    "Pantanal": {
        "risk_level": "high",
        "deforestation_baseline": "medium",
        "monitoring_sources": ["INPE", "MapBiomas"],
        "notes": "Bioma de áreas úmidas, vulnerável a queimadas e mudanças hídricas.",
    },
    "Caatinga": {
        "risk_level": "medium",
        "deforestation_baseline": "medium",
        "monitoring_sources": ["MapBiomas"],
        "notes": "Bioma semiárido. Projetos de energia renovável são predominantes.",
    },
    "Pampa": {
        "risk_level": "low",
        "deforestation_baseline": "low",
        "monitoring_sources": ["MapBiomas"],
        "notes": "Bioma de campos nativos. Menor volume de projetos de carbono.",
    },
}


class BrazilAdapter(RegulatoryAdapter):
    """Regulatory adapter for Brazil — SINARE, biomes, and INPE stubs."""

    def validate_requirements(self, project_data: dict) -> dict:
        issues = []
        warnings = []

        # Check SINARE registration  
        sinare_id = project_data.get("sinare_id")
        if not sinare_id:
            warnings.append({
                "code": "BR_SINARE_MISSING",
                "message": "Projeto sem registro no SINARE. Quando o mercado regulado brasileiro entrar em vigor, o registro será obrigatório.",
                "severity": "warning",
            })

        # Check biome information
        region = project_data.get("region", "")
        biome = self._detect_biome(region)
        if biome and biome in BRAZIL_BIOMES:
            biome_info = BRAZIL_BIOMES[biome]
            if biome_info["risk_level"] in ("critical", "high"):
                warnings.append({
                    "code": f"BR_BIOME_{biome_info['risk_level'].upper()}",
                    "message": f"Bioma {biome}: {biome_info['notes']}",
                    "severity": "info",
                    "monitoring_sources": biome_info["monitoring_sources"],
                })

        # Check project type compatibility
        project_type = project_data.get("project_type", "")
        if project_type in ("REDD+", "ARR") and not project_data.get("area_hectares"):
            issues.append({
                "code": "BR_AREA_REQUIRED",
                "message": "Projetos florestais no Brasil devem declarar área em hectares para validação via satélite.",
                "severity": "error",
            })

        return {
            "valid": len(issues) == 0,
            "jurisdiction": "BR",
            "issues": issues,
            "warnings": warnings,
        }

    def interpret_rating(self, rating_data: dict, project_data: dict) -> dict:
        context = {
            "jurisdiction": "BR",
            "market_type": "voluntary_transitioning",
            "regulatory_status": "Mercado regulado em formação (SINARE aprovado, implementação pendente)",
        }

        grade = rating_data.get("grade", "N/A")
        recommendations = []

        # Grade-specific recommendations for Brazil
        if grade in ("D", "C", "CC", "CCC"):
            recommendations.append(
                "No contexto brasileiro, créditos de baixa qualidade enfrentam risco adicional "
                "quando o mercado regulado entrar em vigor. Considere reforçar MRV e adicionalidade."
            )

        if project_data.get("project_type") in ("REDD+",):
            recommendations.append(
                "Para projetos REDD+ no Brasil, recomenda-se verificação cruzada com dados "
                "INPE/PRODES para validar linha de base de desmatamento."
            )

        region = project_data.get("region", "")
        biome = self._detect_biome(region)
        if biome:
            biome_info = BRAZIL_BIOMES.get(biome, {})
            recommendations.append(
                f"Bioma {biome}: nível de risco {biome_info.get('risk_level', 'N/A')}. "
                f"Fontes de monitoramento disponíveis: {', '.join(biome_info.get('monitoring_sources', []))}"
            )

        context["recommendations"] = recommendations
        context["grade_context"] = (
            f"Rating {grade} em contexto brasileiro: mercado voluntário com transição para regulado. "
            "Créditos de alta qualidade terão vantagem regulatória futura."
        )
        return context

    def get_regulatory_context(self) -> dict:
        return {
            "jurisdiction_code": "BR",
            "jurisdiction_name": "Brasil",
            "market_type": "Voluntário em transição para regulado",
            "key_regulations": [
                {"name": "SINARE", "status": "approved", "description": "Sistema Nacional de Registro de Emissões. Aprovado, implementação em andamento."},
                {"name": "Lei 14.590/2023", "status": "enacted", "description": "Institui o Mercado Brasileiro de Redução de Emissões (MBRE)."},
                {"name": "Decreto MBRE", "status": "pending", "description": "Regulamentação detalhada do MBRE. Esperado para 2025-2026."},
            ],
            "biomes_covered": list(BRAZIL_BIOMES.keys()),
            "compliance_frameworks": ["CSRD (para empresas com operações EU)", "SBTi (voluntário)"],
            "data_sources": {
                "INPE/PRODES": "Monitoramento anual de desmatamento por satélite",
                "INPE/DETER": "Alertas em tempo quase real de desmatamento",
                "MapBiomas": "Mapeamento anual de uso e cobertura do solo",
                "IBGE": "Dados geográficos e socioeconômicos",
                "SINARE": "Registro oficial de créditos (futuro)",
            },
            "risk_factors": [
                "Mercado regulado em formação — regras finais desconhecidas",
                "Alta pressão de desmatamento em Amazônia e Cerrado",
                "Complexidade fundiária e questões de FPIC com comunidades indígenas",
                "Incerteza sobre aceitação de créditos voluntários no mercado regulado",
            ],
        }

    def get_data_source_stubs(self) -> list[dict]:
        return [
            {
                "source": "INPE/PRODES",
                "type": "satellite_deforestation",
                "status": "stub",
                "endpoint_pattern": "http://terrabrasilis.dpi.inpe.br/api/v1/prodes/{biome}",
                "data_format": "GeoJSON",
                "refresh_frequency": "annual",
                "integration_ready": False,
                "description": "Dados anuais de desmatamento por bioma. Integração futura via API TerraBrasilis.",
            },
            {
                "source": "INPE/DETER",
                "type": "deforestation_alerts",
                "status": "stub",
                "endpoint_pattern": "http://terrabrasilis.dpi.inpe.br/api/v1/deter/{biome}",
                "data_format": "GeoJSON",
                "refresh_frequency": "weekly",
                "integration_ready": False,
                "description": "Alertas semanais de desmatamento. Útil para monitoramento contínuo de projetos REDD+.",
            },
            {
                "source": "MapBiomas",
                "type": "land_use_cover",
                "status": "stub",
                "endpoint_pattern": "https://api.mapbiomas.org/v1/{collection}",
                "data_format": "GeoTIFF/JSON",
                "refresh_frequency": "annual",
                "integration_ready": False,
                "description": "Dados de uso e cobertura do solo 1985-present. Coleção 8+ disponível.",
            },
            {
                "source": "SINARE",
                "type": "credit_registry",
                "status": "not_available",
                "endpoint_pattern": "TBD",
                "data_format": "TBD",
                "refresh_frequency": "real_time",
                "integration_ready": False,
                "description": "Sistema Nacional de Registro de Emissões. API ainda não disponibilizada publicamente.",
            },
        ]

    def _detect_biome(self, region: str) -> Optional[str]:
        """Detect biome from region string using keyword matching."""
        if not region:
            return None
        region_lower = region.lower()
        biome_keywords = {
            "Amazônia": ["amazonia", "amazônia", "amazon", "norte", "pará", "amazonas", "rondônia", "acre", "roraima", "amapá", "tocantins"],
            "Cerrado": ["cerrado", "goiás", "goias", "mato grosso do sul", "distrito federal", "tocantins", "minas gerais"],
            "Mata Atlântica": ["mata atlântica", "mata atlantica", "atlantic forest", "são paulo", "rio de janeiro", "paraná", "santa catarina"],
            "Pantanal": ["pantanal", "mato grosso do sul"],
            "Caatinga": ["caatinga", "bahia", "pernambuco", "ceará", "piauí", "maranhão", "paraíba", "alagoas", "sergipe"],
            "Pampa": ["pampa", "rio grande do sul"],
        }
        for biome, keywords in biome_keywords.items():
            if any(kw in region_lower for kw in keywords):
                return biome
        return None


# ─── EU Adapter (minimal) ───────────────────────────────────────────────

class EUAdapter(RegulatoryAdapter):
    """Minimal EU regulatory adapter."""

    def validate_requirements(self, project_data: dict) -> dict:
        return {"valid": True, "jurisdiction": "EU", "issues": [], "warnings": []}

    def interpret_rating(self, rating_data: dict, project_data: dict) -> dict:
        return {
            "jurisdiction": "EU",
            "market_type": "regulated",
            "regulatory_status": "EU ETS ativo. CSRD obrigatório a partir de 2025.",
            "recommendations": ["CSRD compliance obrigatório para empresas abrangidas."],
            "grade_context": f"Rating {rating_data.get('grade', 'N/A')} no contexto EU ETS.",
        }

    def get_regulatory_context(self) -> dict:
        return {
            "jurisdiction_code": "EU",
            "jurisdiction_name": "União Europeia",
            "market_type": "Regulado (EU ETS)",
            "key_regulations": [
                {"name": "EU ETS", "status": "active", "description": "Sistema de comércio de emissões da UE."},
                {"name": "CSRD/ESRS", "status": "active", "description": "Diretiva de reporte de sustentabilidade corporativa."},
                {"name": "CBAM", "status": "transitional", "description": "Mecanismo de ajuste de fronteira de carbono."},
            ],
        }

    def get_data_source_stubs(self) -> list[dict]:
        return []


# ─── Adapter Registry ───────────────────────────────────────────────────

_ADAPTERS = {
    "BR": BrazilAdapter,
    "EU": EUAdapter,
}


def get_adapter(jurisdiction_code: str) -> Optional[RegulatoryAdapter]:
    """Get the regulatory adapter for a jurisdiction code."""
    adapter_class = _ADAPTERS.get(jurisdiction_code)
    return adapter_class() if adapter_class else None


def get_jurisdiction_summary(project, jurisdiction) -> dict:
    """Get a complete jurisdiction summary for a project.
    
    Args:
        project: CarbonProject model instance
        jurisdiction: Jurisdiction model instance (or None)
    """
    country = project.country if project else "N/A"
    jur_code = jurisdiction.code if jurisdiction else None

    result = {
        "project_id": project.id if project else None,
        "project_name": project.name if project else "N/A",
        "country": country,
        "jurisdiction_code": jur_code,
        "jurisdiction_name": jurisdiction.name if jurisdiction else "Desconhecida",
        "jurisdiction_region": jurisdiction.region if jurisdiction else None,
        "has_adapter": False,
        "regulatory_context": None,
        "validation": None,
        "rating_interpretation": None,
        "data_sources": [],
    }

    if not jur_code:
        return result

    adapter = get_adapter(jur_code)
    if not adapter:
        result["regulatory_context"] = {
            "jurisdiction_code": jur_code,
            "market_type": "unknown",
            "message": f"Adaptador regulatório para '{jur_code}' ainda não implementado.",
        }
        return result

    result["has_adapter"] = True

    # Build project data dict
    project_data = {
        "name": project.name,
        "project_type": project.project_type.value if hasattr(project.project_type, 'value') else str(project.project_type),
        "country": project.country,
        "region": project.region,
        "area_hectares": project.area_hectares,
        "sinare_id": getattr(project, 'sinare_id', None),
        "registry": project.registry,
        "methodology": project.methodology,
    }

    rating_data = {}
    if hasattr(project, 'rating') and project.rating:
        r = project.rating
        rating_data = {
            "grade": r.grade.value if hasattr(r.grade, 'value') else str(r.grade),
            "overall_score": r.overall_score,
            "discount_factor": r.discount_factor,
        }

    result["regulatory_context"] = adapter.get_regulatory_context()
    result["validation"] = adapter.validate_requirements(project_data)
    result["rating_interpretation"] = adapter.interpret_rating(rating_data, project_data)
    result["data_sources"] = adapter.get_data_source_stubs()

    return result
