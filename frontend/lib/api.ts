const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
export const API_BASE_URL = RAW_API_BASE_URL.endsWith("/v1")
  ? RAW_API_BASE_URL
  : `${RAW_API_BASE_URL.replace(/\/$/, "")}/v1`;

type RequestOptions = RequestInit & { skipJson?: boolean };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { skipJson, ...fetchOptions } = options;
  const headers = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers ?? {}),
  };
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    ...fetchOptions,
    headers,
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const errorBody = await response.json();
      if (errorBody.detail) {
        message = Array.isArray(errorBody.detail)
          ? errorBody.detail.map((item: any) => item.msg ?? item).join(", ")
          : errorBody.detail;
      }
    } catch {
      // Ignore JSON parsing errors for error payloads
    }
    throw new Error(message);
  }
  if (response.status === 204 || skipJson) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface Domain {
  id: number;
  domain_name: string;
  provider_type: string;
  provider_credential_id?: number | null;
  auto_ssl_enabled: boolean;
  auto_dns_enabled: boolean;
  is_wildcard: boolean;
  base_domain_id?: number | null;
  created_at: string;
}

export interface Server {
  id: number;
  name: string;
  description?: string | null;
  is_master: boolean;
  agent_url?: string | null;
  agent_token?: string | null;
  location?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: number;
  name: string;
  slug: string;
  type: string;
  description?: string | null;
  repository_url?: string | null;
  default_image?: string | null;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface AppBlueprint {
  type: string;
  docker_image?: string;
  docker_port?: number;
  env?: string[];
  requires?: string[];
}

export interface DomainMappingInput {
  domain_id: number;
  subdomain?: string;
  is_primary?: boolean;
}

export interface AppDomainMapping {
  id: number;
  domain_id: number;
  subdomain?: string | null;
  is_primary: boolean;
  created_at: string;
  domain?: Domain;
}

export interface AppInstance {
  id: number;
  app_id: number;
  server_id: number;
  display_name: string;
  status: string;
  main_domain_id?: number | null;
  internal_container_name: string;
  docker_image: string;
  docker_port: number;
  replicas: number;
  env_vars: Record<string, string>;
  created_at: string;
  updated_at: string;
  domain_mappings: AppDomainMapping[];
}

export interface AlertEvent {
  id: number;
  rule_id: number;
  scope_type: string;
  scope_id?: number | null;
  message: string;
  severity: string;
  created_at: string;
  is_acknowledged: boolean;
  acknowledged_at?: string | null;
}

export interface AlertRule {
  id: number;
  name: string;
  scope_type: string;
  scope_id?: number | null;
  rule_type: string;
  threshold_value?: number | null;
  is_enabled: boolean;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface ActivityLog {
  id: number;
  user_id?: number | null;
  action: string;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface SuspiciousLoginAttempt {
  id: number;
  username: string;
  ip_address: string;
  user_agent?: string | null;
  reason: string;
  created_at: string;
}

export interface CreateAppInstanceRequest {
  app_id: number;
  server_id: number;
  display_name: string;
  app_type?: string;
  config?: Record<string, unknown>;
  domains: DomainMappingInput[];
}

export interface AttachDomainsRequest {
  domains: DomainMappingInput[];
}

export async function getAppBlueprints(): Promise<AppBlueprint[]> {
  return request<AppBlueprint[]>("/apps/blueprints");
}

export async function getServers(): Promise<Server[]> {
  return request<Server[]>("/servers");
}

export async function getDomains(): Promise<Domain[]> {
  return request<Domain[]>("/domains");
}

export async function getApplications(): Promise<Application[]> {
  return request<Application[]>("/apps");
}

export async function suggestSubdomain(domainId: number, appName: string): Promise<string> {
  const result = await request<{ suggested_subdomain: string }>(
    `/domains/${domainId}/subdomain-preview`,
    {
      method: "POST",
      body: JSON.stringify({ app_name: appName }),
    },
  );
  return result.suggested_subdomain;
}

export async function createAppInstance(payload: CreateAppInstanceRequest): Promise<AppInstance> {
  return request<AppInstance>("/apps/instances", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAppInstances(): Promise<AppInstance[]> {
  return request<AppInstance[]>("/apps/instances");
}

export async function attachAppDomains(
  instanceId: number,
  payload: AttachDomainsRequest,
): Promise<AppInstance> {
  return request<AppInstance>(`/apps/instances/${instanceId}/domains`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function stopAppInstance(instanceId: number): Promise<void> {
  await request(`/apps/instances/${instanceId}/stop`, { method: "POST", skipJson: true });
}

export async function restartAppInstance(instanceId: number): Promise<AppInstance> {
  return request<AppInstance>(`/apps/instances/${instanceId}/restart`, { method: "POST" });
}

export async function getAppInstanceLogs(instanceId: number, tail = 200): Promise<string> {
  const result = await request<{ logs: string }>(
    `/apps/instances/${instanceId}/logs?tail=${tail}`,
  );
  return result.logs;
}

export async function getAlerts(params: {
  limit?: number;
  severity?: string;
  is_acknowledged?: boolean;
} = {}): Promise<AlertEvent[]> {
  const query = new URLSearchParams();
  if (params.limit) query.set("limit", String(params.limit));
  if (params.severity) query.set("severity", params.severity);
  if (params.is_acknowledged !== undefined) {
    query.set("is_acknowledged", String(params.is_acknowledged));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<AlertEvent[]>(`/alerts${suffix}`);
}

export async function ackAlert(alertId: number): Promise<AlertEvent> {
  return request<AlertEvent>(`/alerts/${alertId}/ack`, { method: "POST" });
}

export async function getActivityLogs(params: {
  user_id?: number;
  action?: string;
  limit?: number;
} = {}): Promise<ActivityLog[]> {
  const query = new URLSearchParams();
  if (params.user_id !== undefined) query.set("user_id", String(params.user_id));
  if (params.action) query.set("action", params.action);
  if (params.limit) query.set("limit", String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<ActivityLog[]>(`/logs/activity${suffix}`);
}

export async function getSuspiciousLogins(): Promise<SuspiciousLoginAttempt[]> {
  return request<SuspiciousLoginAttempt[]>(`/logs/security/suspicious-logins`);
}
