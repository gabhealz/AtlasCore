import React, { useState } from 'react';
import { api } from '../../lib/api';
import { useNavigate } from 'react-router-dom';
import { Loader2, UserPlus, AlertCircle } from 'lucide-react';
import type { AxiosError } from 'axios';

interface Props {
  onboardingId: number;
}

export function ClientConversionForm({ onboardingId }: Props) {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    email: '',
    phone: '',
    city: '',
    state: '',
    monthly_fee: ''
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      const response = await api.post(`/onboardings/${onboardingId}/activate_client`, {
        ...formData,
        monthly_fee: parseFloat(formData.monthly_fee.replace(',', '.')) || 0
      });
      
      const clientId = response.data.client_id;
      // Navigate to the ops dashboard detail page for this client
      navigate(`/ops/${clientId}`);
    } catch (err) {
      const axiosError = err as AxiosError<any>;
      setError(axiosError.response?.data?.detail?.message || 'Ocorreu um erro ao ativar o cliente.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white p-8 rounded-xl shadow-sm border border-brand/10 max-w-2xl mx-auto my-12">
      <div className="text-center mb-8">
        <div className="mx-auto w-16 h-16 bg-brand/10 rounded-full flex items-center justify-center mb-4">
          <UserPlus className="h-8 w-8 text-brand" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Onboarding Finalizado! 🎉</h2>
        <p className="mt-2 text-gray-600">
          A IA concluiu todas as etapas. Para ativar este cliente no Ops Dashboard e liberar a integração com as plataformas de anúncios, preencha os dados finais de contato e faturamento abaixo.
        </p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3">
          <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="col-span-2">
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email de Contato</label>
            <input
              type="email"
              name="email"
              id="email"
              required
              value={formData.email}
              onChange={handleChange}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-brand focus:ring-brand sm:text-sm p-2.5 border"
              placeholder="medico@clinica.com.br"
            />
          </div>

          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700">Celular / WhatsApp</label>
            <input
              type="text"
              name="phone"
              id="phone"
              required
              value={formData.phone}
              onChange={handleChange}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-brand focus:ring-brand sm:text-sm p-2.5 border"
              placeholder="(11) 99999-9999"
            />
          </div>

          <div>
            <label htmlFor="monthly_fee" className="block text-sm font-medium text-gray-700">Mensalidade (R$)</label>
            <div className="mt-1 relative rounded-md shadow-sm">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span className="text-gray-500 sm:text-sm">R$</span>
              </div>
              <input
                type="number"
                step="0.01"
                name="monthly_fee"
                id="monthly_fee"
                required
                value={formData.monthly_fee}
                onChange={handleChange}
                className="pl-9 block w-full rounded-md border-gray-300 shadow-sm focus:border-brand focus:ring-brand sm:text-sm p-2.5 border"
                placeholder="2500.00"
              />
            </div>
          </div>

          <div>
            <label htmlFor="city" className="block text-sm font-medium text-gray-700">Cidade</label>
            <input
              type="text"
              name="city"
              id="city"
              required
              value={formData.city}
              onChange={handleChange}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-brand focus:ring-brand sm:text-sm p-2.5 border"
              placeholder="São Paulo"
            />
          </div>

          <div>
            <label htmlFor="state" className="block text-sm font-medium text-gray-700">Estado (UF)</label>
            <input
              type="text"
              name="state"
              id="state"
              required
              maxLength={2}
              value={formData.state}
              onChange={handleChange}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-brand focus:ring-brand sm:text-sm p-2.5 border uppercase"
              placeholder="SP"
            />
          </div>
        </div>

        <div className="pt-4 border-t border-gray-100">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex justify-center items-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand hover:bg-brand-soft focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="animate-spin -ml-1 mr-2 h-5 w-5" />
                Ativando Cliente...
              </>
            ) : (
              'Ativar Cliente e Ir para Dashboard'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
