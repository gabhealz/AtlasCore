import React, { useState } from 'react';
import { X } from 'lucide-react';
import { upsertSnapshot, type ManualSnapshotInput } from '../../lib/opsApi';

interface Props {
  clientId: number;
  onClose: () => void;
  onSaved: () => void;
}

function currentMonday(): string {
  const d = new Date();
  const day = (d.getDay() + 6) % 7; // 0 = segunda
  d.setDate(d.getDate() - day);
  return d.toISOString().slice(0, 10);
}

export function ManualMetricsModal({ clientId, onClose, onSaved }: Props) {
  const [form, setForm] = useState<ManualSnapshotInput>({ week_start: currentMonday() });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setNum = (k: keyof ManualSnapshotInput, v: string) =>
    setForm((f) => ({ ...f, [k]: v === '' ? undefined : parseFloat(v) }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await upsertSnapshot(clientId, form);
      onSaved();
      onClose();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: { message?: string } } } };
      setError(e?.response?.data?.detail?.message || 'Erro ao salvar dados.');
    } finally {
      setSaving(false);
    }
  };

  const field = 'mt-1 block w-full border border-line rounded-md py-2 px-3 bg-card text-ink text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand';
  const label = 'block text-xs font-medium text-muted';

  const fields: { key: keyof ManualSnapshotInput; label: string; step?: string }[] = [
    { key: 'revenue', label: 'Faturamento (R$)', step: '0.01' },
    { key: 'bookings', label: 'Agendamentos' },
    { key: 'conversions', label: 'Leads / Conversas (WhatsApp)' },
    { key: 'ad_spend', label: 'Investimento (R$)', step: '0.01' },
    { key: 'impressions', label: 'Impressões' },
    { key: 'clicks', label: 'Cliques' },
    { key: 'lp_sessions', label: 'Sessões LP (GA4)' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg bg-card rounded-2xl shadow-xl border border-line" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-line">
          <h2 className="text-lg font-bold text-ink">Lançar dados da semana</h2>
          <button onClick={onClose} className="text-subtle hover:text-ink"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          {error && <div className="p-3 bg-rose-50 text-rose-700 rounded text-sm">{error}</div>}
          <p className="text-xs text-subtle">Preencha o que tiver — o que ficar em branco não é alterado. Ideal para dados que a secretária repassa (faturamento, agendamentos).</p>
          <div>
            <label className={label}>Semana (segunda-feira)</label>
            <input type="date" className={field} value={form.week_start} onChange={(e) => setForm((f) => ({ ...f, week_start: e.target.value }))} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            {fields.map((f) => (
              <div key={f.key}>
                <label className={label}>{f.label}</label>
                <input type="number" step={f.step || '1'} className={field}
                  value={(form[f.key] as number | undefined) ?? ''}
                  onChange={(e) => setNum(f.key, e.target.value)} />
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-line rounded-md text-sm font-medium text-muted hover:bg-elevated">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-md text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft disabled:opacity-50">
              {saving ? 'Salvando...' : 'Salvar dados'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
