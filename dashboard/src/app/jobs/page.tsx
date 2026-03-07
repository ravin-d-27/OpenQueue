"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { format } from "date-fns";
import {
  Beaker,
  RefreshCw,
  Eye,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, Job, JobListResponse } from "@/lib/api";

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

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queueFilter, setQueueFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const pageSize = 20;

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: {
        queue_name?: string;
        status?: string;
        limit: number;
        offset: number;
      } = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
      };

      if (queueFilter !== "all") params.queue_name = queueFilter;
      if (statusFilter !== "all") params.status = statusFilter;

      const data = await api.getJobs(params);
      setJobs(data?.items || []);
      setTotal(data?.total || 0);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch jobs");
      setJobs([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, queueFilter, statusFilter]);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 30000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const totalPages = Math.ceil(total / pageSize);

  if (loading && jobs.length === 0) {
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
          <h1 className="text-xl font-bold text-[#00ff00]">JOBS</h1>
          <p className="text-xs text-[#444] mt-1">
            {lastUpdated ? `Last updated: ${lastUpdated.toLocaleTimeString()}` : "Initializing..."}
          </p>
        </div>
        <Button onClick={fetchJobs} variant="outline" size="sm" className="border-[#333] text-[#666] hover:text-[#00ff00] hover:border-[#00ff00] bg-transparent">
          <RefreshCw className="h-4 w-4 mr-2" />
          REFRESH
        </Button>
      </div>

      {error && jobs.length === 0 && (
        <div className="border border-red-900 bg-red-950/30 p-3 text-red-400 text-sm">
          Error: {error}
        </div>
      )}

      <Card className="bg-black border-[#333]">
        <CardHeader className="border-b border-[#222]">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Input
                placeholder="Search jobs..."
                className="bg-black border-[#333] text-white placeholder:text-[#444]"
                value={queueFilter === "all" ? "" : queueFilter}
                onChange={(e) => {
                  if (e.target.value === "") {
                    setQueueFilter("all");
                  }
                }}
              />
            </div>
            <Select value={queueFilter} onValueChange={setQueueFilter}>
              <SelectTrigger className="w-[150px] bg-black border-[#333] text-white">
                <SelectValue placeholder="Queue" />
              </SelectTrigger>
              <SelectContent className="bg-black border-[#333]">
                <SelectItem value="all" className="text-white">ALL QUEUES</SelectItem>
                <SelectItem value="emails" className="text-white">emails</SelectItem>
                <SelectItem value="default" className="text-white">default</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px] bg-black border-[#333] text-white">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent className="bg-black border-[#333]">
                <SelectItem value="all" className="text-white">ALL STATUS</SelectItem>
                <SelectItem value="pending" className="text-white">PENDING</SelectItem>
                <SelectItem value="processing" className="text-white">PROCESSING</SelectItem>
                <SelectItem value="completed" className="text-white">COMPLETED</SelectItem>
                <SelectItem value="failed" className="text-white">FAILED</SelectItem>
                <SelectItem value="dead" className="text-white">DEAD</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 ? (
            <div className="text-center py-8 text-[#444]">
              <Beaker className="h-12 w-12 text-[#333] mx-auto mb-4" />
              <p>No jobs found</p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-[#222] hover:bg-transparent">
                    <TableHead className="text-[#666]">JOB ID</TableHead>
                    <TableHead className="text-[#666]">QUEUE</TableHead>
                    <TableHead className="text-[#666]">STATUS</TableHead>
                    <TableHead className="text-[#666]">PRIORITY</TableHead>
                    <TableHead className="text-[#666]">RETRIES</TableHead>
                    <TableHead className="text-[#666]">CREATED</TableHead>
                    <TableHead className="text-[#666]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.id} className="border-[#222] hover:bg-[#111]">
                      <TableCell className="font-mono text-sm text-[#00aaff]">
                        {job.id.slice(0, 8)}...
                      </TableCell>
                      <TableCell className="text-white">{job.queue_name}</TableCell>
                      <TableCell>
                        <span className={statusColors[job.status]}>
                          {statusLabels[job.status]}
                        </span>
                      </TableCell>
                      <TableCell className="text-white">{job.priority}</TableCell>
                      <TableCell className="text-white">
                        {job.retry_count}/{job.max_retries}
                      </TableCell>
                      <TableCell className="text-[#666] text-sm">
                        {format(new Date(job.created_at), "MMM d, HH:mm")}
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" asChild className="text-[#666] hover:text-[#00ff00]">
                          <Link href={`/jobs/${job.id}`}>
                            <Eye className="h-4 w-4" />
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#222]">
                <p className="text-sm text-[#444]">
                  Showing {jobs.length} of {total} jobs
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="border-[#333] text-[#666] hover:text-[#00ff00] hover:border-[#00ff00] bg-transparent"
                  >
                    PREV
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="border-[#333] text-[#666] hover:text-[#00ff00] hover:border-[#00ff00] bg-transparent"
                  >
                    NEXT
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
