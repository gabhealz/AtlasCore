"""Seed (idempotente) da carteira real de clientes da Healz no Atlas-Core.

Fonte: planilha de contratos (Banco Inter). Preenche o BI com os clientes
reais para já podermos acompanhar tempo de casa / LTV.

Campos por linha (separados por '|'):
    nome | plano | status | inicio(dd/mm/aaaa) | fim(dd/mm/aaaa) | mensalidade | documento | email | telefone

Upsert por `document` (CPF/CNPJ); se não houver, casa por `name`. Rodar com:
    python seed_clients.py
"""
import asyncio
import logging
from datetime import date

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# nome | plano | status | inicio | fim | mensalidade | documento | email | telefone
RAW_CLIENTS = """
VITOR LUIS TIMOSSI BUSNARDO|AQF|Ativo|29/05/2026|29/05/2027|2000|390.804.928-84|v_itorltb@hotmail.com|(19) 3241-0154
NATALIA SILVEIRA DE PAIVA|AQF + Secretariado|Ativo|29/04/2026|29/04/2027|2500|101.329.796-24|natalia.paiva@yahoo.com.br|(21) 98027-1790
ARTUR DE CASTRO KOPPER SOCIEDADE INDIVIDUAL DE ADVOCACIA|Pareto|Ativo|30/08/2023|29/08/2026|900|49.828.860/0001-07|adv.kopper@gmail.com|(48) 9162-7525
CAROLINE FERREIRA PEREIRA|AQF + Secretariado|Ativo|29/04/2026|29/04/2027|2800|057.351.419-45|croline1979@hotmail.com|(11) 98565-4641
IGOR PRADO GENEROSO|AQF + Secretariado|Ativo|20/05/2026|20/05/2027|2800|096.589.086-40|igorpg@hotmail.com|(11) 3237-4891
ANA CAROLINA PESSOA CANTARELLI|AQF + Secretariado|Ativo|07/05/2026|07/05/2027|2850|011.264.574-77|carolinapessoacantarelli@hotmail.com|(81) 99132-2765
ANDRE LUIZ TORRES OLIVEIRA|AQF + Secretariado|Ativo|15/05/2026|15/05/2027|3100|839.572.002-53|andre.torres.oliveira@hotmail.com|(11) 98291-8788
RODRIGO FREDDI|AQF|Ativo|15/04/2026|15/04/2027|2200|311.459.088-88|rofreddi@yahoo.com.br|(11) 99605-8163
FERNANDO RODRIGUES GERVASIO|Mentoria|Ativo|27/03/2026|28/03/2027|20000|081.130.206-75|fernandogervasio@gmail.com|(34) 99880-2798
POWERUP CLINICA|AQF|Ativo|26/03/2026|26/03/2027|2000|59.911.320/0001-46|powerupclinica@gmail.com|(11) 6611-8414
GABRIEL MACHADO DE OLIVEIRA|AQF|Ativo|17/03/2026|17/03/2027|2100|418.702.658-40|deoliveira.gabriel@hotmail.com|(11) 96030-9024
MARGARETH CHIHARU IWATA DA FONSECA|Carol|Ativo|02/02/2026|02/02/2027|397|297.919.118-35|mchiaharu@terra.com.br|(21) 99675-3544
MICHELLE CAILLEAUX CEZAR FERREIRA|AQF + Secretariado|Ativo|12/02/2026|11/02/2027|3000|069.485.747-50|micailleaux@gmail.com|(21) 99971-9751
UROCENTER|AQF|Ativo|06/02/2026|05/02/2027|3500|40.829.736/0001-91|urocenterpf@gmail.com|(54) 9918-2221
JULIA ROSSI BAZZANELLA|AQF + Secretariado|Ativo|28/11/2025|30/11/2026|2350|124.774.747-66|jrbazzanella@gmail.com|(21) 99777-5077
RONALDO GRANGEIRO DE SALES|AQF|Ativo|01/11/2025|01/11/2026|2100|263.466.948-80|ronaldo.sales@totalfono.com|(11) 99117-6592
MILTON ALEXANDRE FERREIRA ARANHA|Secretariado|Ativo|13/10/2025|12/10/2026|900|322.738.538-40|milton_aranha@yahoo.com.br|(34) 98834-4512
MARIANGELI HORWACZ|Pareto|Ativo|28/08/2025|28/08/2026|1804|023.949.857-71|mariangelihorwacz@hotmail.com|(22) 98144-0554
ALVES & PEREIRA SERVICOS MEDICOS LTDA|AQF|Ativo|25/09/2025|25/09/2026|2500|40.516.461/0001-36|caio.pereira@fm.usp.br|(11) 2538-3681
EJJEMED|Pareto + Secretariado|Ativo|18/07/2025|18/07/2026|1900|33.507.551/0001-03|pedro.ejje@gmail.com|(21) 2742-1610
MIGUEL HORWACZ|Pareto|Ativo|23/04/2025|23/04/2027|1900|160.261.737-65|miguelhorwacz@hotmail.com|
EDGARD COSTA SCOPACASA|AQF|Ativo|28/05/2024|28/05/2027|4000|141.220.857-21|edgardcscopacasa@gmail.com|(24) 99925-3880
SKINDOO|Pareto|Ativo|25/03/2024|25/03/2027|1199.69|47.541.772/0001-02|memaiasantos@gmail.com|(41) 9888-0068
BETHLEM PNEUMOLOGIA|Pareto|Ativo|07/12/2023|06/12/2026|1100|51.850.045/0001-96|meucnpj@contabilizei.com.br|(41) 9788-0145
CONEPEN - CONHECER E PENSAR LTDA|Personalizado|Ativo|29/08/2023|28/08/2026|7800|50.047.946/0001-81|clovissanchez10@gmail.com|(11) 9159-8891
HELENA BANDEIRA DE MELO PAIVA UCHOA|Carol|Suspenso|18/09/2025|30/09/2026|397|006.609.986-29|hbmpaiva@yahoo.com.br|(21) 99335-7632
VACINAR - CLINICA DE VACINAS|Carol|Suspenso|19/09/2025|19/09/2026|397|09.093.633/0001-66|contato@clinicavacinar.com.br|(64) 3611-1010
ISABEL TOSTES E CLARA ORLANDI|Pareto|Suspenso|07/07/2025|07/07/2026|2200|50.872.369/0001-62|isabelstostes@gmail.com|(21) 9301-9070
FERNANDA MARTIN CASTRO|Carol|Suspenso|16/09/2025|16/09/2026|397|126.644.768-74|drafernandamartinc.skincare@gmail.com|(11) 96189-6205
BEATRIZ OLIVEIRA DO VALE|Carol|Suspenso|13/10/2025|13/10/2026|541|228.507.348-88|beaovale@gmail.com|(19) 99862-9651
RENATO DA SILVA FARIA|Pareto|Suspenso|15/09/2025|15/09/2026|3000|585.842.931-91|renatofaria.med@gmail.com|(62) 99976-8291
FABRICIO NAGATANI PASSOS|Personalizado|Suspenso|26/01/2026|28/02/2026|1600|096.378.394-70|fabricionagatani@ig.com.br|(11) 98316-4570
MARIO HORWACZ|Pareto|Suspenso|09/10/2025|08/10/2026|1478|014.715.777-32|mhorwacz@gmail.com|(22) 99728-6531
CLINICA MITHIE|Carol|Suspenso|01/10/2025|01/10/2026|397|63.132.978/0001-27|dramithielhen@gmail.com|(51) 9977-6099
FABIO AUGUSTO DE CARVALHO|Carol|Suspenso|27/01/2026|26/01/2027|1647|876.422.559-34|drfac@hotmail.com|(41) 99995-0685
FERNANDO BARATELLA DE ASSIS|Carol|Suspenso|18/11/2025|18/11/2026|247|352.379.058-11|drfbaratellaassis@gmail.com|(11) 99994-0351
ELISA BARBUGIANI BORGES|Carol|Suspenso|24/11/2025|24/11/2026|247|719.928.041-68|elisabarbugiani@yahoo.com|(34) 99209-1111
PEROLA NEGRA PET SHOP E VETERINARIA LTDA|Personalizado|Suspenso|11/08/2022|01/08/2026|3000|24.769.079/0001-88|perolanegrapetshop@hotmail.com|(48) 3030-0200
FISIOTERAPIA ESPORTE E MOVIMENTO|Carol|Suspenso|24/11/2025|24/11/2026|247|50.431.549/0001-09|fisioterapeutakelly@hotmail.com|(11) 8928-1957
PAULA DE SOUZA ZANON ALVES|Carol|Suspenso|24/11/2025|24/11/2026|247|099.102.427-37|cadurazr@gmail.com|(27) 99905-1442
MIRELLA TAINA KUSDRA DOS SANTOS|Carol|Suspenso|01/02/2026|01/02/2027|450|431.035.628-10|mirella.kusdra@hotmail.com|(11) 95756-5100
""".strip()


