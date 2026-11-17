import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  private instance: AxiosInstance;
  private connectionId: string | null = null;
  private accessToken: string | null = null;

  constructor() {
    this.instance = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.instance.interceptors.request.use(
      (config) => {
        if (this.connectionId) {
          config.headers['X-Connection-ID'] = this.connectionId;
        }
        if (this.accessToken) {
          config.headers['Authorization'] = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.instance.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  setConnectionId(id: string | null) {
    this.connectionId = id;
  }

  getConnectionId(): string | null {
    return this.connectionId;
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  async downloadCsv(connectionId: string, payload: { sql: string; filename?: string }) {
    const response = await this.instance.post(
      `/export/csv/${connectionId}`,
      payload,
      {
        responseType: 'blob',
      }
    );

    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = payload.filename || `export_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  get axiosInstance() {
    return this.instance;
  }
}

export const apiClient = new ApiClient();
export const api = apiClient.axiosInstance;
