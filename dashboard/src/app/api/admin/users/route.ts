import { auth, currentUser } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
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

export async function GET() {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
    }

    const callerUser = await currentUser();
    const callerEmail = callerUser?.emailAddresses?.[0]?.emailAddress;
    if (!callerEmail || !isAdmin(callerEmail)) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }

    const rows = await sql`
      SELECT
        id,
        email,
        is_active,
        clerk_id,
        created_at,
        last_seen_at
      FROM users
      ORDER BY created_at DESC
    `;

    return NextResponse.json({ users: rows });
  } catch (err) {
    console.error("[admin/users] error:", err);
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
    }

    const callerUser = await currentUser();
    const callerEmail = callerUser?.emailAddresses?.[0]?.emailAddress;
    if (!callerEmail || !isAdmin(callerEmail)) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }

    const { email } = await req.json() as { email?: string };
    if (!email) {
      return NextResponse.json({ error: "email_required" }, { status: 400 });
    }

    // Prevent admin from deactivating themselves
    if (email.toLowerCase() === callerEmail.toLowerCase()) {
      return NextResponse.json({ error: "cannot_deactivate_self" }, { status: 400 });
    }

    await sql`
      UPDATE users SET is_active = false WHERE email = ${email}
    `;

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[admin/users] DELETE error:", err);
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}
