import { auth, currentUser } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, {
  ssl: "require",
  max: 1,
  idle_timeout: 20,
  connect_timeout: 10,
});

function isAdmin(email: string): boolean {
  const adminEmails = (process.env.ADMIN_EMAILS || "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  return adminEmails.includes(email.toLowerCase());
}

async function ensureTable() {
  await sql`
    CREATE TABLE IF NOT EXISTS signup_requests (
      id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email        TEXT UNIQUE NOT NULL,
      clerk_id     TEXT,
      requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `;
}

async function adminGuard() {
  const { userId } = await auth();
  if (!userId) return null;
  const callerUser = await currentUser();
  const email = callerUser?.emailAddresses?.[0]?.emailAddress;
  if (!email || !isAdmin(email)) return null;
  return email;
}

// GET — list all pending signup requests
export async function GET() {
  try {
    const caller = await adminGuard();
    if (!caller) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    await ensureTable();
    const rows = await sql`
      SELECT id, email, clerk_id, requested_at
      FROM signup_requests
      ORDER BY requested_at ASC
    `;
    return NextResponse.json({ signups: rows });
  } catch (err) {
    console.error("[admin/signups] GET error:", err);
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}

// DELETE — reject (remove) a pending signup request
export async function DELETE(req: NextRequest) {
  try {
    const caller = await adminGuard();
    if (!caller) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }
    const { email } = await req.json() as { email?: string };
    if (!email) {
      return NextResponse.json({ error: "email_required" }, { status: 400 });
    }
    await ensureTable();
    await sql`DELETE FROM signup_requests WHERE email = ${email}`;
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[admin/signups] DELETE error:", err);
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}
