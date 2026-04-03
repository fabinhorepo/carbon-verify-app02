"""Carbon Verify v3 — Seed Data (Production).

Creates 30 projects with full data, ratings, fraud alerts,
credit batches, portfolio positions, entities, compliance frameworks,
jurisdictions, workspaces, and market prices.
"""
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import async_session
from app.models.models import (
    Organization, User, CarbonProject, CreditBatch, ProjectRating,
    RatingPillar, FraudAlert, Portfolio, PortfolioPosition,
    CarbonPriceHistory, SatelliteObservation, CorporateEmission,
    CarbonBalance, IntegrationSync, MetricSnapshot,
    Entity, EntityRelation, Jurisdiction, Workspace, WorkspaceMembership,
    ComplianceFramework, MarketPrice,
    ProjectType, RatingGrade, FraudSeverity, UserRole,
    WorkspaceProfileType, EntityType, ComplianceFrameworkType,
    IntegrationSource,
)
from app.modules.rating.service import calculate_rating
from app.modules.fraud_ops.service import run_fraud_detection
import bcrypt

def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
rng = random.Random(42)


PROJECTS_DATA = [
    {"name": "Amazônia REDD+ Xingu", "type": ProjectType.REDD, "country": "Brazil", "registry": "Verra", "methodology": "VM0015", "area": 85000, "credits": 450000, "retired": 180000, "vintage": 2020, "lat": -3.5, "lng": -52.0, "proponent": "Conservation Intl Brazil", "buffer": 18, "region": "Pará", "monitoring": "Semestral"},
    {"name": "Cerrado Restoration Project", "type": ProjectType.ARR, "country": "Brazil", "registry": "Verra", "methodology": "AR-ACM0003", "area": 12000, "credits": 85000, "retired": 34000, "vintage": 2021, "lat": -15.8, "lng": -47.9, "proponent": "Instituto Terra", "buffer": 20, "region": "Goiás", "monitoring": "Anual"},
    {"name": "Atlantic Forest Blue Carbon", "type": ProjectType.BLUE_CARBON, "country": "Brazil", "registry": "Gold Standard", "methodology": "GS-Mangrove", "area": 5500, "credits": 25000, "retired": 12000, "vintage": 2022, "lat": -23.5, "lng": -46.6, "proponent": "SOS Mata Atlântica", "buffer": 15, "region": "São Paulo", "monitoring": "Trimestral"},
    {"name": "Kalimantan Peatland Protection", "type": ProjectType.REDD, "country": "Indonesia", "registry": "Verra", "methodology": "VM0007", "area": 150000, "credits": 800000, "retired": 350000, "vintage": 2019, "lat": -2.0, "lng": 113.5, "proponent": "Permian Global", "buffer": 12, "region": "Borneo", "monitoring": "Anual"},
    {"name": "Kenya Improved Cookstoves", "type": ProjectType.COOKSTOVE, "country": "Kenya", "registry": "Gold Standard", "methodology": "GS-TPDDTEC", "area": None, "credits": 120000, "retired": 90000, "vintage": 2021, "lat": -1.3, "lng": 36.8, "proponent": "BURN Manufacturing", "buffer": None, "region": "Nairobi", "monitoring": "Anual"},
    {"name": "India Wind Power Gujarat", "type": ProjectType.RENEWABLE_ENERGY, "country": "India", "registry": "Verra", "methodology": "ACM0002", "area": None, "credits": 250000, "retired": 200000, "vintage": 2018, "lat": 22.3, "lng": 71.8, "proponent": "Suzlon Energy", "buffer": None, "region": "Gujarat", "monitoring": "Anual"},
    {"name": "Colombia Cloud Forest REDD+", "type": ProjectType.REDD, "country": "Colombia", "registry": "Verra", "methodology": "VM0006", "area": 48000, "credits": 220000, "retired": 88000, "vintage": 2020, "lat": 5.0, "lng": -75.5, "proponent": "Fondo Acción", "buffer": 16, "region": "Antioquia", "monitoring": "Semestral"},
    {"name": "Ethiopia Biochar Initiative", "type": ProjectType.BIOCHAR, "country": "Ethiopia", "registry": "Verra", "methodology": "VM0044", "area": 2500, "credits": 35000, "retired": 10000, "vintage": 2022, "lat": 9.0, "lng": 38.7, "proponent": "Biochar Africa", "buffer": 20, "region": "Amhara", "monitoring": "Trimestral"},
    {"name": "Iceland DAC Orca Facility", "type": ProjectType.DAC, "country": "Iceland", "registry": "Gold Standard", "methodology": "GS-DAC", "area": 15, "credits": 4000, "retired": 3500, "vintage": 2023, "lat": 63.9, "lng": -21.9, "proponent": "Climeworks AG", "buffer": None, "region": "Reykjanes", "monitoring": "Trimestral"},
    {"name": "Peru Methane Capture", "type": ProjectType.METHANE, "country": "Peru", "registry": "ACR", "methodology": "ACR-MCA", "area": 500, "credits": 60000, "retired": 25000, "vintage": 2021, "lat": -12.0, "lng": -77.0, "proponent": "Veolia LatAm", "buffer": None, "region": "Lima", "monitoring": "Semestral"},
    {"name": "Congo Basin Forest Protection", "type": ProjectType.REDD, "country": "Congo", "registry": "Verra", "methodology": "VM0009", "area": 300000, "credits": 1500000, "retired": 450000, "vintage": 2019, "lat": -1.5, "lng": 24.0, "proponent": "Wildlife Works", "buffer": 10, "region": "Mai-Ndombe", "monitoring": "Anual"},
    {"name": "Vietnam Solar Energy", "type": ProjectType.RENEWABLE_ENERGY, "country": "Vietnam", "registry": "Gold Standard", "methodology": "GS-Solar", "area": None, "credits": 180000, "retired": 150000, "vintage": 2020, "lat": 10.8, "lng": 106.7, "proponent": "Vietnam Green Power", "buffer": None, "region": "Ho Chi Minh", "monitoring": "Anual"},
    {"name": "Honduras Community Forest", "type": ProjectType.ARR, "country": "Honduras", "registry": "Plan Vivo", "methodology": "PV-ARR", "area": 8000, "credits": 40000, "retired": 15000, "vintage": 2021, "lat": 14.1, "lng": -87.2, "proponent": "Lenca Communities", "buffer": 22, "region": "La Paz", "monitoring": "Semestral"},
    {"name": "Mexico Avoided Deforestation", "type": ProjectType.REDD, "country": "Mexico", "registry": "Verra", "methodology": "VM0015", "area": 65000, "credits": 320000, "retired": 128000, "vintage": 2020, "lat": 18.5, "lng": -90.5, "proponent": "CONAFOR", "buffer": 14, "region": "Yucatán", "monitoring": "Anual"},
    {"name": "Argentina Wind Farm Patagonia", "type": ProjectType.RENEWABLE_ENERGY, "country": "Argentina", "registry": "Verra", "methodology": "ACM0002", "area": None, "credits": 300000, "retired": 250000, "vintage": 2019, "lat": -43.3, "lng": -65.1, "proponent": "Genneia", "buffer": None, "region": "Chubut", "monitoring": "Anual"},
    {"name": "Paraguay Chaco Conservation", "type": ProjectType.REDD, "country": "Paraguay", "registry": "Verra", "methodology": "VM0015", "area": 72000, "credits": 180000, "retired": 50000, "vintage": 2022, "lat": -21.5, "lng": -59.5, "proponent": "World Land Trust", "buffer": 5, "region": "Chaco", "monitoring": "Anual"},
    {"name": "Cambodia Mangrove Restoration", "type": ProjectType.BLUE_CARBON, "country": "Cambodia", "registry": "Verra", "methodology": "VM0033", "area": 3200, "credits": 18000, "retired": 8000, "vintage": 2022, "lat": 11.5, "lng": 104.9, "proponent": "WorldFish", "buffer": 18, "region": "Kampot", "monitoring": "Semestral"},
    {"name": "Chile Biochar Soil Carbon", "type": ProjectType.BIOCHAR, "country": "Chile", "registry": "ACR", "methodology": "ACR-Biochar", "area": 1800, "credits": 22000, "retired": 8000, "vintage": 2023, "lat": -33.4, "lng": -70.6, "proponent": "BioChar Chile", "buffer": 25, "region": "Santiago", "monitoring": "Trimestral"},
    {"name": "Uganda Cookstove Distribution", "type": ProjectType.COOKSTOVE, "country": "Uganda", "registry": "Gold Standard", "methodology": "GS-TPDDTEC", "area": None, "credits": 95000, "retired": 70000, "vintage": 2020, "lat": 0.3, "lng": 32.6, "proponent": "UpEnergy", "buffer": None, "region": "Kampala", "monitoring": "Anual"},
    {"name": "Ghana Cocoa Agroforestry", "type": ProjectType.ARR, "country": "Ghana", "registry": "Gold Standard", "methodology": "GS-ARR", "area": 15000, "credits": 55000, "retired": 20000, "vintage": 2021, "lat": 6.7, "lng": -1.6, "proponent": "Solidaridad", "buffer": 15, "region": "Ashanti", "monitoring": "Semestral"},
    # Problematic/Low quality projects for fraud detection
    {"name": "Unknown Forest Project Alpha", "type": ProjectType.REDD, "country": "Brazil", "registry": None, "methodology": None, "area": 15000000, "credits": 2000000, "retired": 1800000, "vintage": 2008, "lat": -5.0, "lng": -55.0, "proponent": None, "buffer": 2, "region": None, "monitoring": None},
    {"name": "Suspicious Carbon Scheme Beta", "type": ProjectType.OTHER, "country": "Brazil", "registry": None, "methodology": None, "area": None, "credits": 500000, "retired": 450000, "vintage": 2010, "lat": -8.0, "lng": -50.0, "proponent": None, "buffer": None, "region": None, "monitoring": None},
    {"name": "Unverified Renewable Gamma", "type": ProjectType.RENEWABLE_ENERGY, "country": "India", "registry": None, "methodology": None, "area": None, "credits": 150000, "retired": 130000, "vintage": 2009, "lat": 20.0, "lng": 78.0, "proponent": None, "buffer": None, "region": None, "monitoring": None},
    {"name": "Ecuador Cloud Forest REDD", "type": ProjectType.REDD, "country": "Ecuador", "registry": "Verra", "methodology": "VM0015", "area": 22000, "credits": 110000, "retired": 45000, "vintage": 2021, "lat": -0.2, "lng": -78.5, "proponent": "Fundación Jocotoco", "buffer": 17, "region": "Pichincha", "monitoring": "Semestral"},
    {"name": "Bolivia Deforestation Avoidance", "type": ProjectType.REDD, "country": "Bolivia", "registry": "Verra", "methodology": "VM0006", "area": 95000, "credits": 500000, "retired": 200000, "vintage": 2020, "lat": -16.5, "lng": -64.0, "proponent": "Noel Kempff Project", "buffer": 13, "region": "Santa Cruz", "monitoring": "Anual"},
    {"name": "Costa Rica Reforestation", "type": ProjectType.ARR, "country": "Costa Rica", "registry": "Gold Standard", "methodology": "GS-ARR", "area": 6000, "credits": 30000, "retired": 12000, "vintage": 2022, "lat": 9.9, "lng": -84.1, "proponent": "FONAFIFO", "buffer": 20, "region": "San José", "monitoring": "Trimestral"},
    {"name": "Tanzania Efficient Stoves", "type": ProjectType.COOKSTOVE, "country": "Tanzania", "registry": "Gold Standard", "methodology": "GS-TPDDTEC", "area": None, "credits": 75000, "retired": 55000, "vintage": 2021, "lat": -6.8, "lng": 37.7, "proponent": "EzyLife Foundation", "buffer": None, "region": "Dodoma", "monitoring": "Anual"},
    {"name": "Philippines Mangrove Blue Carbon", "type": ProjectType.BLUE_CARBON, "country": "Philippines", "registry": "Verra", "methodology": "VM0033", "area": 4200, "credits": 20000, "retired": 7000, "vintage": 2023, "lat": 14.6, "lng": 121.0, "proponent": "ZSL Philippines", "buffer": 16, "region": "Luzon", "monitoring": "Semestral"},
    {"name": "Uruguay Methane Reduction", "type": ProjectType.METHANE, "country": "Uruguay", "registry": "ACR", "methodology": "ACR-MCA", "area": 300, "credits": 45000, "retired": 20000, "vintage": 2022, "lat": -34.9, "lng": -56.2, "proponent": "UTE Uruguay", "buffer": None, "region": "Montevideo", "monitoring": "Semestral"},
    {"name": "Dominican Republic Solar", "type": ProjectType.RENEWABLE_ENERGY, "country": "Dominican Republic", "registry": "Gold Standard", "methodology": "GS-Solar", "area": None, "credits": 55000, "retired": 40000, "vintage": 2022, "lat": 18.5, "lng": -69.9, "proponent": "DR Solar Corp", "buffer": None, "region": "Santo Domingo", "monitoring": "Anual"},
]


