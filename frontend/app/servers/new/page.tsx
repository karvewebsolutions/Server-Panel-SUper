"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createServer } from "../../../lib/serverApi";

export default function NewServerPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    description: "",
    is_master: false,
    agent_url: "",
    agent_token: "",
    location: "",
  });
  const [error, setError] = useState<string | null>(null);

  const handleChange = (key: string, value: any) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createServer({
        name: form.name,
        description: form.description || undefined,
        is_master: form.is_master,
        agent_url: form.agent_url || undefined,
        agent_token: form.agent_token || undefined,
        location: form.location || undefined,
      });
      router.push("/servers");
    } catch (err: any) {
      setError(err.message || "Failed to create server");
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Add Server</h2>
        <button onClick={() => router.back()} className="text-sm text-blue-400 hover:text-blue-300">
          Cancel
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4 bg-slate-950 border border-slate-800 p-5 rounded">
        <div className="space-y-1">
          <label className="text-sm font-medium">Name</label>
          <input
            required
            value={form.name}
            onChange={(e) => handleChange("name", e.target.value)}
            className="w-full rounded bg-slate-900 border border-slate-700 px-3 py-2"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => handleChange("description", e.target.value)}
            className="w-full rounded bg-slate-900 border border-slate-700 px-3 py-2"
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id="is_master"
            type="checkbox"
            checked={form.is_master}
            onChange={(e) => handleChange("is_master", e.target.checked)}
          />
          <label htmlFor="is_master" className="text-sm">
            Master server (use local Docker)
          </label>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Agent URL</label>
            <input
              value={form.agent_url}
              onChange={(e) => handleChange("agent_url", e.target.value)}
              className="w-full rounded bg-slate-900 border border-slate-700 px-3 py-2"
              placeholder="http://server:8001"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Agent Token</label>
            <input
              value={form.agent_token}
              onChange={(e) => handleChange("agent_token", e.target.value)}
              className="w-full rounded bg-slate-900 border border-slate-700 px-3 py-2"
              placeholder="secret token"
            />
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Location</label>
          <input
            value={form.location}
            onChange={(e) => handleChange("location", e.target.value)}
            className="w-full rounded bg-slate-900 border border-slate-700 px-3 py-2"
            placeholder="IN, EU, US, ..."
          />
        </div>
        {error && <div className="text-sm text-red-400">{error}</div>}
        <button
          type="submit"
          className="px-4 py-2 rounded bg-blue-600 text-white font-semibold hover:bg-blue-500"
        >
          Save Server
        </button>
      </form>
    </div>
  );
}
