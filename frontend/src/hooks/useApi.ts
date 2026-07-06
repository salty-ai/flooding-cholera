import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import type {
  LGA,
  GeoJSONFeatureCollection,
  RiskScore,
  DashboardSummary,
  LGAAnalytics,
  UploadResponse,
  SatelliteStatus,
  SatelliteData,
  Alert,
  WeeklySummary,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
});

// Query keys for cache management
export const queryKeys = {
  lgas: ['lgas'] as const,
  lgasSearch: (search: string) => ['lgas', 'search', search] as const,
  lga: (id: number) => ['lgas', id] as const,
  lgaCases: (id: number) => ['lgas', id, 'cases'] as const,
  geojson: ['geojson'] as const,
  dashboard: ['dashboard'] as const,
  lgaAnalytics: (id: number, days: number) => ['analytics', 'lga', id, days] as const,
  riskScores: ['riskScores'] as const,
  satelliteStatus: ['satellite', 'status'] as const,
  satelliteLatest: ['satellite', 'latest'] as const,
  satelliteThumbnail: (id: number) => ['satellite', 'thumbnail', id] as const,
  alerts: ['alerts'] as const,
};

// API functions
export const apiService = {
  // LGAs
  getLgas: async (search?: string): Promise<{ total: number; lgas: LGA[] }> => {
    const params = search ? { search } : {};
    const response = await api.get('/lgas', { params });
    return response.data;
  },

  getLgasGeojson: async (date?: string): Promise<GeoJSONFeatureCollection> => {
    const params = date ? { date } : {};
    const response = await api.get('/lgas/geojson', { params });
    return response.data;
  },

  getLga: async (id: number): Promise<LGA> => {
    const response = await api.get(`/lgas/${id}`);
    return response.data;
  },

  getLgaCases: async (id: number): Promise<{ id: number; date: string; new_cases: number; deaths: number }[]> => {
    const response = await api.get(`/lgas/${id}/cases`);
    return response.data;
  },

  // Dashboard
  getDashboardSummary: async (): Promise<DashboardSummary> => {
    const response = await api.get('/lgas/dashboard');
    return response.data;
  },

  // Analytics
  getLgaAnalytics: async (id: number, days: number = 90): Promise<LGAAnalytics> => {
    const response = await api.get(`/analytics/lga/${id}`, { params: { days } });
    return response.data;
  },

  getAllRiskScores: async (): Promise<RiskScore[]> => {
    const response = await api.get('/analytics/risk-scores');
    return response.data;
  },

  getWeeklySummary: async (weeks: number = 12): Promise<WeeklySummary> => {
    const response = await api.get('/analytics/summary/weekly', { params: { weeks } });
    return response.data;
  },

  getCorrelation: async (params: { lga_id?: number; state?: string; from_year: number; to_year: number }) => {
    const response = await api.get('/analytics/correlation', { params });
    return response.data;
  },

  // Risk calculation
  calculateRisks: async (): Promise<{ success: boolean; results: unknown[] }> => {
    const response = await api.post('/risk-scores/calculate');
    return response.data;
  },

  // Upload
  uploadData: async (file: File, dataType: 'cases' | 'environmental'): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('data_type', dataType);

    const response = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getUploadTemplate: async (dataType: 'cases' | 'environmental'): Promise<Blob> => {
    const response = await api.get(`/upload/template/${dataType}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Satellite
  getSatelliteStatus: async (): Promise<SatelliteStatus> => {
    const response = await api.get('/satellite/status');
    return response.data;
  },

  getLatestSatelliteData: async (): Promise<SatelliteData[]> => {
    const response = await api.get('/satellite/latest');
    return response.data;
  },

  getSatelliteThumbnail: async (lgaId: number): Promise<{ url: string }> => {
    const response = await api.get(`/satellite/thumbnail/${lgaId}`);
    return response.data;
  },

  // Alerts - fetches from backend alerts endpoint
  getAlerts: async (filters?: { severity?: string; is_acknowledged?: boolean; lga_id?: number }): Promise<Alert[]> => {
    try {
      const params = { is_active: true, ...filters };
      const response = await api.get('/alerts', { params });
      const alertsData = response.data.alerts || response.data || [];

      // Transform backend format to frontend format
      return alertsData.map((alert: {
        id: number;
        type: string;
        severity: string;
        title: string;
        message: string;
        lga_id?: number;
        lga_name?: string;
        created_at: string;
        acknowledged_at?: string;
      }) => ({
        id: String(alert.id),
        type: alert.type,
        severity: alert.severity as 'critical' | 'warning' | 'info',
        title: alert.title,
        message: alert.message,
        lga_id: alert.lga_id,
        lga_name: alert.lga_name,
        created_at: alert.created_at,
        read: !!alert.acknowledged_at,
      }));
    } catch {
      // Fallback to risk-score derived alerts if backend endpoint fails
      try {
        const response = await api.get('/analytics/risk-scores');
        const scores: RiskScore[] = response.data;
        const alerts: Alert[] = [];

        scores.forEach((score) => {
          if (score.level === 'red') {
            alerts.push({
              id: `high-risk-${score.lga_id}`,
              type: 'high_risk',
              severity: 'critical',
              title: `High Risk Alert: ${score.lga_name || 'Unknown LGA'}`,
              message: `${score.lga_name} is currently at high cholera risk level (Score: ${(score.score * 100).toFixed(0)}%)`,
              lga_id: score.lga_id,
              lga_name: score.lga_name,
              created_at: score.calculated_at,
              read: false,
            });
          } else if (score.level === 'yellow' && score.recent_cases && score.recent_cases > 5) {
            alerts.push({
              id: `elevated-cases-${score.lga_id}`,
              type: 'case_spike',
              severity: 'warning',
              title: `Case Increase: ${score.lga_name || 'Unknown LGA'}`,
              message: `${score.recent_cases} cases reported in ${score.lga_name} over the past 30 days`,
              lga_id: score.lga_id,
              lga_name: score.lga_name,
              created_at: score.calculated_at,
              read: false,
            });
          }
        });

        return alerts.sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      } catch {
        return [];
      }
    }
  },

  acknowledgeAlert: async (id: number, body: { user_id: number | null }) => {
    const response = await api.patch(`/alerts/${id}`, body);
    return response.data;
  },

  getAlertRules: async () => {
    const response = await api.get('/alerts/rules');
    return response.data;
  },
  createAlertRule: async (body: Record<string, unknown>) => {
    const response = await api.post('/alerts/rules', body);
    return response.data;
  },
  updateAlertRule: async (id: number, body: Record<string, unknown>) => {
    const response = await api.put(`/alerts/rules/${id}`, body);
    return response.data;
  },

  // Surveillance reports
  getSurveillanceReport: async (params: { period: string; from: string; to: string; lga_id?: number; state?: string }) => {
    const response = await api.get('/reports/surveillance', { params });
    return response.data;
  },
};

// React Query Hooks

export function useLgas(search?: string) {
  return useQuery({
    queryKey: search ? queryKeys.lgasSearch(search) : queryKeys.lgas,
    queryFn: () => apiService.getLgas(search),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useGeojson(date?: string) {
  return useQuery({
    queryKey: date ? [...queryKeys.geojson, date] : queryKeys.geojson,
    queryFn: () => apiService.getLgasGeojson(date),
    staleTime: 5 * 60 * 1000,
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: apiService.getDashboardSummary,
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: false, // Will be controlled by auto-refresh setting
  });
}

export function useLgaAnalytics(lgaId: number | null, days: number = 90) {
  return useQuery({
    queryKey: lgaId ? queryKeys.lgaAnalytics(lgaId, days) : ['analytics', 'null'],
    queryFn: () => apiService.getLgaAnalytics(lgaId!, days),
    enabled: !!lgaId,
    staleTime: 2 * 60 * 1000,
  });
}

export function useRiskScores() {
  return useQuery({
    queryKey: queryKeys.riskScores,
    queryFn: apiService.getAllRiskScores,
    staleTime: 2 * 60 * 1000,
  });
}

export function useWeeklySummary(weeks: number = 12) {
  return useQuery({
    queryKey: ['analytics', 'summary', 'weekly', weeks],
    queryFn: () => apiService.getWeeklySummary(weeks),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCorrelation(params: { lga_id?: number; state?: string; from_year: number; to_year: number } | null) {
  return useQuery({
    queryKey: ['analytics', 'correlation', params],
    queryFn: () => apiService.getCorrelation(params!),
    enabled: !!params,
    staleTime: 60 * 1000,
  });
}

export function useSatelliteStatus() {
  return useQuery({
    queryKey: queryKeys.satelliteStatus,
    queryFn: apiService.getSatelliteStatus,
    staleTime: 10 * 60 * 1000, // 10 minutes
    retry: 1,
  });
}

export function useSatelliteData() {
  return useQuery({
    queryKey: queryKeys.satelliteLatest,
    queryFn: apiService.getLatestSatelliteData,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
}

export function useAlerts(filters?: { severity?: string; is_acknowledged?: boolean; lga_id?: number }) {
  return useQuery({
    queryKey: filters ? ['alerts', filters] : queryKeys.alerts,
    queryFn: () => apiService.getAlerts(filters),
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

// Mutations
export function useUploadData() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, dataType }: { file: File; dataType: 'cases' | 'environmental' }) =>
      apiService.uploadData(file, dataType),
    onSuccess: () => {
      // Invalidate related queries after successful upload
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      queryClient.invalidateQueries({ queryKey: queryKeys.riskScores });
      queryClient.invalidateQueries({ queryKey: queryKeys.geojson });
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts });
    },
  });
}

export function useCalculateRisks() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: apiService.calculateRisks,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.riskScores });
      queryClient.invalidateQueries({ queryKey: queryKeys.geojson });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard });
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts });
    },
  });
}

// Hook for downloading templates
export function useDownloadTemplate() {
  return useMutation({
    mutationFn: async (dataType: 'cases' | 'environmental') => {
      const blob = await apiService.getUploadTemplate(dataType);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${dataType}_template.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  });
}

// Hook to invalidate all queries (for manual refresh)
export function useRefreshAll() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.invalidateQueries();
  };
}

// Auto-refresh hook
export function useAutoRefresh(intervalMs: number | null) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ['autoRefresh', intervalMs],
    queryFn: async () => {
      if (intervalMs) {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: queryKeys.dashboard }),
          queryClient.invalidateQueries({ queryKey: queryKeys.riskScores }),
          queryClient.invalidateQueries({ queryKey: queryKeys.geojson }),
          queryClient.invalidateQueries({ queryKey: queryKeys.alerts }),
        ]);
      }
      return new Date().toISOString();
    },
    enabled: !!intervalMs,
    refetchInterval: intervalMs || false,
    staleTime: 0,
  });
}

export function useSatelliteThumbnail(lgaId: number | null) {
  return useQuery({
    queryKey: lgaId ? queryKeys.satelliteThumbnail(lgaId) : ['satellite', 'thumbnail', 'null'],
    queryFn: () => apiService.getSatelliteThumbnail(lgaId!),
    enabled: !!lgaId,
    retry: false,
    staleTime: 60 * 60 * 1000,
  });
}
