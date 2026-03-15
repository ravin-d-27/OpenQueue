"use client";

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";

/**
 * Runs after sign-in (and whenever oq:reauth is fired):
 * calls /api/auth/sync, stores the returned token + api_url in localStorage.
 * Redirects to /no-access if the email isn't registered.
 */
export function AuthSync() {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const synced = useRef(false);

  const doSync = useCallback(() => {
    fetch("/api/auth/sync", { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        if (data.error === "no_access") {
          router.replace("/no-access");
          return;
        }
        if (data.token) {
          localStorage.setItem("api_token", data.token);
          localStorage.setItem(
            "api_url",
            data.api_url || "https://open-queue-ivory.vercel.app"
          );
        }
      })
      .catch((err) => {
        console.error("[AuthSync] sync failed:", err);
      });
  }, [router]);

  // Initial sync on sign-in (skip if we already have a valid token this session).
  useEffect(() => {
    if (!isLoaded || !isSignedIn || synced.current) return;

    const existing = localStorage.getItem("api_token");
    if (existing) {
      synced.current = true;
      return;
    }

    synced.current = true;
    doSync();
  }, [isLoaded, isSignedIn, doSync]);

  // Re-sync whenever the API client fires oq:reauth (e.g. after a 401).
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;

    const handler = () => {
      synced.current = false; // allow re-run
      doSync();
    };

    window.addEventListener("oq:reauth", handler);
    return () => window.removeEventListener("oq:reauth", handler);
  }, [isLoaded, isSignedIn, doSync]);

  return null;
}
