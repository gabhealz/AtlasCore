import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Key, Plus, Trash2, CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import { fetchIntegrations, createIntegration, deleteIntegration, testIntegration, type IntegrationSetting } from '../lib/opsApi';

export function OpsClientSettings() {
  const { clientId } = useParams<{ clientId: string }>();
  const [integrations, setIntegrations] = useState<IntegrationSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  
  // Form state
  const [showForm, setShowForm] = useState(false);
  const [newPlatform, setNewPlatform] = useState('meta');
  const [newAccountId, setNewAccountId] = useState('');
  const [newAccessToken, setNewAccessToken] = useState('');

  const loadData = useCallback(() => {
    if (!clientId) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      try {
        const data = await fetchIntegrations(parseInt(clientId, 10));
        if (!cancelled) setIntegrations(data);
      } catch (_) {
        if (!cancelled) console.error(_);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [clientId]);

  useEffect(() => {
    const cleanup = loadData();
    return cleanup ?? undefined;
  }, [loadData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId) return;
    try {
      await createIntegration(parseInt(clientId, 10), {
        platform: newPlatform,
        account_id: newAccountId,
        access_token: newAccessToken,
      });
      setShowForm(false);
      setNewAccountId('');
      setNewAccessToken('');
      loadData();
    } catch (_) {
      console.error(_);
      alert('Erro ao salvar integração. Verifique os dados.');
    }
  };

  const handleDelete = async (platform: string) => {
    if (!clientId) return;
    if (!confirm(`Deseja realmente remover a integração com ${platform}?`)) return;
    
    try {
      await deleteIntegration(parseInt(clientId, 10), platform);
      loadData();
    } catch (_) {
      console.error(_);
      alert('Erro ao remover integração.');
    }
  };

  const handleTest = async (platform: string) => {
    if (!clientId) return;
    setTesting(prev => ({ ...prev, [platform]: true }));
    try {
      const result = await testIntegration(parseInt(clientId, 10), platform);
      setTestResults(prev => ({ ...prev, [platform]: result }));
    } catch {
      setTestResults(prev => ({ ...prev, [platform]: { success: false, message: 'Erro na requisição.' } }));
    } finally {
      setTesting(prev => ({ ...prev, [platform]: false }));
    }
  };

  if (loading) {
    return (
      <div className="py-12 flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand"></div>
      </div>
    );
  }

  return (
    <div className="py-8 space-y-8">
      <div className="flex items-center gap-4">
        <Link to={`/ops/${clientId}`} className="p-2 text-muted hover:text-ink rounded-full hover:bg-elevated transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Integrações</h1>
          <p className="text-muted mt-1">Gerencie os tokens e conexões das plataformas para este cliente.</p>
        </div>
      </div>

      <div className="bg-card rounded-xl shadow-sm border border-line overflow-hidden">
        <div className="p-6 border-b border-line flex justify-between items-center">
          <h2 className="text-lg font-bold text-ink flex items-center">
            <Key className="w-5 h-5 mr-2 text-brand" />
            Tokens Ativos
          </h2>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md shadow-sm text-onbrand bg-brand hover:bg-brand-soft"
            >
              <Plus className="w-4 h-4 mr-1" /> Adicionar
            </button>
          )}
        </div>

        {showForm && (
          <div className="p-6 bg-base border-b border-line">
            <form onSubmit={handleCreate} className="space-y-4 max-w-2xl">
              <div>
                <label className="block text-sm font-medium text-muted">Plataforma</label>
                <select 
                  value={newPlatform} 
                  onChange={e => setNewPlatform(e.target.value)}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-line focus:outline-none focus:ring-brand focus:border-brand sm:text-sm rounded-md border"
                >
                  <option value="meta">Meta Ads (Facebook / Instagram)</option>
                  <option value="google">Google Ads</option>
                  <option value="ga4">Google Analytics 4 (GA4)</option>
                  <option value="tintim">Tintim (WhatsApp Tracking)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-muted">
                  {newPlatform === 'meta' ? 'Account ID da Conta de Anúncios' :
                   newPlatform === 'google' ? 'Customer ID (Google Ads)' :
                   newPlatform === 'ga4' ? 'Property ID (GA4)' :
                   'Webhook Secret (auto-gerado)'}
                </label>
                <input 
                  type="text" 
                  value={newAccountId}
                  onChange={e => setNewAccountId(e.target.value)}
                  className="mt-1 block w-full border border-line rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand focus:border-brand sm:text-sm"
                  placeholder={
                    newPlatform === 'meta' ? 'ex: act_12345678' :
                    newPlatform === 'google' ? 'ex: 123-456-7890' :
                    newPlatform === 'ga4' ? 'ex: 312345678' :
                    'Será gerado automaticamente'
                  }
                  disabled={newPlatform === 'tintim'}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-muted">
                  {newPlatform === 'meta' ? 'Access Token (System User ou Pessoal)' :
                   newPlatform === 'google' ? 'Refresh Token (OAuth2)' :
                   newPlatform === 'ga4' ? 'JSON da Service Account (colar o conteúdo inteiro)' :
                   'API Key do Tintim (se disponível)'}
                </label>
                {newPlatform === 'ga4' ? (
                  <textarea 
                    required
                    rows={4}
                    value={newAccessToken}
                    onChange={e => setNewAccessToken(e.target.value)}
                    className="mt-1 block w-full border border-line rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand focus:border-brand sm:text-sm font-mono text-xs"
                    placeholder='{"type": "service_account", "project_id": "..."}'
                  />
                ) : (
                  <input 
                    type="password" 
                    required={newPlatform !== 'tintim'}
                    value={newAccessToken}
                    onChange={e => setNewAccessToken(e.target.value)}
                    className="mt-1 block w-full border border-line rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-brand focus:border-brand sm:text-sm"
                  />
                )}
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="bg-card py-2 px-4 border border-line rounded-md shadow-sm text-sm font-medium text-muted hover:bg-elevated focus:outline-none"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="bg-brand border border-transparent rounded-md shadow-sm py-2 px-4 inline-flex justify-center text-sm font-medium text-onbrand hover:bg-brand-soft focus:outline-none"
                >
                  Salvar
                </button>
              </div>
            </form>
          </div>
        )}

        {integrations.length === 0 && !showForm ? (
          <div className="p-8 text-center text-muted">
            Nenhuma integração configurada para este cliente.
          </div>
        ) : (
          <ul className="divide-y divide-line">
            {integrations.map((integ) => (
              <li key={integ.id} className="p-6 flex items-center justify-between hover:bg-elevated transition-colors">
                <div className="flex flex-col">
                  <div className="flex items-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium uppercase ${
                      integ.platform === 'meta' ? 'bg-sky-50 text-sky-700' :
                      integ.platform === 'google' ? 'bg-rose-50 text-rose-700' :
                      integ.platform === 'ga4' ? 'bg-amber-50 text-amber-700' :
                      integ.platform === 'tintim' ? 'bg-emerald-50 text-emerald-700' :
                      'bg-elevated text-muted'
                    }`}>
                      {integ.platform === 'meta' ? 'Meta Ads' :
                       integ.platform === 'google' ? 'Google Ads' :
                       integ.platform === 'ga4' ? 'GA4' :
                       integ.platform === 'tintim' ? 'Tintim' :
                       integ.platform}
                    </span>
                    <span className="ml-3 text-sm font-medium text-ink">
                      ID da Conta: <span className="font-mono font-normal text-subtle">{integ.account_id || 'Não definido'}</span>
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-muted flex items-center gap-4">
                    <span>Token Ativo: {integ.has_access_token ? 'Sim' : 'Não'}</span>
                    <span>Última Sincronização: {integ.last_sync_at ? new Date(integ.last_sync_at).toLocaleString('pt-BR') : 'Nunca'}</span>
                  </div>
                  {integ.platform === 'tintim' && integ.account_id && (
                    <div className="mt-3 p-3 rounded-lg bg-brand/10 border border-brand/20">
                      <div className="text-xs font-semibold text-ink mb-1">URL do Webhook (cole no painel do Tintim)</div>
                      <code className="block text-xs font-mono text-brand-soft break-all select-all">
                        {`${window.location.origin}/api/v1/webhooks/tintim/${integ.account_id}`}
                      </code>
                    </div>
                  )}
                  
                  {testResults[integ.platform] && (
                    <div className={`mt-3 flex items-center text-sm ${testResults[integ.platform].success ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {testResults[integ.platform].success ? <CheckCircle2 className="w-4 h-4 mr-1" /> : <XCircle className="w-4 h-4 mr-1" />}
                      {testResults[integ.platform].message}
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-4">
                  <button
                    onClick={() => handleTest(integ.platform)}
                    disabled={testing[integ.platform]}
                    className="inline-flex items-center text-sm text-brand hover:text-brand-soft disabled:opacity-50"
                  >
                    <RefreshCw className={`w-4 h-4 mr-1 ${testing[integ.platform] ? 'animate-spin' : ''}`} />
                    Testar
                  </button>
                  <button
                    onClick={() => handleDelete(integ.platform)}
                    className="inline-flex items-center text-sm text-rose-600 hover:text-rose-700"
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Remover
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
