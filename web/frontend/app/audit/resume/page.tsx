"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getPendingAuditUrl, startAuditFlow } from "@/lib/audit-flow";
import { useAuth } from "@/lib/auth";

function ResumeAudit() {
  const router = useRouter();
  const { ready, user } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    const url = getPendingAuditUrl();
    if (!url) {
      router.replace("/");
      return;
    }
    if (!user) {
      router.replace(`/login?next=${encodeURIComponent("/audit/resume")}`);
      return;
    }

    let cancelled = false;
    startAuditFlow(url, { authenticated: true, router }).catch((err: unknown) => {
      if (cancelled) return;
      setError(err instanceof Error ? err.message : "Could not start audit.");
    });

    return () => {
      cancelled = true;
    };
  }, [ready, user, router]);

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col items-center justify-center bg-[#F7F6F1] px-4">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-900 border-t-transparent" />
      <p className="mt-3 text-sm text-neutral-500">
        {error || "Starting your audit…"}
      </p>
      {error && (
        <button
          type="button"
          onClick={() => router.replace("/#audit")}
          className="mt-4 text-sm font-medium text-neutral-900 hover:underline"
        >
          Return to audit
        </button>
      )}
    </div>
  );
}

export default function ResumeAuditPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#F7F6F1]">
          <p className="text-sm text-neutral-500">Starting your audit…</p>
        </div>
      }
    >
      <ResumeAudit />
    </Suspense>
  );
}
