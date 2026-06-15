import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, DollarSign, Calendar, Activity, ChevronRight, TrendingUp } from 'lucide-react';
import { fetchOpsDashboard } from '../lib/opsApi';
import type { ClientDashboard } from '../types/ops';
import { formatCurrency, formatNumber } from '../lib/formatters';
import { StatusBadge } from '../components/ui/StatusBadge';
import { DataTable } from '../components/ui/DataTable';
import { KPICard } from '../components/ui/KPICard';

export function OpsDashboard() {
  const [data, setData] = useState<ClientDashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetchOpsDashboard()
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

  if (errorMsg) {
    return (
      <div className="p-8 text-rose-600">
        <h2 className="text-xl font-bold">Erro de Renderização/API</h2>
        <pre className="mt-4 p-4 bg-rose-50 rounded-lg whitespace-pre-wrap">{errorMsg}</pre>
      </div>
    );
  }

  const filteredData = (data || []).filter((item) => {
    try {
      return item?.client?.name?.toLowerCase().includes(searchQuery.toLowerCase());
    } catch (e) {
      console.error("Filter error on item:", item, e);
      return false;
    }
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
          <div className="font-medium text-ink">{row.client.name}</div>
          <div className="text-xs text-subtle">
            {row.client.specialty || row.client.plan_name || '—'}
          </div>
        </div>
      ),
    },
    {
      header: 'Status',
      accessor: (row: ClientDashboard) => (
        <StatusBadge status={row.health_status as any} />
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

        <div className="relative w-full sm:w-96">
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
      </div>

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
