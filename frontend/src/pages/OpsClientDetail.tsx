import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ChevronDown, ChevronUp, Settings } from 'lucide-react';
import { fetchClientDashboard } from '../lib/opsApi';
import type { ClientDashboard, CampaignSnapshot } from '../types/ops';
import { formatCurrency, formatNumber, formatPct } from '../lib/formatters';
import { KPICard } from '../components/ui/KPICard';
import { StatusBadge } from '../components/ui/StatusBadge';
import { DataTable } from '../components/ui/DataTable';
import type { Column } from '../components/ui/DataTable';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

export function OpsClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const [data, setData] = useState<ClientDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCampaigns, setShowCampaigns] = useState(false);

  useEffect(() => {
    if (!clientId) return;
    fetchClientDashboard(parseInt(clientId, 10))
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [clientId]);

  if (loading) {
    return (
      <div className="py-12 flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="py-12 text-center">
        <p className="text-gray-500">Cliente não encontrado.</p>
      </div>
    );
  }

  const { client, current_week, roi, roas, health_status, weekly_history, campaigns } = data;

  // Chart data formatting
  const chartData = [...weekly_history].reverse().map(h => ({
    week: new Date(h.week_start).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }),
    revenue: h.revenue || 0,
    spend: h.ad_spend || 0,
  }));

  const campaignColumns: Column<CampaignSnapshot>[] = [
    { header: 'Campanha', accessor: 'campaign_name', className: 'font-medium text-gray-900' },
    { 
      header: 'Plataforma', 
      accessor: (row: any) => (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${row.platform === 'meta' ? 'bg-blue-100 text-blue-800' : 'bg-red-100 text-red-800'}`}>
          {row.platform.toUpperCase()}
        </span>
      )
    },
    { header: 'Impressões', accessor: (row: any) => formatNumber(row.impressions), className: 'text-right' },
    { header: 'Cliques', accessor: (row: any) => formatNumber(row.clicks), className: 'text-right' },
    { header: 'CTR', accessor: (row: any) => formatPct(row.ctr), className: 'text-right' },
    { header: 'CPC', accessor: (row: any) => formatCurrency(row.cpc), className: 'text-right' },
    { header: 'Conversões', accessor: (row: any) => formatNumber(row.conversions), className: 'text-right' },
    { header: 'Gasto', accessor: (row: any) => formatCurrency(row.spend), className: 'text-right font-medium text-gray-900' },
  ];

  return (
    <div className="py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/ops" className="p-2 text-gray-500 hover:text-gray-900 rounded-full hover:bg-gray-100 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-gray-900">{client.name}</h1>
              <StatusBadge status={health_status as any} />
            </div>
            {client.specialty && <p className="text-sm text-gray-500 mt-1">{client.specialty} • {client.city}/{client.state}</p>}
          </div>
        </div>
        <Link
          to={`/ops/${client.id}/settings`}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
        >
          <Settings className="w-4 h-4 mr-2 text-gray-500" />
          Integrações
        </Link>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPICard 
          title="Faturamento" 
          value={formatCurrency(current_week?.revenue)} 
          trend={data.revenue_change_pct ? (data.revenue_change_pct >= 0 ? 'up' : 'down') : 'neutral'}
          trendValue={data.revenue_change_pct ? `${Math.abs(data.revenue_change_pct).toFixed(1)}%` : undefined}
          subtitle="vs ant."
        />
        <KPICard 
          title="ROI" 
          value={roi !== undefined && roi !== null ? `${roi.toFixed(1)}x` : '-'} 
          trend={data.roi_change_pct ? (data.roi_change_pct >= 0 ? 'up' : 'down') : 'neutral'}
          trendValue={data.roi_change_pct ? `${Math.abs(data.roi_change_pct).toFixed(1)}%` : undefined}
          subtitle="vs ant."
        />
        <KPICard 
          title="ROAS" 
          value={roas !== undefined && roas !== null ? `${roas.toFixed(1)}x` : '-'} 
        />
        <KPICard 
          title="Consultas Agend." 
          value={formatNumber(current_week?.bookings)} 
          trend={data.bookings_change_pct ? (data.bookings_change_pct >= 0 ? 'up' : 'down') : 'neutral'}
          trendValue={data.bookings_change_pct ? `${Math.abs(data.bookings_change_pct).toFixed(1)}%` : undefined}
          subtitle="vs ant."
        />
        <KPICard 
          title="Ad Spend" 
          value={formatCurrency(current_week?.ad_spend)} 
        />
        <KPICard 
          title="Fee Healz" 
          value={formatCurrency(client.monthly_fee)} 
        />
      </div>

      {/* Chart */}
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
        <h3 className="text-base font-semibold text-gray-900 mb-6">Histórico de Faturamento (8 semanas)</h3>
        <div className="h-72 w-full">
          {chartData.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6b7280' }} tickFormatter={(value) => `R$ ${value / 1000}k`} />
                <Tooltip 
                  formatter={(value: number) => [formatCurrency(value), 'Faturamento']}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Area type="monotone" dataKey="revenue" stroke="#4f46e5" strokeWidth={3} fillOpacity={1} fill="url(#colorRevenue)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400 text-sm">Dados insuficientes para o gráfico</div>
          )}
        </div>
      </div>

      {/* Funnel */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-6">Saúde do Funil</h2>
        
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-8 bg-gray-50 p-6 rounded-lg border border-gray-100">
          <div className="text-center w-full md:w-1/4">
            <div className="text-sm text-gray-500 mb-1">Impressões</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(current_week?.impressions)}</div>
          </div>
          <div className="hidden md:block w-8 border-t-2 border-dashed border-gray-300"></div>
          <div className="text-center w-full md:w-1/4">
            <div className="text-sm text-gray-500 mb-1">Cliques</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(current_week?.clicks)}</div>
          </div>
          <div className="hidden md:block w-8 border-t-2 border-dashed border-gray-300"></div>
          <div className="text-center w-full md:w-1/4">
            <div className="text-sm text-gray-500 mb-1">Conversões (WhatsApp)</div>
            <div className="text-2xl font-bold text-gray-900">{formatNumber(current_week?.conversions)}</div>
          </div>
          <div className="hidden md:block w-8 border-t-2 border-dashed border-gray-300"></div>
          <div className="text-center w-full md:w-1/4 bg-indigo-50 py-3 rounded-lg border border-indigo-100">
            <div className="text-sm text-indigo-600 mb-1 font-medium">Agendamentos</div>
            <div className="text-2xl font-bold text-indigo-900">{formatNumber(current_week?.bookings)}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="p-4 rounded-lg bg-gray-50">
            <div className="text-xs text-gray-500 mb-1">CTR</div>
            <div className="font-semibold text-gray-900">{formatPct(current_week?.ctr)}</div>
          </div>
          <div className="p-4 rounded-lg bg-gray-50">
            <div className="text-xs text-gray-500 mb-1">CPC</div>
            <div className="font-semibold text-gray-900">{formatCurrency(current_week?.cpc)}</div>
          </div>
          <div className="p-4 rounded-lg bg-gray-50">
            <div className="text-xs text-gray-500 mb-1">Taxa LP → WhatsApp</div>
            <div className="font-semibold text-gray-900">{formatPct(current_week?.lp_to_whatsapp_rate)}</div>
          </div>
          <div className="p-4 rounded-lg bg-gray-50">
            <div className="text-xs text-gray-500 mb-1">Taxa WhatsApp → Agend.</div>
            <div className="font-semibold text-gray-900">{formatPct(current_week?.whatsapp_to_booking_rate)}</div>
          </div>
          <div className="p-4 rounded-lg bg-gray-50">
            <div className="text-xs text-gray-500 mb-1">Custo por Conversão</div>
            <div className="font-semibold text-gray-900">{formatCurrency(current_week?.cost_per_conversion)}</div>
          </div>
        </div>
      </div>

      {/* Campaigns */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div 
          className="p-6 flex justify-between items-center cursor-pointer hover:bg-gray-50 transition-colors"
          onClick={() => setShowCampaigns(!showCampaigns)}
        >
          <h2 className="text-lg font-bold text-gray-900">Campanhas da Semana ({campaigns.length})</h2>
          <button className="text-indigo-600 font-medium text-sm flex items-center">
            {showCampaigns ? (
              <>Ocultar <ChevronUp className="w-4 h-4 ml-1" /></>
            ) : (
              <>Expandir <ChevronDown className="w-4 h-4 ml-1" /></>
            )}
          </button>
        </div>
        
        {showCampaigns && (
          <div className="border-t border-gray-200">
            <DataTable
              data={campaigns}
              columns={campaignColumns}
              keyExtractor={(c) => c.id}
              className="border-0 shadow-none rounded-none"
            />
          </div>
        )}
      </div>
    </div>
  );
}
