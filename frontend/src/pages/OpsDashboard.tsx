import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, DollarSign, Calendar, Activity, ChevronRight, TrendingUp, Plus, Download, Trash2, Loader2, X } from 'lucide-react';
import { fetchOpsDashboard, deleteClient, bulkDeleteClients } from '../lib/opsApi';
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

function exportToCSV(rows: ClientDashboard[], weekLabel: string) {
  const headers = ['Cliente', 'Plano', 'Status', 'Saúde', 'Tempo (meses)', 'Fee Mensal', 'Faturamento', 'Ad Spend', 'ROI', 'Consultas', 'LTV'];
  const csvRows = rows.map(r => [
    r.client.name,
    r.client.plan_name || '',
    r.client.is_draft ? 'Rascunho' : r.client.is_active ? 'Ativo' : 'Suspenso',
    r.health_status,
    r.client.tenure_months ?? '',
    r.client.monthly_fee ?? '',
    r.current_week?.revenue ?? '',
    r.current_week?.ad_spend ?? '',
    r.roi != null ? r.roi.toFixed(2) : '',
    r.current_week?.bookings ?? '',
    (r.client.tenure_months && r.client.monthly_fee) ? (r.client.tenure_months * r.client.monthly_fee).toFixed(2) : '',
  ]);
  const csv = [headers, ...csvRows].map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `atlas-ops-${weekLabel || 'semana-atual'}.csv`;
  a.click();
  URL.revokeObjectURL(url);
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
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState<{ ids: number[]; names: string[] } | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredIds = filteredData.map((d) => d.client.id);
  const allFilteredSelected = filteredIds.length > 0 && filteredIds.every((id) => selectedIds.has(id));

  const toggleSelectAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allFilteredSelected) {
        filteredIds.forEach((id) => next.delete(id));
      } else {
        filteredIds.forEach((id) => next.add(id));
      }
      return next;
    });
  };

  const performDelete = async () => {
    if (!confirmDelete) return;
    setDeleting(true);
    try {
      if (confirmDelete.ids.length === 1) {
        await deleteClient(confirmDelete.ids[0]);
      } else {
        await bulkDeleteClients(confirmDelete.ids);
      }
      setSelectedIds((prev) => {
        const next = new Set(prev);
        confirmDelete.ids.forEach((id) => next.delete(id));
        return next;
      });
      setConfirmDelete(null);
      load(selectedWeek || undefined);
    } catch (err) {
      setErrorMsg((err as { message?: string })?.message || String(err));
    } finally {
      setDeleting(false);
    }
  };

  const columns = [
    {
      header: (
        <input
          type="checkbox"
          aria-label="Selecionar todos"
          checked={allFilteredSelected}
          onChange={toggleSelectAll}
          className="h-4 w-4 rounded border-line text-brand focus:ring-brand cursor-pointer"
        />
      ),
      accessor: (row: ClientDashboard) => (
        <input
          type="checkbox"
          aria-label={`Selecionar ${row.client.name}`}
          checked={selectedIds.has(row.client.id)}
          onChange={() => toggleSelect(row.client.id)}
          className="h-4 w-4 rounded border-line text-brand focus:ring-brand cursor-pointer"
        />
      ),
      className: 'w-10',
    },
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
        <div className="flex items-center justify-end gap-3">
          <Link
            to={`/ops/${row.client.id}`}
            className="inline-flex items-center text-sm font-medium text-brand hover:text-brand-soft"
          >
            Detalhes <ChevronRight className="ml-1 w-4 h-4" />
          </Link>
          <button
            onClick={() => setConfirmDelete({ ids: [row.client.id], names: [row.client.name] })}
            title="Excluir cliente"
            aria-label={`Excluir ${row.client.name}`}
            className="p-1.5 rounded-lg text-subtle hover:text-rose-600 hover:bg-rose-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
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
            onClick={() => exportToCSV(filteredData, selectedWeek)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border border-line bg-card text-muted hover:bg-elevated whitespace-nowrap"
          >
            <Download className="w-4 h-4" /> Exportar CSV
          </button>
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

      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between gap-3 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
          <span className="text-sm font-medium text-rose-700">
            {selectedIds.size} {selectedIds.size === 1 ? 'cliente selecionado' : 'clientes selecionados'}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-3 py-1.5 rounded-lg text-sm font-medium border border-line bg-card text-muted hover:bg-elevated"
            >
              Limpar seleção
            </button>
            <button
              onClick={() => {
                const rows = filteredData.filter((d) => selectedIds.has(d.client.id));
                setConfirmDelete({
                  ids: rows.map((d) => d.client.id),
                  names: rows.map((d) => d.client.name),
                });
              }}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-medium bg-rose-600 text-white hover:bg-rose-700"
            >
              <Trash2 className="w-4 h-4" /> Excluir selecionados
            </button>
          </div>
        </div>
      )}

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

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-card border border-line rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-rose-50">
                  <Trash2 className="w-5 h-5 text-rose-600" />
                </div>
                <h3 className="text-lg font-bold text-ink">
                  Excluir {confirmDelete.ids.length === 1 ? 'cliente' : `${confirmDelete.ids.length} clientes`}?
                </h3>
              </div>
              <button
                onClick={() => !deleting && setConfirmDelete(null)}
                className="text-subtle hover:text-ink"
                aria-label="Fechar"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="mt-4 text-sm text-muted">
              Esta ação é <strong>permanente</strong> e remove também métricas, campanhas, integrações e logs vinculados. Os entregáveis do onboarding são preservados.
            </p>
            {confirmDelete.names.length > 0 && (
              <div className="mt-3 max-h-32 overflow-y-auto rounded-lg bg-elevated border border-line px-3 py-2 text-sm text-ink">
                {confirmDelete.names.map((n, i) => (
                  <div key={i} className="truncate">• {n}</div>
                ))}
              </div>
            )}
            <div className="mt-6 flex items-center justify-end gap-2">
              <button
                onClick={() => setConfirmDelete(null)}
                disabled={deleting}
                className="px-4 py-2 rounded-lg text-sm font-medium border border-line bg-card text-muted hover:bg-elevated disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={performDelete}
                disabled={deleting}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50"
              >
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                {deleting ? 'Excluindo...' : 'Excluir'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
