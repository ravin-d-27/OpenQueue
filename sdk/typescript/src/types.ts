export enum JobStatus {
  Pending = "pending",
  Processing = "processing",
  Completed = "completed",
  Failed = "failed",
  Cancelled = "cancelled",
  Dead = "dead",
}

export interface Job {
  id: string;
  queue_name: string;
  status: JobStatus;
  priority: number;
  payload: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error_text: string | null;
  retry_count: number | null;
  max_retries: number | null;
  created_at: string | null;
  updated_at: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface LeasedJob {
  job: Job;
  lease_token: string;
  lease_expires_at: string | null;
}

export interface QueueStats {
  queue_name: string;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  cancelled: number;
  dead: number;
  total: number;
  oldest_pending_created_at: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface EnqueueOptions {
  priority?: number;
  max_retries?: number;
  run_at?: string;
}

export interface LeaseOptions {
  lease_seconds?: number;
}

export interface AckOptions {
  result?: Record<string, unknown>;
}

export interface NackOptions {
  retry?: boolean;
}

export interface HeartbeatOptions {
  lease_seconds?: number;
}

export interface ListJobsOptions {
  queue_name?: string;
  status?: JobStatus;
  limit?: number;
  offset?: number;
}
