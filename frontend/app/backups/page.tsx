"use client";

import { useEffect, useMemo, useState } from "react";

import {
  BackupPolicy,
  BackupTarget,
  createBackupPolicy,
  createBackupTarget,
  getBackupPolicies,
  getBackupTargets,
} from "../../lib/api";

export default function BackupsPage() {
  const [targets, setTargets] = useState<BackupTarget[]>([]);
  const [policies, setPolicies] = useState<BackupPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [targetForm, setTargetForm] = useState({
    name: "",
    type: "local",
    base_path: "/backups",
    endpoint_url: "",
    bucket: "",
    access_key: "",
    secret_key: "",
    region: "",
    host: "",
    port: "22",
    username: "",
    password: "",
  });

  const [policyForm, setPolicyForm] = useState({
    name: "",
    scope_type: "app_instance",
    scope_id: "",
    schedule_cron: "0 3 * * *",
    backup_target_id: "",
    retain_last: "5",
    is_enabled: true,
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [targetsData, policiesData] = await Promise.all([
        getBackupTargets(),
        getBackupPolicies(),
      ]);
      setTargets(targetsData);
      setPolicies(policiesData);
      if (!policyForm.backup_target_id && targetsData.length) {
        setPolicyForm((prev) => ({ ...prev, backup_target_id: String(targetsData[0].id) }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load backup data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const targetConfig = useMemo(() => {
    if (targetForm.type === "local") {
      return { base_path: targetForm.base_path };
    }
    if (targetForm.type === "s3") {
      return {
        endpoint_url: targetForm.endpoint_url || undefined,
        bucket: targetForm.bucket,
        access_key: targetForm.access_key,
        secret_key: targetForm.secret_key,
        region: targetForm.region,
      };
    }
    return {
      host: targetForm.host,
      port: Number(targetForm.port) || 22,
      username: targetForm.username,
      password: targetForm.password,
      base_path: targetForm.base_path || "/backups",
    };
  }, [targetForm]);

  const submitTarget = async () => {
    try {
      await createBackupTarget({
        name: targetForm.name,
        type: targetForm.type,
        config_json: targetConfig,
        is_default: targets.length === 0,
      });
      setTargetForm((prev) => ({ ...prev, name: "" }));
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create backup target");
    }
  };

  const submitPolicy = async () => {
    try {
      await createBackupPolicy({
        name: policyForm.name,
        scope_type: policyForm.scope_type,
        scope_id: policyForm.scope_id ? Number(policyForm.scope_id) : undefined,
        schedule_cron: policyForm.schedule_cron || undefined,
        backup_target_id: Number(policyForm.backup_target_id),
        retain_last: policyForm.retain_last ? Number(policyForm.retain_last) : undefined,
        is_enabled: policyForm.is_enabled,
      });
      setPolicyForm((prev) => ({ ...prev, name: "" }));
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create backup policy");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Backups</h2>
          <p className="text-sm text-slate-400">Configure backup targets and policies.</p>
        </div>
      </div>

      {error && (
        <div className="rounded border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
          Loading backup data...
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3 rounded border border-slate-800 bg-slate-950 p-4">
            <h3 className="text-lg font-semibold">Backup Targets</h3>
            <div className="space-y-2 text-sm text-slate-300">
              {targets.length === 0 && <div className="text-slate-500">No targets yet.</div>}
              {targets.map((target) => (
                <div key={target.id} className="rounded border border-slate-800 bg-slate-900/60 p-3">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold">{target.name}</div>
                    {target.is_default && (
                      <span className="rounded bg-emerald-600/10 px-2 py-0.5 text-xs text-emerald-200">
                        Default
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400">Type: {target.type}</div>
                  <div className="mt-1 text-xs text-slate-400">
                    {(() => {
                      const basePath =
                        typeof target.config_json["base_path"] === "string"
                          ? target.config_json["base_path"]
                          : "";
                      const bucket =
                        typeof target.config_json["bucket"] === "string"
                          ? target.config_json["bucket"]
                          : "";
                      const endpoint = basePath || bucket;
                      return `Path/Endpoint: ${endpoint || "N/A"}`;
                    })()}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 space-y-2 border-t border-slate-800 pt-3">
              <h4 className="text-sm font-semibold">Add Target</h4>
              <input
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                placeholder="Name"
                value={targetForm.name}
                onChange={(e) => setTargetForm({ ...targetForm, name: e.target.value })}
              />
              <select
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                value={targetForm.type}
                onChange={(e) => setTargetForm({ ...targetForm, type: e.target.value })}
              >
                <option value="local">Local</option>
                <option value="s3">S3</option>
                <option value="sftp">SFTP</option>
              </select>
              {targetForm.type === "local" && (
                <input
                  className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                  placeholder="Base path (e.g., /backups)"
                  value={targetForm.base_path}
                  onChange={(e) => setTargetForm({ ...targetForm, base_path: e.target.value })}
                />
              )}
              {targetForm.type === "s3" && (
                <div className="space-y-2">
                  <input
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Bucket"
                    value={targetForm.bucket}
                    onChange={(e) => setTargetForm({ ...targetForm, bucket: e.target.value })}
                  />
                  <input
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Endpoint URL (optional)"
                    value={targetForm.endpoint_url}
                    onChange={(e) => setTargetForm({ ...targetForm, endpoint_url: e.target.value })}
                  />
                  <input
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Region"
                    value={targetForm.region}
                    onChange={(e) => setTargetForm({ ...targetForm, region: e.target.value })}
                  />
                  <input
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Access key"
                    value={targetForm.access_key}
                    onChange={(e) => setTargetForm({ ...targetForm, access_key: e.target.value })}
                  />
                  <input
                    className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Secret key"
                    type="password"
                    value={targetForm.secret_key}
                    onChange={(e) => setTargetForm({ ...targetForm, secret_key: e.target.value })}
                  />
                </div>
              )}
              {targetForm.type === "sftp" && (
                <div className="grid grid-cols-2 gap-2">
                  <input
                    className="col-span-2 rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Host"
                    value={targetForm.host}
                    onChange={(e) => setTargetForm({ ...targetForm, host: e.target.value })}
                  />
                  <input
                    className="rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Port"
                    value={targetForm.port}
                    onChange={(e) => setTargetForm({ ...targetForm, port: e.target.value })}
                  />
                  <input
                    className="rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Username"
                    value={targetForm.username}
                    onChange={(e) => setTargetForm({ ...targetForm, username: e.target.value })}
                  />
                  <input
                    className="rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                    placeholder="Password"
                    type="password"
                    value={targetForm.password}
                    onChange={(e) => setTargetForm({ ...targetForm, password: e.target.value })}
                  />
                </div>
              )}
              <button
                type="button"
                onClick={submitTarget}
                className="rounded bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500"
              >
                Save Target
              </button>
            </div>
          </div>

          <div className="space-y-3 rounded border border-slate-800 bg-slate-950 p-4">
            <h3 className="text-lg font-semibold">Backup Policies</h3>
            <div className="space-y-2 text-sm text-slate-300">
              {policies.length === 0 && <div className="text-slate-500">No policies yet.</div>}
              {policies.map((policy) => (
                <div key={policy.id} className="rounded border border-slate-800 bg-slate-900/60 p-3">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold">{policy.name}</div>
                    {!policy.is_enabled && (
                      <span className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-200">
                        Disabled
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400">
                    Scope: {policy.scope_type} {policy.scope_id ?? "global"}
                  </div>
                  <div className="text-xs text-slate-400">Schedule: {policy.schedule_cron || "manual"}</div>
                  <div className="text-xs text-slate-400">Target: {policy.backup_target_id}</div>
                  {policy.retain_last && (
                    <div className="text-xs text-slate-400">Retain last {policy.retain_last}</div>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-4 space-y-2 border-t border-slate-800 pt-3">
              <h4 className="text-sm font-semibold">Add Policy</h4>
              <input
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                placeholder="Name"
                value={policyForm.name}
                onChange={(e) => setPolicyForm({ ...policyForm, name: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  className="rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                  value={policyForm.scope_type}
                  onChange={(e) => setPolicyForm({ ...policyForm, scope_type: e.target.value })}
                >
                  <option value="app_instance">App Instance</option>
                  <option value="server">Server</option>
                  <option value="database">Database</option>
                </select>
                <input
                  className="rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                  placeholder="Scope ID (optional)"
                  value={policyForm.scope_id}
                  onChange={(e) => setPolicyForm({ ...policyForm, scope_id: e.target.value })}
                />
              </div>
              <input
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                placeholder="Cron expression"
                value={policyForm.schedule_cron}
                onChange={(e) => setPolicyForm({ ...policyForm, schedule_cron: e.target.value })}
              />
              <select
                className="w-full rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                value={policyForm.backup_target_id}
                onChange={(e) => setPolicyForm({ ...policyForm, backup_target_id: e.target.value })}
              >
                <option value="">Select target</option>
                {targets.map((target) => (
                  <option key={target.id} value={target.id}>
                    {target.name}
                  </option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="rounded border border-slate-700 bg-slate-900 p-2 text-sm"
                  placeholder="Retain last N"
                  value={policyForm.retain_last}
                  onChange={(e) => setPolicyForm({ ...policyForm, retain_last: e.target.value })}
                />
                <label className="flex items-center gap-2 text-sm text-slate-200">
                  <input
                    type="checkbox"
                    checked={policyForm.is_enabled}
                    onChange={(e) => setPolicyForm({ ...policyForm, is_enabled: e.target.checked })}
                  />
                  Enabled
                </label>
              </div>
              <button
                type="button"
                onClick={submitPolicy}
                className="rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
              >
                Save Policy
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
