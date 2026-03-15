import Link from "next/link";
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
} from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "Blazing Fast Leasing",
    description:
      "PostgreSQL SELECT FOR UPDATE SKIP LOCKED guarantees sub-millisecond job leasing with zero contention between workers.",
    accent: "text-yellow-400",
    bg: "bg-yellow-400/10",
  },
  {
    icon: Shield,
    title: "Multi-tenant by Design",
    description:
      "Every job is scoped to a user via API token. Total isolation — one tenant's queue never touches another's.",
    accent: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  {
    icon: RefreshCw,
    title: "Automatic Retries",
    description:
      "Configurable retry limits with exponential back-off. Failed jobs go to a dead-letter queue for inspection.",
    accent: "text-green-400",
    bg: "bg-green-400/10",
  },
  {
    icon: Clock,
    title: "Scheduled Jobs",
    description:
      "Set run_at to delay execution. Jobs stay pending until their scheduled time, then become eligible for leasing.",
    accent: "text-purple-400",
    bg: "bg-purple-400/10",
  },
  {
    icon: BarChart3,
    title: "Real-time Dashboard",
    description:
      "Live queue stats, per-job timelines, error inspection, and manual cancellation — all in one terminal-style UI.",
    accent: "text-orange-400",
    bg: "bg-orange-400/10",
  },
  {
    icon: Code2,
    title: "SDK in Python & TypeScript",
    description:
      "Official clients for Python and TypeScript/Node.js. Enqueue, lease, ack, nack, heartbeat — full lifecycle support.",
    accent: "text-cyan-400",
    bg: "bg-cyan-400/10",
  },
];

