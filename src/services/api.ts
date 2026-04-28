// ATLAS API Service
// =================
// Axios instance with interceptors for auth and error handling

import axios, { AxiosError, AxiosInstance } from 'axios';
import { BACKEND_URL, API_TIMEOUT } from '../config';

const USER_ID = 'default_user';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: BACKEND_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    'x-user-id': USER_ID,
  },
});

// Request interceptor - add auth headers
api.interceptors.request.use(
  (config) => {
    // Add user ID header
    config.headers['x-user-id'] = USER_ID;
    
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
      console.warn('[API] Unauthorized - check credentials');
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
