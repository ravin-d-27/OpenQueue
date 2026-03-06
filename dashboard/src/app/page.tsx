"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ListOrdered,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatsCard } from "@/components/stats-card";
import { api, QueueStats } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<QueueStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getQueueStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  const totalPending = stats.reduce((sum, q) => sum + q.pending, 0);
  const totalProcessing = stats.reduce((sum, q) => sum + q.processing, 0);
  const totalCompleted = stats.reduce((sum, q) => sum + q.completed, 0);
  const totalFailed = stats.reduce((sum, q) => sum + q.failed + q.dead, 0);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "processing":
        return "bg-blue-100 text-blue-800";
      case "completed":
        return "bg-green-100 text-green-800";
      case "failed":
      case "dead":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  if (loading && stats.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="h-8 w-8 text-red-500" />
        <p className="text-gray-500">{error}</p>
        <Button onClick={fetchStats}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard Overview</h1>
        <Button onClick={fetchStats} variant="outline" size="sm">
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Pending"
          value={totalPending}
          icon={<Clock className="h-5 w-5 text-yellow-600" />}
        />
        <StatsCard
          title="Processing"
          value={totalProcessing}
          icon={<ListOrdered className="h-5 w-5 text-blue-600" />}
        />
        <StatsCard
          title="Completed"
          value={totalCompleted}
          icon={<CheckCircle2 className="h-5 w-5 text-green-600" />}
        />
        <StatsCard
          title="Failed / Dead"
          value={totalFailed}
          icon={<XCircle className="h-5 w-5 text-red-600" />}
        />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Queue Overview</CardTitle>
          <Button asChild variant="ghost" size="sm">
            <Link href="/queues">
              View All <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {stats.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No queues found. Create a job to get started.
            </div>
          ) : (
            <div className="space-y-4">
              {stats.slice(0, 5).map((queue) => (
                <div
                  key={queue.queue_name}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div>
                    <p className="font-medium">{queue.queue_name}</p>
                    <p className="text-sm text-gray-500">
                      {queue.pending + queue.processing} active jobs
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Badge className={getStatusColor("pending")}>
                      {queue.pending} pending
                    </Badge>
                    <Badge className={getStatusColor("processing")}>
                      {queue.processing} processing
                    </Badge>
                    <Badge className={getStatusColor("completed")}>
                      {queue.completed} completed
                    </Badge>
                    {(queue.failed > 0 || queue.dead > 0) && (
                      <Badge className={getStatusColor("failed")}>
                        {queue.failed + queue.dead} failed
                      </Badge>
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
