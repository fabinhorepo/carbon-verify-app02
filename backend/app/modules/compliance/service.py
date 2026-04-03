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


# ═══════════════════════════════════════════════════════════════════════════
# CSRD PACKAGE EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def generate_csrd_package(
    portfolio_name: str,
    portfolio_id: int,
    compliance_summary: dict,
    portfolio_metrics: dict,
) -> dict:
    """Generate a CSRD compliance package as structured JSON."""
    from datetime import datetime, timezone

    csrd_items = compliance_summary.get("csrd_esrs", {}).get("items", [])
    sbti_items = compliance_summary.get("sbti", {}).get("items", [])
    icvcm_items = compliance_summary.get("icvcm", {}).get("items", [])

    # Build disclosure data
    disclosures = {}
    for item in csrd_items:
        code = item.get("disclosure_item", "")
        if code not in disclosures:
            disclosures[code] = {
                "code": code,
                "title": item.get("disclosure_title", ""),
                "description": item.get("description", ""),
                "status": item.get("status", "gap"),
                "coverage_pct": item.get("coverage_pct", 0),
                "evidence_summaries": [],
                "projects_contributing": [],
            }
        disclosures[code]["evidence_summaries"].append(item.get("evidence_summary", ""))
        details = item.get("details", {})
        if details.get("project_name"):
            disclosures[code]["projects_contributing"].append(details["project_name"])

    return {
        "package_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "portfolio_name": portfolio_name,
            "portfolio_id": portfolio_id,
            "reporting_framework": "CSRD / ESRS E1",
            "reporting_period": str(datetime.now(timezone.utc).year),
        },
        "portfolio_summary": {
            "total_projects": portfolio_metrics.get("total_projects", 0),
            "nominal_tonnes": portfolio_metrics.get("nominal_tonnes", 0),
            "risk_adjusted_tonnes": portfolio_metrics.get("risk_adjusted_tonnes", 0),
            "avg_quality_score": portfolio_metrics.get("avg_quality_score", 0),
            "portfolio_grade": portfolio_metrics.get("portfolio_grade", "N/A"),
            "discount_factor_avg": portfolio_metrics.get("discount_factor_avg", 1.0),
        },
        "csrd_esrs_e1": {
            "disclosures": disclosures,
            "summary": {
                "total_disclosure_items": len(disclosures),
                "verified": sum(1 for d in disclosures.values() if d["status"] == "verified"),
                "mapped": sum(1 for d in disclosures.values() if d["status"] == "mapped"),
                "gaps": sum(1 for d in disclosures.values() if d["status"] == "gap"),
                "avg_coverage": compliance_summary.get("csrd_esrs", {}).get("avg_coverage", 0),
            },
        },
        "sbti_assessment": {
            "requirements": sbti_items,
            "compliant_count": compliance_summary.get("sbti", {}).get("compliant", 0),
            "total_requirements": compliance_summary.get("sbti", {}).get("total", 0),
        },
        "icvcm_assessment": {
            "principles": icvcm_items,
            "met_count": compliance_summary.get("icvcm", {}).get("met", 0),
            "total_principles": compliance_summary.get("icvcm", {}).get("total", 0),
        },
        "overall_compliance_score": compliance_summary.get("overall_score", 0),
        "draft_text": _generate_csrd_draft_text(portfolio_name, portfolio_metrics, disclosures),
    }


def _generate_csrd_draft_text(portfolio_name: str, metrics: dict, disclosures: dict) -> str:
    """Generate a markdown draft report for CSRD submission."""
    lines = [
        f"# CSRD / ESRS E1 — Relatório de Divulgação Climática",
        f"## Portfólio: {portfolio_name}",
        f"**Período de Reporte:** {__import__('datetime').datetime.now().year}",
        "",
        "---",
        "",
        "## 1. Resumo do Portfólio de Créditos de Carbono",
        "",
        f"- **Projetos no portfólio:** {metrics.get('total_projects', 0)}",
        f"- **Toneladas nominais (tCO2e):** {metrics.get('nominal_tonnes', 0):,.0f}",
        f"- **Toneladas risk-adjusted (tCO2e):** {metrics.get('risk_adjusted_tonnes', 0):,.0f}",
        f"- **Rating médio do portfólio:** {metrics.get('portfolio_grade', 'N/A')}",
        f"- **Score médio de qualidade:** {metrics.get('avg_quality_score', 0):.1f}/100",
        f"- **Fator de desconto médio:** {metrics.get('discount_factor_avg', 1.0):.1%}",
        "",
        "---",
        "",
        "## 2. Divulgações ESRS E1",
        "",
    ]

    for code, disc in sorted(disclosures.items()):
        status_label = {"verified": "✅ Verificado", "mapped": "⚠️ Mapeado", "gap": "❌ Lacuna"}.get(disc["status"], "N/A")
        lines.append(f"### {code} — {disc['title']}")
        lines.append(f"**Status:** {status_label} | **Cobertura:** {disc['coverage_pct']:.0f}%")
        lines.append(f"\n{disc['description']}\n")
        if disc["evidence_summaries"]:
            lines.append("**Evidências:**")
            for ev in disc["evidence_summaries"][:3]:
                lines.append(f"- {ev}")
        if disc["projects_contributing"]:
            unique_projects = list(set(disc["projects_contributing"]))
            lines.append(f"\n**Projetos contribuintes:** {', '.join(unique_projects[:5])}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 3. Notas para Auditores",
        "",
        "Este relatório foi gerado automaticamente pela plataforma Carbon Verify.",
        "Os dados de rating e compliance são baseados em análise algorítmica multi-pilar",
        "inspirada pelas metodologias Sylvera, BeZero e Calyx Global.",
        "",
        "Para verificação independente, consulte os registros originais (Verra, Gold Standard, ACR)",
        "referenciados em cada projeto individual.",
    ])

    return "\n".join(lines)


