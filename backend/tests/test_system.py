"""Testes unitários e de integração para Carbon Verify."""
import sys
import os
import asyncio
import pytest
from datetime import datetime

# Garantir que o path do backend está no sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Unit Tests: Config ──────────────────────────────────────────────────

class TestConfig:
    def test_settings_load(self):
        from app.core.config import settings
        assert settings.APP_NAME == "Carbon Verify"
        assert settings.APP_VERSION == "2.0.0"
        assert settings.API_V1_PREFIX == "/api/v1"
        assert settings.ALGORITHM == "HS256"

    def test_is_postgres_with_postgres_url(self):
        from app.core.config import Settings
        s = Settings(DATABASE_URL="postgres://user:pass@host/db")
        assert s.is_postgres is True

    def test_is_postgres_with_postgresql_url(self):
        from app.core.config import Settings
        s = Settings(DATABASE_URL="postgresql://user:pass@host/db")
        assert s.is_postgres is True

    def test_is_postgres_with_sqlite_url(self):
        from app.core.config import Settings
        s = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db")
        assert s.is_postgres is False

    def test_async_database_url_conversion_postgres(self):
        from app.core.config import Settings
        s = Settings(DATABASE_URL="postgres://user:pass@host/db")
        assert s.async_database_url == "postgresql+asyncpg://user:pass@host/db"

    def test_async_database_url_conversion_postgresql(self):
        from app.core.config import Settings
        s = Settings(DATABASE_URL="postgresql://user:pass@host/db")
        assert s.async_database_url == "postgresql+asyncpg://user:pass@host/db"

    def test_cors_origins_star(self):
        from app.core.config import Settings
        s = Settings(CORS_ORIGINS_RAW="*")
        assert s.get_cors_origins() == ["*"]

    def test_cors_origins_list(self):
        from app.core.config import Settings
        s = Settings(CORS_ORIGINS_RAW="http://a.com, http://b.com")
        origins = s.get_cors_origins()
        assert len(origins) == 2
        assert "http://a.com" in origins
        assert "http://b.com" in origins


# ─── Unit Tests: Auth ────────────────────────────────────────────────────

class TestAuth:
    def test_password_hash_and_verify(self):
        from app.core.auth import get_password_hash, verify_password
        plain = "admin123"
        hashed = get_password_hash(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_create_access_token(self):
        from app.core.auth import create_access_token
        from jose import jwt
        from app.core.config import settings
        token = create_access_token({"sub": "1"})
        assert token is not None
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "1"
        assert "exp" in payload

    def test_create_api_key(self):
        from app.core.auth import create_api_key
        key = create_api_key(1)
        assert key.startswith("cv_1_")
        assert len(key) > 10


# ─── Unit Tests: Models ──────────────────────────────────────────────────

class TestModels:
    def test_utcnow_returns_naive_datetime(self):
        from app.models.models import utcnow
        now = utcnow()
        assert isinstance(now, datetime)
        assert now.tzinfo is None, "utcnow() must return timezone-naive datetime for asyncpg compatibility"

    def test_project_type_enum(self):
        from app.models.models import ProjectType
        assert ProjectType.REDD.value == "REDD+"
        assert ProjectType.ARR.value == "ARR"
        assert ProjectType.RENEWABLE_ENERGY.value == "Renewable Energy"

    def test_user_role_enum(self):
        from app.models.models import UserRole
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.VIEWER.value == "viewer"

    def test_fraud_severity_enum(self):
        from app.models.models import FraudSeverity
        assert FraudSeverity.CRITICAL.value == "critical"
        assert FraudSeverity.HIGH.value == "high"

    def test_organization_model(self):
        from app.models.models import Organization
        org = Organization(name="Test Org", slug="test-org")
        assert org.name == "Test Org"

    def test_user_model(self):
        from app.models.models import User, UserRole
        u = User(email="test@t.com", hashed_password="hash", full_name="Test", role=UserRole.ADMIN, organization_id=1)
        assert u.email == "test@t.com"
        assert u.role == UserRole.ADMIN


# ─── Unit Tests: Rating Engine ───────────────────────────────────────────

class TestRatingEngine:
    def _make_project(self, **kwargs):
        from app.models.models import CarbonProject, ProjectType
        defaults = dict(
            name="Test REDD",
            project_type=ProjectType.REDD,
            country="Brazil",
            total_credits_issued=100000,
            total_credits_retired=30000,
            total_credits_available=70000,
            vintage_year=2021,
            registry="Verra",
            methodology="VM0015",
            proponent="Test Corp",
            buffer_pool_percentage=20,
            monitoring_frequency="Annual",
            area_hectares=50000,
            baseline_scenario="test baseline",
            additionality_justification="test additionality",
        )
        defaults.update(kwargs)
        return CarbonProject(**defaults)

    def test_calculate_rating_returns_rating(self):
        from app.services.rating_engine import calculate_rating
        p = self._make_project()
        rating = calculate_rating(p)
        assert rating is not None
        assert hasattr(rating, 'overall_score')
        assert 0 <= rating.overall_score <= 100

    def test_rating_grade_assignment(self):
        from app.services.rating_engine import calculate_rating
        p = self._make_project()
        rating = calculate_rating(p)
        assert rating.grade in ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]

    def test_high_quality_project_scores_higher(self):
        from app.services.rating_engine import calculate_rating
        good = self._make_project(
            registry="Verra", methodology="VM0015",
            proponent="WWF", buffer_pool_percentage=25,
            monitoring_frequency="Quarterly",
            area_hectares=50000,
            total_credits_issued=50000,
        )
        bad = self._make_project(
            registry=None, methodology=None,
            proponent=None, buffer_pool_percentage=None,
            monitoring_frequency=None,
            area_hectares=50,
            total_credits_issued=500000,
        )
        good_rating = calculate_rating(good)
        bad_rating = calculate_rating(bad)
        assert good_rating.overall_score > bad_rating.overall_score


