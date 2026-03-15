import { auth, currentUser } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import postgres from "postgres";
import { Sidebar } from "@/components/sidebar";
import { Header } from "@/components/header";
import { AuthSync } from "@/components/auth-sync";

const sql = postgres(process.env.DATABASE_URL!, {
  ssl: "require",
  max: 1,
  idle_timeout: 20,
  connect_timeout: 10,
});

function checkIsAdmin(email: string): boolean {
  const adminEmails = (process.env.ADMIN_EMAILS || "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  return adminEmails.includes(email.toLowerCase());
}

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // 1. Must be signed in with Clerk
  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-in");
  }

  // 2. Get email from Clerk
  const user = await currentUser();
  const email = user?.emailAddresses?.[0]?.emailAddress;
  if (!email) {
    redirect("/sign-in");
  }

  const isAdmin = checkIsAdmin(email);

  // 3. Admins bypass DB check entirely.
  if (!isAdmin) {
    // Query without is_active filter so we can distinguish "not found" vs "inactive".
    const rows = await sql`
      SELECT is_active FROM users
      WHERE email = ${email}
      LIMIT 1
    `;

    if (rows.length === 0) {
      // New user — record their signup request and send them to the pending page.
      await sql`
        CREATE TABLE IF NOT EXISTS signup_requests (
          id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email        TEXT UNIQUE NOT NULL,
          clerk_id     TEXT,
          requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `;
      await sql`
        INSERT INTO signup_requests (email, clerk_id)
        VALUES (${email}, ${userId})
        ON CONFLICT (email) DO NOTHING
      `;
      redirect("/pending");
    }

    if (!rows[0].is_active) {
      // Previously deactivated — hard deny.
      redirect("/no-access");
    }
  }

  return (
    <>
      <AuthSync />
      <div className="flex h-screen bg-black overflow-hidden">
        <Sidebar isAdmin={isAdmin} />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-auto p-6 bg-[#0a0a0a]">{children}</main>
        </div>
      </div>
    </>
  );
}
