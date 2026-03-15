import { auth, currentUser } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import postgres from "postgres";

const sql = postgres(process.env.DATABASE_URL!, {
  ssl: "require",
  max: 1,
  idle_timeout: 20,
  connect_timeout: 10,
});

function isAdminEmail(email: string): boolean {
  const adminEmails = (process.env.ADMIN_EMAILS || "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  return adminEmails.includes(email.toLowerCase());
}

export async function POST() {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
    }

    const user = await currentUser();
    const email = user?.emailAddresses?.[0]?.emailAddress;
    if (!email) {
      return NextResponse.json({ error: "no_email" }, { status: 400 });
    }

    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://open-queue-ivory.vercel.app";
    const adminSecret = process.env.ADMIN_SECRET;
    if (!adminSecret) {
      return NextResponse.json(
        { error: "admin_secret_not_configured" },
        { status: 500 }
      );
    }

    const admin = isAdminEmail(email);

    // Non-admins: must exist in the database with is_active = true.
    if (!admin) {
      const rows = await sql`
        SELECT id FROM users
        WHERE email = ${email} AND is_active = true
        LIMIT 1
      `;
      if (rows.length === 0) {
        return NextResponse.json({ error: "no_access" }, { status: 403 });
      }
    }

    // Delegate token generation + hashing to FastAPI (backend owns the secret).
    // For admins this also upserts them into the users table automatically.
    const provisionRes = await fetch(`${apiUrl}/admin/provision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Secret": adminSecret,
      },
      body: JSON.stringify({ email }),
    });

    if (!provisionRes.ok) {
      const detail = await provisionRes.text();
      console.error("[auth/sync] FastAPI provision failed:", detail);
      return NextResponse.json({ error: "provision_failed" }, { status: 502 });
    }

    const { token } = await provisionRes.json();

    // Update clerk_id and last_seen_at (best-effort, token hash owned by FastAPI).
    await sql`
      UPDATE users
      SET clerk_id = ${userId}, last_seen_at = NOW()
      WHERE email = ${email}
    `;

    return NextResponse.json({ token, api_url: apiUrl });
  } catch (err) {
    console.error("[auth/sync] error:", err);
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}
