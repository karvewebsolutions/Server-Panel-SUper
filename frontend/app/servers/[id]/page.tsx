import Link from "next/link";
import { notFound } from "next/navigation";
import { PingButton } from "./PingButton";
import { getServer, ServerMetricSnapshot } from "../../../lib/serverApi";

type MetricField = "cpu_percent" | "memory_percent" | "disk_percent";

function MetricRow({ label, metric, field }: { label: string; metric?: ServerMetricSnapshot; field: MetricField }) {
  const value = metric ? (metric[field] as number) : undefined;
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold">{value !== undefined ? `${value}%` : "-"}</span>
    </div>
  );
}

export default async function ServerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params;
  const serverId = Number(resolvedParams.id);
  const server = await getServer(serverId).catch(() => null);
  if (!server) return notFound();
  const latest = server.metrics[0];
  const lastSeen = server.last_seen_at ? new Date(server.last_seen_at) : null;
  const online = lastSeen ? Date.now() - lastSeen.getTime() < 5 * 60 * 1000 : false;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">Server</p>
          <h2 className="text-2xl font-bold">{server.name}</h2>
        </div>
        <Link href="/servers" className="text-sm text-blue-400 hover:text-blue-300">
          ← Back to servers
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">Status</span>
            <span className={`text-sm font-semibold ${online ? "text-green-400" : "text-red-400"}`}>
              {online ? "Online" : "Offline"}
            </span>
          </div>
          <MetricRow label="CPU" metric={latest} field="cpu_percent" />
          <MetricRow label="Memory" metric={latest} field="memory_percent" />
          <MetricRow label="Disk" metric={latest} field="disk_percent" />
          <PingButton serverId={serverId} />
        </div>

        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-2">
          <h3 className="text-lg font-semibold">Connection</h3>
          <div className="text-sm text-slate-300">Location: {server.location || "N/A"}</div>
          <div className="text-sm text-slate-300">Mode: {server.is_master ? "Master" : "Agent"}</div>
          <div className="text-sm text-slate-300 break-words">Agent URL: {server.agent_url || "Local"}</div>
          <div className="text-sm text-slate-400">
            Last seen: {lastSeen ? lastSeen.toLocaleString() : "never"}
          </div>
        </div>

        <div className="rounded border border-slate-800 bg-slate-950 p-4 space-y-3">
          <h3 className="text-lg font-semibold">Recent Metrics</h3>
          <div className="space-y-2">
            {server.metrics.slice(0, 5).map((metric) => (
              <div key={metric.id} className="text-xs text-slate-300">
                <div className="flex justify-between">
                  <span>{new Date(metric.created_at).toLocaleTimeString()}</span>
                  <span>{metric.cpu_percent.toFixed(1)}% CPU</span>
                </div>
                <div className="w-full bg-slate-900 rounded h-1 mt-1">
                  <div
                    className="h-1 rounded bg-blue-500"
                    style={{ width: `${Math.min(100, metric.cpu_percent)}%` }}
                  />
                </div>
              </div>
            ))}
            {server.metrics.length === 0 && (
              <div className="text-slate-400 text-sm">No metrics collected yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
