# OpenQueue TypeScript SDK

TypeScript client for OpenQueue.

## Installation

```bash
npm install @ravin-d-27/openqueue
```

## Usage

### As a Producer

```typescript
import { OpenQueue } from "@ravin-d-27/openqueue";

const client = new OpenQueue("https://queue.example.com", "your-api-token");

const jobId = await client.enqueue("my-queue", { task: "do_something" });
console.log(`Enqueued job: ${jobId}`);
```

### As a Worker

```typescript
import { OpenQueue } from "@ravin-d-27/openqueue";

const client = new OpenQueue("https://queue.example.com", "your-api-token");

const leased = await client.lease("my-queue", "worker-1");
if (leased) {
  console.log(`Processing job: ${leased.job.id}`);
  await client.ack(leased.job.id, leased.lease_token, { result: { done: true } });
}
```

## API

### Producer Methods

- `enqueue(queueName, payload, options?)` - Enqueue a new job
- `enqueueBatch(jobs)` - Enqueue multiple jobs
- `getStatus(jobId)` - Get job status
- `getJob(jobId)` - Get full job details
- `listJobs(options?)` - List jobs with filters
- `cancelJob(jobId)` - Cancel a pending job

### Worker Methods

- `lease(queueName, workerId, options?)` - Lease next available job
- `ack(jobId, leaseToken, options?)` - Acknowledge job completion
- `nack(jobId, leaseToken, error, options?)` - Report job failure
- `heartbeat(jobId, leaseToken, options?)` - Send heartbeat to extend lease

### Dashboard Methods

- `getQueueStats()` - Get queue statistics