def generate_csrd_pdf(
    portfolio_name: str,
    portfolio_id: int,
    compliance_summary: dict,
    portfolio_metrics: dict,
) -> bytes:
    """Generate a CSRD compliance package as PDF using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io
    from datetime import datetime, timezone

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('CVTitle', parent=styles['Title'], fontSize=20,
                                  textColor=HexColor('#06b6d4'), spaceAfter=12)
    subtitle_style = ParagraphStyle('CVSubtitle', parent=styles['Heading2'], fontSize=14,
                                     textColor=HexColor('#1e293b'), spaceAfter=8)
    body_style = ParagraphStyle('CVBody', parent=styles['Normal'], fontSize=10,
                                 spaceAfter=6, leading=14)
    metric_style = ParagraphStyle('CVMetric', parent=styles['Normal'], fontSize=10,
                                   textColor=HexColor('#334155'), spaceAfter=4)

    elements = []

    # Title
    elements.append(Paragraph("Carbon Verify — CSRD / ESRS E1", title_style))
    elements.append(Paragraph(f"Relatório de Compliance — Portfólio: {portfolio_name}", subtitle_style))
    elements.append(Paragraph(f"Gerado em: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}", body_style))
    elements.append(Spacer(1, 0.5*cm))

    # Portfolio Summary Table
    elements.append(Paragraph("1. Resumo do Portfólio", subtitle_style))
    summary_data = [
        ["Métrica", "Valor"],
        ["Projetos", str(portfolio_metrics.get("total_projects", 0))],
        ["Toneladas Nominais", f"{portfolio_metrics.get('nominal_tonnes', 0):,.0f} tCO2e"],
        ["Toneladas Risk-Adjusted", f"{portfolio_metrics.get('risk_adjusted_tonnes', 0):,.0f} tCO2e"],
        ["Rating do Portfólio", portfolio_metrics.get("portfolio_grade", "N/A")],
        ["Score Médio", f"{portfolio_metrics.get('avg_quality_score', 0):.1f}/100"],
        ["Fator de Desconto Médio", f"{portfolio_metrics.get('discount_factor_avg', 1.0):.1%}"],
    ]
    t = Table(summary_data, colWidths=[8*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#06b6d4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f8fafc'), HexColor('#ffffff')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.8*cm))

    # CSRD Disclosures
    elements.append(Paragraph("2. Divulgações ESRS E1", subtitle_style))
    csrd_items = compliance_summary.get("csrd_esrs", {}).get("items", [])

    seen_codes = set()
    for item in csrd_items:
        code = item.get("disclosure_item", "")
        if code in seen_codes:
            continue
        seen_codes.add(code)
        status = item.get("status", "gap")
        status_label = {"verified": "Verificado", "mapped": "Mapeado", "gap": "Lacuna"}.get(status, "N/A")
        coverage = item.get("coverage_pct", 0)

        elements.append(Paragraph(f"<b>{code} — {item.get('disclosure_title', '')}</b>", body_style))
        elements.append(Paragraph(f"Status: {status_label} | Cobertura: {coverage:.0f}%", metric_style))
        if item.get("evidence_summary"):
            elements.append(Paragraph(f"Evidência: {item['evidence_summary']}", metric_style))
        elements.append(Spacer(1, 0.3*cm))

    # SBTi Assessment
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph("3. Avaliação SBTi", subtitle_style))
    sbti_compliant = compliance_summary.get("sbti", {}).get("compliant", 0)
    sbti_total = compliance_summary.get("sbti", {}).get("total", 0)
    elements.append(Paragraph(f"Requisitos atendidos: {sbti_compliant}/{sbti_total}", body_style))

    # ICVCM Assessment
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("4. Princípios ICVCM", subtitle_style))
    icvcm_met = compliance_summary.get("icvcm", {}).get("met", 0)
    icvcm_total = compliance_summary.get("icvcm", {}).get("total", 0)
    elements.append(Paragraph(f"Princípios atendidos: {icvcm_met}/{icvcm_total}", body_style))

    # Overall Score
    elements.append(Spacer(1, 0.5*cm))
    overall = compliance_summary.get("overall_score", 0)
    elements.append(Paragraph(f"<b>Score Geral de Compliance: {overall:.1f}/100</b>", subtitle_style))

    # Footer note
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        "Este relatório foi gerado automaticamente pela plataforma Carbon Verify. "
        "Os dados de rating e compliance são baseados em análise algorítmica multi-pilar. "
        "Para verificação independente, consulte os registros originais.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=HexColor('#94a3b8')),
    ))

    doc.build(elements)
    return buffer.getvalue()
