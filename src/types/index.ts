export type FeatureFlagStatus =
  | 'active'
  | 'potentially-stale'
  | 'stale'
  | 'removal-pending'
  | 'removed';

export type RiskLevel =
  | 'low'
  | 'medium'
  | 'high'
  | 'critical';

export type FlagType =
  | 'release'
  | 'experiment'
  | 'operational'
  | 'permission';

export type ScanStatus =
  | 'idle'
  | 'queued'
  | 'scanning'
  | 'completed'
  | 'failed';

export type RemovalStatus =
  | 'draft'
  | 'prepared'
  | 'in-review'
  | 'merged'
  | 'failed'
  | 'aborted';

export type RemovalTool =
  | 'Piranha'
  | 'FlagShark'
  | 'Manual';

export type VerificationStatus =
  | 'passed'
  | 'failed'
  | 'running'
  | 'skipped';

export type EvidenceType =
  | 'zero-traffic'
  | 'code-commit-staleness'
  | 'time-decay'
  | 'pr-closure'
  | 'ast-unreachable';

export type ReportType =
  | 'stale-summary'
  | 'lifecycle-audit'
  | 'cleanup-impact'
  | 'compliance';

export interface UsageMetrics {
  evaluationsCount: number;
  evaluationsLast7d: number;
  daysInactive: number;
  rolloutPercentage: number;
  environment: 'production' | 'staging' | 'development';
}

export interface FeatureFlag {
  id: string;
  name: string;
  key: string;
  description: string;
  repositoryId: string;
  repositoryName: string;
  status: FeatureFlagStatus;
  risk: RiskLevel;
  flagType: FlagType;
  owner: string;
  ownerTeam?: string;
  createdAt: string;
  lastModified: string;
  staleSince?: string;
  metrics: UsageMetrics;
  tags: string[];
  defaultValue: boolean | string | number;
}

export interface Repository {
  id: string;
  name: string;
  fullName: string;
  owner: string;
  url: string;
  defaultBranch: string;
  language: string;
  scanStatus: ScanStatus;
  lastScannedAt: string;
  totalFlags: number;
  activeFlags: number;
  staleFlags: number;
  potentiallyStaleFlags: number;
  linesOfCode: number;
}

export interface ScanFinding {
  flagKey: string;
  filePath: string;
  lineNumber: number;
  astNodeType: string;
  isStale: boolean;
  confidence: number;
  reason: string;
}

export interface ScanResult {
  id: string;
  repositoryId: string;
  repositoryName: string;
  timestamp: string;
  status: 'success' | 'partial' | 'failed';
  totalFlagsDetected: number;
  staleFlagsDetected: number;
  scannerEngine: 'FlagShark-engine' | 'AST-Analyzer' | 'Hybrid-Scanner';
  scanDurationMs: number;
  commitHash: string;
  branch: string;
  findings: ScanFinding[];
}

export interface CodeReference {
  id: string;
  flagId: string;
  flagName: string;
  repositoryId: string;
  repositoryName: string;
  filePath: string;
  lineNumber: number;
  columnNumber: number;
  codeSnippet: string;
  referenceType: 'definition' | 'check' | 'wrapper' | 'cleanup-candidate';
  isEnclosingControlFlow: boolean;
  astNodeType: string;
}

export interface CodePath {
  id: string;
  flagId: string;
  filePath: string;
  branchCondition: string;
  reachableState: boolean;
  deadCodeLines: number[];
  deadCodeSnippet: string;
  complexityReductionScore: number;
}

export interface RiskFactor {
  category: 'Blast Radius' | 'Production Traffic' | 'Code References' | 'Dependent Services' | 'Team Ownership';
  description: string;
  score: number; // 0 - 100
  level: RiskLevel;
}

export interface RiskAssessment {
  id: string;
  flagId: string;
  flagName: string;
  overallRisk: RiskLevel;
  blastRadiusScore: number; // 0 - 100
  factors: RiskFactor[];
  recommendations: string[];
  assessedAt: string;
  estimatedCleanupHours: number;
}

export interface RemovalOperation {
  id: string;
  flagId: string;
  flagName: string;
  repositoryId: string;
  repositoryName: string;
  targetBranch: string;
  prUrl?: string;
  prNumber?: number;
  status: RemovalStatus;
  toolTarget: RemovalTool;
  filesAffected: number;
  linesRemoved: number;
  linesAdded: number;
  createdAt: string;
  completedAt?: string;
  executedBy: string;
  diffSummary?: string;
}

export interface DiffCheckAnalysis {
  deadCodeEliminated: boolean;
  syntaxValid: boolean;
  regressionDetected: boolean;
  unresolvedReferences: number;
}

export interface VerificationResult {
  id: string;
  operationId: string;
  flagId: string;
  flagName: string;
  repositoryName: string;
  testSuiteStatus: VerificationStatus;
  buildStatus: VerificationStatus;
  astValidationStatus: VerificationStatus;
  diffAnalysis: DiffCheckAnalysis;
  verifiedAt: string;
  summary: string;
  testOutputSummary?: string;
}

export interface EvidenceRecord {
  id: string;
  flagId: string;
  flagName: string;
  repositoryName: string;
  evidenceType: EvidenceType;
  confidenceScore: number; // 0 - 1.0
  detectedAt: string;
  source: string;
  summary: string;
  payload: Record<string, string | number | boolean | string[]>;
}

export interface ReportSummary {
  totalScannedFlags: number;
  staleFlagsIdentified: number;
  removalOperationsCompleted: number;
  techDebtReductionHours: number;
  codeLinesEliminated: number;
}

export interface Report {
  id: string;
  title: string;
  type: ReportType;
  generatedAt: string;
  repositoryId?: string;
  repositoryName?: string;
  summary: ReportSummary;
  downloadFormat: 'json' | 'pdf' | 'csv';
  status: 'ready' | 'generating';
}
