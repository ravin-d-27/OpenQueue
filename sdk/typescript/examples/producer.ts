import { OpenQueue } from "@ravin-d-27/openqueue";

const client = new OpenQueue("http://localhost:8000", "your-api-token");

async function main() {
  const jobId = await client.enqueue("my-queue", { task: "do_something" });
  console.log(`Enqueued job: ${jobId}`);

  const jobs = await client.enqueueBatch([
    { queue_name: "my-queue", payload: { task: "job1" } },
    { queue_name: "my-queue", payload: { task: "job2" }, priority: 10 },
  ]);
  console.log(`Enqueued batch: ${jobs.join(", ")}`);

  const status = await client.getStatus(jobId);
  console.log(`Job status: ${status}`);

  const job = await client.getJob(jobId);
  console.log(`Job details: ${JSON.stringify(job)}`);

  const list = await client.listJobs({ queue_name: "my-queue", limit: 10 });
  console.log(`Found ${list.total} jobs`);
}

main().catch(console.error);
