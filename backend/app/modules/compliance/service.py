"""Compliance Service — CSRD/ESRS, SBTi, ICVCM mapping.

Maps carbon credits and portfolios to compliance disclosure items.
Generates evidence trails and export packages.
"""
from typing import Optional

# ─── CSRD / ESRS E1 Disclosure Items ────────────────────────────────────

ESRS_E1_DISCLOSURES = {
    "E1-1": {
        "title": "Transition plan for climate change mitigation",
        "description": "Plano de transição climática incluindo estratégia de offsets.",
        "required_evidence": ["portfolio_summary", "offset_strategy", "timeline"],
    },
    "E1-5": {
        "title": "Energy consumption and mix",
        "description": "Consumo e mix energético. Relação com projetos de energia renovável.",
        "required_evidence": ["energy_data", "renewable_credits", "methodology"],
    },
    "E1-7": {
        "title": "GHG removals and carbon credits",
        "description": "Remoções de GHG e uso de créditos de carbono para compensação.",
        "required_evidence": ["credit_details", "registry_proof", "rating", "vintage_data"],
    },
    "E1-9": {
        "title": "Anticipated financial effects from climate risks",
        "description": "Efeitos financeiros antecipados de riscos climáticos. Inclui valoração de créditos.",
        "required_evidence": ["risk_assessment", "financial_impact", "portfolio_valuation"],
    },
}

SBTI_REQUIREMENTS = {
    "beyond_value_chain": {
        "title": "Beyond Value Chain Mitigation (BVCM)",
        "description": "Créditos usados para BVCM devem atender critérios de qualidade SBTi.",
        "criteria": ["high_quality_only", "no_avoidance_double_counting", "transparent_reporting"],
        "min_rating": "BBB",
    },
    "neutralization": {
        "title": "Neutralization claims",
        "description": "Apenas créditos de remoção (não evitação) para claims de neutralização.",
        "criteria": ["removal_only", "permanent", "verified"],
        "min_rating": "A",
    },
}

ICVCM_CORE_CARBON_PRINCIPLES = {
    "additionality": {
        "title": "Additionality",
        "description": "Reduções/remoções não teriam ocorrido sem o projeto.",
        "pillar_link": "additionality",
    },
    "permanence": {
        "title": "Permanence",
        "description": "Permanência das reduções/remoções de GHG.",
        "pillar_link": "permanence",
    },
    "robust_quantification": {
        "title": "Robust quantification",
        "description": "Quantificação robusta e conservadora.",
        "pillar_link": "carbon_integrity",
    },
    "no_double_counting": {
        "title": "No double counting",
        "description": "Sem dupla contagem por NDCs ou outros mecanismos.",
        "pillar_link": "governance",
    },
    "sustainable_development": {
        "title": "Sustainable development impacts",
        "description": "Impactos positivos em desenvolvimento sustentável.",
        "pillar_link": "co_benefits",
    },
}


def map_project_to_csrd(project_data: dict, rating_data: dict) -> list[dict]:
    """Map a single project to CSRD/ESRS E1 disclosure items."""
    mappings = []

    for code, disclosure in ESRS_E1_DISCLOSURES.items():
        coverage = _calculate_coverage(code, project_data, rating_data)
        status = "verified" if coverage >= 80 else "mapped" if coverage >= 40 else "gap"

        evidence_summary = _generate_evidence_summary(code, project_data, rating_data)

        mappings.append({
            "disclosure_item": code,
            "disclosure_title": disclosure["title"],
            "description": disclosure["description"],
            "status": status,
            "coverage_pct": coverage,
            "required_evidence": disclosure["required_evidence"],
            "evidence_summary": evidence_summary,
            "details": {
                "project_name": project_data.get("name", ""),
                "project_type": project_data.get("project_type", ""),
                "rating_grade": rating_data.get("grade", "N/A"),
                "registry": project_data.get("registry", "N/A"),
            },
        })

    return mappings


def map_project_to_sbti(project_data: dict, rating_data: dict) -> list[dict]:
    """Map project to SBTi requirements."""
    mappings = []
    grade = rating_data.get("grade", "D")

    for req_key, req in SBTI_REQUIREMENTS.items():
        grade_ok = _grade_meets_minimum(grade, req.get("min_rating", "D"))
        status = "compliant" if grade_ok else "non_compliant"
        coverage = 100 if grade_ok else 30

        mappings.append({
            "requirement": req_key,
            "title": req["title"],
            "description": req["description"],
            "status": status,
            "coverage_pct": coverage,
            "min_rating_required": req.get("min_rating", "D"),
            "current_rating": grade,
            "meets_minimum": grade_ok,
        })

    return mappings


