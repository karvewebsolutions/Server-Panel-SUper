"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  AppInstance,
  BackupJob,
  BackupSnapshot,
  getAppInstance,
  getAppInstanceBackups,
  runAppInstanceBackup,
  restoreAppInstanceBackup,
} from "../../../../lib/api";

export default function AppInstanceDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const appId = Number(params?.id);

  const [instance, setInstance] = useState<AppInstance | null>(null);
  const [backups, setBackups] = useState<BackupSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningJob, setRunningJob] = useState<BackupJob | null>(null);

  const loadData = async () => {
    if (!appId) return;
    setLoading(true);
    setError(null);
    try {
      const [appInstance, snapshots] = await Promise.all([
        getAppInstance(appId),
        getAppInstanceBackups(appId),
      ]);
      setInstance(appInstance);
      setBackups(snapshots);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load app instance");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId]);

  const triggerBackup = async () => {
    try {
      const job = await runAppInstanceBackup(appId);
      setRunningJob(job);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backup failed to start");
    }
  };

  const triggerRestore = async (snapshotId: number) => {
    try {
      await restoreAppInstanceBackup(appId, snapshotId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Restore failed to start");
    }
  };

  if (!appId) {
    return <div className="text-red-400">Invalid app instance ID.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">App Instance Details</h2>
          <p className="text-sm text-slate-400">Backup snapshots and recovery controls.</p>
        </div>
        <Link href="/apps/instances" className="text-sm text-blue-400 hover:text-blue-300">
          Back to list
        </Link>
      </div>

      {error && (
        <div className="rounded border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
          Loading instance...
        </div>
      ) : (
        <>
          {instance && (
            <div className="rounded border border-slate-800 bg-slate-950 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">{instance.display_name}</h3>
                  <div className="text-sm text-slate-400">Status: {instance.status}</div>
                  <div className="text-sm text-slate-400">Server: {instance.server_id}</div>
                </div>
                <button
                  type="button"
                  onClick={triggerBackup}
                  className="rounded bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500"
                >
                  Run Backup Now
                </button>
              </div>
              {runningJob && (
                <div className="mt-2 text-xs text-slate-400">
                  Last job status: {runningJob.status} {runningJob.error_message || ""}
                </div>
              )}
            </div>
          )}

          <div className="rounded border border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Backup Snapshots</h3>
              <span className="text-xs text-slate-400">{backups.length} snapshots</span>
            </div>
            {backups.length === 0 ? (
              <div className="mt-2 text-sm text-slate-400">No backups yet.</div>
            ) : (
              <div className="mt-3 divide-y divide-slate-800 border border-slate-800 rounded">
                {backups.map((snapshot) => (
                  <div key={snapshot.id} className="grid grid-cols-5 items-center gap-3 px-3 py-2 text-sm">
                    <div className="col-span-2">
                      <div className="font-semibold">{new Date(snapshot.created_at).toLocaleString()}</div>
                      <div className="text-xs text-slate-400">{snapshot.location_uri}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Size</div>
                      <div>{snapshot.size_bytes ? `${(snapshot.size_bytes / 1024 ** 2).toFixed(1)} MB` : "—"}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Status</div>
                      <div className="capitalize">{snapshot.job?.status ?? "success"}</div>
                    </div>
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => triggerRestore(snapshot.id)}
                        className="rounded border border-slate-700 px-3 py-1.5 text-xs hover:border-slate-500"
                      >
                        Restore
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
