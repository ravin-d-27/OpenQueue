import Link from "next/link";
import Image from "next/image";
import {
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from "@clerk/nextjs";
import {
  Zap,
  Shield,
  RefreshCw,
  Clock,
  BarChart3,
  Code2,
  ArrowRight,
  CheckCircle2,
  Github,
  Package,
  Database,
  Layers,
  ServerCrash,
  Mail,
  Webhook,
  ImageIcon,
  CalendarClock,
  BrainCircuit,
  Globe,
} from "lucide-react";
import { MatrixBackground } from "@/components/matrix-background";

const features = [
  {
    icon: Zap,
    title: "Atomic job leasing",
    description:
      "PostgreSQL's SELECT FOR UPDATE SKIP LOCKED makes job pickup atomic and contention-free. Two workers can never receive the same job - no locks, no races, no duplicates.",
    accent: "text-yellow-400",
    bg: "bg-yellow-400/10",
  },
  {
    icon: Shield,
    title: "Multi-tenant by design",
    description:
      "Every job is scoped to a user via API token at the schema level. One tenant's queue can never read or interfere with another's - no key-namespacing tricks required.",
    accent: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  {
    icon: RefreshCw,
    title: "Automatic retries & DLQ",
    description:
      "Set max_retries per job. Failed jobs are retried automatically. Once retries are exhausted, jobs land in a dead-letter queue for manual inspection - never silently lost.",
    accent: "text-green-400",
    bg: "bg-green-400/10",
  },
  {
    icon: Clock,
    title: "Scheduled execution",
    description:
      "Pass a run_at timestamp to delay any job. Jobs stay pending until their scheduled time, then become eligible for leasing. No separate cron service needed.",
    accent: "text-purple-400",
    bg: "bg-purple-400/10",
  },
  {
    icon: BarChart3,
    title: "Real-time dashboard",
    description:
      "Per-queue stats, per-job timelines, payload & result inspection, error traces, and manual cancellation - all in a built-in terminal-style UI. No third-party add-on required.",
    accent: "text-orange-400",
    bg: "bg-orange-400/10",
  },
  {
    icon: Code2,
    title: "Python & TypeScript SDKs",
    description:
      "Official clients for Python and TypeScript/Node.js with full lifecycle support: enqueue, lease, ack, nack, heartbeat, cancel. Typed, tested, and published to PyPI & npm.",
    accent: "text-cyan-400",
    bg: "bg-cyan-400/10",
  },
  {
    icon: Database,
    title: "Full SQL observability",
    description:
      "Jobs are rows. Query them with JOIN, WHERE, GROUP BY. Plug in any SQL client, write custom reports, trace slow jobs, or export to your analytics stack - no special tooling needed.",
    accent: "text-pink-400",
    bg: "bg-pink-400/10",
  },
  {
    icon: Layers,
    title: "Priority queues",
    description:
      "Assign an integer priority to any job. Higher-priority jobs are always leased first within a queue, giving you fine-grained control over processing order without multiple queues.",
    accent: "text-indigo-400",
    bg: "bg-indigo-400/10",
  },
  {
    icon: ServerCrash,
    title: "Visibility timeouts & heartbeats",
    description:
      "Leased jobs have a configurable visibility timeout. Long-running workers send heartbeats to extend their lease. Crashed workers release their jobs automatically - no manual cleanup.",
    accent: "text-red-400",
    bg: "bg-red-400/10",
  },
];

const pythonSnippet = `from openqueue import OpenQueue

oq = OpenQueue(
    base_url="https://open-queue-ivory.vercel.app",
    api_token="oq_live_...",
)

# Enqueue a job
job = oq.enqueue("emails", {"to": "user@example.com"})

# Worker loop
while True:
    leased = oq.lease("emails", worker_id="w1")
    if leased:
        process(leased.job.payload)
        oq.ack(leased.job.id, leased.lease_token)`;

const tsSnippet = `import { OpenQueue } from "@ravin-d-27/openqueue";

const oq = new OpenQueue({
  baseUrl: "https://open-queue-ivory.vercel.app",
  apiToken: "oq_live_...",
});

// Enqueue a job
const job = await oq.enqueue("emails", {
  to: "user@example.com",
});

// Worker loop
const leased = await oq.lease("emails", "worker-1");
if (leased) {
  await process(leased.job.payload);
  await oq.ack(leased.job.id, leased.leaseToken);
}`;

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <MatrixBackground />
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-[#050505]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Image
              src="/openqueue-logo.png"
              alt="OpenQueue"
              width={32}
              height={32}
              className="rounded-lg"
            />
            <span className="font-semibold text-lg tracking-tight">
              OpenQueue
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-white/60">
            <Link
              href="#features"
              className="hover:text-white transition-colors"
            >
              Features
            </Link>
            <Link
              href="#how-it-works"
              className="hover:text-white transition-colors"
            >
              How it works
            </Link>
            <Link href="#code" className="hover:text-white transition-colors">
              SDK
            </Link>
            <Link
              href="https://github.com/ravin-d-27/OpenQueue"
              target="_blank"
              className="hover:text-white transition-colors flex items-center gap-1"
            >
              <Github className="w-4 h-4" /> GitHub
            </Link>
          </div>{" "}
          <div className="flex items-center gap-3">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="text-sm text-white/70 hover:text-white transition-colors px-3 py-1.5">
                  Sign in
                </button>
              </SignInButton>
              <SignUpButton mode="modal">
                <button className="text-sm bg-white text-black font-medium px-4 py-1.5 rounded-lg hover:bg-white/90 transition-colors">
                  Get started
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/dashboard"
                className="text-sm bg-white text-black font-medium px-4 py-1.5 rounded-lg hover:bg-white/90 transition-colors"
              >
                Dashboard
              </Link>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-36 pb-28 px-6 overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[600px] bg-gradient-to-b from-[#00ff88]/10 via-transparent to-transparent rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/4 w-[400px] h-[400px] bg-[#00aaff]/5 rounded-full blur-3xl" />
          <div className="absolute top-1/3 right-1/4 w-[300px] h-[300px] bg-[#aa88ff]/5 rounded-full blur-3xl" />
        </div>
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 text-xs font-mono border border-[#00ff88]/30 bg-[#00ff88]/10 text-[#00ff88] px-3 py-1.5 rounded-full mb-8">
            <span className="w-1.5 h-1.5 bg-[#00ff88] rounded-full animate-pulse" />
            Open source · PostgreSQL-backed · Production ready
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
            Background jobs.{" "}
            <span className="bg-gradient-to-r from-[#00ff88] via-[#00aaff] to-[#aa88ff] bg-clip-text text-transparent">
              No Redis required.
            </span>
          </h1>
          <p className="text-xl text-white/50 max-w-2xl mx-auto mb-4 leading-relaxed">
            Most job queue solutions force you to deploy and operate Redis
            alongside your database. OpenQueue runs entirely on the{" "}
            <span className="text-white/80">PostgreSQL you already have</span> -
            giving you reliable background jobs, automatic retries, scheduled
            execution, and a real-time dashboard without adding a single extra
            service.
          </p>
          <p className="text-sm text-white/30 max-w-xl mx-auto mb-10">
            Multi-tenant by design. Python &amp; TypeScript SDKs. Dead-letter
            queues built in.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <SignedOut>
              <SignUpButton mode="modal">
                <button className="flex items-center gap-2 bg-white text-black font-semibold px-6 py-3 rounded-xl hover:bg-white/90 transition-all shadow-lg shadow-white/10 text-base">
                  Get started free <ArrowRight className="w-4 h-4" />
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/dashboard"
                className="flex items-center gap-2 bg-white text-black font-semibold px-6 py-3 rounded-xl hover:bg-white/90 transition-all shadow-lg shadow-white/10 text-base"
              >
                Open dashboard <ArrowRight className="w-4 h-4" />
              </Link>
            </SignedIn>
            <Link
              href="https://github.com/ravin-d-27/OpenQueue"
              target="_blank"
              className="flex items-center gap-2 border border-white/20 text-white px-6 py-3 rounded-xl hover:border-white/40 hover:bg-white/5 transition-all text-base"
            >
              <Github className="w-4 h-4" /> View on GitHub
            </Link>
          </div>

          {/* Stats */}
          <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-px bg-white/5 border border-white/5 rounded-2xl overflow-hidden">
            {[
              {
                label: "Extra infrastructure",
                val: "Zero",
                sub: "PostgreSQL only",
              },
              {
                label: "Job lease latency",
                val: "< 5ms",
                sub: "p99, under load",
              },
              { label: "SDK languages", val: "2", sub: "Python & TypeScript" },
              { label: "License", val: "MIT", sub: "Free forever" },
            ].map((s) => (
              <div key={s.label} className="text-center bg-[#050505] px-6 py-6">
                <p className="text-2xl font-bold text-white">{s.val}</p>
                <p className="text-white/50 text-xs mt-1">{s.label}</p>
                <p className="text-white/25 text-[10px] mt-0.5">{s.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="py-24 px-6 border-t border-white/5 bg-white/[0.01]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs font-mono text-white/30 uppercase tracking-widest mb-3">
              The problem
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Adding a job queue shouldn&apos;t mean
              <br />
              adding a Redis operations team
            </h2>
            <p className="text-white/50 text-lg max-w-2xl mx-auto">
              Every major job queue library today assumes Redis. That means a
              second database to provision, monitor, scale, back up, and pay for
              - before you process a single job.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-5 mb-16">
            {[
              {
                title: "Another service to operate",
                body: "Redis must be deployed separately, kept alive, monitored for memory pressure, and backed up. On managed cloud it adds $50–$200/mo before your queue does anything useful.",
                icon: "⚙️",
              },
              {
                title: "Observability is a black box",
                body: "Redis-based queues store jobs in opaque data structures. You can't write a JOIN, you can't run an EXPLAIN, and you can't use the SQL tools your team already knows.",
                icon: "🔲",
              },
              {
                title: "Multi-tenancy is bolted on",
                body: "Bull, Celery, and RQ have no concept of users. Isolating one tenant's jobs from another requires custom key-namespacing, wrapper logic, and discipline - every time.",
                icon: "🔓",
              },
            ].map((p) => (
              <div
                key={p.title}
                className="p-6 rounded-2xl border border-red-500/15 bg-red-500/5"
              >
                <div className="text-2xl mb-4">{p.icon}</div>
                <h3 className="font-semibold text-white mb-2">{p.title}</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  {p.body}
                </p>
              </div>
            ))}
          </div>

          {/* Solution callout */}
          <div className="relative p-8 rounded-2xl border border-[#00ff88]/20 bg-[#00ff88]/5 text-center overflow-hidden">
            <div className="absolute inset-0 -z-10 bg-gradient-to-r from-[#00ff88]/5 via-transparent to-[#00aaff]/5" />
            <p className="text-sm font-mono text-[#00ff88]/70 uppercase tracking-widest mb-3">
              The OpenQueue approach
            </p>
            <p className="text-xl md:text-2xl font-semibold text-white max-w-3xl mx-auto leading-relaxed">
              Use the PostgreSQL database you&apos;re already running.{" "}
              <span className="text-white/50">
                Your jobs live next to your application data - queryable,
                observable, and isolated per user out of the box.
              </span>
            </p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs font-mono text-white/30 uppercase tracking-widest mb-3">
              Features
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything you need, nothing you don&#39;t
            </h2>
            <p className="text-white/50 text-lg max-w-2xl mx-auto">
              A complete job queue system - retries, scheduling, dead-letter
              queues, multi-tenancy, and observability - all without leaving
              your existing PostgreSQL setup.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f) => (
              <div
                key={f.title}
                className="group p-6 rounded-2xl border border-white/8 bg-white/[0.03] hover:border-white/15 hover:bg-white/5 transition-all"
              >
                <div className={`inline-flex p-2.5 rounded-xl ${f.bg} mb-4`}>
                  <f.icon className={`w-5 h-5 ${f.accent}`} />
                </div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-white/50 text-sm leading-relaxed">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="py-24 px-6 border-t border-white/5 bg-white/[0.01]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs font-mono text-white/30 uppercase tracking-widest mb-3">
              Use cases
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              What can you build with OpenQueue?
            </h2>
            <p className="text-white/50 text-lg max-w-xl mx-auto">
              Any task that shouldn&apos;t block a web request belongs in a
              queue. Here&apos;s what you can do:
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              {
                icon: Mail,
                color: "text-blue-400",
                bg: "bg-blue-400/10",
                border: "border-blue-400/20",
                title: "Transactional Emails",
                body: "Offload sign-up confirmations, password resets, and order receipts to a queue. If your email provider is slow or down, jobs retry automatically - users never see a slow response.",
                tags: ["welcome emails", "receipts", "alerts"],
              },
              {
                icon: Webhook,
                color: "text-green-400",
                bg: "bg-green-400/10",
                border: "border-green-400/20",
                title: "Webhook Delivery",
                body: "Deliver outbound webhooks reliably. Failed deliveries are retried with back-off, dead jobs are inspected from the dashboard, and every attempt is logged - no lost events.",
                tags: ["outbound events", "retries", "delivery logs"],
              },
              {
                icon: ImageIcon,
                color: "text-purple-400",
                bg: "bg-purple-400/10",
                border: "border-purple-400/20",
                title: "Media Processing",
                body: "Resize images, generate thumbnails, transcode video, or run OCR in the background. Queue the work immediately on upload, process asynchronously at your own pace.",
                tags: ["image resize", "thumbnails", "transcoding"],
              },
              {
                icon: CalendarClock,
                color: "text-orange-400",
                bg: "bg-orange-400/10",
                border: "border-orange-400/20",
                title: "Scheduled Reports",
                body: "Use run_at to schedule daily digests, weekly analytics emails, or monthly billing summaries. No separate cron service - the queue is the scheduler.",
                tags: ["daily digests", "billing runs", "cron replacement"],
              },
              {
                icon: BrainCircuit,
                color: "text-pink-400",
                bg: "bg-pink-400/10",
                border: "border-pink-400/20",
                title: "AI & LLM Pipelines",
                body: "Queue document processing, embedding generation, or LLM inference jobs. Handle bursts without overloading your inference budget - workers consume at a controlled rate.",
                tags: ["embeddings", "LLM calls", "batch inference"],
              },
              {
                icon: Globe,
                color: "text-cyan-400",
                bg: "bg-cyan-400/10",
                border: "border-cyan-400/20",
                title: "Data Sync & ETL",
                body: "Sync third-party APIs, run import jobs, or trigger data pipeline steps as queue jobs. Each step is observable, retryable, and scoped per tenant - no shared state issues.",
                tags: ["API sync", "imports", "ETL steps"],
              },
            ].map((u) => (
              <div
                key={u.title}
                className={`p-6 rounded-2xl border ${u.border} bg-white/[0.02] hover:bg-white/[0.04] transition-all`}
              >
                <div className={`inline-flex p-2.5 rounded-xl ${u.bg} mb-4`}>
                  <u.icon className={`w-5 h-5 ${u.color}`} />
                </div>
                <h3 className="font-semibold text-white mb-2">{u.title}</h3>
                <p className="text-white/50 text-sm leading-relaxed mb-4">
                  {u.body}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {u.tags.map((t) => (
                    <span
                      key={t}
                      className="text-[10px] font-mono text-white/30 border border-white/10 px-2 py-0.5 rounded"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs font-mono text-white/30 uppercase tracking-widest mb-3">
              How it works
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Three API calls. That&#39;s the whole model.
            </h2>
            <p className="text-white/50 text-lg max-w-xl mx-auto">
              Producers enqueue. Workers lease and process. The queue handles
              retries, timeouts, and dead letters automatically.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 mb-16">
            {[
              {
                num: "01",
                title: "Enqueue a job",
                desc: "POST to /jobs with a queue name, JSON payload, priority, max retries, and an optional run_at timestamp for deferred execution. Returns a job ID immediately.",
                detail:
                  "Your web request returns instantly. The work happens in the background.",
              },
              {
                num: "02",
                title: "Lease & process",
                desc: "Workers call /lease on a queue. OpenQueue atomically selects the highest-priority eligible job and locks it with a visibility timeout - guaranteed to one worker only.",
                detail:
                  "Workers can send heartbeats to extend the lease on long-running jobs.",
              },
              {
                num: "03",
                title: "Ack or nack",
                desc: "On success, call /ack to mark the job completed. On failure, call /nack - OpenQueue retries up to max_retries times, then moves the job to the dead-letter queue.",
                detail:
                  "Dead jobs are visible in the dashboard and can be re-queued manually.",
              },
            ].map((s) => (
              <div key={s.num} className="relative">
                <div className="text-6xl font-bold text-white/5 font-mono mb-4">
                  {s.num}
                </div>
                <h3 className="text-lg font-semibold mb-2 -mt-2">{s.title}</h3>
                <p className="text-white/50 text-sm leading-relaxed mb-3">
                  {s.desc}
                </p>
                <p className="text-xs text-white/30 leading-relaxed border-l border-white/10 pl-3">
                  {s.detail}
                </p>
              </div>
            ))}
          </div>

          {/* Job lifecycle */}
          <div className="p-6 rounded-2xl border border-white/8 bg-white/[0.03]">
            <p className="text-xs text-white/30 font-mono mb-5 uppercase tracking-widest">
              Job lifecycle
            </p>
            <div className="flex flex-wrap items-center gap-2 font-mono text-sm mb-5">
              {[
                {
                  label: "pending",
                  color:
                    "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
                },
                { label: "→", color: "text-white/20", plain: true },
                {
                  label: "processing",
                  color: "text-blue-400 border-blue-400/30 bg-blue-400/10",
                },
                { label: "→", color: "text-white/20", plain: true },
                {
                  label: "completed",
                  color: "text-green-400 border-green-400/30 bg-green-400/10",
                },
                {
                  label: "or on failure →",
                  color: "text-white/20",
                  plain: true,
                },
                {
                  label: "pending (retry)",
                  color:
                    "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
                },
                { label: "→ … →", color: "text-white/20", plain: true },
                {
                  label: "dead (DLQ)",
                  color: "text-red-400 border-red-400/30 bg-red-400/10",
                },
              ].map((item, i) =>
                item.plain ? (
                  <span key={i} className={`text-xs ${item.color}`}>
                    {item.label}
                  </span>
                ) : (
                  <span
                    key={i}
                    className={`px-3 py-1 rounded-full border text-xs ${item.color}`}
                  >
                    {item.label}
                  </span>
                ),
              )}
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs text-white/40 font-mono">
              {[
                ["Retries on nack", "Configurable per-job retry limit"],
                [
                  "Visibility timeout",
                  "Crashed workers release jobs automatically",
                ],
                ["Heartbeat support", "Long jobs extend their own lease"],
                [
                  "Scheduled execution",
                  "run_at delays jobs until the right moment",
                ],
              ].map(([title, desc]) => (
                <div
                  key={title}
                  className="flex flex-col gap-1 p-3 bg-white/[0.02] rounded-lg border border-white/5"
                >
                  <span className="flex items-center gap-1 text-white/60">
                    <CheckCircle2 className="w-3 h-3 text-green-400 shrink-0" />
                    {title}
                  </span>
                  <span className="text-white/25 text-[10px] leading-relaxed">
                    {desc}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="py-24 px-6 border-t border-white/5 bg-white/[0.01]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs font-mono text-white/30 uppercase tracking-widest mb-3">
              Comparison
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              How OpenQueue stacks up
            </h2>
            <p className="text-white/50 text-lg max-w-xl mx-auto">
              Compared to the most common alternatives for background job
              processing.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left px-6 py-4 text-white/40 font-normal text-xs uppercase tracking-wider w-1/3">
                    Capability
                  </th>
                  <th className="px-5 py-4 text-center">
                    <span className="inline-flex items-center gap-1.5 text-[#00ff88] font-semibold text-sm bg-[#00ff88]/10 border border-[#00ff88]/20 px-3 py-1 rounded-full">
                      <Image
                        src="/openqueue-logo.png"
                        alt="OpenQueue"
                        width={14}
                        height={14}
                        className="rounded-sm"
                      />{" "}
                      OpenQueue
                    </span>
                  </th>
                  <th className="px-5 py-4 text-center text-white/50 font-normal text-sm">
                    Redis / BullMQ
                  </th>
                  <th className="px-5 py-4 text-center text-white/50 font-normal text-sm">
                    Celery
                  </th>
                  <th className="px-5 py-4 text-center text-white/50 font-normal text-sm">
                    RQ
                  </th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    feature: "Infrastructure needed",
                    oq: "PostgreSQL only",
                    bull: "PostgreSQL + Redis",
                    celery: "PostgreSQL + Redis / RabbitMQ",
                    rq: "PostgreSQL + Redis",
                    highlight: true,
                  },
                  {
                    feature: "Multi-tenancy",
                    oq: "✓ Built-in",
                    bull: "✗ Manual",
                    celery: "✗ Manual",
                    rq: "✗ Manual",
                    oqGreen: true,
                  },
                  {
                    feature: "Built-in dashboard",
                    oq: "✓ Included",
                    bull: "Needs Bull Board",
                    celery: "Needs Flower",
                    rq: "✗ None",
                    oqGreen: true,
                  },
                  {
                    feature: "Dead-letter queue",
                    oq: "✓ Built-in",
                    bull: "Partial",
                    celery: "Partial",
                    rq: "✗ Manual",
                    oqGreen: true,
                  },
                  {
                    feature: "Visibility timeout",
                    oq: "✓",
                    bull: "✓",
                    celery: "✗",
                    rq: "✗",
                    oqGreen: true,
                  },
                  {
                    feature: "Scheduled jobs",
                    oq: "✓ Native",
                    bull: "✓ via cron",
                    celery: "✓ via Beat",
                    rq: "Partial",
                  },
                  {
                    feature: "SQL observability",
                    oq: "✓ Full",
                    bull: "✗",
                    celery: "✗",
                    rq: "✗",
                    oqGreen: true,
                  },
                  {
                    feature: "Priority queues",
                    oq: "✓ Built-in",
                    bull: "✓",
                    celery: "✓ Limited",
                    rq: "✗",
                    oqGreen: true,
                  },
                  {
                    feature: "Python SDK",
                    oq: "✓",
                    bull: "✗",
                    celery: "✓",
                    rq: "✓",
                  },
                  {
                    feature: "TypeScript SDK",
                    oq: "✓",
                    bull: "✓",
                    celery: "✗",
                    rq: "✗",
                  },
                ].map((row, i) => (
                  <tr
                    key={row.feature}
                    className={`border-b border-white/5 ${i % 2 === 0 ? "" : "bg-white/[0.01]"}`}
                  >
                    <td className="px-6 py-3.5 text-white/70 text-sm">
                      {row.feature}
                    </td>
                    <td
                      className={`px-5 py-3.5 text-center font-medium text-sm ${row.oqGreen ? "text-[#00ff88]" : row.highlight ? "text-[#00ff88] font-semibold" : "text-white/80"}`}
                    >
                      {row.oq}
                    </td>
                    <td className="px-5 py-3.5 text-center text-white/40 text-sm">
                      {row.bull}
                    </td>
                    <td className="px-5 py-3.5 text-center text-white/40 text-sm">
                      {row.celery}
                    </td>
                    <td className="px-5 py-3.5 text-center text-white/40 text-sm">
                      {row.rq}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-white/20 text-center mt-4">
            Comparison reflects typical default configurations. Some
            capabilities vary by version or plugin.
          </p>
        </div>
      </section>

      {/* Code examples */}
      <section id="code" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs font-mono text-white/30 uppercase tracking-widest mb-3">
              SDKs
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Up and running in minutes
            </h2>
            <p className="text-white/50 text-lg max-w-xl mx-auto">
              Official clients for Python and TypeScript. Install, point at your
              API URL, and start enqueueing - no broker configuration, no
              connection pools to manage.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="rounded-2xl border border-white/8 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/8 bg-white/[0.03]">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-mono text-white/70">
                    Python
                  </span>
                </div>
                <code className="text-xs font-mono text-white/40">
                  pip install openqueue-client
                </code>
              </div>
              <pre className="p-5 text-sm font-mono text-white/80 leading-relaxed overflow-x-auto bg-[#0a0a0a]">
                <code>{pythonSnippet}</code>
              </pre>
            </div>
            <div className="rounded-2xl border border-white/8 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/8 bg-white/[0.03]">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-mono text-white/70">
                    TypeScript
                  </span>
                </div>
                <code className="text-xs font-mono text-white/40">
                  npm i @ravin-d-27/openqueue
                </code>
              </div>
              <pre className="p-5 text-sm font-mono text-white/80 leading-relaxed overflow-x-auto bg-[#0a0a0a]">
                <code>{tsSnippet}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 border-t border-white/5">
        <div className="max-w-3xl mx-auto text-center">
          <div className="relative p-12 rounded-3xl border border-white/10 overflow-hidden">
            <div className="absolute inset-0 -z-10 bg-gradient-to-br from-[#00ff88]/10 via-[#00aaff]/5 to-transparent" />
            <p className="text-xs font-mono text-white/30 uppercase tracking-widest mb-4">
              Get started
            </p>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ship your background jobs today
            </h2>
            <p className="text-white/50 text-lg mb-3 max-w-xl mx-auto">
              Sign up, get your API token, and start enqueueing jobs in under
              five minutes. No Redis. No Celery. No ops overhead.
            </p>
            <p className="text-white/30 text-sm mb-8">
              Free to use · Open source · MIT license
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <SignedOut>
                <SignUpButton mode="modal">
                  <button className="inline-flex items-center gap-2 bg-white text-black font-semibold px-8 py-3.5 rounded-xl hover:bg-white/90 transition-all text-base">
                    Start for free <ArrowRight className="w-5 h-5" />
                  </button>
                </SignUpButton>
              </SignedOut>
              <SignedIn>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 bg-white text-black font-semibold px-8 py-3.5 rounded-xl hover:bg-white/90 transition-all text-base"
                >
                  Open dashboard <ArrowRight className="w-5 h-5" />
                </Link>
              </SignedIn>
              <Link
                href="https://github.com/ravin-d-27/OpenQueue"
                target="_blank"
                className="inline-flex items-center gap-2 border border-white/20 text-white px-8 py-3.5 rounded-xl hover:border-white/40 hover:bg-white/5 transition-all text-base"
              >
                <Github className="w-4 h-4" /> View source
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-10 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-white/30">
          <div className="flex items-center gap-2">
            <Image
              src="/openqueue-logo.png"
              alt="OpenQueue"
              width={20}
              height={20}
              className="rounded"
            />
            <span>OpenQueue</span>
          </div>
          <p>
            Open source, MIT license. Built with FastAPI + PostgreSQL + Next.js.
          </p>
          <div className="flex items-center gap-5">
            <Link
              href="https://github.com/ravin-d-27/OpenQueue"
              target="_blank"
              className="hover:text-white transition-colors"
            >
              GitHub
            </Link>
            <Link
              href="/dashboard"
              className="hover:text-white transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/docs"
              className="hover:text-white transition-colors"
            >
              Docs
            </Link>
            <Link
              href="/concepts"
              className="hover:text-white transition-colors"
            >
              Concepts
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
