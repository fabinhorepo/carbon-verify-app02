"""Unit Tests — Fraud Detection, Portfolio Optimizer, Compliance, Market Intel."""
import pytest
from unittest.mock import MagicMock
from app.modules.fraud_ops.service import (
    run_fraud_detection, calculate_fraud_ops_score,
    _check_overcrediting, _check_area, _check_vintage,
    _check_buffer, _check_retirement, _check_governance,
    _check_wash_trading, FRAUD_TYPE_EXPLANATIONS,
)
from app.modules.portfolio.service import calculate_risk_adjusted_tonnes
from app.modules.compliance.service import (
    map_project_to_csrd, map_project_to_sbti, map_project_to_icvcm,
    get_compliance_summary, _grade_meets_minimum,
)
from app.modules.market_intel.service import (
    calculate_frontier, suggest_rebalance, _calculate_grade_medians, _grade_rank,
)
from app.modules.workspace.service import (
    get_profile_config, get_all_profiles, check_permission, get_visible_modules,
)
from app.models.models import FraudSeverity


def _make_project(**kwargs):
    p = MagicMock()
    defaults = {
        "id": 1, "name": "Test", "project_type": "REDD+",
        "area_hectares": 50000, "total_credits_issued": 200000,
        "total_credits_retired": 80000, "vintage_year": 2021,
        "buffer_pool_percentage": 18, "registry": "Verra",
        "methodology": "VM0015", "proponent": "Test Corp",
        "external_id": "VCS-1234", "monitoring_frequency": "Anual",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(p, k, v)
    return p


# ═══════════════════════════════════════════════════════════════════════════
# FRAUD DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestFraudDetection:
    def test_overcrediting_detected(self):
        p = _make_project(total_credits_issued=500000, area_hectares=1000)
        alert = _check_overcrediting(p)
        assert alert is not None
        assert alert.alert_type == "overcrediting"

    def test_overcrediting_normal(self):
        p = _make_project(total_credits_issued=10000, area_hectares=50000)
        alert = _check_overcrediting(p)
        assert alert is None

    def test_missing_area(self):
        p = _make_project(area_hectares=None)
        alert = _check_area(p)
        assert alert is not None
        assert alert.alert_type == "missing_area"

    def test_area_anomaly(self):
        p = _make_project(area_hectares=20000000)
        alert = _check_area(p)
        assert alert is not None
        assert alert.alert_type == "area_anomaly"

    def test_old_vintage(self):
        p = _make_project(vintage_year=2005)
        alert = _check_vintage(p)
        assert alert is not None

    def test_recent_vintage_ok(self):
        p = _make_project(vintage_year=2023)
        alert = _check_vintage(p)
        assert alert is None

    def test_insufficient_buffer(self):
        p = _make_project(buffer_pool_percentage=2)
        alert = _check_buffer(p)
        assert alert is not None

    def test_sufficient_buffer(self):
        p = _make_project(buffer_pool_percentage=20)
        alert = _check_buffer(p)
        assert alert is None

    def test_retirement_anomaly(self):
        p = _make_project(total_credits_issued=200000, total_credits_retired=195000)
        alert = _check_retirement(p)
        assert alert is not None

    def test_governance_gaps(self):
        p = _make_project(registry=None, methodology=None, proponent=None, external_id=None, monitoring_frequency=None)
        alert = _check_governance(p)
        assert alert is not None

    def test_wash_trading(self):
        p = _make_project(total_credits_issued=200000, total_credits_retired=180000)
        alert = _check_wash_trading(p)
        assert alert is not None

    def test_run_all_returns_list(self):
        p = _make_project()
        alerts = run_fraud_detection(p)
        assert isinstance(alerts, list)

    def test_fraud_ops_score(self):
        alerts = [MagicMock(severity=FraudSeverity.HIGH), MagicMock(severity=FraudSeverity.MEDIUM)]
        score = calculate_fraud_ops_score(alerts)
        assert score == 30  # 20 + 10

    def test_all_fraud_types_have_explanations(self):
        assert len(FRAUD_TYPE_EXPLANATIONS) >= 8
        for key, val in FRAUD_TYPE_EXPLANATIONS.items():
            assert "title" in val
            assert "what_is" in val


# ═══════════════════════════════════════════════════════════════════════════
# PORTFOLIO OPTIMIZER TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPortfolioOptimizer:
    def test_risk_adjusted_tonnes(self):
        result = calculate_risk_adjusted_tonnes(100000, {"AAA": 50, "BB": 50})
        assert result["target_impact"] == 100000
        assert result["total_nominal_needed"] > 100000  # always need more due to discount
        assert "grade_breakdown" in result

    def test_over_purchase_ratio(self):
        result = calculate_risk_adjusted_tonnes(100000, {"D": 100})
        assert result["over_purchase_ratio"] > 10  # D has 0.02 discount

    def test_perfect_credits(self):
        result = calculate_risk_adjusted_tonnes(100000, {"AAA": 100})
        assert result["over_purchase_ratio"] == 1.0  # AAA has 1.0 discount


# ═══════════════════════════════════════════════════════════════════════════
# COMPLIANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestCompliance:
    def test_csrd_mapping(self):
        project = {"name": "Test", "project_type": "REDD+", "registry": "Verra",
                   "methodology": "VM0015", "total_credits_issued": 100000,
                   "vintage_year": 2021, "external_id": "VCS-1", "description": "Test"}
        rating = {"grade": "AA", "discount_factor": 0.95, "risk_flags": []}
        result = map_project_to_csrd(project, rating)
        assert len(result) == 4
        assert all("disclosure_item" in m for m in result)

    def test_sbti_mapping(self):
        result = map_project_to_sbti({}, {"grade": "AA"})
        assert len(result) == 2

    def test_sbti_grade_check(self):
        result = map_project_to_sbti({}, {"grade": "D"})
        assert all(m["status"] == "non_compliant" for m in result)

    def test_icvcm_mapping(self):
        result = map_project_to_icvcm({}, {"grade": "A", "additionality_score": 75, "permanence_score": 80, "carbon_integrity_score": 70, "governance_score": 65, "co_benefits_score": 60})
        assert len(result) == 5

    def test_grade_meets_minimum(self):
        assert _grade_meets_minimum("AAA", "BBB") is True
        assert _grade_meets_minimum("D", "A") is False
        assert _grade_meets_minimum("A", "A") is True

    def test_compliance_summary(self):
        project = {"name": "Test", "project_type": "REDD+", "registry": "Verra",
                   "methodology": "VM0015", "total_credits_issued": 100000,
                   "vintage_year": 2021, "external_id": "VCS-1", "description": "Test"}
        rating = {"grade": "AA", "discount_factor": 0.95, "risk_flags": [],
                 "additionality_score": 75, "permanence_score": 80,
                 "carbon_integrity_score": 70, "governance_score": 65, "co_benefits_score": 60}
        result = get_compliance_summary(project, rating)
        assert "csrd_esrs" in result
        assert "sbti" in result
        assert "icvcm" in result
        assert "overall_score" in result


# ═══════════════════════════════════════════════════════════════════════════
# MARKET INTELLIGENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestMarketIntel:
    def test_frontier_calculation(self):
        credits = [
            {"project_id": 1, "project_name": "A", "project_type": "REDD+", "grade": "AAA", "price_eur": 25, "rating_score": 95, "liquidity_score": 0.9},
            {"project_id": 2, "project_name": "B", "project_type": "REDD+", "grade": "BB", "price_eur": 8, "rating_score": 55, "liquidity_score": 0.5},
            {"project_id": 3, "project_name": "C", "project_type": "REDD+", "grade": "AAA", "price_eur": 15, "rating_score": 92, "liquidity_score": 0.8},
        ]
        result = calculate_frontier(credits)
        assert "frontier" in result
        assert "opportunities" in result
        assert "stats" in result
        assert result["stats"]["total_credits_analyzed"] == 3

    def test_empty_frontier(self):
        result = calculate_frontier([])
        assert result["frontier"] == []

    def test_grade_medians(self):
        credits = [
            {"grade": "AAA", "price_eur": 20},
            {"grade": "AAA", "price_eur": 30},
            {"grade": "BB", "price_eur": 5},
        ]
        medians = _calculate_grade_medians(credits)
        assert "AAA" in medians
        assert "BB" in medians

    def test_grade_rank(self):
        assert _grade_rank("AAA") == 0
        assert _grade_rank("D") == 9
        assert _grade_rank("unknown") == 9

    def test_rebalance_suggestions(self):
        positions = [
            {"project_id": 1, "project_name": "Bad", "grade": "CCC", "price_eur": 10, "quantity": 100},
        ]
        opportunities = [
            {"project_id": 2, "project_name": "Good", "grade": "AA", "price_eur": 18, "opportunity_score": 8},
        ]
        suggestions = suggest_rebalance(positions, opportunities)
        assert isinstance(suggestions, list)


# ═══════════════════════════════════════════════════════════════════════════
# WORKSPACE TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestWorkspace:
    def test_get_all_profiles(self):
        profiles = get_all_profiles()
        assert len(profiles) >= 5
        assert "sustainability" in profiles

    def test_get_profile_config(self):
        config = get_profile_config("sustainability")
        assert "visible_modules" in config
        assert "allowed_actions" in config
        assert "dashboard" in config["visible_modules"]

    def test_check_permission(self):
        assert check_permission("sustainability", "view_projects") is True
        assert check_permission("external_audit", "create_project") is False

    def test_get_visible_modules(self):
        modules = get_visible_modules("procurement")
        assert "market" in modules
        assert "fraud_ops" not in modules

    def test_external_audit_limited(self):
        modules = get_visible_modules("external_audit")
        assert len(modules) <= 3
        assert "compliance" in modules
