"""Catalogo de campos do formulario de lacunas do onboarding (metodo AQF).

E a fonte de verdade unica usada por: (1) o prompt do agente extrator, (2) o
endpoint de schema que o frontend consome para renderizar o formulario, e (3) a
renderizacao do intake como contexto para os agentes makers.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IntakeField(BaseModel):
    key: str
    label: str
    # Dica para o extrator e o operador (o que preencher / onde costuma aparecer).
    hint: str = ""
    # multiline=True vira textarea no frontend.
    multiline: bool = False
    # Campo critico para o metodo AQF (ex.: orcamento de midia) — destacado na UI.
    critical: bool = False
    # Quando preenchido, o frontend renderiza um <select> (multipla escolha).
    options: list[str] | None = None
    # optional=True: campo que pode nao existir (ex.: CNPJ de pessoa fisica) —
    # o frontend NAO marca como "lacuna" nem entra na contagem de pendencias.
    optional: bool = False


class IntakeGroup(BaseModel):
    key: str
    title: str
    fields: list[IntakeField]


INTAKE_GROUPS: list[IntakeGroup] = [
    IntakeGroup(
        key="identificacao",
        title="Identificacao",
        fields=[
            IntakeField(key="nome_completo", label="Nome completo"),
            IntakeField(key="crm", label="CRM", hint="numero do CRM com UF"),
            IntakeField(
                key="rqe",
                label="RQE",
                hint="RQE da especialidade — um ou mais, separe por virgula",
            ),
            IntakeField(key="especialidade", label="Especialidade"),
            IntakeField(key="subespecialidade", label="Subespecialidade / foco"),
            IntakeField(key="email", label="E-mail"),
            IntakeField(key="whatsapp", label="WhatsApp", hint="numero usado na captacao"),
            IntakeField(key="instagram", label="Instagram", hint="@ ou URL"),
        ],
    ),
    IntakeGroup(
        key="negocio",
        title="Dados do negocio / pessoa (secao 8)",
        fields=[
            IntakeField(key="razao_social", label="Razao social", optional=True),
            IntakeField(key="cnpj", label="CNPJ", optional=True),
            IntakeField(key="cpf", label="CPF", optional=True),
            IntakeField(key="rg", label="RG", optional=True),
            IntakeField(
                key="data_nascimento", label="Data de nascimento", optional=True
            ),
        ],
    ),
    IntakeGroup(
        key="atendimento",
        title="Atendimento e raio",
        fields=[
            IntakeField(
                key="enderecos",
                label="Endereco(s) de atendimento",
                hint="endereco completo de cada consultorio",
                multiline=True,
            ),
            IntakeField(key="cidade", label="Cidade principal"),
            IntakeField(key="estado", label="UF"),
            IntakeField(
                key="dias_horarios",
                label="Dias e horarios de atendimento",
                multiline=True,
            ),
            IntakeField(
                key="raio_atendimento",
                label="Raio de atendimento",
                hint="bairros/regiao que pretende atingir; critico para segmentacao geo",
                critical=True,
            ),
            IntakeField(
                key="telemedicina",
                label="Faz teleconsulta?",
                options=["Sim", "Nao"],
            ),
            IntakeField(
                key="secretaria",
                label="Tem secretaria?",
                options=["Sim", "Nao", "Healz"],
            ),
        ],
    ),
    IntakeGroup(
        key="oferta",
        title="Oferta e operacao",
        fields=[
            IntakeField(
                key="ticket_consulta",
                label="Valor da consulta (ticket)",
                hint="R$ — critico para viabilidade e script",
                critical=True,
            ),
            IntakeField(
                key="formas_pagamento",
                label="Formas de pagamento",
                hint="PIX, cartao (com/sem taxa), dinheiro, parcelamento",
                multiline=True,
            ),
            IntakeField(
                key="convenios_politica",
                label="Politica de convenios",
                hint="apenas particular / aceita alguns / aceita todos",
                multiline=True,
            ),
            IntakeField(
                key="retorno_politica",
                label="Politica de retorno",
                hint="15 dias / 30 dias / atrelado a alta / sem retorno incluso",
                multiline=True,
            ),
            IntakeField(key="duracao_consulta", label="Duracao da consulta"),
            IntakeField(key="politica_cancelamento", label="Politica de cancelamento"),
            IntakeField(
                key="ficha_cadastral",
                label="Exige ficha cadastral completa?",
                options=["Sim", "Nao"],
            ),
        ],
    ),
    IntakeGroup(
        key="servicos",
        title="Servicos",
        fields=[
            IntakeField(
                key="procedimentos_carro_chefe",
                label="Procedimentos carro-chefe",
                multiline=True,
            ),
            IntakeField(
                key="esteira_servicos",
                label="Esteira completa de servicos",
                multiline=True,
            ),
            IntakeField(
                key="ticket_procedimentos",
                label="Ticket medio por procedimento/cirurgia",
                multiline=True,
            ),
        ],
    ),
    IntakeGroup(
        key="objetivos",
        title="Objetivos e metas",
        fields=[
            IntakeField(
                key="foco_projeto",
                label="Foco do projeto",
                options=["Captacao", "Autoridade", "Misto"],
            ),
            IntakeField(key="meta_pacientes", label="Meta de pacientes/procedimentos por mes"),
            IntakeField(key="meta_faturamento", label="Meta de faturamento"),
            IntakeField(key="horizonte", label="Horizonte da meta", hint="3 ou 6 meses"),
            IntakeField(
                key="orcamento_midia",
                label="Orcamento de midia mensal",
                hint="R$/mes — input critico do Documento 2 (Estrategia)",
                critical=True,
            ),
        ],
    ),
    IntakeGroup(
        key="marketing",
        title="Marketing e assets",
        fields=[
            IntakeField(
                key="historico_anuncios",
                label="Historico de anuncios",
                hint="ja anunciou? plataformas? resultados",
                multiline=True,
            ),
            IntakeField(key="status_instagram", label="Status do Instagram", hint="cru / ativo / profissional"),
            IntakeField(key="fotos_disponiveis", label="Fotos disponiveis?", hint="perfil, ambiente, procedimentos"),
            IntakeField(key="depoimentos", label="Depoimentos reais?", hint="Google/Doctoralia — quantos", multiline=True),
        ],
    ),
]

# Lista achatada de chaves canonicas, na ordem de exibicao.
INTAKE_FIELD_KEYS: list[str] = [
    field.key for group in INTAKE_GROUPS for field in group.fields
]
INTAKE_FIELDS_BY_KEY = {
    field.key: (group, field)
    for group in INTAKE_GROUPS
    for field in group.fields
}


class IntakeSchemaEnvelope(BaseModel):
    data: list[IntakeGroup]


class IntakeUpdate(BaseModel):
    """Submissao do operador: mapa chave->valor. Chaves desconhecidas sao
    ignoradas; ausentes viram null."""
    fields: dict[str, str | None]


class IntakeResponse(BaseModel):
    onboarding_id: int
    status: str
    fields: dict[str, str | None]
    extracted: bool
    # True quando ja existe intake salvo (extraido ou preenchido) — usado pelo
    # frontend para liberar o botao de iniciar a esteira.
    saved: bool = False

    model_config = ConfigDict(from_attributes=False)


class IntakeEnvelope(BaseModel):
    data: IntakeResponse
