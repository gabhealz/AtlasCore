import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AxiosError } from 'axios';

import { useAuthStore } from '../store/auth';
import { api } from '../lib/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const setToken = useAuthStore((state) => state.setToken);
  const navigate = useNavigate();

  type LoginErrorResponse = {
    detail?: {
      message?: string;
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await api.post(
        '/auth/login',
        { email, password },
        { timeout: 15000 },
      );
      setToken(response.data.access_token);
      navigate('/dashboard');
    } catch (err) {
      const error = err as AxiosError<LoginErrorResponse>;
      if (error.code === 'ECONNABORTED') {
        setError(
          'A API demorou demais para responder. Tente novamente em alguns segundos.',
        );
      } else if (!error.response) {
        setError(
          'Nao foi possivel conectar com a API. Verifique se o backend esta online.',
        );
      } else {
        setError(
          error.response.data?.detail?.message || 'Erro ao realizar login.',
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-base">
      <div className="w-full max-w-md p-8 bg-card rounded-2xl shadow-md border border-line">
        <div className="flex items-center justify-center gap-2.5 mb-2">
          <img src="/favicon-healz.png" alt="" className="h-10 w-10" />
          <span className="text-3xl font-bold tracking-tight text-ink">healz</span>
        </div>
        <h2 className="text-xs font-semibold uppercase tracking-[0.25em] text-center text-subtle mb-8">Atlas</h2>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 text-rose-700 rounded text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-line rounded-md shadow-sm focus:outline-none focus:ring-brand focus:border-brand"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted">Senha</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-line rounded-md shadow-sm focus:outline-none focus:ring-brand focus:border-brand"
            />
          </div>
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-onbrand bg-brand hover:bg-brand-soft focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand disabled:cursor-not-allowed disabled:bg-brand/40"
          >
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}
