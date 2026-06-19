import { useState } from 'react';
import { Search, Database, Sparkles, Users, FileText } from 'lucide-react';

import { api } from '../lib/api';

type KeywordResult = {
  keyword: string;
  avg_monthly_searches: number | null;
  cpc: number | null;
  competition: string | null;
  source: string;
  from_cache: boolean;
  queried_at?: string | null;
};

type InternalClient = {
  id: number;
  name: string;
  specialty?: string | null;
  city?: string | null;
  state?: string | null;
  is_active: boolean;
};

type InternalOnboarding = {
  id: number;
  doctor_name: string;
  specialty?: string | null;
  status: string;
};

type SearchData = {
  keywords: KeywordResult[];
  internal: {
    specialty: string | null;
    clients: InternalClient[];
    onboardings: InternalOnboarding[];
  };
  notes: string[];
  location_code: number;
  language_code: string;
};

type SearchResponse = { data: SearchData };

function formatVolume(value: number | null) {
  if (value === null || value === undefined) return '—';
  return value.toLocaleString('pt-BR');
}

function formatCpc(value: number | null) {
  if (value === null || value === undefined) return '—';
  return `R$ ${value.toFixed(2).replace('.', ',')}`;
}

function competitionBadge(competition: string | null) {
  const normalized = (competition || '').toUpperCase();
  if (normalized === 'LOW') return 'bg-emerald-100 text-emerald-800';
  if (normalized === 'MEDIUM') return 'bg-amber-100 text-amber-800';
  if (normalized === 'HIGH') return 'bg-rose-100 text-rose-800';
  return 'bg-elevated text-muted';
}

