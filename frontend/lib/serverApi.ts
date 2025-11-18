import { API_BASE_URL } from "./api";

interface RequestOptions extends RequestInit {
  skipJson?: boolean;
}

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
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  if (response.status === 204 || skipJson) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface ServerMetricSnapshot {
  id: number;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  docker_running_containers: number;
  docker_total_containers: number;
  created_at: string;
}

export interface ServerSummary {
  id: number;
  name: string;
  description?: string | null;
  is_master: boolean;
  agent_url?: string | null;
  agent_token?: string | null;
  location?: string | null;
  is_active: boolean;
  last_seen_at?: string | null;
  created_at: string;
  updated_at: string;
  latest_metric?: ServerMetricSnapshot | null;
}

export interface ServerDetail extends ServerSummary {
  metrics: ServerMetricSnapshot[];
}

export interface ServerPayload {
  name: string;
  description?: string;
  is_master?: boolean;
  agent_url?: string;
  agent_token?: string;
  location?: string;
  is_active?: boolean;
}

export async function getServers(): Promise<ServerSummary[]> {
  return request<ServerSummary[]>("/servers");
}

export async function getServer(id: number): Promise<ServerDetail> {
  return request<ServerDetail>(`/servers/${id}`);
}

export async function createServer(payload: ServerPayload): Promise<ServerSummary> {
  return request<ServerSummary>("/servers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateServer(id: number, payload: ServerPayload): Promise<ServerDetail> {
  return request<ServerDetail>(`/servers/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function pingServer(id: number): Promise<any> {
  return request<any>(`/servers/${id}/ping`, { method: "POST" });
}

export async function getServerMetrics(
  id: number,
  params: { skip?: number; limit?: number } = {},
): Promise<ServerMetricSnapshot[]> {
  const query = new URLSearchParams();
  if (params.skip) query.set("skip", String(params.skip));
  if (params.limit) query.set("limit", String(params.limit));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<ServerMetricSnapshot[]>(`/servers/${id}/metrics${suffix}`);
}
