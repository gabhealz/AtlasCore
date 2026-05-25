import { api } from './api';
import type { ClientDashboard, OpsDashboardEnvelope } from '../types/ops';

export async function fetchOpsDashboard(): Promise<ClientDashboard[]> {
  const response = await api.get<OpsDashboardEnvelope>('/ops/dashboard');
  return response.data.data;
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
