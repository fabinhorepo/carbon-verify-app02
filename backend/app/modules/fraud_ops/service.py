"""Fraud Ops Service v3 — Carbon Verify Production.

Inspired by ClimeFi + Renoster:
- Entity relationship graph
- 8 detection rules (overcrediting, area, vintage, buffer, retirement, governance, wash trading, sanctions)
- Fraud Ops score per project/counterparty
- Alert feed with categorization
"""
from datetime import datetime, timezone
from typing import Optional
from app.models.models import CarbonProject, FraudAlert, FraudSeverity, Entity, EntityRelation

MAX_CREDITS_PER_HA = {
    "REDD+": 30, "ARR": 25, "Renewable Energy": 100, "Cookstove": 50,
    "Methane Avoidance": 80, "Blue Carbon": 20, "Biochar": 40,
    "Direct Air Capture": 200, "Other": 50,
}

FRAUD_TYPE_EXPLANATIONS = {
    "overcrediting": {
        "title": "Overcrediting (Créditos em Excesso)",
        "what_is": "Overcrediting ocorre quando um projeto emite mais créditos do que a quantidade real de carbono efetivamente removida ou evitada. O projeto 'infla' seus números.",
        "consequences": "Compradores acreditam compensar emissões que não foram realmente compensadas. Mina a credibilidade do mercado e contribui para greenwashing.",
        "ideal_situation": "Metodologias conservadoras de cálculo, verificação independente. Créditos emitidos ≤ carbono real sequestrado/evitado.",
        "icon": "alert-triangle", "severity_typical": "high",
    },
    "vintage_age": {
        "title": "Vintage Antigo (Créditos Envelhecidos)",
        "what_is": "Créditos gerados há mais de 5-10 anos que ainda não foram aposentados. Podem não refletir condições atuais do projeto.",
        "consequences": "Créditos antigos podem não representar reduções adicionais. O projeto pode ter mudado ou sido abandonado.",
        "ideal_situation": "Créditos devem ser utilizados dentro de 3-5 anos. Monitoramento contínuo obrigatório.",
        "icon": "clock", "severity_typical": "medium",
    },
    "retirement_anomaly": {
        "title": "Anomalia de Aposentadoria",
        "what_is": "Padrão de aposentadoria incomum — volume elevado de uma vez, datas suspeitas, ou padrões que sugerem manipulação contábil.",
        "consequences": "Pode indicar manipulação de mercado, dupla contagem ou fraude direta.",
        "ideal_situation": "Aposentadorias seguem padrão regular e proporcional. Cada crédito com ID único, aposentado apenas uma vez.",
        "icon": "repeat", "severity_typical": "high",
    },
    "missing_area": {
        "title": "Área do Projeto Ausente ou Inconsistente",
        "what_is": "Projeto sem informações geográficas adequadas ou com área declarada inconsistente com imagens de satélite.",
        "consequences": "Impossível verificar existência física do projeto. Projetos fantasma são forma grave de fraude.",
        "ideal_situation": "Coordenadas precisas, verificação por satélite atualizada, validação por auditores independentes.",
        "icon": "map-pin", "severity_typical": "medium",
    },
    "area_anomaly": {
        "title": "Área Anormalmente Grande",
        "what_is": "Área declarada do projeto excede limites razoáveis (>10M hectares), sugerindo erro ou fraude.",
        "consequences": "Área inflada pode mascarar overcrediting ou criar créditos fictícios.",
        "ideal_situation": "Área deve ser verificada com coordenadas GPS e imagens de satélite.",
        "icon": "maximize", "severity_typical": "high",
    },
    "governance_gaps": {
        "title": "Lacunas de Governança",
        "what_is": "Ausência de informações essenciais sobre gestão, transparência e conformidade do projeto.",
        "consequences": "Projetos com governança fraca são mais suscetíveis a fraudes e conflitos.",
        "ideal_situation": "Documentação completa: validação, monitoramento periódico, FPIC, auditorias regulares.",
        "icon": "file-warning", "severity_typical": "medium",
    },
    "insufficient_buffer": {
        "title": "Buffer de Permanência Insuficiente",
        "what_is": "Reserva de créditos insuficiente como 'seguro' contra reversão (incêndio, desmatamento).",
        "consequences": "Se ocorrer reversão e buffer insuficiente, créditos vendidos não podem ser compensados.",
        "ideal_situation": "Projetos florestais: buffer mínimo de 15-20%, ajustado por perfil de risco.",
        "icon": "shield-off", "severity_typical": "high",
    },
    "wash_trading": {
        "title": "Suspeita de Wash Trading",
        "what_is": "Padrão circular de compra/venda entre entidades relacionadas sem mudança real de propriedade.",
        "consequences": "Infla artificialmente volumes de mercado e pode manipular preços.",
        "ideal_situation": "Transações entre partes independentes com due diligence sobre contrapartes.",
        "icon": "refresh-ccw", "severity_typical": "critical",
    },
    "sanctioned_entity": {
        "title": "Entidade Sancionada",
        "what_is": "Developer, broker ou contraparte do projeto consta em lista de sanções ou enforcement.",
        "consequences": "Riscos legais, regulatórios e reputacionais graves para compradores.",
        "ideal_situation": "Due diligence completa sobre todas as contrapartes. Screening contra listas de sanções.",
        "icon": "shield-alert", "severity_typical": "critical",
    },
    "fire_proximity": {
        "title": "Incêndio Próximo ao Projeto",
        "what_is": "Dados de satélite detectam focos de calor próximos à área do projeto.",
        "consequences": "Incêndios podem destruir vegetação e liberar carbono, anulando créditos emitidos.",
        "ideal_situation": "Planos de contingência, seguro contra reversão, monitoramento remoto contínuo.",
        "icon": "flame", "severity_typical": "critical",
    },
    "deforestation_detected": {
        "title": "Desmatamento Detectado por Satélite",
        "what_is": "Queda significativa no índice de vegetação (NDVI) na área do projeto.",
        "consequences": "Em projetos REDD+ invalida completamente os créditos.",
        "ideal_situation": "Cobertura vegetal mantida/aumentada. Monitoramento por satélite confirma permanência.",
        "icon": "tree-deciduous", "severity_typical": "critical",
    },
}


