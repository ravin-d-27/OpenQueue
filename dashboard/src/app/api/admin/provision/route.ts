import { auth, currentUser } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

function isAdmin(email: string): boolean {
  const adminEmails = (process.env.ADMIN_EMAILS || "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  return adminEmails.includes(email.toLowerCase());
}

export async function POST(req: NextRequest) {
  try {
    // 1. Must be signed in.
    const { userId } = await auth();
    if (!userId) {
      return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
    }

    // 2. Caller must be an admin.
    const callerUser = await currentUser();
    const callerEmail = callerUser?.emailAddresses?.[0]?.emailAddress;
    if (!callerEmail || !isAdmin(callerEmail)) {
      return NextResponse.json({ error: "forbidden" }, { status: 403 });
    }

    // 3. Parse target email from request body.
    const body = await req.json();
    const { email } = body as { email?: string };
    if (!email || !email.includes("@")) {
      return NextResponse.json({ error: "invalid_email" }, { status: 400 });
    }

    // 4. Call FastAPI /admin/provision (backend owns hashing).
    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://open-queue-ivory.vercel.app";
    const adminSecret = process.env.ADMIN_SECRET;
    if (!adminSecret) {
      return NextResponse.json(
        { error: "admin_secret_not_configured" },
        { status: 500 }
      );
    }

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
      console.error("[admin/provision] FastAPI error:", detail);
      return NextResponse.json({ error: "provision_failed" }, { status: 502 });
    }

    const data = await provisionRes.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("[admin/provision] error:", err);
    return NextResponse.json({ error: "internal_error" }, { status: 500 });
  }
}
