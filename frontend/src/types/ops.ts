export interface Client {
  id: number;
  /** Onboarding de origem — link para ver os entregáveis salvos do projeto. */
  onboarding_id?: number | null;
  name: string;
  specialty?: string;
  city?: string;
  state?: string;
  phone?: string;
  email?: string;
  monthly_fee: number;
  plan_name?: string;
  external_code?: string;
  document?: string;
  contract_start_date?: string;
  contract_end_date?: string;
  /** Dias desde o início do contrato (tempo de casa) — calculado no backend. */
  tenure_days?: number;
  /** Meses completos de casa — usado para LTV. */
  tenure_months?: number;
  meta_account_id?: string;
  google_account_id?: string;
  ga4_property_id?: string;
  ga4_measurement_id?: string;
  tintim_id?: string;
  active_platforms: string;
  is_active: boolean;
  is_draft?: boolean;
  created_at: string;
  updated_at: string;
}

export interface MetricSnapshot {
  id: number;
  client_id: number;
  week_start: string;
  date?: string;
  source: string;
  impressions?: number;
  clicks?: number;
  ctr?: number;
  cpc?: number;
  ad_spend?: number;
  conversions?: number;
  cost_per_conversion?: number;
  lp_to_whatsapp_rate?: number;
  whatsapp_to_booking_rate?: number;
  lp_sessions?: number;
  revenue?: number;
  bookings?: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignSnapshot {
  id: number;
  client_id: number;
  week_start: string;
  platform: string;
  campaign_id: string;
  campaign_name: string;
  impressions?: number;
  clicks?: number;
  ctr?: number;
  cpc?: number;
  spend?: number;
  conversions?: number;
  created_at: string;
}

export interface ClientDashboard {
  client: Client;
  current_week?: MetricSnapshot;
  previous_week?: MetricSnapshot;
  roi?: number;
  roas?: number;
  roi_change_pct?: number;
  revenue_change_pct?: number;
  bookings_change_pct?: number;
  health_status: 'green' | 'yellow' | 'red';
  weekly_history: MetricSnapshot[];
  campaigns: CampaignSnapshot[];
}

export interface OpsDashboardEnvelope {
  data: ClientDashboard[];
}

export interface ClientDashboardEnvelope {
  data: ClientDashboard;
}
