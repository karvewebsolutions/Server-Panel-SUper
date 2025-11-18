import { AckButton } from "./AckButton";
import { getAlerts } from "../../lib/api";

const severityBadge: Record<string, string> = {
  critical: "bg-red-900/60 text-red-100",
  warning: "bg-amber-900/60 text-amber-100",
  info: "bg-slate-800 text-slate-100",
};

export default async function AlertsPage() {
  const alerts = await getAlerts({ limit: 50 });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Alerts</h2>
          <p className="text-sm text-slate-400">Monitor infrastructure and application issues.</p>
        </div>
      </div>

      <div className="rounded border border-slate-800 bg-slate-950">
        <div className="grid grid-cols-6 gap-2 px-4 py-2 text-sm text-slate-400 border-b border-slate-800">
          <div>Time</div>
          <div>Rule</div>
          <div>Scope</div>
          <div>Severity</div>
          <div>Status</div>
          <div></div>
        </div>
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="grid grid-cols-6 gap-2 px-4 py-3 text-sm items-center border-b border-slate-900"
          >
            <div className="text-slate-300">
              {new Date(alert.created_at).toLocaleString()}
            </div>
            <div className="font-semibold text-slate-100">{alert.rule_id}</div>
            <div className="text-slate-300">{alert.scope_type}</div>
            <div>
              <span
                className={`text-xs px-2 py-1 rounded ${severityBadge[alert.severity] || severityBadge.info}`}
              >
                {alert.severity}
              </span>
            </div>
            <div className="text-slate-300">
              {alert.is_acknowledged ? "Acknowledged" : "Unacked"}
            </div>
            <div className="text-right">
              <AckButton id={alert.id} disabled={alert.is_acknowledged} />
            </div>
          </div>
        ))}
        {alerts.length === 0 && (
          <div className="p-4 text-slate-400 text-sm">No alerts generated yet.</div>
        )}
      </div>
    </div>
  );
}
