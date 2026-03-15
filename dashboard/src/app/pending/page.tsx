import { SignOutButton } from "@clerk/nextjs";
import { Clock } from "lucide-react";
import Link from "next/link";

export default function PendingPage() {
  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center font-mono">
      <div className="max-w-md w-full mx-auto px-6 text-center space-y-6">
        <div className="flex justify-center">
          <Clock className="h-12 w-12 text-[#ffff00]" strokeWidth={1.5} />
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-white">Access Pending</h1>
          <p className="text-[#666] text-sm leading-relaxed">
            Your sign-up request has been received. An admin will review and
            approve your account shortly.
          </p>
          <p className="text-[#444] text-xs">
            You will be able to sign in once your account is approved.
          </p>
        </div>

        <div className="border border-[#222] p-4 text-left text-xs text-[#555] space-y-1">
          <p className="text-[#333] font-bold uppercase tracking-wider mb-2">What happens next</p>
          <p>1. Admin reviews your signup request</p>
          <p>2. Your account is provisioned with an API token</p>
          <p>3. Sign in again to access the dashboard</p>
        </div>

        <div className="flex gap-3 justify-center">
          <Link
            href="/"
            className="px-4 py-2 text-sm border border-[#333] text-[#666]
                       hover:text-white hover:border-[#555] transition-colors"
          >
            Back to home
          </Link>
          <SignOutButton redirectUrl="/">
            <button className="px-4 py-2 text-sm border border-[#333] text-[#666]
                               hover:text-white hover:border-[#555] transition-colors">
              Sign out
            </button>
          </SignOutButton>
        </div>
      </div>
    </div>
  );
}
