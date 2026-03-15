"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { format } from "date-fns";
import {
  ArrowLeft,
  RefreshCw,
  Beaker,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api, Job } from "@/lib/api";
import { toast } from "sonner";

const statusLabels: Record<string, string> = {
  pending: "PENDING",
  processing: "PROCESSING",
  completed: "COMPLETED",
  failed: "FAILED",
  dead: "DEAD",
  cancelled: "CANCELLED",
};

const statusColors: Record<string, string> = {
  pending: "text-[#ffff00]",
  processing: "text-[#00aaff]",
  completed: "text-[#00ff00]",
  failed: "text-[#ff0000]",
  dead: "text-[#ff0000]",
  cancelled: "text-[#666]",
};

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchJob = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getJob(jobId);
      setJob(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch job");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  const handleCancel = async () => {
    try {
      await api.cancelJob(jobId);
      toast.success("Job cancelled");
      fetchJob();
    } catch {
      toast.error("Failed to cancel job");
    }
  };

  useEffect(() => {
    fetchJob();
    const interval = setInterval(fetchJob, 30000);
    return () => clearInterval(interval);
  }, [fetchJob]);

  if (loading && !job) {
    return (
      <div className="flex items-center justify-center h-64 font-mono">
        <span className="text-[#666]">Loading...</span>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="space-y-4 font-mono">
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="text-[#666] hover:text-white"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          BACK
        </Button>
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <Beaker className="h-8 w-8 text-[#333]" />
          <p className="text-[#666]">{error || "Job not found"}</p>
          <Button onClick={fetchJob} className="bg-[#00ff00] text-black hover:bg-[#00cc00]">
            RETRY
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="text-[#666] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            BACK
          </Button>
          <div>
            <h1 className="text-xl font-bold text-[#00ff00]">JOB DETAILS</h1>
            <p className="text-xs text-[#444] mt-1">
              {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : ""}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={fetchJob}
            className="border-[#333] text-[#666] hover:text-[#00ff00] hover:border-[#00ff00] bg-transparent"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            REFRESH
          </Button>
          {job.status === "pending" && (
            <Button
              variant="destructive"
              onClick={handleCancel}
              className="bg-red-900 text-white hover:bg-red-800"
            >
              CANCEL
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="bg-black border-[#333]">
          <CardHeader className="border-b border-[#222]">
            <CardTitle className="text-white text-sm">JOB INFORMATION</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex justify-between">
              <span className="text-[#666]">Job ID</span>
              <code className="text-xs text-[#00aaff]">{job.id}</code>
            </div>
            <div className="flex justify-between">
              <span className="text-[#666]">Queue</span>
              <span className="text-white">{job.queue_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#666]">Status</span>
              <span className={statusColors[job.status]}>{statusLabels[job.status]}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#666]">Priority</span>
              <span className="text-white">{job.priority}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#666]">Retries</span>
              <span className="text-white">
                {job.retry_count} / {job.max_retries}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-black border-[#333]">
          <CardHeader className="border-b border-[#222]">
            <CardTitle className="text-white text-sm">TIMESTAMPS</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex justify-between">
              <span className="text-[#666]">Created</span>
              <span className="text-white text-sm">
                {job.created_at ? format(new Date(job.created_at), "yyyy-MM-dd HH:mm:ss") : "—"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#666]">Scheduled</span>
              <span className="text-white text-sm">
                {job.run_at ? format(new Date(job.run_at), "yyyy-MM-dd HH:mm:ss") : "—"}
              </span>
            </div>
            {job.started_at && (
              <div className="flex justify-between">
                <span className="text-[#666]">Started</span>
                <span className="text-white text-sm">
                  {format(new Date(job.started_at), "yyyy-MM-dd HH:mm:ss")}
                </span>
              </div>
            )}
            {job.finished_at && (
              <div className="flex justify-between">
                <span className="text-[#666]">Finished</span>
                <span className="text-white text-sm">
                  {format(new Date(job.finished_at), "yyyy-MM-dd HH:mm:ss")}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-[#666]">Updated</span>
              <span className="text-white text-sm">
                {job.updated_at ? format(new Date(job.updated_at), "yyyy-MM-dd HH:mm:ss") : "—"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2 bg-black border-[#333]">
          <CardHeader className="border-b border-[#222]">
            <CardTitle className="text-[#00ff00] text-sm">PAYLOAD</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-[#0a0a0a] p-4 border border-[#222] overflow-x-auto text-sm text-[#00ff00]">
              {JSON.stringify(job.payload, null, 2)}
            </pre>
          </CardContent>
        </Card>

        {job.result && (
          <Card className="lg:col-span-2 bg-black border-[#333]">
            <CardHeader className="border-b border-[#222]">
              <CardTitle className="text-[#00ff00] text-sm">RESULT</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-[#0a0a0a] p-4 border border-[#222] overflow-x-auto text-sm text-[#00ff00]">
                {JSON.stringify(job.result, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {job.error_text && (
          <Card className="lg:col-span-2 bg-black border-[#ff0000]/30">
            <CardHeader className="border-b border-[#ff0000]/30">
              <CardTitle className="text-[#ff0000] text-sm">ERROR</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-[#1a0a0a] p-4 border border-[#ff0000]/30 overflow-x-auto text-sm text-[#ff0000]">
                {job.error_text}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
