"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Key, Save, AlertCircle, CheckCircle2, ExternalLink } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function SettingsPage() {
  const router = useRouter();
  const [apiToken, setApiToken] = useState("");
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"unknown" | "success" | "failed">("unknown");

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
      toast.success("Connection successful!");
    } catch {
      setConnectionStatus("failed");
      toast.error("Connection failed. Check your settings.");
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
      router.push("/");
    } finally {
      setLoading(false);
    }
  };

  const clearSettings = () => {
    localStorage.removeItem("api_token");
    localStorage.removeItem("api_url");
    setApiToken("");
    setApiUrl("http://localhost:8000");
    setConnectionStatus("unknown");
    toast.info("Settings cleared");
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Configuration
          </CardTitle>
          <CardDescription>
            Configure how the dashboard connects to your OpenQueue server
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="api-url">API URL</Label>
            <Input
              id="api-url"
              placeholder="http://localhost:8000"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
            />
            <p className="text-sm text-gray-500">
              The base URL of your OpenQueue API server
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="api-token">API Token</Label>
            <Input
              id="api-token"
              type="password"
              placeholder="Enter your API token"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
            />
            <p className="text-sm text-gray-500">
              Your OpenQueue API token for authentication
            </p>
          </div>

          {connectionStatus === "success" && (
            <div className="flex items-center gap-2 p-3 bg-green-50 text-green-600 rounded-lg">
              <CheckCircle2 className="h-5 w-5" />
              Connected successfully
            </div>
          )}

          {connectionStatus === "failed" && (
            <div className="flex items-center gap-2 p-3 bg-red-50 text-red-600 rounded-lg">
              <AlertCircle className="h-5 w-5" />
              Failed to connect. Check your settings.
            </div>
          )}

          <div className="flex gap-2 pt-4">
            <Button onClick={handleSave} disabled={loading || !apiToken}>
              <Save className="h-4 w-4 mr-2" />
              Save & Test
            </Button>
            <Button variant="outline" onClick={testConnection} disabled={testing || !apiToken}>
              Test Connection
            </Button>
            <Button variant="ghost" onClick={clearSettings}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Getting Your API Token</CardTitle>
          <CardDescription>
            Learn how to get your OpenQueue API token
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm">
              By default, OpenQueue creates a default user with the token:{" "}
              <code className="bg-gray-200 px-2 py-1 rounded text-sm">
                oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA
              </code>
            </p>
            <p className="text-sm text-gray-500 mt-2">
              For production, create additional users with unique tokens via the API.
            </p>
          </div>
          <Button variant="outline" asChild>
            <a href="https://github.com/ravin-d-27/OpenQueue" target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4 mr-2" />
              View Documentation
            </a>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Environment Variables</CardTitle>
          <CardDescription>
            Configure the dashboard via environment variables
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between p-3 bg-gray-50 rounded-lg">
              <code className="text-sm">NEXT_PUBLIC_API_URL</code>
              <span className="text-gray-500">API base URL</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
