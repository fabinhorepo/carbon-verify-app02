"""Motor de Rating de Qualidade v2 - Carbon Verify Produção."""
from app.models.models import CarbonProject, ProjectRating, RatingGrade

DIMENSION_WEIGHTS = {
    "additionality": 0.20, "permanence": 0.18, "baseline_integrity": 0.15,
    "leakage": 0.12, "mrv": 0.15, "co_benefits": 0.10, "governance": 0.10,
}

GRADE_BOUNDARIES = [
    (90, RatingGrade.AAA), (80, RatingGrade.AA), (70, RatingGrade.A),
    (60, RatingGrade.BBB), (50, RatingGrade.BB), (40, RatingGrade.B),
    (30, RatingGrade.CCC), (20, RatingGrade.CC), (10, RatingGrade.C), (0, RatingGrade.D),
]

BASE_SCORES = {
    "REDD+": {"additionality": 35, "permanence": 30, "leakage": 30, "mrv": 35, "co_benefits": 45, "governance": 30, "baseline_integrity": 35},
    "ARR": {"additionality": 40, "permanence": 35, "leakage": 35, "mrv": 40, "co_benefits": 50, "governance": 35, "baseline_integrity": 40},
    "Renewable Energy": {"additionality": 30, "permanence": 50, "leakage": 50, "mrv": 45, "co_benefits": 25, "governance": 40, "baseline_integrity": 40},
    "Cookstove": {"additionality": 35, "permanence": 40, "leakage": 45, "mrv": 30, "co_benefits": 50, "governance": 30, "baseline_integrity": 35},
    "Methane Avoidance": {"additionality": 45, "permanence": 50, "leakage": 55, "mrv": 40, "co_benefits": 30, "governance": 35, "baseline_integrity": 45},
    "Blue Carbon": {"additionality": 40, "permanence": 30, "leakage": 30, "mrv": 30, "co_benefits": 55, "governance": 30, "baseline_integrity": 35},
    "Biochar": {"additionality": 50, "permanence": 55, "leakage": 60, "mrv": 40, "co_benefits": 30, "governance": 35, "baseline_integrity": 45},
    "Direct Air Capture": {"additionality": 60, "permanence": 65, "leakage": 65, "mrv": 50, "co_benefits": 20, "governance": 40, "baseline_integrity": 55},
    "Other": {"additionality": 25, "permanence": 25, "leakage": 25, "mrv": 25, "co_benefits": 25, "governance": 25, "baseline_integrity": 25},
}

REGISTRY_MODS = {"Verra": 5, "Gold Standard": 8, "ACR": 4, "CAR": 4, "Plan Vivo": 6}

RISK_FLAG_DETAILS = {
    "permanence_risk": {"description": "Risco de reversão do carbono sequestrado.", "recommendation": "Exigir buffer pool mínimo de 15-20%, monitoramento remoto contínuo."},
    "leakage_risk": {"description": "Emissões deslocadas para outras áreas.", "recommendation": "Ampliar monitoramento para zonas de buffer, descontos conservadores."},
    "additionality_concern": {"description": "Projeto pode ter sido implementado sem créditos.", "recommendation": "Documentar análise de barreiras, validação por terceiros."},
    "mrv_weakness": {"description": "Sistema MRV insuficiente.", "recommendation": "Monitoramento semestral, sensoriamento remoto, verificadores credenciados."},
    "governance_concern": {"description": "Falta de transparência e documentação.", "recommendation": "Documentação completa, FPIC, auditorias regulares."},
    "overcrediting_risk": {"description": "Créditos/hectare acima do esperado.", "recommendation": "Auditoria independente, comparar com benchmarks."},
    "no_registry": {"description": "Sem registro em padrão reconhecido.", "recommendation": "Exigir registro antes de aquisição."},
}


def _clamp(v): return min(100, max(0, v))


def _score_additionality(p, base):
    s = base
    if p.additionality_justification:
        tl = len(p.additionality_justification)
        s += 30 if tl > 300 else 20 if tl > 100 else 10 if tl > 30 else 0
    else:
        s -= 15
    s += 10 if p.methodology else -10
    return _clamp(s)


def _score_permanence(p, base):
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


def _score_leakage(p, base):
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


def _score_mrv(p, base):
    s = base
    if p.monitoring_frequency:
        f = p.monitoring_frequency.lower()
        s += 30 if any(x in f for x in ["quarterly", "trimestral"]) else 25 if any(x in f for x in ["biannual", "semestral"]) else 15 if any(x in f for x in ["annual", "anual"]) else 0
    else:
        s -= 15
    s += 10 if p.methodology else -10
    return _clamp(s)


def _score_co_benefits(p, base):
    s = base
    developing = ["Brazil", "India", "Indonesia", "Kenya", "Colombia", "Peru", "Congo", "Ethiopia", "Vietnam", "Cambodia", "Uganda", "Rwanda", "Ghana", "Tanzania", "Mozambique", "Bangladesh", "Nepal", "Honduras", "Mexico", "Zambia", "Philippines", "Guatemala", "Madagascar", "Myanmar"]
    if p.country in developing:
        s += 10
    if p.description and len(p.description) > 200:
        s += 10
    elif p.description and len(p.description) > 50:
        s += 5
    else:
        s -= 5
    return _clamp(s)


