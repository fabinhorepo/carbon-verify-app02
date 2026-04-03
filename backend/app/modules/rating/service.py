"""Rating Engine v3 — Carbon Verify Production.

Inspired by Sylvera, BeZero, Calyx Global:
- AAA-D scale with 7 core pillars
- Methodology-specific scoring logic
- Risk-adjusted discount factors
- Dynamic pillar support via RatingPillar
"""
from app.models.models import (
    CarbonProject, ProjectRating, RatingPillar, RatingGrade
)

# ─── Weights & Boundaries ───────────────────────────────────────────────

PILLAR_WEIGHTS = {
    "carbon_integrity": 0.18,
    "additionality": 0.18,
    "permanence": 0.16,
    "leakage": 0.12,
    "mrv": 0.14,
    "co_benefits": 0.12,
    "governance": 0.10,
}

GRADE_BOUNDARIES = [
    (90, RatingGrade.AAA), (80, RatingGrade.AA), (70, RatingGrade.A),
    (60, RatingGrade.BBB), (50, RatingGrade.BB), (40, RatingGrade.B),
    (30, RatingGrade.CCC), (20, RatingGrade.CC), (10, RatingGrade.C),
    (0, RatingGrade.D),
]

# Risk-adjusted discount factors per grade (BeZero-style)
GRADE_DISCOUNT_FACTORS = {
    "AAA": 1.00, "AA": 0.95, "A": 0.85, "BBB": 0.70, "BB": 0.55,
    "B": 0.40, "CCC": 0.25, "CC": 0.15, "C": 0.08, "D": 0.02,
}

# Base scores per project type (methodology-specific)
BASE_SCORES = {
    "REDD+": {"carbon_integrity": 35, "additionality": 35, "permanence": 30, "leakage": 30, "mrv": 35, "co_benefits": 45, "governance": 30},
    "ARR": {"carbon_integrity": 40, "additionality": 40, "permanence": 35, "leakage": 35, "mrv": 40, "co_benefits": 50, "governance": 35},
    "Renewable Energy": {"carbon_integrity": 45, "additionality": 30, "permanence": 50, "leakage": 50, "mrv": 45, "co_benefits": 25, "governance": 40},
    "Cookstove": {"carbon_integrity": 35, "additionality": 35, "permanence": 40, "leakage": 45, "mrv": 30, "co_benefits": 50, "governance": 30},
    "Methane Avoidance": {"carbon_integrity": 50, "additionality": 45, "permanence": 50, "leakage": 55, "mrv": 40, "co_benefits": 30, "governance": 35},
    "Blue Carbon": {"carbon_integrity": 38, "additionality": 40, "permanence": 30, "leakage": 30, "mrv": 30, "co_benefits": 55, "governance": 30},
    "Biochar": {"carbon_integrity": 50, "additionality": 50, "permanence": 55, "leakage": 60, "mrv": 40, "co_benefits": 30, "governance": 35},
    "Direct Air Capture": {"carbon_integrity": 60, "additionality": 60, "permanence": 65, "leakage": 65, "mrv": 50, "co_benefits": 20, "governance": 40},
    "Other": {"carbon_integrity": 25, "additionality": 25, "permanence": 25, "leakage": 25, "mrv": 25, "co_benefits": 25, "governance": 25},
}

REGISTRY_MODS = {"Verra": 5, "Gold Standard": 8, "ACR": 4, "CAR": 4, "Plan Vivo": 6}

DEVELOPING_COUNTRIES = [
    "Brazil", "India", "Indonesia", "Kenya", "Colombia", "Peru", "Congo",
    "Ethiopia", "Vietnam", "Cambodia", "Uganda", "Rwanda", "Ghana",
    "Tanzania", "Mozambique", "Bangladesh", "Nepal", "Honduras", "Mexico",
    "Zambia", "Philippines", "Guatemala", "Madagascar", "Myanmar",
    "Chile", "Argentina", "Ecuador", "Bolivia", "Paraguay", "Uruguay",
    "Costa Rica", "Panama", "Dominican Republic",
]