const steps = [
  {
    num: "01",
    title: "Enqueue a job",
    desc: "POST to /jobs with a queue name, payload, priority, and optional run_at timestamp.",
  },
  {
    num: "02",
    title: "Lease & process",
    desc: "Workers call /lease. OpenQueue atomically hands out one job, locked with a visibility timeout.",
  },
  {
    num: "03",
    title: "Ack or nack",
    desc: "On success call /ack to complete. On failure call /nack — OpenQueue retries or moves to DLQ.",
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
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-[#050505]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#00ff88] to-[#00aaff] flex items-center justify-center">
              <Zap className="w-4 h-4 text-black" />
            </div>
            <span className="font-semibold text-lg tracking-tight">OpenQueue</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-white/60">
            <Link href="#features" className="hover:text-white transition-colors">Features</Link>
            <Link href="#how-it-works" className="hover:text-white transition-colors">How it works</Link>
            <Link href="#code" className="hover:text-white transition-colors">SDK</Link>
            <Link
              href="https://github.com/ravin-d-27/OpenQueue"
              target="_blank"
              className="hover:text-white transition-colors flex items-center gap-1"
            >
              <Github className="w-4 h-4" /> GitHub
            </Link>
          </div>
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
      <section className="relative pt-36 pb-24 px-6 overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-b from-[#00ff88]/10 via-transparent to-transparent rounded-full blur-3xl" />
        </div>
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 text-xs font-mono border border-[#00ff88]/30 bg-[#00ff88]/10 text-[#00ff88] px-3 py-1 rounded-full mb-8">
            <span className="w-1.5 h-1.5 bg-[#00ff88] rounded-full animate-pulse" />
            Open source · PostgreSQL-backed · Production ready
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-tight mb-6">
            Job queues that{" "}
            <span className="bg-gradient-to-r from-[#00ff88] via-[#00aaff] to-[#aa88ff] bg-clip-text text-transparent">
              just work
            </span>
          </h1>
          <p className="text-xl text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed">
            OpenQueue is a lightweight, PostgreSQL-backed job queue with multi-tenancy,
            automatic retries, scheduled jobs, and a real-time dashboard — no Redis, no
            extra infrastructure.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <SignedOut>
              <SignUpButton mode="modal">
                <button className="flex items-center gap-2 bg-white text-black font-semibold px-6 py-3 rounded-xl hover:bg-white/90 transition-all shadow-lg shadow-white/10">
                  Get started free <ArrowRight className="w-4 h-4" />
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/dashboard"
                className="flex items-center gap-2 bg-white text-black font-semibold px-6 py-3 rounded-xl hover:bg-white/90 transition-all shadow-lg shadow-white/10"
              >
                Open dashboard <ArrowRight className="w-4 h-4" />
              </Link>
            </SignedIn>
            <Link
              href="https://github.com/ravin-d-27/OpenQueue"
              target="_blank"
              className="flex items-center gap-2 border border-white/20 text-white px-6 py-3 rounded-xl hover:border-white/40 hover:bg-white/5 transition-all"
            >
              <Github className="w-4 h-4" /> View on GitHub
            </Link>
          </div>

          {/* Stats */}
          <div className="mt-16 flex flex-col sm:flex-row items-center justify-center gap-10 text-sm">
            {[
              { label: "Open source", val: "100%" },
              { label: "Dependencies", val: "PostgreSQL only" },
              { label: "API response", val: "< 5ms p99" },
              { label: "SDK languages", val: "Python & TS" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <p className="text-2xl font-bold text-white">{s.val}</p>
                <p className="text-white/40 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Everything you need, nothing you don&#39;t
            </h2>
            <p className="text-white/50 text-lg max-w-xl mx-auto">
              Built for developers who want reliable background jobs without
              managing yet another piece of infrastructure.
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
                <p className="text-white/50 text-sm leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">How it works</h2>
            <p className="text-white/50 text-lg">Three API calls. That&#39;s the whole model.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {steps.map((s) => (
              <div key={s.num}>
                <div className="text-6xl font-bold text-white/5 font-mono mb-4">{s.num}</div>
                <h3 className="text-lg font-semibold mb-2 -mt-2">{s.title}</h3>
                <p className="text-white/50 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-16 p-6 rounded-2xl border border-white/8 bg-white/[0.03]">
            <p className="text-xs text-white/30 font-mono mb-4 uppercase tracking-widest">Job lifecycle</p>
            <div className="flex flex-wrap items-center gap-2 font-mono text-sm">
              {[
                { label: "pending", color: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10" },
                { label: "→", color: "text-white/20", plain: true },
                { label: "processing", color: "text-blue-400 border-blue-400/30 bg-blue-400/10" },
                { label: "→", color: "text-white/20", plain: true },
                { label: "completed", color: "text-green-400 border-green-400/30 bg-green-400/10" },
                { label: "or", color: "text-white/20", plain: true },
                { label: "dead (DLQ)", color: "text-red-400 border-red-400/30 bg-red-400/10" },
              ].map((item, i) =>
                item.plain ? (
                  <span key={i} className={item.color}>{item.label}</span>
                ) : (
                  <span key={i} className={`px-3 py-1 rounded-full border text-xs ${item.color}`}>
                    {item.label}
                  </span>
                )
              )}
            </div>
            <div className="mt-4 flex flex-wrap gap-4 text-xs text-white/40 font-mono">
              {["Retries on nack", "Visibility timeout", "Heartbeat support", "Scheduled execution"].map((t) => (
                <span key={t}><CheckCircle2 className="inline w-3 h-3 mr-1 text-green-400" />{t}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Code examples */}
      <section id="code" className="py-24 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">SDKs for your language</h2>
            <p className="text-white/50 text-lg">Official clients in Python and TypeScript. Install in seconds.</p>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="rounded-2xl border border-white/8 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/8 bg-white/[0.03]">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-mono text-white/70">Python</span>
                </div>
                <code className="text-xs font-mono text-white/40">pip install openqueue-client</code>
              </div>
              <pre className="p-5 text-sm font-mono text-white/80 leading-relaxed overflow-x-auto bg-[#0a0a0a]">
                <code>{pythonSnippet}</code>
              </pre>
            </div>
            <div className="rounded-2xl border border-white/8 overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-white/8 bg-white/[0.03]">
                <div className="flex items-center gap-2">
                  <Package className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-mono text-white/70">TypeScript</span>
                </div>
                <code className="text-xs font-mono text-white/40">npm i @ravin-d-27/openqueue</code>
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
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ready to ship your background jobs?
            </h2>
            <p className="text-white/50 text-lg mb-8">
              Sign up, get your API token instantly, and start enqueueing in minutes.
            </p>
            <SignedOut>
              <SignUpButton mode="modal">
                <button className="inline-flex items-center gap-2 bg-white text-black font-semibold px-8 py-3.5 rounded-xl hover:bg-white/90 transition-all text-lg">
                  Start for free <ArrowRight className="w-5 h-5" />
                </button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 bg-white text-black font-semibold px-8 py-3.5 rounded-xl hover:bg-white/90 transition-all text-lg"
              >
                Open dashboard <ArrowRight className="w-5 h-5" />
              </Link>
            </SignedIn>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-10 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-white/30">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-gradient-to-br from-[#00ff88] to-[#00aaff] flex items-center justify-center">
              <Zap className="w-3 h-3 text-black" />
            </div>
            <span>OpenQueue</span>
          </div>
          <p>Open source, MIT license. Built with FastAPI + PostgreSQL + Next.js.</p>
          <div className="flex items-center gap-5">
            <Link href="https://github.com/ravin-d-27/OpenQueue" target="_blank" className="hover:text-white transition-colors">GitHub</Link>
            <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
            <Link href="https://open-queue-ivory.vercel.app/docs" target="_blank" className="hover:text-white transition-colors">API Docs</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
