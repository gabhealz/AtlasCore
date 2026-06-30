"""Mini-banco de benchmarks de mídia por especialidade (Google e Meta).

Serve de FALLBACK de CPC/CTR/CPL quando o DataForSEO (e o Apify) nao retornam
volume/CPC para as palavras-chave da especialidade — o que e comum em saude no
Brasil. Em vez de uma faixa generica sem credibilidade, aqui o numero tem base:

- O BASELINE e o numero REAL da operacao Healz (blended, toda a carteira):
  agregado de 84 semanas-cliente no Google e 44 no Meta (abr-jun/2026,
  metric_snapshots). Google: CPC ~R$3,1-5,5 (mediana 4,1), CTR ~4,5-7% (5,8).
  Meta: CPC ~R$0,3-1,2 (mediana 0,33; ponderado por gasto ~1,0), CTR ~2-3,5% (2,9).
- O valor POR ESPECIALIDADE e o baseline real ajustado por um fator de
  COMPETITIVIDADE por tier (estetica/plastica disputam mais o clique -> CPC
  maior; pediatria/clinico -> menor). E uma estimativa ANCORADA no dado real,
  nao um chute generico. Conforme a Healz preencher `clients.specialty` e
  acumular historico, estes tiers podem ser substituidos por dado real por nicho.

Como atualizar: edite BASELINE_* (quando rodar nova varredura do real) e os
mapeamentos de tier. Tudo versionado.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Baseline REAL Healz (blended) — (low, mid, high)
BASELINE_GOOGLE_CPC = (3.10, 4.10, 5.50)
BASELINE_GOOGLE_CTR = (4.5, 5.8, 7.0)  # %
BASELINE_META_CPC = (0.30, 0.60, 1.20)
BASELINE_META_CTR = (2.0, 2.9, 3.5)  # %

# Fator de competitividade do CPC por tier (multiplicador sobre o baseline real).
TIER_CPC_FACTOR = {
    "alto": 1.5,        # estetica, plastica, HOF, implante, bariatrica, refrativa
    "medio_alto": 1.15,  # ortopedia, gineco, urologia, oftalmo, endocrino, dermato, cardio
    "medio": 1.0,       # otorrino, gastro, pneumo, neuro, reumato, psiquiatria, vascular
    "medio_baixo": 0.8,  # pediatria, clinico geral, geriatria, nutricao, psicologia
}

# Especialidade (normalizada, sem acento, minuscula) -> tier. Chaves sao
# fragmentos; o lookup casa por "contem". Ordem nao importa.
SPECIALTY_TIER = {
    # ALTO (estetica / alto ticket eletivo, muita disputa de clique)
    "estetica": "alto",
    "harmonizacao": "alto",
    "dermatologia estetica": "alto",
    "cirurgia plastica": "alto",
    "plastica": "alto",
    "bariatrica": "alto",
    "implante": "alto",
    "odontologia": "alto",
    "ortodontia": "alto",
    "refrativa": "alto",
    "transplante capilar": "alto",
    "medicina estetica": "alto",
    # MEDIO-ALTO
    "ortopedia": "medio_alto",
    "ortopedista": "medio_alto",
    "joelho": "medio_alto",
    "coluna": "medio_alto",
    "ginecologia": "medio_alto",
    "obstetricia": "medio_alto",
    "urologia": "medio_alto",
    "oftalmologia": "medio_alto",
    "endocrinologia": "medio_alto",
    "dermatologia": "medio_alto",
    "cardiologia": "medio_alto",
    "mastologia": "medio_alto",
    "vascular": "medio_alto",
    "medicina esportiva": "medio_alto",
    # MEDIO
    "otorrinolaringologia": "medio",
    "otorrino": "medio",
    "gastroenterologia": "medio",
    "pneumologia": "medio",
    "neurologia": "medio",
    "neurocirurgia": "medio",
    "reumatologia": "medio",
    "psiquiatria": "medio",
    "nefrologia": "medio",
    "hematologia": "medio",
    "oncologia": "medio",
    "infectologia": "medio",
    "proctologia": "medio",
    "angiologia": "medio",
    # MEDIO-BAIXO
    "pediatria": "medio_baixo",
    "neuropediatria": "medio_baixo",
    "clinica medica": "medio_baixo",
    "clinico geral": "medio_baixo",
    "geriatria": "medio_baixo",
    "nutricao": "medio_baixo",
    "nutrologia": "medio_baixo",
    "psicologia": "medio_baixo",
    "fisioterapia": "medio_baixo",
}

DEFAULT_TIER = "medio_alto"


@dataclass(slots=True)
class SpecialtyBenchmark:
    specialty: str
    tier: str
    matched: bool  # True se casou uma especialidade conhecida; False = default
    google_cpc: tuple[float, float, float]
    google_ctr: tuple[float, float, float]
    google_cpl: tuple[float, float]
    meta_cpc: tuple[float, float, float]
    meta_ctr: tuple[float, float, float]

    @property
    def basis(self) -> str:
        if self.matched:
            return (
                "Base real Healz (operacao blended, abr-jun/2026) ajustada por "
                f"competitividade da especialidade (tier {self.tier})"
            )
        return "Base real Healz (operacao blended, abr-jun/2026) — tier padrao"


def _norm(text: str | None) -> str:
    if not text:
        return ""
    d = unicodedata.normalize("NFKD", text)
    return "".join(c for c in d if not unicodedata.combining(c)).lower().strip()


def _scale(base: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return (round(base[0] * factor, 2), round(base[1] * factor, 2), round(base[2] * factor, 2))


def _cpl_from_cpc(cpc: tuple[float, float, float]) -> tuple[float, float]:
    # CPL derivado: custo por LEAD = CPC / taxa de conversao LP->lead.
    # Faixa conservadora 8%-20% de conversao -> CPL entre cpc_low/0.20 e cpc_high/0.08.
    return (round(cpc[0] / 0.20, 0), round(cpc[2] / 0.08, 0))


def lookup(specialty: str | None) -> SpecialtyBenchmark:
    norm = _norm(specialty)
    tier = None
    matched_key = ""
    if norm:
        # casa pelo fragmento mais especifico (mais longo) contido no texto
        for key in sorted(SPECIALTY_TIER, key=len, reverse=True):
            if key in norm:
                tier = SPECIALTY_TIER[key]
                matched_key = key
                break
    matched = tier is not None
    tier = tier or DEFAULT_TIER
    factor = TIER_CPC_FACTOR[tier]
    g_cpc = _scale(BASELINE_GOOGLE_CPC, factor)
    m_cpc = _scale(BASELINE_META_CPC, factor)
    return SpecialtyBenchmark(
        specialty=specialty or "(nao informada)",
        tier=tier,
        matched=matched,
        google_cpc=g_cpc,
        google_ctr=BASELINE_GOOGLE_CTR,
        google_cpl=_cpl_from_cpc(g_cpc),
        meta_cpc=m_cpc,
        meta_ctr=BASELINE_META_CTR,
    )


def render_prompt_block(bench: SpecialtyBenchmark) -> str:
    """Bloco de fallback para injetar no contexto do researcher/strategist."""
    g = bench
    return "\n".join(
        [
            "BENCHMARK HEALZ POR ESPECIALIDADE (fallback quando nao ha volume/CPC "
            "real do DataForSEO). " + g.basis + ":",
            f"- Google Ads — CPC R$ {g.google_cpc[0]:.2f}–{g.google_cpc[2]:.2f} "
            f"(mediana ~R$ {g.google_cpc[1]:.2f}); CTR {g.google_ctr[0]:.1f}–"
            f"{g.google_ctr[2]:.1f}% (mediana ~{g.google_ctr[1]:.1f}%); "
            f"CPL estimado R$ {g.google_cpl[0]:.0f}–{g.google_cpl[1]:.0f}.",
            f"- Meta Ads — CPC R$ {g.meta_cpc[0]:.2f}–{g.meta_cpc[2]:.2f} "
            f"(mediana ~R$ {g.meta_cpc[1]:.2f}); CTR {g.meta_ctr[0]:.1f}–"
            f"{g.meta_ctr[2]:.1f}% (mediana ~{g.meta_ctr[1]:.1f}%).",
            "Use estes numeros (rotulados 'Benchmark Healz por especialidade') no "
            "lugar de faixas genericas quando o volume/CPC real nao vier.",
        ]
    )
