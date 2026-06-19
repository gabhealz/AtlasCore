import { api } from './api';

export interface Municipio {
  id: number;
  nome: string;
  uf_sigla: string;
  uf_nome?: string;
  is_capital: boolean;
  populacao?: number;
  populacao_ano?: number;
  classificacao_porte?: string; // AA | A | B | C
}

export interface PiramideItem {
  faixa: string;
  homens: number;
  mulheres: number;
}

export interface PiramideResponse {
  municipio_id: number;
  ano?: number;
  data: PiramideItem[];
}

export async function resolveMunicipio(city: string, uf: string): Promise<Municipio> {
  const res = await api.get<{ data: Municipio }>('/ibge/resolve', { params: { city, uf } });
  return res.data.data;
}

export async function fetchPiramide(municipioId: number): Promise<PiramideResponse> {
  const res = await api.get<PiramideResponse>(`/ibge/municipios/${municipioId}/piramide`);
  return res.data;
}

export interface RendaData {
  municipio_id: number;
  renda_per_capita: number | null;
  ano: number | null;
  fonte: string;
}

export async function fetchRenda(municipioId: number): Promise<RendaData> {
  const res = await api.get<RendaData>(`/ibge/municipios/${municipioId}/renda`);
  return res.data;
}

export const PORTE_LABEL: Record<string, string> = {
  AA: 'Capital',
  A: 'Interior grande (> 300 mil)',
  B: 'Interior médio (100–300 mil)',
  C: 'Interior pequeno (≤ 100 mil)',
};
