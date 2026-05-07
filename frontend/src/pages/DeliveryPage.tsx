import type { AxiosError } from 'axios';
import { ArrowLeft, CheckCircle2, Code2, Copy, FileText } from 'lucide-react';
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import CodeViewer from '../components/CodeViewer';
import TrackingSheet, { type TrackingSheetRow } from '../components/TrackingSheet';
import { api } from '../lib/api';

const LANDING_PAGE_FEATURES_ENABLED = false;

type DeliverableDocument = {
  id: number;
  onboarding_id: number;
  step_name: string;
  agent_name: string;
  document_kind: string;
  title: string;
  content: string;
  content_format: string;
  review_status: string;
  created_at: string;
  updated_at: string;
};

type DeliverableListResponse = {
  data: DeliverableDocument[];
};

type DeliverableResponse = {
  data: DeliverableDocument;
};

type TrackingSheetResponse = {
  data: TrackingSheetRow[];
};

type OnboardingSummary = {
  id: number;
  status: string;
};

type OnboardingListResponse = {
  data: OnboardingSummary[];
};

type ApiErrorResponse = {
  detail?:
    | {
        error_code?: string;
        message?: string;
        current_status?: string;
      }
    | Array<{
        loc?: string[];
        msg?: string;
      }>;
};

function getApiErrorMessage(
  error: AxiosError<ApiErrorResponse>,
  fallbackMessage: string,
) {
  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail[0]?.msg ?? fallbackMessage;
  }

  return detail?.message ?? fallbackMessage;
}

function getOnboardingStatusLabel(status: string) {
  switch (status) {
    case 'PENDING':
      return 'Pendente';
    case 'RUNNING':
      return 'Em execucao';
    case 'AWAITING_REVIEW':
      return 'Aguardando revisao';
    case 'APPROVED':
      return 'Aprovado';
    case 'REJECTED':
      return 'Recusado';
    case 'FAILED':
      return 'Falhou';
    default:
      return status;
  }
}

function getDeliverableLabel(documentKind: string) {
  switch (documentKind) {
    case 'research_report':
      return 'Benchmarking';
    case 'strategy_plan':
      return 'Estrategia';
    case 'copy_deck':
      return 'Copy da landing';
    case 'secretary_script':
      return 'Script da secretaria';
    default:
      return documentKind;
  }
}

function formatDateTimeLabel(value: string) {
  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(parsedDate);
}

function escapeCsvValue(value: string) {
  return `"${value.replaceAll('"', '""')}"`;
}

function buildTrackingSheetCsv(rows: TrackingSheetRow[]) {
  const header = ['Nome do Botao', 'ID CSS', 'Evento Sugerido'];
  const lines = rows.map((row) =>
    [
      escapeCsvValue(row.name),
      escapeCsvValue(row.css_id),
      escapeCsvValue(row.suggested_event),
    ].join(','),
  );

  return [header.map(escapeCsvValue).join(','), ...lines].join('\n');
}

