"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  AppInstance,
  Application,
  AttachDomainsRequest,
  Domain,
  DomainMappingInput,
  Server,
  attachAppDomains,
  getAppInstances,
  getApplications,
  getAppInstanceLogs,
  getDomains,
  getServers,
  restartAppInstance,
  stopAppInstance,
  suggestSubdomain,
} from "../../../lib/api";

type DomainRow = DomainMappingInput & { id: string };

const createRow = (overrides?: Partial<DomainRow>): DomainRow => ({
  id:
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2),
  is_primary: false,
  ...overrides,
});

export default function AppInstancesPage() {
  const [instances, setInstances] = useState<AppInstance[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [logsModal, setLogsModal] = useState<{ open: boolean; title: string; logs: string }>({
    open: false,
    title: "",
    logs: "",
  });
  const [domainModal, setDomainModal] = useState<{ open: boolean; instance: AppInstance | null }>(
    { open: false, instance: null },
  );
  const [domainRows, setDomainRows] = useState<DomainRow[]>([]);
  const [modalError, setModalError] = useState<string | null>(null);
  const [modalSubmitting, setModalSubmitting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [instancesData, serversData, appsData, domainsData] = await Promise.all([
        getAppInstances(),
        getServers(),
        getApplications(),
        getDomains(),
      ]);
      setInstances(instancesData);
      setServers(serversData);
      setApplications(appsData);
      setDomains(domainsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load app instances");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const serverMap = useMemo(
    () => new Map(servers.map((server) => [server.id, server])),
    [servers],
  );
  const appMap = useMemo(
    () => new Map(applications.map((app) => [app.id, app])),
    [applications],
  );

  const primaryDomainFor = (instance: AppInstance) => {
    const mapping =
      instance.domain_mappings.find((m) => m.is_primary) ?? instance.domain_mappings[0];
    if (!mapping || !mapping.domain) {
      return "—";
    }
    const prefix = mapping.subdomain ? `${mapping.subdomain}.` : "";
    return `${prefix}${mapping.domain.domain_name}`;
  };

  const handleStop = async (instance: AppInstance) => {
    try {
      await stopAppInstance(instance.id);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to stop app");
    }
  };

  const handleRestart = async (instance: AppInstance) => {
    try {
      await restartAppInstance(instance.id);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to restart app");
    }
  };

  const openLogs = async (instance: AppInstance) => {
    try {
      const logs = await getAppInstanceLogs(instance.id, 200);
      setLogsModal({
        open: true,
        title: `${instance.display_name} logs`,
        logs,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load logs");
    }
  };

  const openDomainManager = (instance: AppInstance) => {
    const rows =
      instance.domain_mappings.length > 0
        ? instance.domain_mappings.map((mapping) =>
            createRow({
              domain_id: mapping.domain_id,
              subdomain: mapping.subdomain ?? undefined,
              is_primary: mapping.is_primary,
            }),
          )
        : [createRow({ is_primary: true })];
    setDomainRows(rows);
    setModalError(null);
    setDomainModal({ open: true, instance });
  };

  const updateDomainRow = (rowId: string, updates: Partial<DomainRow>) => {
    setDomainRows((rows) => rows.map((row) => (row.id === rowId ? { ...row, ...updates } : row)));
  };

  const setPrimaryRow = (rowId: string) => {
    setDomainRows((rows) => rows.map((row) => ({ ...row, is_primary: row.id === rowId })));
  };

  const addDomainRow = () => {
    setDomainRows((rows) => [...rows, createRow({ is_primary: rows.length === 0 })]);
  };

  const removeDomainRow = (rowId: string) => {
    setDomainRows((rows) => {
      const remaining = rows.filter((row) => row.id !== rowId);
      if (remaining.length === 0) {
        return [createRow({ is_primary: true })];
      }
      if (!remaining.some((row) => row.is_primary)) {
        remaining[0].is_primary = true;
      }
      return [...remaining];
    });
  };

  const submitDomainChanges = async () => {
    const instance = domainModal.instance;
    if (!instance) return;
    const payload: AttachDomainsRequest = {
      domains: domainRows
        .filter((row) => row.domain_id)
        .map((row) => ({
          domain_id: row.domain_id as number,
          subdomain: row.subdomain?.trim() || undefined,
          is_primary: Boolean(row.is_primary),
        })),
    };
    if (payload.domains.length === 0) {
      setModalError("Select at least one domain.");
      return;
    }
    setModalSubmitting(true);
    setModalError(null);
    try {
      await attachAppDomains(instance.id, payload);
      setDomainModal({ open: false, instance: null });
      await loadData();
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Failed to update domains");
    } finally {
      setModalSubmitting(false);
    }
  };

  const suggestForRow = async (row: DomainRow) => {
    const instance = domainModal.instance;
    if (!instance || !row.domain_id) {
      setModalError("Select a domain before requesting a suggestion.");
      return;
    }
    try {
      const suggested = await suggestSubdomain(row.domain_id, instance.display_name);
      updateDomainRow(row.id, { subdomain: suggested });
      setModalError(null);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : "Unable to suggest subdomain");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold">App Instances</h2>
          <p className="text-sm text-slate-400">Manage running applications and routing.</p>
        </div>
        <Link
          href="/apps/new"
          className="rounded bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
        >
          New App
        </Link>
      </div>

      {error && (
        <div className="rounded border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="rounded border border-slate-800 bg-slate-950 p-6 text-sm text-slate-400">
          Loading app instances...
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {instances.map((instance) => (
            <div key={instance.id} className="rounded border border-slate-800 bg-slate-950 p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">{instance.display_name}</h3>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                    instance.status === "running"
                      ? "bg-emerald-500/10 text-emerald-300"
                      : instance.status === "error"
                        ? "bg-rose-500/10 text-rose-300"
                        : "bg-slate-700/40 text-slate-200"
                  }`}
                >
                  {instance.status}
                </span>
              </div>
              <dl className="mt-3 space-y-1 text-sm text-slate-300">
                <div className="flex justify-between">
                  <dt className="text-slate-400">App type</dt>
                  <dd>{appMap.get(instance.app_id)?.type ?? "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Server</dt>
                  <dd>{serverMap.get(instance.server_id)?.name ?? "—"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-400">Primary domain</dt>
                  <dd>{primaryDomainFor(instance)}</dd>
                </div>
              </dl>
              <div className="mt-4 flex flex-wrap gap-2 text-sm">
                <button
                  type="button"
                  onClick={() => handleStop(instance)}
                  className="rounded border border-slate-700 px-3 py-1.5 hover:border-slate-500"
                >
                  Stop
                </button>
                <button
                  type="button"
                  onClick={() => handleRestart(instance)}
                  className="rounded border border-slate-700 px-3 py-1.5 hover:border-slate-500"
                >
                  Restart
                </button>
                <button
                  type="button"
                  onClick={() => openLogs(instance)}
                  className="rounded border border-slate-700 px-3 py-1.5 hover:border-slate-500"
                >
                  View Logs
                </button>
                <button
                  type="button"
                  onClick={() => openDomainManager(instance)}
                  className="rounded border border-emerald-600 px-3 py-1.5 text-emerald-300 hover:border-emerald-400"
                >
                  Manage Domains
                </button>
                <Link
                  href={`/apps/instances/${instance.id}`}
                  className="rounded border border-slate-700 px-3 py-1.5 hover:border-slate-500"
                >
                  Backups
                </Link>
              </div>
            </div>
          ))}
          {instances.length === 0 && (
            <div className="rounded border border-slate-800 bg-slate-950 p-6 text-sm text-slate-400">
              No app instances yet. Deploy your first app from the wizard.
            </div>
          )}
        </div>
      )}

      {logsModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-3xl rounded border border-slate-700 bg-slate-900 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{logsModal.title}</h3>
              <button
                type="button"
                onClick={() => setLogsModal({ open: false, title: "", logs: "" })}
                className="text-sm text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
            <pre className="mt-4 max-h-[60vh] overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-200">
              {logsModal.logs || "No logs yet."}
            </pre>
          </div>
        </div>
      )}

      {domainModal.open && domainModal.instance && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-2xl space-y-4 rounded border border-slate-700 bg-slate-900 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">Manage Domains</h3>
                <p className="text-sm text-slate-400">{domainModal.instance.display_name}</p>
              </div>
              <button
                type="button"
                onClick={() => setDomainModal({ open: false, instance: null })}
                className="text-sm text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
            {modalError && (
              <div className="rounded border border-rose-500/40 bg-rose-500/10 p-2 text-sm text-rose-100">
                {modalError}
              </div>
            )}
            <div className="space-y-3">
              {domainRows.map((row) => {
                const domain = domains.find((d) => d.id === row.domain_id);
                const fqdn = domain
                  ? `${row.subdomain ? `${row.subdomain}.` : ""}${domain.domain_name}`
                  : "Select a domain";
                return (
                  <div key={row.id} className="rounded border border-slate-800 bg-slate-950 p-3">
                    <div className="grid gap-3 md:grid-cols-[2fr,2fr,auto]">
                      <select
                        value={row.domain_id ?? ""}
                        onChange={(event) =>
                          updateDomainRow(row.id, {
                            domain_id: Number(event.target.value) || undefined,
                          })
                        }
                        className="rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                      >
                        <option value="">Domain</option>
                        {domains.map((domainOption) => (
                          <option key={domainOption.id} value={domainOption.id}>
                            {domainOption.domain_name}
                          </option>
                        ))}
                      </select>
                      <input
                        type="text"
                        value={row.subdomain ?? ""}
                        onChange={(event) =>
                          updateDomainRow(row.id, { subdomain: event.target.value })
                        }
                        placeholder="Subdomain"
                        className="rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => setPrimaryRow(row.id)}
                        className={`rounded px-3 py-2 text-sm ${
                          row.is_primary
                            ? "bg-emerald-600 text-white"
                            : "border border-slate-700 text-slate-300"
                        }`}
                      >
                        {row.is_primary ? "Primary" : "Make Primary"}
                      </button>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                      <span>{fqdn}</span>
                      <div className="flex gap-3">
                        <button
                          type="button"
                          onClick={() => suggestForRow(row)}
                          className="text-emerald-300 hover:text-emerald-200"
                        >
                          Suggest
                        </button>
                        <button
                          type="button"
                          onClick={() => removeDomainRow(row.id)}
                          className="text-rose-400 hover:text-rose-300"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <button
              type="button"
              onClick={addDomainRow}
              className="rounded border border-slate-700 px-3 py-2 text-sm hover:border-emerald-500"
            >
              + Add domain
            </button>
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={submitDomainChanges}
                disabled={modalSubmitting}
                className="rounded bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {modalSubmitting ? "Saving..." : "Apply"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
