import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ChevronDown, ChevronUp, Settings, PlusCircle, Pencil } from 'lucide-react';
import { fetchClientDashboard } from '../lib/opsApi';
import type { ClientDashboard, CampaignSnapshot } from '../types/ops';
import { formatCurrency, formatNumber, formatPct } from '../lib/formatters';
import { KPICard } from '../components/ui/KPICard';
import { StatusBadge } from '../components/ui/StatusBadge';
import { DataTable } from '../components/ui/DataTable';
import type { Column } from '../components/ui/DataTable';
import { ManualMetricsModal } from '../components/ops/ManualMetricsModal';
import { EditClientModal } from '../components/ops/EditClientModal';
import { IbgeMarketPanel } from '../components/ops/IbgeMarketPanel';
import { benchmarks, healthClasses, healthDot, type Diag } from '../lib/benchmarks';
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
  const [showManual, setShowManual] = useState(false);
  const [showEdit, setShowEdit] = useState(false);

  const load = useCallback(() => {
    if (!clientId) return;
    fetchClientDashboard(parseInt(clientId, 10))
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [clientId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="py-12 flex justify-center items-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted">Cliente não encontrado.</p>
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
    { header: 'Campanha', accessor: 'campaign_name', className: 'font-medium text-ink' },
    {
      header: 'Plataforma',
      accessor: (row: any) => (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${row.platform === 'meta' ? 'bg-sky-50 text-sky-700' : 'bg-rose-50 text-rose-700'}`}>
          {row.platform.toUpperCase()}
        </span>
      )
    },
    { header: 'Impressões', accessor: (row: any) => formatNumber(row.impressions), className: 'text-right' },
    { header: 'Cliques', accessor: (row: any) => formatNumber(row.clicks), className: 'text-right' },
    { header: 'CTR', accessor: (row: any) => formatPct(row.ctr), className: 'text-right' },
    { header: 'CPC', accessor: (row: any) => formatCurrency(row.cpc), className: 'text-right' },
    { header: 'Conversões', accessor: (row: any) => formatNumber(row.conversions), className: 'text-right' },
    { header: 'Gasto', accessor: (row: any) => formatCurrency(row.spend), className: 'text-right font-medium text-ink' },
  ];

  return (
    <div className="py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/ops" className="p-2 text-muted hover:text-ink rounded-full hover:bg-elevated transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-ink">{client.name}</h1>
              <StatusBadge status={health_status as any} />
            </div>
            {(client.specialty || client.city) && <p className="text-sm text-muted mt-1">{client.specialty}{client.city ? ` • ${client.city}/${client.state}` : ''}</p>}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowEdit(true)}
            className={`inline-flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              client.is_draft
                ? 'bg-brand text-onbrand hover:bg-brand-soft'
                : 'border border-line text-muted bg-card hover:bg-elevated'
            }`}
          >
            <Pencil className="w-4 h-4 mr-2" />
            {client.is_draft ? 'Concluir cadastro' : 'Editar'}
          </button>
          <button
            onClick={() => setShowManual(true)}
            className="inline-flex items-center px-4 py-2 rounded-md text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft transition-colors"
          >
            <PlusCircle className="w-4 h-4 mr-2" />
            Lançar dados
          </button>
          <Link
            to={`/ops/${client.id}/settings`}
            className="inline-flex items-center px-4 py-2 border border-line rounded-md shadow-sm text-sm font-medium text-muted bg-card hover:bg-elevated transition-colors"
          >
            <Settings className="w-4 h-4 mr-2 text-subtle" />
            Integrações
          </Link>
        </div>
      </div>

      {showEdit && (
        <EditClientModal client={client} onClose={() => setShowEdit(false)} onSaved={load} />
      )}
      {showManual && clientId && (
        <ManualMetricsModal
          clientId={parseInt(clientId, 10)}
          onClose={() => setShowManual(false)}
          onSaved={load}
        />
      )}

      {/* Contrato / tempo de casa (LTV) */}
      <div className="flex flex-wrap gap-x-10 gap-y-3 bg-card border border-line rounded-xl px-6 py-4 text-sm">
        <div>
          <div className="text-subtle">Plano</div>
          <div className="text-ink font-medium">{client.plan_name || '—'}</div>
        </div>
        <div>
          <div className="text-subtle">Início do contrato</div>
          <div className="text-ink font-medium">{client.contract_start_date ? client.contract_start_date.split('-').reverse().join('/') : '—'}</div>
        </div>
        <div>
          <div className="text-subtle">Tempo de casa</div>
          <div className="text-brand font-semibold">{client.tenure_months != null ? `${client.tenure_months} meses` : '—'}{client.tenure_days != null ? ` (${client.tenure_days} dias)` : ''}</div>
        </div>
        <div>
          <div className="text-subtle">Fee mensal</div>
          <div className="text-ink font-medium">{formatCurrency(client.monthly_fee)}</div>
        </div>
        <div>
          <div className="text-subtle">Receita acumulada (LTV Healz)</div>
          <div className="text-brand font-semibold">
            {client.tenure_months != null ? formatCurrency(client.tenure_months * client.monthly_fee) : '—'}
          </div>
        </div>
        <div>
          <div className="text-subtle">Situação</div>
          <div className="text-ink font-medium">{client.is_active ? 'Ativo' : 'Suspenso'}</div>
        </div>
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
      <div className="bg-card p-6 rounded-xl border border-line shadow-sm">
        <h3 className="text-base font-semibold text-ink mb-6">Histórico de Faturamento (8 semanas)</h3>
        <div className="h-72 w-full">
          {chartData.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ec298f" stopOpacity={0.35}/>
                    <stop offset="95%" stopColor="#ec298f" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7e9f2" />
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9aa1b4' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9aa1b4' }} tickFormatter={(value) => `R$ ${value / 1000}k`} />
                <Tooltip
                  formatter={(value: number) => [formatCurrency(value), 'Faturamento']}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e7e9f2', background: '#ffffff', color: '#1a1f36' }}
                  labelStyle={{ color: '#9aa1b4' }}
                />
                <Area type="monotone" dataKey="revenue" stroke="#ec298f" strokeWidth={3} fillOpacity={1} fill="url(#colorRevenue)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-subtle text-sm">Dados insuficientes para o gráfico</div>
          )}
        </div>
      </div>

      {/* Funnel */}
      <div className="bg-card rounded-xl shadow-sm border border-line p-6">
        <h2 className="text-lg font-bold text-ink mb-6">Saúde do Funil</h2>

        <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-8 bg-base p-6 rounded-lg border border-line">
          <div className="text-center w-full md:w-1/4">
            <div className="text-sm text-muted mb-1">Impressões</div>
            <div className="text-2xl font-bold text-ink">{formatNumber(current_week?.impressions)}</div>
          </div>
          <div className="hidden md:block w-8 border-t-2 border-dashed border-line"></div>
          <div className="text-center w-full md:w-1/4">
            <div className="text-sm text-muted mb-1">Cliques</div>
            <div className="text-2xl font-bold text-ink">{formatNumber(current_week?.clicks)}</div>
          </div>
          <div className="hidden md:block w-8 border-t-2 border-dashed border-line"></div>
          <div className="text-center w-full md:w-1/4">
            <div className="text-sm text-muted mb-1">Conversões (WhatsApp)</div>
            <div className="text-2xl font-bold text-ink">{formatNumber(current_week?.conversions)}</div>
          </div>
          <div className="hidden md:block w-8 border-t-2 border-dashed border-line"></div>
          <div className="text-center w-full md:w-1/4 bg-brand/10 py-3 rounded-lg border border-brand/30">
            <div className="text-sm text-brand mb-1 font-medium">Agendamentos</div>
            <div className="text-2xl font-bold text-ink">{formatNumber(current_week?.bookings)}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {([
            { d: benchmarks.ctr(current_week?.ctr), v: formatPct(current_week?.ctr) },
            { d: benchmarks.cpc(current_week?.cpc), v: formatCurrency(current_week?.cpc) },
            { d: benchmarks.lp_to_whatsapp_rate(current_week?.lp_to_whatsapp_rate), v: formatPct(current_week?.lp_to_whatsapp_rate) },
            { d: benchmarks.whatsapp_to_booking_rate(current_week?.whatsapp_to_booking_rate), v: formatPct(current_week?.whatsapp_to_booking_rate) },
            { d: benchmarks.cost_per_conversion(current_week?.cost_per_conversion), v: formatCurrency(current_week?.cost_per_conversion) },
          ] as { d: Diag; v: string }[]).map(({ d, v }) => (
            <div key={d.label} className={`p-4 rounded-lg border ${healthClasses(d.status)}`} title={d.ideal}>
              <div className="flex items-center gap-1.5 mb-1">
                <span className={`inline-block w-2 h-2 rounded-full ${healthDot(d.status)}`}></span>
                <span className="text-xs text-muted">{d.label}</span>
              </div>
              <div className="font-semibold text-ink">{v}</div>
              <div className="text-[10px] text-subtle mt-1 leading-tight">{d.ideal}</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-subtle mt-4">Diagnóstico segundo os benchmarks internos da Healz (Doc 3). Verde = saudável · Amarelo = atenção · Vermelho = gargalo.</p>
      </div>

      {/* Mercado da região (IBGE) */}
      <IbgeMarketPanel city={client.city} state={client.state} />

      {/* Campaigns */}
      <div className="bg-card rounded-xl shadow-sm border border-line overflow-hidden">
        <div
          className="p-6 flex justify-between items-center cursor-pointer hover:bg-elevated transition-colors"
          onClick={() => setShowCampaigns(!showCampaigns)}
        >
          <h2 className="text-lg font-bold text-ink">Campanhas da Semana ({campaigns.length})</h2>
          <button className="text-brand font-medium text-sm flex items-center">
            {showCampaigns ? (
              <>Ocultar <ChevronUp className="w-4 h-4 ml-1" /></>
            ) : (
              <>Expandir <ChevronDown className="w-4 h-4 ml-1" /></>
            )}
          </button>
        </div>
        
        {showCampaigns && (
          <div className="border-t border-line">
            <DataTable
              data={[...campaigns].sort((a, b) => (Number(b.spend) || 0) - (Number(a.spend) || 0))}
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
