"""Workspace Service — Multi-stakeholder profiles and permissions.

Defines workspace profiles per organizational role with
visible modules, allowed actions, and approval flow support.
"""

WORKSPACE_PROFILES = {
    "sustainability": {
        "label": "Sustentabilidade / Clima",
        "description": "Visão completa de projetos, ratings, portfólio e compliance para equipes de sustentabilidade.",
        "visible_modules": [
            "dashboard", "projects", "ratings", "portfolio", "compliance",
            "market", "map", "compare", "reports", "api_docs",
        ],
        "allowed_actions": [
            "view_projects", "create_project", "view_ratings", "simulate_portfolio",
            "view_compliance", "request_purchase", "generate_report", "view_market",
        ],
        "dashboard_kpis": [
            "total_projects", "avg_quality_score", "portfolio_value",
            "risk_adjusted_tonnes", "compliance_coverage",
        ],
    },
    "risk_compliance": {
        "label": "Risco / Compliance",
        "description": "Foco em fraud detection, alertas de risco e compliance regulatória.",
        "visible_modules": [
            "dashboard", "projects", "ratings", "fraud_ops", "compliance",
            "reports",
        ],
        "allowed_actions": [
            "view_projects", "view_ratings", "view_fraud_alerts", "review_alerts",
            "approve_compliance", "flag_project", "generate_report",
        ],
        "dashboard_kpis": [
            "fraud_alerts_count", "risk_summary", "compliance_coverage",
            "avg_quality_score", "high_risk_projects",
        ],
    },
    "legal": {
        "label": "Jurídico",
        "description": "Acesso a evidências de compliance, enforcement e fluxos de aprovação legal.",
        "visible_modules": [
            "compliance", "fraud_ops", "approvals", "reports",
        ],
        "allowed_actions": [
            "view_compliance", "view_evidence", "review_evidence",
            "legal_approve", "export_compliance", "view_fraud_alerts",
        ],
        "dashboard_kpis": [
            "compliance_coverage", "pending_approvals", "enforcement_alerts",
        ],
    },
    "procurement": {
        "label": "Compras / Procurement",
        "description": "Ferramentas de mercado, frontier preço-qualidade e simulação de compras.",
        "visible_modules": [
            "dashboard", "market", "portfolio", "compare", "reports",
        ],
        "allowed_actions": [
            "view_market", "view_frontier", "simulate_purchase",
            "request_approval", "compare_credits", "view_portfolio",
        ],
        "dashboard_kpis": [
            "portfolio_value", "opportunities_count", "avg_price",
            "risk_adjusted_cost", "pending_purchases",
        ],
    },
    "external_audit": {
        "label": "Auditoria Externa",
        "description": "Acesso read-only a compliance, evidências e relatórios para auditores.",
        "visible_modules": [
            "compliance", "reports",
        ],
        "allowed_actions": [
            "view_compliance", "view_evidence", "export_package",
            "navigate_evidence", "download_report",
        ],
        "dashboard_kpis": [
            "compliance_coverage", "evidence_completeness", "report_count",
        ],
    },
    "custom": {
        "label": "Personalizado",
        "description": "Configuração personalizada de módulos e permissões.",
        "visible_modules": [],
        "allowed_actions": [],
        "dashboard_kpis": [],
    },
}


def get_profile_config(profile_type: str) -> dict:
    """Get workspace profile configuration."""
    return WORKSPACE_PROFILES.get(profile_type, WORKSPACE_PROFILES["custom"])


def get_all_profiles() -> dict:
    """Return all available workspace profiles."""
    return {
        k: {"label": v["label"], "description": v["description"]}
        for k, v in WORKSPACE_PROFILES.items()
    }


def check_permission(profile_type: str, action: str) -> bool:
    """Check if a workspace profile allows a specific action."""
    profile = WORKSPACE_PROFILES.get(profile_type, {})
    return action in profile.get("allowed_actions", [])


def get_visible_modules(profile_type: str) -> list[str]:
    """Get list of visible modules for a workspace profile."""
    profile = WORKSPACE_PROFILES.get(profile_type, {})
    return profile.get("visible_modules", [])


def get_dashboard_kpis(profile_type: str) -> list[str]:
    """Get list of relevant KPIs for a workspace profile's dashboard."""
    profile = WORKSPACE_PROFILES.get(profile_type, {})
    return profile.get("dashboard_kpis", [])