async def run_seed():
    async with async_session() as db:
        existing = (await db.execute(select(Organization))).scalars().first()
        if existing:
            print("✅ Seed: dados já existem, pulando.")
            return

        print("🌱 Seed v3: Criando dados iniciais...")

        # ─── Jurisdictions ───────────────────────────────────────────
        jurisdictions = []
        for code, name, region_name in [
            ("BR", "Brasil", "LatAm"), ("CO", "Colômbia", "LatAm"), ("PE", "Peru", "LatAm"),
            ("MX", "México", "LatAm"), ("AR", "Argentina", "LatAm"), ("CL", "Chile", "LatAm"),
            ("EC", "Equador", "LatAm"), ("BO", "Bolívia", "LatAm"),
            ("US", "Estados Unidos", "North America"), ("EU", "União Europeia", "Europe"),
            ("ID", "Indonésia", "Asia"), ("IN", "Índia", "Asia"),
            ("KE", "Quênia", "Africa"), ("GH", "Gana", "Africa"),
        ]:
            j = Jurisdiction(code=code, name=name, region=region_name,
                             data_sources={"inpe": True, "ibge": True} if code == "BR" else None,
                             compliance_requirements={"sinare": True} if code == "BR" else None)
            db.add(j)
            jurisdictions.append(j)
        await db.flush()

        # ─── Organization & Users ────────────────────────────────────
        org = Organization(name="Carbon Verify Demo", slug="cv-demo", plan="professional",
                           rate_limit=120, locale="pt-BR", jurisdiction_id=jurisdictions[0].id)
        db.add(org)
        await db.flush()

        admin = User(email="admin@carbonverify.com", hashed_password=_hash_pw("admin123"),
                     full_name="Admin Carbon Verify", role=UserRole.ADMIN, organization_id=org.id)
        analyst = User(email="analyst@carbonverify.com", hashed_password=_hash_pw("analyst123"),
                       full_name="Ana Silva (Analista)", role=UserRole.ANALYST, organization_id=org.id)
        viewer = User(email="viewer@carbonverify.com", hashed_password=_hash_pw("viewer123"),
                      full_name="Carlos Viewer", role=UserRole.VIEWER, organization_id=org.id)
        db.add_all([admin, analyst, viewer])
        await db.flush()

        # ─── Workspaces ──────────────────────────────────────────────
        ws_profiles = [
            ("Sustentabilidade", WorkspaceProfileType.SUSTAINABILITY, True),
            ("Risco & Compliance", WorkspaceProfileType.RISK_COMPLIANCE, False),
            ("Jurídico", WorkspaceProfileType.LEGAL, False),
            ("Compras", WorkspaceProfileType.PROCUREMENT, False),
            ("Auditoria", WorkspaceProfileType.EXTERNAL_AUDIT, False),
        ]
        workspaces = []
        for ws_name, ws_type, is_default in ws_profiles:
            ws = Workspace(name=ws_name, organization_id=org.id, profile_type=ws_type, is_default=is_default)
            db.add(ws)
            workspaces.append(ws)
        await db.flush()

        for ws in workspaces:
            db.add(WorkspaceMembership(user_id=admin.id, workspace_id=ws.id, role="admin"))
        db.add(WorkspaceMembership(user_id=analyst.id, workspace_id=workspaces[0].id, role="member"))
        await db.flush()

        # ─── Compliance Frameworks ───────────────────────────────────
        frameworks = [
            ComplianceFramework(code="csrd_e1", name="CSRD / ESRS E1", framework_type=ComplianceFrameworkType.CSRD_ESRS, version="2024"),
            ComplianceFramework(code="sbti", name="SBTi Framework", framework_type=ComplianceFrameworkType.SBTI, version="2024"),
            ComplianceFramework(code="icvcm", name="ICVCM Core Carbon Principles", framework_type=ComplianceFrameworkType.ICVCM, version="2023"),
        ]
        for f in frameworks:
            db.add(f)
        await db.flush()

        # ─── Entities (Graph nodes) ──────────────────────────────────
        entities = []
        entity_data = [
            ("Conservation Intl Brazil", EntityType.DEVELOPER, "BR"),
            ("Permian Global", EntityType.DEVELOPER, "UK"),
            ("Climeworks AG", EntityType.DEVELOPER, "CH"),
            ("Verra", EntityType.REGISTRY, "US"),
            ("Gold Standard", EntityType.REGISTRY, "CH"),
            ("South Pole", EntityType.BROKER, "CH"),
            ("Carbon Trade Exchange", EntityType.PLATFORM, "UK"),
            ("NovaStar Corp", EntityType.BUYER, "BR"),
            ("SCS Global Services", EntityType.VERIFIER, "US"),
        ]
        for e_name, e_type, e_jur in entity_data:
            e = Entity(name=e_name, entity_type=e_type, jurisdiction_code=e_jur, risk_score=rng.uniform(0, 30))
            db.add(e)
            entities.append(e)
        await db.flush()

        # Entity relations
        relations = [
            (0, 3, "registered_with"), (1, 3, "registered_with"), (2, 4, "registered_with"),
            (5, 0, "brokers_for"), (5, 1, "brokers_for"), (6, 5, "platform_for"),
            (7, 5, "buys_through"), (8, 0, "verifies"), (8, 1, "verifies"),
        ]
        for src, tgt, rel_type in relations:
            db.add(EntityRelation(source_entity_id=entities[src].id, target_entity_id=entities[tgt].id, relation_type=rel_type))
        await db.flush()

        # ─── Projects, Ratings, Fraud Alerts ─────────────────────────
        projects = []
        portfolio = Portfolio(name="Portfólio Principal", organization_id=org.id, description="Portfólio de créditos diversificado")
        db.add(portfolio)
        await db.flush()

        for i, pd in enumerate(PROJECTS_DATA):
            start_d = datetime(pd["vintage"] - rng.randint(1, 3), 1, 1, tzinfo=timezone.utc)
            end_d = datetime(pd["vintage"] + rng.randint(10, 25), 12, 31, tzinfo=timezone.utc)
            desc_text = f"Projeto de {pd['type'].value} localizado em {pd['country']}."
            if pd.get("registry"):
                desc_text += f" Registrado no {pd['registry']} com metodologia {pd.get('methodology', 'N/A')}."
            desc_text += f" Área total: {pd.get('area', 'N/A')} hectares." if pd.get("area") else ""
            add_just = None
            if pd.get("methodology"):
                add_just = f"O projeto demonstra adicionalidade através da análise de barreiras financeiras e institucionais. Sem o incentivo dos créditos de carbono, a atividade de {pd['type'].value} não seria viável. Metodologia {pd['methodology']} aplicada com validação independente."
            baseline = None
            if pd.get("area"):
                baseline = f"O cenário de linha de base considera a tendência histórica de uso do solo na região de {pd.get('region', pd['country'])}. Taxas de desmatamento/degradação projetadas com base em dados de sensoriamento remoto dos últimos 10 anos."

            project = CarbonProject(
                external_id=f"CV-{2024+i:04d}-{pd['country'][:2].upper()}", name=pd["name"],
                description=desc_text, project_type=pd["type"], methodology=pd.get("methodology"),
                registry=pd.get("registry"), country=pd["country"], region=pd.get("region"),
                latitude=pd["lat"], longitude=pd["lng"], start_date=start_d, end_date=end_d,
                proponent=pd.get("proponent"), total_credits_issued=pd["credits"],
                total_credits_retired=pd["retired"], total_credits_available=pd["credits"] - pd["retired"],
                vintage_year=pd["vintage"], area_hectares=pd.get("area"),
                baseline_scenario=baseline, additionality_justification=add_just,
                monitoring_frequency=pd.get("monitoring"), buffer_pool_percentage=pd.get("buffer"),
                developer_entity_id=entities[i % len(entities)].id if i < 20 else None,
                sinare_id=f"SINARE-{1000+i}" if pd["country"] == "Brazil" else None,
            )
            db.add(project)
            await db.flush()
            projects.append(project)

            # Rating
            rating, pillars = calculate_rating(project)
            db.add(rating)
            await db.flush()
            for pillar in pillars:
                pillar.rating_id = rating.id
                db.add(pillar)

            # Fraud detection
            alerts = run_fraud_detection(project)
            for a in alerts:
                db.add(a)

            # Credit batches and portfolio positions
            credit = CreditBatch(
                project_id=project.id, serial_number=f"CB-{project.id:04d}-{pd['vintage']}",
                vintage_year=pd["vintage"], quantity=pd["credits"],
                price_eur=round(rng.uniform(3, 28), 2), status="active",
                issuance_date=datetime(pd["vintage"], rng.randint(1, 12), 1, tzinfo=timezone.utc),
                verification_body=rng.choice(["SCS", "SGS", "TÜV SÜD", "DNV"]) if pd.get("registry") else None,
            )
            db.add(credit)
            await db.flush()

            # Add some projects to portfolio
            if i < 20 and rng.random() > 0.3:
                qty = rng.randint(500, 5000)
                pos = PortfolioPosition(
                    portfolio_id=portfolio.id, credit_id=credit.id,
                    quantity=qty, acquisition_price_eur=credit.price_eur,
                    acquisition_date=datetime(pd["vintage"], rng.randint(1, 12), rng.randint(1, 28), tzinfo=timezone.utc),
                )
                db.add(pos)

            # Market prices
            for _ in range(rng.randint(1, 3)):
                mp = MarketPrice(
                    project_id=project.id,
                    project_type=pd["type"].value,
                    grade=rating.grade.value,
                    vintage_year=pd["vintage"],
                    price_eur=round(credit.price_eur * rng.uniform(0.8, 1.3), 2),
                    volume=rng.randint(100, 10000),
                    liquidity_score=round(rng.uniform(0.2, 1.0), 2),
                    source="seed_data",
                )
                db.add(mp)

        await db.flush()

        # ─── Carbon Price History ────────────────────────────────────
        base_price = 72.50
        for i in range(30):
            change = rng.uniform(-3, 3)
            price = round(base_price + change, 2)
            db.add(CarbonPriceHistory(
                price_eur=price, previous_close_eur=base_price,
                change_24h=round(change, 2), change_pct_24h=round(change / base_price * 100, 2),
                day_high_eur=round(price + rng.uniform(0, 2), 2),
                day_low_eur=round(price - rng.uniform(0, 2), 2),
                market="EU ETS", source="seed_data",
                recorded_at=datetime.now(timezone.utc) - timedelta(days=30 - i),
            ))
            base_price = price

        # ─── Corporate Emissions ─────────────────────────────────────
        for year in [2022, 2023, 2024]:
            db.add(CorporateEmission(organization_id=org.id, scope="scope_1", amount_tco2e=rng.uniform(5000, 15000), year=year, category="Combustão", verified=year < 2024))
            db.add(CorporateEmission(organization_id=org.id, scope="scope_2", amount_tco2e=rng.uniform(3000, 8000), year=year, category="Eletricidade", verified=year < 2024))
            db.add(CorporateEmission(organization_id=org.id, scope="scope_3", amount_tco2e=rng.uniform(20000, 50000), year=year, category="Cadeia de Valor", verified=year < 2024))

        # Carbon balances
        for period in ["2022", "2023", "2024"]:
            emissions = rng.uniform(30000, 70000)
            offsets = rng.uniform(10000, 40000)
            db.add(CarbonBalance(organization_id=org.id, period=period, total_emissions=round(emissions, 2), total_offsets=round(offsets, 2), net_balance=round(emissions - offsets, 2)))

        await db.commit()
        print(f"✅ Seed v3: {len(projects)} projetos, {len(jurisdictions)} jurisdições, {len(entities)} entidades, {len(workspaces)} workspaces criados.")
