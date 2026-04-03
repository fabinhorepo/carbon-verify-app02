"""Seed de dados para Carbon Verify - Produção."""
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.database import async_session
from app.core.auth import get_password_hash
from app.models.models import (
    Organization, User, UserRole, CarbonProject, CarbonCredit,
    Portfolio, PortfolioPosition, ProjectType
)
from app.services.rating_engine import calculate_rating
from app.services.fraud_detection import run_fraud_detection

PROJECTS_DATA = [
    {"name": "Amazonia REDD+ Conservation", "type": ProjectType.REDD, "country": "Brazil", "lat": -3.4653, "lng": -62.2159, "area": 85000, "credits": 450000, "retired": 180000, "vintage": 2020, "registry": "Verra", "meth": "VM0015", "prop": "Conservation International", "buffer": 18, "mon": "Semestral", "ext": "VCS-1234"},
    {"name": "Borneo Forest Protection", "type": ProjectType.REDD, "country": "Indonesia", "lat": 1.5, "lng": 110.0, "area": 120000, "credits": 680000, "retired": 250000, "vintage": 2019, "registry": "Verra", "meth": "VM0009", "prop": "WWF Indonesia", "buffer": 15, "mon": "Annual", "ext": "VCS-2345"},
    {"name": "Kenya Cookstoves Program", "type": ProjectType.COOKSTOVE, "country": "Kenya", "lat": -1.2921, "lng": 36.8219, "area": None, "credits": 95000, "retired": 42000, "vintage": 2021, "registry": "Gold Standard", "meth": "GS Cookstove", "prop": "Burn Manufacturing", "buffer": None, "mon": "Annual", "ext": "GS-3456"},
    {"name": "Indian Solar Energy Grid", "type": ProjectType.RENEWABLE_ENERGY, "country": "India", "lat": 28.6139, "lng": 77.2090, "area": 500, "credits": 320000, "retired": 280000, "vintage": 2018, "registry": "Gold Standard", "meth": "AMS-I.D", "prop": "ReNew Power", "buffer": None, "mon": "Annual", "ext": "GS-4567"},
    {"name": "Colombian Blue Carbon Mangroves", "type": ProjectType.BLUE_CARBON, "country": "Colombia", "lat": 10.3910, "lng": -75.5144, "area": 12000, "credits": 65000, "retired": 15000, "vintage": 2022, "registry": "Verra", "meth": "VM0033", "prop": "Invemar", "buffer": 20, "mon": "Quarterly", "ext": "VCS-5678"},
    {"name": "Peru Afforestation Project", "type": ProjectType.ARR, "country": "Peru", "lat": -13.5226, "lng": -71.9673, "area": 25000, "credits": 180000, "retired": 45000, "vintage": 2021, "registry": "Verra", "meth": "AR-ACM0003", "prop": "Reforestação Andina", "buffer": 22, "mon": "Semestral", "ext": "VCS-6789"},
    {"name": "Vietnam Methane Capture", "type": ProjectType.METHANE, "country": "Vietnam", "lat": 10.8231, "lng": 106.6297, "area": 200, "credits": 120000, "retired": 95000, "vintage": 2020, "registry": "Gold Standard", "meth": "AMS-III.H", "prop": "Vietnam Energy JSC", "buffer": None, "mon": "Quarterly", "ext": "GS-7890"},
    {"name": "Ethiopia Community Forestry", "type": ProjectType.ARR, "country": "Ethiopia", "lat": 9.0192, "lng": 38.7525, "area": 18000, "credits": 92000, "retired": 28000, "vintage": 2022, "registry": "Plan Vivo", "meth": "PV Standard", "prop": "Farm Africa", "buffer": 12, "mon": "Annual", "ext": "PV-8901"},
    {"name": "Congo Basin REDD+", "type": ProjectType.REDD, "country": "Congo", "lat": -4.3175, "lng": 15.3137, "area": 350000, "credits": 1200000, "retired": 180000, "vintage": 2019, "registry": "Verra", "meth": "VM0006", "prop": "Wildlife Works", "buffer": 25, "mon": "Annual", "ext": "VCS-9012"},
    {"name": "Honduras Improved Cookstoves", "type": ProjectType.COOKSTOVE, "country": "Honduras", "lat": 14.0723, "lng": -87.1921, "area": None, "credits": 35000, "retired": 12000, "vintage": 2023, "registry": "Gold Standard", "meth": "GS TPDDTEC", "prop": "Proyecto Mirador", "buffer": None, "mon": "Semestral", "ext": "GS-0123"},
    {"name": "Madagascar Reforestation", "type": ProjectType.ARR, "country": "Madagascar", "lat": -18.8792, "lng": 47.5079, "area": 8000, "credits": 42000, "retired": 5000, "vintage": 2023, "registry": "Verra", "meth": "AR-ACM0003", "prop": "Eden Reforestation", "buffer": 18, "mon": "Semestral", "ext": "VCS-1011"},
    {"name": "Cambodia Solar Farm", "type": ProjectType.RENEWABLE_ENERGY, "country": "Cambodia", "lat": 11.5564, "lng": 104.9282, "area": 250, "credits": 85000, "retired": 70000, "vintage": 2020, "registry": "Gold Standard", "meth": "AMS-I.D", "prop": "Cleanergy Asia", "buffer": None, "mon": "Annual", "ext": "GS-1112"},
    {"name": "Ghana Biochar Initiative", "type": ProjectType.BIOCHAR, "country": "Ghana", "lat": 5.6037, "lng": -0.1870, "area": 3000, "credits": 28000, "retired": 8000, "vintage": 2023, "registry": "Verra", "meth": "VM0044", "prop": "Biochar Ghana Ltd", "buffer": 10, "mon": "Quarterly", "ext": "VCS-1213"},
    {"name": "Philippines Wind Power", "type": ProjectType.RENEWABLE_ENERGY, "country": "Philippines", "lat": 14.5995, "lng": 120.9842, "area": 150, "credits": 200000, "retired": 185000, "vintage": 2017, "registry": "ACR", "meth": "ACR Wind", "prop": "AboitizPower", "buffer": None, "mon": "Annual", "ext": "ACR-1314"},
    {"name": "Tanzania Community Forest", "type": ProjectType.REDD, "country": "Tanzania", "lat": -6.3690, "lng": 34.8888, "area": 45000, "credits": 250000, "retired": 80000, "vintage": 2021, "registry": "Verra", "meth": "VM0015", "prop": "TFCG", "buffer": 16, "mon": "Annual", "ext": "VCS-1415"},
    {"name": "Bangladesh Mangrove Restoration", "type": ProjectType.BLUE_CARBON, "country": "Bangladesh", "lat": 21.4272, "lng": 92.0058, "area": 5000, "credits": 22000, "retired": 3000, "vintage": 2024, "registry": "Verra", "meth": "VM0033", "prop": "Sundarbans Foundation", "buffer": 20, "mon": "Quarterly", "ext": "VCS-1516"},
    {"name": "Guatemala Forestry Initiative", "type": ProjectType.ARR, "country": "Guatemala", "lat": 14.6349, "lng": -90.5069, "area": 12000, "credits": 55000, "retired": 20000, "vintage": 2022, "registry": "Plan Vivo", "meth": "PV Standard", "prop": "Fundación Defensores", "buffer": 14, "mon": "Semestral", "ext": "PV-1617"},
    {"name": "Mozambique Wind Energy", "type": ProjectType.RENEWABLE_ENERGY, "country": "Mozambique", "lat": -25.9692, "lng": 32.5732, "area": 300, "credits": 110000, "retired": 60000, "vintage": 2021, "registry": "Gold Standard", "meth": "AMS-I.D", "prop": "Globeleq", "buffer": None, "mon": "Annual", "ext": "GS-1718"},
    {"name": "Nepal Biogas Program", "type": ProjectType.METHANE, "country": "Nepal", "lat": 27.7172, "lng": 85.3240, "area": None, "credits": 45000, "retired": 38000, "vintage": 2019, "registry": "Gold Standard", "meth": "AMS-I.I", "prop": "Nepal Biogas Support Program", "buffer": None, "mon": "Annual", "ext": "GS-1819"},
    {"name": "Zambia Community REDD+", "type": ProjectType.REDD, "country": "Zambia", "lat": -15.3875, "lng": 28.3228, "area": 60000, "credits": 310000, "retired": 95000, "vintage": 2020, "registry": "Verra", "meth": "VM0009", "prop": "Biocarbon Partners", "buffer": 17, "mon": "Annual", "ext": "VCS-1920"},
    # Projetos sem dados completos (para testar fraude)
    {"name": "Unlicensed Forest Project X", "type": ProjectType.REDD, "country": "Brazil", "lat": -5.0, "lng": -55.0, "area": 500, "credits": 500000, "retired": 480000, "vintage": 2010, "registry": None, "meth": None, "prop": None, "buffer": None, "mon": None, "ext": None},
    {"name": "Suspicious Energy Credits", "type": ProjectType.RENEWABLE_ENERGY, "country": "India", "lat": 19.0, "lng": 73.0, "area": 50, "credits": 200000, "retired": 190000, "vintage": 2012, "registry": None, "meth": None, "prop": None, "buffer": None, "mon": None, "ext": None},
    {"name": "Overestimated Carbon Sink", "type": ProjectType.ARR, "country": "Mexico", "lat": 19.4326, "lng": -99.1332, "area": 100, "credits": 150000, "retired": 20000, "vintage": 2023, "registry": "Verra", "meth": "AR-ACM0003", "prop": "Project Dev MX", "buffer": 2, "mon": None, "ext": "VCS-BAD1"},
    {"name": "Minimal Documentation Project", "type": ProjectType.OTHER, "country": "Uganda", "lat": 0.3476, "lng": 32.5825, "area": 15_000_000, "credits": 80000, "retired": 10000, "vintage": 2022, "registry": None, "meth": None, "prop": None, "buffer": None, "mon": None, "ext": None},
    {"name": "Rwanda Agroforestry Carbon", "type": ProjectType.ARR, "country": "Rwanda", "lat": -1.9403, "lng": 29.8739, "area": 6000, "credits": 35000, "retired": 12000, "vintage": 2023, "registry": "Gold Standard", "meth": "AR-AMS0007", "prop": "One Tree Planted", "buffer": 15, "mon": "Semestral", "ext": "GS-2021"},
]


