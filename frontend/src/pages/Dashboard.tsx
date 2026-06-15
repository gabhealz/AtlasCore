import type { AxiosError } from 'axios';
import { ChevronRight, LogOut, Plus, Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../lib/api';
import { useAuthStore } from '../store/auth';

interface Onboarding {
  id: number;
  doctor_name?: string | null;
  status?: string | null;
  created_at?: string | null;
}

type OnboardingListResponse = {
  data?: Onboarding[];
};

function getDoctorName(project: Onboarding) {
  return project.doctor_name?.trim() || `Projeto #${project.id}`;
}

function formatCreatedAt(value: string | null | undefined) {
  if (!value) {
    return 'Data indisponivel';
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return 'Data indisponivel';
  }

  return parsedDate.toLocaleDateString('pt-BR');
}

export default function Dashboard() {
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const [onboardings, setOnboardings] = useState<Onboarding[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    const fetchOnboardings = async () => {
      try {
        const response = await api.get<OnboardingListResponse>('/onboardings');
        setOnboardings(Array.isArray(response.data.data) ? response.data.data : []);
      } catch (error) {
        const axiosError = error as AxiosError;
        if (axiosError.response?.status !== 401) {
          console.error('Failed to fetch onboardings', error);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchOnboardings();
  }, []);

  const filteredOnboardings = onboardings.filter((project) =>
    getDoctorName(project).toLowerCase().includes(query.toLowerCase().trim())
  );

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'PENDING':
        return 'bg-amber-50 text-amber-700';
      case 'RUNNING':
      case 'ACTIVE':
        return 'bg-sky-50 text-sky-700';
      case 'AWAITING_REVIEW':
        return 'bg-amber-50 text-amber-700';
      case 'APPROVED':
      case 'COMPLETED':
        return 'bg-emerald-50 text-emerald-700';
      case 'REJECTED':
        return 'bg-rose-50 text-rose-700';
      case 'FAILED':
        return 'bg-rose-50 text-rose-700';
      default:
        return 'bg-elevated text-muted';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'PENDING':
        return 'Pendente';
      case 'RUNNING':
        return 'Em execucao';
      case 'AWAITING_REVIEW':
        return 'Aguardando revisao';
      case 'APPROVED':
        return 'Aprovado';
      case 'REJECTED':
        return 'Recusado';
      case 'FAILED':
        return 'Falhou';
      case 'ACTIVE':
        return 'Ativo';
      case 'COMPLETED':
        return 'Concluido';
      default:
        return status;
    }
  };

  return (
    <div className="min-h-screen bg-base">
      <header className="bg-card shadow">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-ink">Atlas-Core Dashboard</h1>
          <button
            onClick={logout}
            className="flex items-center text-subtle transition-colors hover:text-rose-600"
          >
            <LogOut className="mr-1 h-5 w-5" />
            <span className="text-sm font-medium">Sair</span>
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div className="relative w-full max-w-xs">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Search className="h-5 w-5 text-subtle" />
            </div>
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="block w-full rounded-md border border-line bg-card py-2 pl-10 pr-3 leading-5 placeholder-subtle focus:border-brand focus:outline-none focus:placeholder-subtle focus:ring-1 focus:ring-brand sm:text-sm"
              placeholder="Buscar medico..."
            />
          </div>

          <div className="flex gap-2">
            <button
              className="flex items-center rounded-md border border-line bg-card px-4 py-2 text-sm font-medium text-muted shadow-sm hover:bg-elevated"
              onClick={() => navigate('/ops')}
            >
              Ops Dashboard
            </button>
            <button
              className="flex items-center rounded-md border border-transparent bg-brand px-4 py-2 text-sm font-medium text-onbrand shadow-sm hover:bg-brand-soft"
              onClick={() => navigate('/onboarding/new')}
            >
              <Plus className="mr-2 h-4 w-4" />
              Novo Projeto
            </button>
          </div>
        </div>

        <div className="overflow-hidden rounded-md bg-card shadow">
          {loading ? (
            <div className="p-8 text-center text-muted">Carregando projetos...</div>
          ) : filteredOnboardings.length === 0 ? (
            <div className="flex flex-col items-center p-12 text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-elevated text-subtle">
                <Search className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-medium text-ink">Nenhum projeto encontrado</h3>
              <p className="mt-1 text-sm text-muted">
                {query
                  ? 'Tente ajustar a busca para encontrar um onboarding existente.'
                  : 'Comece criando um novo projeto de onboarding.'}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-line">
              {filteredOnboardings.map((project) => (
                <li key={project.id}>
                  <div className="block hover:bg-elevated">
                    <div className="flex items-center px-4 py-4 sm:px-6">
                      <div className="flex min-w-0 flex-1 items-center">
                        <div className="min-w-0 flex-1 px-4 md:grid md:grid-cols-2 md:gap-4">
                          <div>
                            <p className="truncate text-sm font-semibold text-ink">
                              {getDoctorName(project)}
                            </p>
                            <p className="mt-2 flex items-center text-sm text-muted">
                              <span className="truncate">
                                Criado em:{' '}
                                {formatCreatedAt(project.created_at)}
                              </span>
                            </p>
                          </div>
                          <div className="hidden md:block">
                            <p className="text-sm text-ink">ID do Projeto: #{project.id}</p>
                            <p className="mt-2 flex items-center text-sm text-muted">
                              <span
                                className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${getStatusBadgeColor(project.status ?? '')}`}
                              >
                                {getStatusLabel(project.status ?? '')}
                              </span>
                            </p>
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          navigate(`/onboarding/${project.id}`, {
                            state: { onboardingStatus: project.status },
                          })
                        }
                        className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium text-muted transition-colors hover:border-brand/40 hover:bg-brand/10 hover:text-brand"
                      >
                        Abrir
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
