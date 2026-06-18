import { CheckCircle2, Copy } from 'lucide-react';

export type TrackingSheetRow = {
  name: string;
  css_id: string;
  suggested_event: string;
};

type TrackingSheetProps = {
  rows: TrackingSheetRow[];
  isLoading: boolean;
  errorMessage: string;
  onCopyCsv: () => void;
  copied: boolean;
};

export default function TrackingSheet({
  rows,
  isLoading,
  errorMessage,
  onCopyCsv,
  copied,
}: TrackingSheetProps) {
  return (
    <div className="rounded-xl bg-card p-6 shadow">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-brand">
            Tracking Sheet
          </p>
          <h2 className="mt-2 text-2xl font-bold text-ink">
            IDs CSS e eventos sugeridos
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-muted">
            Use esta tabela final para copiar o mapeamento operacional dos botoes
            CTA direto para a configuracao do Google Tag Manager.
          </p>
        </div>

        <button
          type="button"
          onClick={onCopyCsv}
          disabled={isLoading || rows.length === 0 || !!errorMessage}
          className="inline-flex items-center justify-center rounded-md border border-transparent bg-brand px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:bg-brand/40"
        >
          {copied ? (
            <CheckCircle2 className="mr-2 h-4 w-4" />
          ) : (
            <Copy className="mr-2 h-4 w-4" />
          )}
          {copied ? 'CSV copiado' : 'Copiar CSV'}
        </button>
      </div>

      {isLoading ? (
        <div className="mt-6 rounded-lg border border-brand/20 bg-brand/10 px-4 py-5 text-sm text-brand">
          Carregando Tracking Sheet final...
        </div>
      ) : null}

      {!isLoading && errorMessage ? (
        <div className="mt-6 rounded-lg border border-dashed border-amber-300 bg-amber-50 px-4 py-5 text-sm text-amber-800">
          {errorMessage}
        </div>
      ) : null}

      {!isLoading && !errorMessage && rows.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed border-line bg-elevated px-4 py-5 text-sm text-muted">
          Nenhum dado de tracking foi encontrado para este onboarding.
        </div>
      ) : null}

      {!isLoading && !errorMessage && rows.length > 0 ? (
        <div className="mt-6 overflow-x-auto rounded-lg border border-line bg-card">
          <table className="min-w-full divide-y divide-line text-sm">
            <thead className="bg-elevated text-left text-xs font-semibold uppercase tracking-wide text-subtle">
              <tr>
                <th className="px-4 py-3">Nome do botao</th>
                <th className="px-4 py-3">ID CSS</th>
                <th className="px-4 py-3">Evento sugerido</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line text-ink">
              {rows.map((row) => (
                <tr key={row.css_id}>
                  <td className="px-4 py-3 font-medium text-ink">{row.name}</td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-brand/10 px-2 py-1 font-mono text-xs text-brand-soft">
                      {row.css_id}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-800">
                      {row.suggested_event}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
