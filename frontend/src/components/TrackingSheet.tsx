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
    <div className="rounded-xl bg-white p-6 shadow">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-violet-700">
            Tracking Sheet
          </p>
          <h2 className="mt-2 text-2xl font-bold text-gray-900">
            IDs CSS e eventos sugeridos
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-gray-600">
            Use esta tabela final para copiar o mapeamento operacional dos botoes
            CTA direto para a configuracao do Google Tag Manager.
          </p>
        </div>

        <button
          type="button"
          onClick={onCopyCsv}
          disabled={isLoading || rows.length === 0 || !!errorMessage}
          className="inline-flex items-center justify-center rounded-md border border-transparent bg-violet-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-violet-300"
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
        <div className="mt-6 rounded-lg border border-violet-100 bg-violet-50 px-4 py-5 text-sm text-violet-700">
          Carregando Tracking Sheet final...
        </div>
      ) : null}

      {!isLoading && errorMessage ? (
        <div className="mt-6 rounded-lg border border-dashed border-amber-300 bg-amber-50 px-4 py-5 text-sm text-amber-800">
          {errorMessage}
        </div>
      ) : null}

      {!isLoading && !errorMessage && rows.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-5 text-sm text-gray-600">
          Nenhum dado de tracking foi encontrado para este onboarding.
        </div>
      ) : null}

      {!isLoading && !errorMessage && rows.length > 0 ? (
        <div className="mt-6 overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-3">Nome do botao</th>
                <th className="px-4 py-3">ID CSS</th>
                <th className="px-4 py-3">Evento sugerido</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-gray-700">
              {rows.map((row) => (
                <tr key={row.css_id}>
                  <td className="px-4 py-3 font-medium text-gray-900">{row.name}</td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-violet-50 px-2 py-1 font-mono text-xs text-violet-800">
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
