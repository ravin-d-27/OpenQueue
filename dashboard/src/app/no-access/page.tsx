import Link from "next/link";
import { SignOutButton } from "@clerk/nextjs";
import { ShieldX, ArrowLeft } from "lucide-react";

export default function NoAccessPage() {
  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-6">
      <div className="max-w-md w-full text-center">
        <div className="inline-flex p-4 rounded-2xl bg-red-500/10 border border-red-500/20 mb-6">
          <ShieldX className="w-10 h-10 text-red-400" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">Access Denied</h1>
        <p className="text-white/50 mb-2">
          Your account is not authorised to access this dashboard.
        </p>
        <p className="text-white/30 text-sm mb-8">
          If you believe this is a mistake, please contact the administrator to have your email added.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 border border-white/20 text-white/70 px-5 py-2.5 rounded-lg hover:border-white/40 hover:text-white transition-all text-sm"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>
          <SignOutButton redirectUrl="/">
            <button className="inline-flex items-center gap-2 bg-white/10 text-white px-5 py-2.5 rounded-lg hover:bg-white/15 transition-all text-sm border border-white/10">
              Sign out
            </button>
          </SignOutButton>
        </div>
      </div>
    </div>
  );
}
