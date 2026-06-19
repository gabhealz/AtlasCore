import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, DollarSign, Calendar, Activity, ChevronRight, TrendingUp, Plus } from 'lucide-react';
import { fetchOpsDashboard } from '../lib/opsApi';
import type { ClientDashboard } from '../types/ops';
import { formatCurrency, formatNumber } from '../lib/formatters';
import { StatusBadge } from '../components/ui/StatusBadge';
import { DataTable } from '../components/ui/DataTable';
import { KPICard } from '../components/ui/KPICard';
import { NewClientModal } from '../components/ops/NewClientModal';
import { OpsLtvPanel } from '../components/ops/OpsLtvPanel';

/** Generate the last N Monday dates as week options */
function generateWeekOptions(count: number): Array<{ label: string; value: string }> {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0=Sunday, 1=Monday, ...
  // Days since last Monday (Sunday=6, Monday=0, ...)
  const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
  const currentMonday = new Date(today);
  currentMonday.setDate(today.getDate() - daysToMonday);
  currentMonday.setHours(0, 0, 0, 0);

  const options: Array<{ label: string; value: string }> = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(currentMonday);
    d.setDate(currentMonday.getDate() - i * 7);
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    const label = `Seg ${dd}/${mm}/${yyyy}`;
    const value = `${yyyy}-${mm}-${dd}`;
    options.push({ label, value });
  }
  return options;
}

