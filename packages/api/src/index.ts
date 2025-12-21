import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

type ApiOptions = {
  baseURL?: string;
  apiKey?: string;
  axiosConfig?: AxiosRequestConfig;
};

const DEFAULT_BASE =
  process.env.EXPO_PUBLIC_API_BASE_URL ??
  process.env.EXPO_PUBLIC_API_BASE ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE ??
  process.env.API_BASE_URL ??
  process.env.API_BASE ??
  'http://localhost:8000';

const DEFAULT_KEY =
  process.env.EXPO_PUBLIC_API_KEY ??
  process.env.NEXT_PUBLIC_API_KEY ??
  process.env.API_KEY ??
  '';

const defaultHeaders = DEFAULT_KEY
  ? {
      'X-API-Key': DEFAULT_KEY
    }
  : undefined;

export const api: AxiosInstance = axios.create({
  baseURL: DEFAULT_BASE,
  headers: defaultHeaders,
});

export function createApi(options: ApiOptions = {}): AxiosInstance {
  const { baseURL = DEFAULT_BASE, apiKey = DEFAULT_KEY, axiosConfig = {} } = options;
  return axios.create({
    baseURL,
    headers: apiKey
      ? {
          'X-API-Key': apiKey,
          ...(axiosConfig.headers ?? {})
        }
      : axiosConfig.headers,
    ...axiosConfig,
  });
}

export type { AxiosInstance, AxiosRequestConfig } from 'axios';