def map_project_to_icvcm(project_data: dict, rating_data: dict) -> list[dict]:
    """Map project to ICVCM Core Carbon Principles."""
    mappings = []

    for principle_key, principle in ICVCM_CORE_CARBON_PRINCIPLES.items():
        pillar = principle.get("pillar_link", "")
        score_key = f"{pillar}_score"
        score = rating_data.get(score_key, 0)
        status = "met" if score >= 60 else "partially_met" if score >= 40 else "not_met"

        mappings.append({
            "principle": principle_key,
            "title": principle["title"],
            "description": principle["description"],
            "status": status,
            "pillar_score": score,
            "pillar_name": pillar,
        })

    return mappings


def _calculate_coverage(disclosure_code: str, project: dict, rating: dict) -> float:
    """Calculate evidence coverage percentage for a disclosure item."""
    coverage_checks = {
        "E1-1": [
            bool(project.get("description")),
            bool(project.get("methodology")),
            bool(rating.get("grade")),
        ],
        "E1-5": [
            project.get("project_type") in ("Renewable Energy", "Cookstove"),
            bool(project.get("methodology")),
            bool(project.get("total_credits_issued")),
        ],
        "E1-7": [
            bool(project.get("registry")),
            bool(project.get("total_credits_issued")),
            bool(rating.get("grade")),
            bool(project.get("vintage_year")),
            bool(project.get("external_id")),
        ],
        "E1-9": [
            bool(rating.get("risk_flags")),
            bool(project.get("total_credits_issued")),
            bool(rating.get("discount_factor")),
        ],
    }

    checks = coverage_checks.get(disclosure_code, [])
    if not checks:
        return 0.0
    return round(sum(checks) / len(checks) * 100, 1)


def _generate_evidence_summary(disclosure_code: str, project: dict, rating: dict) -> str:
    """Generate human-readable evidence summary."""
    grade = rating.get("grade", "N/A")
    name = project.get("name", "Projeto")

    summaries = {
        "E1-1": f"Projeto '{name}' avaliado com rating {grade}. "
                f"Metodologia: {project.get('methodology', 'N/A')}.",
        "E1-5": f"Tipo: {project.get('project_type', 'N/A')}. "
                f"Créditos emitidos: {project.get('total_credits_issued', 0):,}.",
        "E1-7": f"Registry: {project.get('registry', 'N/A')}. "
                f"Vintage: {project.get('vintage_year', 'N/A')}. "
                f"Rating: {grade}. "
                f"Créditos: {project.get('total_credits_issued', 0):,} tCO2e.",
        "E1-9": f"Fator de desconto: {rating.get('discount_factor', 1.0):.0%}. "
                f"Risk flags: {len(rating.get('risk_flags', []))} identificados.",
    }
    return summaries.get(disclosure_code, f"Dados disponíveis para {name}.")


def _grade_meets_minimum(current: str, minimum: str) -> bool:
    """Check if current grade meets minimum requirement."""
    grade_order = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
    try:
        return grade_order.index(current) <= grade_order.index(minimum)
    except ValueError:
        return False


def get_compliance_summary(project_data: dict, rating_data: dict) -> dict:
    """Get unified compliance summary across all frameworks."""
    csrd = map_project_to_csrd(project_data, rating_data)
    sbti = map_project_to_sbti(project_data, rating_data)
    icvcm = map_project_to_icvcm(project_data, rating_data)

    csrd_coverage = sum(m["coverage_pct"] for m in csrd) / len(csrd) if csrd else 0
    sbti_compliant = sum(1 for m in sbti if m["status"] == "compliant")
    icvcm_met = sum(1 for m in icvcm if m["status"] == "met")

    return {
        "csrd_esrs": {
            "items": csrd,
            "avg_coverage": round(csrd_coverage, 1),
            "total_items": len(csrd),
            "verified": sum(1 for m in csrd if m["status"] == "verified"),
            "gaps": sum(1 for m in csrd if m["status"] == "gap"),
        },
        "sbti": {
            "items": sbti,
            "compliant": sbti_compliant,
            "total": len(sbti),
        },
        "icvcm": {
            "items": icvcm,
            "met": icvcm_met,
            "total": len(icvcm),
        },
        "overall_score": round(
            (csrd_coverage * 0.4 + (sbti_compliant / max(len(sbti), 1)) * 100 * 0.3
             + (icvcm_met / max(len(icvcm), 1)) * 100 * 0.3), 1
        ),
    }
