import asyncio
import logging
from datetime import date, timedelta
import random

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.client import Client
from app.models.metric_snapshot import MetricSnapshot
from app.models.campaign_snapshot import CampaignSnapshot
from app.models.integration_setting import IntegrationSetting
from app.models.sync_log import SyncLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT_DATA = [
    {
        "name": "Dr. Marcos Oliveira",
        "monthly_fee": 1500.00,
        "meta_account_id": "act_123456",
        "google_account_id": "123-456-7890",
        "tintim_id": "tintim_123",
        "active_platforms": "meta,google",
        "is_active": True,
    },
    {
        "name": "Dra. Ana Ferreira",
        "monthly_fee": 2000.00,
        "meta_account_id": "act_654321",
        "google_account_id": "098-765-4321",
        "tintim_id": "tintim_456",
        "active_platforms": "meta",
        "is_active": True,
    },
    {
        "name": "Dr. Rafael Costa",
        "monthly_fee": 1200.00,
        "meta_account_id": "act_789012",
        "google_account_id": "111-222-3333",
        "tintim_id": "tintim_789",
        "active_platforms": "google",
        "is_active": True,
    },
    {
        "name": "Dra. Juliana Santos",
        "monthly_fee": 2500.00,
        "meta_account_id": "act_345678",
        "google_account_id": "444-555-6666",
        "tintim_id": "tintim_012",
        "active_platforms": "meta,google",
        "is_active": True,
    },
]


async def seed_ops_dashboard():
    async with AsyncSessionLocal() as db:
        logger.info("Iniciando seed do Ops Dashboard...")

        # Create clients
        clients = []
        for client_data in CLIENT_DATA:
            client = Client(**client_data)
            db.add(client)
            clients.append(client)
        
        await db.commit()
        for client in clients:
            await db.refresh(client)
        
        logger.info(f"Criados {len(clients)} clientes.")

        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())

        # Create MetricSnapshots (last 8 weeks)
        for client in clients:
            platforms = client.active_platforms.split(",")
            
            for i in range(8):
                ws = current_week_start - timedelta(days=7 * i)
                
                for platform in platforms:
                    impressions = random.randint(5000, 50000)
                    clicks = int(impressions * random.uniform(0.01, 0.05))
                    ctr = (clicks / impressions) * 100 if impressions > 0 else 0
                    ad_spend = random.uniform(800, 4000)
                    cpc = ad_spend / clicks if clicks > 0 else 0
                    conversions = random.randint(10, 80)
                    cost_per_conversion = ad_spend / conversions if conversions > 0 else 0
                    
                    lp_rate = random.uniform(5.0, 20.0)
                    wpp_rate = random.uniform(10.0, 40.0)
                    
                    revenue = random.uniform(2000, 20000)
                    bookings = random.randint(5, 40)
                    
                    snapshot = MetricSnapshot(
                        client_id=client.id,
                        week_start=ws,
                        date=ws,
                        source=platform,
                        impressions=impressions,
                        clicks=clicks,
                        ctr=ctr,
                        cpc=cpc,
                        ad_spend=ad_spend,
                        conversions=conversions,
                        cost_per_conversion=cost_per_conversion,
                        lp_to_whatsapp_rate=lp_rate,
                        whatsapp_to_booking_rate=wpp_rate,
                        revenue=revenue,
                        bookings=bookings,
                    )
                    db.add(snapshot)
            
            # Create CampaignSnapshots (current week only)
            for platform in platforms:
                num_campaigns = random.randint(2, 4)
                for c_idx in range(num_campaigns):
                    camp_impressions = random.randint(1000, 15000)
                    camp_clicks = int(camp_impressions * random.uniform(0.01, 0.05))
                    camp_ctr = (camp_clicks / camp_impressions) * 100 if camp_impressions > 0 else 0
                    camp_spend = random.uniform(200, 1500)
                    camp_cpc = camp_spend / camp_clicks if camp_clicks > 0 else 0
                    camp_conversions = random.randint(2, 20)
                    
                    campaign = CampaignSnapshot(
                        client_id=client.id,
                        week_start=current_week_start,
                        platform=platform,
                        campaign_id=f"camp_{platform}_{client.id}_{c_idx}",
                        campaign_name=f"Campanha {platform.capitalize()} {c_idx + 1}",
                        impressions=camp_impressions,
                        clicks=camp_clicks,
                        ctr=camp_ctr,
                        cpc=camp_cpc,
                        spend=camp_spend,
                        conversions=camp_conversions,
                    )
                    db.add(campaign)

        await db.commit()
        logger.info("Seed concluído com sucesso!")


if __name__ == "__main__":
    asyncio.run(seed_ops_dashboard())
