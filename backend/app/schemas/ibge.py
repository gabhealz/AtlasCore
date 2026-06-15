from pydantic import BaseModel, ConfigDict


class MunicipioResponse(BaseModel):
    id: int
    nome: str
    uf_sigla: str
    uf_nome: str | None = None
    is_capital: bool = False
    populacao: int | None = None
    populacao_ano: int | None = None
    classificacao_porte: str | None = None  # AA | A | B | C

    model_config = ConfigDict(from_attributes=True)


class MunicipioEnvelope(BaseModel):
    data: MunicipioResponse


class MunicipioListEnvelope(BaseModel):
    data: list[MunicipioResponse]


class PiramideItem(BaseModel):
    faixa: str
    homens: int
    mulheres: int


class PiramideResponse(BaseModel):
    municipio_id: int
    ano: int | None = None
    data: list[PiramideItem]


class EstadoPopulacaoResponse(BaseModel):
    uf: str
    populacao: int | None = None
    ano: int | None = None
