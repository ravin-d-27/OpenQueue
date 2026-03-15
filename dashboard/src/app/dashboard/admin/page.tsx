"use client";

import { useState, useEffect, useCallback } from "react";
import { format } from "date-fns";

// ── Types ────────────────────────────────────────────────────────────────────

interface Overview {
  total_users: number;
  active_users: number;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  pending_jobs: number;
  processing_jobs: number;
  jobs_24h: number;
  jobs_7d: number;
}

interface UserStat {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  last_seen_at: string | null;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  pending_jobs: number;
  processing_jobs: number;
  jobs_24h: number;
  jobs_7d: number;
  active_queues: number;
}

interface SignupRequest {
  id: string;
  email: string;
  clerk_id: string | null;
  requested_at: string;
}

type Tab = "overview" | "pending" | "users";

// ── Helpers ──────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: number | string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className="border border-[#222] bg-[#0a0a0a] p-4 space-y-1">
      <p className="text-[10px] text-[#555] uppercase tracking-widest">{label}</p>
      <p className={`text-2xl font-bold ${highlight ? "text-[#00ff00]" : "text-white"}`}>
        {value}
      </p>
      {sub && <p className="text-[10px] text-[#444]">{sub}</p>}
    </div>
  );
}

function pct(n: number, total: number) {
  if (total === 0) return "—";
  return `${Math.round((n / total) * 100)}%`;
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>("overview");

  // ── Stats ──────────────────────────────────────────────────────────────────
  const [overview, setOverview] = useState<Overview | null>(null);
  const [userStats, setUserStats] = useState<UserStat[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const res = await fetch("/api/admin/stats");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "failed");
      setOverview(data.overview);
      setUserStats(data.users);
    } catch (err) {
      setStatsError(err instanceof Error ? err.message : "Failed to load stats");
    } finally {
      setStatsLoading(false);
    }
  }, []);

  // ── Pending signups ────────────────────────────────────────────────────────
  const [signups, setSignups] = useState<SignupRequest[]>([]);
  const [signupsLoading, setSignupsLoading] = useState(true);
  const [signupsError, setSignupsError] = useState<string | null>(null);
  const [approvingEmail, setApprovingEmail] = useState<string | null>(null);
  const [rejectingEmail, setRejectingEmail] = useState<string | null>(null);
  const [approveResult, setApproveResult] = useState<{
    email: string;
    token?: string;
    error?: string;
  } | null>(null);

  const fetchSignups = useCallback(async () => {
    setSignupsLoading(true);
    setSignupsError(null);
    try {
      const res = await fetch("/api/admin/signups");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "failed");
      setSignups(data.signups);
    } catch (err) {
      setSignupsError(err instanceof Error ? err.message : "Failed to load signups");
    } finally {
      setSignupsLoading(false);
    }
  }, []);

  // ── Deactivate ─────────────────────────────────────────────────────────────
  const [deactivating, setDeactivating] = useState<string | null>(null);

  // ── Provision form (manual) ────────────────────────────────────────────────
  const [manualEmail, setManualEmail] = useState("");
  const [provisioning, setProvisioning] = useState(false);
  const [provisionResult, setProvisionResult] = useState<{
    token?: string;
    email?: string;
    created?: boolean;
    error?: string;
  } | null>(null);

  // ── Load on mount ──────────────────────────────────────────────────────────
  useEffect(() => {
    fetchStats();
    fetchSignups();
  }, [fetchStats, fetchSignups]);

  // ── Handlers ───────────────────────────────────────────────────────────────

  async function handleApprove(email: string) {
    setApprovingEmail(email);
    setApproveResult(null);
    try {
      const res = await fetch("/api/admin/provision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) {
        setApproveResult({ email, error: data.error || "provision_failed" });
      } else {
        setApproveResult({ email, token: data.token });
        fetchSignups();
        fetchStats();
      }
    } catch {
      setApproveResult({ email, error: "network_error" });
    } finally {
      setApprovingEmail(null);
    }
  }

  async function handleReject(email: string) {
    if (!confirm(`Reject signup request from ${email}?`)) return;
    setRejectingEmail(email);
    try {
      const res = await fetch("/api/admin/signups", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const data = await res.json();
        alert(`Error: ${data.error}`);
      } else {
        fetchSignups();
      }
    } catch {
      alert("Network error");
    } finally {
      setRejectingEmail(null);
    }
  }

  async function handleDeactivate(email: string) {
    if (!confirm(`Deactivate ${email}?`)) return;
    setDeactivating(email);
    try {
      const res = await fetch("/api/admin/users", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`Error: ${data.error}`);
      } else {
        fetchStats();
      }
    } catch {
      alert("Network error");
    } finally {
      setDeactivating(null);
    }
  }

  async function handleManualProvision(e: React.FormEvent) {
    e.preventDefault();
    if (!manualEmail) return;
    setProvisioning(true);
    setProvisionResult(null);
    try {
      const res = await fetch("/api/admin/provision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: manualEmail }),
      });
      const data = await res.json();
      if (!res.ok) {
        setProvisionResult({ error: data.error || "unknown_error" });
      } else {
        setProvisionResult(data);
        setManualEmail("");
        fetchStats();
        fetchSignups();
      }
    } catch {
      setProvisionResult({ error: "network_error" });
    } finally {
      setProvisioning(false);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 font-mono max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#00ff00]">ADMIN</h1>
        <p className="text-xs text-[#444] mt-1">Platform management</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-0 border-b border-[#222]">
        {(["overview", "pending", "users"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-5 py-2 text-xs uppercase tracking-widest transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-[#00ff00] text-[#00ff00]"
                : "border-transparent text-[#555] hover:text-[#888]"
            }`}
          >
            {t}
            {t === "pending" && signups.length > 0 && (
              <span className="ml-1.5 bg-[#00ff00] text-black text-[9px] font-bold px-1 rounded-sm">
                {signups.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW tab ── */}
      {tab === "overview" && (
        <div className="space-y-6">
          {statsLoading ? (
            <p className="text-xs text-[#444]">Loading...</p>
          ) : statsError ? (
            <p className="text-xs text-red-400">Error: {statsError}</p>
          ) : overview ? (
            <>
              {/* Users row */}
              <div>
                <p className="text-[10px] text-[#555] uppercase tracking-widest mb-3">Users</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatCard label="Total Users" value={overview.total_users} />
                  <StatCard
                    label="Active Users"
                    value={overview.active_users}
                    sub={`${pct(overview.active_users, overview.total_users)} of total`}
                    highlight
                  />
                </div>
              </div>

              {/* Jobs row */}
              <div>
                <p className="text-[10px] text-[#555] uppercase tracking-widest mb-3">Jobs</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatCard label="Total Jobs" value={overview.total_jobs} />
                  <StatCard
                    label="Completed"
                    value={overview.completed_jobs}
                    sub={pct(overview.completed_jobs, overview.total_jobs) + " success rate"}
                    highlight
                  />
                  <StatCard
                    label="Failed / Dead"
                    value={overview.failed_jobs}
                    sub={pct(overview.failed_jobs, overview.total_jobs) + " failure rate"}
                  />
                  <StatCard
                    label="Pending / Processing"
                    value={overview.pending_jobs + overview.processing_jobs}
                    sub={`${overview.pending_jobs} pending, ${overview.processing_jobs} running`}
                  />
                </div>
              </div>

              {/* Activity row */}
              <div>
                <p className="text-[10px] text-[#555] uppercase tracking-widest mb-3">Activity</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatCard label="Jobs (24 h)" value={overview.jobs_24h} highlight />
                  <StatCard label="Jobs (7 d)" value={overview.jobs_7d} />
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* ── PENDING tab ── */}
      {tab === "pending" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-[#555]">
              Users who signed up and are awaiting admin approval.
            </p>
            <button
              onClick={fetchSignups}
              className="text-xs text-[#444] hover:text-[#00ff00] transition-colors"
            >
              REFRESH
            </button>
          </div>

          {/* Approve result banner */}
          {approveResult && (
            <div
              className={`border p-4 text-xs ${
                approveResult.error
                  ? "border-red-800 bg-red-950/30 text-red-400"
                  : "border-[#00ff00]/40 bg-[#001100]/50 text-[#00ff00]"
              }`}
            >
              {approveResult.error ? (
                <p>
                  <span className="font-bold">ERROR</span> approving {approveResult.email}:{" "}
                  {approveResult.error}
                </p>
              ) : (
                <div className="space-y-2">
                  <p>
                    Approved <span className="font-bold">{approveResult.email}</span>. Token shown
                    once — share with user:
                  </p>
                  <code className="block bg-black border border-[#333] px-3 py-2 text-[#00ff00] break-all">
                    {approveResult.token}
                  </code>
                  <button
                    onClick={() => setApproveResult(null)}
                    className="text-[10px] text-[#555] hover:text-[#888] uppercase"
                  >
                    dismiss
                  </button>
                </div>
              )}
            </div>
          )}

          {signupsLoading ? (
            <p className="text-xs text-[#444]">Loading...</p>
          ) : signupsError ? (
            <p className="text-xs text-red-400">Error: {signupsError}</p>
          ) : signups.length === 0 ? (
            <p className="text-xs text-[#444]">No pending signups.</p>
          ) : (
            <div className="border border-[#222] overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#222] text-[#555]">
                    <th className="text-left px-3 py-2">EMAIL</th>
                    <th className="text-left px-3 py-2">ACCOUNT</th>
                    <th className="text-left px-3 py-2">REQUESTED</th>
                    <th className="px-3 py-2 text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {signups.map((s) => (
                    <tr
                      key={s.id}
                      className="border-b border-[#111] hover:bg-[#0a0a0a] transition-colors"
                    >
                      <td className="px-3 py-2 text-white">{s.email}</td>
                      <td className="px-3 py-2 text-[#555]">
                        {s.clerk_id ? (
                          <span className="text-[#00aaff]">linked</span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-3 py-2 text-[#555]">
                        {format(new Date(s.requested_at), "MMM d, HH:mm")}
                      </td>
                      <td className="px-3 py-2 text-right space-x-3">
                        <button
                          onClick={() => handleApprove(s.email)}
                          disabled={approvingEmail === s.email}
                          className="text-[#00ff00] hover:text-[#00cc00] disabled:opacity-40
                                     transition-colors uppercase font-bold"
                        >
                          {approvingEmail === s.email ? "..." : "approve"}
                        </button>
                        <button
                          onClick={() => handleReject(s.email)}
                          disabled={rejectingEmail === s.email}
                          className="text-[#555] hover:text-red-400 disabled:opacity-40
                                     transition-colors uppercase"
                        >
                          {rejectingEmail === s.email ? "..." : "reject"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Manual invite section */}
          <div className="mt-8 space-y-3 border-t border-[#1a1a1a] pt-6">
            <p className="text-[10px] text-[#555] uppercase tracking-widest">
            Manual Invite
            </p>
            <p className="text-xs text-[#444]">
              Creates an account and returns a one-time API token. Share the token with the user.
            </p>
            <form onSubmit={handleManualProvision} className="flex gap-3 items-end">
              <div className="flex-1">
                <input
                  type="email"
                  value={manualEmail}
                  onChange={(e) => setManualEmail(e.target.value)}
                  placeholder="user@example.com"
                  required
                  className="w-full bg-[#111] border border-[#333] text-white px-3 py-2 text-sm
                             focus:outline-none focus:border-[#00ff00] placeholder-[#444]"
                />
              </div>
              <button
                type="submit"
                disabled={provisioning || !manualEmail}
                className="px-4 py-2 bg-[#00ff00] text-black text-sm font-bold
                           hover:bg-[#00cc00] disabled:opacity-40 disabled:cursor-not-allowed
                           transition-colors whitespace-nowrap"
              >
                {provisioning ? "PROVISIONING..." : "INVITE"}
              </button>
            </form>
            {provisionResult && (
              <div
                className={`border p-4 text-xs ${
                  provisionResult.error
                    ? "border-red-800 bg-red-950/30 text-red-400"
                    : "border-[#00ff00]/40 bg-[#001100]/50 text-[#00ff00]"
                }`}
              >
                {provisionResult.error ? (
                  <p>
                    <span className="font-bold">ERROR:</span> {provisionResult.error}
                  </p>
                ) : (
                  <div className="space-y-2">
                    <p>
                      <span className="text-[#555]">email: </span>
                      {provisionResult.email}{"  "}
                      <span className="text-[#555]">status: </span>
                      {provisionResult.created ? "created" : "token regenerated"}
                    </p>
                    <div>
                      <p className="text-[#555] mb-1">API TOKEN — copy now, not shown again:</p>
                      <code className="block bg-black border border-[#333] px-3 py-2 text-[#00ff00] break-all">
                        {provisionResult.token}
                      </code>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── USERS tab ── */}
      {tab === "users" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-[#555]">
              All provisioned users and their aggregate stats.
            </p>
            <button
              onClick={fetchStats}
              className="text-xs text-[#444] hover:text-[#00ff00] transition-colors"
            >
              REFRESH
            </button>
          </div>

          {statsLoading ? (
            <p className="text-xs text-[#444]">Loading...</p>
          ) : statsError ? (
            <p className="text-xs text-red-400">Error: {statsError}</p>
          ) : userStats.length === 0 ? (
            <p className="text-xs text-[#444]">No users yet.</p>
          ) : (
            <div className="border border-[#222] overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#222] text-[#555]">
                    <th className="text-left px-3 py-2">EMAIL</th>
                    <th className="text-left px-3 py-2">STATUS</th>
                    <th className="text-right px-3 py-2">API CALLS</th>
                    <th className="text-right px-3 py-2">COMPLETED</th>
                    <th className="text-right px-3 py-2">FAILED</th>
                    <th className="text-right px-3 py-2">24 H</th>
                    <th className="text-right px-3 py-2">QUEUES</th>
                    <th className="text-left px-3 py-2">LAST SEEN</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {userStats.map((u) => (
                    <tr
                      key={u.id}
                      className="border-b border-[#111] hover:bg-[#0a0a0a] transition-colors"
                    >
                      <td className="px-3 py-2 text-white">{u.email}</td>
                      <td className="px-3 py-2">
                        <span className={u.is_active ? "text-[#00ff00]" : "text-[#555]"}>
                          {u.is_active ? "active" : "inactive"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right text-white">{u.total_jobs}</td>
                      <td className="px-3 py-2 text-right text-[#00ff00]">{u.completed_jobs}</td>
                      <td className="px-3 py-2 text-right text-[#555]">{u.failed_jobs}</td>
                      <td className="px-3 py-2 text-right text-[#888]">{u.jobs_24h}</td>
                      <td className="px-3 py-2 text-right text-[#555]">{u.active_queues}</td>
                      <td className="px-3 py-2 text-[#555]">
                        {u.last_seen_at
                          ? format(new Date(u.last_seen_at), "MMM d, HH:mm")
                          : "never"}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {u.is_active && (
                          <button
                            onClick={() => handleDeactivate(u.email)}
                            disabled={deactivating === u.email}
                            className="text-[#555] hover:text-red-400 disabled:opacity-40
                                       transition-colors uppercase"
                          >
                            {deactivating === u.email ? "..." : "deactivate"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
