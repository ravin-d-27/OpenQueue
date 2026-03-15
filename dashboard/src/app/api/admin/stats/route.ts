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

    // ── Overall platform stats ──────────────────────────────────────────────
    const [overview] = await sql`
      SELECT
        (SELECT COUNT(*)::int  FROM users)                            AS total_users,
        (SELECT COUNT(*)::int  FROM users WHERE is_active = true)     AS active_users,
        COUNT(j.id)::int                                              AS total_jobs,
        COUNT(j.id) FILTER (WHERE j.status = 'completed')::int       AS completed_jobs,
        COUNT(j.id) FILTER (WHERE j.status IN ('failed','dead'))::int AS failed_jobs,
        COUNT(j.id) FILTER (WHERE j.status = 'pending')::int         AS pending_jobs,
        COUNT(j.id) FILTER (WHERE j.status = 'processing')::int      AS processing_jobs,
        COUNT(j.id) FILTER (
          WHERE j.created_at > NOW() - INTERVAL '24 hours'
        )::int                                                        AS jobs_24h,
        COUNT(j.id) FILTER (
          WHERE j.created_at > NOW() - INTERVAL '7 days'
        )::int                                                        AS jobs_7d
      FROM jobs j
    `;

    // ── Per-user stats ──────────────────────────────────────────────────────
    const userStats = await sql`
      SELECT
        u.id,
        u.email,
        u.is_active,
        u.created_at,
        u.last_seen_at,
        COUNT(j.id)::int                                              AS total_jobs,
        COUNT(j.id) FILTER (WHERE j.status = 'completed')::int       AS completed_jobs,
        COUNT(j.id) FILTER (WHERE j.status IN ('failed','dead'))::int AS failed_jobs,
        COUNT(j.id) FILTER (WHERE j.status = 'pending')::int         AS pending_jobs,
        COUNT(j.id) FILTER (WHERE j.status = 'processing')::int      AS processing_jobs,
        COUNT(j.id) FILTER (
          WHERE j.created_at > NOW() - INTERVAL '24 hours'
        )::int                                                        AS jobs_24h,
        COUNT(j.id) FILTER (
          WHERE j.created_at > NOW() - INTERVAL '7 days'
        )::int                                                        AS jobs_7d,
        COUNT(DISTINCT j.queue_name)::int                             AS active_queues
      FROM users u
      LEFT JOIN jobs j ON j.user_id = u.id
      GROUP BY u.id, u.email, u.is_active, u.created_at, u.last_seen_at
      ORDER BY total_jobs DESC, u.created_at DESC
    `;

    return NextResponse.json({ overview, users: userStats });
  } catch (err) {
    console.error("[admin/stats] error:", err);
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}
