import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <Link
          href="/login"
          className="px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-500"
        >
          Login
        </Link>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded border border-slate-800 bg-slate-950 p-4">
          <h3 className="text-lg font-semibold">Servers</h3>
          <p className="text-sm text-slate-400">Add master and agent nodes.</p>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-4">
          <h3 className="text-lg font-semibold">Applications</h3>
          <p className="text-sm text-slate-400">WordPress, Laravel, Node.js, databases and more.</p>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-4">
          <h3 className="text-lg font-semibold">DNS</h3>
          <p className="text-sm text-slate-400">Multi-provider DNS templates with PowerDNS.</p>
        </div>
        <div className="rounded border border-slate-800 bg-slate-950 p-4">
          <h3 className="text-lg font-semibold">Monitoring</h3>
          <p className="text-sm text-slate-400">CPU, RAM, disk and Docker health.</p>
        </div>
      </div>
    </div>
  );
}
