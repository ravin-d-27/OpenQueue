"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";

/**
 * Runs once after sign-in: calls /api/auth/sync, stores the returned
 * token + api_url in localStorage, then redirects to /no-access if the
 * email isn't registered.
 */
export function AuthSync() {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const synced = useRef(false);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || synced.current) return;

    // Skip if we already have a token in this session
    const existing = localStorage.getItem("api_token");
    if (existing) {
      synced.current = true;
      return;
    }

    synced.current = true;

    fetch("/api/auth/sync", { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        if (data.error === "no_access") {
          router.replace("/no-access");
          return;
        }
        if (data.token) {
          localStorage.setItem("api_token", data.token);
          localStorage.setItem("api_url", data.api_url || "https://open-queue-ivory.vercel.app");
        }
      })
      .catch((err) => {
        console.error("[AuthSync] sync failed:", err);
      });
  }, [isLoaded, isSignedIn, router]);

  return null;
}
