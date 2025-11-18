import { getActivityLogs } from "../../lib/api";

export default async function ActivityPage() {
  const logs = await getActivityLogs({ limit: 100 });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Activity</h2>
          <p className="text-sm text-slate-400">Recent panel actions and authentication events.</p>
        </div>
      </div>

      <div className="rounded border border-slate-800 bg-slate-950">
        <div className="grid grid-cols-4 gap-2 px-4 py-2 text-sm text-slate-400 border-b border-slate-800">
          <div>Time</div>
          <div>User</div>
          <div>Action</div>
          <div>Metadata</div>
        </div>
        {logs.map((log) => (
          <div
            key={log.id}
            className="grid grid-cols-4 gap-2 px-4 py-3 text-sm items-center border-b border-slate-900"
          >
            <div className="text-slate-300">{new Date(log.created_at).toLocaleString()}</div>
            <div className="text-slate-200">{log.user_id ?? "-"}</div>
            <div className="font-semibold text-slate-100">{log.action}</div>
            <div className="text-slate-300 text-xs break-words">
              {log.metadata_json ? JSON.stringify(log.metadata_json) : "-"}
            </div>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="p-4 text-slate-400 text-sm">No activity recorded yet.</div>
        )}
      </div>
    </div>
  );
}