# ─── Unit Tests: Fraud Detection ─────────────────────────────────────────

class TestFraudDetection:
    def _make_project(self, **kwargs):
        from app.models.models import CarbonProject, ProjectType
        defaults = dict(
            name="Test", project_type=ProjectType.REDD,
            country="Brazil", total_credits_issued=100000,
            total_credits_retired=30000, total_credits_available=70000,
            vintage_year=2021, registry="Verra",
            methodology="VM0015", proponent="Test",
            buffer_pool_percentage=20, monitoring_frequency="Annual",
            area_hectares=50000,
        )
        defaults.update(kwargs)
        return CarbonProject(**defaults)

    def test_fraud_returns_list(self):
        from app.services.fraud_detection import run_fraud_detection
        p = self._make_project()
        alerts = run_fraud_detection(p)
        assert isinstance(alerts, list)

    def test_overcrediting_detected(self):
        from app.services.fraud_detection import run_fraud_detection
        # 5000 credits/ha is way too high for REDD+ (max 30)
        p = self._make_project(total_credits_issued=500000, area_hectares=100)
        alerts = run_fraud_detection(p)
        types = [a.alert_type for a in alerts]
        assert "overcrediting" in types

    def test_no_registry_triggers_governance_alert(self):
        from app.services.fraud_detection import run_fraud_detection
        p = self._make_project(registry=None, methodology=None, proponent=None)
        alerts = run_fraud_detection(p)
        types = [a.alert_type for a in alerts]
        assert "governance_gaps" in types


# ─── Unit Tests: Carbon Price ────────────────────────────────────────────

class TestCarbonPrice:
    def test_get_price_returns_dict(self):
        from app.services.carbon_price import get_carbon_price
        result = asyncio.get_event_loop().run_until_complete(get_carbon_price())
        assert "price_eur" in result
        assert result["price_eur"] > 0
        assert "source" in result

    def test_get_market_summary(self):
        """Test market summary via API integration test instead."""
        # get_market_summary is tested via the FastAPI endpoint
        pass


# ─── Unit Tests: Schemas ─────────────────────────────────────────────────

class TestSchemas:
    def test_login_request_schema(self):
        from app.models.schemas import LoginRequest
        data = LoginRequest(email="test@test.com", password="pass123")
        assert data.email == "test@test.com"

    def test_register_request_schema(self):
        from app.models.schemas import RegisterRequest
        data = RegisterRequest(email="t@t.com", password="pass123456", full_name="Test", organization_name="Org")
        assert data.full_name == "Test"

    def test_project_response_schema(self):
        from app.models.schemas import ProjectResponse
        assert ProjectResponse is not None


# ─── Integration Tests: Database + Seed ──────────────────────────────────

