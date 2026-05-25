import { useEffect, useState } from 'react';
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

  const loadData = () => {
    if (!clientId) return;
    setLoading(true);
    fetchIntegrations(parseInt(clientId, 10))
      .then(setIntegrations)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [clientId]);

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
    } catch (err) {
      console.error(err);
      alert('Erro ao salvar integração. Verifique os dados.');
    }
  };

  const handleDelete = async (platform: string) => {
    if (!clientId) return;
    if (!confirm(`Deseja realmente remover a integração com ${platform}?`)) return;
    
    try {
      await deleteIntegration(parseInt(clientId, 10), platform);
      loadData();
    } catch (err) {
      console.error(err);
      alert('Erro ao remover integração.');
    }
  };

  const handleTest = async (platform: string) => {
    if (!clientId) return;
    setTesting(prev => ({ ...prev, [platform]: true }));
    try {
      const result = await testIntegration(parseInt(clientId, 10), platform);
      setTestResults(prev => ({ ...prev, [platform]: result }));
    } catch (err) {
      setTestResults(prev => ({ ...prev, [platform]: { success: false, message: 'Erro na requisição.' } }));
    } finally {
      setTesting(prev => ({ ...prev, [platform]: false }));
    }
  };

  if (loading) {
    return (
      <div className="py-12 flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="py-8 space-y-8">
      <div className="flex items-center gap-4">
        <Link to={`/ops/${clientId}`} className="p-2 text-gray-500 hover:text-gray-900 rounded-full hover:bg-gray-100 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Integrações</h1>
          <p className="text-gray-500 mt-1">Gerencie os tokens e conexões das plataformas para este cliente.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-bold text-gray-900 flex items-center">
            <Key className="w-5 h-5 mr-2 text-indigo-500" />
            Tokens Ativos
          </h2>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4 mr-1" /> Adicionar
            </button>
          )}
        </div>

        {showForm && (
          <div className="p-6 bg-gray-50 border-b border-gray-200">
            <form onSubmit={handleCreate} className="space-y-4 max-w-2xl">
              <div>
                <label className="block text-sm font-medium text-gray-700">Plataforma</label>
                <select 
                  value={newPlatform} 
                  onChange={e => setNewPlatform(e.target.value)}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md border"
                >
                  <option value="meta">Meta Ads (Facebook / Instagram)</option>
                  <option value="google">Google Ads</option>
                  <option value="ga4">Google Analytics 4 (GA4)</option>
                  <option value="tintim">Tintim (WhatsApp Tracking)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  {newPlatform === 'meta' ? 'Account ID da Conta de Anúncios' :
                   newPlatform === 'google' ? 'Customer ID (Google Ads)' :
                   newPlatform === 'ga4' ? 'Property ID (GA4)' :
                   'Webhook Secret (auto-gerado)'}
                </label>
                <input 
                  type="text" 
                  value={newAccountId}
                  onChange={e => setNewAccountId(e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
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
                <label className="block text-sm font-medium text-gray-700">
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
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono text-xs"
                    placeholder='{"type": "service_account", "project_id": "..."}'
                  />
                ) : (
                  <input 
                    type="password" 
                    required={newPlatform !== 'tintim'}
                    value={newAccessToken}
                    onChange={e => setNewAccessToken(e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                )}
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 border border-transparent rounded-md shadow-sm py-2 px-4 inline-flex justify-center text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none"
                >
                  Salvar
                </button>
              </div>
            </form>
          </div>
        )}

        {integrations.length === 0 && !showForm ? (
          <div className="p-8 text-center text-gray-500">
            Nenhuma integração configurada para este cliente.
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {integrations.map((integ) => (
              <li key={integ.id} className="p-6 flex items-center justify-between hover:bg-gray-50 transition-colors">
                <div className="flex flex-col">
                  <div className="flex items-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium uppercase ${
                      integ.platform === 'meta' ? 'bg-blue-100 text-blue-800' :
                      integ.platform === 'google' ? 'bg-rose-100 text-rose-800' :
                      integ.platform === 'ga4' ? 'bg-amber-100 text-amber-800' :
                      integ.platform === 'tintim' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {integ.platform === 'meta' ? 'Meta Ads' :
                       integ.platform === 'google' ? 'Google Ads' :
                       integ.platform === 'ga4' ? 'GA4' :
                       integ.platform === 'tintim' ? 'Tintim' :
                       integ.platform}
                    </span>
                    <span className="ml-3 text-sm font-medium text-gray-900">
                      ID da Conta: <span className="font-mono font-normal text-gray-600">{integ.account_id || 'Não definido'}</span>
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500 flex items-center gap-4">
                    <span>Token Ativo: {integ.has_access_token ? 'Sim' : 'Não'}</span>
                    <span>Última Sincronização: {integ.last_sync_at ? new Date(integ.last_sync_at).toLocaleString('pt-BR') : 'Nunca'}</span>
                  </div>
                  
                  {testResults[integ.platform] && (
                    <div className={`mt-3 flex items-center text-sm ${testResults[integ.platform].success ? 'text-green-600' : 'text-red-600'}`}>
                      {testResults[integ.platform].success ? <CheckCircle2 className="w-4 h-4 mr-1" /> : <XCircle className="w-4 h-4 mr-1" />}
                      {testResults[integ.platform].message}
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-4">
                  <button
                    onClick={() => handleTest(integ.platform)}
                    disabled={testing[integ.platform]}
                    className="inline-flex items-center text-sm text-indigo-600 hover:text-indigo-900 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-4 h-4 mr-1 ${testing[integ.platform] ? 'animate-spin' : ''}`} />
                    Testar
                  </button>
                  <button
                    onClick={() => handleDelete(integ.platform)}
                    className="inline-flex items-center text-sm text-red-600 hover:text-red-900"
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
