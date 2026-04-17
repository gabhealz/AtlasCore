const API_BASE = 'http://localhost:8000/api';

interface RequestOptions {
  method?: string;
  body?: any;
  headers?: Record<string, string>;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('atlas_token', token);
    } else {
      localStorage.removeItem('atlas_token');
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('atlas_token');
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, headers = {} } = options;
    const token = this.getToken();

    const config: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
    };

    if (body) {
      config.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, config);

    if (response.status === 401) {
      this.setToken(null);
      window.location.href = '/login';
      throw new Error('Não autorizado');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
      throw new Error(error.detail || `Erro ${response.status}`);
    }

    if (response.status === 204) return {} as T;
    return response.json();
  }

  // Auth
  async register(email: string, password: string, fullName: string) {
    return this.request<{ access_token: string; user: any }>('/auth/register', {
      method: 'POST',
      body: { email, password, full_name: fullName },
    });
  }

  async login(email: string, password: string) {
    return this.request<{ access_token: string; user: any }>('/auth/login', {
      method: 'POST',
      body: { email, password },
    });
  }

  // Clients
  async getClients() {
    return this.request<any[]>('/clients/');
  }

  async getClient(id: string) {
    return this.request<any>(`/clients/${id}`);
  }

  async createClient(data: any) {
    return this.request<any>('/clients/', { method: 'POST', body: data });
  }

  async updateClient(id: string, data: any) {
    return this.request<any>(`/clients/${id}`, { method: 'PATCH', body: data });
  }

  async deleteClient(id: string) {
    return this.request<void>(`/clients/${id}`, { method: 'DELETE' });
  }

  // Transcripts
  async getTranscripts(clientId: string) {
    return this.request<any[]>(`/clients/${clientId}/transcripts/`);
  }

  async createTranscript(clientId: string, data: { title: string; source?: string; raw_text: string }) {
    return this.request<any>(`/clients/${clientId}/transcripts/`, { method: 'POST', body: data });
  }

  async uploadTranscript(clientId: string, file: File, title: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('source', 'upload');

    const token = this.getToken();
    const response = await fetch(`${API_BASE}/clients/${clientId}/transcripts/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Erro no upload' }));
      throw new Error(error.detail || 'Erro no upload');
    }

    return response.json();
  }

  async deleteTranscript(clientId: string, transcriptId: string) {
    return this.request<void>(`/clients/${clientId}/transcripts/${transcriptId}`, { method: 'DELETE' });
  }

  // Benchmarks
  async getBenchmarks(clientId: string) {
    return this.request<any[]>(`/clients/${clientId}/benchmarks/`);
  }

  async getBenchmark(clientId: string, benchmarkId: string) {
    return this.request<any>(`/clients/${clientId}/benchmarks/${benchmarkId}`);
  }

  async generateBenchmark(clientId: string) {
    return this.request<any>(`/clients/${clientId}/benchmarks/generate`, { method: 'POST' });
  }

  async approveBenchmark(clientId: string, benchmarkId: string, approved: boolean, notes?: string) {
    return this.request<any>(`/clients/${clientId}/benchmarks/${benchmarkId}/approve`, {
      method: 'POST',
      body: { approved, notes },
    });
  }
}

export const api = new ApiClient();
