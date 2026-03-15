"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Key, Save, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function SettingsPage() {
  const router = useRouter();
  const [apiToken, setApiToken] = useState("");
  const [apiUrl, setApiUrl] = useState("https://open-queue-ivory.vercel.app");
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"unknown" | "success" | "failed">(
    "unknown"
  );

  useEffect(() => {
    const storedToken = localStorage.getItem("api_token");
    const storedUrl = localStorage.getItem("api_url");
    if (storedToken) setApiToken(storedToken);
    if (storedUrl) setApiUrl(storedUrl);
  }, []);

  const testConnection = async () => {
    setTesting(true);
    setConnectionStatus("unknown");
    try {
      localStorage.setItem("api_token", apiToken);
      localStorage.setItem("api_url", apiUrl);
      await api.healthCheck();
      setConnectionStatus("success");
      toast.success("Connected successfully");
    } catch {
      setConnectionStatus("failed");
      toast.error("Connection failed");
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      localStorage.setItem("api_token", apiToken);
      localStorage.setItem("api_url", apiUrl);
      await testConnection();
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const clearSettings = () => {
    localStorage.removeItem("api_token");
    localStorage.removeItem("api_url");
    setApiToken("");
    setApiUrl("https://open-queue-ivory.vercel.app");
    setConnectionStatus("unknown");
    toast.info("Settings cleared");
  };

  return (
    <div className="space-y-6 max-w-2xl font-mono">
      <h1 className="text-xl font-bold text-[#00ff00]">SETTINGS</h1>

      <Card className="bg-black border-[#333]">
        <CardHeader className="border-b border-[#222]">
          <CardTitle className="flex items-center gap-2 text-white">
            <Key className="h-4 w-4 text-[#00ff00]" />
            API Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="space-y-2">
            <Label htmlFor="api-url" className="text-[#666]">
              API URL
            </Label>
            <Input
              id="api-url"
              placeholder="https://open-queue-ivory.vercel.app"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="bg-black border-[#333] text-white placeholder:text-[#444]"
            />
            <p className="text-xs text-[#444]">The base URL of your OpenQueue API server</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="api-token" className="text-[#666]">
              API Token
            </Label>
            <Input
              id="api-token"
              type="password"
              placeholder="oq_live_..."
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              className="bg-black border-[#333] text-white placeholder:text-[#444]"
            />
            <p className="text-xs text-[#444]">
              Your API token is auto-configured on sign-in. You can override it here.
            </p>
          </div>

          {connectionStatus === "success" && (
            <div className="flex items-center gap-2 p-3 bg-[#00ff00]/10 text-[#00ff00] border border-[#00ff00]/30">
              <CheckCircle2 className="h-4 w-4" />
              Connected successfully
            </div>
          )}

          {connectionStatus === "failed" && (
            <div className="flex items-center gap-2 p-3 bg-red-900/20 text-red-400 border border-red-900/30">
              Connection failed. Check your settings.
            </div>
          )}

          <div className="flex gap-2 pt-4">
            <Button
              onClick={handleSave}
              disabled={loading || !apiToken}
              className="bg-[#00ff00] text-black hover:bg-[#00cc00]"
            >
              <Save className="h-4 w-4 mr-2" />
              SAVE
            </Button>
            <Button
              variant="outline"
              onClick={testConnection}
              disabled={testing || !apiToken}
              className="border-[#333] text-[#666] hover:text-[#00ff00] hover:border-[#00ff00] bg-transparent"
            >
              TEST
            </Button>
            <Button
              variant="ghost"
              onClick={clearSettings}
              className="text-[#444] hover:text-white"
            >
              CLEAR
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-black border-[#333]">
        <CardHeader className="border-b border-[#222]">
          <CardTitle className="text-white text-sm">ABOUT</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="p-3 bg-[#111] border border-[#222]">
            <p className="text-xs text-[#666] mb-2">API endpoint:</p>
            <code className="text-[#00aaff] text-sm">
              https://open-queue-ivory.vercel.app
            </code>
            <p className="text-xs text-[#444] mt-2">
              Your token is automatically provisioned when you sign in with Clerk.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