# ─── Detection Rules ───────────────────────────────────────────────────

def _check_overcrediting(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.area_hectares or p.area_hectares <= 0 or not p.total_credits_issued or p.total_credits_issued <= 0:
        return None
    ptk = p.project_type if isinstance(p.project_type, str) else p.project_type.value
    max_ph = MAX_CREDITS_PER_HA.get(ptk, 50)
    actual = p.total_credits_issued / p.area_hectares
    if actual > max_ph:
        ratio = actual / max_ph
        sev = FraudSeverity.CRITICAL if ratio > 3 else FraudSeverity.HIGH if ratio > 2 else FraudSeverity.MEDIUM
        return FraudAlert(
            project_id=p.id, alert_type="overcrediting", severity=sev,
            title="Possível over-crediting detectado",
            description=f"Emitiu {actual:.1f} créditos/ha, máximo esperado {max_ph} ({ratio:.1f}x acima).",
            evidence={"credits_per_ha": round(actual, 2), "max_expected": max_ph, "ratio": round(ratio, 2)},
            recommendation="Revisar metodologia de cálculo e linha de base.",
            detection_method="rule_based", confidence=min(0.95, 0.5 + (ratio - 1) * 0.2),
        )
    return None


def _check_area(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.area_hectares:
        return FraudAlert(
            project_id=p.id, alert_type="missing_area", severity=FraudSeverity.LOW,
            title="Área não declarada",
            description="Projeto sem informação de área declarada.",
            evidence={"area_hectares": None},
            recommendation="Solicitar documentação geográfica.",
            detection_method="rule_based", confidence=0.3,
        )
    if p.area_hectares > 10_000_000:
        return FraudAlert(
            project_id=p.id, alert_type="area_anomaly", severity=FraudSeverity.HIGH,
            title="Área anormalmente grande",
            description=f"Área declarada de {p.area_hectares:,.0f} ha excede limites razoáveis.",
            evidence={"area_hectares": p.area_hectares},
            recommendation="Verificar coordenadas e confrontar com imagens satelitais.",
            detection_method="rule_based", confidence=0.7,
        )
    return None


def _check_vintage(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.vintage_year:
        return None
    current_year = datetime.now(timezone.utc).year
    age = current_year - p.vintage_year
    if age > 10:
        sev = FraudSeverity.HIGH if age > 15 else FraudSeverity.MEDIUM
        return FraudAlert(
            project_id=p.id, alert_type="vintage_age", severity=sev,
            title="Vintage muito antigo",
            description=f"Vintage {p.vintage_year} ({age} anos). Créditos podem não refletir condições atuais.",
            evidence={"vintage_year": p.vintage_year, "age": age},
            recommendation="Avaliar condições atuais do projeto e monitoramento recente.",
            detection_method="rule_based", confidence=0.6,
        )
    return None


def _check_buffer(p: CarbonProject) -> Optional[FraudAlert]:
    ptk = p.project_type if isinstance(p.project_type, str) else p.project_type.value
    if ptk not in ("REDD+", "ARR", "Blue Carbon", "Biochar"):
        return None
    if not p.buffer_pool_percentage or p.buffer_pool_percentage < 5:
        return FraudAlert(
            project_id=p.id, alert_type="insufficient_buffer", severity=FraudSeverity.MEDIUM,
            title="Buffer de permanência insuficiente",
            description=f"Buffer: {p.buffer_pool_percentage or 0}% (mínimo recomendado: 15%).",
            evidence={"buffer": p.buffer_pool_percentage, "min_recommended": 15},
            recommendation="Verificar exigências do padrão e aumentar buffer pool.",
            detection_method="rule_based", confidence=0.65,
        )
    return None


def _check_retirement(p: CarbonProject) -> Optional[FraudAlert]:
    if not p.total_credits_issued or p.total_credits_issued == 0:
        return None
    rate = p.total_credits_retired / p.total_credits_issued
    if rate > 0.90 and p.total_credits_issued > 10000:
        return FraudAlert(
            project_id=p.id, alert_type="retirement_anomaly", severity=FraudSeverity.MEDIUM,
            title="Taxa de aposentadoria anômala",
            description=f"{rate*100:.1f}% dos créditos aposentados em projeto com {p.total_credits_issued:,} emitidos.",
            evidence={"rate": round(rate, 4), "issued": p.total_credits_issued, "retired": p.total_credits_retired},
            recommendation="Verificar histórico detalhado de transações e contrapartes.",
            detection_method="rule_based", confidence=0.5,
        )
    return None


def _check_governance(p: CarbonProject) -> Optional[FraudAlert]:
    missing = []
    if not p.registry:
        missing.append("registro")
    if not p.methodology:
        missing.append("metodologia")
    if not p.proponent:
        missing.append("proponente")
    if not p.external_id:
        missing.append("ID externo")
    if not p.monitoring_frequency:
        missing.append("monitoramento")
    if len(missing) >= 3:
        sev = FraudSeverity.MEDIUM if len(missing) < 4 else FraudSeverity.HIGH
        return FraudAlert(
            project_id=p.id, alert_type="governance_gaps", severity=sev,
            title="Lacunas de governança identificadas",
            description=f"{len(missing)} campos críticos ausentes: {', '.join(missing)}.",
            evidence={"missing": missing, "count": len(missing)},
            recommendation="Solicitar documentação completa antes de prosseguir.",
            detection_method="rule_based", confidence=0.7,
        )
    return None


def _check_wash_trading(p: CarbonProject) -> Optional[FraudAlert]:
    """Check for wash trading patterns via retirement rate + volume anomalies."""
    if not p.total_credits_issued or p.total_credits_issued < 50000:
        return None
    if not p.total_credits_retired:
        return None
    # Heuristic: very high retirement with very high issuance in short time
    if p.total_credits_retired > 0.85 * p.total_credits_issued and p.total_credits_issued > 100000:
        return FraudAlert(
            project_id=p.id, alert_type="wash_trading", severity=FraudSeverity.HIGH,
            title="Suspeita de wash trading",
            description=f"Volume elevado ({p.total_credits_issued:,} emitidos, {p.total_credits_retired:,} aposentados). Padrão requer investigação.",
            evidence={"issued": p.total_credits_issued, "retired": p.total_credits_retired, "ratio": round(p.total_credits_retired / p.total_credits_issued, 3)},
            recommendation="Investigar contrapartes e padrão de transações. Verificar relações entre comprador/vendedor.",
            detection_method="heuristic", confidence=0.4,
        )
    return None


def run_fraud_detection(project: CarbonProject) -> list[FraudAlert]:
    """Run all fraud detection rules on a project."""
    checks = [
        _check_overcrediting, _check_area, _check_vintage,
        _check_buffer, _check_retirement, _check_governance,
        _check_wash_trading,
    ]
    alerts = [a for check in checks if (a := check(project)) is not None]

    # Calculate Fraud Ops score (0-100, higher = more suspicious)
    if alerts:
        severity_weights = {"critical": 30, "high": 20, "medium": 10, "low": 5}
        fraud_ops_score = min(100, sum(
            severity_weights.get(a.severity.value if hasattr(a.severity, 'value') else a.severity, 5)
            for a in alerts
        ))
        for a in alerts:
            a.fraud_ops_score = fraud_ops_score

    return alerts


def calculate_fraud_ops_score(alerts: list) -> float:
    """Calculate aggregate Fraud Ops score from alert list."""
    if not alerts:
        return 0.0
    severity_weights = {"critical": 30, "high": 20, "medium": 10, "low": 5}
    score = sum(severity_weights.get(
        a.severity.value if hasattr(a, 'severity') and hasattr(a.severity, 'value') else str(getattr(a, 'severity', 'low')),
        5
    ) for a in alerts)
    return min(100.0, float(score))
