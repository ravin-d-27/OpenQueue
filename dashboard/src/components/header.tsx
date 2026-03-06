"use client";

import { useState, useEffect } from "react";
import { Key, Bell, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export function Header() {
  const [isConnected, setIsConnected] = useState(false);
  const [checking, setChecking] = useState(true);

  const checkConnection = async () => {
    setChecking(true);
    try {
      await api.healthCheck();
      setIsConnected(true);
    } catch {
      setIsConnected(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const hasToken = typeof window !== "undefined" && !!localStorage.getItem("api_token");

  return (
    <header className="h-16 bg-white border-b px-6 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Badge variant={isConnected ? "default" : "destructive"}>
          {checking ? "Checking..." : isConnected ? "Connected" : "Disconnected"}
        </Badge>
        <Button variant="ghost" size="sm" onClick={checkConnection}>
          <RefreshCw className={`h-4 w-4 ${checking ? "animate-spin" : ""}`} />
        </Button>
      </div>
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm">
          <Bell className="h-5 w-5" />
        </Button>
        <Button
          variant={hasToken ? "outline" : "default"}
          size="sm"
          onClick={() => {
            if (!hasToken) {
              window.location.href = "/settings";
            }
          }}
        >
          <Key className="h-4 w-4 mr-2" />
          {hasToken ? "API Connected" : "Setup API Token"}
        </Button>
      </div>
    </header>
  );
}
