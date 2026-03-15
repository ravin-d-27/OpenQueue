import Link from "next/link";
import {
  ArrowLeft,
  Code2,
  Package,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Layers,
  Copy,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-black font-mono text-white">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <Link href="/">
          <Button variant="ghost" className="text-[#666] hover:text-white mb-8">
            <ArrowLeft className="h-4 w-4 mr-2" />
            BACK TO HOME
          </Button>
        </Link>

        <h1 className="text-3xl font-bold text-[#00ff00] mb-2">DOCUMENTATION</h1>
        <p className="text-[#666] mb-12">Official SDKs for interacting with OpenQueue</p>

        <div className="space-y-8">
          <section className="border border-[#333] bg-black">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-[#333] bg-[#0a0a0a]">
              <Package className="h-5 w-5 text-[#00aaff]" />
              <span className="text-[#00aaff] font-bold">Python SDK</span>
              <span className="text-xs text-[#444] ml-auto">pip install openqueue-pg</span>
            </div>
            <div className="p-6 space-y-6">
              <p className="text-[#888]">
                Official Python client for OpenQueue. Provides a simple interface for producers and workers.
              </p>

              <div>
                <h3 className="text-[#00ff00] text-sm font-bold mb-3">INSTALLATION</h3>
                <pre className="bg-[#0a0a0a] border border-[#222] p-4 text-sm text-[#00aaff] overflow-x-auto">
                  <code>pip install openqueue-pg</code>
                </pre>
              </div>

              <div>
                <h3 className="text-[#00ff00] text-sm font-bold mb-3">INITIALIZATION</h3>
                <pre className="bg-[#0a0a0a] border border-[#222] p-4 text-sm text-[#888] overflow-x-auto">
                  <code>{`from openqueue import OpenQueue

client = OpenQueue(
    base_url="https://your-api-url.com",
    api_token="oq_live_..."
)`}</code>
                </pre>
              </div>

              <div>
                <h3 className="text-[#00ff00] text-sm font-bold mb-3">PRODUCER - ENQUEUE JOBS</h3>
                <pre className="bg-[#0a0a0a] border border-[#222] p-4 text-sm text-[#888] overflow-x-auto">
                  <code>{`# Simple job
job_id = client.enqueue(
    queue_name="emails",
    payload={"to": "user@example.com", "subject": "Hello"}
)

# Scheduled job (run later)
job_id = client.enqueue(
    queue_name="reminders",
    payload={"user_id": 123, "message": "Reminder!"},
    run_at="2026-01-01T09:00:00Z"
)

# With priority (higher = more urgent)
job_id = client.enqueue(
    queue_name="emails",
    payload={"to": "user@example.com"},
    priority=10
)

# Batch enqueue
job_ids = client.enqueue_batch([
    {"queue_name": "emails", "payload": {"to": "a@b.com"}},
    {"queue_name": "emails", "payload": {"to": "c@d.com"}, "priority": 10},
])`}</code>
                </pre>
              </div>

              <div>
                <h3 className="text-[#00ff00] text-sm font-bold mb-3">WORKER - PROCESS JOBS</h3>
                <pre className="bg-[#0a0a0a] border border-[#222] p-4 text-sm text-[#888] overflow-x-auto">
                  <code>{`while True:
    leased = client.lease(queue_name="emails", worker_id="worker-1")
    
    if leased:
        try:
            # Process the job
            payload = leased.job.payload
            print(f"Processing: {payload}")
            
            # Success - mark complete
            client.ack(
                leased.job.id,
                leased.lease_token,
                result={"done": True}
            )
        except Exception as e:
            # Failure - retry
            client.nack(
                leased.job.id,
                leased.lease_token,
                error=str(e)
            )`}</code>
                </pre>
              </div>

              <div>
                <h3 className="text-[#00ff00] text-sm font-bold mb-3">HEARTBEAT</h3>
                <p className="text-[#666] text-sm mb-3">
                  For long-running jobs, extend the lease to prevent timeout:
                </p>
                <pre className="bg-[#0a0a0a] border border-[#222] p-4 text-sm text-[#888] overflow-x-auto">
                  <code>{`# Extend lease by 30 seconds
client.heartbeat(
    job_id="...",
    lease_token="...",
    lease_seconds=30
)`}</code>
                </pre>
              </div>

              <div>
                <h3 className="text-[#00ff00] text-sm font-bold mb-3">JOB OPERATIONS</h3>
                <pre className="bg-[#0a0a0a] border border-[#222] p-4 text-sm text-[#888] overflow-x-auto">
                  <code>{`# Get job status
status = client.get_status(job_id="...")

# Get full job details
job = client.get_job(job_id="...")

# List jobs
jobs = client.list_jobs(
    queue_name="emails",
    status="completed",
    limit=50,
    offset=0
)

# Cancel pending job
client.cancel_job(job_id="...")

# Get queue statistics
stats = client.get_queue_stats()`}</code>
                </pre>
              </div>

              <div>
                <h3 className="text-[#00ff00] text-sm font-bold mb-3">EXCEPTIONS</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-[#ff0000]" />
                    <span className="text-[#888]">JobNotFoundError</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-[#ff0000]" />
                    <span className="text-[#888]">LeaseTokenError</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-[#ff0000]" />
                    <span className="text-[#888]">LeaseNotFoundError</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-[#ff0000]" />
                    <span className="text-[#888]">OpenQueueError</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="border border-[#333] bg-black opacity-60">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-[#333] bg-[#0a0a0a]">
              <Code2 className="h-5 w-5 text-[#ffff00]" />
              <span className="text-[#ffff00] font-bold">TypeScript / JavaScript SDK</span>
              <span className="text-xs text-[#444] ml-auto bg-[#222] px-2 py-1">COMING SOON</span>
            </div>
            <div className="p-6">
              <p className="text-[#666]">
                TypeScript SDK with full type support is under development. Stay tuned for release announcements.
              </p>
            </div>
          </section>

          <section className="border border-[#333] bg-black">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-[#333] bg-[#0a0a0a]">
              <Layers className="h-5 w-5 text-[#888]" />
              <span className="text-[#888] font-bold">REST API REFERENCE</span>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-[#666] text-sm">
                You can also interact with OpenQueue directly via HTTP without using an SDK.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="border border-[#222] p-4">
                  <div className="text-[#00ff00] text-sm font-bold mb-2">PRODUCER</div>
                  <div className="space-y-1 text-xs text-[#666] font-mono">
                    <div>POST /jobs - Enqueue job</div>
                    <div>GET /jobs/&#123;id&#125; - Get status</div>
                    <div>GET /jobs - List jobs</div>
                    <div>POST /jobs/batch - Batch enqueue</div>
                    <div>POST /jobs/&#123;id&#125;/cancel - Cancel</div>
                  </div>
                </div>
                <div className="border border-[#222] p-4">
                  <div className="text-[#00ff00] text-sm font-bold mb-2">WORKER</div>
                  <div className="space-y-1 text-xs text-[#666] font-mono">
                    <div>POST /queues/&#123;name&#125;/lease - Lease</div>
                    <div>POST /jobs/&#123;id&#125;/ack - Success</div>
                    <div>POST /jobs/&#123;id&#125;/nack - Failure</div>
                    <div>POST /jobs/&#123;id&#125;/heartbeat - Renew</div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
