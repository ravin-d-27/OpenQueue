import Link from "next/link";
import {
  ArrowLeft,
  Zap,
  Layers,
  Clock,
  RefreshCw,
  Shield,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Database,
  Server,
  Workflow,
  Users,
  Send,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ConceptsPage() {
  return (
    <div className="min-h-screen bg-black font-mono text-white">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <Link href="/">
          <Button variant="ghost" className="text-[#666] hover:text-white mb-8">
            <ArrowLeft className="h-4 w-4 mr-2" />
            BACK TO HOME
          </Button>
        </Link>

        <h1 className="text-3xl font-bold text-[#00ff00] mb-2">CONCEPTS</h1>
        <p className="text-[#666] mb-12">Understanding OpenQueue and event-driven architecture</p>

        <div className="space-y-12">
          <section>
            <div className="flex items-center gap-3 mb-4">
              <Workflow className="h-6 w-6 text-[#00ff00]" />
              <h2 className="text-xl font-bold text-white">What is Event-Driven Architecture?</h2>
            </div>
            <div className="prose prose-invert">
              <p className="text-[#888] leading-relaxed">
                Event-driven architecture (EDA) is a software design pattern where components communicate by producing and consuming events. Instead of direct, synchronous calls between services, systems emit events when something happens, and other services react to those events asynchronously.
              </p>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="border border-[#333] bg-[#0a0a0a] p-4">
                <h3 className="text-[#00ff00] font-bold mb-2">Traditional (Synchronous)</h3>
                <div className="flex items-center justify-center gap-2 text-sm text-[#666]">
                  <span>Client</span>
                  <ArrowRight className="h-4 w-4" />
                  <span>API</span>
                  <ArrowRight className="h-4 w-4" />
                  <span>Processing</span>
                </div>
                <p className="text-xs text-[#444] mt-2">Client waits for processing to complete</p>
              </div>
              <div className="border border-[#333] bg-[#0a0a0a] p-4">
                <h3 className="text-[#00ff00] font-bold mb-2">Event-Driven</h3>
                <div className="flex items-center justify-center gap-2 text-sm text-[#666]">
                  <span>Client</span>
                  <ArrowRight className="h-4 w-4" />
                  <span>Queue</span>
                  <ArrowRight className="h-4 w-4" />
                  <span>Worker</span>
                </div>
                <p className="text-xs text-[#444] mt-2">Client gets immediate confirmation, work happens in background</p>
              </div>
            </div>
          </section>

          <section>
            <div className="flex items-center gap-3 mb-4">
              <Zap className="h-6 w-6 text-[#00ff00]" />
              <h2 className="text-xl font-bold text-white">Why Event-Driven?</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="border border-[#222] p-4">
                <CheckCircle2 className="h-5 w-5 text-[#00ff00] mb-2" />
                <h3 className="text-white font-bold text-sm">Decoupling</h3>
                <p className="text-[#666] text-xs mt-1">Producers and workers don't need to know about each other. Just enqueue work and move on.</p>
              </div>
              <div className="border border-[#222] p-4">
                <CheckCircle2 className="h-5 w-5 text-[#00ff00] mb-2" />
                <h3 className="text-white font-bold text-sm">Scalability</h3>
                <p className="text-[#666] text-xs mt-1">Add more workers to handle increased load. The queue absorbs spikes gracefully.</p>
              </div>
              <div className="border border-[#222] p-4">
                <CheckCircle2 className="h-5 w-5 text-[#00ff00] mb-2" />
                <h3 className="text-white font-bold text-sm">Reliability</h3>
                <p className="text-[#666] text-xs mt-1">Jobs persist in the queue until processed. No work is lost if a worker crashes.</p>
              </div>
              <div className="border border-[#222] p-4">
                <CheckCircle2 className="h-5 w-5 text-[#00ff00] mb-2" />
                <h3 className="text-white font-bold text-sm">Responsiveness</h3>
                <p className="text-[#666] text-xs mt-1">Clients get immediate responses. Heavy processing happens asynchronously in the background.</p>
              </div>
              <div className="border border-[#222] p-4">
                <CheckCircle2 className="h-5 w-5 text-[#00ff00] mb-2" />
                <h3 className="text-white font-bold text-sm">Ordering</h3>
                <p className="text-[#666] text-xs mt-1">Jobs can be prioritized. Critical tasks jump to the front of the line.</p>
              </div>
              <div className="border border-[#222] p-4">
                <CheckCircle2 className="h-5 w-5 text-[#00ff00] mb-2" />
                <h3 className="text-white font-bold text-sm">Scheduling</h3>
                <p className="text-[#666] text-xs mt-1">Delay execution with run_at. Perfect for cron jobs, retries, and deferred work.</p>
              </div>
            </div>
          </section>

          <section>
            <div className="flex items-center gap-3 mb-4">
              <Layers className="h-6 w-6 text-[#00ff00]" />
              <h2 className="text-xl font-bold text-white">How OpenQueue Supports Event-Driven Architecture</h2>
            </div>
            <p className="text-[#888] mb-6">
              OpenQueue implements a job queue pattern - one of the most common ways to achieve event-driven processing. Here's how each concept maps to OpenQueue:
            </p>

            <div className="space-y-6">
              <div className="border border-[#222] bg-[#0a0a0a]">
                <div className="flex items-center gap-3 px-4 py-3 border-b border-[#222]">
                  <Send className="h-5 w-5 text-[#00aaff]" />
                  <span className="text-[#00aaff] font-bold">Producer</span>
                </div>
                <div className="p-4">
                  <p className="text-[#666] text-sm">
                    Any service that creates work. It enqueues a job with a payload and gets back a job ID immediately. The producer doesn't care who processes it or when.
                  </p>
                  <pre className="mt-3 bg-black border border-[#222] p-3 text-xs text-[#888] overflow-x-auto">
                    <code>{`# Producer enqueues work
job_id = client.enqueue(
    queue_name="send_email",
    payload={"to": "user@example.com", "subject": "Welcome!"}
)
# Returns immediately - job is queued`}</code>
                  </pre>
                </div>
              </div>

              <div className="border border-[#222] bg-[#0a0a0a]">
                <div className="flex items-center gap-3 px-4 py-3 border-b border-[#222]">
                  <Users className="h-5 w-5 text-[#00ff00]" />
                  <span className="text-[#00ff00] font-bold">Worker</span>
                </div>
                <div className="p-4">
                  <p className="text-[#666] text-sm">
                    Services that consume and process work. Workers lease jobs from the queue, process them, and report success or failure. You can run multiple workers for parallel processing.
                  </p>
                  <pre className="mt-3 bg-black border border-[#222] p-3 text-xs text-[#888] overflow-x-auto">
                    <code>{`# Worker leases and processes
leased = client.lease(queue_name="send_email", worker_id="worker-1")
if leased:
    send_email(leased.job.payload)
    client.ack(leased.job.id, leased.lease_token)`}</code>
                  </pre>
                </div>
              </div>

              <div className="border border-[#222] bg-[#0a0a0a]">
                <div className="flex items-center gap-3 px-4 py-3 border-b border-[#222]">
                  <Database className="h-5 w-5 text-[#ffff00]" />
                  <span className="text-[#ffff00] font-bold">Queue</span>
                </div>
                <div className="p-4">
                  <p className="text-[#666] text-sm">
                    The buffer between producers and workers. OpenQueue uses PostgreSQL as the backing store - jobs are rows in a table, giving you durability, querying, and ACID guarantees.
                  </p>
                  <div className="mt-3 flex items-center gap-4 text-xs">
                    <span className="text-[#444]">PostgreSQL-backed</span>
                    <span className="text-[#444]">|</span>
                    <span className="text-[#444]">ACID compliant</span>
                    <span className="text-[#444]">|</span>
                    <span className="text-[#444]">Queryable</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section>
            <div className="flex items-center gap-3 mb-4">
              <Zap className="h-6 w-6 text-[#00ff00]" />
              <h2 className="text-xl font-bold text-white">Core Concepts</h2>
            </div>

            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">Leasing</div>
                <div className="text-[#888] text-sm">
                  Workers atomically "claim" a job using database row locking (<code className="text-[#00aaff]">FOR UPDATE SKIP LOCKED</code>). This prevents two workers from processing the same job - no race conditions, no duplicates.
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">Lease Token</div>
                <div className="text-[#888] text-sm">
                  A unique token returned when leasing. Required for ack/nack operations. Prevents stale workers from updating a job after their lease expires.
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">Visibility Timeout</div>
                <div className="text-[#888] text-sm">
                  If a worker crashes, the job automatically becomes available again after the lease expires. This is "visibility timeout" - the job becomes "visible" to other workers.
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">Heartbeat</div>
                <div className="text-[#888] text-sm">
                  For long-running jobs, workers can send heartbeats to extend their lease. The job stays locked while processing continues.
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">ACK / NACK</div>
                <div className="text-[#888] text-sm">
                  <span className="text-[#00ff00]">ACK</span> marks a job as completed successfully. <span className="text-[#ff0000]">NACK</span> marks it as failed - OpenQueue will retry automatically with exponential backoff.
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">Dead Letter Queue</div>
                <div className="text-[#888] text-sm">
                  Jobs that exhaust all retries go to a "dead" state. They're not deleted - you can inspect them, understand what went wrong, and manually replay if needed.
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">Priority</div>
                <div className="text-[#888] text-sm">
                  Jobs have priority (higher = more urgent). When leasing, OpenQueue picks the highest priority job first. Critical tasks jump the queue.
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-32 text-[#666] text-sm shrink-0">Scheduled Jobs</div>
                <div className="text-[#888] text-sm">
                  The <code className="text-[#00aaff]">run_at</code> parameter delays execution. Jobs stay pending until their scheduled time, then become available for leasing. No cron needed.
                </div>
              </div>
            </div>
          </section>

          <section>
            <div className="flex items-center gap-3 mb-4">
              <RefreshCw className="h-6 w-6 text-[#00ff00]" />
              <h2 className="text-xl font-bold text-white">Job Lifecycle</h2>
            </div>

            <div className="flex items-center justify-between gap-2 text-xs font-mono overflow-x-auto pb-4">
              <div className="flex flex-col items-center gap-2 min-w-[100px]">
                <div className="w-20 h-12 border border-[#ffff00] bg-[#ffff00]/10 flex items-center justify-center text-[#ffff00]">
                  PENDING
                </div>
                <span className="text-[#666]">Queued</span>
              </div>
              <ArrowRight className="h-4 w-4 text-[#444]" />
              <div className="flex flex-col items-center gap-2 min-w-[100px]">
                <div className="w-20 h-12 border border-[#00aaff] bg-[#00aaff]/10 flex items-center justify-center text-[#00aaff]">
                  PROCESSING
                </div>
                <span className="text-[#666]">Leased</span>
              </div>
              <div className="flex flex-col items-center gap-2 min-w-[100px]">
                <div className="w-20 h-12 border border-[#00ff00] bg-[#00ff00]/10 flex items-center justify-center text-[#00ff00]">
                  COMPLETED
                </div>
                <span className="text-[#666]">Done</span>
              </div>
              <div className="flex flex-col items-center gap-2 min-w-[100px]">
                <div className="w-20 h-12 border border-[#ff0000] bg-[#ff0000]/10 flex items-center justify-center text-[#ff0000]">
                  FAILED
                </div>
                <span className="text-[#666]">Retrying</span>
              </div>
              <ArrowRight className="h-4 w-4 text-[#444]" />
              <div className="flex flex-col items-center gap-2 min-w-[100px]">
                <div className="w-20 h-12 border border-[#666] bg-[#666]/10 flex items-center justify-center text-[#666]">
                  DEAD
                </div>
                <span className="text-[#666]">DLQ</span>
              </div>
            </div>

            <div className="mt-6 border-t border-[#222] pt-6">
              <div className="text-sm text-[#666] mb-3">Pathways:</div>
              <div className="space-y-2 text-xs font-mono">
                <div><span className="text-[#ffff00]">PENDING</span> → lease → <span className="text-[#00aaff]">PROCESSING</span> → ack → <span className="text-[#00ff00]">COMPLETED</span></div>
                <div><span className="text-[#ffff00]">PENDING</span> → lease → <span className="text-[#00aaff]">PROCESSING</span> → nack → <span className="text-[#ff0000]">FAILED</span> → retry → <span className="text-[#ffff00]">PENDING</span></div>
                <div><span className="text-[#ffff00]">PENDING</span> → lease → <span className="text-[#00aaff]">PROCESSING</span> → nack (no retries) → <span className="text-[#666]">DEAD</span></div>
                <div><span className="text-[#ffff00]">PENDING</span> → cancel → cancelled</div>
              </div>
            </div>
          </section>

          <section className="border-t border-[#222] pt-8">
            <div className="text-center">
              <p className="text-[#666] mb-4">Ready to get started?</p>
              <div className="flex justify-center gap-4">
                <Link href="/docs">
                  <Button className="bg-[#00ff00] text-black hover:bg-[#00cc00]">
                    VIEW SDK DOCS
                  </Button>
                </Link>
                <Link href="/">
                  <Button variant="outline" className="border-[#333] text-[#666] hover:text-white hover:border-[#00ff00]">
                    BACK TO HOME
                  </Button>
                </Link>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
