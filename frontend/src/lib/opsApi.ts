import { api } from './api';
import type { Client, ClientDashboard, OpsDashboardEnvelope } from '../types/ops';

export async function fetchOpsDashboard(): Promise<ClientDashboard[]> {
  const response = await api.get<OpsDashboardEnvelope>('/ops/dashboard');
  return response.data.data;
}

// --- Clients API ---

export interface ClientCreateInput {
  name: string;
  monthly_fee: number;
  plan_name?: string;
  specialty?: string;
  city?: string;
  state?: string;
  phone?: string;
  email?: string;
  document?: string;
  contract_start_date?: string;
  contract_end_date?: string;
}

export async function createClient(data: ClientCreateInput): Promise<Client> {
  const response = await api.post<{ data: Client }>('/clients', data);
  return response.data.data;
}

export interface ClientUpdateInput extends Partial<ClientCreateInput> {
  is_active?: boolean;
  is_draft?: boolean;
}

export async function updateClient(clientId: number, data: ClientUpdateInput): Promise<Client> {
  const response = await api.patch<{ data: Client }>(`/clients/${clientId}`, data);
  return response.data.data;
}

// --- Lançamento manual de métricas (faturamento/agendamentos da secretária) ---

export interface ManualSnapshotInput {
  week_start: string; // YYYY-MM-DD (segunda-feira)
  source?: string;    // default "manual"
  revenue?: number;
  bookings?: number;
  conversions?: number;
  impressions?: number;
  clicks?: number;
  ad_spend?: number;
}

export async function upsertSnapshot(clientId: number, data: ManualSnapshotInput): Promise<void> {
  await api.post(`/ops/clients/${clientId}/snapshots`, {
    client_id: clientId,
    source: 'manual',
    ...data,
  });
}

export async function fetchClientDashboard(clientId: number): Promise<ClientDashboard> {
  // P09 fix: endpoint now returns the object directly (no envelope)
  const response = await api.get<ClientDashboard>(`/ops/clients/${clientId}/dashboard`);
  return response.data;
}

// --- Integration Settings API ---

export interface IntegrationSetting {
  id: number;
  client_id: number;
  platform: 'meta' | 'google' | 'ga4' | 'tintim';
  account_id: string | null;
  is_active: boolean;
  has_access_token: boolean;
  has_refresh_token: boolean;
  token_expires_at: string | null;
  last_sync_at: string | null;
  sync_status: string;
  created_at: string;
  updated_at: string;
}

export interface IntegrationTestResult {
  platform: string;
  success: boolean;
  message: string;
}

export async function fetchIntegrations(clientId: number): Promise<IntegrationSetting[]> {
  const response = await api.get<{ data: IntegrationSetting[] }>(`/ops/clients/${clientId}/integrations`);
  return response.data.data;
}

export async function createIntegration(
  clientId: number,
  data: { platform: string; account_id?: string; access_token?: string; refresh_token?: string }
): Promise<IntegrationSetting> {
  const response = await api.post<{ data: IntegrationSetting }>(`/ops/clients/${clientId}/integrations`, data);
  return response.data.data;
}

export async function updateIntegration(
  clientId: number,
  platform: string,
  data: { account_id?: string; access_token?: string; refresh_token?: string; is_active?: boolean }
): Promise<IntegrationSetting> {
  const response = await api.patch<{ data: IntegrationSetting }>(`/ops/clients/${clientId}/integrations/${platform}`, data);
  return response.data.data;
}

export async function deleteIntegration(clientId: number, platform: string): Promise<void> {
  await api.delete(`/ops/clients/${clientId}/integrations/${platform}`);
}

export async function testIntegration(clientId: number, platform: string): Promise<IntegrationTestResult> {
  const response = await api.post<IntegrationTestResult>(`/ops/clients/${clientId}/integrations/${platform}/test`);
  return response.data;
}
