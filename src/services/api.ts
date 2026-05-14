// ATLAS API Service
// =================
// Axios instance with interceptors for auth (JWT Bearer token) and error handling

import axios, { AxiosError, AxiosInstance } from 'axios';
import { BACKEND_URL, API_TIMEOUT, getAuthToken, clearAuthToken } from '../config';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: BACKEND_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add JWT Bearer token
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Log in development
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.code === 'ECONNABORTED') {
      console.warn('[API] Request timeout');
      return Promise.reject(new Error('Request timeout - server may be unavailable'));
    }
    
    if (error.response?.status === 401) {
      console.warn('[API] Unauthorized - token may be expired. Use /auth/jwt/login to get a new one.');
      clearAuthToken();
    }
    
    if (error.response?.status === 429) {
      console.warn('[API] Rate limited');
    }
    
    if (!error.response) {
      console.error('[API] Network error - backend unreachable');
    }
    
    return Promise.reject(error);
  }
);

// Helper functions
export const getData = <T>(url: string, params?: Record<string, any>) => 
  api.get<T>(url, { params }).then(r => r.data);

export const postData = <T>(url: string, data?: any) => 
  api.post<T>(url, data).then(r => r.data);

export const putData = <T>(url: string, data?: any) => 
  api.put<T>(url, data).then(r => r.data);

export const deleteData = <T>(url: string) => 
  api.delete<T>(url).then(r => r.data);

export default api;
