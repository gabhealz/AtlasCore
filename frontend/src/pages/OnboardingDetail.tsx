import type { AxiosError } from 'axios';
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  FileUp,
  FolderOpen,
  MousePointerClick,
  PlayCircle,
  RotateCcw,
  Upload,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import {
  type PipelineStreamEvent,
  useOnboardingStream,
  type StreamConnectionStatus,
} from '../hooks/useOnboardingStream';
import { api } from '../lib/api';

type UploadedAsset = {
  id: number;
  onboarding_id: number;
  asset_kind: string;
  asset_category?: string | null;
  original_filename: string;
  storage_url?: string | null;
  content_type: string;
  size_bytes: number;
  created_at: string;
};

type AssetCategory =
  | 'hero_image'
  | 'profile_picture'
  | 'environment_photo'
  | 'treatment_photo';

type AssetUploadResponse = {
  data: UploadedAsset;
};

type AssetListResponse = {
  data: UploadedAsset[];
};

type CTAButton = {
  id: number;
  onboarding_id: number;
  name: string;
  button_text: string;
  css_id: string;
  created_at: string;
};

type CTAButtonResponse = {
  data: CTAButton;
};

type CTAButtonListResponse = {
  data: CTAButton[];
};

type OnboardingSummary = {
  id: number;
  status: string;
};

type OnboardingListResponse = {
  data: OnboardingSummary[];
};

type PipelineStartData = {
  onboarding_id: number;
  status: string;
};

type PipelineStartResponse = {
  data: PipelineStartData;
};

type HumanReviewDocument = {
  id: number;
  onboarding_id: number;
  step_name: string;
  agent_name: string;
  document_kind: string;
  title: string;
  content: string;
  content_format: 'markdown' | 'html' | string;
  review_status: string;
  review_feedback?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
};

type HumanReviewDocumentResponse = {
  data: HumanReviewDocument;
};

type HumanReviewActionData = {
  onboarding_id: number;
  status: string;
  next_step_name?: string | null;
};

