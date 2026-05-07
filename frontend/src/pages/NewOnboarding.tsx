import type { AxiosError } from 'axios';
import { ArrowLeft, FileUp, Save } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../lib/api';

type OnboardingFormData = {
  doctor_name: string;
};

type FormErrors = Partial<Record<keyof OnboardingFormData, string>>;

type ApiValidationDetail = {
  loc?: Array<string | number>;
  msg?: string;
};

type ApiErrorResponse = {
  detail?: ApiValidationDetail[] | { message?: string };
};

const FIELD_LABELS: Record<keyof OnboardingFormData, string> = {
  doctor_name: 'Nome do medico',
};

const INITIAL_FORM_DATA: OnboardingFormData = {
  doctor_name: '',
};

function validateForm(values: OnboardingFormData): FormErrors {
  const nextErrors: FormErrors = {};

  if (!values.doctor_name.trim()) {
    nextErrors.doctor_name = `${FIELD_LABELS.doctor_name} e obrigatorio.`;
  }

  return nextErrors;
}

function parseApiValidationErrors(detail?: ApiErrorResponse['detail']): FormErrors {
  if (!Array.isArray(detail)) {
    return {};
  }

  const nextErrors: FormErrors = {};

  for (const issue of detail) {
    const field = issue.loc?.[1];
    if (typeof field === 'string' && field in FIELD_LABELS) {
      nextErrors[field as keyof OnboardingFormData] = issue.msg ?? 'Campo invalido.';
    }
  }

  return nextErrors;
}

export default function NewOnboarding() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<OnboardingFormData>(INITIAL_FORM_DATA);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange =
    (field: keyof OnboardingFormData) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setFormData((current) => ({
        ...current,
        [field]: event.target.value,
      }));

      setErrors((current) => {
        if (!current[field]) {
          return current;
        }

        const nextErrors = { ...current };
        delete nextErrors[field];
        return nextErrors;
      });
    };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const validationErrors = validateForm(formData);
    setErrors(validationErrors);
    setSubmitError('');

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await api.post('/onboardings', {
        doctor_name: formData.doctor_name,
      });
      navigate(`/onboarding/${response.data.data.id}`, {
        state: {
          justCreated: true,
          onboardingStatus: response.data.data.status,
        },
      });
    } catch (error) {
      const axiosError = error as AxiosError<ApiErrorResponse>;
      const apiErrors = parseApiValidationErrors(axiosError.response?.data?.detail);

      if (Object.keys(apiErrors).length > 0) {
        setErrors(apiErrors);
        setSubmitError('Revise os campos destacados e tente novamente.');
      } else {
        const detail = axiosError.response?.data?.detail;
        const fallbackMessage =
          !Array.isArray(detail) && detail?.message
            ? detail.message
            : 'Nao foi possivel criar o projeto.';
        setSubmitError(fallbackMessage);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-4xl">
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          className="mb-6 flex items-center text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Voltar para Dashboard
        </button>

        <div className="mb-6 rounded-xl bg-white p-6 shadow">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">
            Novo onboarding
          </p>
          <h1 className="mt-2 text-3xl font-bold text-gray-900">
            Criar projeto vazio
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-gray-600">
            Informe apenas o nome do medico para abrir o onboarding. Na proxima
            tela, anexe transcricoes e documentos para a IA extrair os dados do
            cliente e pedir somente o que estiver faltando.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-xl bg-white p-6 shadow">
          <div className="grid gap-5">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Nome do medico
              </label>
              <input
                type="text"
                value={formData.doctor_name}
                onChange={handleChange('doctor_name')}
                className={`mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:outline-none focus:ring-1 ${
                  errors.doctor_name
                    ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                    : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                }`}
                placeholder="Ex: Dra. Ana Silva"
              />
              {errors.doctor_name ? (
                <p className="mt-1 text-sm text-red-600">{errors.doctor_name}</p>
              ) : null}
            </div>

            <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-800">
              <div className="flex items-start gap-3">
                <FileUp className="mt-0.5 h-4 w-4 shrink-0" />
                <p>
                  Depois de criar, envie briefing, transcricoes, prints, links ou
                  documentos. A esteira de IA vai preencher o maximo possivel e
                  apontar as pendencias.
                </p>
              </div>
            </div>
          </div>

          {submitError ? (
            <div className="mt-5 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">
              {submitError}
            </div>
          ) : null}

          <div className="mt-6 flex flex-col gap-3 border-t border-gray-200 pt-5 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            >
              <Save className="mr-2 h-4 w-4" />
              {isSubmitting ? 'Criando projeto...' : 'Criar Projeto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
