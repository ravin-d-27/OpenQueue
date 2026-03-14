import {
  Job,
  LeasedJob,
  QueueStats,
  JobListResponse,
  EnqueueOptions,
  LeaseOptions,
  AckOptions,
  NackOptions,
  HeartbeatOptions,
  ListJobsOptions,
  JobStatus,
} from "./types";
import {
  OpenQueueError,
  AuthenticationError,
  JobNotFoundError,
  LeaseTokenError,
  ValidationError,
  RateLimitError,
} from "./errors";

export { JobStatus } from "./types";
export {
  OpenQueueError,
  AuthenticationError,
  JobNotFoundError,
  LeaseTokenError,
  ValidationError,
  RateLimitError,
} from "./errors";
export type { Job, LeasedJob, QueueStats, JobListResponse } from "./types";

export class OpenQueue {
  private baseUrl: string;
  private apiToken: string;
  private timeout: number;
  private maxRetries: number;

  constructor(
    baseUrl: string,
    apiToken: string,
    options?: {
      timeout?: number;
      maxRetries?: number;
    }
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiToken = apiToken;
    this.timeout = options?.timeout ?? 30000;
    this.maxRetries = options?.maxRetries ?? 3;
  }

  private async request<T>(
    method: string,
    path: string,
    options?: {
      params?: Record<string, unknown>;
      body?: Record<string, unknown>;
    }
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (options?.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(url.toString(), {
          method,
          headers: {
            Authorization: `Bearer ${this.apiToken}`,
            "Content-Type": "application/json",
          },
          body: options?.body ? JSON.stringify(options.body) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (response.status === 401) {
          throw new AuthenticationError();
        }
        if (response.status === 422) {
          const text = await response.text();
          throw new ValidationError(`Validation error: ${text.slice(0, 100)}`);
        }
        if (response.status === 429) {
          throw new RateLimitError();
        }
        if (response.status === 404) {
          throw new JobNotFoundError();
        }
        if (response.status === 409) {
          throw new LeaseTokenError();
        }
        if (response.status >= 500) {
          const text = await response.text();
          throw new OpenQueueError(
            `Server error: ${response.status} - ${text.slice(0, 100)}`
          );
        }
        if (response.status === 400) {
          const text = await response.text();
          if (text.toLowerCase().includes("lease")) {
            throw new LeaseTokenError("Invalid lease token");
          }
          throw new ValidationError(text);
        }

        if (response.status === 204) {
          return {} as T;
        }

        if (response.status === 201 || response.status === 200) {
          return await response.json();
        }

        return await response.json();
      } catch (error) {
        if (error instanceof AuthenticationError ||
            error instanceof ValidationError ||
            error instanceof RateLimitError ||
            error instanceof JobNotFoundError ||
            error instanceof LeaseTokenError ||
            error instanceof OpenQueueError) {
          throw error;
        }
        lastError = error as Error;
        if (attempt < this.maxRetries - 1) {
          await new Promise((resolve) =>
            setTimeout(resolve, 500 * (attempt + 1))
          );
        }
      }
    }

    throw new OpenQueueError(lastError?.message ?? "Request failed");
  }

  async enqueue(
    queueName: string,
    payload: Record<string, unknown>,
    options?: EnqueueOptions
  ): Promise<string> {
    const body: Record<string, unknown> = {
      queue_name: queueName,
      payload,
      priority: options?.priority ?? 0,
      max_retries: options?.max_retries ?? 3,
    };
    if (options?.run_at) {
      body.run_at = options.run_at.replace("Z", "+00:00");
    }
    const result = await this.request<{ job_id: string }>("POST", "/jobs", {
      body,
    });
    return result.job_id;
  }

  async enqueueBatch(
    jobs: Array<{
      queue_name: string;
      payload: Record<string, unknown>;
      priority?: number;
      max_retries?: number;
      run_at?: string;
    }>
  ): Promise<string[]> {
    const formattedJobs = jobs.map((job) => ({
      queue_name: job.queue_name,
      payload: job.payload,
      priority: job.priority ?? 0,
      max_retries: job.max_retries ?? 3,
      run_at: job.run_at?.replace("Z", "+00:00"),
    }));
    const result = await this.request<{ job_ids: string[] }>("POST", "/jobs/batch", {
      body: { jobs: formattedJobs },
    });
    return result.job_ids;
  }

  async getStatus(jobId: string): Promise<JobStatus> {
    const result = await this.request<{ status: string }>("GET", `/jobs/${jobId}`);
    return result.status as JobStatus;
  }

  async getJob(jobId: string): Promise<Job> {
    return await this.request<Job>("GET", `/jobs/${jobId}/detail`);
  }

  async listJobs(options?: ListJobsOptions): Promise<JobListResponse> {
    const params: Record<string, unknown> = {
      limit: options?.limit ?? 50,
      offset: options?.offset ?? 0,
    };
    if (options?.queue_name) {
      params.queue_name = options.queue_name;
    }
    if (options?.status) {
      params.status = options.status;
    }
    return await this.request<JobListResponse>("GET", "/jobs", { params });
  }

  async cancelJob(jobId: string): Promise<boolean> {
    try {
      await this.request("POST", `/jobs/${jobId}/cancel`);
      return true;
    } catch (error) {
      if (error instanceof JobNotFoundError) {
        return false;
      }
      throw error;
    }
  }

  async lease(
    queueName: string,
    workerId: string,
    options?: LeaseOptions
  ): Promise<LeasedJob | null> {
    const body: Record<string, unknown> = {
      worker_id: workerId,
      lease_seconds: options?.lease_seconds ?? 30,
    };
    const result = await this.request<LeasedJob | null>("POST", `/queues/${queueName}/lease`, {
      body,
    });
    return result;
  }

  async ack(jobId: string, leaseToken: string, options?: AckOptions): Promise<boolean> {
    const body: Record<string, unknown> = { lease_token: leaseToken };
    if (options?.result) {
      body.result = options.result;
    }
    await this.request("POST", `/jobs/${jobId}/ack`, { body });
    return true;
  }

  async nack(
    jobId: string,
    leaseToken: string,
    error: string,
    options?: NackOptions
  ): Promise<boolean> {
    const body: Record<string, unknown> = {
      lease_token: leaseToken,
      error,
      retry: options?.retry ?? true,
    };
    await this.request("POST", `/jobs/${jobId}/nack`, { body });
    return true;
  }

  async heartbeat(
    jobId: string,
    leaseToken: string,
    options?: HeartbeatOptions
  ): Promise<boolean> {
    const body: Record<string, unknown> = {
      lease_token: leaseToken,
      lease_seconds: options?.lease_seconds ?? 30,
    };
    await this.request("POST", `/jobs/${jobId}/heartbeat`, { body });
    return true;
  }

  async getQueueStats(): Promise<QueueStats[]> {
    return await this.request<QueueStats[]>("GET", "/dashboard/queues");
  }
}
