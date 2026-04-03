"""Carbon Verify v3 — Domain Models (Production).

Complete domain model with 20+ entities covering:
- Multi-tenant organizations & workspaces
- Carbon projects with jurisdiction support
- Rating system with dynamic pillars
- Fraud Ops with entity graph
- Portfolio with risk-adjusted tonnes
- Compliance (CSRD/ESRS, SBTi, ICVCM)
- Market intelligence & price data
- Approval workflows
- Audit trail
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════

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


class WorkspaceProfileType(str, enum.Enum):
    SUSTAINABILITY = "sustainability"
    RISK_COMPLIANCE = "risk_compliance"
    LEGAL = "legal"
    PROCUREMENT = "procurement"
    EXTERNAL_AUDIT = "external_audit"
    CUSTOM = "custom"


class EntityType(str, enum.Enum):
    DEVELOPER = "developer"
    BROKER = "broker"
    BUYER = "buyer"
    VERIFIER = "verifier"
    PLATFORM = "platform"
    REGISTRY = "registry"


class ComplianceFrameworkType(str, enum.Enum):
    CSRD_ESRS = "csrd_esrs"
    SBTI = "sbti"
    ICVCM = "icvcm"
    ETS_CBAM = "ets_cbam"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_INFO = "needs_info"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    XBRL = "xbrl"


class ReportType(str, enum.Enum):
    PORTFOLIO = "portfolio"
    DUE_DILIGENCE = "due_diligence"
    FRAUD = "fraud"
    ESG = "esg"
    EXECUTIVE = "executive"
    COMPLIANCE = "compliance"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class IntegrationSource(str, enum.Enum):
    VERRA = "verra"
    GOLD_STANDARD = "gold_standard"
    ACR = "acr"
    CAR = "car"
    PLAN_VIVO = "plan_vivo"
    INPE = "inpe"
    IBGE = "ibge"


# ═══════════════════════════════════════════════════════════════════════════
# ORGANIZATION & AUTH
# ═══════════════════════════════════════════════════════════════════════════

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    api_key = Column(String(500), nullable=True)
    plan = Column(String(50), default="free")
    rate_limit = Column(Integer, default=60)
    locale = Column(String(10), default="pt-BR")
    settings = Column(JSON, nullable=True)
    jurisdiction_id = Column(Integer, ForeignKey("jurisdictions.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    users = relationship("User", back_populates="organization")
    portfolios = relationship("Portfolio", back_populates="organization")
    workspaces = relationship("Workspace", back_populates="organization")
    emissions = relationship("CorporateEmission", back_populates="organization")
    carbon_balances = relationship("CarbonBalance", back_populates="organization")
    jurisdiction = relationship("Jurisdiction", back_populates="organizations")


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
    workspace_memberships = relationship("WorkspaceMembership", back_populates="user")
    approval_steps = relationship("ApprovalStep", back_populates="user")


# ═══════════════════════════════════════════════════════════════════════════
# WORKSPACE (Multi-stakeholder)
# ═══════════════════════════════════════════════════════════════════════════

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    profile_type = Column(SQLEnum(WorkspaceProfileType), default=WorkspaceProfileType.SUSTAINABILITY)
    visible_modules = Column(JSON, nullable=True)
    allowed_actions = Column(JSON, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    organization = relationship("Organization", back_populates="workspaces")
    memberships = relationship("WorkspaceMembership", back_populates="workspace")
    approval_flows = relationship("ApprovalFlow", back_populates="workspace")


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    role = Column(String(50), default="member")
    permissions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="workspace_memberships")
    workspace = relationship("Workspace", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_user_workspace"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# JURISDICTION (Brasil/LatAm + International)
# ═══════════════════════════════════════════════════════════════════════════

class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, unique=True)  # BR, CO, US, EU
    name = Column(String(255), nullable=False)
    region = Column(String(100), nullable=True)  # LatAm, Europe, Asia
    regulatory_fields = Column(JSON, nullable=True)  # extra fields per jurisdiction
    data_sources = Column(JSON, nullable=True)  # INPE, IBGE, etc.
    compliance_requirements = Column(JSON, nullable=True)  # SINARE, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    organizations = relationship("Organization", back_populates="jurisdiction")


# ═══════════════════════════════════════════════════════════════════════════
# CARBON PROJECT
# ═══════════════════════════════════════════════════════════════════════════

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

    # Integration fields
    verra_id = Column(String(100), nullable=True)
    gs_id = Column(String(100), nullable=True)
    sinare_id = Column(String(100), nullable=True)  # Brazil SINARE
    sdg_contributions = Column(JSON, nullable=True)
    integration_source = Column(String(50), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)

    # Entity graph linkage
    developer_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    jurisdiction_id = Column(Integer, ForeignKey("jurisdictions.id"), nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    credits = relationship("CreditBatch", back_populates="project")
    rating = relationship("ProjectRating", back_populates="project", uselist=False)
    fraud_alerts = relationship("FraudAlert", back_populates="project")
    satellite_observations = relationship("SatelliteObservation", back_populates="project")
    compliance_mappings = relationship("ComplianceMapping", back_populates="project")
    documents = relationship("ProjectDocument", back_populates="project")
    developer_entity = relationship("Entity", back_populates="projects")
    market_prices = relationship("MarketPrice", back_populates="project")

    __table_args__ = (
        Index("idx_project_country", "country"),
        Index("idx_project_type", "project_type"),
        Index("idx_project_registry", "registry"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# CREDIT BATCH (renamed from CarbonCredit)
# ═══════════════════════════════════════════════════════════════════════════

class CreditBatch(Base):
    __tablename__ = "credit_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial_number = Column(String(255), nullable=True, unique=True)
    batch_serial = Column(String(255), nullable=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=False)
    vintage_year = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(String(50), default="active")
    issuance_date = Column(DateTime, nullable=True)
    retirement_date = Column(DateTime, nullable=True)
    price_eur = Column(Float, nullable=True)
    verification_body = Column(String(255), nullable=True)
    token_address = Column(String(100), nullable=True)
    tokenized = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("CarbonProject", back_populates="credits")
    positions = relationship("PortfolioPosition", back_populates="credit")


# ═══════════════════════════════════════════════════════════════════════════
# RATING SYSTEM (Dynamic Pillars)
# ═══════════════════════════════════════════════════════════════════════════

class ProjectRating(Base):
    __tablename__ = "project_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=False)
    grade = Column(SQLEnum(RatingGrade), nullable=False)

    # 7 core pillar scores (denormalized for fast queries)
    carbon_integrity_score = Column(Float, default=0)
    additionality_score = Column(Float, default=0)
    permanence_score = Column(Float, default=0)
    leakage_score = Column(Float, default=0)
    mrv_score = Column(Float, default=0)
    co_benefits_score = Column(Float, default=0)
    governance_score = Column(Float, default=0)

    satellite_confidence_score = Column(Float, nullable=True)
    methodology_version = Column(String(50), default="v3.0")
    confidence_level = Column(Float, default=0.0)
    explanation = Column(Text, nullable=True)
    risk_flags = Column(JSON, nullable=True)

    # Risk-adjusted discount factor
    discount_factor = Column(Float, default=1.0)

    rated_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("CarbonProject", back_populates="rating")
    pillars = relationship("RatingPillar", back_populates="rating")
    evidences = relationship("Evidence", back_populates="rating")


class RatingPillar(Base):
    """Dynamic pillar scores — allows methodology-specific pillars."""
    __tablename__ = "rating_pillars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rating_id = Column(Integer, ForeignKey("project_ratings.id"), nullable=False)
    pillar_name = Column(String(100), nullable=False)
    score = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    max_score = Column(Float, default=100.0)
    methodology_specific = Column(Boolean, default=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    rating = relationship("ProjectRating", back_populates="pillars")


# ═══════════════════════════════════════════════════════════════════════════
# FRAUD OPS (Entity Graph + Alerts)
# ═══════════════════════════════════════════════════════════════════════════

class Entity(Base):
    """Node in the entity relationship graph."""
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    jurisdiction_code = Column(String(10), nullable=True)
    sanction_status = Column(String(50), default="clear")  # clear, flagged, sanctioned
    risk_score = Column(Float, default=0.0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    projects = relationship("CarbonProject", back_populates="developer_entity")
    relations_as_source = relationship("EntityRelation", foreign_keys="EntityRelation.source_entity_id", back_populates="source")
    relations_as_target = relationship("EntityRelation", foreign_keys="EntityRelation.target_entity_id", back_populates="target")


class EntityRelation(Base):
    """Edge in the entity relationship graph."""
    __tablename__ = "entity_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    relation_type = Column(String(100), nullable=False)  # develops, brokers, buys_from, verifies
    metadata_json = Column(JSON, nullable=True)
    first_seen = Column(DateTime, default=utcnow)
    last_seen = Column(DateTime, default=utcnow)

    source = relationship("Entity", foreign_keys=[source_entity_id], back_populates="relations_as_source")
    target = relationship("Entity", foreign_keys=[target_entity_id], back_populates="relations_as_target")


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

    # Fraud Ops specific
    fraud_ops_score = Column(Float, nullable=True)
    entity_graph_refs = Column(JSON, nullable=True)  # linked entity IDs
    enforcement_source = Column(String(255), nullable=True)

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


# ═══════════════════════════════════════════════════════════════════════════
# PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════

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
    portfolio_rating = relationship("PortfolioRating", back_populates="portfolio", uselist=False)


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    credit_id = Column(Integer, ForeignKey("credit_batches.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    acquisition_price_eur = Column(Float, nullable=True)
    acquisition_date = Column(DateTime, nullable=True)
    planned_retirement_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    portfolio = relationship("Portfolio", back_populates="positions")
    credit = relationship("CreditBatch", back_populates="positions")


class PortfolioRating(Base):
    """Aggregated rating for a portfolio."""
    __tablename__ = "portfolio_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=False)
    grade = Column(SQLEnum(RatingGrade), nullable=False)
    risk_adjusted_tonnes = Column(Float, default=0)
    nominal_tonnes = Column(Float, default=0)
    discount_factor_avg = Column(Float, default=1.0)
    grade_distribution = Column(JSON, nullable=True)
    concentration_risk = Column(JSON, nullable=True)
    calculated_at = Column(DateTime, default=utcnow)

    portfolio = relationship("Portfolio", back_populates="portfolio_rating")


# ═══════════════════════════════════════════════════════════════════════════
# COMPLIANCE (CSRD/ESRS, SBTi, ICVCM)
# ═══════════════════════════════════════════════════════════════════════════

class ComplianceFramework(Base):
    __tablename__ = "compliance_frameworks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)  # csrd_e1_5, sbti, icvcm
    name = Column(String(255), nullable=False)
    framework_type = Column(SQLEnum(ComplianceFrameworkType), nullable=False)
    version = Column(String(50), default="1.0")
    disclosure_items = Column(JSON, nullable=True)  # list of disclosure line items
    requirements = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    mappings = relationship("ComplianceMapping", back_populates="framework")


class ComplianceMapping(Base):
    """Maps a project/portfolio to specific compliance disclosure items."""
    __tablename__ = "compliance_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    framework_id = Column(Integer, ForeignKey("compliance_frameworks.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    disclosure_item = Column(String(100), nullable=False)  # E1-5, E1-7, E1-9
    status = Column(String(50), default="mapped")  # mapped, verified, gap
    coverage_pct = Column(Float, default=0.0)
    details = Column(JSON, nullable=True)
    evidence_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    framework = relationship("ComplianceFramework", back_populates="mappings")
    project = relationship("CarbonProject", back_populates="compliance_mappings")
    evidence_links = relationship("EvidenceLink", back_populates="compliance_mapping")


# ═══════════════════════════════════════════════════════════════════════════
# EVIDENCE & DOCUMENTS
# ═══════════════════════════════════════════════════════════════════════════

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evidence_type = Column(String(100), nullable=False)  # document, satellite_image, data_point, calculation_log
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)  # S3/MinIO path
    data_snapshot = Column(JSON, nullable=True)  # raw data if inline
    source = Column(String(255), nullable=True)
    rating_id = Column(Integer, ForeignKey("project_ratings.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    rating = relationship("ProjectRating", back_populates="evidences")
    evidence_links = relationship("EvidenceLink", back_populates="evidence")


class EvidenceLink(Base):
    """Links evidence to compliance mappings."""
    __tablename__ = "evidence_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evidence_id = Column(Integer, ForeignKey("evidences.id"), nullable=False)
    compliance_mapping_id = Column(Integer, ForeignKey("compliance_mappings.id"), nullable=False)
    relevance_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    evidence = relationship("Evidence", back_populates="evidence_links")
    compliance_mapping = relationship("ComplianceMapping", back_populates="evidence_links")


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=False)
    document_type = Column(String(100), nullable=False)  # pdd, monitoring_report, verification_report
    title = Column(String(500), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=utcnow)

    project = relationship("CarbonProject", back_populates="documents")


# ═══════════════════════════════════════════════════════════════════════════
# MARKET INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════

class MarketPrice(Base):
    """Price data per project type/rating/vintage for frontier analysis."""
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("carbon_projects.id"), nullable=True)
    project_type = Column(String(100), nullable=True)
    grade = Column(String(10), nullable=True)
    vintage_year = Column(Integer, nullable=True)
    price_eur = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    liquidity_score = Column(Float, nullable=True)  # 0-1
    source = Column(String(100), nullable=True)
    recorded_at = Column(DateTime, default=utcnow)

    project = relationship("CarbonProject", back_populates="market_prices")

    __table_args__ = (
        Index("idx_market_price_type", "project_type"),
        Index("idx_market_price_grade", "grade"),
    )


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


# ═══════════════════════════════════════════════════════════════════════════
# APPROVAL WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════

class ApprovalFlow(Base):
    __tablename__ = "approval_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    flow_type = Column(String(100), nullable=False)  # credit_purchase, portfolio_change, compliance_sign_off
    required_steps = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    workspace = relationship("Workspace", back_populates="approval_flows")
    steps = relationship("ApprovalStep", back_populates="flow")


class ApprovalStep(Base):
    __tablename__ = "approval_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_id = Column(Integer, ForeignKey("approval_flows.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role_required = Column(String(50), nullable=True)
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    decision_note = Column(Text, nullable=True)
    evidence_ids = Column(JSON, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    flow = relationship("ApprovalFlow", back_populates="steps")
    user = relationship("User", back_populates="approval_steps")


# ═══════════════════════════════════════════════════════════════════════════
# SATELLITE & OBSERVATIONS
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# CORPORATE EMISSIONS (ESG)
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# REPORTS, AUDIT, INTEGRATION SYNC, METRICS
# ═══════════════════════════════════════════════════════════════════════════

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
    compliance_framework = Column(String(50), nullable=True)
    xbrl_data = Column(JSON, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    event_type = Column(String(100), nullable=True)  # project.created, rating.calculated, etc.
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True)
    tenant_id = Column(Integer, nullable=True)  # organization_id for isolation
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_tenant", "tenant_id"),
    )


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


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY ALIASES
# ═══════════════════════════════════════════════════════════════════════════
CarbonCredit = CreditBatch  # Legacy alias
