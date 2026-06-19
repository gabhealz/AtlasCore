import { useState } from 'react';

import { api } from '../lib/api';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await api.post('/auth/forgot-password', { email });
      setSent(true);
    } catch {
      setError('Erro ao processar a solicitação. Tente novamente.');
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

        {sent ? (
          <div className="text-center space-y-4">
            <div className="w-12 h-12 bg-brand/10 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-6 h-6 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-ink font-medium">Email enviado!</p>
            <p className="text-sm text-muted">
              Se esse email existir no sistema, você receberá as instruções para redefinir sua senha em breve.
            </p>
            <a href="/login" className="inline-block text-sm text-brand hover:underline mt-2">
              Voltar ao login
            </a>
          </div>
        ) : (
          <>
            <h1 className="text-center text-lg font-semibold text-ink mb-1">Esqueceu a senha?</h1>
            <p className="text-center text-sm text-muted mb-6">
              Informe seu email e enviaremos um link para redefinição.
            </p>

            {error && (
              <div className="mb-4 p-3 bg-rose-50 text-rose-700 rounded text-sm text-center">{error}</div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-muted">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="seu@healz.com.br"
                  className="mt-1 block w-full px-3 py-2 border border-line rounded-md text-sm text-ink bg-base focus:outline-none focus:ring-brand focus:border-brand"
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full flex justify-center py-2 px-4 rounded-md text-sm font-medium text-onbrand bg-brand hover:bg-brand-soft disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? 'Enviando...' : 'Enviar link de redefinição'}
              </button>
            </form>

            <div className="mt-4 text-center">
              <a href="/login" className="text-sm text-muted hover:text-brand transition-colors">
                Voltar ao login
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
