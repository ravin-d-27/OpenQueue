"use client";

import { useState, useEffect } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UserButton } from "@clerk/nextjs";
import { api } from "@/lib/api";

export function Header() {
  const [isConnected, setIsConnected] = useState(false);
  const [checking, setChecking] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const checkConnection = async () => {
    setChecking(true);
    try {
      await api.healthCheck();
      setIsConnected(true);
      setLastUpdated(new Date());
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

  return (
    <header className="h-14 bg-black border-b border-[#333] px-6 flex items-center justify-between font-mono">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${isConnected ? "bg-[#00ff00]" : "bg-red-500"} ${
              checking ? "animate-pulse" : ""
            }`}
          />
          <span className="text-sm text-[#888]">
            {checking ? "checking..." : isConnected ? "connected" : "disconnected"}
          </span>
        </div>
        {lastUpdated && (
          <span className="text-xs text-[#444]">
            last check: {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={checkConnection}
          className="text-[#666] hover:text-[#00ff00] hover:bg-[#111]"
        >
          <RefreshCw className={`h-4 w-4 ${checking ? "animate-spin" : ""}`} />
        </Button>
        <UserButton afterSignOutUrl="/" />
      </div>
    </header>
  );
}