RISK_FLAG_DETAILS = {
    "permanence_risk": {
        "description": "Risco de reversão do carbono sequestrado.",
        "recommendation": "Exigir buffer pool mínimo de 15-20%, monitoramento remoto contínuo.",
    },
    "leakage_risk": {
        "description": "Emissões deslocadas para outras áreas.",
        "recommendation": "Ampliar monitoramento para zonas de buffer, descontos conservadores.",
    },
    "additionality_concern": {
        "description": "Projeto pode ter sido implementado sem créditos.",
        "recommendation": "Documentar análise de barreiras, validação por terceiros.",
    },
    "mrv_weakness": {
        "description": "Sistema MRV insuficiente.",
        "recommendation": "Monitoramento semestral, sensoriamento remoto, verificadores credenciados.",
    },
    "governance_concern": {
        "description": "Falta de transparência e documentação.",
        "recommendation": "Documentação completa, FPIC, auditorias regulares.",
    },
    "overcrediting_risk": {
        "description": "Créditos/hectare acima do esperado para o tipo de projeto.",
        "recommendation": "Auditoria independente, comparar com benchmarks.",
    },
    "no_registry": {
        "description": "Sem registro em padrão reconhecido.",
        "recommendation": "Exigir registro antes de aquisição.",
    },
    "carbon_integrity_low": {
        "description": "Baixa integridade na quantificação do carbono.",
        "recommendation": "Revisão independente da linha de base e cálculos.",
    },
}


def _clamp(v: float) -> float:
    return min(100.0, max(0.0, v))


# ─── Individual Pillar Scorers ──────────────────────────────────────────

def _score_carbon_integrity(p: CarbonProject, base: float) -> float:
    """Carbon Integrity / Carbon Impact - core Sylvera/BeZero pillar."""
    s = base
    if p.baseline_scenario:
        tl = len(p.baseline_scenario)
        s += 25 if tl > 300 else 15 if tl > 100 else 8 if tl > 30 else 0
    else:
        s -= 15
    if p.total_credits_issued and p.area_hectares and p.area_hectares > 0:
        cph = p.total_credits_issued / p.area_hectares
        s += -15 if cph > 50 else -5 if cph > 30 else 5 if cph < 5 else 0
    s += 5 if p.methodology else -5
    return _clamp(s)


def _score_additionality(p: CarbonProject, base: float) -> float:
    s = base
    if p.additionality_justification:
        tl = len(p.additionality_justification)
        s += 30 if tl > 300 else 20 if tl > 100 else 10 if tl > 30 else 0
    else:
        s -= 15
    s += 10 if p.methodology else -10
    return _clamp(s)


def _score_permanence(p: CarbonProject, base: float) -> float:
    s = base
    if p.buffer_pool_percentage:
        s += 25 if p.buffer_pool_percentage >= 20 else 20 if p.buffer_pool_percentage >= 15 else 15 if p.buffer_pool_percentage >= 10 else 8 if p.buffer_pool_percentage >= 5 else -5
    else:
        pt = p.project_type if isinstance(p.project_type, str) else p.project_type.value
        if pt in ("REDD+", "ARR", "Blue Carbon"):
            s -= 10
    if p.end_date and p.start_date:
        dy = (p.end_date - p.start_date).days / 365
        s += 15 if dy >= 30 else 10 if dy >= 20 else 5 if dy >= 10 else -5
    return _clamp(s)


def _score_leakage(p: CarbonProject, base: float) -> float:
    s = base
    if p.area_hectares:
        s += -5 if p.area_hectares > 100000 else 5 if p.area_hectares < 1000 else 0
    if p.baseline_scenario:
        tl = len(p.baseline_scenario)
        s += 15 if tl > 200 else 8 if tl > 50 else 0
    else:
        s -= 10
    s += 5 if p.methodology else 0
    return _clamp(s)


def _score_mrv(p: CarbonProject, base: float) -> float:
    s = base
    if p.monitoring_frequency:
        f = p.monitoring_frequency.lower()
        if any(x in f for x in ["quarterly", "trimestral"]):
            s += 30
        elif any(x in f for x in ["biannual", "semestral"]):
            s += 25
        elif any(x in f for x in ["annual", "anual"]):
            s += 15
    else:
        s -= 15
    s += 10 if p.methodology else -10
    return _clamp(s)


def _score_co_benefits(p: CarbonProject, base: float) -> float:
    """Beyond Carbon / Co-benefits — aligned with Calyx Global."""
    s = base
    if p.country in DEVELOPING_COUNTRIES:
        s += 10
    if p.description and len(p.description) > 200:
        s += 10
    elif p.description and len(p.description) > 50:
        s += 5
    else:
        s -= 5
    if p.sdg_contributions:
        sdg_count = len(p.sdg_contributions) if isinstance(p.sdg_contributions, (list, dict)) else 0
        s += min(15, sdg_count * 3)
    return _clamp(s)


def _score_governance(p: CarbonProject, base: float) -> float:
    s = base
    s += 10 if p.proponent else -15
    s += REGISTRY_MODS.get(p.registry, 0) if p.registry else 0
    s += 5 if p.external_id else 0
    s += 5 if p.methodology else -10
    return _clamp(s)


def _get_grade(score: float) -> RatingGrade:
    for threshold, grade in GRADE_BOUNDARIES:
        if score >= threshold:
            return grade
    return RatingGrade.D