export default function DeliveryPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const onboardingId = Number(id);
  const hasValidOnboardingId = Number.isInteger(onboardingId) && onboardingId > 0;
  const onboardingStatusFromState =
    typeof location.state?.onboardingStatus === 'string'
      ? location.state.onboardingStatus
      : null;
  const [pipelineStatus, setPipelineStatus] = useState<string | null>(
    hasValidOnboardingId ? onboardingStatusFromState : null,
  );
  const [isLoadingPipelineStatus, setIsLoadingPipelineStatus] = useState(
    hasValidOnboardingId && onboardingStatusFromState === null,
  );
  const [deliverables, setDeliverables] = useState<DeliverableDocument[]>([]);
  const [landingPageHtml, setLandingPageHtml] = useState<DeliverableDocument | null>(null);
  const [trackingSheetRows, setTrackingSheetRows] = useState<TrackingSheetRow[]>([]);
  const [isLoadingDeliverables, setIsLoadingDeliverables] = useState(false);
  const [isLoadingLandingPageHtml, setIsLoadingLandingPageHtml] = useState(false);
  const [isLoadingTrackingSheet, setIsLoadingTrackingSheet] = useState(false);
  const [statusErrorMessage, setStatusErrorMessage] = useState('');
  const [deliverablesErrorMessage, setDeliverablesErrorMessage] = useState('');
  const [landingPageHtmlErrorMessage, setLandingPageHtmlErrorMessage] = useState('');
  const [trackingSheetErrorMessage, setTrackingSheetErrorMessage] = useState('');
  const [copySuccessMessage, setCopySuccessMessage] = useState('');
  const [copyErrorMessage, setCopyErrorMessage] = useState('');
  const [copiedTargetId, setCopiedTargetId] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    if (!hasValidOnboardingId) {
      return () => {
        isCancelled = true;
      };
    }

    async function loadOnboardingStatus() {
      setIsLoadingPipelineStatus(true);
      setPipelineStatus(onboardingStatusFromState);
      setStatusErrorMessage('');

      try {
        const response = await api.get<OnboardingListResponse>('/onboardings');
        if (isCancelled) {
          return;
        }

        const onboarding = response.data.data.find((item) => item.id === onboardingId);
        if (!onboarding) {
          setPipelineStatus(null);
          setStatusErrorMessage(
            'Nao foi possivel encontrar este onboarding para carregar os entregaveis.',
          );
          return;
        }

        setPipelineStatus(onboarding.status);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const axiosError = error as AxiosError<ApiErrorResponse>;
        setPipelineStatus(null);
        setStatusErrorMessage(
          getApiErrorMessage(
            axiosError,
            'Nao foi possivel carregar o status atual deste onboarding.',
          ),
        );
      } finally {
        if (!isCancelled) {
          setIsLoadingPipelineStatus(false);
        }
      }
    }

    void loadOnboardingStatus();

    return () => {
      isCancelled = true;
    };
  }, [hasValidOnboardingId, onboardingId, onboardingStatusFromState]);

  useEffect(() => {
    let isCancelled = false;

    if (!hasValidOnboardingId || pipelineStatus !== 'APPROVED') {
      return () => {
        isCancelled = true;
      };
    }

    async function loadDeliverables() {
      setIsLoadingDeliverables(true);
      setDeliverablesErrorMessage('');

      try {
        const response = await api.get<DeliverableListResponse>(
          `/onboardings/${onboardingId}/deliverables`,
        );
        if (isCancelled) {
          return;
        }

        setDeliverables(response.data.data);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const axiosError = error as AxiosError<ApiErrorResponse>;
        setDeliverables([]);
        setDeliverablesErrorMessage(
          getApiErrorMessage(
            axiosError,
            'Nao foi possivel carregar os entregaveis finais de texto.',
          ),
        );
      } finally {
        if (!isCancelled) {
          setIsLoadingDeliverables(false);
        }
      }
    }

    void loadDeliverables();

    return () => {
      isCancelled = true;
    };
  }, [hasValidOnboardingId, onboardingId, pipelineStatus]);

  useEffect(() => {
    let isCancelled = false;

    if (
      !LANDING_PAGE_FEATURES_ENABLED ||
      !hasValidOnboardingId ||
      pipelineStatus !== 'APPROVED'
    ) {
      return () => {
        isCancelled = true;
      };
    }

    async function loadTrackingSheet() {
      setIsLoadingTrackingSheet(true);
      setTrackingSheetErrorMessage('');

      try {
        const response = await api.get<TrackingSheetResponse>(
          `/tracking/${onboardingId}/sheet`,
        );
        if (isCancelled) {
          return;
        }

        setTrackingSheetRows(response.data.data);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const axiosError = error as AxiosError<ApiErrorResponse>;
        setTrackingSheetRows([]);
        setTrackingSheetErrorMessage(
          getApiErrorMessage(
            axiosError,
            'Nao foi possivel carregar a Tracking Sheet final.',
          ),
        );
      } finally {
        if (!isCancelled) {
          setIsLoadingTrackingSheet(false);
        }
      }
    }

    void loadTrackingSheet();

    return () => {
      isCancelled = true;
    };
  }, [hasValidOnboardingId, onboardingId, pipelineStatus]);

  useEffect(() => {
    let isCancelled = false;

    if (
      !LANDING_PAGE_FEATURES_ENABLED ||
      !hasValidOnboardingId ||
      pipelineStatus !== 'APPROVED'
    ) {
      return () => {
        isCancelled = true;
      };
    }

    async function loadLandingPageHtml() {
      setIsLoadingLandingPageHtml(true);
      setLandingPageHtmlErrorMessage('');

      try {
        const response = await api.get<DeliverableResponse>(
          `/onboardings/${onboardingId}/landing-page-html`,
        );
        if (isCancelled) {
          return;
        }

        setLandingPageHtml(response.data.data);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const axiosError = error as AxiosError<ApiErrorResponse>;
        setLandingPageHtml(null);
        setLandingPageHtmlErrorMessage(
          getApiErrorMessage(
            axiosError,
            'Nao foi possivel carregar o HTML final da landing page.',
          ),
        );
      } finally {
        if (!isCancelled) {
          setIsLoadingLandingPageHtml(false);
        }
      }
    }

    void loadLandingPageHtml();

    return () => {
      isCancelled = true;
    };
  }, [hasValidOnboardingId, onboardingId, pipelineStatus]);

  const handleCopy = async ({
    content,
    successMessage,
    targetId,
  }: {
    content: string;
    successMessage: string;
    targetId: string;
  }) => {
    setCopySuccessMessage('');
    setCopyErrorMessage('');

    if (
      typeof navigator === 'undefined' ||
      !navigator.clipboard ||
      typeof navigator.clipboard.writeText !== 'function'
    ) {
      setCopiedTargetId(null);
      setCopyErrorMessage(
        'A area de transferencia nao esta disponivel neste navegador.',
      );
      return;
    }

    try {
      await navigator.clipboard.writeText(content);
      setCopiedTargetId(targetId);
      setCopySuccessMessage(successMessage);
    } catch {
      setCopiedTargetId(null);
      setCopyErrorMessage(
        'Nao foi possivel copiar este conteudo.',
      );
    }
  };

  const resolvedStatusLabel = pipelineStatus
    ? getOnboardingStatusLabel(pipelineStatus)
    : 'Status indisponivel';

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() =>
              navigate(`/onboarding/${onboardingId}`, {
                state: { onboardingStatus: pipelineStatus },
              })
            }
            className="inline-flex items-center text-blue-600 hover:text-blue-800"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Voltar para o onboarding
          </button>

          <button
            onClick={() => navigate('/dashboard')}
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Dashboard
          </button>
        </div>

        <div className="mt-6 rounded-xl border border-emerald-200 bg-white p-6 shadow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
                Entregaveis finais
              </p>
              <h1 className="mt-2 text-3xl font-bold text-gray-900">
                Benchmarking final do onboarding #{id}
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-gray-600">
                Esta tela concentra o Benchmarking aprovado para leitura rapida,
                revisao final e copy-paste operacional.
              </p>
            </div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-800">
              {resolvedStatusLabel}
            </span>
          </div>
        </div>

        {!hasValidOnboardingId ? (
          <div className="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
            ID de onboarding invalido para carregar os entregaveis finais.
          </div>
        ) : null}

        {statusErrorMessage ? (
          <div className="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
            {statusErrorMessage}
          </div>
        ) : null}

        {copySuccessMessage ? (
          <div className="mt-6 rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
            {copySuccessMessage}
          </div>
        ) : null}

        {copyErrorMessage ? (
          <div className="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
            {copyErrorMessage}
          </div>
        ) : null}

        {hasValidOnboardingId && isLoadingPipelineStatus ? (
          <div className="mt-6 rounded-lg bg-white px-4 py-5 text-sm text-gray-600 shadow">
            Carregando status do onboarding para liberar os entregaveis...
          </div>
        ) : null}

        {hasValidOnboardingId &&
        !isLoadingPipelineStatus &&
        pipelineStatus !== null &&
        pipelineStatus !== 'APPROVED' ? (
          <div className="mt-6 rounded-xl border border-dashed border-amber-300 bg-amber-50 p-6 text-sm text-amber-800 shadow">
            O Benchmarking final so fica disponivel quando o onboarding chega ao estado `APPROVED`. No
            momento, este projeto esta em ` {resolvedStatusLabel} `.
          </div>
        ) : null}

        {hasValidOnboardingId &&
        !isLoadingPipelineStatus &&
        pipelineStatus === 'APPROVED' &&
        !statusErrorMessage ? (
          <div className="mt-6 grid gap-5">
            {LANDING_PAGE_FEATURES_ENABLED ? (
              <>
            <div className="rounded-xl bg-white p-6 shadow">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-indigo-700">
                    Codigo da landing page
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-gray-900">
                    HTML final aprovado
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm text-gray-600">
                    Revise o codigo final com syntax highlighting antes de copiar
                    o HTML completo para o Elementor.
                  </p>
                </div>

                {landingPageHtml ? (
                  <button
                    type="button"
                    onClick={() =>
                      void handleCopy({
                        content: landingPageHtml.content,
                        successMessage: 'Codigo HTML copiado com sucesso.',
                        targetId: 'landing-page-html',
                      })
                    }
                    className="inline-flex items-center justify-center rounded-md border border-transparent bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-slate-800"
                  >
                    {copiedTargetId === 'landing-page-html' ? (
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                    ) : (
                      <Copy className="mr-2 h-4 w-4" />
                    )}
                    {copiedTargetId === 'landing-page-html'
                      ? 'Codigo copiado'
                      : 'Copiar codigo HTML'}
                  </button>
                ) : null}
              </div>

              {isLoadingLandingPageHtml ? (
                <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-600">
                  Carregando HTML final aprovado...
                </div>
              ) : null}

              {!isLoadingLandingPageHtml && landingPageHtmlErrorMessage ? (
                <div className="mt-6 rounded-lg border border-dashed border-amber-300 bg-amber-50 px-4 py-5 text-sm text-amber-800">
                  {landingPageHtmlErrorMessage}
                </div>
              ) : null}

              {!isLoadingLandingPageHtml && !landingPageHtmlErrorMessage && landingPageHtml ? (
                <div className="mt-6 space-y-4">
                  <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                    <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 font-semibold uppercase tracking-wide text-slate-700">
                      <Code2 className="mr-2 h-3.5 w-3.5" />
                      HTML + Tailwind
                    </span>
                    <span>Atualizado em {formatDateTimeLabel(landingPageHtml.updated_at)}</span>
                  </div>
                  <CodeViewer code={landingPageHtml.content} />
                </div>
              ) : null}
            </div>

            <TrackingSheet
              rows={trackingSheetRows}
              isLoading={isLoadingTrackingSheet}
              errorMessage={trackingSheetErrorMessage}
              copied={copiedTargetId === 'tracking-sheet-csv'}
              onCopyCsv={() =>
                void handleCopy({
                  content: buildTrackingSheetCsv(trackingSheetRows),
                  successMessage: 'Tracking Sheet copiada em CSV com sucesso.',
                  targetId: 'tracking-sheet-csv',
                })
              }
            />
              </>
            ) : null}

            <div className="rounded-xl bg-white p-6 shadow">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
                  Benchmarking
                </p>
                <h2 className="mt-2 text-2xl font-bold text-gray-900">
                  Documento final aprovado
                </h2>
                <p className="mt-2 max-w-3xl text-sm text-gray-600">
                  Leia e copie o benchmark final em Markdown sem sair da
                  experiencia de entrega.
                </p>
              </div>
            </div>

            {deliverablesErrorMessage ? (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                {deliverablesErrorMessage}
              </div>
            ) : null}

            {isLoadingDeliverables ? (
              <div className="rounded-lg bg-white px-4 py-5 text-sm text-gray-600 shadow">
                Carregando os textos finais aprovados...
              </div>
            ) : null}

            {!isLoadingDeliverables && !deliverablesErrorMessage
              ? deliverables.map((document) => (
                  <div
                    key={document.id}
                    className="rounded-xl bg-white p-6 shadow"
                  >
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <div className="inline-flex rounded-full bg-blue-100 p-3 text-blue-700">
                          <FileText className="h-5 w-5" />
                        </div>
                        <p className="mt-4 text-sm font-semibold uppercase tracking-wide text-blue-700">
                          {getDeliverableLabel(document.document_kind)}
                        </p>
                        <h2 className="mt-2 text-2xl font-bold text-gray-900">
                          {document.title}
                        </h2>
                        <p className="mt-2 text-xs text-gray-500">
                          Atualizado em {formatDateTimeLabel(document.updated_at)}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          void handleCopy({
                            content: document.content,
                            successMessage: `${getDeliverableLabel(document.document_kind)} copiado com sucesso.`,
                            targetId: `document-${document.id}`,
                          })
                        }
                        className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
                      >
                        {copiedTargetId === `document-${document.id}` ? (
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                        ) : (
                          <Copy className="mr-2 h-4 w-4" />
                        )}
                        {copiedTargetId === `document-${document.id}` ? 'Texto copiado' : 'Copiar texto'}
                      </button>
                    </div>

                    <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-5">
                      <div className="prose prose-sm max-w-none text-gray-800 prose-headings:text-gray-900 prose-p:text-gray-700 prose-li:text-gray-700">
                        <ReactMarkdown>{document.content}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                ))
              : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
