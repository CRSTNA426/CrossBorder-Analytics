/**
 * API wrapper for CrossBorder Analytics backend.
 * All calls go to http://localhost:8000/api/...
 */
const API_BASE = 'http://localhost:8000/api';

const api = {
  async get(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  },

  async post(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  },

  async put(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  },

  async del(path) {
    const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  },

  // Platforms
  getPlatforms: () => api.get('/platforms'),
  getPlatformMetrics: (id) => api.get(`/platforms/${id}/metrics`),
  getDefaultMetrics: (id) => api.get(`/platforms/${id}/default-metrics`),

  // Metrics
  createMetric: (body) => api.post('/metrics', body),
  updateMetric: (id, body) => api.put(`/metrics/${id}`, body),
  deleteMetric: (id) => api.del(`/metrics/${id}`),
  permanentDeleteMetric: (id) => api.del(`/metrics/${id}/permanent`),
  restoreMetric: (id) => api.post(`/metrics/${id}/restore`),
  listDeletedMetrics: (platformId) => api.get(`/metrics/deleted?platform_id=${platformId}`),
  validateFormula: (body) => api.post('/metrics/validate-formula', body),

  // Dashboards
  createDashboard: (body) => api.post('/dashboards', body),
  getDashboard: (id) => api.get(`/dashboards/${id}`),
  listDashboards: () => api.get('/dashboards'),
  updateLayout: (id, layout) => api.put(`/dashboards/${id}/layout`, layout),
  addWidget: (dashboardId, body) => api.post(`/dashboards/${dashboardId}/widgets`, body),
  updateWidget: (dashboardId, widgetId, body) => api.put(`/dashboards/${dashboardId}/widgets/${widgetId}`, body),
  removeWidget: (dashboardId, widgetId) => api.del(`/dashboards/${dashboardId}/widgets/${widgetId}`),

  // Data
  getDashboardData: (dashboardId, date) => api.get(`/data?dashboard_id=${dashboardId}&date=${date}`),
  getTrendData: (dashboardId, metricKeys, days) => api.get(`/data/trend?dashboard_id=${dashboardId}&metric_keys=${metricKeys}&days=${days}`),
};
