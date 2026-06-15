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
  if (value === null || value === undefined) {
    return '—';
  }
  return value.toLocaleString('pt-BR');
}

function formatCpc(value: number | null) {
  if (value === null || value === undefined) {
    return '—';
  }
  return `R$ ${value.toFixed(2).replace('.', ',')}`;
}

function competitionBadge(competition: string | null) {
  const normalized = (competition || '').toUpperCase();
  if (normalized === 'LOW') {
    return 'bg-emerald-100 text-emerald-800';
  }
  if (normalized === 'MEDIUM') {
    return 'bg-amber-100 text-amber-800';
  }
  if (normalized === 'HIGH') {
    return 'bg-rose-100 text-rose-800';
  }
  return 'bg-gray-100 text-gray-700';
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
      setError('Nao foi possivel concluir a pesquisa SEO.');
    } finally {
      setLoading(false);
    }
  };

  const internal = data?.internal;
  const hasInternal =
    !!internal &&
    (internal.clients.length > 0 || internal.onboardings.length > 0);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto flex max-w-5xl flex-col">
        <header className="mb-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-brand">
            Inteligencia SEO
          </p>
          <h1 className="mt-1 text-3xl font-bold text-gray-900">
            Pesquisa de palavras-chave
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-600">
            Volume de busca, CPC e concorrencia via DataForSEO, reaproveitando o
            cache do nosso banco para economizar API. Informe a especialidade
            para cruzar com clientes e onboardings que ja atendemos.
          </p>
        </header>

        <form
          onSubmit={handleSearch}
          className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
        >
          <div className="grid gap-4 md:grid-cols-[1fr_260px]">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Palavras-chave
              </label>
              <textarea
                value={keywordsInput}
                onChange={(event) => setKeywordsInput(event.target.value)}
                rows={3}
                placeholder="harmonizacao facial, botox, preenchimento labial"
                className="mt-2 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700"
              />
              <p className="mt-1 text-xs text-gray-500">
                Separe varias por virgula, ponto e virgula ou quebra de linha.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Especialidade (opcional)
              </label>
              <input
                type="text"
                value={specialty}
                onChange={(event) => setSpecialty(event.target.value)}
                placeholder="dermatologia"
                className="mt-2 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700"
              />
              <p className="mt-1 text-xs text-gray-500">
                Cruza com nossa base de clientes/onboardings.
              </p>
            </div>
          </div>

          {error ? (
            <div className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          ) : null}

          <div className="mt-4 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-brand px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:bg-brand"
            >
              <Search className="mr-2 h-4 w-4" />
              {loading ? 'Pesquisando...' : 'Pesquisar'}
            </button>
          </div>
        </form>

        {data ? (
          <>
            <div className="mt-6 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
                <h2 className="text-lg font-semibold text-gray-900">
                  Resultados ({data.keywords.length})
                </h2>
                <span className="text-xs text-gray-500">
                  location {data.location_code} · {data.language_code}
                </span>
              </div>

              {data.keywords.length === 0 ? (
                <p className="px-6 py-6 text-sm text-gray-600">
                  Nenhum dado retornado para essas palavras-chave.
                </p>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
                    <tr>
                      <th className="px-6 py-3 font-semibold">Palavra-chave</th>
                      <th className="px-6 py-3 font-semibold">Volume/mes</th>
                      <th className="px-6 py-3 font-semibold">CPC</th>
                      <th className="px-6 py-3 font-semibold">Concorrencia</th>
                      <th className="px-6 py-3 font-semibold">Origem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.keywords.map((row) => (
                      <tr key={row.keyword}>
                        <td className="px-6 py-3 font-medium text-gray-900">
                          {row.keyword}
                        </td>
                        <td className="px-6 py-3 text-gray-700">
                          {formatVolume(row.avg_monthly_searches)}
                        </td>
                        <td className="px-6 py-3 text-gray-700">
                          {formatCpc(row.cpc)}
                        </td>
                        <td className="px-6 py-3">
                          <span
                            className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${competitionBadge(row.competition)}`}
                          >
                            {row.competition || '—'}
                          </span>
                        </td>
                        <td className="px-6 py-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${
                              row.from_cache
                                ? 'bg-sky-100 text-sky-800'
                                : 'bg-violet-100 text-violet-800'
                            }`}
                          >
                            {row.from_cache ? (
                              <Database className="h-3 w-3" />
                            ) : (
                              <Sparkles className="h-3 w-3" />
                            )}
                            {row.from_cache ? 'Cache' : 'Novo'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">
                Nossa base interna
                {internal?.specialty ? ` · ${internal.specialty}` : ''}
              </h2>
              {!internal?.specialty ? (
                <p className="mt-2 text-sm text-gray-600">
                  Informe uma especialidade na busca para cruzar com clientes e
                  onboardings que ja atendemos.
                </p>
              ) : !hasInternal ? (
                <p className="mt-2 text-sm text-gray-600">
                  Ainda nao temos clientes ou onboardings registrados nessa
                  especialidade.
                </p>
              ) : (
                <div className="mt-4 grid gap-6 md:grid-cols-2">
                  <div>
                    <p className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                      <Users className="h-4 w-4 text-emerald-600" />
                      Clientes ({internal.clients.length})
                    </p>
                    <ul className="mt-3 space-y-2">
                      {internal.clients.map((client) => (
                        <li
                          key={client.id}
                          className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm"
                        >
                          <span className="font-medium text-gray-900">
                            {client.name}
                          </span>
                          <span className="ml-2 text-xs text-gray-500">
                            {[client.city, client.state]
                              .filter(Boolean)
                              .join('/') || 'local nao informado'}
                            {client.is_active ? '' : ' · inativo'}
                          </span>
                        </li>
                      ))}
                      {internal.clients.length === 0 ? (
                        <li className="text-sm text-gray-500">Nenhum.</li>
                      ) : null}
                    </ul>
                  </div>
                  <div>
                    <p className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                      <FileText className="h-4 w-4 text-brand" />
                      Onboardings ({internal.onboardings.length})
                    </p>
                    <ul className="mt-3 space-y-2">
                      {internal.onboardings.map((onboarding) => (
                        <li
                          key={onboarding.id}
                          className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm"
                        >
                          <span className="font-medium text-gray-900">
                            {onboarding.doctor_name}
                          </span>
                          <span className="ml-2 text-xs text-gray-500">
                            #{onboarding.id} · {onboarding.status}
                          </span>
                        </li>
                      ))}
                      {internal.onboardings.length === 0 ? (
                        <li className="text-sm text-gray-500">Nenhum.</li>
                      ) : null}
                    </ul>
                  </div>
                </div>
              )}
            </div>

            {data.notes.length > 0 ? (
              <div className="mt-4 rounded-md bg-amber-50 px-4 py-3 text-xs text-amber-800">
                {data.notes.map((note, index) => (
                  <p key={index}>{note}</p>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
