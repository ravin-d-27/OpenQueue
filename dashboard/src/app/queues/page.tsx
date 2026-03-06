"use client";

import { useEffect, useState } from "react";
import {
  ListOrdered,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, QueueStats } from "@/lib/api";

export default function QueuesPage() {
  const [queues, setQueues] = useState<QueueStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQueues = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getQueueStats();
      setQueues(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch queues");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueues();
  }, []);

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

  if (loading && queues.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading queues...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Queues</h1>
        <Button onClick={fetchQueues} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-600 rounded-lg">
          <AlertCircle className="h-5 w-5" />
          {error}
        </div>
      )}

      {queues.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <ListOrdered className="h-12 w-12 text-gray-400 mb-4" />
            <p className="text-gray-500">No queues found</p>
            <p className="text-sm text-gray-400 mt-1">
              Enqueue a job to create a queue
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {queues.map((queue) => (
            <Card key={queue.queue_name}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{queue.queue_name}</CardTitle>
                  <div className="flex gap-2">
                    <Badge variant="outline" className="gap-1">
                      <Clock className="h-3 w-3" />
                      {queue.pending} pending
                    </Badge>
                    <Badge variant="outline" className="gap-1">
                      <ListOrdered className="h-3 w-3" />
                      {queue.processing} processing
                    </Badge>
                    <Badge variant="outline" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      {queue.completed} completed
                    </Badge>
                    <Badge variant="outline" className="gap-1">
                      <XCircle className="h-3 w-3" />
                      {queue.failed + queue.dead} failed
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">{queue.pending}</p>
                    <p className="text-sm text-gray-500">Pending</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{queue.processing}</p>
                    <p className="text-sm text-gray-500">Processing</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{queue.completed}</p>
                    <p className="text-sm text-gray-500">Completed</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-red-600">
                      {queue.failed + queue.dead}
                    </p>
                    <p className="text-sm text-gray-500">Failed</p>
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
