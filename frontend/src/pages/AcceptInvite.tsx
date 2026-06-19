import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useAuthStore } from '../store/auth';
import { api } from '../lib/api';

type InviteInfo = { email: string; role: string; department: string | null };

export default function AcceptInvite() {
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);

  const [info, setInfo] = useState<InviteInfo | null>(null);
  const [loadError, setLoadError] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) { setLoadError('Link inválido.'); return; }
    api.get<{ email: string; role: string; department: string | null }>(`/auth/invitation-info?token=${token}`)
      .then((r) => setInfo(r.data))
      .catch(() => setLoadError('Este convite é inválido ou já expirou.'));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError('As senhas não coincidem.'); return; }
    if (password.length < 8) { setError('A senha deve ter pelo menos 8 caracteres.'); return; }
    setSubmitting(true);
    setError('');
    try {
      const r = await api.post<{ access_token: string }>('/auth/accept-invite', {
        token,
        full_name: fullName,
        password,
      });
      setToken(r.data.access_token);
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })
        ?.response?.data?.detail?.message;
      setError(msg || 'Erro ao criar conta. Tente novamente.');
    } finally {
      setSubmitting(false);
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

        {loadError ? (
          <div className="text-center">
            <p className="text-rose-600 text-sm font-medium mb-4">{loadError}</p>
            <a href="/login" className="text-sm text-brand hover:underline">Ir para o login</a>
          </div>
        ) : !info ? (
          <p className="text-center text-muted text-sm">Verificando convite...</p>
        ) : (
          <>
            <p className="text-sm text-muted text-center mb-6">
              Você foi convidado para o Atlas com o email{' '}
              <strong className="text-ink">{info.email}</strong>.
            </p>

            {error && (
              <div className="mb-4 p-3 bg-rose-50 text-rose-700 rounded text-sm text-center">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-muted">Seu nome completo</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder="Ex: João Silva"
                  className="mt-1 block w-full px-3 py-2 border border-line rounded-md text-sm text-ink bg-base focus:outline-none focus:ring-brand focus:border-brand"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted">Criar senha</label>
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
                <label className="block text-sm font-medium text-muted">Confirmar senha</label>
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
                {submitting ? 'Criando conta...' : 'Criar conta'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