type HumanReviewActionResponse = {
  data: HumanReviewActionData;
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

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.docx'];
const IMAGE_ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'];
const CSS_ID_PATTERN = /^[a-z][a-z0-9_-]*$/;
const LANDING_PAGE_FEATURES_ENABLED = false;
const IMAGE_CATEGORY_OPTIONS: Array<{
  value: AssetCategory;
  label: string;
  description: string;
}> = [
  {
    value: 'hero_image',
    label: 'Hero',
    description: 'Imagem principal da landing page.',
  },
  {
    value: 'profile_picture',
    label: 'Perfil',
    description: 'Foto principal do medico ou especialista.',
  },
  {
    value: 'environment_photo',
    label: 'Ambiente',
    description: 'Foto de consultorio, clinica ou estrutura.',
  },
  {
    value: 'treatment_photo',
    label: 'Tratamento',
    description: 'Foto complementar para cards de dores ou procedimentos.',
  },
];

function getFileExtension(filename: string) {
  const dotIndex = filename.lastIndexOf('.');
  if (dotIndex === -1) {
    return '';
  }

  return filename.slice(dotIndex).toLowerCase();
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getAssetCategoryLabel(category: string | null | undefined) {
  const option = IMAGE_CATEGORY_OPTIONS.find((item) => item.value === category);
  return option?.label ?? category ?? 'Nao informado';
}

function getAssetKindLabel(asset: UploadedAsset) {
  if (asset.asset_kind === 'transcription') {
    return 'Documento base';
  }

  if (asset.asset_kind === 'image') {
    return `Imagem - ${getAssetCategoryLabel(asset.asset_category)}`;
  }

  return asset.asset_kind;
}

function getOnboardingStatusBadgeColor(status: string) {
  switch (status) {
    case 'PENDING':
      return 'bg-yellow-100 text-yellow-800';
    case 'RUNNING':
      return 'bg-blue-100 text-blue-800';
    case 'AWAITING_REVIEW':
      return 'bg-amber-100 text-amber-800';
    case 'APPROVED':
      return 'bg-green-100 text-green-800';
    case 'REJECTED':
      return 'bg-rose-100 text-rose-800';
    case 'FAILED':
      return 'bg-red-100 text-red-800';
    case 'ACTIVE':
      return 'bg-blue-100 text-blue-800';
    case 'COMPLETED':
      return 'bg-green-100 text-green-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
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
    case 'ACTIVE':
      return 'Ativo';
    case 'COMPLETED':
      return 'Concluido';
    default:
      return status;
  }
}

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

function getStreamConnectionBadgeColor(status: StreamConnectionStatus) {
  switch (status) {
    case 'connected':
      return 'bg-emerald-100 text-emerald-800';
    case 'connecting':
      return 'bg-sky-100 text-sky-800';
    case 'reconnecting':
      return 'bg-amber-100 text-amber-800';
    case 'unavailable':
      return 'bg-rose-100 text-rose-800';
    case 'idle':
    default:
      return 'bg-gray-100 text-gray-700';
  }
}

function getStreamConnectionLabel(status: StreamConnectionStatus) {
  switch (status) {
    case 'connected':
      return 'Tempo real conectado';
    case 'connecting':
      return 'Conectando stream';
    case 'reconnecting':
      return 'Reconectando stream';
    case 'unavailable':
      return 'Stream indisponivel';
    case 'idle':
    default:
      return 'Stream em espera';
  }
}

function formatPipelineStepLabel(stepName: string | null | undefined) {
  if (!stepName) {
    return 'Sem etapa recebida ainda';
  }

  const knownLabels: Record<string, string> = {
    pipeline_start: 'inicio do pipeline',
    llm_runner_probe: 'teste inicial do runner',
    researcher: 'pesquisador',
    researcher_review: 'revisao CFM do pesquisador',
    strategist: 'estrategista',
    strategist_review: 'revisao CFM do estrategista',
    copywriter: 'copywriter',
    copywriter_review: 'revisao CFM do copywriter',
    script_writer: 'roteirista',
    script_writer_review: 'revisao CFM do roteirista',
    html_developer: 'desenvolvedor HTML',
    html_developer_review: 'revisao CFM do HTML',
  };

  return knownLabels[stepName] ?? stepName.split('_').join(' ');
}

function getPipelineActivityLabel(event: PipelineStreamEvent | null) {
  if (!event) {
    return 'Aguardando o primeiro sinal da IA';
  }

  const stepLabel = formatPipelineStepLabel(event.step_name);

  switch (event.trigger) {
    case 'manual_start':
      return 'Pipeline iniciado. Aguardando o primeiro agente assumir.';
    case 'agent_step_started':
      return `IA trabalhando agora: ${stepLabel}`;
    case 'agent_step_completed':
      return `IA concluiu: ${stepLabel}`;
    case 'review_step_started':
      return `Checker CFM revisando: ${stepLabel}`;
    case 'review_step_approved':
      return `Checker CFM aprovou: ${stepLabel}`;
    case 'review_step_rejected':
      return `Checker CFM pediu reescrita: ${stepLabel}`;
    case 'human_review_approved':
      return `Revisao humana aprovada: ${stepLabel}`;
    case 'human_review_rejected':
      return `Revisao humana recusou: ${stepLabel}`;
    case 'agent_runner_failed':
    case 'agent_output_invalid':
    case 'html_validation_failed':
    case 'review_rewrite_limit_exceeded':
      return `Pipeline parou em: ${stepLabel}`;
    case 'stream_connect':
      return `Snapshot atual: ${getOnboardingStatusLabel(event.to_status)}`;
    default:
      return stepLabel;
  }
}

function getPipelineTriggerLabel(trigger: string | null | undefined) {
  switch (trigger) {
    case 'agent_step_started':
    case 'review_step_started':
      return 'em andamento';
    case 'agent_step_completed':
    case 'review_step_approved':
      return 'concluido';
    case 'review_step_rejected':
    case 'human_review_rejected':
      return 'reexecucao';
    case 'agent_runner_failed':
    case 'agent_output_invalid':
    case 'html_validation_failed':
    case 'review_rewrite_limit_exceeded':
      return 'falha';
    case 'manual_start':
      return 'inicio';
    case 'stream_connect':
      return 'snapshot';
    default:
      return trigger ?? 'sem evento';
  }
}

function formatDateTimeLabel(value: string | null | undefined) {
  if (!value) {
    return 'Sem atualizacao recebida ainda';
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(parsedDate);
}

function getReviewContentFormatLabel(contentFormat: string) {
  return contentFormat === 'html' ? 'HTML bruto' : 'Markdown';
}

export default function OnboardingDetail() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const justCreated = location.state?.justCreated === true;
  const onboardingStatusFromState =
    typeof location.state?.onboardingStatus === 'string'
      ? location.state.onboardingStatus
      : null;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const imageFileInputRef = useRef<HTMLInputElement | null>(null);
  const pipelineStreamEventHandlerRef = useRef<
    ((event: PipelineStreamEvent) => void) | null
  >(null);
  const onboardingId = Number(id);
  const hasValidOnboardingId = Number.isInteger(onboardingId) && onboardingId > 0;
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedAssets, setUploadedAssets] = useState<UploadedAsset[]>([]);
  const [onboardingAssets, setOnboardingAssets] = useState<UploadedAsset[]>([]);
  const [assetLoadErrorMessage, setAssetLoadErrorMessage] = useState('');
  const [isLoadingAssets, setIsLoadingAssets] = useState(false);
  const [selectedImageCategory, setSelectedImageCategory] = useState<
    AssetCategory | ''
  >('');
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [imageErrorMessage, setImageErrorMessage] = useState('');
  const [imageSuccessMessage, setImageSuccessMessage] = useState('');
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [uploadedImageAsset, setUploadedImageAsset] =
    useState<UploadedAsset | null>(null);
  const [ctaButtons, setCtaButtons] = useState<CTAButton[]>([]);
  const [ctaName, setCtaName] = useState('');
  const [ctaButtonText, setCtaButtonText] = useState('');
  const [ctaCssId, setCtaCssId] = useState('');
  const [ctaErrorMessage, setCtaErrorMessage] = useState('');
  const [ctaLoadErrorMessage, setCtaLoadErrorMessage] = useState('');
  const [ctaSuccessMessage, setCtaSuccessMessage] = useState('');
  const [isLoadingCtaButtons, setIsLoadingCtaButtons] = useState(false);
  const [isSavingCtaButton, setIsSavingCtaButton] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<string | null>(
    hasValidOnboardingId ? onboardingStatusFromState : null,
  );
  const [pipelineErrorMessage, setPipelineErrorMessage] = useState('');
  const [pipelineSuccessMessage, setPipelineSuccessMessage] = useState('');
  const [isStartingPipeline, setIsStartingPipeline] = useState(false);
  const [isLoadingPipelineStatus, setIsLoadingPipelineStatus] = useState(
    hasValidOnboardingId && onboardingStatusFromState === null,
  );
  const [reviewDocument, setReviewDocument] = useState<HumanReviewDocument | null>(
    null,
  );
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewContent, setReviewContent] = useState('');
  const [reviewFeedback, setReviewFeedback] = useState('');
  const [reviewLoadErrorMessage, setReviewLoadErrorMessage] = useState('');
  const [reviewActionErrorMessage, setReviewActionErrorMessage] = useState('');
  const [reviewActionSuccessMessage, setReviewActionSuccessMessage] = useState('');
  const [isLoadingReviewDocument, setIsLoadingReviewDocument] = useState(false);
  const [isApprovingReview, setIsApprovingReview] = useState(false);
  const [isRejectingReview, setIsRejectingReview] = useState(false);
  const {
    connectionStatus: pipelineConnectionStatus,
    latestEvent: latestPipelineEvent,
  } = useOnboardingStream({
    onboardingId,
    enabled: hasValidOnboardingId,
    onEventRef: pipelineStreamEventHandlerRef,
  });
  const resolvedPipelineStatus = pipelineStatus;
  const resolvedPipelineStatusLoading = isLoadingPipelineStatus;

  useEffect(() => {
    pipelineStreamEventHandlerRef.current = (event) => {
      setPipelineStatus(event.to_status);
    };

    return () => {
      pipelineStreamEventHandlerRef.current = null;
    };
  }, []);

  useEffect(() => {
    let isCancelled = false;

    if (!hasValidOnboardingId) {
      return () => {
        isCancelled = true;
      };
    }

    async function loadCtaButtons() {
      setIsLoadingCtaButtons(true);
      setCtaLoadErrorMessage('');

      try {
        const response = await api.get<CTAButtonListResponse>(
          `/tracking/${onboardingId}/cta_buttons`,
        );

        if (isCancelled) {
          return;
        }

        setCtaButtons(response.data.data);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const axiosError = error as AxiosError<ApiErrorResponse>;
        setCtaLoadErrorMessage(
          getApiErrorMessage(
            axiosError,
            'Nao foi possivel carregar a matriz de botoes CTA.',
          ),
        );
        setCtaButtons([]);
      } finally {
        if (!isCancelled) {
          setIsLoadingCtaButtons(false);
        }
      }
    }

    void loadCtaButtons();

    return () => {
      isCancelled = true;
    };
  }, [hasValidOnboardingId, onboardingId]);

  useEffect(() => {
    let isCancelled = false;

    if (!hasValidOnboardingId) {
      return () => {
        isCancelled = true;
      };
    }

    async function loadOnboardingAssets() {
      setIsLoadingAssets(true);
      setAssetLoadErrorMessage('');

      try {
        const response = await api.get<AssetListResponse>(
          `/assets/onboarding/${onboardingId}`,
        );

        if (isCancelled) {
          return;
        }

        setOnboardingAssets(response.data.data);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const axiosError = error as AxiosError<ApiErrorResponse>;
        setAssetLoadErrorMessage(
          getApiErrorMessage(
            axiosError,
            'Nao foi possivel carregar os arquivos ja anexados.',
          ),
        );
        setOnboardingAssets([]);
      } finally {
        if (!isCancelled) {
          setIsLoadingAssets(false);
        }
      }
    }

    void loadOnboardingAssets();

    return () => {
      isCancelled = true;
    };
  }, [hasValidOnboardingId, onboardingId]);

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

      try {
        const response = await api.get<OnboardingListResponse>('/onboardings');

        if (isCancelled) {
          return;
        }

        const onboarding = response.data.data.find((item) => item.id === onboardingId);
        if (!onboarding) {
          if (onboardingStatusFromState === null) {
            setPipelineStatus(null);
            setPipelineErrorMessage(
              'Nao foi possivel encontrar este onboarding para carregar o status atual.',
            );
          }
          return;
        }

        setPipelineStatus(onboarding.status);
        setPipelineErrorMessage('');
      } catch (error) {
        if (isCancelled) {
          return;
        }

        if (onboardingStatusFromState === null) {
          const axiosError = error as AxiosError<ApiErrorResponse>;
          setPipelineStatus(null);
          setPipelineErrorMessage(
            getApiErrorMessage(
              axiosError,
              'Nao foi possivel carregar o status atual deste onboarding.',
            ),
          );
        }
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

    if (!hasValidOnboardingId || resolvedPipelineStatus !== 'AWAITING_REVIEW') {
      return () => {
        isCancelled = true;
      };
    }

    async function loadPendingReviewDocument() {
      setIsLoadingReviewDocument(true);
      setReviewLoadErrorMessage('');

      try {
        const response = await api.get<HumanReviewDocumentResponse>(
          `/onboardings/${onboardingId}/review`,
        );

        if (isCancelled) {
          return;
        }

        const document = response.data.data;
        setReviewDocument(document);
        setReviewTitle(document.title);
        setReviewContent(document.content);
        setReviewFeedback('');
        setReviewActionErrorMessage('');
      } catch (error) {
        if (isCancelled) {
          return;
        }

        const axiosError = error as AxiosError<ApiErrorResponse>;
        setReviewDocument(null);
        setReviewTitle('');
        setReviewContent('');
        setReviewLoadErrorMessage(
          getApiErrorMessage(
            axiosError,
            'Nao foi possivel carregar o documento pendente de revisao.',
          ),
        );
      } finally {
        if (!isCancelled) {
          setIsLoadingReviewDocument(false);
        }
      }
    }

    void loadPendingReviewDocument();

    return () => {
      isCancelled = true;
    };
  }, [
    hasValidOnboardingId,
    onboardingId,
    resolvedPipelineStatus,
    latestPipelineEvent?.created_at,
  ]);

  const validateFile = (file: File | null) => {
    if (!file) {
      return 'Selecione ao menos um arquivo PDF, DOCX ou TXT antes de continuar.';
    }

    const extension = getFileExtension(file.name);
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return 'Apenas arquivos PDF, DOCX ou TXT sao permitidos.';
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      return 'O limite de upload para transcricoes e de 50MB.';
    }

    if (file.size === 0) {
      return 'O arquivo selecionado esta vazio.';
    }

    return '';
  };

  const validateFiles = (files: File[]) => {
    if (files.length === 0) {
      return 'Selecione ao menos um arquivo PDF, DOCX ou TXT antes de continuar.';
    }

    for (const file of files) {
      const validationMessage = validateFile(file);
      if (validationMessage) {
        return `${file.name}: ${validationMessage}`;
      }
    }

    return '';
  };

  const validateImageFile = (file: File | null) => {
    if (!file) {
      return 'Selecione uma imagem JPG, PNG, WebP, HEIC ou HEIF antes de continuar.';
    }

    const extension = getFileExtension(file.name);
    if (!IMAGE_ALLOWED_EXTENSIONS.includes(extension)) {
      return 'Apenas imagens JPG, PNG, WebP, HEIC ou HEIF sao permitidas.';
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      return 'O limite de upload para assets fotograficos e de 50MB.';
    }

    if (file.size === 0) {
      return 'A imagem selecionada esta vazia.';
    }

    return '';
  };

  const validateCtaForm = () => {
    const normalizedName = ctaName.trim();
    const normalizedButtonText = ctaButtonText.trim();
    const normalizedCssId = ctaCssId.trim().toLowerCase();

    if (!normalizedName) {
      return 'Informe o nome do botao CTA.';
    }

    if (!normalizedButtonText) {
      return 'Informe o texto do botao CTA.';
    }

    if (!normalizedCssId) {
      return 'Informe o ID CSS do botao.';
    }

    if (!CSS_ID_PATTERN.test(normalizedCssId)) {
      return "O ID CSS deve comecar com letra e usar apenas letras minusculas, numeros, '-' ou '_'.";
    }

    return '';
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    setSuccessMessage('');
    setUploadedAssets([]);

    const validationMessage = validateFiles(files);
    setErrorMessage(validationMessage);

    if (validationMessage) {
      setSelectedFiles([]);
      event.target.value = '';
      return;
    }

    setSelectedFiles(files);
  };

  const handleUpload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const validationMessage = validateFiles(selectedFiles);
    if (validationMessage) {
      setErrorMessage(validationMessage);
      setSuccessMessage('');
      return;
    }

    if (!Number.isInteger(onboardingId) || onboardingId <= 0) {
      setErrorMessage('ID de onboarding invalido para upload.');
      setSuccessMessage('');
      return;
    }

    setIsUploading(true);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      const uploadedDocuments: UploadedAsset[] = [];

      for (const selectedFile of selectedFiles) {
        const formData = new FormData();
        formData.append('onboarding_id', String(onboardingId));
        formData.append('file', selectedFile);

        const response = await api.post<AssetUploadResponse>(
          '/assets/upload',
          formData,
        );
        uploadedDocuments.push(response.data.data);
      }

      setUploadedAssets(uploadedDocuments);
      setOnboardingAssets((currentAssets) => [
        ...currentAssets,
        ...uploadedDocuments,
      ]);
      setSuccessMessage(
        `${uploadedDocuments.length} documento${
          uploadedDocuments.length === 1 ? '' : 's'
        } enviado${uploadedDocuments.length === 1 ? '' : 's'} com sucesso.`,
      );
      setSelectedFiles([]);

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      setErrorMessage(
        getApiErrorMessage(
          axiosError,
          'Nao foi possivel concluir o upload dos documentos.',
        ),
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleImageFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setImageSuccessMessage('');
    setUploadedImageAsset(null);

    const validationMessage = validateImageFile(file);
    setImageErrorMessage(validationMessage);

    if (validationMessage) {
      setSelectedImageFile(null);
      event.target.value = '';
      return;
    }

    setSelectedImageFile(file);
  };

  const handleImageUpload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!selectedImageCategory) {
      setImageErrorMessage('Escolha uma categoria para o asset fotografico.');
      setImageSuccessMessage('');
      return;
    }

    const validationMessage = validateImageFile(selectedImageFile);
    if (validationMessage) {
      setImageErrorMessage(validationMessage);
      setImageSuccessMessage('');
      return;
    }

    if (!Number.isInteger(onboardingId) || onboardingId <= 0) {
      setImageErrorMessage('ID de onboarding invalido para upload.');
      setImageSuccessMessage('');
      return;
    }

    const formData = new FormData();
    formData.append('onboarding_id', String(onboardingId));
    formData.append('asset_category', selectedImageCategory);
    formData.append('file', selectedImageFile as File);

    setIsUploadingImage(true);
    setImageErrorMessage('');
    setImageSuccessMessage('');

    try {
      const response = await api.post<AssetUploadResponse>(
        '/assets/upload-image',
        formData,
      );
      setUploadedImageAsset(response.data.data);
      setOnboardingAssets((currentAssets) => [
        ...currentAssets,
        response.data.data,
      ]);
      setImageSuccessMessage('Asset fotografico enviado com sucesso.');
      setSelectedImageFile(null);
      setSelectedImageCategory('');

      if (imageFileInputRef.current) {
        imageFileInputRef.current.value = '';
      }
    } catch (error) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      setImageErrorMessage(
        getApiErrorMessage(
          axiosError,
          'Nao foi possivel concluir o upload do asset fotografico.',
        ),
      );
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleCtaButtonSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const validationMessage = validateCtaForm();
    if (validationMessage) {
      setCtaErrorMessage(validationMessage);
      setCtaSuccessMessage('');
      return;
    }

    if (!Number.isInteger(onboardingId) || onboardingId <= 0) {
      setCtaErrorMessage('ID de onboarding invalido para tracking.');
      setCtaSuccessMessage('');
      return;
    }

    setIsSavingCtaButton(true);
    setCtaErrorMessage('');
    setCtaSuccessMessage('');

    try {
      const response = await api.post<CTAButtonResponse>(
        `/tracking/${onboardingId}/cta_buttons`,
        {
          name: ctaName.trim(),
          button_text: ctaButtonText.trim(),
          css_id: ctaCssId.trim().toLowerCase(),
        },
      );

      setCtaButtons((currentButtons) =>
        [...currentButtons, response.data.data].sort((left, right) => {
          const leftDate = new Date(left.created_at).getTime();
          const rightDate = new Date(right.created_at).getTime();
          if (leftDate === rightDate) {
            return left.id - right.id;
          }

          return leftDate - rightDate;
        }),
      );
      setCtaName('');
      setCtaButtonText('');
      setCtaCssId('');
      setCtaSuccessMessage('Botao CTA cadastrado com sucesso.');
      setCtaLoadErrorMessage('');
    } catch (error) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      setCtaErrorMessage(
        getApiErrorMessage(axiosError, 'Nao foi possivel salvar o botao CTA.'),
      );
    } finally {
      setIsSavingCtaButton(false);
    }
  };

  const handleStartPipeline = async () => {
    if (!Number.isInteger(onboardingId) || onboardingId <= 0) {
      setPipelineErrorMessage('ID de onboarding invalido para iniciar o pipeline.');
      setPipelineSuccessMessage('');
      return;
    }

    if (!pipelineInputsReady) {
      setPipelineErrorMessage(
        LANDING_PAGE_FEATURES_ENABLED
          ? 'Complete documento base, imagem hero, foto do medico, foto da clinica e CTA antes de iniciar a esteira de IA.'
          : 'Anexe ao menos um documento base ou transcricao antes de gerar o benchmark.',
      );
      setPipelineSuccessMessage('');
      return;
    }

    setIsStartingPipeline(true);
    setPipelineErrorMessage('');
    setPipelineSuccessMessage('');

    try {
      const response = await api.post<PipelineStartResponse>(
        `/onboardings/${onboardingId}/start`,
      );
      setPipelineStatus(response.data.data.status);
      setPipelineSuccessMessage(
        'Pipeline iniciado com sucesso. Acompanhe as atualizacoes em tempo real neste card.',
      );
    } catch (error) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      const detail = axiosError.response?.data?.detail;
      if (!Array.isArray(detail) && typeof detail?.current_status === 'string') {
        setPipelineStatus(detail.current_status);
      }

      setPipelineErrorMessage(
        getApiErrorMessage(
          axiosError,
          'Nao foi possivel iniciar o pipeline deste onboarding.',
        ),
      );
    } finally {
      setIsStartingPipeline(false);
    }
  };

  const validateReviewApproval = () => {
    if (!reviewTitle.trim()) {
      return 'Informe um titulo antes de aprovar esta etapa.';
    }

    if (!reviewContent.trim()) {
      return 'O conteudo da etapa nao pode ficar vazio na aprovacao.';
    }

    return '';
  };

  const validateReviewRejection = () => {
    if (!reviewFeedback.trim()) {
      return 'Escreva um feedback para o agente antes de recusar.';
    }

    return '';
  };

  const handleApproveReview = async () => {
    const validationMessage = validateReviewApproval();
    if (validationMessage) {
      setReviewActionErrorMessage(validationMessage);
      setReviewActionSuccessMessage('');
      return;
    }

    if (!Number.isInteger(onboardingId) || onboardingId <= 0) {
      setReviewActionErrorMessage('ID de onboarding invalido para aprovacao.');
      setReviewActionSuccessMessage('');
      return;
    }

    setIsApprovingReview(true);
    setReviewActionErrorMessage('');
    setReviewActionSuccessMessage('');

    try {
      const response = await api.post<HumanReviewActionResponse>(
        `/onboardings/${onboardingId}/review/approve`,
        {
          title: reviewTitle.trim(),
          content: reviewContent.trim(),
        },
      );
      setPipelineStatus(response.data.data.status);
      setReviewActionSuccessMessage(
        response.data.data.status === 'APPROVED'
          ? 'Etapa aprovada. O onboarding chegou ao estado final aprovado.'
          : 'Etapa aprovada. O pipeline foi retomado para a proxima fase.',
      );
      setPipelineSuccessMessage(
        response.data.data.status === 'APPROVED'
          ? 'A revisao humana finalizou este onboarding com sucesso.'
          : 'Revisao aprovada. A esteira voltou a rodar em background.',
      );
      setReviewDocument(null);
      setReviewTitle('');
      setReviewContent('');
      setReviewFeedback('');
      setReviewLoadErrorMessage('');
    } catch (error) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      setReviewActionErrorMessage(
        getApiErrorMessage(
          axiosError,
          'Nao foi possivel aprovar a etapa atual.',
        ),
      );
    } finally {
      setIsApprovingReview(false);
    }
  };

  const handleRejectReview = async () => {
    const validationMessage = validateReviewRejection();
    if (validationMessage) {
      setReviewActionErrorMessage(validationMessage);
      setReviewActionSuccessMessage('');
      return;
    }

    if (!Number.isInteger(onboardingId) || onboardingId <= 0) {
      setReviewActionErrorMessage('ID de onboarding invalido para recusa.');
      setReviewActionSuccessMessage('');
      return;
    }

    setIsRejectingReview(true);
    setReviewActionErrorMessage('');
    setReviewActionSuccessMessage('');

    try {
      const response = await api.post<HumanReviewActionResponse>(
        `/onboardings/${onboardingId}/review/reject`,
        {
          feedback: reviewFeedback.trim(),
        },
      );
      setPipelineStatus(response.data.data.status);
      setReviewActionSuccessMessage(
        'Etapa recusada. O agente esta refazendo o material com o seu feedback.',
      );
      setPipelineSuccessMessage(
        'Revisao recusada. A etapa voltou para execucao em background.',
      );
      setReviewDocument(null);
      setReviewTitle('');
      setReviewContent('');
      setReviewFeedback('');
      setReviewLoadErrorMessage('');
    } catch (error) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      setReviewActionErrorMessage(
        getApiErrorMessage(
          axiosError,
          'Nao foi possivel recusar a etapa atual.',
        ),
      );
    } finally {
      setIsRejectingReview(false);
    }
  };

  const pipelineFailureMessage =
    resolvedPipelineStatus === 'FAILED' && latestPipelineEvent?.to_status === 'FAILED'
      ? latestPipelineEvent.error_message ??
        'O pipeline falhou durante a execucao da chamada de IA.'
      : '';
  const resolvedPipelineErrorMessage =
    pipelineFailureMessage || (latestPipelineEvent === null ? pipelineErrorMessage : '');
  const pipelineFailureIssues =
    latestPipelineEvent?.to_status === 'FAILED' ? latestPipelineEvent.issues ?? [] : [];
  const resolvedPipelineSuccessMessage =
    latestPipelineEvent?.to_status === 'FAILED' ? '' : pipelineSuccessMessage;
  const pipelineBadgeColor = getOnboardingStatusBadgeColor(
    !hasValidOnboardingId || resolvedPipelineStatusLoading
      ? ''
      : resolvedPipelineStatus ?? '',
  );
  const pipelineStatusLabel = !hasValidOnboardingId
    ? 'Status indisponivel'
    : resolvedPipelineStatusLoading
      ? 'Carregando status...'
      : resolvedPipelineStatus
        ? getOnboardingStatusLabel(resolvedPipelineStatus)
        : 'Status indisponivel';
  const hasBaseDocument = onboardingAssets.some(
    (asset) => asset.asset_kind === 'transcription',
  );
  const hasHeroImage = onboardingAssets.some(
    (asset) => asset.asset_kind === 'image' && asset.asset_category === 'hero_image',
  );
  const hasProfilePicture = onboardingAssets.some(
    (asset) =>
      asset.asset_kind === 'image' && asset.asset_category === 'profile_picture',
  );
  const hasEnvironmentPhoto = onboardingAssets.some(
    (asset) =>
      asset.asset_kind === 'image' && asset.asset_category === 'environment_photo',
  );
  const hasCtaButton = ctaButtons.length > 0;
  const documentAssets = onboardingAssets.filter(
    (asset) => asset.asset_kind === 'transcription',
  );
  const imageAssets = onboardingAssets.filter((asset) => asset.asset_kind === 'image');
  const pipelineInputsReady = LANDING_PAGE_FEATURES_ENABLED
    ? hasBaseDocument &&
      hasHeroImage &&
      hasProfilePicture &&
      hasEnvironmentPhoto &&
      hasCtaButton
    : hasBaseDocument;
  const pipelineButtonLabel = isStartingPipeline
    ? 'Iniciando pipeline...'
    : !hasValidOnboardingId || resolvedPipelineStatusLoading
      ? 'Carregando status...'
      : resolvedPipelineStatus === 'PENDING' && !pipelineInputsReady
        ? 'Complete os insumos'
        : resolvedPipelineStatus === 'FAILED'
        ? 'Tentar novamente'
        : resolvedPipelineStatus === 'PENDING'
        ? 'Gerar Benchmark'
        : 'Pipeline indisponivel neste estado';
  const pipelineConnectionLabel =
    getStreamConnectionLabel(pipelineConnectionStatus);
  const pipelineConnectionBadgeColor =
    getStreamConnectionBadgeColor(pipelineConnectionStatus);
  const pipelineLastStepLabel = formatPipelineStepLabel(
    latestPipelineEvent?.step_name,
  );
  const pipelineActivityLabel = getPipelineActivityLabel(latestPipelineEvent);
  const pipelineTriggerLabel = getPipelineTriggerLabel(latestPipelineEvent?.trigger);
  const pipelineLastUpdateLabel = formatDateTimeLabel(
    latestPipelineEvent?.created_at,
  );
  const pipelineAttemptLabel =
    typeof latestPipelineEvent?.attempt_count === 'number'
      ? `${latestPipelineEvent.attempt_count} tentativa${
          latestPipelineEvent.attempt_count === 1 ? '' : 's'
        }`
      : 'Nao informado';
  const pipelineModelLabel = latestPipelineEvent?.model ?? 'Nao informado';
  const preparationItems = [
    {
      label: 'Documento base ou transcricao',
      description: 'Briefing, entrevista, pesquisa ou materiais do cliente.',
      done: hasBaseDocument,
    },
    ...(LANDING_PAGE_FEATURES_ENABLED
      ? [
          {
            label: 'Imagem hero',
            description: 'Foto principal para a primeira dobra do site.',
            done: hasHeroImage,
          },
          {
            label: 'Foto do medico',
            description: 'Retrato real para a secao de autoridade e bio.',
            done: hasProfilePicture,
          },
          {
            label: 'Foto da clinica',
            description: 'Ambiente, estrutura ou consultorio para localizacao.',
            done: hasEnvironmentPhoto,
          },
          {
            label: 'CTA da landing page',
            description: 'Nome, texto do botao e ID CSS para tracking.',
            done: hasCtaButton,
          },
        ]
      : []),
  ];
  const pendingPreparationItems = preparationItems.filter((item) => !item.done);
  const pipelineReadinessLabel = pipelineInputsReady
    ? 'Pronto para IA'
    : `${pendingPreparationItems.length} pendencia${
        pendingPreparationItems.length === 1 ? '' : 's'
      }`;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto flex max-w-5xl flex-col">
        <button
          onClick={() => navigate('/dashboard')}
          className="mb-6 flex items-center text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Voltar para Dashboard
        </button>

        <div
          className={`mb-6 rounded-xl border p-5 ${
            justCreated
              ? 'border-green-200 bg-green-50'
              : 'border-blue-200 bg-blue-50'
          }`}
        >
          <p
            className={`text-sm font-semibold uppercase tracking-wide ${
              justCreated ? 'text-green-700' : 'text-blue-700'
            }`}
          >
            {justCreated ? 'Projeto criado com sucesso' : 'Detalhes do onboarding'}
          </p>
          <h1 className="mt-2 text-3xl font-bold text-gray-900">Projeto #{id}</h1>
          <p className="mt-2 text-sm text-gray-700">
            {justCreated
              ? 'O briefing inicial foi salvo. O proximo passo do fluxo e anexar as transcricoes e documentos base deste onboarding.'
              : 'Este onboarding ja existe. O fluxo de detalhe completo ainda sera expandido nas proximas historias.'}
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-white p-6 shadow">
            <div className="mb-4 inline-flex rounded-full bg-blue-100 p-3 text-blue-700">
              <FileUp className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">
              {justCreated
                ? 'Proximo passo: upload de transcricoes'
                : 'Proxima etapa planejada'}
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Envie transcricoes em PDF, DOCX ou TXT para alimentar o pipeline
              de IA com o contexto do cliente.
            </p>
          </div>

          <div className="rounded-lg bg-white p-6 shadow">
            <div className="mb-4 inline-flex rounded-full bg-gray-100 p-3 text-gray-700">
              <FolderOpen className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">
              Estado atual do onboarding
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              {justCreated
                ? 'O projeto ja esta pronto para receber a primeira transcricao. Depois disso, as proximas historias vao expandir o restante do onboarding.'
                : 'A abertura direta pelo dashboard continua neutra: voce pode anexar novas transcricoes sem que a tela sugira uma criacao recente.'}
            </p>
          </div>
        </div>

        <div className="mt-6 rounded-xl bg-white p-6 shadow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-slate-600">
                Checklist de preparo
              </p>
              <h2 className="mt-2 text-2xl font-bold text-gray-900">
                Complete os insumos do benchmark
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-gray-600">
                Neste recorte urgente do MVP, a IA precisa apenas dos documentos
                base para gerar o Benchmarking. Landing page, imagens, CTA e
                tracking ficam desativados temporariamente.
              </p>
            </div>
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                pipelineInputsReady
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
            >
              {pipelineReadinessLabel}
            </span>
          </div>

          {assetLoadErrorMessage ? (
            <div className="mt-5 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
              {assetLoadErrorMessage}
            </div>
          ) : null}

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {preparationItems.map((item) => (
              <div
                key={item.label}
                className={`rounded-lg border px-4 py-3 text-sm ${
                  item.done
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                    : 'border-gray-200 bg-gray-50 text-gray-700'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold">{item.label}</p>
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-semibold uppercase ${
                      item.done
                        ? 'bg-white text-emerald-700'
                        : 'bg-white text-gray-500'
                    }`}
                  >
                    {item.done ? 'ok' : 'pendente'}
                  </span>
                </div>
                <p className="mt-2 text-xs">{item.description}</p>
              </div>
            ))}
          </div>

          <p className="mt-4 text-xs text-gray-500">
            {isLoadingAssets
              ? 'Carregando arquivos ja anexados...'
              : `${onboardingAssets.length} arquivo${
                  onboardingAssets.length === 1 ? '' : 's'
                } anexado${onboardingAssets.length === 1 ? '' : 's'} neste onboarding.`}
          </p>
        </div>

        {resolvedPipelineStatus === 'APPROVED' ? (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-white p-6 shadow">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
                  Entrega final
                </p>
                <h2 className="mt-2 text-2xl font-bold text-gray-900">
                  Entrega final pronta para copy-paste
                </h2>
                <p className="mt-2 max-w-2xl text-sm text-gray-600">
                  Este onboarding ja foi aprovado. Agora voce pode abrir a tela de
                  entrega para ler e copiar o Benchmarking final aprovado.
                </p>
              </div>

              <button
                type="button"
                onClick={() =>
                  navigate(`/onboarding/${onboardingId}/delivery`, {
                    state: { onboardingStatus: resolvedPipelineStatus },
                  })
                }
                className="inline-flex items-center justify-center rounded-md border border-transparent bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700"
              >
                <FileText className="mr-2 h-4 w-4" />
                Abrir entregaveis finais
              </button>
            </div>
          </div>
        ) : null}

        <div className="order-last mt-6 rounded-xl bg-white p-6 shadow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">
                Execucao do pipeline
              </p>
              <h2 className="mt-2 text-2xl font-bold text-gray-900">
                Gerar Benchmarking
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-gray-600">
                Depois de salvar ao menos um documento base, gere o Benchmarking
                e acompanhe este card em tempo real enquanto o pesquisador e o
                checker CFM trabalham.
              </p>
            </div>
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${pipelineBadgeColor}`}
            >
              {pipelineStatusLabel}
            </span>
          </div>

          {resolvedPipelineErrorMessage ? (
            <div className="mt-5 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
              <p>{resolvedPipelineErrorMessage}</p>
              {pipelineFailureIssues.length > 0 ? (
                <ul className="mt-3 list-disc space-y-1 pl-5">
                  {pipelineFailureIssues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {resolvedPipelineSuccessMessage ? (
            <div className="mt-5 rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
              {resolvedPipelineSuccessMessage}
            </div>
          ) : null}

          <div className="mt-5 grid gap-4 rounded-lg border border-gray-200 bg-gray-50 p-4 md:grid-cols-[220px_1fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Conexao SSE
              </p>
              <span
                className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${pipelineConnectionBadgeColor}`}
              >
                {pipelineConnectionLabel}
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  IA agora
                </p>
                <p className="mt-2 text-sm font-medium text-gray-900">
                  {pipelineActivityLabel}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  {pipelineLastStepLabel}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Evento / atualizacao
                </p>
                <p className="mt-2 text-sm font-medium text-gray-900">
                  {pipelineTriggerLabel}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  {pipelineLastUpdateLabel}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Tentativas / modelo
                </p>
                <p className="mt-2 text-sm font-medium text-gray-900">
                  {pipelineAttemptLabel}
                </p>
                <p className="mt-1 text-xs text-gray-500">{pipelineModelLabel}</p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-gray-500">
              O start fica disponivel em `PENDING` ou para tentar novamente em
              `FAILED`, depois que ao menos um documento base estiver salvo.
            </p>
            <button
              type="button"
              onClick={handleStartPipeline}
              disabled={
                !hasValidOnboardingId ||
                isStartingPipeline ||
                resolvedPipelineStatusLoading ||
                !['PENDING', 'FAILED'].includes(resolvedPipelineStatus ?? '') ||
                !pipelineInputsReady
              }
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300"
            >
              <PlayCircle className="mr-2 h-4 w-4" />
              {pipelineButtonLabel}
            </button>
          </div>
        </div>

        <div className="mt-6 rounded-xl bg-white p-6 shadow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-violet-600">
                Human-in-the-loop
              </p>
              <h2 className="mt-2 text-2xl font-bold text-gray-900">
                Revisao humana por etapa
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-gray-600">
                Quando o pipeline pausa em `AWAITING_REVIEW`, este bloco libera o
                documento atual para leitura, edicao inline e decisao de aprovar
                ou recusar com feedback.
              </p>
            </div>
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                reviewDocument
                  ? 'bg-violet-100 text-violet-800'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {reviewDocument
                ? formatPipelineStepLabel(reviewDocument.step_name)
                : 'Sem etapa pendente'}
            </span>
          </div>

          {reviewActionErrorMessage ? (
            <div className="mt-5 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
              {reviewActionErrorMessage}
            </div>
          ) : null}

          {reviewActionSuccessMessage ? (
            <div className="mt-5 rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
              {reviewActionSuccessMessage}
            </div>
          ) : null}

          {resolvedPipelineStatus !== 'AWAITING_REVIEW' ? (
            <div className="mt-6 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-5 text-sm text-gray-600">
              O editor de revisao aparece quando o Benchmarking pausa para
              aprovacao humana. Enquanto isso, upload de documentos e
              acompanhamento SSE continuam disponiveis normalmente nesta tela.
            </div>
          ) : isLoadingReviewDocument ? (
            <div className="mt-6 rounded-lg bg-gray-50 px-4 py-5 text-sm text-gray-600">
              Carregando documento pendente de revisao...
            </div>
          ) : reviewLoadErrorMessage ? (
            <div className="mt-6 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
              {reviewLoadErrorMessage}
            </div>
          ) : reviewDocument ? (
            <>
              <div className="mt-6 grid gap-4 rounded-lg border border-gray-200 bg-gray-50 p-4 md:grid-cols-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Etapa atual
                  </p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {formatPipelineStepLabel(reviewDocument.step_name)}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Formato
                  </p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {getReviewContentFormatLabel(reviewDocument.content_format)}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Documento interno
                  </p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {reviewDocument.document_kind}
                  </p>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Atualizado em
                  </p>
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {formatDateTimeLabel(reviewDocument.updated_at)}
                  </p>
                </div>
              </div>

              <div className="mt-6 grid gap-5">
                <div>
                  <label
                    htmlFor="review-title"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Titulo da etapa
                  </label>
                  <input
                    id="review-title"
                    type="text"
                    value={reviewTitle}
                    onChange={(event) => {
                      setReviewTitle(event.target.value);
                      setReviewActionErrorMessage('');
                      setReviewActionSuccessMessage('');
                    }}
                    className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700"
                  />
                </div>

                <div>
                  <label
                    htmlFor="review-content"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Conteudo gerado
                  </label>
                  <textarea
                    id="review-content"
                    value={reviewContent}
                    onChange={(event) => {
                      setReviewContent(event.target.value);
                      setReviewActionErrorMessage('');
                      setReviewActionSuccessMessage('');
                    }}
                    rows={reviewDocument.content_format === 'html' ? 18 : 14}
                    className={`mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 ${
                      reviewDocument.content_format === 'html' ? 'font-mono' : ''
                    }`}
                  />
                  <p className="mt-2 text-xs text-gray-500">
                    O conteudo pode ser ajustado manualmente antes da aprovacao.
                    Para HTML, esta historia mantem edicao textual sem preview.
                  </p>
                </div>

                <div>
                  <label
                    htmlFor="review-feedback"
                    className="block text-sm font-medium text-gray-700"
                  >
                    Feedback para recusar a etapa
                  </label>
                  <textarea
                    id="review-feedback"
                    value={reviewFeedback}
                    onChange={(event) => {
                      setReviewFeedback(event.target.value);
                      setReviewActionErrorMessage('');
                      setReviewActionSuccessMessage('');
                    }}
                    rows={4}
                    placeholder="Ex: deixe o tom mais formal e reduza promessas muito fortes."
                    className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700"
                  />
                  <p className="mt-2 text-xs text-gray-500">
                    Na recusa, esse feedback volta para o agente na mesma etapa.
                  </p>
                </div>
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-gray-500">
                  Aprovar salva a versao atual e finaliza o MVP de Benchmarking.
                  Recusar mantem o controle humano e pede reexecucao do pesquisador.
                </p>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={handleRejectReview}
                    disabled={isRejectingReview || isApprovingReview}
                    className="inline-flex items-center justify-center rounded-md border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-100 disabled:cursor-not-allowed disabled:border-rose-100 disabled:bg-rose-50 disabled:text-rose-300"
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    {isRejectingReview ? 'Recusando etapa...' : 'Recusar com Feedback'}
                  </button>

                  <button
                    type="button"
                    onClick={handleApproveReview}
                    disabled={isApprovingReview || isRejectingReview}
                    className="inline-flex items-center justify-center rounded-md border border-transparent bg-violet-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-violet-300"
                  >
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    {isApprovingReview ? 'Aprovando etapa...' : 'Aprovar Etapa'}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="mt-6 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-5 text-sm text-gray-600">
              O onboarding esta em `AWAITING_REVIEW`, mas nenhum documento
              pendente foi encontrado para esta etapa.
            </div>
          )}
        </div>

        <div className="mt-6 rounded-xl bg-white p-6 shadow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">
                Upload de transcricao
              </p>
              <h2 className="mt-2 text-2xl font-bold text-gray-900">
                Anexar documento base do onboarding
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-gray-600">
                Aceitamos varios documentos por envio, nos formatos PDF, DOCX
                ou TXT, com ate 50MB por arquivo. Cada upload fica associado a
                este onboarding para uso futuro no pipeline.
              </p>
            </div>
            <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600">
              Projeto #{id}
            </div>
          </div>

          <form onSubmit={handleUpload} className="mt-6 space-y-5">
            <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5">
              <label className="block text-sm font-medium text-gray-700">
                Arquivo da transcricao
              </label>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                onChange={handleFileChange}
                className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-blue-600 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-blue-700"
              />
              <p className="mt-2 text-xs text-gray-500">
                Formatos aceitos: `.pdf`, `.docx` e `.txt`. Limite: 50MB por
                arquivo.
              </p>

              {selectedFiles.length > 0 ? (
                <div className="mt-4 space-y-2">
                  {selectedFiles.map((file) => (
                    <div
                      key={`${file.name}-${file.size}-${file.lastModified}`}
                      className="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900"
                    >
                      <div className="flex items-center gap-3">
                        <FileText className="h-4 w-4" />
                        <div>
                          <p className="font-medium">{file.name}</p>
                          <p className="text-xs text-blue-700">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                      </div>
                      <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold uppercase text-blue-700">
                        pronto
                      </span>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            {errorMessage ? (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                {errorMessage}
              </div>
            ) : null}

            {successMessage ? (
              <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
                {successMessage}
              </div>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-gray-500">
                O upload e validado no navegador e novamente no backend antes de
                ir para o storage.
              </p>
              <button
                type="submit"
                disabled={isUploading || selectedFiles.length === 0}
                className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
              >
                <Upload className="mr-2 h-4 w-4" />
                {isUploading
                  ? 'Enviando documentos...'
                  : `Enviar ${selectedFiles.length || ''} Documento${
                      selectedFiles.length === 1 ? '' : 's'
                    }`}
              </button>
            </div>
          </form>
        </div>

        {LANDING_PAGE_FEATURES_ENABLED ? (
          <>
        <div className="mt-6 rounded-xl bg-white p-6 shadow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-emerald-600">
                Upload de assets fotograficos
              </p>
              <h2 className="mt-2 text-2xl font-bold text-gray-900">
                Anexar imagens reais do cliente
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-gray-600">
                Envie uma imagem por vez, definindo a categoria correta para que
                historias futuras possam reutilizar esse asset no HTML gerado.
              </p>
            </div>
            <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600">
              JPG, PNG ou WebP
            </div>
          </div>

          <form onSubmit={handleImageUpload} className="mt-6 space-y-5">
            <div className="grid gap-5 md:grid-cols-[220px_1fr]">
              <div>
                <label
                  htmlFor="asset-category"
                  className="block text-sm font-medium text-gray-700"
                >
                  Categoria do asset
                </label>
                <select
                  id="asset-category"
                  value={selectedImageCategory}
                  onChange={(event) => {
                    setSelectedImageCategory(event.target.value as AssetCategory | '');
                    setImageErrorMessage('');
                    setImageSuccessMessage('');
                    setUploadedImageAsset(null);
                  }}
                  className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700"
                >
                  <option value="">Selecione uma categoria</option>
                  {IMAGE_CATEGORY_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-xs text-gray-500">
                  Hero, perfil, ambiente ou tratamento.
                </p>
              </div>

              <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5">
                <label className="block text-sm font-medium text-gray-700">
                  Arquivo da imagem
                </label>
                <input
                  ref={imageFileInputRef}
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp,.heic,.heif,image/jpeg,image/png,image/webp,image/heic,image/heif"
                  onChange={handleImageFileChange}
                  className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-emerald-600 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-emerald-700"
                />
                <p className="mt-2 text-xs text-gray-500">
                  Formatos aceitos: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic` e
                  `.heif`. Limite: 50MB por arquivo.
                </p>

                {selectedImageFile ? (
                  <div className="mt-4 flex items-center justify-between rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
                    <div className="flex items-center gap-3">
                      <FileText className="h-4 w-4" />
                      <div>
                        <p className="font-medium">{selectedImageFile.name}</p>
                        <p className="text-xs text-emerald-700">
                          {formatFileSize(selectedImageFile.size)}
                        </p>
                      </div>
                    </div>
                    <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold uppercase text-emerald-700">
                      pronto
                    </span>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-4">
              {IMAGE_CATEGORY_OPTIONS.map((option) => (
                <div
                  key={option.value}
                  className={`rounded-lg border px-4 py-3 text-sm ${
                    selectedImageCategory === option.value
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-900'
                      : 'border-gray-200 bg-gray-50 text-gray-600'
                  }`}
                >
                  <p className="font-semibold">{option.label}</p>
                  <p className="mt-1 text-xs">{option.description}</p>
                </div>
              ))}
            </div>

            {imageErrorMessage ? (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                {imageErrorMessage}
              </div>
            ) : null}

            {imageSuccessMessage ? (
              <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
                {imageSuccessMessage}
              </div>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-gray-500">
                Nesta historia o MVP confirma os metadados do asset e a URL estavel
                retornada pelo backend, sem exigir preview remoto da imagem.
              </p>
              <button
                type="submit"
                disabled={isUploadingImage || !selectedImageFile || !selectedImageCategory}
                className="inline-flex items-center justify-center rounded-md border border-transparent bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
              >
                <Upload className="mr-2 h-4 w-4" />
                {isUploadingImage ? 'Enviando asset...' : 'Enviar Asset Fotografico'}
              </button>
            </div>
          </form>
        </div>

        <div className="mt-6 rounded-xl bg-white p-6 shadow">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-amber-600">
                Matriz de tracking CTA
              </p>
              <h2 className="mt-2 text-2xl font-bold text-gray-900">
                Configurar botoes da landing page
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-gray-600">
                Cadastre os botoes que o futuro HTML vai renderizar com IDs CSS
                consistentes para Tag Manager, tracking sheet e mapeamento de
                conversoes.
              </p>
            </div>
            <div className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
              Nome, texto e ID CSS
            </div>
          </div>

          <form onSubmit={handleCtaButtonSubmit} className="mt-6 space-y-5">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label
                  htmlFor="cta-name"
                  className="block text-sm font-medium text-gray-700"
                >
                  Nome do botao
                </label>
                <input
                  id="cta-name"
                  type="text"
                  value={ctaName}
                  onChange={(event) => {
                    setCtaName(event.target.value);
                    setCtaErrorMessage('');
                    setCtaSuccessMessage('');
                  }}
                  placeholder="Ex: Botao Hero WhatsApp"
                  className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700"
                />
              </div>

              <div>
                <label
                  htmlFor="cta-button-text"
                  className="block text-sm font-medium text-gray-700"
                >
                  Texto do botao
                </label>
                <input
                  id="cta-button-text"
                  type="text"
                  value={ctaButtonText}
                  onChange={(event) => {
                    setCtaButtonText(event.target.value);
                    setCtaErrorMessage('');
                    setCtaSuccessMessage('');
                  }}
                  placeholder="Ex: Falar no WhatsApp"
                  className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700"
                />
              </div>

              <div>
                <label
                  htmlFor="cta-css-id"
                  className="block text-sm font-medium text-gray-700"
                >
                  ID CSS
                </label>
                <input
                  id="cta-css-id"
                  type="text"
                  value={ctaCssId}
                  onChange={(event) => {
                    setCtaCssId(event.target.value);
                    setCtaErrorMessage('');
                    setCtaSuccessMessage('');
                  }}
                  placeholder="Ex: btn-whatsapp-hero"
                  className="mt-3 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-sm text-gray-700"
                />
                <p className="mt-2 text-xs text-gray-500">
                  Use apenas letras minusculas, numeros, `-` ou `_`, sempre
                  comecando por letra.
                </p>
              </div>
            </div>

            {ctaErrorMessage ? (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                {ctaErrorMessage}
              </div>
            ) : null}

            {ctaSuccessMessage ? (
              <div className="rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
                {ctaSuccessMessage}
              </div>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-gray-500">
                O cadastro fica persistido por onboarding para ser reutilizado
                depois no HTML final e no tracking sheet.
              </p>
              <button
                type="submit"
                disabled={isSavingCtaButton}
                className="inline-flex items-center justify-center rounded-md border border-transparent bg-amber-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-amber-700 disabled:cursor-not-allowed disabled:bg-amber-300"
              >
                <MousePointerClick className="mr-2 h-4 w-4" />
                {isSavingCtaButton ? 'Salvando botao...' : 'Salvar Botao CTA'}
              </button>
            </div>
          </form>

          <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-gray-900">
                  Botoes cadastrados
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  Esta matriz sera a base do mapeamento futuro de tracking da
                  landing page.
                </p>
              </div>
              <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-600">
                {ctaButtons.length} item{ctaButtons.length === 1 ? '' : 's'}
              </span>
            </div>

            {ctaLoadErrorMessage ? (
              <div className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
                {ctaLoadErrorMessage}
              </div>
            ) : null}

            {isLoadingCtaButtons ? (
              <div className="mt-4 rounded-md bg-white px-4 py-3 text-sm text-gray-600">
                Carregando matriz CTA...
              </div>
            ) : null}

            {!isLoadingCtaButtons &&
            !ctaLoadErrorMessage &&
            ctaButtons.length === 0 ? (
              <div className="mt-4 rounded-md border border-dashed border-gray-300 bg-white px-4 py-5 text-sm text-gray-600">
                Nenhum botao CTA cadastrado ainda para este onboarding.
              </div>
            ) : null}

            {!isLoadingCtaButtons && ctaButtons.length > 0 ? (
              <div className="mt-4 overflow-x-auto rounded-lg border border-gray-200 bg-white">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Nome</th>
                      <th className="px-4 py-3">Texto</th>
                      <th className="px-4 py-3">ID CSS</th>
                      <th className="px-4 py-3">Criado em</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 text-gray-700">
                    {ctaButtons.map((button) => (
                      <tr key={button.id}>
                        <td className="px-4 py-3 font-medium text-gray-900">
                          {button.name}
                        </td>
                        <td className="px-4 py-3">{button.button_text}</td>
                        <td className="px-4 py-3">
                          <span className="rounded bg-amber-50 px-2 py-1 font-mono text-xs text-amber-800">
                            {button.css_id}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {new Date(button.created_at).toLocaleString('pt-BR')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        </div>

          </>
        ) : null}

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-gray-600">
                Arquivos anexados
              </p>
              <h3 className="mt-1 text-lg font-semibold text-gray-900">
                {isLoadingAssets
                  ? 'Carregando arquivos salvos...'
                  : `${onboardingAssets.length} arquivo${
                      onboardingAssets.length === 1 ? '' : 's'
                    } salvo${onboardingAssets.length === 1 ? '' : 's'}`}
              </h3>
              <p className="mt-2 text-sm text-gray-600">
                Esta lista vem do backend e continua aparecendo depois de recarregar
                a pagina.
              </p>
            </div>

            {uploadedAssets.length > 0 || uploadedImageAsset ? (
              <span className="inline-flex items-center rounded-full bg-green-50 px-3 py-1 text-xs font-semibold uppercase text-green-700">
                <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                Upload recente
              </span>
            ) : null}
          </div>

          {assetLoadErrorMessage ? (
            <div className="mt-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
              {assetLoadErrorMessage}
            </div>
          ) : null}

          {!isLoadingAssets && onboardingAssets.length === 0 ? (
            <div className="mt-4 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-6 text-sm text-gray-600">
              Nenhum arquivo salvo neste onboarding ainda.
            </div>
          ) : null}

          {documentAssets.length > 0 ? (
            <div className="mt-5">
              <p className="text-sm font-semibold text-gray-900">
                Documentos e transcricoes
              </p>
              <div className="mt-3 space-y-3 text-sm text-gray-700">
                {documentAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3"
                  >
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                      <p className="font-medium text-gray-900">
                        {asset.original_filename}
                      </p>
                      <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-gray-600">
                        {getAssetKindLabel(asset)}
                      </span>
                    </div>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <p>Tipo: {asset.content_type}</p>
                      <p>Tamanho: {formatFileSize(asset.size_bytes)}</p>
                      <p>Onboarding: #{asset.onboarding_id}</p>
                      <p>
                        Enviado em:{' '}
                        {new Date(asset.created_at).toLocaleString('pt-BR')}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {LANDING_PAGE_FEATURES_ENABLED && imageAssets.length > 0 ? (
            <div className="mt-5">
              <p className="text-sm font-semibold text-gray-900">
                Assets fotograficos
              </p>
              <div className="mt-3 space-y-3 text-sm text-gray-700">
                {imageAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className="rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-3"
                  >
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                      <p className="font-medium text-gray-900">
                        {asset.original_filename}
                      </p>
                      <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-emerald-700">
                        {getAssetKindLabel(asset)}
                      </span>
                    </div>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <p>Tipo: {asset.content_type}</p>
                      <p>Tamanho: {formatFileSize(asset.size_bytes)}</p>
                      <p>Onboarding: #{asset.onboarding_id}</p>
                      <p>
                        Enviado em:{' '}
                        {new Date(asset.created_at).toLocaleString('pt-BR')}
                      </p>
                      {asset.storage_url ? (
                        <p className="md:col-span-2">
                          URL estavel:{' '}
                          <span className="break-all font-mono text-xs">
                            {asset.storage_url}
                          </span>
                        </p>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {LANDING_PAGE_FEATURES_ENABLED && uploadedImageAsset ? (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-700" />
              <div className="min-w-0">
                <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
                  Asset fotografico confirmado
                </p>
                <h3 className="mt-1 text-lg font-semibold text-gray-900">
                  {uploadedImageAsset.original_filename}
                </h3>
                <div className="mt-3 grid gap-3 text-sm text-gray-700 md:grid-cols-2">
                  <p>
                    Categoria:{' '}
                    {getAssetCategoryLabel(uploadedImageAsset.asset_category)}
                  </p>
                  <p>Tipo: {uploadedImageAsset.content_type}</p>
                  <p>Tamanho: {formatFileSize(uploadedImageAsset.size_bytes)}</p>
                  <p>Onboarding: #{uploadedImageAsset.onboarding_id}</p>
                  <p className="md:col-span-2">
                    URL estavel:{' '}
                    <span className="break-all font-mono text-xs">
                      {uploadedImageAsset.storage_url ?? 'Nao informada'}
                    </span>
                  </p>
                  <p>
                    Enviado em:{' '}
                    {new Date(uploadedImageAsset.created_at).toLocaleString('pt-BR')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
