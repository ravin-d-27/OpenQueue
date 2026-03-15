"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ListOrdered,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, QueueStats } from "@/lib/api";
import { useCache } from "@/hooks/useCache";

export default function QueuesPage() {
  const [queues, setQueues] = useState<QueueStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchFn = useCallback(() => api.getQueueStats(), []);
  const { fetchData, getCached } = useCache<QueueStats[]>("queues_list", fetchFn, 30000);

  const fetchQueues = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchData();
      if (result.data) {
        setQueues(result.data);
        setLastUpdated(new Date());
      } else {
        const cached = getCached();
        if (cached?.data) {
          setQueues((prev) => (prev.length === 0 ? cached.data! : prev));
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch queues");
      const cached = getCached();
      if (cached?.data) {
        setQueues(cached.data);
      }
    } finally {
      setLoading(false);
    }
  }, [fetchData, getCached]);

  useEffect(() => {
    fetchQueues();
    const interval = setInterval(fetchQueues, 30000);
    return () => clearInterval(interval);
  }, [fetchQueues]);

  if (loading && queues.length === 0) {
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
          <h1 className="text-xl font-bold text-[#00ff00]">QUEUES</h1>
          <p className="text-xs text-[#444] mt-1">
            {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : "Initializing..."}
          </p>
        </div>
        <Button
          onClick={fetchQueues}
          variant="outline"
          size="sm"
          className="border-[#333] text-[#666] hover:text-[#00ff00] hover:border-[#00ff00] bg-transparent"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          REFRESH
        </Button>
      </div>

      {error && queues.length === 0 && (
        <div className="border border-red-900 bg-red-950/30 p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      {queues.length === 0 ? (
        <Card className="bg-black border-[#333]">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <ListOrdered className="h-12 w-12 text-[#333] mb-4" />
            <p className="text-[#666]">No queues found</p>
            <p className="text-xs text-[#444] mt-1">Enqueue a job to create a queue</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {queues.map((queue) => (
            <Card key={queue.queue_name} className="bg-black border-[#333]">
              <CardHeader className="pb-3 border-b border-[#222]">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white text-lg">{queue.queue_name}</CardTitle>
                  <div className="flex gap-3 text-xs">
                    <span className="text-[#ffff00]">{queue.pending} pending</span>
                    <span className="text-[#00aaff]">{queue.processing} processing</span>
                    <span className="text-[#00ff00]">{queue.completed} completed</span>
                    <span className="text-[#ff0000]">{queue.failed + queue.dead} failed</span>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold text-[#ffff00]">{queue.pending}</p>
                    <p className="text-xs text-[#444]">PENDING</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-[#00aaff]">{queue.processing}</p>
                    <p className="text-xs text-[#444]">PROCESSING</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-[#00ff00]">{queue.completed}</p>
                    <p className="text-xs text-[#444]">COMPLETED</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-[#ff0000]">
                      {queue.failed + queue.dead}
                    </p>
                    <p className="text-xs text-[#444]">FAILED</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