export function SeoResearch() {
  const [keywordsInput, setKeywordsInput] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<SearchData | null>(null);

  const handleSearch = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const keywords = keywordsInput
      .split(/[\n,;]/)
      .map((item) => item.trim())
      .filter(Boolean);

    if (keywords.length === 0) {
      setError('Informe ao menos uma palavra-chave.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await api.post<SearchResponse>('/seo/keywords', {
        keywords,
        specialty: specialty.trim() || null,
      });
      setData(response.data.data);
    } catch {
      setError('Não foi possível concluir a pesquisa SEO.');
    } finally {
      setLoading(false);
    }
  };

  const internal = data?.internal;
  const hasInternal =
    !!internal && (internal.clients.length > 0 || internal.onboardings.length > 0);

  return (
    <div className="py-8 space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand mb-1">
          Inteligência SEO
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-ink">
          Pesquisa de palavras-chave
        </h1>
        <p className="mt-1 text-sm text-muted max-w-2xl">
          Volume de busca, CPC e concorrência via DataForSEO, com cache interno para economizar API.
          Informe a especialidade para cruzar com nossa base de clientes e onboardings.
        </p>
      </div>

      <form
        onSubmit={handleSearch}
        className="bg-card rounded-xl border border-line p-6 shadow-sm"
      >
        <div className="grid gap-4 md:grid-cols-[1fr_260px]">
          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">
              Palavras-chave
            </label>
            <textarea
              value={keywordsInput}
              onChange={(e) => setKeywordsInput(e.target.value)}
              rows={3}
              placeholder="harmonização facial, botox, preenchimento labial"
              className="block w-full rounded-lg border border-line bg-base px-3 py-2 text-sm text-ink placeholder-subtle focus:outline-none focus:ring-2 focus:ring-brand"
            />
            <p className="mt-1 text-xs text-muted">
              Separe por vírgula, ponto e vírgula ou quebra de linha.
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-ink mb-1.5">
              Especialidade (opcional)
            </label>
            <input
              type="text"
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
              placeholder="dermatologia"
              className="block w-full rounded-lg border border-line bg-base px-3 py-2 text-sm text-ink placeholder-subtle focus:outline-none focus:ring-2 focus:ring-brand"
            />
            <p className="mt-1 text-xs text-muted">
              Cruza com nossa base de clientes/onboardings.
            </p>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        <div className="mt-4 flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            <Search className="w-4 h-4" />
            {loading ? 'Pesquisando...' : 'Pesquisar'}
          </button>
        </div>
      </form>

      {data && (
        <>
          <div className="bg-card rounded-xl border border-line shadow-sm overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-6 py-4">
              <h2 className="text-base font-semibold text-ink">
                Resultados ({data.keywords.length})
              </h2>
              <span className="text-xs text-muted">
                location {data.location_code} · {data.language_code}
              </span>
            </div>

            {data.keywords.length === 0 ? (
              <p className="px-6 py-6 text-sm text-muted">
                Nenhum dado retornado para essas palavras-chave.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-elevated text-xs uppercase tracking-wide text-subtle">
                    <tr>
                      <th className="px-6 py-3 font-semibold">Palavra-chave</th>
                      <th className="px-6 py-3 font-semibold">Volume/mês</th>
                      <th className="px-6 py-3 font-semibold">CPC</th>
                      <th className="px-6 py-3 font-semibold">Concorrência</th>
                      <th className="px-6 py-3 font-semibold">Origem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {data.keywords.map((row) => (
                      <tr key={row.keyword} className="hover:bg-elevated/50 transition-colors">
                        <td className="px-6 py-3 font-medium text-ink">{row.keyword}</td>
                        <td className="px-6 py-3 text-ink">{formatVolume(row.avg_monthly_searches)}</td>
                        <td className="px-6 py-3 text-ink">{formatCpc(row.cpc)}</td>
                        <td className="px-6 py-3">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${competitionBadge(row.competition)}`}>
                            {row.competition || '—'}
                          </span>
                        </td>
                        <td className="px-6 py-3">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
                            row.from_cache ? 'bg-sky-100 text-sky-800' : 'bg-violet-100 text-violet-800'
                          }`}>
                            {row.from_cache ? <Database className="w-3 h-3" /> : <Sparkles className="w-3 h-3" />}
                            {row.from_cache ? 'Cache' : 'Novo'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="bg-card rounded-xl border border-line p-6 shadow-sm">
            <h2 className="text-base font-semibold text-ink">
              Nossa base interna{internal?.specialty ? ` · ${internal.specialty}` : ''}
            </h2>
            {!internal?.specialty ? (
              <p className="mt-2 text-sm text-muted">
                Informe uma especialidade para cruzar com clientes e onboardings que já atendemos.
              </p>
            ) : !hasInternal ? (
              <p className="mt-2 text-sm text-muted">
                Ainda não temos clientes ou onboardings registrados nessa especialidade.
              </p>
            ) : (
              <div className="mt-4 grid gap-6 md:grid-cols-2">
                <div>
                  <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                    <Users className="w-4 h-4 text-emerald-600" />
                    Clientes ({internal.clients.length})
                  </p>
                  <ul className="mt-3 space-y-2">
                    {internal.clients.map((client) => (
                      <li key={client.id} className="rounded-lg border border-line bg-elevated px-3 py-2 text-sm">
                        <span className="font-medium text-ink">{client.name}</span>
                        <span className="ml-2 text-xs text-muted">
                          {[client.city, client.state].filter(Boolean).join('/') || 'local não informado'}
                          {client.is_active ? '' : ' · inativo'}
                        </span>
                      </li>
                    ))}
                    {internal.clients.length === 0 && (
                      <li className="text-sm text-muted">Nenhum.</li>
                    )}
                  </ul>
                </div>
                <div>
                  <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                    <FileText className="w-4 h-4 text-brand" />
                    Onboardings ({internal.onboardings.length})
                  </p>
                  <ul className="mt-3 space-y-2">
                    {internal.onboardings.map((onboarding) => (
                      <li key={onboarding.id} className="rounded-lg border border-line bg-elevated px-3 py-2 text-sm">
                        <span className="font-medium text-ink">{onboarding.doctor_name}</span>
                        <span className="ml-2 text-xs text-muted">
                          #{onboarding.id} · {onboarding.status}
                        </span>
                      </li>
                    ))}
                    {internal.onboardings.length === 0 && (
                      <li className="text-sm text-muted">Nenhum.</li>
                    )}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {data.notes.length > 0 && (
            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-xs text-amber-800">
              {data.notes.map((note, i) => <p key={i}>{note}</p>)}
            </div>
          )}
        </>
      )}
    </div>
  );
}
