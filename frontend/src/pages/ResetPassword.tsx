import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { api } from '../lib/api';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError('As senhas não coincidem.'); return; }
    if (password.length < 8) { setError('A senha deve ter pelo menos 8 caracteres.'); return; }

    setSubmitting(true);
    setError('');
    try {
      await api.post('/auth/reset-password', { token, password });
      navigate('/login', { state: { message: 'Senha redefinida com sucesso! Faça login.' } });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })
        ?.response?.data?.detail?.message;
      setError(msg || 'Link inválido ou expirado. Solicite um novo link.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-base">
        <p className="text-rose-600">Link inválido. <a href="/forgot-password" className="underline">Solicitar novo link</a>.</p>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-base">
      <div className="w-full max-w-md p-8 bg-card rounded-2xl shadow-md border border-line">
        <div className="flex items-center justify-center gap-2.5 mb-2">
          <img src="/favicon-healz.png" alt="" className="h-10 w-10" />
          <span className="text-3xl font-bold tracking-tight text-ink">healz</span>
        </div>
        <h2 className="text-xs font-semibold uppercase tracking-[0.25em] text-center text-subtle mb-8">Atlas</h2>

        <h1 className="text-center text-lg font-semibold text-ink mb-1">Nova senha</h1>
        <p className="text-center text-sm text-muted mb-6">Escolha uma nova senha para sua conta.</p>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 text-rose-700 rounded text-sm text-center">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted">Nova senha</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              placeholder="Mínimo 8 caracteres"
              className="mt-1 block w-full px-3 py-2 border border-line rounded-md text-sm text-ink bg-base focus:outline-none focus:ring-brand focus:border-brand"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted">Confirmar nova senha</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-line rounded-md text-sm text-ink bg-base focus:outline-none focus:ring-brand focus:border-brand"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full flex justify-center py-2 px-4 rounded-md text-sm font-medium text-onbrand bg-brand hover:bg-brand-soft disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Salvando...' : 'Redefinir senha'}
          </button>
        </form>
      </div>
    </div>
  );
}
