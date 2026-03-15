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

  // 2. Email must exist in Supabase users table
  const user = await currentUser();
  const email = user?.emailAddresses?.[0]?.emailAddress;
  if (!email) {
    redirect("/no-access");
  }

  const rows = await sql`
    SELECT id FROM users
    WHERE email = ${email} AND is_active = true
    LIMIT 1
  `;
  if (rows.length === 0) {
    redirect("/no-access");
  }

  const isAdmin = checkIsAdmin(email);

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
