"use client";

import { useState, useCallback } from "react";

const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://open-queue-ivory.vercel.app";

const getApiBaseUrl = (): string => {
  if (typeof window !== "undefined") {
    return localStorage.getItem("api_url") || DEFAULT_API_URL;
  }
  return DEFAULT_API_URL;
};

export interface QueueStats {
  queue_name: string;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  dead: number;
}

export interface Job {
  id: string;
  queue_name: string;
  payload: Record<string, unknown>;
  status: "pending" | "processing" | "completed" | "failed" | "dead" | "cancelled";
  priority: number;
  retry_count: number;
  max_retries: number;
  run_at: string;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  result: Record<string, unknown> | null;
  error_text: string | null;
  locked_by: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface LeaseResponse {
  job: Job;
  lease_token: string;
  locked_until: string;
}

export interface ApiError {
  detail: string;
}

class OpenQueueApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "OpenQueueApiError";
  }
}

function getAuthHeader(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("api_token");
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthHeader();
  const baseUrl = getApiBaseUrl();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    // On 401, clear the stale token so AuthSync will fetch a fresh one.
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("api_token");
      window.dispatchEvent(new CustomEvent("oq:reauth"));
    }
    const error: ApiError = await response.json().catch(() => ({
      detail: "An error occurred",
    }));
    throw new OpenQueueApiError(response.status, error.detail);
  }

  return response.json();
}

export const api = {
  // Dashboard
  async getQueueStats(): Promise<QueueStats[]> {
    return fetchApi<QueueStats[]>("/dashboard/queues");
  },

  // Jobs
  async getJobs(params: {
    queue_name?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<JobListResponse> {
    const searchParams = new URLSearchParams();
    if (params.queue_name) searchParams.set("queue_name", params.queue_name);
    if (params.status) searchParams.set("status", params.status);
    if (params.limit) searchParams.set("limit", params.limit.toString());
    if (params.offset) searchParams.set("offset", params.offset.toString());

    const query = searchParams.toString();
    return fetchApi<JobListResponse>(`/jobs?${query}`);
  },

  async getJob(jobId: string): Promise<Job> {
    return fetchApi<Job>(`/jobs/${jobId}`);
  },

  async enqueueJob(data: {
    queue_name: string;
    payload: Record<string, unknown>;
    priority?: number;
    max_retries?: number;
    run_at?: string;
  }): Promise<{ id: string }> {
    return fetchApi<{ id: string }>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async cancelJob(jobId: string): Promise<void> {
    return fetchApi<void>(`/jobs/${jobId}/cancel`, { method: "POST" });
  },

  // Workers
  async leaseJob(
    queueName: string,
    workerId: string,
    leaseSeconds: number = 30
  ): Promise<LeaseResponse | null> {
    return fetchApi<LeaseResponse | null>(`/queues/${queueName}/lease`, {
      method: "POST",
      body: JSON.stringify({ worker_id: workerId, lease_seconds: leaseSeconds }),
    });
  },

  async ackJob(
    jobId: string,
    leaseToken: string,
    result?: Record<string, unknown>
  ): Promise<void> {
    return fetchApi<void>(`/jobs/${jobId}/ack`, {
      method: "POST",
      body: JSON.stringify({ lease_token: leaseToken, result }),
    });
  },

  async nackJob(
    jobId: string,
    leaseToken: string,
    error: string,
    retry: boolean = true
  ): Promise<void> {
    return fetchApi<void>(`/jobs/${jobId}/nack`, {
      method: "POST",
      body: JSON.stringify({ lease_token: leaseToken, error, retry }),
    });
  },

  async heartbeatJob(
    jobId: string,
    leaseToken: string,
    leaseSeconds: number = 30
  ): Promise<void> {
    return fetchApi<void>(`/jobs/${jobId}/heartbeat`, {
      method: "POST",
      body: JSON.stringify({ lease_token: leaseToken, lease_seconds: leaseSeconds }),
    });
  },

  // Health
  async healthCheck(): Promise<{ status: string }> {
    return fetchApi<{ status: string }>("/health");
  },
};

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async <T,>(
    fn: () => Promise<T>
  ): Promise<T | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      return result;
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, execute };
}