def _gen_explanation(p: CarbonProject, scores: dict, grade: RatingGrade) -> str:
    strengths = [f"{d.replace('_', ' ').title()} ({s:.0f}/100)" for d, s in scores.items() if s >= 75]
    weaknesses = [f"{d.replace('_', ' ').title()} ({s:.0f}/100)" for d, s in scores.items() if s < 50]
    exp = f"Projeto '{p.name}' recebeu rating {grade.value} com base em 7 pilares. "
    if strengths:
        exp += f"Pontos fortes: {', '.join(strengths)}. "
    if weaknesses:
        exp += f"Áreas de atenção: {', '.join(weaknesses)}. "
    return exp


def _gen_risk_flags(p: CarbonProject, scores: dict) -> list:
    flags = []
    checks = [
        ("permanence", 40, "permanence_risk", "high", "Alto risco de reversão"),
        ("leakage", 40, "leakage_risk", "high", "Risco de vazamento de emissões"),
        ("additionality", 40, "additionality_concern", "high", "Adicionalidade questionável"),
        ("mrv", 50, "mrv_weakness", "medium", "Sistema MRV insuficiente"),
        ("governance", 40, "governance_concern", "medium", "Governança precisa de atenção"),
        ("carbon_integrity", 40, "carbon_integrity_low", "high", "Integridade de carbono baixa"),
    ]
    for dim, threshold, flag_type, sev, msg in checks:
        if scores.get(dim, 100) < threshold:
            d = RISK_FLAG_DETAILS[flag_type]
            flags.append({
                "type": flag_type, "severity": sev, "message": msg,
                "description": d["description"], "recommendation": d["recommendation"],
            })
    if p.total_credits_issued and p.area_hectares:
        ratio = p.total_credits_issued / max(p.area_hectares, 1)
        if ratio > 50:
            d = RISK_FLAG_DETAILS["overcrediting_risk"]
            flags.append({
                "type": "overcrediting_risk", "severity": "high",
                "message": f"Taxa créditos/ha ({ratio:.1f}) elevada",
                "description": d["description"], "recommendation": d["recommendation"],
            })
    if not p.registry:
        d = RISK_FLAG_DETAILS["no_registry"]
        flags.append({
            "type": "no_registry", "severity": "medium",
            "message": "Sem registro em padrão",
            "description": d["description"], "recommendation": d["recommendation"],
        })
    return flags


def calculate_rating(project: CarbonProject) -> tuple[ProjectRating, list[RatingPillar]]:
    """Calculate full rating with pillars and discount factor.

    Returns:
        tuple of (ProjectRating, list[RatingPillar])
    """
    ptk = project.project_type if isinstance(project.project_type, str) else project.project_type.value
    base = BASE_SCORES.get(ptk, BASE_SCORES["Other"])

    scores = {
        "carbon_integrity": _score_carbon_integrity(project, base["carbon_integrity"]),
        "additionality": _score_additionality(project, base["additionality"]),
        "permanence": _score_permanence(project, base["permanence"]),
        "leakage": _score_leakage(project, base["leakage"]),
        "mrv": _score_mrv(project, base["mrv"]),
        "co_benefits": _score_co_benefits(project, base["co_benefits"]),
        "governance": _score_governance(project, base["governance"]),
    }

    overall = sum(scores[d] * w for d, w in PILLAR_WEIGHTS.items())
    grade = _get_grade(overall)
    discount_factor = GRADE_DISCOUNT_FACTORS.get(grade.value, 0.5)

    # Confidence based on data completeness
    fields = [
        project.methodology, project.registry, project.baseline_scenario,
        project.additionality_justification, project.monitoring_frequency,
        project.buffer_pool_percentage, project.area_hectares, project.proponent,
        project.external_id, project.description,
    ]
    confidence = sum(1 for f in fields if f) / len(fields)

    rating = ProjectRating(
        project_id=project.id,
        overall_score=round(overall, 2),
        grade=grade,
        carbon_integrity_score=round(scores["carbon_integrity"], 2),
        additionality_score=round(scores["additionality"], 2),
        permanence_score=round(scores["permanence"], 2),
        leakage_score=round(scores["leakage"], 2),
        mrv_score=round(scores["mrv"], 2),
        co_benefits_score=round(scores["co_benefits"], 2),
        governance_score=round(scores["governance"], 2),
        confidence_level=round(confidence, 2),
        discount_factor=discount_factor,
        explanation=_gen_explanation(project, scores, grade),
        risk_flags=_gen_risk_flags(project, scores),
    )

    pillars = [
        RatingPillar(
            pillar_name=name,
            score=round(score, 2),
            weight=PILLAR_WEIGHTS[name],
            methodology_specific=(name == "carbon_integrity"),
            details={"base_score": base[name], "final_score": round(score, 2)},
        )
        for name, score in scores.items()
    ]

    return rating, pillars
