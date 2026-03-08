import { OpenQueue } from "@ravin-d-27/openqueue";

const client = new OpenQueue("http://localhost:8000", "your-api-token");

async function processJob() {
  while (true) {
    const leased = await client.lease("my-queue", "worker-1");

    if (!leased) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      continue;
    }

    console.log(`Processing job: ${leased.job.id}`);

    try {
      const result = await client.ack(
        leased.job.id,
        leased.lease_token,
        { result: { success: true } }
      );
      console.log(`Job acknowledged: ${result}`);
    } catch (error) {
      console.error(`Failed to ack job: ${error}`);
      await client.nack(
        leased.job.id,
        leased.lease_token,
        "Processing failed",
        { retry: true }
      );
    }
  }
}

processJob().catch(console.error);
