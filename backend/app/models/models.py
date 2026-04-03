"""Modelos SQLAlchemy para Carbon Verify - Produção."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ─── Enums ───────────────────────────────────────────────────────────────

class RatingGrade(str, enum.Enum):
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"


class ProjectType(str, enum.Enum):
    REDD = "REDD+"
    ARR = "ARR"
    RENEWABLE_ENERGY = "Renewable Energy"
    COOKSTOVE = "Cookstove"
    METHANE = "Methane Avoidance"
    BLUE_CARBON = "Blue Carbon"
    BIOCHAR = "Biochar"
    DAC = "Direct Air Capture"
    OTHER = "Other"


class FraudSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"


class ReportType(str, enum.Enum):
    PORTFOLIO = "portfolio"
    DUE_DILIGENCE = "due_diligence"
    FRAUD = "fraud"
    ESG = "esg"
    EXECUTIVE = "executive"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class IntegrationSource(str, enum.Enum):
    VERRA = "verra"
    GOLD_STANDARD = "gold_standard"
    CARBONMARK = "carbonmark"
    TOUCAN = "toucan"
    PLAN_A = "plan_a"
    NORMATIVE = "normative"


# ─── Organization ────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    api_key = Column(String(500), nullable=True)
    plan = Column(String(50), default="free")
    rate_limit = Column(Integer, default=60)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    users = relationship("User", back_populates="organization")
    portfolios = relationship("Portfolio", back_populates="organization")
    emissions = relationship("CorporateEmission", back_populates="organization")
    carbon_balances = relationship("CarbonBalance", back_populates="organization")


# ─── User ────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.ANALYST)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    organization = relationship("Organization", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


# ─── Carbon Project ─────────────────────────────────────────────────────

class CarbonProject(Base):
    __tablename__ = "carbon_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), nullable=True, unique=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(SQLEnum(ProjectType), nullable=False)
    methodology = Column(String(255), nullable=True)
    registry = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False)
    region = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    proponent = Column(String(255), nullable=True)
    total_credits_issued = Column(Integer, default=0)
    total_credits_retired = Column(Integer, default=0)
    total_credits_available = Column(Integer, default=0)
    vintage_year = Column(Integer, nullable=True)
    area_hectares = Column(Float, nullable=True)
    baseline_scenario = Column(Text, nullable=True)
    additionality_justification = Column(Text, nullable=True)
    monitoring_frequency = Column(String(100), nullable=True)
    buffer_pool_percentage = Column(Float, nullable=True)

    # Novos campos para integrações
    verra_id = Column(String(100), nullable=True)
    gs_id = Column(String(100), nullable=True)
    sdg_contributions = Column(JSON, nullable=True)
    integration_source = Column(String(50), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    credits = relationship("CarbonCredit", back_populates="project")
    rating = relationship("ProjectRating", back_populates="project", uselist=False)
    fraud_alerts = relationship("FraudAlert", back_populates="project")
    satellite_observations = relationship("SatelliteObservation", back_populates="project")

    __table_args__ = (
        Index("idx_project_country", "country"),
        Index("idx_project_type", "project_type"),
        Index("idx_project_registry", "registry"),
    )


# ─── Carbon Credit ──────────────────────────────────────────────────────

class CarbonCredit(Base):
    __tablename__ = "carbon_credits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial_number = Column(String(255), nullable=True, unique=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=False)
    vintage_year = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(String(50), default="active")
    issuance_date = Column(DateTime, nullable=True)
    retirement_date = Column(DateTime, nullable=True)
    price_eur = Column(Float, nullable=True)
    token_address = Column(String(100), nullable=True)
    tokenized = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("CarbonProject", back_populates="credits")
    positions = relationship("PortfolioPosition", back_populates="credit")


# ─── Rating de Qualidade ─────────────────────────────────────────────────

class ProjectRating(Base):
    __tablename__ = "project_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=False)
    grade = Column(SQLEnum(RatingGrade), nullable=False)
    additionality_score = Column(Float, default=0)
    permanence_score = Column(Float, default=0)
    leakage_score = Column(Float, default=0)
    mrv_score = Column(Float, default=0)
    co_benefits_score = Column(Float, default=0)
    governance_score = Column(Float, default=0)
    baseline_integrity_score = Column(Float, default=0)
    satellite_confidence_score = Column(Float, nullable=True)
    methodology_version = Column(String(50), default="v2.0")
    confidence_level = Column(Float, default=0.0)
    explanation = Column(Text, nullable=True)
    risk_flags = Column(JSON, nullable=True)
    rated_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("CarbonProject", back_populates="rating")


# ─── Fraud Detection ────────────────────────────────────────────────────

class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=False)
    alert_type = Column(String(100), nullable=False)
    severity = Column(SQLEnum(FraudSeverity), nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.OPEN)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)
    recommendation = Column(Text, nullable=True)
    detection_method = Column(String(100), nullable=True)
    confidence = Column(Float, default=0.0)
    reviewed_by = Column(String(255), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("CarbonProject", back_populates="fraud_alerts")

    __table_args__ = (
        Index("idx_fraud_severity", "severity"),
        Index("idx_fraud_type", "alert_type"),
        Index("idx_fraud_status", "status"),
    )


# ─── Portfolio ───────────────────────────────────────────────────────────

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    description = Column(Text, nullable=True)
    total_credits = Column(Integer, default=0)
    total_value_eur = Column(Float, default=0)
    avg_quality_score = Column(Float, default=0)
    risk_exposure = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="portfolios")
    positions = relationship("PortfolioPosition", back_populates="portfolio")


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    credit_id = Column(Integer, ForeignKey("carbon_credits.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    acquisition_price_eur = Column(Float, nullable=True)
    acquisition_date = Column(DateTime, nullable=True)
    planned_retirement_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    portfolio = relationship("Portfolio", back_populates="positions")
    credit = relationship("CarbonCredit", back_populates="positions")


# ─── Market Data ─────────────────────────────────────────────────────────

class CarbonPriceHistory(Base):
    __tablename__ = "carbon_price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    price_eur = Column(Float, nullable=False)
    previous_close_eur = Column(Float, nullable=True)
    change_24h = Column(Float, nullable=True)
    change_pct_24h = Column(Float, nullable=True)
    day_high_eur = Column(Float, nullable=True)
    day_low_eur = Column(Float, nullable=True)
    market = Column(String(100), default="EU ETS")
    source = Column(String(100), nullable=True)
    recorded_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_price_recorded", "recorded_at"),
    )


# ─── Reports ─────────────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    report_type = Column(SQLEnum(ReportType), nullable=False)
    format = Column(SQLEnum(ReportFormat), nullable=False)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.PENDING)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    parameters = Column(JSON, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


# ─── Audit Log ───────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
    )


# ─── Integration Sync ───────────────────────────────────────────────────

class IntegrationSync(Base):
    __tablename__ = "integration_syncs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(SQLEnum(IntegrationSource), nullable=False)
    status = Column(String(50), default="idle")
    last_sync_at = Column(DateTime, nullable=True)
    projects_synced = Column(Integer, default=0)
    projects_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)


# ─── Satellite Observation ───────────────────────────────────────────────

class SatelliteObservation(Base):
    __tablename__ = "satellite_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=False)
    satellite = Column(String(100), nullable=False)
    observation_type = Column(String(100), nullable=False)
    value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    observed_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("CarbonProject", back_populates="satellite_observations")

    __table_args__ = (
        Index("idx_sat_project", "project_id"),
        Index("idx_sat_type", "observation_type"),
    )


# ─── Corporate Emissions (ESG) ──────────────────────────────────────────

class CorporateEmission(Base):
    __tablename__ = "corporate_emissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    scope = Column(String(20), nullable=False)
    amount_tco2e = Column(Float, nullable=False)
    year = Column(Integer, nullable=False)
    category = Column(String(100), nullable=True)
    source_description = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    organization = relationship("Organization", back_populates="emissions")


# ─── Carbon Balance (Accounting) ────────────────────────────────────────

class CarbonBalance(Base):
    __tablename__ = "carbon_balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    period = Column(String(20), nullable=False)
    total_emissions = Column(Float, default=0)
    total_offsets = Column(Float, default=0)
    net_balance = Column(Float, default=0)
    created_at = Column(DateTime, default=utcnow)

    organization = relationship("Organization", back_populates="carbon_balances")


# ─── Metric Snapshot (Analytics) ─────────────────────────────────────────

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_metric_name_date", "metric_name", "recorded_at"),
    )