def parse_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    day, month, year = value.split("/")
    return date(int(year), int(month), int(day))


def parse_fee(value: str) -> float:
    value = value.strip().replace(" ", "")
    # formato BR: "1.199,69" -> 1199.69 ; "2.000,00" -> 2000.00 ; "397" -> 397
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def build_records() -> list[dict]:
    records = []
    for line in RAW_CLIENTS.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        name, plan, status, start, end, fee, document, email, phone = (
            parts + [""] * (9 - len(parts))
        )
        records.append(
            {
                "name": name.strip(),
                "plan_name": plan.strip() or None,
                "is_active": status.strip().lower().startswith("ativo"),
                "contract_start_date": parse_date(start),
                "contract_end_date": parse_date(end),
                "monthly_fee": parse_fee(fee),
                "document": document.strip() or None,
                "email": (email.strip() or None),
                "phone": (phone.strip() or None),
                "active_platforms": "meta,google",
            }
        )
    return records


async def seed_clients() -> None:
    records = build_records()
    created = 0
    updated = 0
    async with AsyncSessionLocal() as db:
        for rec in records:
            existing = None
            if rec["document"]:
                existing = (
                    await db.execute(
                        select(Client).where(Client.document == rec["document"])
                    )
                ).scalar_one_or_none()
            if existing is None:
                existing = (
                    await db.execute(
                        select(Client).where(Client.name == rec["name"])
                    )
                ).scalar_one_or_none()

            if existing is None:
                db.add(Client(**rec))
                created += 1
            else:
                for key, value in rec.items():
                    setattr(existing, key, value)
                updated += 1
        await db.commit()
    logger.info(
        "Seed de clientes concluído: %s criados, %s atualizados (total %s).",
        created,
        updated,
        len(records),
    )


if __name__ == "__main__":
    asyncio.run(seed_clients())