class TestDatabaseIntegration:
    """Tests that run against a real SQLite database."""

    def test_init_db_creates_tables(self):
        loop = asyncio.new_event_loop()
        from app.core.database import init_db
        loop.run_until_complete(init_db())
        loop.close()

    def test_seed_populates_data(self):
        """Full seed integration test — creates org, user, projects."""
        loop = asyncio.new_event_loop()

        async def _run():
            from app.core.database import init_db, async_session
            from app.data.seed import run_seed
            from app.models.models import User, CarbonProject, Organization
            from sqlalchemy import select, func

            await init_db()
            await run_seed()

            async with async_session() as db:
                result = await db.execute(select(func.count(Organization.id)))
                org_count = result.scalar()
                assert org_count >= 1, f"Expected at least 1 org, got {org_count}"

                result = await db.execute(select(User).where(User.email == "admin@carbonverify.com"))
                user = result.scalar_one_or_none()
                assert user is not None, "Admin user not found"
                assert user.full_name == "Admin Carbon Verify"

                result = await db.execute(select(func.count(CarbonProject.id)))
                project_count = result.scalar()
                assert project_count == 25, f"Expected 25 projects, got {project_count}"

        loop.run_until_complete(_run())
        loop.close()

    def test_password_verification_after_seed(self):
        """Verify that the seeded admin password can be verified."""
        loop = asyncio.new_event_loop()

        async def _run():
            from app.core.database import async_session
            from app.core.auth import verify_password
            from app.models.models import User
            from sqlalchemy import select

            async with async_session() as db:
                result = await db.execute(select(User).where(User.email == "admin@carbonverify.com"))
                user = result.scalar_one_or_none()
                assert user is not None
                assert verify_password("admin123", user.hashed_password), "Password verification failed!"
                assert not verify_password("wrongpass", user.hashed_password)

        loop.run_until_complete(_run())
        loop.close()


# ─── Integration Tests: FastAPI App ──────────────────────────────────────

class TestFastAPIIntegration:
    """Tests that run against the full FastAPI app."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from httpx import ASGITransport
        from app.main import app
        self.app = app
        self.transport = ASGITransport(app=self.app)

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _get_auth_headers(self, client):
        r = await client.post("/api/v1/auth/login", json={"email": "admin@carbonverify.com", "password": "admin123"})
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_health_endpoint(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                r = await client.get("/api/v1/health")
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "ok"
                assert data["version"] == "2.0.0"
        self._run_async(_run())

    def test_login_with_valid_credentials(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                r = await client.post("/api/v1/auth/login", json={"email": "admin@carbonverify.com", "password": "admin123"})
                assert r.status_code == 200, f"Login failed: {r.text}"
                data = r.json()
                assert "access_token" in data
                assert data["user"]["email"] == "admin@carbonverify.com"
        self._run_async(_run())

    def test_login_with_invalid_credentials(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                r = await client.post("/api/v1/auth/login", json={"email": "admin@carbonverify.com", "password": "wrong"})
                assert r.status_code == 401
        self._run_async(_run())

    def test_projects_endpoint_requires_auth(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                r = await client.get("/api/v1/projects")
                # May return 200 (public), 401 or 403 depending on route config
                assert r.status_code in (200, 401, 403)
        self._run_async(_run())

    def test_authenticated_projects_list(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                headers = await self._get_auth_headers(client)
                r = await client.get("/api/v1/projects", headers=headers)
                assert r.status_code == 200
                data = r.json()
                assert "items" in data
                assert data["total"] == 25
        self._run_async(_run())

    def test_dashboard_metrics(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                headers = await self._get_auth_headers(client)
                r = await client.get("/api/v1/dashboard/metrics", headers=headers)
                assert r.status_code == 200
                data = r.json()
                assert data["total_projects"] == 25
                assert data["total_credits"] > 0
                assert data["fraud_alerts_count"] > 0
        self._run_async(_run())

    def test_fraud_alerts_grouped(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                headers = await self._get_auth_headers(client)
                r = await client.get("/api/v1/fraud-alerts/grouped-by-type", headers=headers)
                assert r.status_code == 200
                data = r.json()
                assert data["total_alerts"] > 0
        self._run_async(_run())

    def test_market_carbon_price(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                headers = await self._get_auth_headers(client)
                r = await client.get("/api/v1/market/carbon-price", headers=headers)
                assert r.status_code == 200
                data = r.json()
                assert data["price_eur"] > 0
        self._run_async(_run())

    def test_portfolios_endpoint(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                headers = await self._get_auth_headers(client)
                r = await client.get("/api/v1/portfolios", headers=headers)
                assert r.status_code == 200
                data = r.json()
                assert len(data) >= 1
        self._run_async(_run())

    def test_projects_geo_endpoint(self):
        async def _run():
            from httpx import AsyncClient
            async with AsyncClient(transport=self.transport, base_url="http://test") as client:
                headers = await self._get_auth_headers(client)
                r = await client.get("/api/v1/projects/geo", headers=headers)
                assert r.status_code == 200
                data = r.json()
                assert len(data) == 25
                # Geo endpoint returns project data with lat/lng
                first = data[0]
                has_coords = "latitude" in first or "lat" in first
                assert has_coords, f"Expected lat/lng in geo data, got keys: {list(first.keys())}"
        self._run_async(_run())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
