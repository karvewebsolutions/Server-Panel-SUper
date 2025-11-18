import Link from "next/link";
import { getServers, ServerSummary } from "../../lib/serverApi";

function serverStatus(server: ServerSummary): { label: string; color: string } {
  const lastSeen = server.last_seen_at ? new Date(server.last_seen_at).getTime() : 0;
  const online = lastSeen && Date.now() - lastSeen < 5 * 60 * 1000;
  if (online) return { label: "Online", color: "text-green-400" };
  return { label: "Offline", color: "text-red-400" };
}

export default async function ServersPage() {
  const servers = await getServers();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Servers</h2>
          <p className="text-sm text-slate-400">Manage master and remote nodes.</p>
        </div>
        <Link
          href="/servers/new"
          className="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500"
        >
          Add Server
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {servers.map((server) => {
          const status = serverStatus(server);
          const metric = server.latest_metric;
          return (
            <div
              key={server.id}
              className="rounded border border-slate-800 bg-slate-950 p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">{server.name}</h3>
                  <p className="text-sm text-slate-400">{server.location || "N/A"}</p>
                </div>
                <div className="text-right text-sm">
                  <div className={`font-semibold ${status.color}`}>{status.label}</div>
                  <div className="text-xs text-slate-400">{server.is_master ? "Master" : "Agent"}</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div>
                  <div className="text-slate-400">CPU</div>
                  <div className="font-semibold">
                    {metric ? `${metric.cpu_percent.toFixed(1)}%` : "-"}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Memory</div>
                  <div className="font-semibold">
                    {metric ? `${metric.memory_percent.toFixed(1)}%` : "-"}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Disk</div>
                  <div className="font-semibold">
                    {metric ? `${metric.disk_percent.toFixed(1)}%` : "-"}
                  </div>
                </div>
              </div>
              <Link
                href={`/servers/${server.id}`}
                className="inline-flex text-sm text-blue-400 hover:text-blue-300"
              >
                View details →
              </Link>
            </div>
          );
        })}
        {servers.length === 0 && (
          <div className="text-slate-400">No servers configured yet. Add one to get started.</div>
        )}
      </div>
    </div>
  );
}
