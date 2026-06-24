import React, { useState } from 'react';
import { X, Zap, Lock } from 'lucide-react';
import { upsertSnapshot } from '../../lib/opsApi';
import type { MetricSnapshot } from '../../types/ops';
import { formatCurrency, formatNumber } from '../../lib/formatters';

interface Props {
  clientId: number;
  weekStart?: string;
  currentWeekData?: MetricSnapshot;
  onClose: () => void;
  onSaved: () => void;
}

function currentMonday(): string {
  const d = new Date();
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  return d.toISOString().slice(0, 10);
}

export function ManualMetricsModal({ clientId, weekStart, currentWeekData, onClose, onSaved }: Props) {
  const [week, setWeek] = useState(weekStart || currentMonday());
  const [revenue, setRevenue] = useState('');
  const [bookings, setBookings] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await upsertSnapshot(clientId, {
        week_start: week,
        source: 'manual',
        revenue: revenue !== '' ? parseFloat(revenue) : undefined,
        bookings: bookings !== '' ? parseInt(bookings, 10) : undefined,
      });
      onSaved();
      onClose();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: { message?: string } } } };
      setError(e?.response?.data?.detail?.message || 'Erro ao salvar dados.');
    } finally {
      setSaving(false);
    }
  };

  const inputCls = 'mt-1 block w-full border border-line rounded-lg py-2.5 px-3 bg-card text-ink text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand';
  const labelCls = 'block text-xs font-semibold text-muted uppercase tracking-wide';

  const autoItems = [
    { label: 'Impressões', value: formatNumber(currentWeekData?.impressions) },
    { label: 'Cliques', value: formatNumber(currentWeekData?.clicks) },
    { label: 'Investimento (Meta/Google)', value: formatCurrency(currentWeekData?.ad_spend) },
    { label: 'Leads / Conversas (WhatsApp)', value: formatNumber(currentWeekData?.conversions) },
    { label: 'Sessões LP (GA4)', value: formatNumber(currentWeekData?.lp_sessions) },
  ];

  const hasAutoData = currentWeekData && (
    currentWeekData.impressions || currentWeekData.clicks ||
    currentWeekData.ad_spend || currentWeekData.conversions || currentWeekData.lp_sessions
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg bg-card rounded-2xl shadow-xl border border-line" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-line">
          <h2 className="text-lg font-bold text-ink">Lançar dados da semana</h2>
          <button onClick={onClose} className="text-subtle hover:text-ink"><X className="w-5 h-5" /></button>
        </div>

        <form onSubmit={submit} className="p-6 space-y-5">
          {error && <div className="p-3 bg-rose-50 text-rose-700 rounded-lg text-sm">{error}</div>}

          {/* Semana */}
          <div>
            <label className={labelCls}>Semana (segunda-feira)</label>
            <input type="date" className={inputCls} value={week}
              onChange={(e) => setWeek(e.target.value)} required />
          </div>

          {/* Auto-synced section */}
          {hasAutoData && (
            <div className="rounded-xl border border-line bg-base overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-line bg-elevated">
                <Zap className="w-3.5 h-3.5 text-brand" />
                <span className="text-xs font-semibold text-muted uppercase tracking-wide">Sincronizado automaticamente</span>
              </div>
              <div className="grid grid-cols-2 gap-px bg-line">
                {autoItems.map((item) => (
                  <div key={item.label} className="bg-base px-4 py-3 flex items-center gap-2">
                    <Lock className="w-3 h-3 text-subtle flex-shrink-0" />
                    <div>
                      <div className="text-[10px] text-subtle">{item.label}</div>
                      <div className="text-sm font-semibold text-ink">{item.value ?? '—'}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Manual section */}
          <div className="rounded-xl border border-brand/30 bg-brand/5 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-brand/20 bg-brand/10">
              <span className="text-xs font-semibold text-brand uppercase tracking-wide">Informar manualmente</span>
              <span className="text-[10px] text-brand/70">— dados que só a equipe tem</span>
            </div>
            <div className="grid grid-cols-2 gap-4 p-4">
              <div>
                <label className={labelCls}>Faturamento (R$)</label>
                <input type="number" step="0.01" min="0" className={inputCls}
                  placeholder="ex: 45000"
                  value={revenue}
                  onChange={(e) => setRevenue(e.target.value)} />
                <p className="mt-1 text-[10px] text-subtle">Receita gerada pela clínica na semana</p>
              </div>
              <div>
                <label className={labelCls}>Agendamentos</label>
                <input type="number" step="1" min="0" className={inputCls}
                  placeholder="ex: 12"
                  value={bookings}
                  onChange={(e) => setBookings(e.target.value)} />
                <p className="mt-1 text-[10px] text-subtle">Consultas efetivamente agendadas</p>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="px-4 py-2 border border-line rounded-lg text-sm font-medium text-muted hover:bg-elevated">
              Cancelar
            </button>
            <button type="submit" disabled={saving}
              className="px-5 py-2 rounded-lg text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft disabled:opacity-50">
              {saving ? 'Salvando...' : 'Salvar dados'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
