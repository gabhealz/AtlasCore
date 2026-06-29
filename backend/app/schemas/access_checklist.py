"""Catalogo do checklist operacional de Contas & Acessos (secao 2 do onboarding).

Apoio operacional para o time configurar contas/integracoes do cliente. NAO
bloqueia a esteira de IA; serve para acompanhar o progresso da configuracao.
"""
from __future__ import annotations

import json

from pydantic import BaseModel


class AccessChecklistItem(BaseModel):
    key: str
    label: str
    url: str = ""
    hint: str = ""


ACCESS_CHECKLIST_ITEMS: list[AccessChecklistItem] = [
    AccessChecklistItem(
        key="whatsapp_group",
        label="Criar grupo de WhatsApp do cliente",
    ),
    AccessChecklistItem(key="drive_folder", label="Criar pasta no Google Drive"),
    AccessChecklistItem(
        key="gmb",
        label="Google Meu Negocio (Perfil da Empresa)",
        url="https://business.google.com",
        hint="criar/assumir o perfil antes do lancamento de Search",
    ),
    AccessChecklistItem(
        key="google_ads",
        label="Google Ads",
        url="https://business.google.com/br/google-ads/",
    ),
    AccessChecklistItem(
        key="gtm",
        label="Google Tag Manager",
        url="https://tagmanager.google.com/",
    ),
    AccessChecklistItem(
        key="ga4",
        label="Google Analytics (GA4)",
        url="https://analytics.google.com/analytics/web",
        hint="adicionar o e-mail do robo como Visualizador na propriedade",
    ),
    AccessChecklistItem(
        key="meta_business",
        label="Meta Business / Meta Ads configurado",
        url="https://business.meta.com/",
    ),
    AccessChecklistItem(
        key="hosting",
        label="Hospedagem (Hostinger)",
        url="https://www.hostinger.com.br/",
        hint="se nao tiver, indicar e pegar acesso administrativo",
    ),
    AccessChecklistItem(key="domain", label="Dominio registrado/apontado"),
    AccessChecklistItem(
        key="wordpress",
        label="WordPress + Elementor para a landing page",
    ),
    AccessChecklistItem(
        key="access_granted",
        label="Acesso administrativo concedido a gabriel@healz.com.br",
    ),
]

ACCESS_CHECKLIST_KEYS = [item.key for item in ACCESS_CHECKLIST_ITEMS]


def load_checklist_state(raw: str | None) -> dict[str, bool]:
    state = {key: False for key in ACCESS_CHECKLIST_KEYS}
    if not raw:
        return state
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return state
    if isinstance(parsed, dict):
        for key in ACCESS_CHECKLIST_KEYS:
            state[key] = bool(parsed.get(key, False))
    return state


def dump_checklist_state(state: dict[str, bool]) -> str:
    return json.dumps(
        {key: bool(state.get(key, False)) for key in ACCESS_CHECKLIST_KEYS},
        ensure_ascii=False,
    )


class AccessChecklistSchemaEnvelope(BaseModel):
    data: list[AccessChecklistItem]


class AccessChecklistUpdate(BaseModel):
    state: dict[str, bool]


class AccessChecklistResponse(BaseModel):
    onboarding_id: int
    state: dict[str, bool]


class AccessChecklistEnvelope(BaseModel):
    data: AccessChecklistResponse
