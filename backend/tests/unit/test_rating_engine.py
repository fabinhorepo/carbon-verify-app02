"""Unit Tests — Rating Engine v3."""
import pytest
from unittest.mock import MagicMock
from app.modules.rating.service import (
    calculate_rating, _score_carbon_integrity, _score_additionality,
    _score_permanence, _score_leakage, _score_mrv, _score_co_benefits,
    _score_governance, _get_grade, _clamp, GRADE_DISCOUNT_FACTORS,
    PILLAR_WEIGHTS, GRADE_BOUNDARIES,
)
from app.models.models import RatingGrade


def _make_project(**kwargs):
    p = MagicMock()
    defaults = {
        "id": 1, "name": "Test Project", "project_type": "REDD+",
        "methodology": "VM0015", "registry": "Verra", "country": "Brazil",
        "area_hectares": 50000, "total_credits_issued": 200000,
        "total_credits_retired": 80000, "total_credits_available": 120000,
        "vintage_year": 2021, "proponent": "Test Corp",
        "buffer_pool_percentage": 18, "monitoring_frequency": "Semestral",
        "baseline_scenario": "Historical deforestation analysis based on 10+ years of satellite data. Conservative projections used.",
        "additionality_justification": "Financial barriers analysis shows the project would not be viable without carbon credit revenue. Independent validation by SCS Global.",
        "external_id": "VCS-1234", "description": "Large REDD+ project in the Amazon.",
        "sdg_contributions": {"SDG13": True, "SDG15": True},
        "start_date": MagicMock(year=2018), "end_date": MagicMock(year=2048),
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(p, k, v)
    if p.start_date is not None and p.end_date is not None:
        p.end_date.__sub__ = lambda self, other: MagicMock(days=30 * 365)
    return p


class TestClamp:
    def test_clamp_normal(self):
        assert _clamp(50) == 50

    def test_clamp_over_100(self):
        assert _clamp(150) == 100

    def test_clamp_below_0(self):
        assert _clamp(-10) == 0


class TestGetGrade:
    def test_grade_AAA(self):
        assert _get_grade(95) == RatingGrade.AAA

    def test_grade_AA(self):
        assert _get_grade(85) == RatingGrade.AA

    def test_grade_A(self):
        assert _get_grade(75) == RatingGrade.A

    def test_grade_BBB(self):
        assert _get_grade(65) == RatingGrade.BBB

    def test_grade_D(self):
        assert _get_grade(5) == RatingGrade.D

    def test_grade_boundary_exact(self):
        assert _get_grade(90) == RatingGrade.AAA
        assert _get_grade(80) == RatingGrade.AA


class TestCarbonIntegrity:
    def test_with_good_baseline(self):
        p = _make_project(baseline_scenario="x" * 400)
        score = _score_carbon_integrity(p, 35)
        assert score >= 50

    def test_without_baseline(self):
        p = _make_project(baseline_scenario=None)
        score = _score_carbon_integrity(p, 35)
        assert score < 35

    def test_overcrediting_penalty(self):
        p = _make_project(total_credits_issued=500000, area_hectares=1000, baseline_scenario=None, methodology=None)
        score = _score_carbon_integrity(p, 35)
        assert score < 25


class TestAdditionality:
    def test_with_strong_justification(self):
        p = _make_project(additionality_justification="x" * 400)
        score = _score_additionality(p, 35)
        assert score >= 60

    def test_without_justification(self):
        p = _make_project(additionality_justification=None, methodology=None)
        score = _score_additionality(p, 35)
        assert score < 20


class TestPermanence:
    def test_high_buffer(self):
        p = _make_project(buffer_pool_percentage=25)
        score = _score_permanence(p, 30)
        assert score >= 50

    def test_no_buffer_nature_based(self):
        p = _make_project(buffer_pool_percentage=None, project_type="REDD+", start_date=None, end_date=None)
        score = _score_permanence(p, 30)
        assert score <= 30


class TestCobenefits:
    def test_developing_country_bonus(self):
        p = _make_project(country="Brazil")
        score = _score_co_benefits(p, 45)
        assert score > 45

    def test_sdg_bonus(self):
        p = _make_project(sdg_contributions={"SDG1": True, "SDG13": True, "SDG15": True})
        score = _score_co_benefits(p, 45)
        assert score > 55


class TestGovernance:
    def test_complete_governance(self):
        p = _make_project()
        score = _score_governance(p, 30)
        assert score >= 45

    def test_poor_governance(self):
        p = _make_project(proponent=None, registry=None, methodology=None, external_id=None)
        score = _score_governance(p, 30)
        assert score < 20


class TestCalculateRating:
    def test_returns_rating_and_pillars(self):
        p = _make_project()
        rating, pillars = calculate_rating(p)
        assert rating is not None
        assert len(pillars) == 7
        assert rating.overall_score > 0

    def test_rating_has_discount_factor(self):
        p = _make_project()
        rating, _ = calculate_rating(p)
        assert 0 < rating.discount_factor <= 1.0

    def test_high_quality_project_gets_good_grade(self):
        p = _make_project()
        rating, _ = calculate_rating(p)
        assert rating.grade in (RatingGrade.A, RatingGrade.AA, RatingGrade.AAA, RatingGrade.BBB)

    def test_low_quality_project_gets_bad_grade(self):
        p = _make_project(
            methodology=None, registry=None, proponent=None,
            baseline_scenario=None, additionality_justification=None,
            monitoring_frequency=None, buffer_pool_percentage=None,
            external_id=None, description=None, area_hectares=None,
        )
        rating, _ = calculate_rating(p)
        assert rating.grade in (RatingGrade.C, RatingGrade.D, RatingGrade.CC, RatingGrade.CCC, RatingGrade.B)

    def test_pillar_weights_sum_to_one(self):
        assert abs(sum(PILLAR_WEIGHTS.values()) - 1.0) < 0.01

    def test_all_grades_have_discount_factors(self):
        for grade in RatingGrade:
            assert grade.value in GRADE_DISCOUNT_FACTORS

    def test_risk_flags_generated(self):
        p = _make_project(
            registry=None, additionality_justification=None,
            buffer_pool_percentage=2,
        )
        rating, _ = calculate_rating(p)
        assert len(rating.risk_flags) > 0

    def test_explanation_generated(self):
        p = _make_project()
        rating, _ = calculate_rating(p)
        assert rating.explanation
        assert "Test Project" in rating.explanation
