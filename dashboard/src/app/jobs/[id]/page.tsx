"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { format } from "date-fns";
import {
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
  Beaker,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { api, Job } from "@/lib/api";
import { toast } from "sonner";

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  dead: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-800",
};

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJob = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getJob(jobId);
      setJob(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch job");
    } finally {
      setLoading(false);
    }
  };

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
  }, [jobId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading job...</div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <AlertCircle className="h-8 w-8 text-red-500" />
          <p className="text-gray-500">{error || "Job not found"}</p>
          <Button onClick={fetchJob}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <h1 className="text-2xl font-bold">Job Details</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchJob}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {job.status === "pending" && (
            <Button variant="destructive" onClick={handleCancel}>
              Cancel Job
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Job Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-500">Job ID</span>
              <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                {job.id}
              </code>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Queue</span>
              <span className="font-medium">{job.queue_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Status</span>
              <Badge className={statusColors[job.status]}>{job.status}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Priority</span>
              <span>{job.priority}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Retries</span>
              <span>
                {job.retry_count} / {job.max_retries}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Timestamps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-500">Created</span>
              <span className="text-sm">
                {format(new Date(job.created_at), "PPpp")}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Scheduled (run_at)</span>
              <span className="text-sm">
                {format(new Date(job.run_at), "PPpp")}
              </span>
            </div>
            {job.started_at && (
              <div className="flex justify-between">
                <span className="text-gray-500">Started</span>
                <span className="text-sm">
                  {format(new Date(job.started_at), "PPpp")}
                </span>
              </div>
            )}
            {job.finished_at && (
              <div className="flex justify-between">
                <span className="text-gray-500">Finished</span>
                <span className="text-sm">
                  {format(new Date(job.finished_at), "PPpp")}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-500">Updated</span>
              <span className="text-sm">
                {format(new Date(job.updated_at), "PPpp")}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Payload</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
              {JSON.stringify(job.payload, null, 2)}
            </pre>
          </CardContent>
        </Card>

        {job.result && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                Result
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
                {JSON.stringify(job.result, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {job.error_text && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-red-500" />
                Error
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-red-50 p-4 rounded-lg overflow-x-auto text-sm text-red-800">
                {job.error_text}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
