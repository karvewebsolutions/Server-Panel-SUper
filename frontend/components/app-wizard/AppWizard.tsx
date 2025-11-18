 "use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  AppBlueprint,
  Application,
  CreateAppInstanceRequest,
  Domain,
  DomainMappingInput,
  Server,
  createAppInstance,
  getAppBlueprints,
  getApplications,
  getDomains,
  getServers,
  suggestSubdomain,
} from "../../lib/api";

type DomainRow = DomainMappingInput & { id: string };

const steps = ["App Type", "Server", "Domains", "Review"];

const generateRowId = () =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

export function AppWizard() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [blueprints, setBlueprints] = useState<AppBlueprint[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);

  const [selectedBlueprint, setSelectedBlueprint] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [serverId, setServerId] = useState<number | null>(null);
  const [domainRows, setDomainRows] = useState<DomainRow[]>([
    { id: generateRowId(), is_primary: true },
  ]);

  useEffect(() => {
    async function load() {
      try {
        const [blueprintData, serverData, domainData, applicationData] = await Promise.all([
          getAppBlueprints(),
          getServers(),
          getDomains(),
          getApplications(),
        ]);
        setBlueprints(blueprintData);
        setServers(serverData);
        setDomains(domainData);
        setApplications(applicationData);
        if (blueprintData.length > 0 && !selectedBlueprint) {
          setSelectedBlueprint(blueprintData[0].type);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load wizard data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (!displayName && selectedBlueprint) {
      setDisplayName(`${selectedBlueprint}-app`);
    }
  }, [selectedBlueprint, displayName]);

  const selectedBlueprintDetails = useMemo(
    () => blueprints.find((bp) => bp.type === selectedBlueprint),
    [blueprints, selectedBlueprint],
  );

  const selectedApplication = useMemo(() => {
    if (!selectedBlueprint) {
      return null;
    }
    return (
      applications.find(
        (app) =>
          app.slug === selectedBlueprint ||
          app.type === selectedBlueprint ||
          app.name.toLowerCase() === selectedBlueprint,
      ) ?? applications[0] ?? null
    );
  }, [applications, selectedBlueprint]);

  const canProceed = useMemo(() => {
    switch (step) {
      case 1:
        return Boolean(selectedBlueprint && displayName.trim());
      case 2:
        return Boolean(serverId);
      case 3:
        return domainRows.some((row) => row.domain_id);
      case 4:
        return true;
      default:
        return false;
    }
  }, [step, selectedBlueprint, displayName, serverId, domainRows]);

  const handleNext = () => {
    if (step < steps.length && canProceed) {
      setStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep((prev) => prev - 1);
    }
  };

  const updateDomainRow = (id: string, updates: Partial<DomainRow>) => {
    setDomainRows((rows) =>
      rows.map((row) => (row.id === id ? { ...row, ...updates } : row)),
    );
  };

  const handleSetPrimary = (id: string) => {
    setDomainRows((rows) =>
      rows.map((row) => ({ ...row, is_primary: row.id === id })),
    );
  };

  const handleAddDomainRow = () => {
    setDomainRows((rows) => [...rows, { id: generateRowId(), is_primary: rows.length === 0 }]);
  };

  const handleRemoveDomainRow = (id: string) => {
    setDomainRows((rows) => {
      const filtered = rows.filter((row) => row.id !== id);
      if (filtered.length === 0) {
        return [{ id: generateRowId(), is_primary: true }];
      }
      if (!filtered.some((row) => row.is_primary)) {
        filtered[0].is_primary = true;
      }
      return [...filtered];
    });
  };

  const handleSuggestSubdomain = async (row: DomainRow) => {
    if (!row.domain_id || !displayName.trim()) {
      setError("Select a domain and provide an app name before suggesting.");
      return;
    }
    try {
      const suggested = await suggestSubdomain(row.domain_id, displayName);
      updateDomainRow(row.id, { subdomain: suggested });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to suggest subdomain");
    }
  };

  const handleDeploy = async () => {
    if (!selectedBlueprint || !serverId) {
      return;
    }
    if (!selectedApplication) {
      setError("No application blueprint available. Please create one first.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    const sanitizedDomains = domainRows
      .filter((row) => row.domain_id)
      .map((row) => ({
        domain_id: row.domain_id as number,
        subdomain: row.subdomain?.trim() || undefined,
        is_primary: Boolean(row.is_primary),
      }));
    const payload: CreateAppInstanceRequest = {
      app_id: selectedApplication.id,
      server_id: serverId,
      display_name: displayName.trim(),
      app_type: selectedBlueprint,
      config: {
        docker_image: selectedBlueprintDetails?.docker_image,
        docker_port: selectedBlueprintDetails?.docker_port,
      },
      domains: sanitizedDomains,
    };
    try {
      const instance = await createAppInstance(payload);
      router.push(`/apps/instances?created=${instance.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deployment failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStepContent = () => {
    if (loading) {
      return (
        <div className="rounded border border-slate-800 bg-slate-950 p-6 text-sm text-slate-400">
          Loading wizard data...
        </div>
      );
    }

    switch (step) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              {blueprints.map((bp) => (
                <button
                  key={bp.type}
                  type="button"
                  onClick={() => setSelectedBlueprint(bp.type)}
                  className={`rounded border p-4 text-left transition ${
                    selectedBlueprint === bp.type
                      ? "border-emerald-500 bg-emerald-500/10"
                      : "border-slate-800 bg-slate-950 hover:border-slate-700"
                  }`}
                >
                  <div className="text-lg font-semibold capitalize">{bp.type}</div>
                  <p className="text-sm text-slate-400">
                    Image: {bp.docker_image ?? "Custom"} · Port: {bp.docker_port ?? 80}
                  </p>
                </button>
              ))}
            </div>
            <div>
              <label className="text-sm text-slate-400">App Display Name</label>
              <input
                type="text"
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                className="mt-1 w-full rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                placeholder="e.g. Marketing Site"
              />
            </div>
          </div>
        );
      case 2:
        return (
          <div className="space-y-4">
            <label className="text-sm text-slate-400">Target Server</label>
            <select
              value={serverId ?? ""}
              onChange={(event) => setServerId(Number(event.target.value) || null)}
              className="w-full rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
            >
              <option value="">Select a server</option>
              {servers.map((server) => (
                <option key={server.id} value={server.id}>
                  {server.name} {server.location ? `— ${server.location}` : ""}
                </option>
              ))}
            </select>
          </div>
        );
      case 3:
        return (
          <div className="space-y-4">
            {domainRows.map((row) => {
              const domain = domains.find((d) => d.id === row.domain_id);
              const fqdn = domain
                ? `${row.subdomain ? `${row.subdomain}.` : ""}${domain.domain_name}`
                : "Select a domain";
              return (
                <div
                  key={row.id}
                  className="space-y-3 rounded border border-slate-800 bg-slate-950 p-4"
                >
                  <div className="grid gap-3 md:grid-cols-[2fr,2fr,auto]">
                    <select
                      value={row.domain_id ?? ""}
                      onChange={(event) =>
                        updateDomainRow(row.id, { domain_id: Number(event.target.value) || undefined })
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
                      placeholder="Subdomain (optional)"
                      className="rounded border border-slate-800 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => handleSetPrimary(row.id)}
                      className={`rounded px-3 py-2 text-sm font-medium transition ${
                        row.is_primary
                          ? "bg-emerald-600 text-white"
                          : "border border-slate-700 text-slate-300 hover:border-slate-500"
                      }`}
                    >
                      {row.is_primary ? "Primary" : "Make Primary"}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-3 text-sm text-slate-400">
                    <span>FQDN: {fqdn}</span>
                    <button
                      type="button"
                      onClick={() => handleSuggestSubdomain(row)}
                      className="text-emerald-400 hover:text-emerald-300"
                    >
                      Suggest subdomain
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemoveDomainRow(row.id)}
                      className="text-rose-400 hover:text-rose-300"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              );
            })}
            <button
              type="button"
              onClick={handleAddDomainRow}
              className="rounded border border-slate-700 px-3 py-2 text-sm hover:border-emerald-500"
            >
              + Add domain mapping
            </button>
          </div>
        );
      case 4:
        return (
          <div className="space-y-4 rounded border border-slate-800 bg-slate-950 p-4">
            <div>
              <h3 className="text-sm text-slate-400">App Type</h3>
              <p className="text-lg font-semibold capitalize">{selectedBlueprint}</p>
            </div>
            <div>
              <h3 className="text-sm text-slate-400">Server</h3>
              <p className="text-lg font-semibold">
                {servers.find((server) => server.id === serverId)?.name ?? "—"}
              </p>
            </div>
            <div>
              <h3 className="text-sm text-slate-400">Domains</h3>
              <ul className="text-sm text-slate-300">
                {domainRows
                  .filter((row) => row.domain_id)
                  .map((row) => {
                    const domain = domains.find((d) => d.id === row.domain_id);
                    const fqdn = domain
                      ? `${row.subdomain ? `${row.subdomain}.` : ""}${domain.domain_name}`
                      : null;
                    return (
                      <li key={row.id}>
                        {fqdn} {row.is_primary ? "(primary)" : ""}
                      </li>
                    );
                  })}
              </ul>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">App Creation Wizard</h2>
        <p className="text-sm text-slate-400">
          Deploy a new application with automated domain and DNS wiring.
        </p>
      </div>

      <div className="flex items-center gap-4">
        {steps.map((label, index) => {
          const stepNumber = index + 1;
          const isActive = stepNumber === step;
          const isComplete = stepNumber < step;
          return (
            <div key={label} className="flex items-center gap-2 text-sm">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border text-sm font-semibold ${
                  isActive
                    ? "border-emerald-500 text-emerald-400"
                    : isComplete
                      ? "border-slate-600 bg-slate-800 text-white"
                      : "border-slate-700 text-slate-500"
                }`}
              >
                {stepNumber}
              </div>
              <span className={isActive ? "text-white" : "text-slate-400"}>{label}</span>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="rounded border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      {renderStepContent()}

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={handleBack}
          disabled={step === 1 || isSubmitting}
          className="rounded border border-slate-700 px-4 py-2 text-sm disabled:opacity-50"
        >
          Back
        </button>
        {step < steps.length && (
          <button
            type="button"
            disabled={!canProceed || isSubmitting}
            onClick={handleNext}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Next
          </button>
        )}
        {step === steps.length && (
          <button
            type="button"
            onClick={handleDeploy}
            disabled={isSubmitting || !canProceed}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {isSubmitting ? "Deploying..." : "Deploy"}
          </button>
        )}
      </div>
    </div>
  );
}
