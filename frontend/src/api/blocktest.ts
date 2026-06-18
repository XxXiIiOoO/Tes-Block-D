import { apiRequest, downloadFile, streamSse } from "./client";
import type {
  AdminUserUpdatePayload,
  AdminUserCreatePayload,
  AuditEvent,
  AuthResponse,
  LoginResponse,
  Project,
  ProjectMember,
  ProjectPayload,
  ProjectSecret,
  ProjectSecretPayload,
  RegisterResponse,
  Run,
  RunComparison,
  RunInsights,
  RunLog,
  RunLogStreamSnapshot,
  StatsOverview,
  TestChatMessage,
  TestItem,
  TestPayload,
  User,
  UserProfilePayload,
} from "../types";


function buildQuery(params: Record<string, string | undefined>) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}


export function registerRequest(payload: {
  email: string;
  username: string;
  password: string;
}) {
  return apiRequest<RegisterResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}




export function loginRequest(payload: { email: string; password: string }) {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function verifyTwoFactorRequest(payload: { email: string; code: string }) {
  return apiRequest<AuthResponse>("/auth/verify-2fa", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function verifyEmailRequest(payload: { token: string }) {
  return apiRequest<AuthResponse>("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function forgotPasswordRequest(payload: { email: string }) {
  return apiRequest<{ message: string }>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function resetPasswordRequest(payload: { token: string; new_password: string }) {
  return apiRequest<{ message: string }>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function logoutRequest(payload: { refresh_token: string }) {
  return apiRequest<{ message: string }>("/auth/logout", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function getMe() {
  return apiRequest<User>("/auth/me");
}


export function updateMe(payload: Partial<UserProfilePayload>) {
  return apiRequest<User>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}


export function getAdminUsers(params: { search?: string; role?: string } = {}) {
  return apiRequest<User[]>(
    `/admin/users${buildQuery({
      search: params.search,
      role: params.role,
    })}`,
  );
}

export function createAdminUser(payload: AdminUserCreatePayload) {
  return apiRequest<User>("/admin/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function updateAdminUser(userId: number, payload: AdminUserUpdatePayload) {
  return apiRequest<User>(`/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteAdminUser(userId: number) {
  return apiRequest<void>(`/admin/users/${userId}`, { method: "DELETE" });
}


export function getAuditEvents(
  params: {
    action?: string;
    entityType?: string;
    userId?: number;
    limit?: number;
  } = {},
) {
  return apiRequest<AuditEvent[]>(
    `/admin/audit-events${buildQuery({
      action: params.action,
      entity_type: params.entityType,
      user_id: params.userId ? String(params.userId) : undefined,
      limit: params.limit ? String(params.limit) : undefined,
    })}`,
  );
}


export function getStatsOverview() {
  return apiRequest<StatsOverview>("/stats/overview");
}


export function getProjects(search?: string) {
  return apiRequest<Project[]>(`/projects${buildQuery({ search })}`);
}


export function createProject(payload: ProjectPayload) {
  return apiRequest<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function getProject(projectId: number) {
  return apiRequest<Project>(`/projects/${projectId}`);
}


export function updateProject(projectId: number, payload: Partial<ProjectPayload>) {
  return apiRequest<Project>(`/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}


export function deleteProject(projectId: number) {
  return apiRequest<void>(`/projects/${projectId}`, { method: "DELETE" });
}

export function getProjectMembers(projectId: number) {
  return apiRequest<ProjectMember[]>(`/projects/${projectId}/members`);
}

export function createProjectMember(projectId: number, payload: { user_id: number; role: ProjectMember["role"] }) {
  return apiRequest<ProjectMember>(`/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProjectMember(projectId: number, memberId: number, payload: { role: ProjectMember["role"] }) {
  return apiRequest<ProjectMember>(`/projects/${projectId}/members/${memberId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteProjectMember(projectId: number, memberId: number) {
  return apiRequest<void>(`/projects/${projectId}/members/${memberId}`, { method: "DELETE" });
}


export function getProjectTests(projectId: number) {
  return apiRequest<TestItem[]>(`/projects/${projectId}/tests`);
}

export function getProjectSecrets(projectId: number) {
  return apiRequest<ProjectSecret[]>(`/projects/${projectId}/secrets`);
}

export function createProjectSecret(projectId: number, payload: ProjectSecretPayload) {
  return apiRequest<ProjectSecret>(`/projects/${projectId}/secrets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProjectSecret(projectId: number, secretId: number, payload: { value: string }) {
  return apiRequest<ProjectSecret>(`/projects/${projectId}/secrets/${secretId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteProjectSecret(projectId: number, secretId: number) {
  return apiRequest<void>(`/projects/${projectId}/secrets/${secretId}`, { method: "DELETE" });
}


export function createTest(projectId: number, payload: TestPayload) {
  return apiRequest<TestItem>(`/projects/${projectId}/tests`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function getTest(testId: number) {
  return apiRequest<TestItem>(`/tests/${testId}`);
}


export function getTestChatMessages(testId: number) {
  return apiRequest<TestChatMessage[]>(`/tests/${testId}/chat`);
}


export function postTestChatMessage(testId: number, payload: { message: string }) {
  return apiRequest<TestChatMessage>(`/tests/${testId}/chat`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


export function updateTest(testId: number, payload: Partial<TestPayload>) {
  return apiRequest<TestItem>(`/tests/${testId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}


export function deleteTest(testId: number) {
  return apiRequest<void>(`/tests/${testId}`, { method: "DELETE" });
}


export function runTest(testId: number) {
  return apiRequest<Run>(`/tests/${testId}/run`, { method: "POST" });
}


export function rerunRun(runId: number) {
  return apiRequest<Run>(`/runs/${runId}/rerun`, { method: "POST" });
}


export function cancelRun(runId: number) {
  return apiRequest<Run>(`/runs/${runId}/cancel`, { method: "POST" });
}


export function getRuns(params: {
  status?: string;
  dateFrom?: string;
  dateTo?: string;
  sortBy?: string;
  order?: string;
} = {}) {
  return apiRequest<Run[]>(
    `/runs${buildQuery({
      status: params.status,
      date_from: params.dateFrom,
      date_to: params.dateTo,
      sort_by: params.sortBy,
      order: params.order,
    })}`,
  );
}


export function getTestRuns(
  testId: number,
  params: {
    status?: string;
    dateFrom?: string;
    dateTo?: string;
    sortBy?: string;
    order?: string;
  } = {},
) {
  return apiRequest<Run[]>(
    `/tests/${testId}/runs${buildQuery({
      status: params.status,
      date_from: params.dateFrom,
      date_to: params.dateTo,
      sort_by: params.sortBy,
      order: params.order,
    })}`,
  );
}


export function getRun(runId: number) {
  return apiRequest<Run>(`/runs/${runId}`);
}

export function getRunComparison(runId: number, baselineRunId?: number) {
  return apiRequest<RunComparison>(
    `/runs/${runId}/compare${buildQuery({
      baseline_run_id: baselineRunId ? String(baselineRunId) : undefined,
    })}`,
  );
}


export function getRunLogs(runId: number) {
  return apiRequest<RunLog[]>(`/runs/${runId}/logs`);
}


export function streamRunLogs(
  runId: number,
  options: {
    signal?: AbortSignal;
    onSnapshot: (snapshot: RunLogStreamSnapshot) => void;
  },
) {
  return streamSse<RunLogStreamSnapshot>(`/runs/${runId}/logs/stream`, {
    signal: options.signal,
    onEvent: (payload) => options.onSnapshot(payload),
  });
}


export function getRunInsights(runId: number) {
  return apiRequest<RunInsights>(`/runs/${runId}/insights`);
}


export type RunExportFormat = "json" | "html" | "pdf";

export function downloadRunExport(runId: number, format: RunExportFormat = "json") {
  if (format === "json") {
    return downloadFile(`/runs/${runId}/export`, `run-${runId}.json`);
  }

  return downloadFile(`/runs/${runId}/report.${format}`, `run-${runId}-report.${format}`);
}
