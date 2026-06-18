export type RunStatus = "queued" | "running" | "finished" | "failed" | "cancelled";
export type RunLogSource = "stdout" | "stderr" | "system";
export type RunLogSeverity = "info" | "warning" | "error";

export interface StatsDailyPoint {
  day: string;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
}


export interface StatsStatusBreakdown {
  status: RunStatus;
  count: number;
}


export interface StatsProjectPerformance {
  project_id: number;
  project_name: string;
  owner_username: string | null;
  run_count: number;
  successful_run_count: number;
  failed_run_count: number;
  success_rate: number;
}

export interface StatsFailureReason {
  category: string;
  count: number;
}

export interface StatsTestInsight {
  test_id: number;
  test_name: string;
  project_name: string | null;
  run_count: number;
  success_rate: number;
  average_duration_seconds: number;
}

export interface StatsRecentFailure {
  run_id: number;
  test_name: string | null;
  project_name: string | null;
  created_at: string;
  result_summary: string | null;
  failure_category: string | null;
}

export interface StatsAlert {
  severity: "info" | "warning" | "error";
  title: string;
  detail: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  is_admin: boolean;
  role: "admin" | "worker" | "viewer";
  email_verified: boolean;
  full_name: string | null;
  position: string | null;
  avatar_url: string | null;
  bio: string | null;
  created_at: string;
}

export interface UserProfilePayload {
  full_name: string | null;
  position: string | null;
  avatar_url: string | null;
  bio: string | null;
}

export interface AdminUserUpdatePayload {
  email?: string;
  username?: string;
  password?: string;
  role?: "admin" | "worker" | "viewer";
  email_verified?: boolean;
  full_name?: string | null;
  position?: string | null;
  avatar_url?: string | null;
  bio?: string | null;
}

export interface AdminUserCreatePayload {
  email: string;
  username: string;
  password: string;
  role: "admin" | "worker" | "viewer";
  email_verified: boolean;
  full_name?: string | null;
  position?: string | null;
  avatar_url?: string | null;
  bio?: string | null;
}

export interface AuditEvent {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  details: string | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface TwoFactorChallengeResponse {
  two_factor_required: true;
  message: string;
  email: string;
}

export type LoginResponse = AuthResponse | TwoFactorChallengeResponse;

export interface RegisterResponse {
  message: string;
  verification_required: boolean;
  verification_token: string | null;
  user: User;
}

export interface Project {
  id: number;
  owner_id: number;
  owner_username: string | null;
  access_role: "admin" | "owner" | "developer" | "viewer" | null;
  name: string;
  description: string | null;
  repository_url: string | null;
  repository_branch: string | null;
  repository_subdir: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectPayload {
  name: string;
  description: string | null;
  repository_url: string | null;
  repository_branch: string | null;
  repository_subdir: string | null;
}

export interface ProjectMember {
  id: number;
  project_id: number;
  user_id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: "developer" | "viewer";
  created_at: string;
  updated_at: string;
}

export interface ProjectSecret {
  id: number;
  project_id: number;
  name: string;
  value_mask: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectSecretPayload {
  name: string;
  value: string;
}

export interface TestItem {
  id: number;
  project_id: number;
  name: string;
  description: string | null;
  scenario: string;
  docker_image: string;
  command: string | null;
  script: string | null;
  repository_url: string | null;
  repository_branch: string | null;
  repository_subdir: string | null;
  setup_command: string | null;
  rpc_url: string | null;
  chain_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface TestPayload {
  name: string;
  description: string | null;
  scenario: string;
  docker_image: string;
  command: string | null;
  script: string | null;
  repository_url: string | null;
  repository_branch: string | null;
  repository_subdir: string | null;
  setup_command: string | null;
  rpc_url: string | null;
  chain_id: number | null;
}

export interface TestChatMessage {
  id: number;
  test_id: number;
  user_id: number;
  username: string;
  role: "admin" | "worker" | "viewer";
  message: string;
  created_at: string;
}

export interface Run {
  id: number;
  test_id: number;
  status: RunStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  queue_time_seconds: number | null;
  result_summary: string | null;
  exit_code: number | null;
  created_at: string;
  test_name: string | null;
  project_id: number | null;
  project_name: string | null;
}

export interface RunLog {
  id: number;
  run_id: number;
  message: string;
  source: RunLogSource;
  severity: RunLogSeverity;
  created_at: string;
}

export interface RunLogStreamSnapshot {
  run: Run;
  logs: RunLog[];
  done: boolean;
}

export interface RunMetrics {
  duration_seconds: number | null;
  queue_time_seconds: number | null;
  total_logs: number;
  stdout_lines: number;
  stderr_lines: number;
  system_lines: number;
  info_count: number;
  warning_count: number;
  error_count: number;
}

export interface RunSignal {
  severity: RunLogSeverity;
  title: string;
  detail: string;
}

export interface RunQualityGate {
  enabled: boolean;
  passed: boolean | null;
  baseline_run_id: number | null;
  baseline_delta_seconds: number | null;
  reasons: string[];
}

export interface RunInsights {
  summary: string;
  failure_category: string | null;
  latest_error: string | null;
  metrics: RunMetrics;
  signals: RunSignal[];
  recommendations: string[];
  quality_gate: RunQualityGate | null;
}

export interface RunComparisonMetric {
  key: string;
  label: string;
  current: number | string | null;
  baseline: number | string | null;
  delta: number | null;
  delta_percent: number | null;
  unit: string | null;
}

export interface RunLogDiff {
  added: string[];
  removed: string[];
  added_count: number;
  removed_count: number;
  unchanged_count: number;
}

export interface RunComparison {
  current_run: Run;
  baseline_run: Run | null;
  metrics: RunComparisonMetric[];
  status_changed: boolean;
  exit_code_changed: boolean;
  log_diff: RunLogDiff | null;
}

export interface StatsOverview {
  project_count: number;
  test_count: number;
  run_count: number;
  successful_run_count: number;
  failed_run_count: number;
  queued_run_count: number;
  running_run_count: number;
  success_rate: number;
  average_duration_seconds: number;
  average_queue_time_seconds: number;
  active_projects_last_7_days: number;
  last_run_at: string | null;
  daily_runs: StatsDailyPoint[];
  runs_by_status: StatsStatusBreakdown[];
  top_projects: StatsProjectPerformance[];
  failure_reasons: StatsFailureReason[];
  slowest_tests: StatsTestInsight[];
  flaky_tests: StatsTestInsight[];
  recent_failures: StatsRecentFailure[];
  alerts: StatsAlert[];
}
