import React, { useState } from 'react';
import { X } from 'lucide-react';
import { createClient, type ClientCreateInput } from '../../lib/opsApi';

interface Props {
  onClose: () => void;
  onCreated: () => void;
}

const PLANS = ['AQF', 'AQF + Secretariado', 'Pareto', 'Pareto + Secretariado', 'Secretariado', 'Carol', 'Mentoria', 'Personalizado'];

export function NewClientModal({ onClose, onCreated }: Props) {
  const [form, setForm] = useState<ClientCreateInput>({ name: '', monthly_fee: 0 });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof ClientCreateInput, v: string | number) =>
    setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.monthly_fee) {
      setError('Nome e fee mensal são obrigatórios.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createClient(form);
      onCreated();
      onClose();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: { message?: string } } } };
      setError(e?.response?.data?.detail?.message || 'Erro ao criar cliente.');
    } finally {
      setSaving(false);
    }
  };

  const field = 'mt-1 block w-full border border-line rounded-md py-2 px-3 bg-card text-ink text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand';
  const label = 'block text-xs font-medium text-muted';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg bg-card rounded-2xl shadow-xl border border-line max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-line">
          <h2 className="text-lg font-bold text-ink">Novo cliente</h2>
          <button onClick={onClose} className="text-subtle hover:text-ink"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          {error && <div className="p-3 bg-rose-50 text-rose-700 rounded text-sm">{error}</div>}
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className={label}>Nome *</label>
              <input className={field} value={form.name} onChange={(e) => set('name', e.target.value)} required />
            </div>
            <div>
              <label className={label}>Plano</label>
              <select className={field} value={form.plan_name || ''} onChange={(e) => set('plan_name', e.target.value)}>
                <option value="">—</option>
                {PLANS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className={label}>Fee mensal (R$) *</label>
              <input type="number" step="0.01" className={field} value={form.monthly_fee || ''} onChange={(e) => set('monthly_fee', parseFloat(e.target.value) || 0)} required />
            </div>
            <div>
              <label className={label}>Especialidade</label>
              <input className={field} value={form.specialty || ''} onChange={(e) => set('specialty', e.target.value)} />
            </div>
            <div>
              <label className={label}>Documento (CPF/CNPJ)</label>
              <input className={field} value={form.document || ''} onChange={(e) => set('document', e.target.value)} />
            </div>
            <div>
              <label className={label}>Cidade</label>
              <input className={field} value={form.city || ''} onChange={(e) => set('city', e.target.value)} />
            </div>
            <div>
              <label className={label}>UF</label>
              <input maxLength={2} className={field} value={form.state || ''} onChange={(e) => set('state', e.target.value.toUpperCase())} />
            </div>
            <div>
              <label className={label}>Início do contrato</label>
              <input type="date" className={field} value={form.contract_start_date || ''} onChange={(e) => set('contract_start_date', e.target.value)} />
            </div>
            <div>
              <label className={label}>Fim do contrato</label>
              <input type="date" className={field} value={form.contract_end_date || ''} onChange={(e) => set('contract_end_date', e.target.value)} />
            </div>
            <div>
              <label className={label}>Telefone</label>
              <input className={field} value={form.phone || ''} onChange={(e) => set('phone', e.target.value)} />
            </div>
            <div>
              <label className={label}>E-mail</label>
              <input className={field} value={form.email || ''} onChange={(e) => set('email', e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-line rounded-md text-sm font-medium text-muted hover:bg-elevated">Cancelar</button>
            <button type="submit" disabled={saving} className="px-4 py-2 rounded-md text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft disabled:opacity-50">
              {saving ? 'Salvando...' : 'Criar cliente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
