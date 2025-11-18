"use client";

import { useState } from "react";
import { pingServer } from "../../../lib/serverApi";

export function PingButton({ serverId }: { serverId: number }) {
  const [status, setStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const handlePing = async () => {
    setLoading(true);
    setStatus("");
    try {
      const result = await pingServer(serverId);
      setStatus(result.status || "ok");
    } catch (err: any) {
      setStatus(err.message || "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handlePing}
        disabled={loading}
        className="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-60"
      >
        {loading ? "Pinging..." : "Ping Now"}
      </button>
      {status && <span className="text-sm text-slate-300">Status: {status}</span>}
    </div>
  );
}
