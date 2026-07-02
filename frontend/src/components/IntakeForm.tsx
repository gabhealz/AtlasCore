import type { AxiosError } from 'axios';
import { AlertTriangle, ClipboardList, Save, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { api } from '../lib/api';

type IntakeField = {
  key: string;
  label: string;
  hint?: string;
  multiline?: boolean;
  critical?: boolean;
  options?: string[];
  optional?: boolean;
};

type IntakeGroup = {
  key: string;
  title: string;
  fields: IntakeField[];
};

type IntakeFields = Record<string, string | null>;

type Props = {
  onboardingId: string | number;
  /** Chamado apos extrair/salvar, para o container recarregar o status. */
  onChanged?: () => void;
};

function errorMessageFrom(error: unknown, fallback: string): string {
  const axiosError = error as AxiosError<{ detail?: { message?: string } }>;
  return axiosError.response?.data?.detail?.message ?? fallback;
}

export default function IntakeForm({ onboardingId, onChanged }: Props) {
  const [groups, setGroups] = useState<IntakeGroup[]>([]);
  const [fields, setFields] = useState<IntakeFields>({});
  const [extracted, setExtracted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ kind: 'ok' | 'err'; text: string } | null>(
    null,
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [schemaRes, intakeRes] = await Promise.all([
        api.get('/onboardings/intake/schema'),
        api.get(`/onboardings/${onboardingId}/intake`),
      ]);
      setGroups(schemaRes.data.data as IntakeGroup[]);
      setFields((intakeRes.data.data.fields ?? {}) as IntakeFields);
      setExtracted(Boolean(intakeRes.data.data.extracted));
    } catch (error) {
      setMessage({ kind: 'err', text: errorMessageFrom(error, 'Falha ao carregar o formulario.') });
    } finally {
      setLoading(false);
    }
  }, [onboardingId]);

  useEffect(() => {
    void load();
  }, [load]);

  const missingCount = useMemo(() => {
    // Campos opcionais (ex.: CNPJ de pessoa fisica) nao contam como lacuna.
    const allKeys = groups.flatMap((group) =>
      group.fields.filter((field) => !field.optional).map((field) => field.key),
    );
    return allKeys.filter((key) => !(fields[key] ?? '').toString().trim()).length;
  }, [groups, fields]);

  const handleExtract = async () => {
    setIsExtracting(true);
    setMessage(null);
    try {
      const res = await api.post(`/onboardings/${onboardingId}/intake/extract`);
      setFields((res.data.data.fields ?? {}) as IntakeFields);
      setExtracted(Boolean(res.data.data.extracted));
      setMessage({
        kind: 'ok',
        text: 'Extracao concluida. Revise os campos e complete as lacunas destacadas.',
      });
      onChanged?.();
    } catch (error) {
      setMessage({ kind: 'err', text: errorMessageFrom(error, 'Falha ao extrair dos documentos.') });
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);
    try {
      await api.put(`/onboardings/${onboardingId}/intake`, { fields });
      setMessage({
        kind: 'ok',
        text: 'Formulario salvo. O onboarding esta pronto para iniciar a esteira de IA.',
      });
      onChanged?.();
    } catch (error) {
      setMessage({ kind: 'err', text: errorMessageFrom(error, 'Falha ao salvar o formulario.') });
    } finally {
      setIsSaving(false);
    }
  };

  const handleField = (key: string) => (value: string) => {
    setFields((current) => ({ ...current, [key]: value }));
  };

  return (
    <div className="mt-6 rounded-xl bg-white p-6 shadow">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-brand">
            <ClipboardList className="h-4 w-4" />
            Formulario de lacunas (AQF)
          </p>
          <h2 className="mt-2 text-2xl font-bold text-gray-900">
            Dados estruturados do onboarding
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-gray-600">
            Extraia o que der dos documentos e complete o que faltar. A esteira
            de IA so libera depois que este formulario for salvo — e estes dados
            chegam a todos os agentes.
          </p>
        </div>
        <button
          type="button"
          onClick={handleExtract}
          disabled={isExtracting}
          className="inline-flex items-center justify-center rounded-md border border-brand/30 bg-brand/10 px-4 py-2 text-sm font-medium text-brand-soft transition-colors hover:bg-brand/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Sparkles className="mr-2 h-4 w-4" />
          {isExtracting ? 'Extraindo...' : 'Extrair dos documentos'}
        </button>
      </div>

      {!loading && (extracted || missingCount > 0) ? (
        <div className="mt-4 flex flex-wrap items-center gap-3 text-xs">
          <span className="rounded-full bg-gray-100 px-3 py-1 font-semibold uppercase tracking-wide text-gray-600">
            {extracted ? 'Extraido dos documentos' : 'Sem extracao ainda'}
          </span>
          {missingCount > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 font-semibold uppercase tracking-wide text-amber-700">
              <AlertTriangle className="h-3 w-3" />
              {missingCount} lacuna{missingCount === 1 ? '' : 's'}
            </span>
          ) : (
            <span className="rounded-full bg-green-100 px-3 py-1 font-semibold uppercase tracking-wide text-green-700">
              Completo
            </span>
          )}
        </div>
      ) : null}

      {message ? (
        <div
          className={`mt-4 rounded-md px-4 py-3 text-sm ${
            message.kind === 'ok'
              ? 'bg-green-50 text-green-700'
              : 'bg-red-50 text-red-700'
          }`}
        >
          {message.text}
        </div>
      ) : null}

      {loading ? (
        <p className="mt-6 text-sm text-gray-500">Carregando formulario...</p>
      ) : (
        <div className="mt-6 space-y-8">
          {groups.map((group) => (
            <fieldset key={group.key}>
              <legend className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
                {group.title}
              </legend>
              <div className="grid gap-4 md:grid-cols-2">
                {group.fields.map((field) => {
                  const value = (fields[field.key] ?? '').toString();
                  const isEmpty = !value.trim();
                  // Lacuna so para campos NAO opcionais.
                  const showGap = isEmpty && !field.optional;
                  const borderClass = showGap
                    ? 'border-amber-300 bg-amber-50/40'
                    : 'border-gray-300';
                  return (
                    <div
                      key={field.key}
                      className={field.multiline ? 'md:col-span-2' : ''}
                    >
                      <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                        {field.label}
                        {field.critical ? (
                          <span className="rounded bg-brand/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-brand-soft">
                            critico
                          </span>
                        ) : null}
                        {field.optional ? (
                          <span className="text-[10px] font-semibold uppercase text-gray-400">
                            opcional
                          </span>
                        ) : null}
                        {showGap ? (
                          <span className="text-[10px] font-semibold uppercase text-amber-600">
                            lacuna
                          </span>
                        ) : null}
                      </label>
                      {field.options && field.options.length > 0 ? (
                        <select
                          value={value}
                          onChange={(event) => handleField(field.key)(event.target.value)}
                          className={`mt-1 block w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:border-brand focus:ring-brand ${borderClass}`}
                        >
                          <option value="">Selecione...</option>
                          {/* valor extraido que nao esta na lista de opcoes ainda aparece */}
                          {value && !field.options.includes(value) ? (
                            <option value={value}>{value}</option>
                          ) : null}
                          {field.options.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      ) : field.multiline ? (
                        <textarea
                          value={value}
                          onChange={(event) => handleField(field.key)(event.target.value)}
                          rows={2}
                          placeholder={field.hint}
                          className={`mt-1 block w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:border-brand focus:ring-brand ${borderClass}`}
                        />
                      ) : (
                        <input
                          type="text"
                          value={value}
                          onChange={(event) => handleField(field.key)(event.target.value)}
                          placeholder={field.hint}
                          className={`mt-1 block w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:border-brand focus:ring-brand ${borderClass}`}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </fieldset>
          ))}

          <div className="flex flex-wrap items-center justify-end gap-3 border-t border-gray-200 pt-5">
            {message ? (
              <span
                className={`text-sm ${
                  message.kind === 'ok' ? 'text-green-700' : 'text-red-700'
                }`}
              >
                {message.text}
              </span>
            ) : null}
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-brand px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:bg-brand/40 text-onbrand"
            >
              <Save className="mr-2 h-4 w-4" />
              {isSaving ? 'Salvando...' : 'Salvar formulario'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
