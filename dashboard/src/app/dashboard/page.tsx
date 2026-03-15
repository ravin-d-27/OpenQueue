"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  ListOrdered,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, QueueStats } from "@/lib/api";
import { useCache } from "@/hooks/useCache";

export default function DashboardPage() {
  const [stats, setStats] = useState<QueueStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchFn = useCallback(() => api.getQueueStats(), []);
  const { fetchData, getCached } = useCache<QueueStats[]>("queue_stats", fetchFn, 30000);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchData();
      if (result.data) {
        setStats(result.data);
        setLastUpdated(new Date());
      } else {
        const cached = getCached();
        if (cached?.data) {
          setStats((prev) => (prev.length === 0 ? cached.data! : prev));
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch stats");
      const cached = getCached();
      if (cached?.data) {
        setStats(cached.data);
      }
    } finally {
      setLoading(false);
    }
  }, [fetchData, getCached]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const totalPending = stats.reduce((sum, q) => sum + q.pending, 0);
  const totalProcessing = stats.reduce((sum, q) => sum + q.processing, 0);
  const totalCompleted = stats.reduce((sum, q) => sum + q.completed, 0);
  const totalFailed = stats.reduce((sum, q) => sum + q.failed + q.dead, 0);

  const StatBox = ({
    label,
    value,
    icon: Icon,
    accent,
  }: {
    label: string;
    value: number;
    icon: React.ElementType;
    accent: string;
  }) => (
    <div className="border border-[#333] bg-black p-4">
      <div className="flex items-center justify-between">
        <span className="text-[#666] text-sm font-mono">{label}</span>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <div className="mt-2 text-2xl font-mono font-bold text-white">{value}</div>
    </div>
  );

  if (loading && stats.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 font-mono">
        <span className="text-[#666]">Loading...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#00ff00]">DASHBOARD</h1>
          <p className="text-xs text-[#444] mt-1">
            {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : "Initializing..."}
          </p>
        </div>
        <Button
          onClick={fetchStats}
          variant="outline"
          size="sm"
          className="border-[#333] text-[#666] hover:text-[#00ff00] hover:border-[#00ff00] bg-transparent"
        >
          REFRESH
        </Button>
      </div>

      {error && stats.length === 0 && (
        <div className="border border-red-900 bg-red-950/30 p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatBox label="PENDING" value={totalPending} icon={Clock} accent="text-[#ffff00]" />
        <StatBox label="PROCESSING" value={totalProcessing} icon={ListOrdered} accent="text-[#00aaff]" />
        <StatBox label="COMPLETED" value={totalCompleted} icon={CheckCircle2} accent="text-[#00ff00]" />
        <StatBox label="FAILED" value={totalFailed} icon={XCircle} accent="text-[#ff0000]" />
      </div>

      <Card className="bg-black border-[#333]">
        <CardHeader className="flex flex-row items-center justify-between border-b border-[#333]">
          <CardTitle className="text-[#00ff00] text-sm">QUEUES</CardTitle>
          <Button asChild variant="ghost" size="sm" className="text-[#666] hover:text-[#00ff00]">
            <Link href="/dashboard/queues">
              VIEW ALL <ArrowRight className="ml-2 h-3 w-3" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent className="pt-4">
          {stats.length === 0 ? (
            <div className="text-center py-8 text-[#444]">No queues found</div>
          ) : (
            <div className="space-y-2">
              {stats.slice(0, 5).map((queue) => (
                <div
                  key={queue.queue_name}
                  className="flex items-center justify-between p-3 bg-[#0a0a0a] border border-[#222]"
                >
                  <div>
                    <p className="text-white font-medium">{queue.queue_name}</p>
                    <p className="text-xs text-[#444]">
                      {queue.pending + queue.processing} active
                    </p>
                  </div>
                  <div className="flex gap-3 text-xs">
                    <span className="text-[#ffff00]">{queue.pending} pending</span>
                    <span className="text-[#00aaff]">{queue.processing} processing</span>
                    <span className="text-[#00ff00]">{queue.completed} completed</span>
                    {(queue.failed > 0 || queue.dead > 0) && (
                      <span className="text-[#ff0000]">{queue.failed + queue.dead} failed</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