def _score_governance(p, base):
    s = base
    s += 10 if p.proponent else -15
    s += REGISTRY_MODS.get(p.registry, 0)
    s += 5 if p.external_id else 0
    s += 5 if p.methodology else -10
    return _clamp(s)


def _score_baseline(p, base):
    s = base
    if p.baseline_scenario:
        tl = len(p.baseline_scenario)
        s += 25 if tl > 300 else 15 if tl > 100 else 8 if tl > 30 else 0
    else:
        s -= 15
    if p.total_credits_issued and p.area_hectares:
        cph = p.total_credits_issued / p.area_hectares
        s += -15 if cph > 50 else -5 if cph > 30 else 5 if cph < 5 else 0
    s += 5 if p.methodology else 0
    return _clamp(s)


def _get_grade(score):
    for threshold, grade in GRADE_BOUNDARIES:
        if score >= threshold:
            return grade
    return RatingGrade.D


def _gen_explanation(p, ss, grade):
    strengths = [f"{d.replace('_', ' ').title()} ({s:.0f}/100)" for d, s in ss.items() if s >= 75]
    weaknesses = [f"{d.replace('_', ' ').title()} ({s:.0f}/100)" for d, s in ss.items() if s < 50]
    exp = f"Projeto '{p.name}' recebeu rating {grade.value} com base em 7 dimensões. "
    if strengths:
        exp += f"Pontos fortes: {', '.join(strengths)}. "
    if weaknesses:
        exp += f"Áreas de atenção: {', '.join(weaknesses)}. "
    return exp


def _gen_risk_flags(p, ss):
    flags = []
    checks = [("permanence", 40, "permanence_risk", "high", "Alto risco de reversão"),
              ("leakage", 40, "leakage_risk", "high", "Risco de vazamento de emissões"),
              ("additionality", 40, "additionality_concern", "high", "Adicionalidade questionável"),
              ("mrv", 50, "mrv_weakness", "medium", "Sistema MRV insuficiente"),
              ("governance", 40, "governance_concern", "medium", "Governança precisa de atenção")]
    for dim, threshold, flag_type, sev, msg in checks:
        if ss[dim] < threshold:
            d = RISK_FLAG_DETAILS[flag_type]
            flags.append({"type": flag_type, "severity": sev, "message": msg, "description": d["description"], "recommendation": d["recommendation"]})
    if p.total_credits_issued and p.area_hectares:
        ratio = p.total_credits_issued / max(p.area_hectares, 1)
        if ratio > 50:
            d = RISK_FLAG_DETAILS["overcrediting_risk"]
            flags.append({"type": "overcrediting_risk", "severity": "high", "message": f"Taxa créditos/ha ({ratio:.1f}) elevada", "description": d["description"], "recommendation": d["recommendation"]})
    if not p.registry:
        d = RISK_FLAG_DETAILS["no_registry"]
        flags.append({"type": "no_registry", "severity": "medium", "message": "Sem registro em padrão", "description": d["description"], "recommendation": d["recommendation"]})
    return flags


def calculate_rating(project: CarbonProject) -> ProjectRating:
    ptk = project.project_type if isinstance(project.project_type, str) else project.project_type.value
    base = BASE_SCORES.get(ptk, BASE_SCORES["Other"])
    ss = {
        "additionality": _score_additionality(project, base["additionality"]),
        "permanence": _score_permanence(project, base["permanence"]),
        "leakage": _score_leakage(project, base["leakage"]),
        "mrv": _score_mrv(project, base["mrv"]),
        "co_benefits": _score_co_benefits(project, base["co_benefits"]),
        "governance": _score_governance(project, base["governance"]),
        "baseline_integrity": _score_baseline(project, base["baseline_integrity"]),
    }
    overall = sum(ss[d] * w for d, w in DIMENSION_WEIGHTS.items())
    grade = _get_grade(overall)
    fields = [project.methodology, project.registry, project.baseline_scenario, project.additionality_justification,
              project.monitoring_frequency, project.buffer_pool_percentage, project.area_hectares, project.proponent,
              project.external_id, project.description]
    confidence = sum(1 for f in fields if f) / len(fields)
    return ProjectRating(
        project_id=project.id, overall_score=round(overall, 2), grade=grade,
        additionality_score=round(ss["additionality"], 2), permanence_score=round(ss["permanence"], 2),
        leakage_score=round(ss["leakage"], 2), mrv_score=round(ss["mrv"], 2),
        co_benefits_score=round(ss["co_benefits"], 2), governance_score=round(ss["governance"], 2),
        baseline_integrity_score=round(ss["baseline_integrity"], 2),
        confidence_level=round(confidence, 2), explanation=_gen_explanation(project, ss, grade),
        risk_flags=_gen_risk_flags(project, ss),
    )