async def run_seed():
    """Popula o banco com dados iniciais se estiver vazio."""
    async with async_session() as db:
        existing = await db.execute(select(CarbonProject).limit(1))
        if existing.scalar_one_or_none():
            return  # Já tem dados

        # Org + User
        org = Organization(name="Carbon Verify Demo", slug="carbon-verify-demo")
        db.add(org)
        await db.flush()

        user = User(
            email="admin@carbonverify.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin Carbon Verify",
            role=UserRole.ADMIN,
            organization_id=org.id,
        )
        db.add(user)
        await db.flush()

        # Portfolio
        portfolio = Portfolio(name="Portfólio Principal", organization_id=org.id, description="Portfólio de demonstração")
        db.add(portfolio)
        await db.flush()

        rng = random.Random(42)

        for pd in PROJECTS_DATA:
            avail = pd["credits"] - pd["retired"]
            start_d = datetime(pd["vintage"] - 2, 1, 1)
            end_d = datetime(pd["vintage"] + rng.randint(10, 25), 12, 31)

            project = CarbonProject(
                name=pd["name"], project_type=pd["type"], country=pd["country"],
                latitude=pd["lat"], longitude=pd["lng"], area_hectares=pd["area"],
                total_credits_issued=pd["credits"], total_credits_retired=pd["retired"],
                total_credits_available=max(0, avail), vintage_year=pd["vintage"],
                registry=pd["registry"], methodology=pd["meth"], proponent=pd["prop"],
                buffer_pool_percentage=pd["buffer"], monitoring_frequency=pd["mon"],
                external_id=pd["ext"], start_date=start_d, end_date=end_d,
                region=pd["country"],
                description=f"Projeto {pd['name']} localizado em {pd['country']}. Tipo: {pd['type'].value}. Metodologia: {pd['meth'] or 'N/A'}.",
                baseline_scenario=f"Baseline conservador para projeto {pd['type'].value} em {pd['country']}. Cenário de referência sem intervenção do projeto." if pd["meth"] else None,
                additionality_justification=f"Análise de barreiras demonstra que o projeto não seria viável sem receita de créditos de carbono. Barreiras: financeira, tecnológica, institucional." if pd["registry"] else None,
            )
            db.add(project)
            await db.flush()

            # Rating
            rating = calculate_rating(project)
            db.add(rating)

            # Fraud alerts
            alerts = run_fraud_detection(project)
            for a in alerts:
                db.add(a)

            # Credits
            num_credits = rng.randint(3, 8)
            for ci in range(num_credits):
                qty = pd["credits"] // num_credits + rng.randint(-1000, 1000)
                price = rng.uniform(5, 35)
                credit = CarbonCredit(
                    serial_number=f"CV-{project.id}-{ci+1:04d}",
                    project_id=project.id, vintage_year=pd["vintage"],
                    quantity=max(100, qty), price_eur=round(price, 2),
                    issuance_date=datetime(pd["vintage"], rng.randint(1, 12), rng.randint(1, 28)),
                )
                db.add(credit)
                await db.flush()

                # Posição no portfólio (70% dos créditos)
                if rng.random() < 0.7:
                    pos = PortfolioPosition(
                        portfolio_id=portfolio.id, credit_id=credit.id,
                        quantity=max(50, qty // 2),
                        acquisition_price_eur=round(price * rng.uniform(0.9, 1.1), 2),
                        acquisition_date=datetime(pd["vintage"], rng.randint(1, 12), rng.randint(1, 28)),
                    )
                    db.add(pos)

        await db.commit()
        print(f"✅ Seed completo: {len(PROJECTS_DATA)} projetos inseridos")
