import Link from "next/link";

import { getAppInstances, getAlerts } from "../lib/api";
import { getServerMetrics, getServers, ServerMetricSnapshot } from "../lib/serverApi";

function serverOnlineCount(lastSeen?: string | null) {
  if (!lastSeen) return false;
  return Date.now() - new Date(lastSeen).getTime() < 5 * 60 * 1000;
}

function sparklinePoints(metrics: ServerMetricSnapshot[]): string {
  if (!metrics.length) return "0 10 100 10";
  const values = metrics.map((m) => m.cpu_percent);
  const maxVal = Math.max(...values, 100);
  return metrics
    .map((m, idx) => {
      const x = (idx / Math.max(metrics.length - 1, 1)) * 100;
      const y = 100 - (m.cpu_percent / maxVal) * 100;
      return `${x},${Math.min(100, Math.max(0, y))}`;
    })
    .join(" ");
}

export default async function DashboardPage() {
  const [servers, apps, alerts] = await Promise.all([
    getServers(),
    getAppInstances(),
    getAlerts({ limit: 5 }),
  ]);

  const onlineServers = servers.filter((srv) => serverOnlineCount(srv.last_seen_at));
  const offlineServers = servers.length - onlineServers.length;
  const runningApps = apps.filter((app) => app.status === "running").length;
  const stoppedApps = apps.filter((app) => app.status === "stopped").length;
  const errorApps = apps.filter((app) => app.status === "error").length;
  const criticalAlerts = alerts.filter((a) => a.severity === "critical").length;

  const masterServer = servers.find((srv) => srv.is_master);
  let masterMetrics: ServerMetricSnapshot[] = [];
  if (masterServer) {
    masterMetrics = await getServerMetrics(masterServer.id, { limit: 8 });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <Link
          href="/servers"
          className="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500"
        >
          Manage Servers
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-2">
          <div className="text-sm text-slate-400">Servers</div>
          <div className="text-3xl font-bold">{servers.length}</div>
          <div className="text-xs text-slate-400">
            Online {onlineServers.length} · Offline {offlineServers}
          </div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-2">
          <div className="text-sm text-slate-400">Applications</div>
          <div className="text-3xl font-bold">{apps.length}</div>
          <div className="text-xs text-slate-400">
            Running {runningApps} · Stopped {stoppedApps} · Error {errorApps}
          </div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-2">
          <div className="text-sm text-slate-400">Critical Alerts</div>
          <div className="text-3xl font-bold text-red-400">{criticalAlerts}</div>
          <div className="text-xs text-slate-400">Recent severity: {alerts[0]?.severity || "-"}</div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-2">
          <div className="text-sm text-slate-400">Log Center</div>
          <div className="text-3xl font-bold">Audit</div>
          <div className="text-xs text-slate-400">Track access, app logs and alerts.</div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-3 md:col-span-2">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Recent Alerts</h3>
            <Link href="/alerts" className="text-sm text-blue-400 hover:text-blue-300">
              View all
            </Link>
          </div>
          <div className="space-y-2">
            {alerts.length === 0 && (
              <div className="text-slate-400 text-sm">No alerts yet.</div>
            )}
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/60 px-3 py-2"
              >
                <div>
                  <div className="text-sm font-semibold">{alert.message}</div>
                  <div className="text-xs text-slate-400">{alert.scope_type}</div>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded ${
                    alert.severity === "critical"
                      ? "bg-red-900/50 text-red-200"
                      : alert.severity === "warning"
                        ? "bg-amber-900/50 text-amber-200"
                        : "bg-slate-800 text-slate-200"
                  }`}
                >
                  {alert.severity}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Master CPU</h3>
            <div className="text-xs text-slate-400">last {masterMetrics.length} samples</div>
          </div>
          <div className="h-24 flex items-center justify-center bg-slate-900/50 rounded">
            {masterMetrics.length ? (
              <svg viewBox="0 0 100 100" className="w-full h-full text-blue-400">
                <polyline
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  points={sparklinePoints(masterMetrics)}
                />
              </svg>
            ) : (
              <div className="text-slate-500 text-sm">No metrics yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
