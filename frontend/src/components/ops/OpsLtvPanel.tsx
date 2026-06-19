import { useMemo, useState } from 'react';
import type { ClientDashboard } from '../../types/ops';

interface OpsLtvPanelProps {
  clients: ClientDashboard[];
}

// ─── helpers ────────────────────────────────────────────────────────────────

function parseDate(str: string | undefined): Date | null {
  if (!str) return null;
  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
}

/** Difference in whole months between two dates (start → end, >=0). */
function diffMonths(start: Date, end: Date): number {
  const years = end.getFullYear() - start.getFullYear();
  const months = end.getMonth() - start.getMonth();
  let total = years * 12 + months;
  // Subtract 1 if end day < start day (haven't completed that month yet)
  if (end.getDate() < start.getDate()) total -= 1;
  return Math.max(0, total);
}

function formatBRL(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
}

function monthLabel(date: Date): string {
  const SHORT_MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  return `${SHORT_MONTHS[date.getMonth()]}/${String(date.getFullYear()).slice(2)}`;
}

/** Sort key for cohort month (YYYY-MM) */
function cohortKey(date: Date): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  return `${yyyy}-${mm}`;
}

// ─── retention color coding ──────────────────────────────────────────────────

function retentionClass(pct: number): string {
  if (pct >= 80) return 'bg-teal-800 text-white';
  if (pct >= 60) return 'bg-teal-600 text-white';
  if (pct >= 40) return 'bg-teal-400 text-white';
  if (pct >= 20) return 'bg-teal-200 text-teal-900';
  return 'bg-rose-100 text-rose-800';
}

// ─── types ───────────────────────────────────────────────────────────────────

interface CohortRow {
  key: string;
  label: string;
  size: number;
  cohortStart: Date;
  retention: (number | null)[]; // index 0 = M1, ..., 11 = M12; null = future
}

// ─── component ───────────────────────────────────────────────────────────────

