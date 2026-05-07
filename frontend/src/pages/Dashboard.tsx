import type { AxiosError } from 'axios';
import { ChevronRight, LogOut, Plus, Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../lib/api';
import { useAuthStore } from '../store/auth';

interface Onboarding {
  id: number;
  doctor_name: string;
  status: string;
  created_at: string;
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
        const response = await api.get('/onboardings');
        setOnboardings(response.data.data);
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
    project.doctor_name.toLowerCase().includes(query.toLowerCase().trim())
  );

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800';
      case 'RUNNING':
      case 'ACTIVE':
        return 'bg-blue-100 text-blue-800';
      case 'AWAITING_REVIEW':
        return 'bg-amber-100 text-amber-800';
      case 'APPROVED':
      case 'COMPLETED':
        return 'bg-green-100 text-green-800';
      case 'REJECTED':
        return 'bg-rose-100 text-rose-800';
      case 'FAILED':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
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
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-gray-900">Atlas-Core Dashboard</h1>
          <button
            onClick={logout}
            className="flex items-center text-gray-600 transition-colors hover:text-red-600"
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
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="block w-full rounded-md border border-gray-300 bg-white py-2 pl-10 pr-3 leading-5 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 sm:text-sm"
              placeholder="Buscar medico..."
            />
          </div>

          <button
            className="flex items-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
            onClick={() => navigate('/onboarding/new')}
          >
            <Plus className="mr-2 h-4 w-4" />
            Novo Projeto
          </button>
        </div>

        <div className="overflow-hidden rounded-md bg-white shadow">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Carregando projetos...</div>
          ) : filteredOnboardings.length === 0 ? (
            <div className="flex flex-col items-center p-12 text-center">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 text-gray-300">
                <Search className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-medium text-gray-900">Nenhum projeto encontrado</h3>
              <p className="mt-1 text-sm text-gray-500">
                {query
                  ? 'Tente ajustar a busca para encontrar um onboarding existente.'
                  : 'Comece criando um novo projeto de onboarding.'}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {filteredOnboardings.map((project) => (
                <li key={project.id}>
                  <div className="block hover:bg-gray-50">
                    <div className="flex items-center px-4 py-4 sm:px-6">
                      <div className="flex min-w-0 flex-1 items-center">
                        <div className="min-w-0 flex-1 px-4 md:grid md:grid-cols-2 md:gap-4">
                          <div>
                            <p className="truncate text-sm font-medium text-blue-600">
                              {project.doctor_name}
                            </p>
                            <p className="mt-2 flex items-center text-sm text-gray-500">
                              <span className="truncate">
                                Criado em:{' '}
                                {new Date(project.created_at).toLocaleDateString('pt-BR')}
                              </span>
                            </p>
                          </div>
                          <div className="hidden md:block">
                            <p className="text-sm text-gray-900">ID do Projeto: #{project.id}</p>
                            <p className="mt-2 flex items-center text-sm text-gray-500">
                              <span
                                className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${getStatusBadgeColor(project.status)}`}
                              >
                                {getStatusLabel(project.status)}
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
                        className="inline-flex items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
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
