"use client";
import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@karve.fun");
  const [password, setPassword] = useState("admin123");

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    alert(`Login placeholder: ${email}`);
  };

  return (
    <div className="max-w-md mx-auto space-y-4">
      <div>
        <h2 className="text-2xl font-bold">Login</h2>
        <p className="text-sm text-slate-400">
          Enter the default admin credentials to access the panel.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4 bg-slate-950 p-4 rounded border border-slate-800">
        <div className="space-y-1">
          <label className="text-sm font-medium">Email</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            className="w-full rounded bg-slate-900 border border-slate-700 px-3 py-2"
            required
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Password</label>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            className="w-full rounded bg-slate-900 border border-slate-700 px-3 py-2"
            required
          />
        </div>
        <button
          type="submit"
          className="w-full rounded bg-blue-600 hover:bg-blue-500 px-3 py-2 font-semibold"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
