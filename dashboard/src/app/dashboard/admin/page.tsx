"use client";

import { useState } from "react";

export default function AdminPage() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<{
    token?: string;
    email?: string;
    created?: boolean;
    error?: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleProvision(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("/api/admin/provision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) {
        setResult({ error: data.error || "unknown_error" });
      } else {
        setResult(data);
        setEmail("");
      }
    } catch {
      setResult({ error: "network_error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6 font-mono">
      <div>
        <h1 className="text-xl font-bold text-[#00ff00]">ADMIN / PROVISION USER</h1>
        <p className="text-sm text-[#666] mt-1">
          Add a new user or regenerate their API token. The token is shown once — save it.
        </p>
      </div>

      <form onSubmit={handleProvision} className="space-y-4">
        <div>
          <label className="block text-xs text-[#666] mb-1 uppercase tracking-wider">
            User Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="user@example.com"
            required
            className="w-full bg-[#111] border border-[#333] text-white px-3 py-2 text-sm
                       focus:outline-none focus:border-[#00ff00] placeholder-[#444]"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !email}
          className="px-4 py-2 bg-[#00ff00] text-black text-sm font-bold
                     hover:bg-[#00cc00] disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors"
        >
          {loading ? "PROVISIONING..." : "ADD USER"}
        </button>
      </form>

      {result && (
        <div
          className={`border p-4 text-sm ${
            result.error
              ? "border-red-800 bg-red-950/30 text-red-400"
              : "border-[#00ff00]/40 bg-[#001100]/50 text-[#00ff00]"
          }`}
        >
          {result.error ? (
            <p>
              <span className="font-bold">ERROR:</span> {result.error}
            </p>
          ) : (
            <div className="space-y-2">
              <p>
                <span className="text-[#666]">email: </span>
                {result.email}
              </p>
              <p>
                <span className="text-[#666]">status: </span>
                {result.created ? "created" : "token regenerated"}
              </p>
              <div>
                <p className="text-[#666] mb-1">api token (save this — shown once):</p>
                <code className="block bg-black border border-[#333] px-3 py-2 text-[#00ff00] break-all">
                  {result.token}
                </code>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
