"use client";

import { useState, useEffect } from "react";
import { Eye, EyeOff, Key, RefreshCw, Copy, Check, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [showToken, setShowToken] = useState(false);
  const [copied, setCopied] = useState(false);
  const [apiUrl, setApiUrl] = useState("https://open-queue-ivory.vercel.app");

  const [regenerating, setRegenerating] = useState(false);
  const [regenStatus, setRegenStatus] = useState<"idle" | "success" | "error">("idle");

  const [testing, setTesting] = useState(false);
  const [connStatus, setConnStatus] = useState<"idle" | "success" | "error">("idle");

  useEffect(() => {
    const storedToken = localStorage.getItem("api_token");
    const storedUrl = localStorage.getItem("api_url");
    if (storedToken) setToken(storedToken);
    if (storedUrl) setApiUrl(storedUrl);
  }, []);

  const maskedToken = token
    ? token.slice(0, 12) + "•".repeat(Math.max(token.length - 12, 8))
    : null;

  async function handleCopy() {
    if (!token) return;
    await navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function handleRegenerate() {
    if (
      !confirm(
        "This will invalidate your current token immediately.\n\n" +
          "Any API clients using the old token will stop working until updated.\n\n" +
          "Continue?"
      )
    )
      return;

    setRegenerating(true);
    setRegenStatus("idle");
    try {
      // Remove old token so the sync endpoint always issues a fresh one.
      localStorage.removeItem("api_token");
      const res = await fetch("/api/auth/sync", { method: "POST" });
      const data = await res.json();
      if (!res.ok || data.error) {
        setRegenStatus("error");
        // Restore previous token so the user isn't locked out.
        if (token) localStorage.setItem("api_token", token);
        return;
      }
      localStorage.setItem("api_token", data.token);
      if (data.api_url) localStorage.setItem("api_url", data.api_url);
      setToken(data.token);
      setShowToken(true); // reveal new token so user can copy it
      setRegenStatus("success");
    } catch {
      setRegenStatus("error");
      if (token) localStorage.setItem("api_token", token);
    } finally {
      setRegenerating(false);
    }
  }

  async function handleTestConnection() {
    setTesting(true);
    setConnStatus("idle");
    try {
      await api.healthCheck();
      setConnStatus("success");
    } catch {
      setConnStatus("error");
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl font-mono">
      <h1 className="text-xl font-bold text-[#00ff00]">SETTINGS</h1>

      {/* ── API Token ─────────────────────────────────────────────────────── */}
      <section className="border border-[#222] p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-[#1a1a1a] pb-3">
          <Key className="h-4 w-4 text-[#00ff00]" />
          <h2 className="text-sm font-bold text-white">API Token</h2>
        </div>

        {token ? (
          <>
            {/* Token display row */}
            <div className="flex items-stretch gap-2">
              <code className="flex-1 bg-black border border-[#333] px-3 py-2 text-xs text-[#00ff00] break-all">
                {showToken ? token : maskedToken}
              </code>
              <button
                onClick={() => setShowToken((v) => !v)}
                title={showToken ? "Hide token" : "Show token"}
                className="px-2 border border-[#333] text-[#555] hover:text-[#00ff00] transition-colors"
              >
                {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <button
                onClick={handleCopy}
                title="Copy token"
                className="px-2 border border-[#333] text-[#555] hover:text-[#00ff00] transition-colors"
              >
                {copied ? <Check className="h-4 w-4 text-[#00ff00]" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>

            <p className="text-xs text-[#555]">
              Your token is provisioned automatically when you sign in. Keep it secret — it grants
              full API access to your account.
            </p>

            {/* Regen status messages */}
            {regenStatus === "success" && (
              <div className="flex items-center gap-2 text-[#00ff00] text-xs">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Token regenerated. Copy it above — it will not be shown again after you leave.
              </div>
            )}
            {regenStatus === "error" && (
              <p className="text-xs text-red-400">
                Regeneration failed. Try signing out and back in.
              </p>
            )}

            {/* Regenerate button */}
            <div className="pt-1">
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="flex items-center gap-2 px-4 py-2 border border-[#333] text-xs text-[#666]
                           hover:text-[#ffcc00] hover:border-[#ffcc00] disabled:opacity-40 transition-colors"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${regenerating ? "animate-spin" : ""}`} />
                {regenerating ? "REGENERATING..." : "REGENERATE TOKEN"}
              </button>
              <p className="text-[10px] text-[#444] mt-2">
                Issues a new token and immediately invalidates the old one.
              </p>
            </div>
          </>
        ) : (
          <p className="text-xs text-[#555]">
            No token found. Sign out and sign back in to provision one.
          </p>
        )}
      </section>

      {/* ── API Endpoint ─────────────────────────────────────────────────── */}
      <section className="border border-[#222] p-5 space-y-4">
        <h2 className="text-sm font-bold text-white border-b border-[#1a1a1a] pb-3">
          API Endpoint
        </h2>

        <div className="flex items-stretch gap-2">
          <code className="flex-1 bg-[#0a0a0a] border border-[#222] px-3 py-2 text-xs text-[#00aaff]">
            {apiUrl}
          </code>
          <button
            onClick={handleTestConnection}
            disabled={testing || !token}
            className="px-4 border border-[#333] text-xs text-[#666]
                       hover:text-[#00ff00] hover:border-[#00ff00] disabled:opacity-40 transition-colors"
          >
            {testing ? "..." : "TEST"}
          </button>
        </div>

        {connStatus === "success" && (
          <p className="text-xs text-[#00ff00] flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" /> Connected successfully
          </p>
        )}
        {connStatus === "error" && (
          <p className="text-xs text-red-400">Connection failed. Check your token.</p>
        )}
      </section>
    </div>
  );
}
