"""Motor de Fraud Detection v2 - Carbon Verify Produção."""
from datetime import datetime, timezone
from typing import Optional
from app.models.models import CarbonProject, FraudAlert, FraudSeverity

MAX_CREDITS_PER_HA = {"REDD+": 30, "ARR": 25, "Renewable Energy": 100, "Cookstove": 50, "Methane Avoidance": 80, "Blue Carbon": 20, "Biochar": 40, "Direct Air Capture": 200, "Other": 50}


def _check_overcrediting(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.area_hectares or p.area_hectares <= 0 or not p.total_credits_issued or p.total_credits_issued <= 0:
        return None
    ptk = p.project_type if isinstance(p.project_type, str) else p.project_type.value
    max_ph = MAX_CREDITS_PER_HA.get(ptk, 50)
    actual = p.total_credits_issued / p.area_hectares
    if actual > max_ph:
        ratio = actual / max_ph
        sev = FraudSeverity.CRITICAL if ratio > 3 else FraudSeverity.HIGH if ratio > 2 else FraudSeverity.MEDIUM
        return FraudAlert(project_id=p.id, alert_type="overcrediting", severity=sev,
                         title="Possível over-crediting detectado",
                         description=f"Emitiu {actual:.1f} créditos/ha, máximo esperado {max_ph} ({ratio:.1f}x acima).",
                         evidence={"credits_per_ha": round(actual, 2), "max_expected": max_ph, "ratio": round(ratio, 2)},
                         recommendation="Revisar metodologia de cálculo.", detection_method="rule_based",
                         confidence=min(0.95, 0.5 + (ratio - 1) * 0.2))
    return None


def _check_area(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.area_hectares:
        return FraudAlert(project_id=p.id, alert_type="missing_area", severity=FraudSeverity.LOW,
                         title="Área não declarada", description="Sem informação de área.",
                         evidence={"area_hectares": None}, recommendation="Solicitar documentação.",
                         detection_method="rule_based", confidence=0.3)
    if p.area_hectares > 10_000_000:
        return FraudAlert(project_id=p.id, alert_type="area_anomaly", severity=FraudSeverity.HIGH,
                         title="Área anormalmente grande", description=f"Área de {p.area_hectares:,.0f} ha.",
                         evidence={"area_hectares": p.area_hectares}, recommendation="Verificar coordenadas.",
                         detection_method="rule_based", confidence=0.7)
    return None


def _check_vintage(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.vintage_year:
        return None
    age = datetime.utcnow().year - p.vintage_year
    if age > 10:
        sev = FraudSeverity.HIGH if age > 15 else FraudSeverity.MEDIUM
        return FraudAlert(project_id=p.id, alert_type="vintage_age", severity=sev,
                         title="Vintage muito antigo", description=f"Vintage {p.vintage_year} ({age} anos).",
                         evidence={"vintage_year": p.vintage_year, "age": age},
                         recommendation="Avaliar condições atuais.", detection_method="rule_based", confidence=0.6)
    return None


def _check_buffer(p: CarbonProject) -> Optional[FraudAlert]:
    ptk = p.project_type if isinstance(p.project_type, str) else p.project_type.value
    if ptk not in ("REDD+", "ARR", "Blue Carbon", "Biochar"):
        return None
    if not p.buffer_pool_percentage or p.buffer_pool_percentage < 5:
        return FraudAlert(project_id=p.id, alert_type="insufficient_buffer", severity=FraudSeverity.MEDIUM,
                         title="Buffer insuficiente", description=f"Buffer: {p.buffer_pool_percentage or 0}% (mínimo 5%).",
                         evidence={"buffer": p.buffer_pool_percentage, "min": 5},
                         recommendation="Verificar exigências do padrão.", detection_method="rule_based", confidence=0.65)
    return None


def _check_retirement(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.total_credits_issued or p.total_credits_issued == 0:
        return None
    rate = p.total_credits_retired / p.total_credits_issued
    if rate > 0.90 and p.total_credits_issued > 10000:
        return FraudAlert(project_id=p.id, alert_type="retirement_anomaly", severity=FraudSeverity.MEDIUM,
                         title="Taxa de aposentadoria anômala", description=f"{rate*100:.1f}% aposentados.",
                         evidence={"rate": round(rate, 4), "issued": p.total_credits_issued, "retired": p.total_credits_retired},
                         recommendation="Verificar histórico de transações.", detection_method="rule_based", confidence=0.5)
    return None


def _check_governance(p: CarbonProject) -> Optional[FraudAlert]:
    missing = []
    if not p.registry: missing.append("registro")
    if not p.methodology: missing.append("metodologia")
    if not p.proponent: missing.append("proponente")
    if not p.external_id: missing.append("ID externo")
    if not p.monitoring_frequency: missing.append("monitoramento")
    if len(missing) >= 3:
        sev = FraudSeverity.MEDIUM if len(missing) < 4 else FraudSeverity.HIGH
        return FraudAlert(project_id=p.id, alert_type="governance_gaps", severity=sev,
                         title="Lacunas de governança", description=f"{len(missing)} campos ausentes: {', '.join(missing)}.",
                         evidence={"missing": missing, "count": len(missing)},
                         recommendation="Solicitar documentação completa.", detection_method="rule_based", confidence=0.7)
    return None


def run_fraud_detection(project: CarbonProject) -> list[FraudAlert]:
    checks = [_check_overcrediting, _check_area, _check_vintage, _check_buffer, _check_retirement, _check_governance]
    return [a for check in checks if (a := check(project)) is not None]