export function OpsLtvPanel({ clients }: OpsLtvPanelProps) {
  const [activeTab, setActiveTab] = useState<'retencao' | 'churn'>('retencao');
  const today = useMemo(() => new Date(), []);

  // ── LTV KPI metrics ──────────────────────────────────────────────────────

  const ltvMetrics = useMemo(() => {
    const activeNonDraft = clients.filter(
      (c) => c.client.is_active && !c.client.is_draft
    );

    // Ticket médio e mediana
    const fees = activeNonDraft
      .map((c) => c.client.monthly_fee ?? 0)
      .filter((f) => f > 0)
      .sort((a, b) => a - b);

    const ticketMedio = fees.length > 0 ? fees.reduce((a, b) => a + b, 0) / fees.length : 0;
    const mediana =
      fees.length === 0
        ? 0
        : fees.length % 2 === 0
        ? (fees[fees.length / 2 - 1] + fees[fees.length / 2]) / 2
        : fees[Math.floor(fees.length / 2)];

    // Churn rate mensal
    const twelveMonthsAgo = new Date(today);
    twelveMonthsAgo.setFullYear(today.getFullYear() - 1);

    const churnedClients = clients.filter((c) => {
      if (c.client.is_active) return false;
      const endDate = parseDate(c.client.contract_end_date);
      if (endDate) {
        return endDate >= twelveMonthsAgo && endDate <= today;
      }
      // Fallback to created_at
      const createdAt = parseDate(c.client.created_at);
      return createdAt ? createdAt >= twelveMonthsAgo && createdAt <= today : false;
    });

    const avgActiveCount = activeNonDraft.length || 1; // avoid divide by zero
    const churnRateMonthly = churnedClients.length > 0
      ? (churnedClients.length / 12) / avgActiveCount
      : 0;

    // Vida média e LTV estimado
    const vidaMedia = churnRateMonthly > 0 ? 1 / churnRateMonthly : Infinity;
    const ltvEstimado = isFinite(vidaMedia) ? ticketMedio * vidaMedia : Infinity;

    return {
      ticketMedio,
      mediana,
      churnRateMonthly,
      churnedCount: churnedClients.length,
      vidaMedia,
      ltvEstimado,
    };
  }, [clients, today]);

  // ── Cohort retention data ────────────────────────────────────────────────

  const cohortRows = useMemo((): CohortRow[] => {
    // Only clients with a contract_start_date
    const withStart = clients.filter((c) => !!c.client.contract_start_date);
    if (withStart.length < 3) return [];

    // Group by cohort month
    const groups: Map<string, { start: Date; clients: ClientDashboard[] }> = new Map();

    for (const c of withStart) {
      const startDate = parseDate(c.client.contract_start_date);
      if (!startDate) continue;
      const key = cohortKey(startDate);
      if (!groups.has(key)) {
        groups.set(key, { start: new Date(startDate.getFullYear(), startDate.getMonth(), 1), clients: [] });
      }
      groups.get(key)!.clients.push(c);
    }

    // Sort cohorts chronologically
    const sorted = Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));

    return sorted.map(([key, { start, clients: cohortClients }]) => {
      const size = cohortClients.length;
      const monthsExisted = diffMonths(start, today);

      const retention: (number | null)[] = [];

      for (let m = 1; m <= 12; m++) {
        if (m > monthsExisted) {
          // Cohort hasn't reached this month yet
          retention.push(null);
        } else {
          const survivors = cohortClients.filter((c) => {
            const clientStart = parseDate(c.client.contract_start_date);
            if (!clientStart) return false;

            let monthsActive: number;
            if (c.client.is_active) {
              monthsActive = diffMonths(clientStart, today);
            } else {
              const endDate = parseDate(c.client.contract_end_date);
              if (!endDate) return false; // unknown — skip
              monthsActive = diffMonths(clientStart, endDate);
            }
            return monthsActive >= m;
          }).length;

          retention.push(Math.round((survivors / size) * 100));
        }
      }

      return {
        key,
        label: monthLabel(start),
        size,
        cohortStart: start,
        retention,
      };
    });
  }, [clients, today]);

  const hasEnoughData = cohortRows.length > 0;

  // ── render ───────────────────────────────────────────────────────────────

  const { ticketMedio, mediana, churnRateMonthly, churnedCount, vidaMedia, ltvEstimado } = ltvMetrics;

  const churnLabel =
    churnedCount === 0
      ? '0,0% (sem churns)'
      : `${(churnRateMonthly * 100).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

  const vidaMediaLabel = isFinite(vidaMedia)
    ? `${vidaMedia.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} meses`
    : '∞';

  const ltvLabel = isFinite(ltvEstimado) ? formatBRL(ltvEstimado) : '∞';

  return (
    <div className="space-y-4">
      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Ticket médio */}
        <div className="bg-card border border-line rounded-xl p-4 space-y-1">
          <p className="text-xs font-semibold text-subtle uppercase tracking-wide">Ticket médio (ativos)</p>
          <p className="text-2xl font-bold text-ink">{formatBRL(ticketMedio)}</p>
          <p className="text-xs text-muted">Mediana: {formatBRL(mediana)}</p>
        </div>

        {/* Churn rate */}
        <div className="bg-card border border-line rounded-xl p-4 space-y-1">
          <p className="text-xs font-semibold text-subtle uppercase tracking-wide">Churn rate mensal</p>
          <p className="text-2xl font-bold text-ink">{churnLabel}</p>
          <p className="text-xs text-muted">{churnedCount} churns nos últimos 12 meses</p>
        </div>

        {/* Vida média */}
        <div className="bg-card border border-line rounded-xl p-4 space-y-1">
          <p className="text-xs font-semibold text-subtle uppercase tracking-wide">Vida média do cliente</p>
          <p className="text-2xl font-bold text-ink">{vidaMediaLabel}</p>
          <p className="text-xs text-muted">1 / churn rate mensal</p>
        </div>

        {/* LTV estimado */}
        <div className="bg-card border border-line rounded-xl p-4 space-y-1">
          <p className="text-xs font-semibold text-subtle uppercase tracking-wide">LTV estimado</p>
          <p className="text-2xl font-bold text-ink">{ltvLabel}</p>
          <p className="text-xs text-muted">ticket médio × vida média</p>
        </div>
      </div>

      {/* Cohort panel */}
      <div className="bg-card border border-line rounded-xl overflow-hidden">
        {/* Tab bar */}
        <div className="flex border-b border-line">
          <button
            onClick={() => setActiveTab('retencao')}
            className={`px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'retencao'
                ? 'text-brand border-b-2 border-brand -mb-px'
                : 'text-muted hover:text-ink'
            }`}
          >
            Retenção mensal
          </button>
          <button
            onClick={() => setActiveTab('churn')}
            className={`px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'churn'
                ? 'text-brand border-b-2 border-brand -mb-px'
                : 'text-muted hover:text-ink'
            }`}
          >
            Churn acumulado
          </button>
        </div>

        <div className="p-4">
          {activeTab === 'churn' ? (
            <p className="text-sm text-muted text-center py-8">Em breve.</p>
          ) : !hasEnoughData ? (
            <p className="text-sm text-muted text-center py-8">
              São necessários pelo menos 3 clientes com data de início de contrato para exibir a tabela de retenção.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className="text-left py-2 pr-3 text-xs font-semibold text-subtle uppercase tracking-wide whitespace-nowrap">
                      Coorte
                    </th>
                    <th className="text-center py-2 px-2 text-xs font-semibold text-subtle uppercase tracking-wide">
                      n
                    </th>
                    {Array.from({ length: 12 }, (_, i) => (
                      <th
                        key={i}
                        className="text-center py-2 px-1 text-xs font-semibold text-subtle uppercase tracking-wide min-w-[42px]"
                      >
                        M{i + 1}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cohortRows.map((row) => (
                    <tr key={row.key} className="border-t border-line">
                      <td className="py-2 pr-3 font-medium text-ink whitespace-nowrap">{row.label}</td>
                      <td className="py-2 px-2 text-center text-muted">{row.size}</td>
                      {row.retention.map((pct, i) => (
                        <td key={i} className="py-1 px-1 text-center">
                          {pct === null ? (
                            <span className="block w-full text-center text-muted">—</span>
                          ) : (
                            <span
                              className={`block rounded text-xs font-semibold py-1 px-0.5 ${retentionClass(pct)}`}
                            >
                              {pct}%
                            </span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
