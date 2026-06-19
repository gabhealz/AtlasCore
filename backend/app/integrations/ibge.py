"""Cliente da API pública do IBGE (servicodados.ibge.gov.br). Sem credencial.

- Lista de municípios por UF (localidades v1).
- População estimada (agregado 6579, variável 9324) por município ou UF.
- Pirâmide etária (Censo 2022, agregado 9514, variável 93, sexo + faixas de 5 anos).
- Renda domiciliar per capita (Censo 2022, agregado 9534, variável 9529).
"""

import logging

import httpx

logger = logging.getLogger(__name__)

BASE = "https://servicodados.ibge.gov.br"
TIMEOUT = httpx.Timeout(20.0)

# Faixas etárias de 5 anos da classificação 287 (Censo 2022) -> rótulo.
AGE_GROUPS: list[tuple[str, str]] = [
    ("93070", "0 a 4"), ("93084", "5 a 9"), ("93085", "10 a 14"),
    ("93086", "15 a 19"), ("93087", "20 a 24"), ("93088", "25 a 29"),
    ("93089", "30 a 34"), ("93090", "35 a 39"), ("93091", "40 a 44"),
    ("93092", "45 a 49"), ("93093", "50 a 54"), ("93094", "55 a 59"),
    ("93095", "60 a 64"), ("93096", "65 a 69"), ("93097", "70 a 74"),
    ("93098", "75 a 79"), ("49108", "80 a 84"), ("49109", "85 a 89"),
    ("60040", "90 a 94"), ("60041", "95 a 99"), ("6653", "100+"),
]
_AGE_LABEL = {gid: label for gid, label in AGE_GROUPS}


async def fetch_municipios_uf(uf: str) -> list[dict]:
    """Lista municípios de uma UF: [{id, nome, uf_id, uf_sigla, uf_nome}]."""
    url = f"{BASE}/api/v1/localidades/estados/{uf}/municipios"
    out: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        for m in data:
            ufd = (
                m.get("microrregiao", {}).get("mesorregiao", {}).get("UF", {})
                or m.get("regiao-imediata", {}).get("regiao-intermediaria", {}).get("UF", {})
                or {}
            )
            out.append({
                "id": m.get("id"),
                "nome": m.get("nome"),
                "uf_id": ufd.get("id"),
                "uf_sigla": ufd.get("sigla", uf.upper()),
                "uf_nome": ufd.get("nome"),
            })
    except Exception as exc:
        logger.warning("IBGE: falha ao listar municípios de %s: %s", uf, exc)
    return [m for m in out if m["id"] and m["nome"]]


def _latest_serie_value(payload: list) -> tuple[int | None, int | None]:
    try:
        serie = payload[0]["resultados"][0]["series"][0]["serie"]
        if not serie:
            return None, None
        year = max(serie.keys())
        raw = serie[year]
        if raw in (None, "", "-", "...", "..", "X"):
            return None, int(year)
        return int(float(raw)), int(year)
    except (KeyError, IndexError, ValueError, TypeError):
        return None, None


async def fetch_populacao(localidade: str) -> tuple[int | None, int | None]:
    """População estimada. `localidade` = 'N6[<mun_id>]' ou 'N3[<uf_id>]'."""
    url = f"{BASE}/api/v3/agregados/6579/periodos/-1/variaveis/9324?localidades={localidade}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return _latest_serie_value(resp.json())
    except Exception as exc:
        logger.warning("IBGE: falha ao buscar população %s: %s", localidade, exc)
        return None, None


async def fetch_piramide(municipio_id: int) -> tuple[list[dict] | None, int | None]:
    """Pirâmide etária (Censo 2022) do município: [{faixa, homens, mulheres}]."""
    ids = ",".join(gid for gid, _ in AGE_GROUPS)
    url = (
        f"{BASE}/api/v3/agregados/9514/periodos/2022/variaveis/93"
        f"?localidades=N6[{municipio_id}]&classificacao=2[4,5]|287[{ids}]"
    )
    buckets: dict[str, dict] = {label: {"faixa": label, "homens": 0, "mulheres": 0} for _, label in AGE_GROUPS}
    ano = 2022
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        resultados = data[0]["resultados"]
        for res in resultados:
            cats: dict[str, str] = {}
            for c in res.get("classificacoes", []):
                cats.update(c.get("categoria", {}))
            sexo_id = "4" if "4" in cats else ("5" if "5" in cats else None)
            age_id = next((k for k in cats if k in _AGE_LABEL), None)
            if not sexo_id or not age_id:
                continue
            label = _AGE_LABEL[age_id]
            serie = res["series"][0]["serie"]
            year = max(serie.keys()) if serie else "2022"
            ano = int(year)
            raw = serie.get(year)
            val = int(float(raw)) if raw not in (None, "", "-", "...", "..", "X") else 0
            buckets[label]["homens" if sexo_id == "4" else "mulheres"] += val
        result = list(buckets.values())
        if not any(b["homens"] or b["mulheres"] for b in result):
            return None, ano
        return result, ano
    except Exception as exc:
        logger.warning("IBGE: falha ao buscar pirâmide do município %s: %s", municipio_id, exc)
        return None, ano


async def fetch_renda_per_capita(municipio_id: int) -> dict | None:
    """Rendimento nominal médio mensal per capita (Censo 2022).

    Returns: {"media": float, "ano": int} or None if unavailable.
    """
    url = (
        f"{BASE}/api/v3/agregados/9534/periodos/2022/variaveis/9529"
        f"?localidades=N6[{municipio_id}]"
    )
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        value, year = _latest_serie_value(data)
        if value is None:
            return None
        return {"media": float(value), "ano": year or 2022}
    except Exception as exc:
        logger.warning("IBGE: falha ao buscar renda per capita do município %s: %s", municipio_id, exc)
        return None
