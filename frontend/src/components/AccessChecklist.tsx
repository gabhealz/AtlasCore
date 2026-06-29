import { CheckSquare, ExternalLink, ListChecks, Square } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { api } from '../lib/api';

type ChecklistItem = {
  key: string;
  label: string;
  url?: string;
  hint?: string;
};

type Props = {
  onboardingId: string | number;
};

export default function AccessChecklist({ onboardingId }: Props) {
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [state, setState] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [schemaRes, stateRes] = await Promise.all([
        api.get('/onboardings/access-checklist/schema'),
        api.get(`/onboardings/${onboardingId}/access-checklist`),
      ]);
      setItems(schemaRes.data.data as ChecklistItem[]);
      setState((stateRes.data.data.state ?? {}) as Record<string, boolean>);
    } catch {
      // silencioso: o checklist e apoio operacional, nao bloqueia nada.
    } finally {
      setLoading(false);
    }
  }, [onboardingId]);

  useEffect(() => {
    void load();
  }, [load]);

  const doneCount = useMemo(
    () => items.filter((item) => state[item.key]).length,
    [items, state],
  );

  const toggle = (key: string) => {
    setState((current) => ({ ...current, [key]: !current[key] }));
    setSaved(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.put(`/onboardings/${onboardingId}/access-checklist`, { state });
      setSaved(true);
    } catch {
      setSaved(false);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="mt-6 rounded-xl bg-white p-6 shadow">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-brand">
            <ListChecks className="h-4 w-4" />
            Contas & Acessos
          </p>
          <h2 className="mt-2 text-2xl font-bold text-gray-900">
            Checklist de configuracao do cliente
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-gray-600">
            Apoio operacional do time. Nao bloqueia a esteira de IA; serve para
            acompanhar a configuracao de contas e integracoes do cliente.
          </p>
        </div>
        {!loading ? (
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600">
            {doneCount}/{items.length} concluidos
          </span>
        ) : null}
      </div>

      {loading ? (
        <p className="mt-6 text-sm text-gray-500">Carregando checklist...</p>
      ) : (
        <>
          <ul className="mt-6 space-y-2">
            {items.map((item) => {
              const checked = Boolean(state[item.key]);
              return (
                <li key={item.key}>
                  <div className="flex items-start gap-3 rounded-lg border border-gray-200 px-4 py-3">
                    <button
                      type="button"
                      onClick={() => toggle(item.key)}
                      className="mt-0.5 shrink-0 text-brand"
                      aria-pressed={checked}
                    >
                      {checked ? (
                        <CheckSquare className="h-5 w-5" />
                      ) : (
                        <Square className="h-5 w-5 text-gray-400" />
                      )}
                    </button>
                    <div className="min-w-0">
                      <p
                        className={`text-sm font-medium ${
                          checked ? 'text-gray-400 line-through' : 'text-gray-800'
                        }`}
                      >
                        {item.label}
                      </p>
                      {item.hint ? (
                        <p className="text-xs text-gray-500">{item.hint}</p>
                      ) : null}
                      {item.url ? (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex items-center gap-1 text-xs text-brand hover:text-brand-soft"
                        >
                          {item.url}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : null}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>

          <div className="mt-5 flex items-center justify-end gap-3 border-t border-gray-200 pt-5">
            {saved ? (
              <span className="text-sm text-green-600">Salvo.</span>
            ) : null}
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-brand px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:bg-brand/40 text-onbrand"
            >
              {isSaving ? 'Salvando...' : 'Salvar checklist'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