export function OpsDashboard() {
  const [data, setData] = useState<ClientDashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showNewClient, setShowNewClient] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'suspended' | 'draft'>('all');
  const [healthFilter, setHealthFilter] = useState<'all' | 'green' | 'yellow' | 'red'>('all');
  const [planFilter, setPlanFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<string>('activity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [selectedWeek, setSelectedWeek] = useState<string>('');

  const weekOptions = useMemo(() => generateWeekOptions(12), []);

  const load = useCallback((week?: string) => {
    setLoading(true);
    fetchOpsDashboard(week || undefined)
      .then((res) => {
        if (!Array.isArray(res)) {
          setErrorMsg(`A API retornou algo inesperado: ${JSON.stringify(res)}`);
          setData([]);
        } else {
          setData(res);
        }
      })
      .catch((err) => setErrorMsg(err.message || String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load(selectedWeek || undefined);
  }, [load, selectedWeek]);

  if (errorMsg) {
    return (
      <div className="p-8 text-rose-600">
        <h2 className="text-xl font-bold">Erro de Renderização/API</h2>
        <pre className="mt-4 p-4 bg-rose-50 rounded-lg whitespace-pre-wrap">{errorMsg}</pre>
      </div>
    );
  }

  const plans = Array.from(
    new Set((data || []).map((d) => d.client.plan_name).filter(Boolean))
  ) as string[];

  const ltv = (d: ClientDashboard) =>
    (d.client.tenure_months || 0) * (d.client.monthly_fee || 0);

  const sortValue = (d: ClientDashboard): number | string => {
    switch (sortField) {
      case 'name': return (d.client.name || '').toLowerCase();
      case 'tenure': return d.client.tenure_months ?? -1;
      case 'revenue': return d.current_week?.revenue || 0;
      case 'spend': return d.current_week?.ad_spend || 0;
      case 'roi': return d.roi ?? -1;
      case 'bookings': return d.current_week?.bookings || 0;
      case 'fee': return d.client.monthly_fee || 0;
      case 'ltv': return ltv(d);
      default: return (d.current_week?.ad_spend || 0) + (d.current_week?.revenue || 0); // activity
    }
  };

  const filteredData = (data || [])
    .filter((item) => {
      try {
        if (!item?.client?.name?.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        if (statusFilter === 'active' && (!item.client.is_active || item.client.is_draft)) return false;
        if (statusFilter === 'suspended' && item.client.is_active) return false;
        if (statusFilter === 'draft' && !item.client.is_draft) return false;
        if (healthFilter !== 'all' && item.health_status !== healthFilter) return false;
        if (planFilter !== 'all' && item.client.plan_name !== planFilter) return false;
        return true;
      } catch (e) {
        console.error('Filter error on item:', item, e);
        return false;
      }
    })
    .sort((a, b) => {
      const av = sortValue(a);
      const bv = sortValue(b);
      let cmp: number;
      if (typeof av === 'string' || typeof bv === 'string') {
        cmp = String(av).localeCompare(String(bv));
      } else {
        cmp = av - bv;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

  const totalRevenue = filteredData.reduce((acc, curr) => acc + (curr.current_week?.revenue || 0), 0);
  const totalSpend = filteredData.reduce((acc, curr) => acc + (curr.current_week?.ad_spend || 0), 0);
  const totalBookings = filteredData.reduce((acc, curr) => acc + (curr.current_week?.bookings || 0), 0);
  const averageRoi = totalSpend > 0 ? totalRevenue / totalSpend : 0;

  const columns = [
    {
      header: 'Cliente',
      accessor: (row: ClientDashboard) => (
        <div>
          <div className="font-medium text-ink flex items-center gap-2">
            {row.client.name}
            {row.client.is_draft && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                Rascunho
              </span>
            )}
          </div>
          <div className="text-xs text-subtle">
            {row.client.specialty || row.client.plan_name || '—'}
          </div>
        </div>
      ),
    },
    {
      header: 'Status',
      accessor: (row: ClientDashboard) => (
        <StatusBadge status={row.health_status} />
      ),
    },
    {
      header: 'Tempo de casa',
      accessor: (row: ClientDashboard) =>
        row.client.tenure_months != null ? `${row.client.tenure_months} meses` : '-',
      className: 'text-right text-muted',
    },
    {
      header: 'Faturamento',
      accessor: (row: ClientDashboard) => formatCurrency(row.current_week?.revenue),
      className: 'text-right'
    },
    {
      header: 'Investimento',
      accessor: (row: ClientDashboard) => formatCurrency(row.current_week?.ad_spend),
      className: 'text-right'
    },
    {
      header: 'ROI',
      accessor: (row: ClientDashboard) => row.roi ? `${row.roi.toFixed(1)}x` : '-',
      className: 'text-right font-medium text-ink'
    },
    {
      header: 'Consultas',
      accessor: (row: ClientDashboard) => formatNumber(row.current_week?.bookings),
      className: 'text-right'
    },
    {
      header: '',
      accessor: (row: ClientDashboard) => (
        <Link
          to={`/ops/${row.client.id}`}
          className="inline-flex items-center text-sm font-medium text-brand hover:text-brand-soft"
        >
          Detalhes <ChevronRight className="ml-1 w-4 h-4" />
        </Link>
      ),
      className: 'text-right'
    }
  ];

  return (
    <div className="py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Ops Dashboard</h1>
          <p className="text-muted mt-1">Visão geral do desempenho de todas as clínicas na semana atual.</p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative w-full sm:w-80">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-subtle" />
            </div>
            <input
              type="text"
              placeholder="Buscar cliente..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-line rounded-lg leading-5 bg-card text-ink placeholder-subtle focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand sm:text-sm transition-shadow"
            />
          </div>
          <button
            onClick={() => setShowNewClient(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft whitespace-nowrap"
          >
            <Plus className="w-4 h-4" /> Novo cliente
          </button>
        </div>
      </div>

      {/* Week selector */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-subtle">Semana:</span>
        <select
          value={selectedWeek}
          onChange={(e) => setSelectedWeek(e.target.value)}
          className="border border-line rounded-lg bg-card text-ink text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand"
        >
          <option value="">Semana atual</option>
          {weekOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        {selectedWeek && (
          <button
            onClick={() => setSelectedWeek('')}
            className="text-xs text-muted hover:text-ink underline"
          >
            Voltar para semana atual
          </button>
        )}
      </div>

      {showNewClient && (
        <NewClientModal onClose={() => setShowNewClient(false)} onCreated={() => load(selectedWeek || undefined)} />
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard 
          title="Faturamento Total" 
          value={formatCurrency(totalRevenue)} 
          icon={<DollarSign className="w-5 h-5 text-brand" />}
        />
        <KPICard 
          title="Investimento (Ad Spend)" 
          value={formatCurrency(totalSpend)} 
          icon={<Activity className="w-5 h-5 text-rose-600" />}
        />
        <KPICard 
          title="ROI Médio" 
          value={`${averageRoi.toFixed(1)}x`} 
          icon={<TrendingUp className="w-5 h-5 text-emerald-600" />}
        />
        <KPICard 
          title="Consultas Agendadas" 
          value={formatNumber(totalBookings)} 
          icon={<Calendar className="w-5 h-5 text-sky-600" />}
        />
      </div>

      <OpsLtvPanel clients={data} />

      <div className="flex flex-wrap items-center gap-2 bg-card border border-line rounded-xl px-4 py-3">
        <span className="text-xs font-semibold text-subtle uppercase tracking-wide mr-1">Filtros</span>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)} className="border border-line rounded-lg bg-card text-ink text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand">
          <option value="all">Todos os status</option>
          <option value="active">Ativos</option>
          <option value="suspended">Suspensos</option>
          <option value="draft">Rascunhos</option>
        </select>
        <select value={healthFilter} onChange={(e) => setHealthFilter(e.target.value as typeof healthFilter)} className="border border-line rounded-lg bg-card text-ink text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand">
          <option value="all">Toda saúde</option>
          <option value="green">Verde</option>
          <option value="yellow">Amarelo</option>
          <option value="red">Vermelho</option>
        </select>
        <select value={planFilter} onChange={(e) => setPlanFilter(e.target.value)} className="border border-line rounded-lg bg-card text-ink text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand">
          <option value="all">Todos os planos</option>
          {plans.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-subtle">{filteredData.length} clientes · Ordenar:</span>
          <select value={sortField} onChange={(e) => setSortField(e.target.value)} className="border border-line rounded-lg bg-card text-ink text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand">
            <option value="activity">Atividade</option>
            <option value="name">Nome</option>
            <option value="tenure">Tempo de casa</option>
            <option value="revenue">Faturamento</option>
            <option value="spend">Investimento</option>
            <option value="roi">ROI</option>
            <option value="bookings">Consultas</option>
            <option value="fee">Fee mensal</option>
            <option value="ltv">LTV</option>
          </select>
          <button onClick={() => setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))} title="Inverter ordem"
            className="px-2.5 py-1.5 border border-line rounded-lg text-sm text-muted hover:bg-elevated">
            {sortDir === 'asc' ? '↑ Cresc.' : '↓ Decr.'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="animate-pulse space-y-4">
          <div className="h-12 bg-elevated rounded-xl w-full"></div>
          <div className="h-64 bg-card rounded-xl w-full"></div>
        </div>
      ) : (
        <DataTable
          data={filteredData}
          columns={columns}
          keyExtractor={(row) => row.client.id}
        />
      )}
    </div>
  );
}
