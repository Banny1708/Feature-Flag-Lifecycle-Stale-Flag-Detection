import { apiGet, apiPatch, apiPost, apiPut, API_BASE_URL } from './apiClient';
import type { FeatureFlag, RiskAssessment } from '@/types';

/** Client for the lifecycle API (projects, analysis, risk, settings, evidence, audit). */

export interface Project {
  id: string;
  name: string;
  description: string;
  repositoryUrl: string;
  defaultBranch: string;
}

export interface AnalysisRun {
  id: string;
  analysisType: string;
  toolName: string;
  status: string;
  totalFlags: number;
  staleFlags: number;
  untestedPaths: number;
  removalCandidates: number;
}

export interface DetectionResult {
  id: string;
  analysisRunId: string;
  featureFlagId: string;
  detectionStatus: string;
  staleScore: number;
  confidence: number;
  reason: string;
  detectedAt: string;
}

export interface AuditEntry {
  id: string;
  action: string;
  entityType: string;
  entityId: string;
  oldValue: string;
  newValue: string;
  timestamp: string;
  userOrActor: string;
}

export interface SystemSettings {
  stale_days_threshold: number;
  warn_days_threshold: number;
  scanner_engine: string;
  github_token: string;
  slack_webhook: string;
}

export const lifecycleService = {
  // projects
  getProjects: () => apiGet<Project[]>('/api/projects'),
  createProject: (body: { name: string; description?: string }) =>
    apiPost<Project>('/api/projects', body),
  getProjectFlags: (projectId: string) =>
    apiGet<FeatureFlag[]>(`/api/projects/${encodeURIComponent(projectId)}/flags`),

  // flags
  patchFlag: (flagId: string, body: Record<string, unknown>) =>
    apiPatch<FeatureFlag>(`/api/flags/${encodeURIComponent(flagId)}`, body),
  getFlagHistory: (flagId: string) =>
    apiGet<AuditEntry[]>(`/api/flags/${encodeURIComponent(flagId)}/history`),

  // analysis
  runAnalysis: (body: Record<string, unknown>) =>
    apiPost<AnalysisRun>('/api/analysis/run', body),
  getAnalysisRuns: () => apiGet<AnalysisRun[]>('/api/analysis'),
  getDetectionResults: (analysisRunId?: string) =>
    apiGet<DetectionResult[]>('/api/detection-results', analysisRunId ? { analysis_run_id: analysisRunId } : undefined),

  // risk
  createRiskAssessment: (flagId: string) =>
    apiPost<RiskAssessment>('/api/risk-assessments', { flag_id: flagId }),

  // settings
  getSettings: () => apiGet<SystemSettings>('/api/settings'),
  updateSettings: (body: Partial<SystemSettings>) =>
    apiPut<SystemSettings>('/api/settings', body),

  // evidence & audit
  getEvidence: (params?: Record<string, string>) => apiGet<unknown[]>('/api/evidence', params),
  getAuditLogs: (params?: Record<string, string>) => apiGet<AuditEntry[]>('/api/audit-logs', params),

  healthDb: () => apiGet<{ status: string; dialect: string }>(`/health/db`),

  getToolStatus: () =>
    apiGet<Array<{ name: string; available: boolean; version: string; path: string; hint: string }>>(
      '/api/tools/status'
    ),
};

export function backendReportDownloadUrl(reportId: string): string {
  return `${API_BASE_URL}/api/reports/${encodeURIComponent(reportId)}/download`;
}
